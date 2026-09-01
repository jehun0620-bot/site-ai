# -*- coding: utf-8 -*-
"""S91: disambiguate actual submit-state fields for Seongnam legacy gazette search.

S90 showed no effect from guessed date/radio combinations. This stage therefore
stops expanding parameter guesses. It inspects the live source for all date/search
field identifiers, label/handler bindings, and form membership, then executes only
positive-control title searches whose browser contract is already structurally
visible. Purpose: prove whether POST search itself is effective and isolate date
UI legacy-name contamination from the actual wire contract.

No UQQ700 target term, attachment download, negative evidence, SITE/runtime
promotion, or pre-2010 absence inference is allowed.
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
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_submit_state_disambiguation.json"

URL = "https://www.seongnam.go.kr/bbs010308"
HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_REQ = 6
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

FORM_RE = re.compile(r"<form\b(?P<a>[^>]*)>(?P<b>.*?)</form>", re.I | re.S)
INPUT_RE = re.compile(r"<input\b(?P<a>[^>]*)/?>", re.I | re.S)
SELECT_RE = re.compile(r"<select\b(?P<a>[^>]*)>(?P<b>.*?)</select>", re.I | re.S)
OPTION_RE = re.compile(r"<option\b(?P<a>[^>]*)>(?P<b>.*?)</option>", re.I | re.S)
ANCHOR_RE = re.compile(r"<a\b(?P<a>[^>]*)>(?P<b>.*?)</a>", re.I | re.S)
ATTR_RE = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
TAG_RE = re.compile(r"<[^>]+>", re.S)
GAZ_RE = re.compile(r"성남시보\s*제\s*(\d+)\s*호", re.I)
CALL_RE = re.compile(r"fn_move_form\s*\(\s*['\"]?(\d+)['\"]?\s*\)", re.I)
FIELD_TOKEN_RE = re.compile(r"\b(?:srchBeginDt|srchEndDt|srchBgngYmd|srchEndYmd|srchDtType|creatrDt|srchTypeCd|srchText)\b", re.I)


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def rr(r: requests.Response) -> dict:
    return {"http": r.status_code, "url": str(r.url), "host": (urlparse(str(r.url)).hostname or "").lower(), "text": r.text, "bytes": len(r.content)}


def get(session, counter):
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.get(URL, timeout=TIMEOUT, allow_redirects=True))


def post(session, data, counter):
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return rr(session.post(URL, data=data, timeout=TIMEOUT, allow_redirects=True))


def recover_form(text: str) -> dict:
    candidates = []
    for fm in FORM_RE.finditer(text or ""):
        fa = attrs(fm.group("a")); body = fm.group("b"); controls = []; defaults = {}; selects = []
        for im in INPUT_RE.finditer(body):
            ia = attrs(im.group("a")); name = ia.get("name", ""); typ = ia.get("type", "text").lower(); checked = "checked" in ia
            controls.append({"tag": "input", "name": name, "id": ia.get("id", ""), "type": typ, "value": ia.get("value", ""), "checked": checked})
            if name and not (typ in {"radio", "checkbox"} and not checked):
                defaults[name] = ia.get("value", "")
        for sm in SELECT_RE.finditer(body):
            sa = attrs(sm.group("a")); name = sa.get("name", ""); opts = []; chosen = ""
            for om in OPTION_RE.finditer(sm.group("b")):
                oa = attrs(om.group("a")); value = oa.get("value", ""); selected = "selected" in oa
                opts.append({"value": value, "label": clean(om.group("b")), "selected": selected})
                if selected or chosen == "":
                    chosen = value
            if name:
                defaults[name] = chosen
                selects.append({"name": name, "options": opts})
        score = sum(k in defaults for k in ["csrfToken", "srchText", "srchTypeCd"])
        candidates.append({"method": fa.get("method", "GET").upper(), "action": urljoin(URL, fa.get("action", "")), "controls": controls, "defaults": defaults, "selects": selects, "body": body, "score": score})
    candidates.sort(key=lambda x: (x["method"] == "POST", x["score"]), reverse=True)
    if not candidates or candidates[0]["method"] != "POST":
        raise AssertionError("search POST form missing")
    return candidates[0]


def gazette_rows(text: str) -> list[tuple[int, str]]:
    out = []; seen = set()
    for am in ANCHOR_RE.finditer(text or ""):
        a = attrs(am.group("a")); label = clean(am.group("b")); gm = GAZ_RE.search(label)
        if not gm:
            continue
        mm = CALL_RE.search(a.get("href", "") + " " + a.get("onclick", ""))
        if not mm:
            continue
        key = (int(gm.group(1)), mm.group(1))
        if key not in seen:
            seen.add(key); out.append(key)
    return out


def context_records(text: str) -> list[dict]:
    out = []
    for m in FIELD_TOKEN_RE.finditer(text or ""):
        a = max(0, m.start() - 260); b = min(len(text), m.end() + 520)
        snippet = re.sub(r"\s+", " ", text[a:b]).strip()
        rec = {"field": m.group(0), "snippet": snippet[:1000]}
        if rec not in out:
            out.append(rec)
        if len(out) >= 40:
            break
    return out


def build_payload(form: dict, extras: dict[str, str] | None = None) -> dict[str, str]:
    p = dict(form["defaults"])
    p["cntPerPage"] = p.get("cntPerPage") or "30"
    p["sortType"] = p.get("sortType") or "1"
    p["curPage"] = "1"
    if extras:
        p.update(extras)
    return p


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE SUBMIT STATE DISAMBIGUATION - S91")
    print("=" * 60)
    print("UQQ700 target-term search: DISABLED")
    print("Attachment download: DISABLED")
    print("Negative evidence: DISABLED")

    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    c = [0]
    base = get(s, c); form = recover_form(base["text"])

    form_names = sorted({x["name"] for x in form["controls"] if x["name"]} | {x["name"] for x in form["selects"] if x["name"]})
    contexts = context_records(base["text"])
    print("FORM CONTROL NAMES:", form_names)
    print("FIELD CONTEXTS:")
    for x in contexts:
        print(x)

    baseline = post(s, build_payload(form), c); baseline_ids = gazette_rows(baseline["text"])
    print("BASELINE:", baseline_ids)

    # Positive-control queries only. These are generic gazette words, not UQQ700 target terms.
    probes = []
    for label, srch_type, term in [
        ("TITLE_CONTROL_SEONGNAM_GAZETTE", "pstTtl", "성남시보"),
        ("TITLE_CONTROL_2088", "pstTtl", "2088"),
        ("CONTENT_CONTROL_SEONGNAM", "pstCn", "성남"),
    ]:
        payload = build_payload(form, {"srchTypeCd": srch_type, "srchText": term})
        r = post(s, payload, c); ids = gazette_rows(r["text"])
        item = {"label": label, "http": r["http"], "official": r["host"] == HOST, "row_count": len(ids), "identities": ids, "same_as_baseline": ids == baseline_ids, "srchTypeCd": srch_type, "srchText": term}
        probes.append(item); print("PROBE:", item)

    effective = [x for x in probes if not x["same_as_baseline"]]
    summary = {
        "request_count": c[0],
        "form_control_names": form_names,
        "srchBeginDt_in_form": "srchBeginDt" in form_names,
        "srchEndDt_in_form": "srchEndDt" in form_names,
        "srchBgngYmd_in_form": "srchBgngYmd" in form_names,
        "srchEndYmd_in_form": "srchEndYmd" in form_names,
        "positive_control_effect_count": len(effective),
        "effective_positive_controls": [x["label"] for x in effective],
        "search_post_effective": bool(effective),
        "semantic_state": "SEARCH_POST_EFFECT_CONFIRMED" if effective else "SEARCH_POST_EFFECT_UNRESOLVED",
        "pre2010_reachability_conclusion_allowed": False,
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-35-S91",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "LEGACY_LOCAL_GAZETTE",
        "form_contract": {"method": form["method"], "action": form["action"], "control_names": form_names, "selects": form["selects"]},
        "field_contexts": contexts,
        "baseline_identities": baseline_ids,
        "positive_control_probes": probes,
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
        "search form recovered": form["method"] == "POST",
        "request budget respected": c[0] <= MAX_REQ,
        "UQQ700 target-term search disabled": not out["target_term_search_executed"],
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
        raise AssertionError("S91 submit state disambiguation failed")


if __name__ == "__main__":
    main()
