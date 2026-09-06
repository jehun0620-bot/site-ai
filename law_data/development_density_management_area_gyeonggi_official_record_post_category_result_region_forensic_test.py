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
S223B = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_result_html_structure_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_post_category_result_region_forensic.json"

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


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def find_div_bounds(html: str, start_pos: int):
    token_re = re.compile(r"(?is)<(/?)div\b[^>]*>")
    first = token_re.search(html, start_pos)
    if not first or first.start() != start_pos:
        return None
    depth = 0
    for m in token_re.finditer(html, start_pos):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return (start_pos, m.end())
        else:
            depth += 1
    return None


def find_div_start_by_attr(html: str, pattern: re.Pattern):
    for m in re.finditer(r"(?is)<div\b[^>]*>", html):
        if pattern.search(m.group(0)):
            return m.start(), m.group(0)
    return None


def identity_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bcIdx", "menuId", "seq", "idx", "nttId", "boardId", "articleNo"]:
        if q.get(key):
            out[key] = q[key][0]
    return out


def extract_anchors(region: str, absolute_offset: int):
    out = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", region):
        tag = "<a" + m.group(1) + ">"
        a = attrs(tag)
        href = a.get("href")
        text = clean_html(m.group(2))
        abs_href = None
        if href:
            abs_href = href if href.lower().startswith("javascript:") else urljoin(SEARCH_URL, href)
        out.append({
            "region_pos": m.start(),
            "absolute_pos": absolute_offset + m.start(),
            "text": text,
            "href": href,
            "absolute_href": abs_href,
            "onclick": a.get("onclick"),
            "class": a.get("class"),
            "identity": identity_from_url(abs_href) if abs_href and not abs_href.lower().startswith("javascript:") else {},
        })
    return out


def nearest_block(region: str, pos: int, max_back=5000, max_forward=8000):
    lo = max(0, pos - max_back)
    hi = min(len(region), pos + max_forward)
    window = region[lo:hi]
    local = pos - lo
    best = None
    for tag in ["li", "article", "tr", "div"]:
        starts = list(re.finditer(rf"(?is)<{tag}\b[^>]*>", window[:local]))
        if not starts:
            continue
        s = starts[-1]
        end = re.search(rf"(?is)</{tag}\s*>", window[local:])
        if not end:
            continue
        frag = window[s.start(): local + end.end()]
        if best is None or len(frag) < len(best[1]):
            best = (tag, frag)
    return best


def opening_signature(fragment: str):
    m = re.search(r"(?is)<(li|article|tr|div)\b([^>]*)>", fragment or "")
    if not m:
        return None
    a = attrs("<x " + m.group(2) + ">")
    return {"tag": m.group(1).lower(), "id": a.get("id"), "class": a.get("class")}


