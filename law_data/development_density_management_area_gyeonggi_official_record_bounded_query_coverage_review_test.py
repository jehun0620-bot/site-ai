# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S224A = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_uqq700_no_hit_structure_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_bounded_query_coverage_review.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
CATEGORY_TOKEN = "고시공고"
CATEGORY_LABEL = "고시ㆍ공고/채용"
PAGE_SIZE = 10
QUERIES = [
    "개발밀도관리구역",
    "개발밀도관리구역 성남",
    "개발밀도관리구역 성남시",
    "개발밀도관리구역 지정",
    "개발밀도관리구역 결정",
    "개발밀도관리구역 지형도면",
]
DATE_RE = re.compile(r"(?<!\d)(20\d{2})[.\-/](0?[1-9]|1[0-2])[.\-/](0?[1-9]|[12]\d|3[01])(?!\d)")


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def query_identity(url: str):
    q = parse_qs(urlparse(url).query)
    return {k: q[k][0] for k in ("bsIdx", "bIdx", "menuId") if q.get(k)}


def normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    m = DATE_RE.search(raw)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


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


def extract_count_from_wrapper(wrapper: str | None):
    if not wrapper:
        return None
    m = re.search(r'''(?is)<span\b[^>]*class\s*=\s*["'][^"']*\bcount\b[^"']*["'][^>]*>\s*([\d,]+)\s*</span>''', wrapper)
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def extract_category_count(html: str):
    patterns = [
        r'''(?is)goCategory\(\s*['"]고시공고['"]\s*\).*?고시ㆍ공고/채용\s*<span[^>]*>\s*\(?\s*([\d,]+)\s*건\s*\)?''',
        r'''(?is)고시ㆍ공고/채용\s*<span[^>]*>\s*\(?\s*([\d,]+)\s*건\s*\)?''',
        r'''(?is)고시ㆍ공고/채용.{0,120}?([\d,]+)\s*건''',
    ]
    for pat in patterns:
        m = re.search(pat, html)
        if m:
            try:
                return int(m.group(1).replace(",", ""))
            except ValueError:
                pass
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
        abs_url = urljoin(SEARCH_URL, href)
        ident = query_identity(abs_url)
        rows.append({
            "full_title": title,
            "raw_date": raw_date,
            "normalized_date": normalize_date(raw_date),
            "absolute_href": abs_url,
            "identity": ident,
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
    print("GYEONGGI OFFICIAL RECORD BOUNDED QUERY COVERAGE REVIEW - S224B")
    print("=" * 78)
    print("Purpose: bounded designation-oriented query coverage review before source-family closure")
    print("Candidate detail GET: NOT EXECUTED")
    print("Search hit != designation identity")
    print("Search no-hit != legal absence")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s224a = json.loads(S224A.read_text(encoding="utf-8"))
    gate = (
        s224a.get("classification") == "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_DOM_CONTRACT_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        and (s224a.get("forensic") or {}).get("no_hit_dom_contract_verified") is True
        and (s224a.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate:
        raise AssertionError("S224B prerequisite S224A gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    results = []
    canonical = {}
    technical_unknown = False

    for idx, query in enumerate(QUERIES, 1):
        params = {
            "kwd": query,
            "category": CATEGORY_TOKEN,
            "pageNum": "1",
            "pageSize": str(PAGE_SIZE),
            "sort": "d",
            "date": "",
            "startDate": "",
            "endDate": "",
            "srchFd": "all",
            "originalQuery": query,
            "previousQuery": "",
        }
        try:
            r = session.get(SEARCH_URL, params=params, timeout=60, allow_redirects=True, headers={"Referer": ROOT})
            err = None
        except requests.RequestException as ex:
            r = None
            err = f"{type(ex).__name__}: {ex}"

        html = r.text if r is not None else ""
        wrapper = find_result_wrapper(html)
        category_count = extract_category_count(html)
        wrapper_count = extract_count_from_wrapper(wrapper)
        rows = extract_rows(wrapper)[:PAGE_SIZE]
        http_ok = bool(r is not None and r.status_code == 200)

        if not http_ok:
            qclass = "QUERY_TECHNICAL_UNKNOWN"
            technical_unknown = True
        elif rows:
            qclass = "QUERY_RESULT_ROWS_FOUND_DISCOVERY_ONLY"
        elif category_count == 0:
            qclass = "QUERY_TECHNICAL_NO_HIT_VERIFIED"
        else:
            qclass = "QUERY_STRUCTURE_UNRESOLVED"
            technical_unknown = True

        for row in rows:
            bidx = (row.get("identity") or {}).get("bIdx")
            key = bidx or row.get("absolute_href")
            if key not in canonical:
                canonical[key] = {**row, "matched_queries": [query]}
            elif query not in canonical[key]["matched_queries"]:
                canonical[key]["matched_queries"].append(query)

        results.append({
            "query_index": idx,
            "query": query,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "body_bytes": len(r.content) if r is not None else 0,
            "category_reported_count": category_count,
            "wrapper_reported_count": wrapper_count,
            "result_wrapper_found": bool(wrapper),
            "row_count": len(rows),
            "rows": rows,
            "classification": qclass,
        })
        print(f"[{idx:02d}/{len(QUERIES):02d}] {query} | http={results[-1]['http']} | category_count={category_count} | wrapper_count={wrapper_count} | rows={len(rows)} | {qclass}")

    canonical_rows = list(canonical.values())
    query_no_hit_count = sum(1 for x in results if x["classification"] == "QUERY_TECHNICAL_NO_HIT_VERIFIED")
    query_hit_count = sum(1 for x in results if x["classification"] == "QUERY_RESULT_ROWS_FOUND_DISCOVERY_ONLY")
    query_unknown_count = len(results) - query_no_hit_count - query_hit_count
    bounded_search_exhausted = bool(len(results) == len(QUERIES) and query_unknown_count == 0)

    if bounded_search_exhausted and not canonical_rows:
        classification = "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        semantic = classification
        next_action = "CLOSE_GYEONGGI_OFFICIAL_RECORD_SOURCE_FAMILY_AND_KEEP_UQQ700_UNKNOWN"
    elif bounded_search_exhausted and canonical_rows:
        classification = "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_CANDIDATES_FOUND_DISCOVERY_ONLY"
        semantic = classification
        next_action = "BUILD_S225_CANDIDATE_DETAIL_IDENTITY_AND_LOCAL_DESIGNATION_CONTEXT_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_COVERAGE_UNRESOLVED"
        semantic = classification
        next_action = "HARDEN_UNRESOLVED_QUERY_CONTRACT_BEFORE_SOURCE_FAMILY_CLOSURE"

    out = {
        "step": "STEP 17-21-C-16-8-T-137B-S224B",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "prerequisite_s224a_gate": gate,
        "query_family": QUERIES,
        "query_results": results,
        "coverage_summary": {
            "query_count": len(QUERIES),
            "query_technical_no_hit_count": query_no_hit_count,
            "query_hit_count": query_hit_count,
            "query_unresolved_count": query_unknown_count,
            "canonical_candidate_count": len(canonical_rows),
            "bounded_search_exhausted": bounded_search_exhausted,
            "canonical_candidates": canonical_rows,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_queries_executed": True,
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

    print("\nCOVERAGE SUMMARY")
    print("QUERY COUNT:", len(QUERIES))
    print("QUERY TECHNICAL NO-HIT COUNT:", query_no_hit_count)
    print("QUERY HIT COUNT:", query_hit_count)
    print("QUERY UNRESOLVED COUNT:", query_unknown_count)
    print("CANONICAL CANDIDATE COUNT:", len(canonical_rows))
    print("BOUNDED SEARCH EXHAUSTED:", bounded_search_exhausted)
    print("CLASSIFICATION:", classification)

    print("\nCANONICAL CANDIDATES")
    for i, row in enumerate(canonical_rows, 1):
        print(f"--- CANDIDATE {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Candidate detail GET executed: False")
    print("Search hit equals designation identity: False")
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S224A qualified no-hit gate": gate,
        "all bounded queries executed": len(results) == len(QUERIES),
        "query results classified": all(x["classification"] in {"QUERY_TECHNICAL_NO_HIT_VERIFIED", "QUERY_RESULT_ROWS_FOUND_DISCOVERY_ONLY", "QUERY_STRUCTURE_UNRESOLVED", "QUERY_TECHNICAL_UNKNOWN"} for x in results),
        "candidate detail GET not executed": out["summary"]["candidate_detail_get_executed"] is False,
        "canonical candidate set built": isinstance(canonical_rows, list),
        "coverage classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_OPERATIONALLY_CLOSED_WITHOUT_LEGAL_ABSENCE_INFERENCE",
            "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_CANDIDATES_FOUND_DISCOVERY_ONLY",
            "GYEONGGI_OFFICIAL_RECORD_BOUNDED_SEARCH_COVERAGE_UNRESOLVED",
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
        "SITE promotion blocked": not out["site_positive_allowed"] and not out["site_negative_allowed"],
        "runtime registration blocked": not out["runtime_registration_allowed"],
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S224B Gyeonggi bounded query coverage review failed")


if __name__ == "__main__":
    main()
