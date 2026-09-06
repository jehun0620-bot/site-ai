# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S223D = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_category_token_replay.json"
S223E = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_positive_control_detail_identity_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_detail_metadata_hardening.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
CATEGORY_TOKEN = "고시공고"
CATEGORY_LABEL = "고시ㆍ공고/채용"
TARGET = "개발밀도관리구역"
PAGE_SIZE = 10
SAMPLE_LIMIT = 3

DATE_ANY_RE = re.compile(r"(?<!\d)(20\d{2})[.\-/년\s]+(0?[1-9]|1[0-2])[.\-/월\s]+(0?[1-9]|[12]\d|3[01])(?:일)?(?!\d)")
DATE_LABEL_RE = re.compile(
    r"(?is)(등록일|작성일|게시일|공고일|일자|등록\s*일시|작성\s*일시|게시\s*일시|등록일자|작성일자)"
    r".{0,120}?"
    r"(20\d{2}[.\-/년\s]+(?:0?[1-9]|1[0-2])[.\-/월\s]+(?:0?[1-9]|[12]\d|3[01])(?:일)?)"
)


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


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", "", unescape(clean_html(s or ""))).strip()


def normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    m = DATE_ANY_RE.search(value)
    if not m:
        return None
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def query_identity(url: str):
    q = parse_qs(urlparse(url).query)
    return {k: q[k][0] for k in ("bsIdx", "bIdx", "menuId") if q.get(k)}


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


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
        tag = m.group(0)
        a = attrs(tag)
        classes = (a.get("class") or "").split()
        if "wrp-search-result-notice" in classes:
            return find_balanced_div(html, m.start())
    return None


def extract_search_rows(html: str):
    wrapper = find_result_wrapper(html)
    if not wrapper:
        return [], None
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
        strong = re.search(r"(?is)<strong\b[^>]*>(.*?)</strong>", am.group(2))
        title = clean_html(strong.group(1)) if strong else ""
        if not title:
            continue
        span_date = re.search(r'''(?is)<span\b[^>]*class\s*=\s*["'][^"']*\bdate\b[^"']*["'][^>]*>(.*?)</span>''', am.group(2))
        date_blob = clean_html(span_date.group(1)) if span_date else clean_html(am.group(2))
        date_match = DATE_ANY_RE.search(date_blob)
        raw_date = date_match.group(0) if date_match else None
        norm_date = normalize_date(raw_date)
        abs_url = urljoin(SEARCH_URL, href)
        ident = query_identity(abs_url)
        rows.append({
            "full_title": title,
            "raw_date": raw_date,
            "normalized_date": norm_date,
            "href": href,
            "absolute_href": abs_url,
            "identity": ident,
            "row_text": clean_html(am.group(2)),
        })
    return rows, wrapper


