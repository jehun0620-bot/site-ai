# -*- coding: utf-8 -*-
"""S88: recover exact legacy gazette search serialization contract.

S87 proved that merely posting srchBgngYmd/srchEndYmd preserves baseline rows.
This stage inspects the live page JavaScript for fn_srch_list / fn_select_change
and derives which hidden field(s) and values are populated before submission.
It executes only bounded control POSTs required to validate serialization shape.
No UQQ700 target-term query, attachment download, negative evidence, or SITE/runtime
promotion is allowed.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_search_serialization_recovery.json"

URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b(?P<a>[^>]*)/?>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>", re.I | re.S)
SCRIPT_RE = re.compile(r"<script\b[^>]*>(?P<b>.*?)</script>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZ_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
FUNC_TEMPLATE = r"function\s+{name}\s*\(([^)]*)\)\s*\{{(.*?)\}}"
ASSIGN_RE = re.compile(r"\$\(\s*['\"]#([A-Za-z0-9_]+)['\"]\s*\)\.val\(\s*['\"]([^'\"]*)['\"]\s*\)", re.I)
DYNAMIC_ASSIGN_RE = re.compile(r"\$\(\s*['\"]#['\"]\s*\+\s*([A-Za-z0-9_]+)\s*\)\.val\(\s*['\"]([^'\"]*)['\"]\s*\)", re.I)
DATE_INPUT_RE = re.compile(r"srchBgngYmd|srchEndYmd|creatrDt", re.I)


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def rr(r: requests.Response) -> dict:
    return {
        "http": r.status_code,
        "url": str(r.url),
        "host": (urlparse(str(r.url)).hostname or "").lower(),
        "text": r.text,
        "bytes": len(r.content),
    }


def get(session, counter):
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.get(URL, timeout=TIMEOUT, allow_redirects=True))


def post(session, payload, counter):
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.post(URL, data=payload, timeout=TIMEOUT, allow_redirects=True))


def recover_form(text: str) -> dict:
    cand = []
    for fm in FORM_RE.finditer(text or ""):
        fa = attrs(fm.group("a")); body = fm.group("b"); controls = {}; selects = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("a")); name = ia.get("name", ""); typ = ia.get("type", "text").lower()
            if name and not (typ in {"checkbox", "radio"} and "checked" not in ia):
                controls[name] = ia.get("value", "")
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("a")); name = sa.get("name", ""); opts = []; chosen = ""
            for om in OPTION_RE.finditer(sm.group("b")):
                oa = attrs(om.group("a")); value = oa.get("value", ""); label = clean(om.group("b"))
                opts.append({"value": value, "label": label})
                if not chosen:
                    chosen = value
            if name:
                controls[name] = chosen
                selects.append({"name": name, "options": opts})
        score = sum(k in controls for k in ["csrfToken", "srchText", "srchTypeCd", "srchBgngYmd", "srchEndYmd"])
        cand.append({"method": fa.get("method", "GET").upper(), "action": urljoin(URL, fa.get("action", "")), "controls": controls, "selects": selects, "score": score})
    cand.sort(key=lambda x: (x["method"] == "POST", x["score"]), reverse=True)
    if not cand or cand[0]["method"] != "POST":
        raise AssertionError("search POST form missing")
    return cand[0]


def function_body(text: str, name: str) -> str:
    pat = re.compile(FUNC_TEMPLATE.format(name=re.escape(name)), re.I | re.S)
    for sm in SCRIPT_RE.finditer(text or ""):
        m = pat.search(sm.group("b"))
        if m:
            return re.sub(r"\s+", " ", m.group(2)).strip()
    return ""


def rows(text: str) -> list[tuple[int, str]]:
    out = []; seen = set()
    for am in ANCHOR_RE.finditer(text or ""):
        a = attrs(am.group("a")); label = clean(am.group("b")); gm = GAZ_RE.search(label)
        if not gm:
            continue
        mm = CALL_RE.search((a.get("href", "") + " " + a.get("onclick", "")))
        if not mm:
            continue
        key = (int(gm.group(1)), mm.group(1))
        if key not in seen:
            seen.add(key); out.append(key)
    return out


def build_payload(form: dict, *, date_from: str = "", date_to: str = "", date_hidden_value: str | None = None) -> dict[str, str]:
    p = dict(form["controls"])
    p["cntPerPage"] = p.get("cntPerPage") or "30"
    p["sortType"] = p.get("sortType") or "1"
    p["srchTypeCd"] = p.get("srchTypeCd") or "pstTtl"
    p["srchText"] = ""
    p["srchBgngYmd"] = date_from
    p["srchEndYmd"] = date_to
    p["curPage"] = "1"
    if date_hidden_value is not None:
        p["creatrDt"] = date_hidden_value
    return p


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE SEARCH SERIALIZATION RECOVERY - S88")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Attachment download: DISABLED")
    print("Negative evidence: DISABLED")

    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    c = [0]
    base = get(s, c); form = recover_form(base["text"])
    fn_search = function_body(base["text"], "fn_srch_list")
    fn_select = function_body(base["text"], "fn_select_change")
    print("FN_SRCH_LIST:", fn_search[:2200] or "NOT FOUND")
    print("FN_SELECT_CHANGE:", fn_select[:3200] or "NOT FOUND")

    literal_assignments = ASSIGN_RE.findall(fn_select)
    dynamic_assignments = DYNAMIC_ASSIGN_RE.findall(fn_select)
    date_related_snippets = []
    for body in [fn_search, fn_select]:
        for m in DATE_INPUT_RE.finditer(body):
            a = max(0, m.start() - 220); b = min(len(body), m.end() + 420)
            snippet = body[a:b]
            if snippet not in date_related_snippets:
                date_related_snippets.append(snippet)
            if len(date_related_snippets) >= 12:
                break

    print("LITERAL ASSIGNMENTS:", literal_assignments)
    print("DYNAMIC ASSIGNMENTS:", dynamic_assignments)
    print("DATE RELATED SNIPPETS:", date_related_snippets)

    baseline = post(s, build_payload(form), c)
    baseline_ids = rows(baseline["text"])
    print("BASELINE:", {"http": baseline["http"], "rows": baseline_ids})

    # Validate the only date-hidden mapping directly evidenced by fn_select_change.
    date_hidden_value = None
    for variable, value in dynamic_assignments:
        if variable == "srchDtType" and value:
            # This means selected srchDtType controls the hidden field with the same id.
            # For creatrDt the recovered function previously showed value 09.
            if value == "09":
                date_hidden_value = value
    if 'creatrDt' in fn_select and '"09"' in fn_select or "'09'" in fn_select:
        date_hidden_value = "09"

    probes = []
    for label, bg, end, hidden in [
        ("DATE_2024_SERIALIZED", "20240101", "20241231", date_hidden_value),
        ("DATE_2009_SERIALIZED", "20090101", "20091231", date_hidden_value),
    ]:
        p = build_payload(form, date_from=bg, date_to=end, date_hidden_value=hidden)
        r = post(s, p, c); ids = rows(r["text"])
        item = {"label": label, "http": r["http"], "official": r["host"] == HOST, "row_count": len(ids), "identities": ids, "same_as_baseline": ids == baseline_ids, "submitted_creatrDt": hidden}
        probes.append(item); print("PROBE:", item)

    effect = any(not x["same_as_baseline"] for x in probes)
    summary = {
        "request_count": c[0],
        "fn_srch_list_recovered": bool(fn_search),
        "fn_select_change_recovered": bool(fn_select),
        "date_hidden_value_recovered": date_hidden_value,
        "baseline_row_count": len(baseline_ids),
        "serialized_date_filter_effect_observed": effect,
        "semantic_state": "SERIALIZED_DATE_FILTER_EFFECT_OBSERVED" if effect else "SERIALIZATION_STILL_UNRESOLVED",
        "pre2010_reachability_conclusion_allowed": False,
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-35-S88",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "LEGACY_LOCAL_GAZETTE",
        "function_contract": {
            "fn_srch_list": fn_search,
            "fn_select_change": fn_select,
            "literal_assignments": literal_assignments,
            "dynamic_assignments": dynamic_assignments,
            "date_related_snippets": date_related_snippets,
        },
        "baseline_identities": baseline_ids,
        "probes": probes,
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
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "base transport official": base["http"] == 200 and base["host"] == HOST,
        "search POST form recovered": form["method"] == "POST",
        "fn_select_change recovered": bool(fn_select),
        "request budget respected": c[0] <= MAX_REQ,
        "target-term search disabled": not out["target_term_search_executed"],
        "negative evidence disabled": not out["negative_evidence_allowed"],
        "pre2010 conclusion blocked": not summary["pre2010_reachability_conclusion_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nSUMMARY")
    for k, v in summary.items(): print(f"{k}: {v}")
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S88 search serialization recovery failed")


if __name__ == "__main__":
    main()
