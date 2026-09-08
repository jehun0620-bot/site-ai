# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
IN_JS3 = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_searchfields_paginglist_contract_recovery.json"
IN_JS4 = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_paginglist_definition_source_qualification.json"
OUT = OUT_DIR / "development_density_management_area_gyeonggi_gazette_board_ajax_getlist_generic_contract_replay.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
ENTRY = "https://www.gg.go.kr/bbs/board.do?bsIdx=769&menuId=1786"
ENDPOINT = "https://www.gg.go.kr/ajax/board/getList.do"
HOST = "www.gg.go.kr"
TIMEOUT = 20
GENERIC_TERMS = ["경기도보", "고시"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
    "Referer": ENTRY,
    "X-Requested-With": "XMLHttpRequest",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def get(session: requests.Session, url: str):
    try:
        return session.get(url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def post(session: requests.Session, url: str, data: dict):
    try:
        return session.post(url, data=data, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
    except requests.RequestException:
        return None


def parse_json_response(resp):
    if resp is None:
        return None, "REQUEST_FAILED"
    try:
        return resp.json(), None
    except Exception as exc:
        return None, f"JSON_PARSE_FAILED:{type(exc).__name__}"


def extract_hidden(soup: BeautifulSoup, name: str, default=""):
    tag = soup.find(attrs={"id": name}) or soup.find(attrs={"name": name})
    if not tag:
        return default
    return tag.get("value", default) or default


def extract_board_user_flags(html: str):
    # board-list-dobo.js initializes params from BoardUser booleans. Public browsing
    # normally resolves false/false; preserve literal evidence when present.
    is_manager = False
    is_charge = False
    m = re.search(r"BoardUser\s*=\s*\{([^}]{0,1000})\}", html, re.I | re.S)
    if m:
        body = m.group(1)
        mm = re.search(r"isManager\s*:\s*(true|false)", body, re.I)
        mc = re.search(r"isCharge\s*:\s*(true|false)", body, re.I)
        if mm:
            is_manager = mm.group(1).lower() == "true"
        if mc:
            is_charge = mc.group(1).lower() == "true"
    return is_manager, is_charge


def fetch_script(session: requests.Session, soup: BeautifulSoup, needle: str):
    for script in soup.find_all("script", src=True):
        src = urljoin(ENTRY, script.get("src"))
        if needle not in src:
            continue
        r = get(session, src)
        if r is not None and r.status_code == 200:
            return src, r.text
    return None, ""


def infer_list_length(ajax_js: str, board_js: str):
    candidates = []
    # Common constructor/default forms in minified and non-minified builds.
    patterns = [
        r"listLength\s*=\s*(\d{1,3})",
        r"listLength\s*:\s*(\d{1,3})",
        r"this\.listLength\s*=\s*(\d{1,3})",
        r"listLength[^\d]{0,40}(\d{1,3})",
    ]
    for text, source in [(ajax_js, "ajax-paging-list"), (board_js, "board-list-dobo")]:
        for pat in patterns:
            for m in re.finditer(pat, text, re.I):
                val = int(m.group(1))
                if 1 <= val <= 100:
                    candidates.append({"value": val, "source": source, "pattern": pat})
    if candidates:
        # Prefer the most frequent discovered value; tie -> first encountered.
        counts = {}
        for c in candidates:
            counts[c["value"]] = counts.get(c["value"], 0) + 1
        chosen = sorted(counts, key=lambda v: (-counts[v], candidates.index(next(c for c in candidates if c["value"] == v))))[0]
        return chosen, candidates
    return 10, []


def item_identity(item):
    if not isinstance(item, dict):
        return f"scalar:{norm(str(item))[:200]}"
    preferred = ["bIdx", "bcIdx", "bbsIdx", "idx", "seq", "boardIdx", "articleNo", "pstSn", "title", "subject"]
    parts = []
    for key in preferred:
        if key in item and item.get(key) not in (None, ""):
            parts.append(f"{key}={item.get(key)}")
    if parts:
        return "|".join(parts)
    return json.dumps(item, ensure_ascii=False, sort_keys=True)[:1000]


def summarize_payload(payload: dict):
    keys = ["bsIdx", "bcIdx", "menuId", "isManager", "isCharge", "sdate", "edate", "keyword"]
    keys += [f"ck{i:02d}" for i in range(12)]
    keys += ["offset", "limit"]
    return {k: payload.get(k) for k in keys if k in payload}


def run_query(session, base_payload: dict, keyword: str):
    payload = dict(base_payload)
    payload["keyword"] = keyword
    r = post(session, ENDPOINT, payload)
    data, error = parse_json_response(r)
    result = {
        "keyword": keyword,
        "http": None if r is None else r.status_code,
        "content_type": None if r is None else r.headers.get("Content-Type"),
        "json_error": error,
        "payload": summarize_payload(payload),
        "technical_unknown": False,
    }
    if r is None or r.status_code != 200 or data is None or not isinstance(data, dict):
        result.update({
            "total": None,
            "item_count": None,
            "notice_count": None,
            "item_identities": [],
            "schema_ok": False,
            "technical_unknown": True,
        })
        return result

    items = data.get("items")
    notices = data.get("notice")
    total = data.get("total")
    schema_ok = isinstance(items, list) and isinstance(total, (int, float, str))
    identities = [item_identity(x) for x in items] if isinstance(items, list) else []
    result.update({
        "total": total,
        "item_count": len(items) if isinstance(items, list) else None,
        "notice_count": len(notices) if isinstance(notices, list) else (0 if notices is None else None),
        "item_identities": identities,
        "sample_items": items[:5] if isinstance(items, list) else [],
        "schema_ok": schema_ok,
        "technical_unknown": not schema_ok,
    })
    return result


def numeric_total(v):
    try:
        return int(v)
    except Exception:
        return None


def main():
    print("=" * 78)
    print("GYEONGGI GAZETTE BOARD AJAX getList GENERIC CONTRACT REPLAY - S230H-JS5")
    print("=" * 78)
    print("Purpose: replay the recovered browser POST contract with generic positive controls only")
    print("UQQ700 target search: DISABLED")
    print("Endpoint: /ajax/board/getList.do")
    print("Filtering success != designation/current validity/site inclusion")
    print("Filtering failure != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    js3 = load_json(IN_JS3)
    js4 = load_json(IN_JS4)
    assert js3.get("uqq700_target_search_executed") is False
    assert js4.get("uqq700_target_search_executed") is False

    session = requests.Session()
    entry = get(session, ENTRY)
    if entry is None or entry.status_code != 200:
        raise RuntimeError("GG gazette board entry request failed")
    soup = BeautifulSoup(entry.text, "html.parser")

    board_src, board_js = fetch_script(session, soup, "board-list-dobo.js")
    ajax_src, ajax_js = fetch_script(session, soup, "ajax-paging-list.min.js")
    list_length, list_length_evidence = infer_list_length(ajax_js, board_js)

    bs_idx = extract_hidden(soup, "bsIdx", "769") or "769"
    bc_idx = extract_hidden(soup, "bcIdx", "0") or "0"
    menu_id = extract_hidden(soup, "menuId", "1786") or "1786"
    is_manager, is_charge = extract_board_user_flags(entry.text)

    base_payload = {
        "bsIdx": bs_idx,
        "bcIdx": bc_idx,
        "menuId": menu_id,
        "isManager": "true" if is_manager else "false",
        "isCharge": "true" if is_charge else "false",
        "sdate": "",
        "edate": "",
        "keyword": "",
        "ck00": "1",
        "offset": "0",
        "limit": str(list_length),
    }
    for i in range(1, 12):
        base_payload[f"ck{i:02d}"] = ""

    baseline = run_query(session, base_payload, "")
    experiments = [run_query(session, base_payload, term) for term in GENERIC_TERMS]

    baseline_total = numeric_total(baseline.get("total"))
    baseline_ids = set(baseline.get("item_identities") or [])
    all_credible = True
    for e in experiments:
        total = numeric_total(e.get("total"))
        ids = set(e.get("item_identities") or [])
        changed = (total is not None and baseline_total is not None and total != baseline_total) or ids != baseline_ids
        filtered = (
            e.get("http") == 200
            and e.get("schema_ok") is True
            and not e.get("technical_unknown")
            and changed
            and total is not None
            and baseline_total is not None
            and total <= baseline_total
        )
        e["baseline_total"] = baseline_total
        e["total_changed"] = total != baseline_total if total is not None and baseline_total is not None else None
        e["item_identity_changed"] = ids != baseline_ids
        e["credible_filtering"] = filtered
        all_credible = all_credible and filtered

    contract_qualified = (
        baseline.get("http") == 200
        and baseline.get("schema_ok") is True
        and not baseline.get("technical_unknown")
        and len(experiments) == 2
        and all_credible
    )

    if contract_qualified:
        classification = "GYEONGGI_GAZETTE_BOARD_AJAX_GETLIST_GENERIC_CONTRACT_QUALIFIED"
        semantic = "RECOVERED_POST_GETLIST_CONTRACT_RETURNED_VALID_JSON_AND_BOTH_GENERIC_POSITIVE_CONTROLS_CHANGED_FILTERED_RESULT_IDENTITIES"
        next_action = "RUN_ONLY_EXACT_VARIANT_WEAK_UQQ700_BOUNDED_SEARCH_THROUGH_THE_QUALIFIED_AJAX_GETLIST_CONTRACT"
    else:
        classification = "GYEONGGI_GAZETTE_BOARD_AJAX_GETLIST_GENERIC_CONTRACT_TECHNICAL_UNKNOWN"
        semantic = "RECOVERED_POST_GETLIST_REQUEST_DID_NOT_FULLY_PROVE_GENERIC_FILTERING_WITH_VALID_STABLE_JSON_RESULT_SEMANTICS"
        next_action = "HARDEN_ONLY_THE_REMAINING_AJAX_PAYLOAD_OR_LIST_LENGTH_SCHEMA_WITHOUT_UQQ700_QUERY_OR_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-S230H-JS5",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "entry_url": ENTRY,
        "endpoint": ENDPOINT,
        "method": "POST",
        "entry_http": entry.status_code,
        "js3_loaded": True,
        "js4_loaded": True,
        "uqq700_target_search_executed": False,
        "board_script_source": board_src,
        "ajax_paging_script_source": ajax_src,
        "list_length": list_length,
        "list_length_evidence": list_length_evidence,
        "base_payload": summarize_payload(base_payload),
        "baseline": baseline,
        "positive_control_experiments": experiments,
        "generic_positive_control_count": len(experiments),
        "positive_controls_all_credible": all_credible,
        "contract_qualified": contract_qualified,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "search_success_equals_designation": False,
            "search_success_equals_validity": False,
            "search_success_equals_site_inclusion": False,
            "search_failure_equals_legal_absence": False,
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
    print("AJAX CONTRACT REPLAY")
    print("=" * 78)
    print(f"ENTRY HTTP: {entry.status_code}")
    print(f"BOARD SCRIPT RECOVERED: {bool(board_js)}")
    print(f"AJAX PAGING SCRIPT RECOVERED: {bool(ajax_js)}")
    print(f"LIST LENGTH: {list_length}")
    print(f"LIST LENGTH EVIDENCE COUNT: {len(list_length_evidence)}")
    print("BASE PAYLOAD:", json.dumps(summarize_payload(base_payload), ensure_ascii=False))
    print("BASELINE:", json.dumps({k: baseline.get(k) for k in ["http", "content_type", "json_error", "total", "item_count", "notice_count", "schema_ok", "technical_unknown"]}, ensure_ascii=False))
    for e in experiments:
        print("POSITIVE_CONTROL:", json.dumps({k: e.get(k) for k in [
            "keyword", "http", "content_type", "json_error", "baseline_total", "total", "item_count", "notice_count",
            "schema_ok", "total_changed", "item_identity_changed", "credible_filtering", "technical_unknown"
        ]}, ensure_ascii=False))
    print(f"POSITIVE CONTROLS ALL CREDIBLE: {all_credible}")
    print(f"CONTRACT QUALIFIED: {contract_qualified}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("UQQ700 target search executed: False")
    print("No-hit == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "JS3 loaded": out["js3_loaded"] is True,
        "JS4 loaded": out["js4_loaded"] is True,
        "entry host gg": urlparse(ENTRY).hostname == HOST,
        "endpoint host gg": urlparse(ENDPOINT).hostname == HOST,
        "POST endpoint fixed": out["method"] == "POST" and out["endpoint"] == ENDPOINT,
        "no UQQ700 target search": out["uqq700_target_search_executed"] is False,
        "generic controls only": GENERIC_TERMS == ["경기도보", "고시"],
        "generic controls bounded": len(experiments) == 2,
        "search success not designation": out["summary"]["search_success_equals_designation"] is False,
        "search success not validity": out["summary"]["search_success_equals_validity"] is False,
        "search success not site inclusion": out["summary"]["search_success_equals_site_inclusion"] is False,
        "search failure not legal absence": out["summary"]["search_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "GYEONGGI_GAZETTE_BOARD_AJAX_GETLIST_GENERIC_CONTRACT_QUALIFIED",
            "GYEONGGI_GAZETTE_BOARD_AJAX_GETLIST_GENERIC_CONTRACT_TECHNICAL_UNKNOWN",
        },
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
        raise AssertionError("S230H-JS5 validation failed")


if __name__ == "__main__":
    main()
