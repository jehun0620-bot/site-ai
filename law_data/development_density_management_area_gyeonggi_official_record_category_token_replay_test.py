# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
S222 = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_search_contract_forensic.json"
S223C = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_post_category_result_region_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_category_token_replay.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
POSITIVE_CONTROL = "예산"
CATEGORY_LABEL = "고시ㆍ공고/채용"
CATEGORY_TOKEN = "고시공고"
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


def find_div_start_by_attr(html: str, pattern: re.Pattern):
    for m in re.finditer(r"(?is)<div\b[^>]*>", html):
        if pattern.search(m.group(0)):
            return m.start(), m.group(0)
    return None


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


def identity_from_url(url: str):
    q = parse_qs(urlparse(url).query)
    out = {}
    for key in ["bsIdx", "bcIdx", "menuId", "seq", "idx", "nttId", "boardId", "articleNo", "pageIndex"]:
        if q.get(key):
            out[key] = q[key][0]
    return out


def nearest_block(region: str, pos: int, max_back=5000, max_forward=10000):
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


def extract_region_rows(region: str):
    rows = []
    for m in re.finditer(r"(?is)<a\b([^>]*)>(.*?)</a>", region):
        a = attrs("<a" + m.group(1) + ">")
        href = a.get("href")
        onclick = a.get("onclick")
        title = clean_html(m.group(2))
        if not title:
            continue
        abs_href = None
        if href:
            abs_href = href if href.lower().startswith("javascript:") else urljoin(SEARCH_URL, href)
        block = nearest_block(region, m.start())
        if not block:
            continue
        _, frag = block
        lower = frag.lower()
        classes = class_tokens(frag)
        if any(c.startswith("menu-item") for c in classes):
            continue
        if "wrp-search-sorting" in lower or re.search(r'''class\s*=\s*["'][^"']*\brank\b''', lower):
            continue
        text = clean_html(frag)
        dates = DATE_RE.findall(text)
        identity = identity_from_url(abs_href) if abs_href and not abs_href.lower().startswith("javascript:") else {}
        row_specific = bool(identity) or bool(re.search(r"(?i)(detail|view|board|article|seq|idx|ntt|bcidx|bsidx)", (href or "") + " " + (onclick or "")))
        if not (dates or row_specific):
            continue
        rows.append({
            "title": title,
            "href": href,
            "absolute_href": abs_href,
            "onclick": onclick,
            "identity": identity,
            "container_signature": opening_signature(frag),
            "date_hits": dates,
            "fragment_text": text[:1600],
        })
    # Deduplicate by stable identity or href/title.
    dedup = []
    seen = set()
    for row in rows:
        ident = row.get("identity") or {}
        key = ident.get("bcIdx") or ident.get("nttId") or ident.get("seq") or ident.get("idx") or row.get("absolute_href") or row.get("title")
        if not key or key in seen:
            continue
        seen.add(key)
        dedup.append(row)
    return dedup


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD CATEGORY TOKEN REPLAY - S223D")
    print("=" * 78)
    print("Purpose: replay positive control with actual category request token '고시공고'")
    print("Display label != request token")
    print("No detail GET; UQQ700 target query is NOT executed")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s222 = json.loads(S222.read_text(encoding="utf-8"))
    s223c = json.loads(S223C.read_text(encoding="utf-8"))
    gate_222 = (
        s222.get("classification") == "GYEONGGI_OFFICIAL_SEARCH_SURFACE_POSITIVE_CONTROL_QUALIFIED"
        and (s222.get("summary") or {}).get("target_query_executed") is False
    )
    gate_223c = (
        s223c.get("classification") == "GYEONGGI_OFFICIAL_RECORD_POST_CATEGORY_REGION_IDENTIFIED_RESULT_CONTRACT_UNRESOLVED"
        and (s223c.get("summary") or {}).get("target_query_executed") is False
        and (s223c.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_222 or not gate_223c:
        raise AssertionError("S223D prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    })

    # First replay the generic positive-control page to prove the actual token mapping exists in live HTML.
    pre_params = {
        "kwd": POSITIVE_CONTROL,
        "category": "",
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
    pre, pre_err = fetch(session, SEARCH_URL, params=pre_params, referer=ROOT)
    pre_html = pre.text if pre is not None else ""
    token_pattern = re.compile(r"goCategory\(\s*['\"]고시공고['\"]\s*\)", re.I)
    token_mapping_visible = bool(token_pattern.search(pre_html) and CATEGORY_LABEL in clean_html(pre_html))

    params = dict(pre_params)
    params["category"] = CATEGORY_TOKEN
    r, err = fetch(session, SEARCH_URL, params=params, referer=pre.url if pre is not None else ROOT)
    html = r.text if r is not None else ""
    flat = clean_html(html)

    search_start_info = find_div_start_by_attr(html, re.compile(r'''id\s*=\s*["']search-container["']''', re.I))
    cond_start_info = find_div_start_by_attr(html, re.compile(r'''class\s*=\s*["'][^"']*\bwrp-search-condition\b[^"']*["']''', re.I))
    search_bounds = find_div_bounds(html, search_start_info[0]) if search_start_info else None
    cond_bounds = find_div_bounds(html, cond_start_info[0]) if cond_start_info else None

    region = ""
    region_start = region_end = None
    if search_bounds and cond_bounds and cond_bounds[1] < search_bounds[1]:
        region_start = cond_bounds[1]
        region_end = search_bounds[1]
        region = html[region_start:region_end]

    # Remove the known sorting block entirely before row extraction.
    sorting_start = find_div_start_by_attr(region, re.compile(r'''class\s*=\s*["'][^"']*\bwrp-search-sorting\b[^"']*["']''', re.I)) if region else None
    content_region = region
    sorting_bounds = None
    if sorting_start:
        sorting_bounds = find_div_bounds(region, sorting_start[0])
        if sorting_bounds:
            content_region = region[:sorting_bounds[0]] + region[sorting_bounds[1]:]

    result_rows = extract_region_rows(content_region)
    bounded_rows = result_rows[:PAGE_SIZE]
    date_bearing = [x for x in bounded_rows if x.get("date_hits")]
    sorting_rank_excluded = "wrp-search-sorting" not in content_region.lower() and "검색어 순위" not in clean_html(content_region)
    menu_excluded = "menu-item-type-" not in content_region.lower() and "menu-item-object-" not in content_region.lower()
    category_result_content_present = bool(bounded_rows or DATE_RE.search(clean_html(content_region)))
    result_row_count_ok = 0 < len(bounded_rows) <= PAGE_SIZE
    real_result_dom_contract_qualified = bool(
        token_mapping_visible
        and r is not None
        and r.status_code == 200
        and category_result_content_present
        and result_row_count_ok
        and len(date_bearing) > 0
        and sorting_rank_excluded
        and menu_excluded
    )

    if real_result_dom_contract_qualified:
        classification = "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REAL_RESULT_DOM_QUALIFIED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_TOKEN_GOSIGONGGO_POSITIVE_CONTROL_RESULT_DOM_QUALIFIED"
        next_action = "BUILD_S223E_POSITIVE_CONTROL_RESULT_DETAIL_IDENTITY_REPLAY_BEFORE_UQQ700_TARGET_REPLAY"
    elif token_mapping_visible and r is not None and r.status_code == 200:
        classification = "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REPLAY_RESULT_DOM_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_TOKEN_GOSIGONGGO_REPLAYED_RESULT_DOM_UNRESOLVED"
        next_action = "INSPECT_CATEGORY_TOKEN_RESPONSE_RESULT_WRAPPERS_BEFORE_DETAIL_OR_TARGET_REPLAY"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_CATEGORY_TOKEN_GOSIGONGGO_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "RECOVER_CATEGORY_TOKEN_REQUEST_CONTRACT_BEFORE_ANY_TARGET_REPLAY"

    out = {
        "step": "STEP 17-21-C-16-8-T-136D-S223D",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "category_contract": {
            "display_label": CATEGORY_LABEL,
            "actual_request_token": CATEGORY_TOKEN,
            "token_mapping_visible": token_mapping_visible,
            "label_value_replay_superseded": True,
        },
        "prerequisite_request": {
            "http": pre.status_code if pre is not None else None,
            "final_url": pre.url if pre is not None else None,
            "error": pre_err,
        },
        "token_replay_request": {
            "params": params,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "body_bytes": len(r.content) if r is not None else 0,
            "category_label_visible": CATEGORY_LABEL in flat,
            "positive_control_visible": POSITIVE_CONTROL in flat,
        },
        "bounds": {
            "search_container_bounds": search_bounds,
            "search_condition_bounds": cond_bounds,
            "post_category_region_start": region_start,
            "post_category_region_end": region_end,
            "sorting_bounds_within_region": sorting_bounds,
            "content_region_bytes": len(content_region.encode("utf-8")) if content_region else 0,
        },
        "result_contract": {
            "category_result_content_present": category_result_content_present,
            "menu_excluded": menu_excluded,
            "sorting_rank_excluded": sorting_rank_excluded,
            "raw_result_row_count": len(result_rows),
            "result_row_count": len(bounded_rows),
            "result_row_count_bounded": result_row_count_ok,
            "date_bearing_row_count": len(date_bearing),
            "qualified": real_result_dom_contract_qualified,
            "rows": bounded_rows,
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

    print("ACTUAL CATEGORY TOKEN:", CATEGORY_TOKEN)
    print("CATEGORY DISPLAY LABEL:", CATEGORY_LABEL)
    print("CATEGORY TOKEN MAPPING VISIBLE:", token_mapping_visible)
    print("CATEGORY TOKEN REPLAY HTTP:", out["token_replay_request"]["http"])
    print("CATEGORY TOKEN REPLAY FINAL URL:", out["token_replay_request"]["final_url"])
    print("BODY BYTES:", out["token_replay_request"]["body_bytes"])
    print("SEARCH CONTAINER BOUNDS:", search_bounds)
    print("SEARCH CONDITION BOUNDS:", cond_bounds)
    print("SORTING BOUNDS WITHIN REGION:", sorting_bounds)
    print("CATEGORY RESULT CONTENT PRESENT:", category_result_content_present)
    print("GLOBAL MENU EXCLUDED:", menu_excluded)
    print("SEARCH SORTING/RANK EXCLUDED:", sorting_rank_excluded)
    print("RAW RESULT ROW COUNT:", len(result_rows))
    print("RESULT ROW COUNT:", len(bounded_rows))
    print("RESULT ROW COUNT <= 10:", result_row_count_ok)
    print("DATE-BEARING ROWS:", len(date_bearing))
    print("REAL RESULT DOM CONTRACT QUALIFIED:", real_result_dom_contract_qualified)
    print("CLASSIFICATION:", classification)

    print("\nTOKEN REPLAY RESULT ROWS")
    for i, row in enumerate(bounded_rows, 1):
        print(f"--- ROW {i} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nTOKEN REPLAY CONTENT REGION PREFIX")
    print(content_region[:8000])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Display-label replay superseded: True")
    print("Detail GET executed: False")
    print("Target query executed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S222 search contract gate": gate_222,
        "S223C unresolved gate": gate_223c,
        "actual category token mapping checked": isinstance(token_mapping_visible, bool),
        "display-label replay superseded": out["category_contract"]["label_value_replay_superseded"] is True,
        "token replay attempted": r is not None,
        "search-container boundary inspected": isinstance(search_bounds, (tuple, type(None))),
        "search-condition boundary inspected": isinstance(cond_bounds, (tuple, type(None))),
        "sorting region exclusion checked": isinstance(sorting_rank_excluded, bool),
        "global menu exclusion checked": isinstance(menu_excluded, bool),
        "category result content checked": isinstance(category_result_content_present, bool),
        "result rows inspected": isinstance(bounded_rows, list),
        "date-bearing rows inspected": isinstance(date_bearing, list),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REAL_RESULT_DOM_QUALIFIED",
            "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REPLAY_RESULT_DOM_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_ACTUAL_CATEGORY_TOKEN_REPLAY_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S223D Gyeonggi category token replay failed")


if __name__ == "__main__":
    main()
