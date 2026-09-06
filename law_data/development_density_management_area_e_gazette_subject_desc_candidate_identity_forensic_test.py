# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221I = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_target_query_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_candidate_identity_forensic.json"

BASE_URL = "https://www.gwanbo.go.kr/"
ENTRY = urljoin(BASE_URL, "main.do")
SEARCH_PAGE = urljoin(BASE_URL, "user/search/searchKeyword.do")
SEARCH_API = urljoin(BASE_URL, "SearchRestApi.jsp")

TARGET = "개발밀도관리구역"
TARGET_QUERY = (
    "(unstored_field_subject:(개발밀도관리구역) OR "
    "unstored_field_desc:(개발밀도관리구역)) "
    "AND keyword_category_order:(@@ORDER_NUM)"
)


def safe_json(response: requests.Response):
    try:
        return response.json(), None
    except Exception as ex:  # diagnostic stage
        return None, f"{type(ex).__name__}: {ex}"


def scalar_fields(obj: Any, prefix: str = ""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            rows.extend(scalar_fields(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            rows.extend(scalar_fields(v, f"{prefix}[{i}]"))
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        rows.append((prefix, "" if obj is None else str(obj)))
    return rows


def candidate_identity_fields(item: dict[str, Any]):
    keys = (
        "stored_field_subject",
        "keyword_field_subject",
        "stored_field_desc",
        "keyword_field_desc",
        "stored_organ_nm",
        "organ_nm",
        "stored_category_nm",
        "keyword_category_name",
        "category_name",
        "category_order",
        "reg_date",
        "date",
        "ebook_num",
        "page_num",
        "url",
        "link",
        "detail_url",
        "file_url",
        "file_name",
        "file_size",
        "doc_id",
        "document_id",
        "idx",
        "id",
        "title",
    )
    return {k: item.get(k) for k in keys if k in item}


def main():
    print("=" * 78)
    print("E-GAZETTE SUBJECT+DESC CANDIDATE IDENTITY FORENSIC - S221J")
    print("=" * 78)
    print("Target:", TARGET)
    print("Purpose: recover the single S221I notice candidate identity")
    print("Search result != official designation identity")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution before forensic: UNKNOWN")

    s221i = json.loads(S221I.read_text(encoding="utf-8"))
    summary_i = s221i.get("summary") or {}
    gate_i = (
        s221i.get("classification") == "TARGET_HIT"
        and s221i.get("category_total_count_sum") == 1
        and summary_i.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_i.get("legal_absence_inference_allowed") is False
        and s221i.get("official_designation_identity_verified") is False
    )
    if not gate_i:
        raise AssertionError("S221J prerequisite S221I gate not satisfied")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Requested-With": "XMLHttpRequest",
    })

    entry = session.get(ENTRY, timeout=60, allow_redirects=True)
    search_page = session.get(SEARCH_PAGE, timeout=60, allow_redirects=True, headers={"Referer": str(entry.url)})

    payload = {
        "mode": "keyword",
        "index": "gwanbo",
        "query": TARGET_QUERY,
        "pQuery_tmp": TARGET,
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
    data_value = parsed.get("data") if isinstance(parsed, dict) else None
    categories = data_value if isinstance(data_value, list) else []

    response_contract_signal = bool(api_http == 200 and isinstance(parsed, dict) and isinstance(data_value, list))

    nonzero_categories = []
    raw_candidates = []
    total_count = 0

    for category_index, category in enumerate(categories):
        if not isinstance(category, dict):
            continue
        try:
            count = int(category.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        total_count += max(count, 0)
        items = category.get("list") if isinstance(category.get("list"), list) else []
        if count > 0 or items:
            nonzero_categories.append({
                "category_index": category_index,
                "category_name": category.get("category_name"),
                "category_order": category.get("category_order"),
                "count": count,
                "returned_item_count": len(items),
                "page_list": category.get("pageList"),
            })
        for item_index, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            scalar = scalar_fields(item)
            raw_candidates.append({
                "category_index": category_index,
                "category_name": category.get("category_name"),
                "category_order": category.get("category_order"),
                "category_count": count,
                "item_index": item_index,
                "identity_fields": candidate_identity_fields(item),
                "target_visible_paths": [(p, v) for p, v in scalar if TARGET in v],
                "all_scalar_fields": scalar,
                "raw_item": item,
            })

    candidate_count = len(raw_candidates)
    identity_signal_count = 0
    for row in raw_candidates:
        fields = row["identity_fields"]
        strong_values = [
            fields.get("stored_field_subject"),
            fields.get("keyword_field_subject"),
            fields.get("stored_organ_nm"),
            fields.get("organ_nm"),
            fields.get("reg_date"),
            fields.get("ebook_num"),
            fields.get("page_num"),
            fields.get("url"),
            fields.get("link"),
            fields.get("detail_url"),
            fields.get("doc_id"),
            fields.get("document_id"),
            fields.get("id"),
        ]
        if any(v not in (None, "") for v in strong_values):
            identity_signal_count += 1

    if not response_contract_signal:
        classification = "TECHNICAL_UNKNOWN"
    elif candidate_count == 0:
        classification = "CANDIDATE_IDENTITY_INCOMPLETE"
    elif identity_signal_count > 0:
        classification = "CANDIDATE_IDENTITY_RECOVERED"
    else:
        classification = "CANDIDATE_IDENTITY_INCOMPLETE"

    semantic = {
        "CANDIDATE_IDENTITY_RECOVERED": "E_GAZETTE_SUBJECT_DESC_CANDIDATE_IDENTITY_RECOVERED_DISCOVERY_ONLY",
        "CANDIDATE_IDENTITY_INCOMPLETE": "E_GAZETTE_SUBJECT_DESC_CANDIDATE_IDENTITY_INCOMPLETE_WITHOUT_LEGAL_PROMOTION",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_SUBJECT_DESC_CANDIDATE_IDENTITY_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "CANDIDATE_IDENTITY_RECOVERED":
        next_action = "BUILD_S221K_CANDIDATE_DETAIL_OR_DOCUMENT_ENDPOINT_QUALIFICATION_WITHOUT_LEGAL_PROMOTION"
    elif classification == "CANDIDATE_IDENTITY_INCOMPLETE":
        next_action = "INSPECT_E_GAZETTE_RESULT_RENDERER_AND_DETAIL_LINK_CONSTRUCTION_FOR_CANDIDATE_IDENTITY"
    else:
        next_action = "RECHECK_E_GAZETTE_CANDIDATE_FORENSIC_TRANSPORT_BEFORE_ANY_INTERPRETATION"

    out = {
        "step": "STEP 17-21-C-16-8-T-126-S221J",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221i": str(S221I),
        "entry": {"http": entry.status_code, "final_url": str(entry.url)},
        "search_page": {"http": search_page.status_code, "final_url": str(search_page.url)},
        "search_api": {
            "url": SEARCH_API,
            "method": "POST",
            "payload": payload,
            "http": api_http,
            "content_type": content_type,
            "body_bytes": body_bytes,
            "transport_error": transport_error,
            "json_error": json_error,
            "data_is_list": isinstance(data_value, list),
        },
        "classification": classification,
        "nonzero_categories": nonzero_categories,
        "category_total_count_sum": total_count,
        "raw_candidate_count": candidate_count,
        "identity_signal_count": identity_signal_count,
        "raw_candidates": raw_candidates,
        "summary": {
            "response_contract_signal": response_contract_signal,
            "candidate_identity_recovered": classification == "CANDIDATE_IDENTITY_RECOVERED",
            "candidate_identity_incomplete": classification == "CANDIDATE_IDENTITY_INCOMPLETE",
            "technical_unknown": classification == "TECHNICAL_UNKNOWN",
            "semantic_state": semantic,
            "next_action": next_action,
            "search_result_equals_designation_identity": False,
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
    print("SEARCH API HTTP:", api_http)
    print("SEARCH API CONTENT-TYPE:", content_type)
    print("SEARCH API BODY BYTES:", body_bytes)
    print("TRANSPORT ERROR:", transport_error)
    print("JSON PARSE ERROR:", json_error)
    print("DATA IS LIST:", isinstance(data_value, list))
    print("NONZERO CATEGORY COUNT:", len(nonzero_categories))
    print("CATEGORY TOTAL COUNT SUM:", total_count)
    print("RAW CANDIDATE COUNT:", candidate_count)
    print("IDENTITY SIGNAL COUNT:", identity_signal_count)
    print("CLASSIFICATION:", classification)

    print("\nNONZERO CATEGORIES")
    for row in nonzero_categories:
        print(json.dumps(row, ensure_ascii=False, indent=2))

    print("\nRAW CANDIDATES")
    for i, row in enumerate(raw_candidates, 1):
        print(f"--- candidate {i:02d} ---")
        print("CATEGORY:", row["category_name"], row["category_order"], "count=", row["category_count"])
        print("ITEM INDEX:", row["item_index"])
        print("IDENTITY FIELDS:")
        print(json.dumps(row["identity_fields"], ensure_ascii=False, indent=2))
        print("TARGET VISIBLE PATHS:")
        print(json.dumps(row["target_visible_paths"], ensure_ascii=False, indent=2))
        print("ALL SCALAR FIELDS:")
        print(json.dumps(row["all_scalar_fields"], ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221I target-hit safe gate": gate_i,
        "entry GET 200": entry.status_code == 200,
        "search page GET 200": search_page.status_code == 200,
        "response classified": classification in {"CANDIDATE_IDENTITY_RECOVERED", "CANDIDATE_IDENTITY_INCOMPLETE", "TECHNICAL_UNKNOWN"},
        "search result not designation identity": out["summary"]["search_result_equals_designation_identity"] is False,
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
        raise AssertionError("S221J e-gazette subjectDesc candidate identity forensic failed")


if __name__ == "__main__":
    main()
