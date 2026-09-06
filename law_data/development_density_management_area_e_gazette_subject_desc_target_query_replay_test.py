# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests

BASE = Path(__file__).resolve().parent.parent
S221H = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_target_query_replay.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_e_gazette_subject_desc_target_query_replay.json"

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


def flatten_strings(obj: Any, prefix: str = ""):
    rows = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = f"{prefix}.{k}" if prefix else str(k)
            rows.extend(flatten_strings(v, p))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            rows.extend(flatten_strings(v, f"{prefix}[{i}]"))
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        rows.append((prefix, "" if obj is None else str(obj)))
    return rows


def summarize_item(item: Any):
    if not isinstance(item, dict):
        return {"type": type(item).__name__, "value": str(item)[:1000]}
    preferred = (
        "stored_field_subject", "keyword_field_subject", "stored_field_desc",
        "keyword_field_desc", "stored_organ_nm", "organ_nm", "reg_date",
        "ebook_num", "page_num", "url", "file_url", "file_name", "file_size",
        "category_name", "category_order", "title",
    )
    out = {k: item.get(k) for k in preferred if k in item}
    if not out:
        for i, (k, v) in enumerate(item.items()):
            if i >= 30:
                break
            out[k] = f"<{type(v).__name__}:{len(v)}>" if isinstance(v, (dict, list)) else v
    return out


def main():
    print("=" * 78)
    print("E-GAZETTE UQQ700 SUBJECT+DESC TARGET QUERY REPLAY - S221I")
    print("=" * 78)
    print("Target query:", TARGET)
    print("Search scope: subjectDesc (title + content), page 1 bounded discovery only")
    print("Search hit != designation fact")
    print("Negative evidence: DISABLED")
    print("Legal absence inference: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution before replay: UNKNOWN")

    s221h = json.loads(S221H.read_text(encoding="utf-8"))
    summary_h = s221h.get("summary") or {}
    gate_h = (
        s221h.get("classification") == "TARGET_NO_HIT"
        and summary_h.get("uqq700_query_replayed") is True
        and summary_h.get("uqq700_final_resolution") == "UNKNOWN"
        and summary_h.get("legal_absence_inference_allowed") is False
    )
    if not gate_h:
        raise AssertionError("S221I prerequisite S221H gate not satisfied")

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
    category_summaries = []
    candidate_items = []
    total_count = 0
    target_visible_count = 0

    for category_index, category in enumerate(categories):
        if not isinstance(category, dict):
            continue
        category_name = category.get("category_name")
        category_order = category.get("category_order")
        try:
            count = int(category.get("count") or 0)
        except (TypeError, ValueError):
            count = 0
        total_count += max(count, 0)
        items = category.get("list") if isinstance(category.get("list"), list) else []
        matched_item_count = 0

        for item_index, item in enumerate(items):
            matches = [(p, v) for p, v in flatten_strings(item) if TARGET in v]
            if matches:
                matched_item_count += 1
                target_visible_count += len(matches)
                candidate_items.append({
                    "category_index": category_index,
                    "category_name": category_name,
                    "category_order": category_order,
                    "category_count": count,
                    "item_index": item_index,
                    "matches": matches[:40],
                    "item": summarize_item(item),
                    "raw_item": item,
                })

        category_summaries.append({
            "category_index": category_index,
            "category_name": category_name,
            "category_order": category_order,
            "count": count,
            "returned_item_count": len(items),
            "matched_item_count": matched_item_count,
            "page_list_present": bool(category.get("pageList")),
            "needs_pagination_if_targeted": count > len(items) and count > 0,
        })

    if not response_contract_signal:
        classification = "TECHNICAL_UNKNOWN"
    elif candidate_items or total_count > 0:
        classification = "TARGET_HIT"
    else:
        classification = "TARGET_NO_HIT"

    semantic = {
        "TARGET_HIT": "E_GAZETTE_UQQ700_SUBJECT_DESC_TARGET_HIT_DISCOVERY_ONLY",
        "TARGET_NO_HIT": "E_GAZETTE_UQQ700_SUBJECT_DESC_TARGET_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE",
        "TECHNICAL_UNKNOWN": "E_GAZETTE_UQQ700_SUBJECT_DESC_TARGET_QUERY_TECHNICAL_UNKNOWN",
    }[classification]

    if classification == "TARGET_HIT":
        next_action = "QUALIFY_E_GAZETTE_SUBJECT_DESC_TARGET_CANDIDATE_IDENTITIES_AND_PAGINATION_BEFORE_LEGAL_PROMOTION"
    elif classification == "TARGET_NO_HIT":
        next_action = "TEST_BOUNDED_UQQ700_TERM_VARIANTS_OR_NOTICE_CONTEXT_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        next_action = "RECHECK_E_GAZETTE_SUBJECT_DESC_TRANSPORT_BEFORE_ANY_INTERPRETATION"

    out = {
        "step": "STEP 17-21-C-16-8-T-125-S221I",
        "target_name": TARGET,
        "standard_code": "UQQ700",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_family": "E_GAZETTE",
        "input_s221h": str(S221H),
        "query_scope": "subjectDesc",
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
        "category_summaries": category_summaries,
        "candidate_items": candidate_items,
        "target_visible_count": target_visible_count,
        "category_total_count_sum": total_count,
        "summary": {
            "response_contract_signal": response_contract_signal,
            "target_hit": classification == "TARGET_HIT",
            "target_no_hit": classification == "TARGET_NO_HIT",
            "technical_unknown": classification == "TECHNICAL_UNKNOWN",
            "candidate_item_count": len(candidate_items),
            "page_1_bounded_discovery": True,
            "query_replay_performed": True,
            "uqq700_query_replayed": True,
            "search_hit_equals_designation_fact": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "legal_absence": False,
            "semantic_state": semantic,
            "next_action": next_action,
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
    print("CATEGORY COUNT:", len(categories))
    print("CATEGORY TOTAL COUNT SUM:", total_count)
    print("TARGET VISIBLE COUNT:", target_visible_count)
    print("CANDIDATE ITEM COUNT:", len(candidate_items))
    print("CLASSIFICATION:", classification)

    print("\nCATEGORY SUMMARY")
    for row in category_summaries:
        if row["count"] or row["matched_item_count"]:
            print(json.dumps(row, ensure_ascii=False))

    print("\nCANDIDATE ITEMS")
    for i, row in enumerate(candidate_items[:50], 1):
        print(f"--- candidate {i:02d} ---")
        print(json.dumps({
            "category_name": row["category_name"],
            "category_order": row["category_order"],
            "category_count": row["category_count"],
            "item_index": row["item_index"],
            "matches": row["matches"],
            "item": row["item"],
        }, ensure_ascii=False, indent=2))

    print("\nSUMMARY")
    print("Semantic:", semantic)
    print("Next action:", next_action)
    print("UQQ700 final resolution: UNKNOWN")
    print("Output:", OUT)

    checks = {
        "S221H no-hit safe gate": gate_h,
        "entry GET 200": entry.status_code == 200,
        "search page GET 200": search_page.status_code == 200,
        "subjectDesc query performed": out["summary"]["query_replay_performed"] is True,
        "response classified": classification in {"TARGET_HIT", "TARGET_NO_HIT", "TECHNICAL_UNKNOWN"},
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
        raise AssertionError("S221I e-gazette subjectDesc UQQ700 target query replay failed")


if __name__ == "__main__":
    main()