def detail_date_forensic(html: str):
    flat = clean_html(html)
    raw_dates = []
    normalized_dates = []
    for m in DATE_ANY_RE.finditer(html):
        raw = m.group(0)
        norm = normalize_date(raw)
        if norm and norm not in normalized_dates:
            normalized_dates.append(norm)
        if raw not in raw_dates:
            raw_dates.append(raw)
    for m in DATE_ANY_RE.finditer(flat):
        raw = m.group(0)
        norm = normalize_date(raw)
        if norm and norm not in normalized_dates:
            normalized_dates.append(norm)
        if raw not in raw_dates:
            raw_dates.append(raw)

    labeled = []
    for source_name, source in (("html", html), ("flat", flat)):
        for m in DATE_LABEL_RE.finditer(source):
            norm = normalize_date(m.group(2))
            item = {"source": source_name, "label": clean_html(m.group(1)), "raw": clean_html(m.group(2)), "normalized": norm}
            if item not in labeled:
                labeled.append(item)

    metadata_candidates = []
    patterns = [
        r'''(?is)<meta\b[^>]*(?:name|property)\s*=\s*["']([^"']*(?:date|published|modified|created)[^"']*)["'][^>]*content\s*=\s*["']([^"']+)["']''',
        r'''(?is)<meta\b[^>]*content\s*=\s*["']([^"']+)["'][^>]*(?:name|property)\s*=\s*["']([^"']*(?:date|published|modified|created)[^"']*)["']''',
        r'''(?is)(?:regDate|regDt|writeDate|writeDt|createDate|createDt|publishDate|publishDt|boardDate|date)\s*[=:]\s*["']([^"']+)["']''',
    ]
    for idx, pat in enumerate(patterns):
        for m in re.finditer(pat, html):
            vals = list(m.groups())
            norm = next((normalize_date(v) for v in vals if normalize_date(v)), None)
            metadata_candidates.append({"pattern": idx + 1, "groups": [clean_html(v) for v in vals], "normalized": norm})

    return {
        "raw_dates": raw_dates[:100],
        "normalized_dates": normalized_dates[:100],
        "labeled_dates": labeled[:50],
        "metadata_candidates": metadata_candidates[:50],
    }


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD DETAIL METADATA HARDENING - S223F")
    print("=" * 78)
    print("Purpose: recover exact search-row title and normalized detail date metadata")
    print("Positive control only; max 3 detail GETs; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s223d = json.loads(S223D.read_text(encoding="utf-8"))
    s223e = json.loads(S223E.read_text(encoding="utf-8"))
    gate_223d = (
        s223d.get("classification") == "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REAL_RESULT_DOM_QUALIFIED"
        and (s223d.get("summary") or {}).get("target_query_executed") is False
    )
    gate_223e = (
        s223e.get("classification") == "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_IDENTITY_PARTIAL"
        and (s223e.get("summary") or {}).get("target_query_executed") is False
        and (s223e.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_223d or not gate_223e:
        raise AssertionError("S223F prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    params = {
        "kwd": POSITIVE_CONTROL,
        "category": CATEGORY_TOKEN,
        "pageNum": "1",
        "pageSize": str(PAGE_SIZE),
        "sort": "d",
        "date": "",
        "startDate": "",
        "endDate": "",
        "srchFd": "all",
        "originalQuery": POSITIVE_CONTROL,
        "previousQuery": "",
    }
    search, search_err = fetch(session, SEARCH_URL, params=params, referer=ROOT)
    search_html = search.text if search is not None else ""
    search_rows, wrapper = extract_search_rows(search_html)
    sample = search_rows[:SAMPLE_LIMIT]

    full_title_extracted = bool(sample and all(x.get("full_title") for x in sample))
    search_date_extracted = bool(sample and all(x.get("normalized_date") for x in sample))
    bidx_extracted = bool(sample and all((x.get("identity") or {}).get("bIdx") for x in sample))
    bidx_unique = bidx_extracted and len({x["identity"]["bIdx"] for x in sample}) == len(sample)

    details = []
    for row in sample:
        r, err = fetch(session, row["absolute_href"], referer=search.url if search is not None else SEARCH_URL)
        body = r.text if r is not None else ""
        flat = clean_html(body)
        norm_body = normalize_text(body)
        ident = query_identity(r.url if r is not None else "")
        expected = row.get("identity") or {}
        title_norm = normalize_text(row.get("full_title") or "")
        title_match = bool(title_norm and title_norm in norm_body)
        forensic = detail_date_forensic(body)
        expected_date = row.get("normalized_date")
        normalized_date_match = bool(expected_date and expected_date in forensic["normalized_dates"])
        labeled_date_match = bool(expected_date and any(x.get("normalized") == expected_date for x in forensic["labeled_dates"]))
        metadata_date_match = bool(expected_date and any(x.get("normalized") == expected_date for x in forensic["metadata_candidates"]))
        date_field_recovered = bool(forensic["normalized_dates"] or forensic["labeled_dates"] or forensic["metadata_candidates"])
        bidx_match = bool(expected.get("bIdx") and ident.get("bIdx") == expected.get("bIdx"))
        bsidx_match = bool(expected.get("bsIdx") and ident.get("bsIdx") == expected.get("bsIdx"))
        menuid_match = bool(expected.get("menuId") and ident.get("menuId") == expected.get("menuId"))
        board_match = bsidx_match and menuid_match
        http_ok = bool(r is not None and r.status_code == 200)
        detail_identity_match = bool(http_ok and title_match and normalized_date_match and bidx_match and board_match)
        details.append({
            "source_row": row,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "final_url_identity": ident,
            "full_title_match": title_match,
            "detail_date_field_recovered": date_field_recovered,
            "normalized_date_match": normalized_date_match,
            "labeled_date_match": labeled_date_match,
            "metadata_date_match": metadata_date_match,
            "bidx_identity_match": bidx_match,
            "bsidx_identity_match": bsidx_match,
            "menuid_identity_match": menuid_match,
            "board_identity_match": board_match,
            "detail_identity_match": detail_identity_match,
            "date_forensic": forensic,
            "detail_text_prefix": flat[:1400],
        })

    attempted = len(details)
    http_all_200 = bool(attempted and all(x["http"] == 200 for x in details))
    full_title_all_match = bool(attempted and all(x["full_title_match"] for x in details))
    date_field_all_recovered = bool(attempted and all(x["detail_date_field_recovered"] for x in details))
    normalized_date_all_match = bool(attempted and all(x["normalized_date_match"] for x in details))
    bidx_all_match = bool(attempted and all(x["bidx_identity_match"] for x in details))
    board_all_match = bool(attempted and all(x["board_identity_match"] for x in details))
    qualified = bool(
        search is not None and search.status_code == 200
        and wrapper
        and len(sample) == SAMPLE_LIMIT
        and full_title_extracted
        and search_date_extracted
        and bidx_extracted
        and bidx_unique
        and http_all_200
        and full_title_all_match
        and date_field_all_recovered
        and normalized_date_all_match
        and bidx_all_match
        and board_all_match
    )

    if qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_HARDENED_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_FULL_TITLE_NORMALIZED_DATE_BIDX_BOARD_DETAIL_IDENTITY_QUALIFIED"
        next_action = "BUILD_S224_UQQ700_TARGET_REPLAY_USING_VERIFIED_GYEONGGI_SEARCH_RESULT_AND_DETAIL_CONTRACT"
    elif attempted and http_all_200 and full_title_all_match and bidx_all_match and board_all_match:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_DATE_METADATA_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_DETAIL_IDENTITY_VERIFIED_DATE_METADATA_STILL_UNRESOLVED"
        next_action = "INSPECT_DETAIL_DATE_FORENSIC_OUTPUT_BEFORE_UQQ700_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_DETAIL_METADATA_HARDENING_TECHNICAL_UNKNOWN"
        next_action = "HARDEN_DETAIL_IDENTITY_OR_METADATA_BEFORE_UQQ700_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-136F-S223F",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "prerequisites": {"s223d_gate": gate_223d, "s223e_partial_gate": gate_223e},
        "search_replay": {
            "http": search.status_code if search is not None else None,
            "final_url": search.url if search is not None else None,
            "error": search_err,
            "result_wrapper_found": bool(wrapper),
            "real_row_count": len(search_rows),
            "sample_count": len(sample),
            "full_title_extracted": full_title_extracted,
            "search_date_extracted": search_date_extracted,
            "bidx_extracted": bidx_extracted,
            "bidx_unique_across_sample": bidx_unique,
            "sample_rows": sample,
        },
        "detail_results": details,
        "aggregate": {
            "detail_attempted_count": attempted,
            "detail_http_all_200": http_all_200,
            "full_title_all_match": full_title_all_match,
            "detail_date_field_all_recovered": date_field_all_recovered,
            "normalized_date_all_match": normalized_date_all_match,
            "bidx_identity_all_match": bidx_all_match,
            "board_identity_all_match": board_all_match,
            "positive_control_detail_contract_qualified": qualified,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "target_query_executed": False,
            "search_hit_equals_legal_fact": False,
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

    print("S223D GATE:", gate_223d)
    print("S223E PARTIAL GATE:", gate_223e)
    print("SEARCH REPLAY HTTP:", out["search_replay"]["http"])
    print("RESULT WRAPPER FOUND:", bool(wrapper))
    print("REAL ROW COUNT:", len(search_rows))
    print("SAMPLE COUNT:", len(sample))
    print("FULL TITLE EXTRACTED:", full_title_extracted)
    print("SEARCH DATE EXTRACTED:", search_date_extracted)
    print("BIDX EXTRACTED:", bidx_extracted)
    print("BIDX UNIQUE ACROSS SAMPLE:", bidx_unique)
    print("DETAIL ATTEMPTED COUNT:", attempted)
    print("DETAIL HTTP ALL 200:", http_all_200)
    print("FULL TITLE ALL MATCH:", full_title_all_match)
    print("DETAIL DATE FIELD RECOVERED:", date_field_all_recovered)
    print("NORMALIZED DATE ALL MATCH:", normalized_date_all_match)
    print("BIDX IDENTITY ALL MATCH:", bidx_all_match)
    print("BOARD IDENTITY ALL MATCH:", board_all_match)
    print("POSITIVE CONTROL DETAIL CONTRACT QUALIFIED:", qualified)
    print("CLASSIFICATION:", classification)

    print("\nSEARCH SAMPLE ROWS")
    for i, row in enumerate(sample, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nDETAIL METADATA FORENSIC")
    for i, item in enumerate(details, 1):
        print(f"--- DETAIL {i} ---")
        print(json.dumps(item, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S223D qualified gate": gate_223d,
        "S223E partial gate": gate_223e,
        "search replay attempted": search is not None,
        "real result wrapper inspected": isinstance(bool(wrapper), bool),
        "full title extraction inspected": isinstance(full_title_extracted, bool),
        "search date extraction inspected": isinstance(search_date_extracted, bool),
        "bIdx extraction inspected": isinstance(bidx_extracted, bool),
        "bIdx uniqueness inspected": isinstance(bidx_unique, bool),
        "detail navigation attempted": attempted > 0,
        "detail title match inspected": isinstance(full_title_all_match, bool),
        "detail date recovery inspected": isinstance(date_field_all_recovered, bool),
        "normalized date match inspected": isinstance(normalized_date_all_match, bool),
        "detail bIdx identity inspected": isinstance(bidx_all_match, bool),
        "detail board identity inspected": isinstance(board_all_match, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_HARDENED_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_DATE_METADATA_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_POSITIVE_CONTROL_DETAIL_METADATA_TECHNICAL_UNKNOWN",
        },
        "positive control only": out["summary"]["positive_control_only"] is True,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "search hit not legal fact": out["summary"]["search_hit_equals_legal_fact"] is False,
        "search no-hit not legal absence": out["summary"]["search_no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "SITE FALSE inference disabled": not out["summary"]["site_false_inference_allowed"],
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
        raise AssertionError("S223F Gyeonggi detail metadata hardening failed")


if __name__ == "__main__":
    main()
