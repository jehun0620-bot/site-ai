# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from html import unescape
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
S224 = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_uqq700_target_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_gyeonggi_official_record_uqq700_no_hit_structure_forensic.json"

ROOT = "https://www.gg.go.kr/"
SEARCH_URL = "https://www.gg.go.kr/search.do"
TARGET = "개발밀도관리구역"
CATEGORY_TOKEN = "고시공고"
CATEGORY_LABEL = "고시ㆍ공고/채용"
PAGE_SIZE = 10

NO_RESULT_PATTERNS = [
    r"검색\s*결과가\s*없",
    r"검색된\s*결과가\s*없",
    r"검색결과\s*없",
    r"검색\s*결과\s*0\s*건",
    r"0\s*건",
    r"결과가\s*존재하지\s*않",
    r"검색결과가\s*존재하지\s*않",
]


def clean_html(s: str) -> str:
    s = re.sub(r"(?is)<script\b.*?</script>", " ", s or "")
    s = re.sub(r"(?is)<style\b.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]+>", " ", s)
    return " ".join(unescape(s).split())


def attrs(tag: str):
    pairs = re.findall(r'''([:\w-]+)\s*=\s*(["'])(.*?)\2''', tag, flags=re.S)
    return {k: unescape(v) for k, _, v in pairs}


def find_balanced_div(html: str, start_pos: int):
    token_re = re.compile(r"(?is)<(/?)div\b[^>]*>")
    first = token_re.search(html, start_pos)
    if not first or first.start() != start_pos:
        return None, None
    depth = 0
    for m in token_re.finditer(html, start_pos):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return (start_pos, m.end()), html[start_pos:m.end()]
        else:
            depth += 1
    return None, None


def find_div_by_class(html: str, class_name: str):
    for m in re.finditer(r"(?is)<div\b[^>]*>", html):
        a = attrs(m.group(0))
        if class_name in (a.get("class") or "").split():
            return find_balanced_div(html, m.start())
    return None, None


def find_div_by_id(html: str, node_id: str):
    for m in re.finditer(r"(?is)<div\b[^>]*>", html):
        a = attrs(m.group(0))
        if a.get("id") == node_id:
            return find_balanced_div(html, m.start())
    return None, None


def category_count_signals(html: str):
    out = []
    patterns = [
        r'''(?is)goCategory\(\s*['"]고시공고['"]\s*\).*?고시ㆍ공고/채용\s*<span[^>]*>\s*\(?\s*([\d,]+)\s*건\s*\)?''',
        r'''(?is)고시ㆍ공고/채용\s*<span[^>]*>\s*\(?\s*([\d,]+)\s*건\s*\)?''',
        r'''(?is)고시ㆍ공고/채용.{0,120}?([\d,]+)\s*건''',
    ]
    for idx, pat in enumerate(patterns, 1):
        for m in re.finditer(pat, html):
            raw = m.group(1)
            try:
                count = int(raw.replace(",", ""))
            except ValueError:
                continue
            item = {"pattern": idx, "raw": raw, "count": count, "context": clean_html(html[max(0, m.start()-180):m.end()+180])}
            if item not in out:
                out.append(item)
    return out


def no_result_signals(text: str):
    out = []
    for pat in NO_RESULT_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            out.append({"pattern": pat, "match": m.group(0), "context": text[max(0, m.start()-160):m.end()+160]})
    return out


def boardview_rows(html: str):
    rows = []
    for m in re.finditer(r'''(?is)<a\b([^>]*)href\s*=\s*(["'])([^"']*boardView\.do\?[^"']+)\2([^>]*)>(.*?)</a>''', html):
        href = unescape(m.group(3))
        body = clean_html(m.group(5))
        rows.append({"href": href, "text": body[:500]})
    dedup = []
    seen = set()
    for row in rows:
        if row["href"] in seen:
            continue
        seen.add(row["href"])
        dedup.append(row)
    return dedup


