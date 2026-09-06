# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S223F = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_detail_metadata_hardening.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_uqq700_target_replay.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
CATEGORY_TOKEN = "고시공고"
CATEGORY_LABEL = "고시ㆍ공고/채용"
PAGE_SIZE = 10
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[.\-/](0?[1-9]|1[0-2])[.\-/](0?[1-9]|[12]\d|3[01])(?!\d)")


def fetch(session: requests.Session, url: str, params=None, referer: str | None = None):
    try:
        headers = {"Referer": referer} if referer else None
        r = session.get(url, params=params, timeout=60, allow_redirects=True, headers=headers)
        return r, None
    except requests.RequestException as ex:
        return None, f"{type(ex).__name__}: {ex}"


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    m = DATE_RE.search(raw)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def query_identity(url: str):
    q = parse_qs(urlparse(url).query)
    return {k: q[k][0] for k in ("bsIdx", "bIdx", "menuId") if q.get(k)}


def find_balanced_div(html: str, start_pos: int):
    token_re = re.compile(r"(?is)<(/?)div\b[^>]*>")
    first = token_re.search(html, start_pos)
    if not first or first.start() != start_pos:
        return None
    depth = 0
    for m in token_re.finditer(html, start_pos):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return html[start_pos:m.end()]
        else:
            depth += 1
    return None


def find_result_wrapper(html: str):
    for m in re.finditer(r"(?is)<div\b[^>]*>", html):
        a = attrs(m.group(0))
        if "wrp-search-result-notice" in (a.get("class") or "").split():
            return find_balanced_div(html, m.start())
    return None


