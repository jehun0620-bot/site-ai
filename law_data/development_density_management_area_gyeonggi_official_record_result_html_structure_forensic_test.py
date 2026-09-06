# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from collections import Counter
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S222 = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_search_contract_forensic.json"
S223A = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_dom_contract_hardening.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_html_structure_forensic.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
CATEGORY = "고시ㆍ공고/채용"
PAGE_SIZE = 10
TARGET = "개발밀도관리구역"
DATE_RE = re.compile(r"\b20\d{2}[.\-/]\d{1,2}[.\-/]\d{1,2}\b")


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


def snippet(html: str, pos: int, radius: int = 1200) -> str:
    if pos < 0:
        return ""
    lo = max(0, pos - radius)
    hi = min(len(html), pos + radius)
    return html[lo:hi]


def find_all_positions(haystack: str, needle: str):
    out = []
    start = 0
    while True:
        i = haystack.find(needle, start)
        if i < 0:
            break
        out.append(i)
        start = i + max(1, len(needle))
    return out


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def identity_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bcIdx", "menuId", "seq", "idx", "nttId", "boardId", "articleNo", "pageIndex"]:
        if q.get(key):
            out[key] = q[key][0]
    return out


def anchor_rows(html: str):
    rows = []
    anchor_re = re.compile(r"(?is)<a\b([^>]*)>(.*?)</a>")
    for m in anchor_re.finditer(html):
        raw_tag = "<a" + m.group(1) + ">"
        a = attrs(raw_tag)
        href = a.get("href")
        onclick = a.get("onclick")
        text = clean_html(m.group(2))
        abs_href = None
        if href:
            abs_href = href if href.lower().startswith("javascript:") else urljoin(SEARCH_URL, href)
        rows.append({
            "pos": m.start(),
            "text": text,
            "href": href,
            "absolute_href": abs_href,
            "onclick": onclick,
            "identity": identity_from_url(abs_href) if abs_href and not abs_href.lower().startswith("javascript:") else {},
        })
    return rows


def enclosing_fragment(html: str, pos: int, tags=("li", "article", "tr", "div"), max_back=5000, max_forward=8000):
    lo = max(0, pos - max_back)
    hi = min(len(html), pos + max_forward)
    region = html[lo:hi]
    local = pos - lo
    best = None
    for tag in tags:
        starts = list(re.finditer(rf"(?is)<{tag}\b[^>]*>", region[:local]))
        if not starts:
            continue
        s = starts[-1]
        end = re.search(rf"(?is)</{tag}\s*>", region[local:])
        if not end:
            continue
        frag_start = s.start()
        frag_end = local + end.end()
        frag = region[frag_start:frag_end]
        if best is None or len(frag) < len(best[1]):
            best = (tag, frag, lo + frag_start, lo + frag_end)
    return best


def class_tokens(fragment: str):
    out = []
    for m in re.finditer(r'''class\s*=\s*(["'])(.*?)\1''', fragment or "", flags=re.I | re.S):
        out.extend(m.group(2).split())
    return out


