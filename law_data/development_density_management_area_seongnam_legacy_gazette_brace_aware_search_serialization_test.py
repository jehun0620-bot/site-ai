# -*- coding: utf-8 -*-
"""S89: brace-aware recovery of Seongnam legacy gazette search serialization.

S88 recovered fn_srch_list but truncated fn_select_change at the first nested
brace because of a non-nesting regex. This stage uses brace-aware extraction to
recover the complete JavaScript function, derives the exact creatrDt mapping,
and validates bounded date-filter POST serialization against actual gazette row
identities. No UQQ700 target-term query or legal negative inference is allowed.
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
OUT = OUT_DIR / "development_density_management_area_seongnam_legacy_gazette_brace_aware_search_serialization.json"

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
MAPPING_RE = re.compile(
    r"if\s*\(\s*(srchDtType|srchTypeCd)\s*==\s*['\"]([A-Za-z0-9_]+)['\"]\s*\)\s*\{\s*\$\(\s*['\"]#['\"]\s*\+\s*\1\s*\)\.val\(\s*['\"]([^'\"]*)['\"]\s*\)\s*;?\s*\}",
    re.I | re.S,
)


def attrs(raw: str) -> dict[str, str]:
    out = {}
    for m in ATTR_RE.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_RE.sub(" ", raw or ""))).strip()


def response_record(r: requests.Response) -> dict:
    return {
        "http": r.status_code,
        "url": str(r.url),
        "host": (urlparse(str(r.url)).hostname or "").lower(),
        "text": r.text,
        "bytes": len(r.content),
    }


def get(session: requests.Session, counter: list[int]) -> dict:
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return response_record(session.get(URL, timeout=TIMEOUT, allow_redirects=True))


def post(session: requests.Session, data: dict[str, str], counter: list[int]) -> dict:
    if counter[0] >= MAX_REQ:
        raise AssertionError("request budget exceeded")
    counter[0] += 1
    return response_record(session.post(URL, data=data, timeout=TIMEOUT, allow_redirects=True))


def recover_form(text: str) -> dict:
    candidates = []
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
        candidates.append({"method": fa.get("method", "GET").upper(), "action": urljoin(URL, fa.get("action", "")), "controls": controls, "selects": selects, "score": score})
    candidates.sort(key=lambda x: (x["method"] == "POST", x["score"]), reverse=True)
    if not candidates or candidates[0]["method"] != "POST":
        raise AssertionError("search POST form missing")
    return candidates[0]


def extract_function(text: str, name: str) -> str:
    marker = re.search(rf"function\s+{re.escape(name)}\s*\([^)]*\)\s*\{{", text or "", re.I)
    if not marker:
        return ""
    start = marker.start()
    brace_start = (text or "").find("{", marker.start(), marker.end() + 1)
    if brace_start < 0:
        return ""
    depth = 0
    quote = None
    escape = False
    i = brace_start
    while i < len(text):
        ch = text[i]
        if quote:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == quote:
                quote = None
        else:
            if ch in {"'", '"', '`'}:
                quote = ch
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return re.sub(r"\s+", " ", text[start:i + 1]).strip()
        i += 1
    return ""


def gazette_rows(text: str) -> list[tuple[int, str]]:
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


def build_payload(form: dict, *, bg: str = "", end: str = "", use_date_mode: bool = False, date_code: str = "") -> dict[str, str]:
    p = dict(form["controls"])
    p["cntPerPage"] = p.get("cntPerPage") or "30"
    p["sortType"] = p.get("sortType") or "1"
    p["srchTypeCd"] = p.get("srchTypeCd") or "pstTtl"
    p["srchText"] = ""
    p["curPage"] = "1"
    p["srchBgngYmd"] = bg
    p["srchEndYmd"] = end
    if use_date_mode:
        p["srchDtType"] = "creatrDt"
        p["creatrDt"] = date_code
    return p


def main():
    print("=" * 60)
    print("SEONGNAM LEGACY GAZETTE BRACE-AWARE SEARCH SERIALIZATION - S89")
    print("=" * 60)
    print("Target-term search: DISABLED")
    print("Attachment download: DISABLED")
    print("Negative evidence: DISABLED")

    s = requests.Session(); s.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    c = [0]
    base = get(s, c); form = recover_form(base["text"])
    fn_select = extract_function(base["text"], "fn_select_change")
    fn_search = extract_function(base["text"], "fn_srch_list")
    mappings = [{"selector": a, "field": b, "value": v} for a, b, v in MAPPING_RE.findall(fn_select)]
    creatr = [x for x in mappings if x["field"] == "creatrDt"]
    creatr_code = creatr[0]["value"] if creatr else ""

    print("FN_SRCH_LIST:", fn_search[:1200] or "NOT FOUND")
    print("FN_SELECT_CHANGE_LENGTH:", len(fn_select))
    print("FN_SELECT_CHANGE:", fn_select[:7000] or "NOT FOUND")
    print("RECOVERED MAPPINGS:", mappings)
    print("CREATR_DT_MAPPING:", creatr)

    baseline = post(s, build_payload(form), c)
    baseline_ids = gazette_rows(baseline["text"])
    print("BASELINE:", {"http": baseline["http"], "rows": baseline_ids})

    probes = []
    for label, bg, end in [
        ("DATE_2024_EXACT_SERIALIZED", "2024-01-01", "2024-12-31"),
        ("DATE_2009_EXACT_SERIALIZED", "2009-01-01", "2009-12-31"),
    ]:
        payload = build_payload(form, bg=bg, end=end, use_date_mode=bool(creatr_code), date_code=creatr_code)
        r = post(s, payload, c); ids = gazette_rows(r["text"])
        item = {
            "label": label,
            "http": r["http"],
            "official": r["host"] == HOST,
            "row_count": len(ids),
            "identities": ids,
            "same_as_baseline": ids == baseline_ids,
            "submitted_srchDtType": payload.get("srchDtType", ""),
            "submitted_creatrDt": payload.get("creatrDt", ""),
            "submitted_bg": bg,
            "submitted_end": end,
        }
        probes.append(item)
        print("PROBE:", item)

    control = probes[0]
    old = probes[1]
    effect = control["identities"] != baseline_ids
    summary = {
        "request_count": c[0],
        "fn_srch_list_recovered": bool(fn_search),
        "fn_select_change_recovered": bool(fn_select),
        "mapping_count": len(mappings),
        "creatrDt_mapping_recovered": bool(creatr_code),
        "creatrDt_code": creatr_code,
        "baseline_row_count": len(baseline_ids),
        "date_2024_row_count": control["row_count"],
        "date_2009_row_count": old["row_count"],
        "exact_date_filter_effect_observed": effect,
        "date_2009_same_identity_as_baseline": old["identities"] == baseline_ids,
        "semantic_state": "EXACT_DATE_SERIALIZATION_EFFECT_OBSERVED" if effect else "EXACT_SERIALIZATION_NO_EFFECT",
        "pre2010_reachability_conclusion_allowed": False,
    }

    out = {
        "step": "STEP 17-21-C-16-8-T-35-S89",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "LEGACY_LOCAL_GAZETTE",
        "function_contract": {"fn_srch_list": fn_search, "fn_select_change": fn_select, "mappings": mappings},
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
        "fn_srch_list recovered": bool(fn_search),
        "fn_select_change recovered": bool(fn_select),
        "creatrDt mapping recovered": bool(creatr_code),
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
        raise AssertionError("S89 brace-aware serialization recovery failed")


if __name__ == "__main__":
    main()