def extract_count(wrapper: str | None):
    if not wrapper:
        return None
    m = re.search(r'''(?is)<span\b[^>]*class\s*=\s*["'][^"']*\bcount\b[^"']*["'][^>]*>\s*([\d,]+)\s*</span>''', wrapper)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def extract_rows(wrapper: str | None):
    if not wrapper:
        return []
    rows = []
    for li in re.finditer(r"(?is)<li\b[^>]*>(.*?)</li>", wrapper):
        frag = li.group(1)
        am = re.search(r"(?is)<a\b([^>]*)>(.*?)</a>", frag)
        if not am:
            continue
        a = attrs("<a" + am.group(1) + ">")
        href = a.get("href")
        if not href:
            continue
        body = am.group(2)
        sm = re.search(r"(?is)<strong\b[^>]*>(.*?)</strong>", body)
        title = clean_html(sm.group(1)) if sm else ""
        if not title:
            continue
        dm = re.search(r'''(?is)<span\b[^>]*class\s*=\s*["'][^"']*\bdate\b[^"']*["'][^>]*>(.*?)</span>''', body)
        date_blob = clean_html(dm.group(1)) if dm else clean_html(body)
        date_match = DATE_RE.search(date_blob)
        raw_date = date_match.group(0) if date_match else None
        cate_m = re.search(r'''(?is)<p\b[^>]*class\s*=\s*["'][^"']*\bcate\b[^"']*["'][^>]*>(.*?)(?:</p>|</dd>|$)''', body)
        breadcrumb = clean_html(cate_m.group(1)) if cate_m else None
        abs_url = urljoin(SEARCH_URL, href)
        ident = query_identity(abs_url)
        rows.append({
            "full_title": title,
            "raw_date": raw_date,
            "normalized_date": normalize_date(raw_date),
            "breadcrumb": breadcrumb,
            "href": href,
            "absolute_href": abs_url,
            "identity": ident,
            "bidx_present": bool(ident.get("bIdx")),
            "board_identity_present": bool(ident.get("bsIdx") and ident.get("menuId")),
            "row_text": clean_html(body),
        })
    dedup = []
    seen = set()
    for row in rows:
        key = (row.get("identity") or {}).get("bIdx") or row.get("absolute_href")
        if key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    return dedup


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD UQQ700 TARGET REPLAY - S224")
    print("=" * 78)
    print("Purpose: execute first bounded UQQ700 target replay using verified Gyeonggi search contract")
    print("Search hit != legal fact")
    print("Search no-hit != legal absence")
    print("Candidate detail GET: NOT EXECUTED")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s223f = json.loads(S223F.read_text(encoding="utf-8"))
    gate_223f = (
        s223f.get("classification") == "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_HARDENED_QUALIFIED"
        and (s223f.get("aggregate") or {}).get("positive_control_detail_contract_qualified") is True
        and (s223f.get("summary") or {}).get("target_query_executed") is False
        and (s223f.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_223f:
        raise AssertionError("S224 prerequisite S223F gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    params = {
        "kwd": TARGET,
        "category": CATEGORY_TOKEN,
        "pageNum": "1",
        "pageSize": str(PAGE_SIZE),
        "sort": "d",
        "date": "",
        "startDate": "",
        "endDate": "",
        "srchFd": "all",
        "originalQuery": TARGET,
        "previousQuery": "",
    }
    r, err = fetch(session, SEARCH_URL, params=params, referer=ROOT)
    html = r.text if r is not None else ""
    flat = clean_html(html)
    wrapper = find_result_wrapper(html)
    count = extract_count(wrapper)
    rows = extract_rows(wrapper)[:PAGE_SIZE]

    http_ok = bool(r is not None and r.status_code == 200)
    target_visible = TARGET in flat
    result_wrapper_found = bool(wrapper)
    row_count = len(rows)
    row_count_bounded = row_count <= PAGE_SIZE
    all_rows_have_bidx = bool(rows) and all(x.get("bidx_present") for x in rows)
    all_rows_have_board_identity = bool(rows) and all(x.get("board_identity_present") for x in rows)
    all_rows_have_title = bool(rows) and all(x.get("full_title") for x in rows)

    if not http_ok:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "RETRY_OR_FORENSICALLY_RECOVER_TARGET_SEARCH_RESPONSE_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    elif result_wrapper_found and row_count > 0:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_RESULT_ROWS_FOUND_DISCOVERY_ONLY"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_RESULT_ROWS_FOUND_DISCOVERY_ONLY"
        next_action = "BUILD_S225_UQQ700_CANDIDATE_DETAIL_IDENTITY_AND_LOCAL_DESIGNATION_CONTEXT_REPLAY"
    elif row_count == 0:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        next_action = "CLOSE_OR_EXTEND_GYEONGGI_SOURCE_FAMILY_ONLY_AFTER_BOUNDED_QUERY_COVERAGE_REVIEW"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "INSPECT_TARGET_RESPONSE_STRUCTURE_BEFORE_ANY_LEGAL_OR_SITE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-137-S224",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "prerequisite": {
            "s223f_detail_contract_gate": gate_223f,
            "verified_category_token": CATEGORY_TOKEN,
            "verified_result_wrapper": "wrp-search-result-notice",
            "verified_result_list": "ul.lst-search-result",
            "verified_row_identity": "bIdx",
            "verified_board_identity": "bsIdx+menuId",
        },
        "request": {
            "params": params,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "body_bytes": len(r.content) if r is not None else 0,
        },
        "result": {
            "target_visible_in_response": target_visible,
            "result_wrapper_found": result_wrapper_found,
            "reported_count": count,
            "row_count": row_count,
            "row_count_bounded": row_count_bounded,
            "all_rows_have_bidx": all_rows_have_bidx,
            "all_rows_have_board_identity": all_rows_have_board_identity,
            "all_rows_have_title": all_rows_have_title,
            "candidate_rows": rows,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_query_executed": True,
            "candidate_detail_get_executed": False,
            "search_hit_equals_legal_fact": False,
            "search_hit_equals_designation_identity": False,
            "search_hit_equals_current_validity": False,
            "search_hit_equals_site_inclusion": False,
            "search_no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("S223F DETAIL CONTRACT GATE:", gate_223f)
    print("TARGET QUERY:", TARGET)
    print("CATEGORY TOKEN:", CATEGORY_TOKEN)
    print("HTTP:", out["request"]["http"])
    print("FINAL URL:", out["request"]["final_url"])
    print("BODY BYTES:", out["request"]["body_bytes"])
    print("TARGET VISIBLE IN RESPONSE:", target_visible)
    print("RESULT WRAPPER FOUND:", result_wrapper_found)
    print("REPORTED COUNT:", count)
    print("TARGET RESULT ROW COUNT:", row_count)
    print("TARGET RESULT ROW COUNT <= 10:", row_count_bounded)
    print("ALL ROWS HAVE BIDX:", all_rows_have_bidx)
    print("ALL ROWS HAVE BOARD IDENTITY:", all_rows_have_board_identity)
    print("ALL ROWS HAVE TITLE:", all_rows_have_title)
    print("CANDIDATE DETAIL GET EXECUTED: False")
    print("CLASSIFICATION:", classification)

    print("\nTARGET CANDIDATE ROWS")
    for i, row in enumerate(rows, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Search hit equals legal fact: False")
    print("Search hit equals designation identity: False")
    print("Search hit equals current validity: False")
    print("Search hit equals site inclusion: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S223F qualified detail contract gate": gate_223f,
        "target query executed": out["summary"]["target_query_executed"] is True,
        "request attempted": r is not None,
        "result wrapper checked": isinstance(result_wrapper_found, bool),
        "result count checked": count is None or isinstance(count, int),
        "target rows inspected": isinstance(rows, list),
        "row count bounded": row_count_bounded,
        "candidate detail GET not executed": out["summary"]["candidate_detail_get_executed"] is False,
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_RESULT_ROWS_FOUND_DISCOVERY_ONLY",
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE",
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN",
        },
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search hit not designation identity": out["summary"]["search_hit_equals_designation_identity"] is False,
        "search hit not current validity": out["summary"]["search_hit_equals_current_validity"] is False,
        "search hit not site inclusion": out["summary"]["search_hit_equals_site_inclusion"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["official_designation_identity_verified"] is False,
        "current validity not promoted": out["current_validity_verified"] is False,
        "site inclusion not promoted": out["site_spatial_inclusion_verified"] is False,
        "SITE promotion blocked": out["site_positive_allowed"] is False and out["site_negative_allowed"] is False,
        "runtime registration blocked": out["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S224 Gyeonggi UQQ700 target replay failed")


if __name__ == "__main__":
    main()