def tag_class_signature(fragment: str):
    m = re.search(r'''(?is)<(li|article|tr|div)\b([^>]*)>''', fragment or "")
    if not m:
        return None
    a = attrs("<x " + m.group(2) + ">")
    return {
        "tag": m.group(1).lower(),
        "id": a.get("id"),
        "class": a.get("class"),
    }


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD RESULT HTML STRUCTURE FORENSIC - S223B")
    print("=" * 78)
    print("Purpose: recover real repeating result-item HTML contract from raw positive-control response")
    print("S222 search contract retained")
    print("S223 result identity superseded")
    print("S223A wrp-search-sorting candidate superseded as false positive")
    print("Positive control only; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = json.loads(S222.read_text(encoding="utf-8"))
    s223a = json.loads(S223A.read_text(encoding="utf-8"))
    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
        and (s222.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_223a = (
        s223a.get("classification") == "GYEONGGI_OFFICIAL_RECORD_RESULT_DOM_IDENTIFIED_DETAIL_IDENTITY_UNRESOLVED"
        and (s223a.get("summary") or {}).get("target_query_executed") is False
        and (s223a.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_222 or not gate_223a:
        raise AssertionError("S223B prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })
    params = {
        "kwd": POSITIVE_CONTROL,
        "category": CATEGORY,
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
    r, err = fetch(session, SEARCH_URL, params=params, referer=ROOT)
    html = r.text if r is not None else ""
    flat = clean_html(html)

    anchors = anchor_rows(html)
    category_positions = find_all_positions(html, CATEGORY)
    positive_positions = find_all_positions(html, POSITIVE_CONTROL)
    count_positions = []
    for needle in ["869", "869건", "869 건"]:
        count_positions.extend(find_all_positions(html, needle))
    count_positions = sorted(set(count_positions))

    category_slices = [{"position": p, "snippet": snippet(html, p)} for p in category_positions[:10]]
    count_slices = [{"position": p, "snippet": snippet(html, p)} for p in count_positions[:20]]

    # Explicit contamination exclusions.
    excluded_markers = [
        "wrp-search-condition",
        "wrp-search-sorting",
        "class=\"rank\"",
        "class='rank'",
        "<header",
        "<footer",
        "gnb",
        "lnb",
    ]

    boardish = []
    for a in anchors:
        href = str(a.get("href") or "")
        onclick = str(a.get("onclick") or "")
        blob = href + " " + onclick
        if not any(k in blob for k in ["bcIdx=", "bsIdx=", "/bbs/board.do", "board.do"]):
            continue
        fraginfo = enclosing_fragment(html, int(a["pos"]))
        if not fraginfo:
            continue
        tag, frag, frag_start, frag_end = fraginfo
        lower = frag.lower()
        contaminated = any(m.lower() in lower for m in excluded_markers)
        txt = clean_html(frag)
        dates = DATE_RE.findall(txt)
        boardish.append({
            "anchor": a,
            "container_tag": tag,
            "container_signature": tag_class_signature(frag),
            "fragment_start": frag_start,
            "fragment_end": frag_end,
            "fragment_text": txt[:1000],
            "date_hits": dates,
            "positive_term_in_fragment": POSITIVE_CONTROL in txt,
            "category_in_fragment": CATEGORY in txt,
            "contaminated": contaminated,
            "class_tokens": class_tokens(frag),
        })

    uncontaminated_boardish = [x for x in boardish if not x["contaminated"]]
    row_specific = [
        x for x in uncontaminated_boardish
        if (x["anchor"].get("identity") or {}).get("bcIdx")
        and x["anchor"].get("text")
    ]

    # Repeating structure statistics only on row-specific candidates.
    sig_counter = Counter()
    class_counter = Counter()
    for x in row_specific:
        sigj = json.dumps(x.get("container_signature"), ensure_ascii=False, sort_keys=True)
        sig_counter[sigj] += 1
        class_counter.update(x.get("class_tokens") or [])

    dominant_signature = None
    dominant_signature_count = 0
    if sig_counter:
        dominant_signature, dominant_signature_count = sig_counter.most_common(1)[0]

    dominant_rows = []
    if dominant_signature:
        for x in row_specific:
            sigj = json.dumps(x.get("container_signature"), ensure_ascii=False, sort_keys=True)
            if sigj == dominant_signature:
                dominant_rows.append(x)

    # Deduplicate by bcIdx first, then href.
    dedup = []
    seen = set()
    for x in dominant_rows:
        ident = x["anchor"].get("identity") or {}
        key = ident.get("bcIdx") or x["anchor"].get("absolute_href")
        if not key or key in seen:
            continue
        seen.add(key)
        dedup.append(x)

    visible_row_count = len(dedup)
    visible_row_count_bounded = 0 < visible_row_count <= PAGE_SIZE
    date_signal_count = sum(1 for x in dedup if x.get("date_hits"))
    positive_fragment_count = sum(1 for x in dedup if x.get("positive_term_in_fragment"))
    row_specific_detail_url_pattern_found = any((x["anchor"].get("identity") or {}).get("bcIdx") for x in dedup)
    repeating_result_contract_found = bool(dominant_signature and dominant_signature_count >= 2 and visible_row_count_bounded)

    category_control_excluded = all("wrp-search-condition" not in (x.get("fragment_text") or "") for x in dedup)
    sorting_rank_excluded = all(
        "wrp-search-sorting" not in (x.get("fragment_text") or "") and " rank " not in (" " + (x.get("fragment_text") or "").lower() + " ")
        for x in dedup
    )

    structure_qualified = bool(
        repeating_result_contract_found
        and row_specific_detail_url_pattern_found
        and visible_row_count_bounded
        and category_control_excluded
        and sorting_rank_excluded
    )

    if structure_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_REPEATING_RESULT_ITEM_AND_ROW_SPECIFIC_DETAIL_URL_CONTRACT_QUALIFIED"
        next_action = "BUILD_S223C_ROW_DETAIL_IDENTITY_REPLAY_USING_ONLY_HARDENED_RESULT_CONTRACT"
    elif row_specific_detail_url_pattern_found:
        classification = "GYEONGGI_OFFICIAL_RECORD_ROW_SPECIFIC_DETAIL_PATTERN_FOUND_STRUCTURE_PARTIAL"
        semantic = "GYEONGGI_OFFICIAL_RECORD_ROW_SPECIFIC_DETAIL_URL_FOUND_REPEATING_STRUCTURE_PARTIAL"
        next_action = "HARDEN_REPEATING_RESULT_CONTAINER_BEFORE_DETAIL_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_TECHNICAL_UNKNOWN"
        next_action = "FORENSIC_SEARCH_RESPONSE_SOURCE_AROUND_CATEGORY_COUNT_AND_BOARD_LINKS"

    sample_rows = []
    for x in dedup[:3]:
        sample_rows.append({
            "title": x["anchor"].get("text"),
            "absolute_href": x["anchor"].get("absolute_href"),
            "identity": x["anchor"].get("identity"),
            "container_signature": x.get("container_signature"),
            "date_hits": x.get("date_hits"),
            "fragment_text": x.get("fragment_text"),
        })

    out = {
        "step": "STEP 17-21-C-16-8-T-136B-S223B",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "supersession": {
            "s222_search_contract_retained": True,
            "s223_result_identity_superseded": True,
            "s223a_sorting_candidate_superseded": True,
            "s223a_false_positive_container": "div.wrp-search-sorting",
        },
        "request": {
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "params": params,
            "body_bytes": len(r.content) if r is not None else 0,
            "category_visible": CATEGORY in flat,
            "positive_control_visible": POSITIVE_CONTROL in flat,
        },
        "raw_positions": {
            "category_positions": category_positions,
            "positive_term_position_count": len(positive_positions),
            "count_positions": count_positions,
            "category_slices": category_slices,
            "count_slices": count_slices,
        },
        "structure": {
            "anchor_count": len(anchors),
            "boardish_candidate_count": len(boardish),
            "uncontaminated_boardish_count": len(uncontaminated_boardish),
            "row_specific_candidate_count": len(row_specific),
            "dominant_container_signature": json.loads(dominant_signature) if dominant_signature else None,
            "dominant_container_count": dominant_signature_count,
            "visible_row_count": visible_row_count,
            "page_size": PAGE_SIZE,
            "visible_row_count_bounded": visible_row_count_bounded,
            "date_signal_count": date_signal_count,
            "positive_term_fragment_count": positive_fragment_count,
            "top_class_tokens": class_counter.most_common(30),
            "category_control_excluded": category_control_excluded,
            "sorting_rank_excluded": sorting_rank_excluded,
            "repeating_result_item_contract_found": repeating_result_contract_found,
            "row_specific_detail_url_pattern_found": row_specific_detail_url_pattern_found,
            "qualified": structure_qualified,
            "sample_rows": sample_rows,
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

    print("HTTP:", out["request"]["http"])
    print("FINAL URL:", out["request"]["final_url"])
    print("BODY BYTES:", out["request"]["body_bytes"])
    print("CATEGORY VISIBLE:", out["request"]["category_visible"])
    print("POSITIVE CONTROL VISIBLE:", out["request"]["positive_control_visible"])
    print("CATEGORY POSITIONS:", category_positions[:20])
    print("COUNT POSITIONS:", count_positions[:20])
    print("ANCHOR COUNT:", len(anchors))
    print("BOARDISH CANDIDATE COUNT:", len(boardish))
    print("UNCONTAMINATED BOARDISH COUNT:", len(uncontaminated_boardish))
    print("ROW-SPECIFIC CANDIDATE COUNT:", len(row_specific))
    print("DOMINANT CONTAINER SIGNATURE:", json.loads(dominant_signature) if dominant_signature else None)
    print("DOMINANT CONTAINER COUNT:", dominant_signature_count)
    print("VISIBLE ROW COUNT:", visible_row_count)
    print("PAGE SIZE:", PAGE_SIZE)
    print("VISIBLE ROW COUNT <= PAGE SIZE:", visible_row_count_bounded)
    print("DATE SIGNAL COUNT:", date_signal_count)
    print("POSITIVE TERM FRAGMENT COUNT:", positive_fragment_count)
    print("CATEGORY CONTROL EXCLUDED:", category_control_excluded)
    print("SEARCH SORTING/RANK EXCLUDED:", sorting_rank_excluded)
    print("REPEATING RESULT ITEM CONTRACT FOUND:", repeating_result_contract_found)
    print("ROW-SPECIFIC DETAIL URL PATTERN FOUND:", row_specific_detail_url_pattern_found)
    print("STRUCTURE QUALIFIED:", structure_qualified)
    print("CLASSIFICATION:", classification)

    print("\nTOP REPEATING CLASS TOKENS")
    for k, v in class_counter.most_common(30):
        print(v, k)

    print("\nSAMPLE HARDENED ROWS")
    for i, row in enumerate(sample_rows, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nCATEGORY RAW SLICES")
    for i, x in enumerate(category_slices[:3], 1):
        print(f"--- CATEGORY SLICE {i} @ {x['position']} ---")
        print(x["snippet"][:2400])

    print("\nCOUNT RAW SLICES")
    for i, x in enumerate(count_slices[:3], 1):
        print(f"--- COUNT SLICE {i} @ {x['position']} ---")
        print(x["snippet"][:2400])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("S223 result identity superseded: True")
    print("S223A sorting candidate superseded: True")
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 search contract gate": gate_222,
        "S223A unresolved gate": gate_223a,
        "S223 result identity superseded": out["supersession"]["s223_result_identity_superseded"] is True,
        "S223A sorting candidate superseded": out["supersession"]["s223a_sorting_candidate_superseded"] is True,
        "request attempted": r is not None,
        "raw HTML positions inspected": isinstance(category_positions, list) and isinstance(count_positions, list),
        "board links structurally inspected": isinstance(boardish, list),
        "row-specific identity inspected": isinstance(row_specific, list),
        "category control exclusion checked": isinstance(category_control_excluded, bool),
        "sorting/rank exclusion checked": isinstance(sorting_rank_excluded, bool),
        "repeating contract checked": isinstance(repeating_result_contract_found, bool),
        "row-specific detail pattern checked": isinstance(row_specific_detail_url_pattern_found, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_ROW_SPECIFIC_DETAIL_PATTERN_FOUND_STRUCTURE_PARTIAL",
            "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S223B Gyeonggi result HTML structure forensic failed")


if __name__ == "__main__":
    main()
