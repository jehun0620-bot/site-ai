# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_JS5 = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_ajax_getlist_generic_contract_replay.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_ajax_uqq700_bounded_target_search.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENDPOINT = "https://www.gg.go.kr/ajax/board/getList.do"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
HOST = "www.gg.go.kr"
TIMEOUT = 20
PAGE_LIMIT = 50
MAX_PAGES = 5
QUERIES = [
    ("EXACT", "개발밀도관리구역"),
    ("VARIANT", "개발밀도 관리구역"),
    ("WEAK", "개발밀도"),
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def to_int(v):
    try:
        return int(v)
    except Exception:
        return None


def post(session: requests.Session, payload: dict):
    try:
        return session.post(ENDPOINT, data=payload, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def compact_text(item) -> str:
    return json.dumps(item, ensure_ascii=False, sort_keys=True).replace(" ", "")


def item_identity(item):
    if not isinstance(item, dict):
        return str(item)[:200]
    parts = []
    for key in ["bIdx", "bcIdx", "idx", "seq", "title", "subject", "pstTtl"]:
        if item.get(key) not in (None, ""):
            parts.append(f"{key}={item.get(key)}")
    return "|".join(parts) or json.dumps(item, ensure_ascii=False, sort_keys=True)[:800]


def build_base(js5: dict):
    p = dict(js5.get("base_payload") or {})
    p.update({
        "bsIdx": p.get("bsIdx") or "769",
        "bcIdx": p.get("bcIdx") or "0",
        "menuId": p.get("menuId") or "1786",
        "isManager": p.get("isManager") or "false",
        "isCharge": p.get("isCharge") or "false",
        "sdate": "",
        "edate": "",
        "ck00": "1",
        "offset": "0",
        "limit": str(PAGE_LIMIT),
    })
    for i in range(1, 12):
        p[f"ck{i:02d}"] = ""
    return p


def matches(kind: str, text: str):
    if kind == "WEAK":
        return "개발밀도" in text
    return "개발밀도관리구역" in text


def scan_query(session, base, kind, query):
    first_payload = dict(base)
    first_payload["keyword"] = query
    first = post(session, first_payload)
    result = {
        "query_kind": kind,
        "query": query,
        "http": None if first is None else first.status_code,
        "total": None,
        "request_count": 0,
        "scanned_item_count": 0,
        "verified_result_row_hit_count": 0,
        "technical_unknown": False,
        "bounded_exhaustive": False,
        "hit_rows": [],
    }
    if first is None or first.status_code != 200:
        result["technical_unknown"] = True
        result["status"] = f"{kind}_TECHNICAL_UNKNOWN"
        return result
    try:
        first_data = first.json()
    except Exception:
        result["technical_unknown"] = True
        result["status"] = f"{kind}_TECHNICAL_UNKNOWN"
        return result
    if not isinstance(first_data, dict) or not isinstance(first_data.get("items"), list):
        result["technical_unknown"] = True
        result["status"] = f"{kind}_TECHNICAL_UNKNOWN"
        return result

    total = to_int(first_data.get("total"))
    if total is None:
        result["technical_unknown"] = True
        result["status"] = f"{kind}_TECHNICAL_UNKNOWN"
        return result
    result["total"] = total

    pages = 1 if total == 0 else min(MAX_PAGES, (total + PAGE_LIMIT - 1) // PAGE_LIMIT)
    seen = set()
    for page in range(pages):
        if page == 0:
            data = first_data
        else:
            payload = dict(base)
            payload["keyword"] = query
            payload["offset"] = str(page * PAGE_LIMIT)
            r = post(session, payload)
            if r is None or r.status_code != 200:
                result["technical_unknown"] = True
                break
            try:
                data = r.json()
            except Exception:
                result["technical_unknown"] = True
                break
            if not isinstance(data, dict) or not isinstance(data.get("items"), list):
                result["technical_unknown"] = True
                break

        result["request_count"] += 1
        items = data.get("items") or []
        result["scanned_item_count"] += len(items)
        for item in items:
            ident = item_identity(item)
            if ident in seen:
                continue
            seen.add(ident)
            text = compact_text(item)
            if matches(kind, text):
                result["hit_rows"].append({"identity": ident, "item": item})

    result["verified_result_row_hit_count"] = len(result["hit_rows"])
    result["bounded_exhaustive"] = total <= PAGE_LIMIT * MAX_PAGES and not result["technical_unknown"]

    if result["technical_unknown"]:
        result["status"] = f"{kind}_TECHNICAL_UNKNOWN"
    elif result["verified_result_row_hit_count"] > 0:
        result["status"] = f"{kind}_VERIFIED_RESULT_ROW_HIT"
    elif total == 0 or result["bounded_exhaustive"]:
        result["status"] = f"{kind}_NO_VERIFIED_RESULT_HIT"
    else:
        result["technical_unknown"] = True
        result["status"] = f"{kind}_BOUNDED_SCAN_NONEXHAUSTIVE_TECHNICAL_UNKNOWN"
    return result


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD AJAX UQQ700 BOUNDED TARGET SEARCH")
    print("=" * 78)
    print("Search hit != designation/current validity/site inclusion")
    print("No-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    js5 = load_json(IN_JS5)
    assert js5.get("contract_qualified") is True
    assert js5.get("classification") == "GYEONGGI_GAZETTE_BOARD_AJAX_GETLIST_GENERIC_CONTRACT_QUALIFIED"

    session = requests.Session()
    base = build_base(js5)
    results = [scan_query(session, base, kind, query) for kind, query in QUERIES]

    hit_count = sum(r["verified_result_row_hit_count"] for r in results)
    exact_variant_hits = sum(r["verified_result_row_hit_count"] for r in results if r["query_kind"] != "WEAK")
    weak_hits = sum(r["verified_result_row_hit_count"] for r in results if r["query_kind"] == "WEAK")
    technical_unknown_count = sum(1 for r in results if r["technical_unknown"])

    if exact_variant_hits:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_EXACT_OR_VARIANT_RESULT_ROW_HIT"
        semantic = "EXACT_OR_VARIANT_TARGET_ROWS_WERE_VERIFIED_IN_THE_QUALIFIED_BOARD_SEARCH"
        next_action = "VALIDATE_ONLY_THE_HIT_ROWS_FOR_ACTUAL_GAZETTE_DOCUMENT_AND_NOTICE_IDENTITY"
    elif weak_hits:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_WEAK_RESULT_ROW_HIT_ONLY"
        semantic = "ONLY_WEAK_DEVELOPMENT_DENSITY_CONTEXT_ROWS_WERE_VERIFIED"
        next_action = "REVIEW_ONLY_THE_WEAK_HIT_ROWS_FOR_PLAUSIBLE_NOTICE_IDENTITY"
    elif technical_unknown_count:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_BOUNDED_QUERIES_REMAIN_TECHNICALLY_UNRESOLVED"
        next_action = "HARDEN_ONLY_THE_UNRESOLVED_QUERY_SURFACE_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_UQQ700_BOUNDED_SEARCH_NO_VERIFIED_TARGET_RESULT"
        semantic = "NO_VERIFIED_EXACT_VARIANT_OR_WEAK_TARGET_RESULT_ROW_WAS_FOUND_IN_THE_BOUNDED_QUERIES"
        next_action = "TERMINALLY_RECONCILE_THE_GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_WITH_S230G"

    out = {
        "step": "STEP 17-S230H-TARGET",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "endpoint": ENDPOINT,
        "method": "POST",
        "js5_loaded": True,
        "uqq700_target_search_executed": True,
        "query_count": 3,
        "results": results,
        "verified_result_row_hit_count": hit_count,
        "exact_variant_hit_count": exact_variant_hits,
        "weak_hit_count": weak_hits,
        "technical_unknown_query_count": technical_unknown_count,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_hit_equals_designation": False,
            "no_hit_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 78)
    print("BOUNDED TARGET SEARCH")
    print("=" * 78)
    for r in results:
        print("TARGET_QUERY:", json.dumps({k: r.get(k) for k in [
            "query_kind", "query", "http", "total", "request_count", "scanned_item_count",
            "verified_result_row_hit_count", "bounded_exhaustive", "technical_unknown", "status"
        ]}, ensure_ascii=False))
        for hit in r.get("hit_rows", [])[:20]:
            print("HIT_ROW:", json.dumps({"query_kind": r["query_kind"], **hit}, ensure_ascii=False))

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print("TARGET QUERY COUNT: 3")
    print(f"VERIFIED RESULT ROW HIT COUNT: {hit_count}")
    print(f"EXACT/VARIANT HIT COUNT: {exact_variant_hits}")
    print(f"WEAK HIT COUNT: {weak_hits}")
    print(f"TECHNICAL UNKNOWN QUERY COUNT: {technical_unknown_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Search hit == designation identity: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "JS5 loaded": out["js5_loaded"] is True,
        "qualified endpoint fixed": out["endpoint"] == ENDPOINT and out["method"] == "POST",
        "endpoint host gg": urlparse(ENDPOINT).hostname == HOST,
        "target query executed": out["uqq700_target_search_executed"] is True,
        "target queries exactly three": out["query_count"] == 3,
        "search hit not designation": out["summary"]["search_hit_equals_designation"] is False,
        "no hit not legal absence": out["summary"]["no_hit_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("Gyeonggi board bounded target search validation failed")


if __name__ == "__main__":
    main()