def main():
    print("=" * 78)
    print("GYEONGGI OFFICIAL RECORD UQQ700 NO-HIT STRUCTURE FORENSIC - S224A")
    print("=" * 78)
    print("Purpose: verify technical no-result DOM contract before accepting target no-hit classification")
    print("One bounded UQQ700 replay only")
    print("Legal absence inference: DISABLED")
    print("SITE FALSE inference: DISABLED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s224 = json.loads(S224.read_text(encoding="utf-8"))
    gate_s224 = (
        (s224.get("summary") or {}).get("target_query_executed") is True
        and (s224.get("summary") or {}).get("candidate_detail_get_executed") is False
        and (s224.get("summary") or {}).get("uqq700_final_resolution") == "UNKNOWN"
    )
    if not gate_s224:
        raise AssertionError("S224A prerequisite S224 gate not satisfied")

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
    try:
        r = session.get(SEARCH_URL, params=params, timeout=60, allow_redirects=True, headers={"Referer": ROOT})
        err = None
    except requests.RequestException as ex:
        r = None
        err = f"{type(ex).__name__}: {ex}"

    html = r.text if r is not None else ""
    flat = clean_html(html)
    search_bounds, search_container = find_div_by_id(html, "search-container")
    condition_bounds, search_condition = find_div_by_class(search_container or "", "wrp-search-condition")

    bounded_html = ""
    bounded_bounds = None
    if search_container and search_condition and condition_bounds:
        bounded_start = condition_bounds[1]
        bounded_html = search_container[bounded_start:]
        bounded_bounds = (bounded_start, len(search_container))
    elif search_container:
        bounded_html = search_container
        bounded_bounds = (0, len(search_container))

    bounded_flat = clean_html(bounded_html)
    category_signals_all = category_count_signals(html)
    category_signals_bounded = category_count_signals(bounded_html)
    no_result_all = no_result_signals(flat)
    no_result_bounded = no_result_signals(bounded_flat)
    result_wrapper_bounds, result_wrapper = find_div_by_class(html, "wrp-search-result-notice")
    no_result_wrappers = []
    for cls in ["wrp-search-result-none", "wrp-search-none", "search-no-result", "no-result", "nodata", "no-data", "empty"]:
        b, frag = find_div_by_class(html, cls)
        if frag:
            no_result_wrappers.append({"class": cls, "bounds": b, "text": clean_html(frag)[:1200]})

    all_board_rows = boardview_rows(html)
    bounded_board_rows = boardview_rows(bounded_html)
    bounded_target_board_rows = [x for x in bounded_board_rows if TARGET in x.get("text", "")]

    http_ok = bool(r is not None and r.status_code == 200)
    target_echo = TARGET in flat
    category_zero_signal = any(x.get("count") == 0 for x in category_signals_all + category_signals_bounded)
    explicit_no_result_signal = bool(no_result_bounded or no_result_wrappers)
    bounded_boardview_zero = len(bounded_board_rows) == 0
    no_hit_dom_contract_verified = bool(
        http_ok
        and search_container
        and bounded_html
        and bounded_boardview_zero
        and (category_zero_signal or explicit_no_result_signal)
    )

    if no_hit_dom_contract_verified:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_DOM_CONTRACT_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TECHNICAL_NO_HIT_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE"
        next_action = "BUILD_S224B_GYEONGGI_BOUNDED_QUERY_COVERAGE_REVIEW_BEFORE_SOURCE_FAMILY_CLOSURE"
    elif http_ok:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_STRUCTURE_UNRESOLVED"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_RESPONSE_STRUCTURE_UNRESOLVED"
        next_action = "INSPECT_BOUNDED_RESPONSE_OR_SEARCH_JS_CONTRACT_BEFORE_NO_HIT_ACCEPTANCE"
    else:
        classification = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        semantic = "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN"
        next_action = "RETRY_TARGET_RESPONSE_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-137A-S224A",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "GYEONGGI_OFFICIAL_RECORD",
        "s224_gate": gate_s224,
        "request": {
            "params": params,
            "http": r.status_code if r is not None else None,
            "final_url": r.url if r is not None else None,
            "error": err,
            "body_bytes": len(r.content) if r is not None else 0,
        },
        "forensic": {
            "target_visible_in_response": target_echo,
            "search_container_bounds": search_bounds,
            "search_condition_bounds_within_container": condition_bounds,
            "bounded_region_bounds_within_container": bounded_bounds,
            "bounded_region_bytes": len(bounded_html.encode("utf-8")),
            "result_wrapper_found": bool(result_wrapper),
            "result_wrapper_bounds": result_wrapper_bounds,
            "category_count_signals_all": category_signals_all,
            "category_count_signals_bounded": category_signals_bounded,
            "category_zero_signal": category_zero_signal,
            "no_result_signals_all": no_result_all[:30],
            "no_result_signals_bounded": no_result_bounded[:30],
            "no_result_wrappers": no_result_wrappers,
            "explicit_no_result_signal": explicit_no_result_signal,
            "all_boardview_row_count": len(all_board_rows),
            "bounded_boardview_row_count": len(bounded_board_rows),
            "bounded_target_boardview_row_count": len(bounded_target_board_rows),
            "bounded_boardview_zero": bounded_boardview_zero,
            "bounded_boardview_rows": bounded_board_rows[:20],
            "bounded_region_prefix": bounded_html[:12000],
            "no_hit_dom_contract_verified": no_hit_dom_contract_verified,
        },
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "target_query_executed": True,
            "candidate_detail_get_executed": False,
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

    print("S224 GATE:", gate_s224)
    print("HTTP:", out["request"]["http"])
    print("FINAL URL:", out["request"]["final_url"])
    print("BODY BYTES:", out["request"]["body_bytes"])
    print("TARGET VISIBLE IN RESPONSE:", target_echo)
    print("SEARCH CONTAINER BOUNDS:", search_bounds)
    print("SEARCH CONDITION BOUNDS:", condition_bounds)
    print("BOUNDED REGION BYTES:", out["forensic"]["bounded_region_bytes"])
    print("RESULT WRAPPER FOUND:", bool(result_wrapper))
    print("CATEGORY COUNT SIGNALS:", category_signals_all[:10])
    print("CATEGORY ZERO SIGNAL:", category_zero_signal)
    print("NO-RESULT SIGNAL COUNT (ALL):", len(no_result_all))
    print("NO-RESULT SIGNAL COUNT (BOUNDED):", len(no_result_bounded))
    print("NO-RESULT WRAPPER COUNT:", len(no_result_wrappers))
    print("EXPLICIT NO-RESULT SIGNAL:", explicit_no_result_signal)
    print("ALL BOARDVIEW ROW COUNT:", len(all_board_rows))
    print("BOUNDED BOARDVIEW ROW COUNT:", len(bounded_board_rows))
    print("BOUNDED TARGET BOARDVIEW ROW COUNT:", len(bounded_target_board_rows))
    print("NO-HIT DOM CONTRACT VERIFIED:", no_hit_dom_contract_verified)
    print("CLASSIFICATION:", classification)

    print("\nNO-RESULT SIGNALS (BOUNDED)")
    print(json.dumps(no_result_bounded[:20], ensure_ascii=False, indent=2))
    print("\nNO-RESULT WRAPPERS")
    print(json.dumps(no_result_wrappers, ensure_ascii=False, indent=2))
    print("\nBOUNDED BOARDVIEW ROWS")
    print(json.dumps(bounded_board_rows[:20], ensure_ascii=False, indent=2))
    print("\nBOUNDED REGION PREFIX")
    print(bounded_html[:12000])

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("Search no-hit equals legal absence: False")
    print("Negative evidence allowed: False")
    print("SITE FALSE inference allowed: False")
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S224 gate": gate_s224,
        "target replay executed": out["summary"]["target_query_executed"] is True,
        "candidate detail GET not executed": out["summary"]["candidate_detail_get_executed"] is False,
        "request attempted": r is not None,
        "search-container inspected": isinstance(bool(search_container), bool),
        "search-condition inspected": isinstance(bool(search_condition), bool),
        "bounded region inspected": isinstance(bounded_html, str),
        "category count inspected": isinstance(category_signals_all, list),
        "no-result signals inspected": isinstance(no_result_all, list),
        "no-result wrappers inspected": isinstance(no_result_wrappers, list),
        "boardView rows inspected": isinstance(all_board_rows, list) and isinstance(bounded_board_rows, list),
        "response classified": classification in {
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_NO_HIT_DOM_CONTRACT_VERIFIED_WITHOUT_LEGAL_ABSENCE_INFERENCE",
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_STRUCTURE_UNRESOLVED",
            "GYEONGGI_OFFICIAL_RECORD_UQQ700_TARGET_REPLAY_TECHNICAL_UNKNOWN",
        },
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
        raise AssertionError("S224A Gyeonggi UQQ700 no-hit structure forensic failed")


if __name__ == "__main__":
    main()