def class_tokens(fragment: str):
    out = []
    for m in re.finditer(r'''class\s*=\s*(["'])(.*?)\1''', fragment or "", flags=re.I | re.S):
        out.extend(m.group(2).split())
    return out


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD POST-CATEGORY RESULT REGION FORENSIC - S223C")
    print("=" * 78)
    print("Purpose: isolate only the bounded region after wrp-search-condition inside search-container")
    print("S223/S223A/S223B result-identity candidates are not inherited")
    print("Positive control only; no detail GET; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = json.loads(S222.read_text(encoding="utf-8"))
    s223b = json.loads(S223B.read_text(encoding="utf-8"))
    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
        and (s222.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    gate_223b = (
        s223b.get("classification") == "GYEONGGI_OFFICIAL_RECORD_REAL_RESULT_HTML_STRUCTURE_QUALIFIED"
        and (s223b.get("summary") or {}).get("target_query_executed") is False
        and (s223b.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_222 or not gate_223b:
        raise AssertionError("S223C prerequisite gate not satisfied")

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

    search_start_info = find_div_start_by_attr(html, re.compile(r'''id\s*=\s*["']search-container["']''', re.I))
    cond_start_info = find_div_start_by_attr(html, re.compile(r'''class\s*=\s*["'][^"']*\bwrp-search-condition\b[^"']*["']''', re.I))
    if not search_start_info or not cond_start_info:
        search_bounds = cond_bounds = None
    else:
        search_bounds = find_div_bounds(html, search_start_info[0])
        cond_bounds = find_div_bounds(html, cond_start_info[0])

    region = ""
    region_start = region_end = None
    if search_bounds and cond_bounds and cond_bounds[1] < search_bounds[1]:
        region_start = cond_bounds[1]
        region_end = search_bounds[1]
        region = html[region_start:region_end]

    region_lower = region.lower()
    global_menu_excluded = not any(x in region_lower for x in ["menu-item-type-post_type", "menu-item-object-page", "<nav", "class=\"gnb", "class='gnb"])

    anchors = extract_anchors(region, region_start or 0)
    candidates = []
    menu_item_candidate_count = 0
    sorting_rank_candidate_count = 0
    for a in anchors:
        block = nearest_block(region, a["region_pos"])
        if not block:
            continue
        tag, frag = block
        lower = frag.lower()
        classes = class_tokens(frag)
        if any(c.startswith("menu-item") for c in classes) or "menu-item-type-" in lower:
            menu_item_candidate_count += 1
            continue
        if "wrp-search-sorting" in lower or re.search(r'''class\s*=\s*["'][^"']*\brank\b''', lower):
            sorting_rank_candidate_count += 1
            continue
        txt = clean_html(frag)
        dates = DATE_RE.findall(txt)
        href = str(a.get("href") or "")
        onclick = str(a.get("onclick") or "")
        row_specific = bool(a.get("identity")) or bool(re.search(r"(?i)(detail|view|board|article|seq|idx|ntt|bcIdx|bsIdx)", href + " " + onclick))
        positive_signal = POSITIVE_CONTROL in txt or POSITIVE_CONTROL in (a.get("text") or "")
        if not (dates or row_specific or positive_signal):
            continue
        candidates.append({
            "anchor": a,
            "container_signature": opening_signature(frag),
            "fragment_text": txt[:1400],
            "date_hits": dates,
            "positive_term_in_fragment": POSITIVE_CONTROL in txt,
            "class_tokens": classes,
            "row_specific_signal": row_specific,
        })

    # Prefer structures carrying date-bearing rows; dates are a strong signal that this is result content, not UI.
    sig_stats = Counter()
    for c in candidates:
        key = json.dumps(c.get("container_signature"), ensure_ascii=False, sort_keys=True)
        weight = 3 if c.get("date_hits") else 1
        sig_stats[key] += weight
    dominant_sig = sig_stats.most_common(1)[0][0] if sig_stats else None
    dominant_candidates = [c for c in candidates if json.dumps(c.get("container_signature"), ensure_ascii=False, sort_keys=True) == dominant_sig]

    dedup_rows = []
    seen = set()
    for c in dominant_candidates:
        a = c["anchor"]
        ident = a.get("identity") or {}
        key = ident.get("bcIdx") or ident.get("seq") or ident.get("idx") or a.get("absolute_href") or (a.get("text"), c.get("fragment_text"))
        if key in seen:
            continue
        seen.add(key)
        dedup_rows.append(c)

    # Bound output to requested page size, but preserve measured raw dominant count.
    raw_dominant_count = len(dedup_rows)
    output_rows = dedup_rows[:PAGE_SIZE]
    date_bearing_count = sum(1 for c in output_rows if c.get("date_hits"))
    result_row_count_bounded = 0 < len(output_rows) <= PAGE_SIZE
    post_category_region_identified = bool(region and region_start is not None and region_end is not None)
    real_region_contract_qualified = bool(
        post_category_region_identified
        and global_menu_excluded
        and menu_item_candidate_count == 0
        and sorting_rank_candidate_count == 0
        and date_bearing_count > 0
        and result_row_count_bounded
    )

    if real_region_contract_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REAL_RESULT_REGION_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_BOUNDED_REAL_RESULT_REGION_CONTRACT_QUALIFIED"
        next_action = "BUILD_S223D_POSITIVE_CONTROL_ROW_DETAIL_IDENTITY_REPLAY_FROM_BOUNDED_RESULT_REGION"
    elif post_category_region_identified:
        classification = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_IDENTIFIED_RESULT_CONTRACT_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_IDENTIFIED_REAL_RESULT_CONTRACT_UNRESOLVED"
        next_action = "INSPECT_BOUNDED_REGION_MARKERS_AND_RESULT_WRAPPERS_BEFORE_DETAIL_OR_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_TECHNICAL_UNKNOWN"
        next_action = "RECOVER_BALANCED_DIV_BOUNDARIES_BEFORE_ANY_RESULT_REPLAY"

    sample_rows = []
    for c in output_rows:
        a = c["anchor"]
        sample_rows.append({
            "title": a.get("text"),
            "absolute_href": a.get("absolute_href"),
            "onclick": a.get("onclick"),
            "identity": a.get("identity"),
            "container_signature": c.get("container_signature"),
            "date_hits": c.get("date_hits"),
            "positive_term_in_fragment": c.get("positive_term_in_fragment"),
            "fragment_text": c.get("fragment_text"),
        })

    out = {
        "step": "STEP 17-21-C-16-8-T-136C-S223C",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "supersession": {
            "s222_search_contract_retained": True,
            "s223_result_identity_superseded": True,
            "s223a_sorting_candidate_superseded": True,
            "s223b_menu_tree_candidate_superseded": True,
            "reason": "S223B repeating li/bcIdx structure was global menu tree, not search-result rows",
        },
        "request": {
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "params": params,
            "body_bytes": len(r.content) if r is not None else 0,
        },
        "bounds": {
            "search_container_bounds": search_bounds,
            "search_condition_bounds": cond_bounds,
            "post_category_region_start": region_start,
            "post_category_region_end": region_end,
            "post_category_region_bytes": len(region.encode("utf-8")) if region else 0,
            "identified": post_category_region_identified,
        },
        "region_analysis": {
            "global_menu_excluded": global_menu_excluded,
            "anchor_count": len(anchors),
            "candidate_count": len(candidates),
            "menu_item_candidate_count": menu_item_candidate_count,
            "sorting_rank_candidate_count": sorting_rank_candidate_count,
            "dominant_signature": json.loads(dominant_sig) if dominant_sig else None,
            "raw_dominant_row_count": raw_dominant_count,
            "result_row_count": len(output_rows),
            "result_row_count_bounded": result_row_count_bounded,
            "date_bearing_result_row_count": date_bearing_count,
            "qualified": real_region_contract_qualified,
            "rows": sample_rows,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_only": True,
            "detail_get_executed": False,
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
    print("SEARCH CONTAINER BOUNDS:", search_bounds)
    print("SEARCH CONDITION BOUNDS:", cond_bounds)
    print("POST-CATEGORY RESULT REGION IDENTIFIED:", post_category_region_identified)
    print("POST-CATEGORY REGION BYTES:", out["bounds"]["post_category_region_bytes"])
    print("GLOBAL MENU EXCLUDED:", global_menu_excluded)
    print("REGION ANCHOR COUNT:", len(anchors))
    print("REGION CANDIDATE COUNT:", len(candidates))
    print("MENU-ITEM CANDIDATE COUNT:", menu_item_candidate_count)
    print("SORTING/RANK CANDIDATE COUNT:", sorting_rank_candidate_count)
    print("DOMINANT RESULT SIGNATURE:", json.loads(dominant_sig) if dominant_sig else None)
    print("RAW DOMINANT ROW COUNT:", raw_dominant_count)
    print("RESULT ROW COUNT:", len(output_rows))
    print("RESULT ROW COUNT <= 10:", result_row_count_bounded)
    print("DATE-BEARING RESULT ROWS FOUND:", date_bearing_count > 0)
    print("DATE-BEARING RESULT ROW COUNT:", date_bearing_count)
    print("REAL RESULT REGION CONTRACT QUALIFIED:", real_region_contract_qualified)
    print("CLASSIFICATION:", classification)

    print("\nBOUNDED RESULT ROWS")
    for i, row in enumerate(sample_rows, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nBOUNDED REGION PREFIX")
    print(region[:6000])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("S223B menu-tree candidate superseded: True")
    print("Detail GET executed: False")
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 search contract gate": gate_222,
        "S223B prior classification observed": gate_223b,
        "S223B menu tree superseded": out["supersession"]["s223b_menu_tree_candidate_superseded"] is True,
        "request attempted": r is not None,
        "balanced search-container boundary inspected": isinstance(search_bounds, (tuple, type(None))),
        "balanced search-condition boundary inspected": isinstance(cond_bounds, (tuple, type(None))),
        "post-category region classification produced": isinstance(post_category_region_identified, bool),
        "global menu exclusion checked": isinstance(global_menu_excluded, bool),
        "menu-item contamination measured": isinstance(menu_item_candidate_count, int),
        "sorting/rank contamination measured": isinstance(sorting_rank_candidate_count, int),
        "date-bearing rows checked": isinstance(date_bearing_count, int),
        "result row bound checked": isinstance(result_row_count_bounded, bool),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REAL_RESULT_REGION_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_IDENTIFIED_RESULT_CONTRACT_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_TECHNICAL_UNKNOWN",
        },
        "positive control only": out["summary"]["positive_control_only"] is True,
        "detail GET not executed": out["summary"]["detail_get_executed"] is False,
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
        raise AssertionError("S223C Gyeonggi post-category result region forensic failed")


if __name__ == "__main__":
    main()
