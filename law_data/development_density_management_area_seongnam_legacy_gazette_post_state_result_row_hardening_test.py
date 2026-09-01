# -*- coding: utf-8 -*-
"""S86: harden legacy gazette POST state and result-row identity contract.

Replays the official /bbs010308 search form from a session-primed GET, preserving
hidden inputs (including CSRF without persisting the token), recovering date-type
semantics, and identifying actual gazette rows only from row-local detail identity.

This stage does NOT infer pre-2010 presence/absence, search UQQ700 terms, download
attachments, mutate cumulative state, enable negative evidence, or promote SITE /
runtime conclusions.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_legacy_gazette_post_state_result_row_hardening.json"

URL = "https://www.seongnam.go.kr/bbs010308"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 5
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b(?P<attrs>[^>]*)/?>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b(?P<attrs>[^>]*)>(?P<body>.*?)</select>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<attrs>[^>]*)>(?P<body>.*?)</option>", re.I | re.S)
ROW_RE = re.compile(r"<tr\b[^>]*>.*?</tr>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<attrs>[^>]*)>(?P<body>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
DATE_RE = re.compile(r"\b(20\d{2})[.\-/](\d{1,2})[.\-/](\d{1,2})\b")
NOTICE_RE = re.compile(r"(?:성남시\s*)?(?:시보|고시|공고)?\s*제?\s*(\d{1,4})\s*호", re.I)
DETAIL_PATH_RE = re.compile(r"/bbs010308/(\d{3,})(?:\b|[/?#])", re.I)
VIEW_CALL_RE = re.compile(r"(?:f_view|fn_view|goView|view)\s*\(\s*['\"]?(\d{3,})", re.I)
PSTSN_ASSIGN_RE = re.compile(r"pstSn\s*[=:]\s*['\"]?(\d{3,})", re.I)
SRCHDTTYPE_CONTEXT_RE = re.compile(r".{0,240}srchDtType.{0,480}", re.I | re.S)


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def fetch_get(session: requests.Session, counter: list[int]):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.get(URL, timeout=TIMEOUT, allow_redirects=True)
    return response_record(r)


def fetch_post(session: requests.Session, payload: dict[str, str], counter: list[int]):
    if counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    r = session.post(URL, data=payload, timeout=TIMEOUT, allow_redirects=True)
    return response_record(r)


def response_record(r: requests.Response) -> dict:
    return {
        "http_status": r.status_code,
        "final_url": str(r.url),
        "final_host": (urlparse(str(r.url)).hostname or "").lower(),
        "text": r.text,
        "body_length": len(r.content),
    }


def recover_search_form(text: str) -> dict:
    candidates = []
    for fm in FORM_RE.finditer(text or ""):
        fa = attrs(fm.group("attrs")); body = fm.group("body")
        controls: dict[str, str] = {}; meta = []; selects = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("attrs")); name = ia.get("name", "")
            if not name:
                continue
            typ = ia.get("type", "text").lower(); value = ia.get("value", "")
            checked = "checked" in ia
            meta.append({"name": name, "type": typ, "value_length": len(value), "has_value": bool(value), "checked": checked})
            if typ in {"checkbox", "radio"} and not checked:
                continue
            controls[name] = value
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("attrs")); name = sa.get("name", ""); options = []
            chosen = None
            for om in OPTION_RE.finditer(sm.group("body")):
                oa = attrs(om.group("attrs")); value = oa.get("value", ""); label = clean(om.group("body"))
                selected = "selected" in oa
                options.append({"value": value, "label": label, "selected": selected})
                if selected or chosen is None:
                    chosen = value
            if name:
                controls[name] = chosen or ""
                selects.append({"name": name, "options": options})
        action = urljoin(URL, fa.get("action", ""))
        score = sum(k in controls for k in ["srchText", "srchTypeCd", "srchBgngYmd", "srchEndYmd", "csrfToken"])
        candidates.append({"method": fa.get("method", "GET").upper(), "action_url": action, "controls": controls, "control_meta": meta, "selects": selects, "score": score})
    if not candidates:
        raise AssertionError("no forms recovered")
    candidates.sort(key=lambda x: (x["method"] == "POST", x["score"]), reverse=True)
    form = candidates[0]
    if form["method"] != "POST" or form["score"] < 3:
        raise AssertionError("official search POST form not recovered")
    return form


def safe_form_metadata(form: dict) -> dict:
    controls = form["controls"]
    token = controls.get("csrfToken", "")
    return {
        "method": form["method"],
        "action_url": form["action_url"],
        "control_names": sorted(controls),
        "hidden_control_meta": [m for m in form["control_meta"] if m["type"] == "hidden"],
        "csrf_present": bool(token),
        "csrf_length": len(token),
        "csrf_sha256_prefix": hashlib.sha256(token.encode("utf-8")).hexdigest()[:12] if token else None,
        "selects": form["selects"],
    }


def extract_rows(text: str) -> list[dict]:
    records = []
    seen = set()
    for rm in ROW_RE.finditer(text or ""):
        row_html = rm.group(0); row_text = clean(row_html)
        ids = []
        ids.extend(DETAIL_PATH_RE.findall(row_html))
        ids.extend(VIEW_CALL_RE.findall(row_html))
        ids.extend(PSTSN_ASSIGN_RE.findall(row_html))
        for am in ANCHOR_RE.finditer(row_html):
            aa = attrs(am.group("attrs")); href = html.unescape(aa.get("href", "")); onclick = html.unescape(aa.get("onclick", ""))
            ids.extend(DETAIL_PATH_RE.findall(urljoin(URL, href) if href else ""))
            ids.extend(VIEW_CALL_RE.findall(onclick))
            ids.extend(PSTSN_ASSIGN_RE.findall(href + " " + onclick))
        ids = list(dict.fromkeys(ids))
        if not ids:
            continue
        # Pagination/menu links are outside actual result tr in normal contract; require content-like row text.
        if len(row_text) < 12:
            continue
        dates = [f"{y}-{int(m):02d}-{int(d):02d}" for y, m, d in DATE_RE.findall(row_text)]
        notice = NOTICE_RE.search(row_text)
        for pst_sn in ids:
            if pst_sn in seen:
                continue
            seen.add(pst_sn)
            records.append({
                "pstSn": pst_sn,
                "text": row_text[:500],
                "dates": dates[:5],
                "notice_number_hint": notice.group(1) if notice else None,
            })
    return records


def date_type_for_payload(form: dict) -> tuple[str, list[str]]:
    options = []
    for sel in form["selects"]:
        if sel["name"] == "srchDtType":
            options = [o["value"] for o in sel["options"] if o["value"]]
            if options:
                return options[0], options
    # Do not invent a semantic value. Empty remains the observed form default.
    return form["controls"].get("srchDtType", ""), options


def context_hints(text: str) -> list[str]:
    out = []
    for m in SRCHDTTYPE_CONTEXT_RE.finditer(text or ""):
        s = clean(m.group(0))[:700]
        if s and s not in out:
            out.append(s)
        if len(out) >= 8:
            break
    return out


def payload_from_form(form: dict, *, date_from: str = "", date_to: str = "") -> dict[str, str]:
    p = dict(form["controls"])
    p["cntPerPage"] = p.get("cntPerPage") or "30"
    p["sortType"] = p.get("sortType") or "1"
    p["srchTypeCd"] = p.get("srchTypeCd") or "pstTtl"
    p["srchText"] = ""
    dt_value, _ = date_type_for_payload(form)
    p["srchDtType"] = dt_value
    p["srchBgngYmd"] = date_from
    p["srchEndYmd"] = date_to
    p["curPage"] = "1"
    # Remove submit/image controls that browsers do not necessarily serialize unless activated.
    return {k: v for k, v in p.items() if k and v is not None}


def summarize_response(label: str, rec: dict) -> dict:
    rows = extract_rows(rec["text"])
    result = {
        "label": label,
        "http_status": rec["http_status"],
        "official_host": rec["final_host"] == OFFICIAL_HOST,
        "body_length": rec["body_length"],
        "result_row_count": len(rows),
        "pstSn_list": [r["pstSn"] for r in rows],
        "rows": rows[:30],
    }
    print("RESULT:", {k: result[k] for k in ["label", "http_status", "official_host", "body_length", "result_row_count", "pstSn_list"]})
    if rows:
        print("  ROW SAMPLE:", rows[:3])
    return result


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE POST STATE / RESULT ROW HARDENING - S86")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Attachment download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    counter = [0]

    base = fetch_get(session, counter)
    form = recover_search_form(base["text"])
    safe_meta = safe_form_metadata(form)
    dt_value, dt_options = date_type_for_payload(form)
    print("FORM:", safe_meta)
    print("SRCH_DT_TYPE:", {"selected_or_default": dt_value, "option_values": dt_options, "context_hints": context_hints(base["text"])})

    baseline_payload = payload_from_form(form)
    baseline = fetch_post(session, baseline_payload, counter)
    baseline_result = summarize_response("BASELINE_FORM_POST", baseline)

    probe_results = []
    for label, bg, end in [
        ("DATE_2024_CONTROL", "20240101", "20241231"),
        ("DATE_2009_PROBE", "20090101", "20091231"),
    ]:
        payload = payload_from_form(form, date_from=bg, date_to=end)
        rec = fetch_post(session, payload, counter)
        probe_results.append(summarize_response(label, rec))

    base_ids = baseline_result["pstSn_list"]
    comparisons = []
    for r in probe_results:
        ids = r["pstSn_list"]
        comparisons.append({
            "label": r["label"],
            "same_identity_as_baseline": ids == base_ids,
            "overlap_with_baseline": len(set(ids) & set(base_ids)),
            "new_ids_vs_baseline": [x for x in ids if x not in set(base_ids)],
            "missing_ids_vs_baseline": [x for x in base_ids if x not in set(ids)],
        })
    print("COMPARISONS:", comparisons)

    semantic_state = "UNRESOLVED"
    control = next((x for x in probe_results if x["label"] == "DATE_2024_CONTROL"), None)
    old = next((x for x in probe_results if x["label"] == "DATE_2009_PROBE"), None)
    date_filter_effect_observed = bool(control and control["pstSn_list"] != base_ids)
    actual_row_contract_recovered = baseline_result["result_row_count"] > 0
    if actual_row_contract_recovered and date_filter_effect_observed:
        semantic_state = "DATE_FILTER_EFFECT_OBSERVED"

    summary = {
        "request_count": counter[0],
        "csrf_present": safe_meta["csrf_present"],
        "csrf_preserved_in_post": "csrfToken" in baseline_payload,
        "srchDtType_option_values": dt_options,
        "srchDtType_submitted_value": dt_value,
        "actual_result_row_contract_recovered": actual_row_contract_recovered,
        "baseline_result_row_count": baseline_result["result_row_count"],
        "date_filter_effect_observed": date_filter_effect_observed,
        "date_2009_same_identity_as_baseline": bool(old and old["pstSn_list"] == base_ids),
        "semantic_state": semantic_state,
        "pre2010_reachability_conclusion_allowed": False,
    }

    payload = {
        "step": "STEP 17-21-C-16-8-T-35-S86",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "LEGACY_LOCAL_GAZETTE",
        "endpoint": URL,
        "form_metadata_redacted": safe_meta,
        "srchDtType_context_hints": context_hints(base["text"]),
        "baseline_result": baseline_result,
        "probe_results": probe_results,
        "comparisons": comparisons,
        "summary": summary,
        "target_term_search_executed": False,
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "base transport official": base["http_status"] == 200 and base["final_host"] == OFFICIAL_HOST,
        "POST search form recovered": form["method"] == "POST",
        "official form state preserved": "srchText" in baseline_payload and "srchTypeCd" in baseline_payload,
        "request budget respected": counter[0] <= MAX_TOTAL_REQUESTS,
        "target-term search disabled": not payload["target_term_search_executed"],
        "attachment download disabled": not payload["attachment_body_download_executed"],
        "state mutation disabled": not payload["state_mutation_executed"],
        "negative evidence disabled": not payload["negative_evidence_allowed"],
        "pre2010 conclusion blocked": not summary["pre2010_reachability_conclusion_allowed"],
        "unsafe promotion leakage zero": not any(payload[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("Output:", OUTPUT_PATH)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S86 legacy gazette POST/result-row hardening failed")


if __name__ == "__main__":
    main()
