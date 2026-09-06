# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221F = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_live_keyword_submit_js_contract_forensic.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_search_rest_api_positive_control_replay.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH_PAGE = urljoin(BASE_URL, "user/search/searchKeyword.do")
SEARCH_API = urljoin(BASE_URL, "SearchRestApi.jsp")
INSERT_KEYWORD = urljoin(BASE_URL, "user/search/insertKeyword.do")

TARGET = "개발밀도관리구역"
POSITIVE_CONTROL = "성남시"
POSITIVE_QUERY = "(unstored_field_subject:(성남시)) AND keyword_category_order:(@@ORDER_NUM)"


def safe_json(response: requests.Response):
    try:
        return response.json(), None
    except Exception as ex:  # noqa: BLE001 - diagnostic stage
        return None, f"{type(ex).__name__}: {ex}"


def flatten_strings(obj: Any, prefix: str = ""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            rows.extend(flatten_strings(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            p = f"{prefix}[{i}]"
            rows.extend(flatten_strings(v, p))
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        rows.append((prefix, "" if obj is None else str(obj)))
    return rows


def summarize_record(record: Any, max_fields: int = 30):
    if not isinstance(record, dict):
        return {"type": type(record).__name__, "value": str(record)[:1000]}
    out = {}
    for i, (k, v) in enumerate(record.items()):
        if i >= max_fields:
            break
        if isinstance(v, (dict, list)):
            out[k] = f"<{type(v).__name__}:{len(v)}>"
        else:
            out[k] = v
    return out


def main():
    print("=" * 78)
    print("E-GAZETTE SearchRestApi POSITIVE CONTROL REPLAY - S221G")
    print("=" * 78)
    print("Positive control:", POSITIVE_CONTROL)
    print("Target UQQ700 query is NOT replayed")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    s221f = json.loads(S221F.read_text(encoding="utf-8"))
    contract = s221f.get("contract") or {}
    summary_f = s221f.get("summary") or {}
    gate_contract = bool(contract.get("contract_recovered"))
    gate_semantic = summary_f.get("semantic_state") == "E_GAZETTE_LIVE_KEYWORD_SUBMIT_JS_CONTRACT_RECOVERED"
    gate_safe = summary_f.get("uqq700_final_resolution") == "UNKNOWN" and summary_f.get("uqq700_query_replayed") is False
    if not (gate_contract and gate_semantic and gate_safe):
        raise AssertionError("S221G prerequisite gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
    })

    entry = session.get(ENTRY, timeout=60, allow_redirects=True)
    search_page = session.get(SEARCH_PAGE, timeout=60, allow_redirects=True, headers={"Referer": str(entry.url)})

    insert_http = None
    insert_error = None
    try:
        insert_resp = session.post(
            INSERT_KEYWORD,
            data={"keyword": POSITIVE_CONTROL, "page_gubun": "2"},
            timeout=30,
            headers={"Referer": str(search_page.url)},
        )
        insert_http = insert_resp.status_code
    except requests.RequestException as ex:
        insert_error = f"{type(ex).__name__}: {ex}"

    payload = {
        "mode": "keyword",
        "index": "gwanbo",
        "query": POSITIVE_QUERY,
        "pQuery_tmp": POSITIVE_CONTROL,
        "pageNo": "1",
        "listSize": "5",
        "sort": "",
    }

    try:
        resp = session.post(
            SEARCH_API,
            data=payload,
            timeout=60,
            headers={
                "Referer": str(search_page.url),
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            },
        )
        transport_error = None
    except requests.RequestException as ex:
        resp = None
        transport_error = f"{type(ex).__name__}: {ex}"

    api_http = resp.status_code if resp is not None else None
    content_type = resp.headers.get("Content-Type", "") if resp is not None else ""
    body_bytes = len(resp.content) if resp is not None else 0
    parsed, json_error = safe_json(resp) if resp is not None else (None, None)

    top_keys = list(parsed.keys()) if isinstance(parsed, dict) else []
    data_value = parsed.get("data") if isinstance(parsed, dict) else None
    data_list = data_value if isinstance(data_value, list) else []

    flattened = flatten_strings(parsed) if parsed is not None else []
    pc_paths = [(p, v) for p, v in flattened if POSITIVE_CONTROL in v]
    positive_visible_count = len(pc_paths)

    total_like = []
    if isinstance(parsed, dict):
        for k, v in parsed.items():
            if any(token in k.lower() for token in ("total", "count", "size", "num")):
                total_like.append({"key": k, "value": v})

    record_matches = []
    for idx, row in enumerate(data_list):
        flat = flatten_strings(row)
        matches = [(p, v) for p, v in flat if POSITIVE_CONTROL in v]
        if matches:
            record_matches.append({
                "index": idx,
                "matches": matches[:20],
                "record": summarize_record(row),
            })

    result_identity_signal = len(record_matches) > 0
    response_contract_signal = bool(api_http == 200 and parsed is not None and isinstance(parsed, dict) and isinstance(data_value, list))
    positive_control_replay_qualified = bool(response_contract_signal and result_identity_signal)

    semantic = (
        "E_GAZETTE_SEARCH_REST_API_POSITIVE_CONTROL_QUALIFIED"
        if positive_control_replay_qualified
        else "E_GAZETTE_SEARCH_REST_API_POSITIVE_CONTROL_UNRESOLVED"
    )
    next_action = (
        "BUILD_S221H_TARGET_QUERY_REPLAY_WITHOUT_DESIGNATION_OR_SITE_PROMOTION"
        if positive_control_replay_qualified
        else "INSPECT_SEARCH_REST_API_RESPONSE_SCHEMA_AND_QUERY_SEMANTICS_BEFORE_TARGET_QUERY"
    )

    out = {
        "step": "STEP 17-21-C-16-8-T-123-S221G",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "positive_control": POSITIVE_CONTROL,
        "positive_query": POSITIVE_QUERY,
        "input_s221f": str(S221F),
        "entry": {"http": entry.status_code, "final_url": str(entry.url)},
        "search_page": {"http": search_page.status_code, "final_url": str(search_page.url)},
        "insert_keyword": {"http": insert_http, "error": insert_error, "qualification_gate": False},
        "search_api": {
            "url": SEARCH_API,
            "method": "POST",
            "payload": payload,
            "http": api_http,
            "content_type": content_type,
            "body_bytes": body_bytes,
            "transport_error": transport_error,
            "json_error": json_error,
            "top_level_type": type(parsed).__name__ if parsed is not None else None,
            "top_level_keys": top_keys,
            "data_is_list": isinstance(data_value, list),
            "data_count": len(data_list),
            "total_like": total_like,
            "positive_control_visible_count": positive_visible_count,
            "positive_control_paths": pc_paths[:100],
            "record_matches": record_matches[:20],
            "record_samples": [summarize_record(r) for r in data_list[:5]],
        },
        "summary": {
            "response_contract_signal": response_contract_signal,
            "result_identity_signal_observed": result_identity_signal,
            "positive_control_replay_qualified": positive_control_replay_qualified,
            "semantic_state": semantic,
            "next_action": next_action,
            "positive_control_replay_performed": True,
            "uqq700_query_replayed": False,
            "search_hit_equals_designation_fact": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
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

    print("ENTRY HTTP:", entry.status_code)
    print("SEARCH PAGE HTTP:", search_page.status_code)
    print("INSERT KEYWORD HTTP:", insert_http)
    print("INSERT KEYWORD ERROR:", insert_error)
    print("SEARCH API HTTP:", api_http)
    print("SEARCH API CONTENT-TYPE:", content_type)
    print("SEARCH API BODY BYTES:", body_bytes)
    print("JSON PARSE ERROR:", json_error)
    print("TOP LEVEL TYPE:", type(parsed).__name__ if parsed is not None else None)
    print("TOP LEVEL KEYS:", top_keys)
    print("DATA IS LIST:", isinstance(data_value, list))
    print("DATA COUNT:", len(data_list))
    print("TOTAL-LIKE FIELDS:", total_like)
    print("POSITIVE CONTROL VISIBLE COUNT:", positive_visible_count)
    print("MATCHED RECORD COUNT:", len(record_matches))
    print("Response contract signal:", response_contract_signal)
    print("Result identity signal observed:", result_identity_signal)
    print("Positive control replay qualified:", positive_control_replay_qualified)

    print("\nRECORD SAMPLES")
    for i, row in enumerate(data_list[:5], 1):
        print(f"--- record {i:02d} ---")
        print(json.dumps(summarize_record(row), ensure_ascii=False, indent=2))

    print("\nPOSITIVE CONTROL MATCHES")
    for i, row in enumerate(record_matches[:10], 1):
        print(f"--- matched record {i:02d} / index={row['index']} ---")
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221F contract gate": gate_contract and gate_semantic,
        "entry GET 200": entry.status_code == 200,
        "search page GET 200": search_page.status_code == 200,
        "search API POST 200": api_http == 200,
        "JSON parsed": parsed is not None and json_error is None,
        "response contract signal": response_contract_signal,
        "positive control result identity observed": result_identity_signal,
        "positive control replay qualified": positive_control_replay_qualified,
        "UQQ700 query not replayed": out["summary"]["uqq700_query_replayed"] is False,
        "search hit not designation fact": out["summary"]["search_hit_equals_designation_fact"] is False,
        "negative evidence disabled": not out["summary"]["negative_evidence_allowed"],
        "legal absence inference disabled": not out["summary"]["legal_absence_inference_allowed"],
        "legal absence false": out["summary"]["legal_absence"] is False,
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
        raise AssertionError("S221G e-gazette SearchRestApi positive control replay failed")


if __name__ == "__main__":
    main()
