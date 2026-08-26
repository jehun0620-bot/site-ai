# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-3-S1

Development Density Management Area
Historical Search Contract Semantic Hardening

목표
======================================================================

T-3에서 구조적으로 복원된 search contract 중 historical board search가 아닌
semantic false positive를 제거한다.

대표 false positive
======================================================================

1. 사이트 전체 통합검색
    /RSA/front/Search.jsp
    field = qt

2. 만족도 조사
    /portal/satisfaction/voteSatis.do
    field = researchContent

3. JavaScript submit handler는 field/method가 불완전하면 T-4 실행계약으로
   직접 넘기지 않는다.

핵심 원칙
======================================================================

1. 입력은 T-3 recovered contract만 사용한다.
2. actual form action/field 복원 결과를 재분류한다.
3. source endpoint role과 action identity가 historical board search와 호환되어야 한다.
4. global search / satisfaction / login / contact / newsletter form은 제외한다.
5. 게시판 자체 action 또는 동일 board endpoint POST를 우선한다.
6. field name/title/hidden params가 board-local search 구조를 보여야 한다.
7. JS-only contract는 executable contract로 자동 승격하지 않는다.
8. 이 단계는 target query를 실행하지 않는다.
9. query 문자열은 evidence가 아니다.
10. SITE TRUE/FALSE 자동판정 금지.
11. runtime registration 금지.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import urlparse


BASE_DIR = Path(__file__).resolve().parent.parent

T3_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_historical_search_form_action_recovery.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_historical_search_contract_semantic_hardening.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

CLASS_QUALIFIED_BOARD_FORM = "QUALIFIED_HISTORICAL_BOARD_SEARCH_CONTRACT"
CLASS_REJECTED_GLOBAL_SEARCH = "REJECTED_GLOBAL_SITE_SEARCH_CONTRACT"
CLASS_REJECTED_SATISFACTION = "REJECTED_SATISFACTION_FORM_CONTRACT"
CLASS_REJECTED_GENERIC = "REJECTED_GENERIC_NON_BOARD_FORM_CONTRACT"
CLASS_REJECTED_JS_ONLY = "REJECTED_JS_ONLY_INCOMPLETE_CONTRACT"
CLASS_REJECTED_WEAK_BOARD = "REJECTED_WEAK_BOARD_SEARCH_IDENTITY"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_CONTRACT"

VALID_CLASSES = {
    CLASS_QUALIFIED_BOARD_FORM,
    CLASS_REJECTED_GLOBAL_SEARCH,
    CLASS_REJECTED_SATISFACTION,
    CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_JS_ONLY,
    CLASS_REJECTED_WEAK_BOARD,
    CLASS_REJECTED_INVALID,
}

GLOBAL_SEARCH_PATH_TERMS = [
    "/rsa/front/search.jsp",
    "/search/",
    "/search.do",
    "/totalsearch",
    "/total/search",
]

SATISFACTION_PATH_TERMS = [
    "/satisfaction/",
    "votesatis",
    "researchcontent",
]

GENERIC_NON_BOARD_TERMS = [
    "/login",
    "/member",
    "/contact",
    "/newsletter",
    "/subscribe",
]

BOARD_ACTION_TERMS = [
    "/ntt/index.do",
    "/board/",
    "/bbs/",
    "/notice/",
    "/gosi/",
    "/gonggo/",
    "/nscvrg/",
    "/nscvrgrmrk/",
    "list.do",
]

BOARD_SEARCH_FIELD_NAMES = {
    "searchtxt",
    "srchcontents",
    "searchkeyword",
    "keyword",
    "searchword",
    "srchtext",
    "schtext",
}

BOARD_HIDDEN_PARAM_KEYS = {
    "bbsid",
    "menuid",
    "page",
    "pagenum",
    "bcidx",
    "mid",
}


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def normalized_path_query(url: str) -> str:
    try:
        parsed = urlparse(url)
        return ((parsed.path or "") + "?" + (parsed.query or "")).lower()
    except Exception:
        return ""


def classify_contract(item: Dict[str, Any]) -> Dict[str, Any]:
    action_url = normalize_space(item.get("action_url"))
    source_urls = item.get("source_urls") or []
    if not isinstance(source_urls, list):
        source_urls = []
    source_url = normalize_space(source_urls[0] if source_urls else "")
    method = normalize_space(item.get("method")).upper()
    classification = normalize_space(item.get("classification"))
    search_field = item.get("search_field") or {}
    hidden_params = item.get("hidden_params") or {}

    if not action_url or not hostname(action_url):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_INVALID,
            "reasons": ["INVALID_ACTION_URL"],
        }

    action_identity = normalized_path_query(action_url)
    source_identity = normalized_path_query(source_url)
    field_name = normalize_space(search_field.get("name")).lower()
    field_title = normalize_space(search_field.get("title")).lower()
    field_placeholder = normalize_space(search_field.get("placeholder")).lower()

    combined = " ".join([
        action_identity,
        source_identity,
        field_name,
        field_title,
        field_placeholder,
    ])

    # 1. explicit global site search
    if any(term in action_identity for term in GLOBAL_SEARCH_PATH_TERMS):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_GLOBAL_SEARCH,
            "reasons": ["GLOBAL_SITE_SEARCH_ACTION"],
        }

    # 2. explicit satisfaction survey
    if (
        any(term in action_identity for term in SATISFACTION_PATH_TERMS)
        or field_name == "researchcontent"
        or "홈페이지 이용" in field_placeholder
    ):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_SATISFACTION,
            "reasons": ["SATISFACTION_FORM_IDENTITY"],
        }

    # 3. JS-only incomplete contract
    if classification == "RECOVERED_HISTORICAL_SEARCH_JS_CONTRACT":
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_JS_ONLY,
            "reasons": ["JS_ONLY_METHOD_OR_FIELD_INCOMPLETE"],
        }

    # 4. generic non-board action
    if any(term in combined for term in GENERIC_NON_BOARD_TERMS):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_GENERIC,
            "reasons": ["GENERIC_NON_BOARD_FORM"],
        }

    board_action = any(term in action_identity for term in BOARD_ACTION_TERMS)
    source_board = any(term in source_identity for term in BOARD_ACTION_TERMS)
    board_field = field_name in BOARD_SEARCH_FIELD_NAMES
    hidden_keys = {normalize_space(key).lower() for key in hidden_params.keys()}
    board_hidden = bool(hidden_keys & BOARD_HIDDEN_PARAM_KEYS)

    reasons: List[str] = []
    score = 0

    if board_action:
        score += 40
        reasons.append("BOARD_ACTION_IDENTITY")

    if source_board:
        score += 20
        reasons.append("BOARD_SOURCE_IDENTITY")

    if board_field:
        score += 30
        reasons.append(f"BOARD_SEARCH_FIELD:{field_name}")

    if board_hidden:
        score += 20
        reasons.append("BOARD_HIDDEN_PARAMETER_IDENTITY")

    if method == "POST":
        score += 5
        reasons.append("BOARD_FORM_POST")

    # Same endpoint action is very strong for legacy board search.
    if source_url and action_url == source_url:
        score += 25
        reasons.append("SOURCE_ACTION_SAME_ENDPOINT")

    # Require actual board-local identity, not just a generic textual field.
    if score < 55 or not (board_action or source_board):
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_WEAK_BOARD,
            "reasons": unique_strings(reasons + [f"BOARD_IDENTITY_SCORE:{score}"]),
        }

    return {
        "qualified": True,
        "classification": CLASS_QUALIFIED_BOARD_FORM,
        "reasons": unique_strings(reasons + [f"BOARD_IDENTITY_SCORE:{score}"]),
    }


def contract_key(item: Dict[str, Any]) -> Tuple[str, str, str, str]:
    return (
        normalize_space(item.get("source_family")),
        normalize_space(item.get("action_url")),
        normalize_space(item.get("method")).upper(),
        normalize_space((item.get("search_field") or {}).get("name")),
    )


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HISTORICAL SEARCH CONTRACT SEMANTIC HARDENING")
    print("=" * 60)
    print()
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Negative evidence allowed:", NEGATIVE_EVIDENCE_ALLOWED)
    print()

    if not T3_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-3 input not found: {T3_INPUT_PATH}")

    data = json.loads(T3_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("T-3 input must be JSON object.")

    raw = data.get("next_stage_search_contract_pool")
    if not isinstance(raw, list):
        raw = []

    print("T-3 recovered contract count:", len(raw))
    print()

    records: List[Dict[str, Any]] = []

    for index, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue

        result = classify_contract(item)
        record = dict(item)
        record["input_index"] = index
        record["qualified"] = result["qualified"]
        record["classification"] = result["classification"]
        record["hardening_reasons"] = result["reasons"]
        record["target_query_executed"] = False
        record["target_document_evidence"] = False
        record["verified_positive"] = False
        record["runtime_registration_allowed"] = False
        record["site_positive_allowed"] = False
        record["site_negative_allowed"] = False
        record["final_positive_promotion_allowed"] = False
        records.append(record)

        print("-" * 60)
        print(f"CONTRACT {index}")
        print("Family:", record.get("source_family"))
        print("Action:", record.get("action_url"))
        print("Method:", record.get("method"))
        print("Field:", (record.get("search_field") or {}).get("name"))
        print("Qualified:", record.get("qualified"))
        print("Resolution:", record.get("classification"))
        print("Reasons:", record.get("hardening_reasons"))

    qualified = [item for item in records if item.get("qualified") is True]
    rejected = [item for item in records if item.get("qualified") is not True]

    canonical: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    duplicate_count = 0
    for item in qualified:
        key = contract_key(item)
        if key in canonical:
            duplicate_count += 1
            existing = canonical[key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["source_urls"] = unique_strings((existing.get("source_urls") or []) + (item.get("source_urls") or []))
            existing["hardening_reasons"] = unique_strings((existing.get("hardening_reasons") or []) + (item.get("hardening_reasons") or []))
            continue
        canonical[key] = dict(item)

    hardened_contracts = list(canonical.values())
    hardened_contracts.sort(key=contract_key)

    next_stage_search_contract_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "classification": item.get("classification"),
            "action_url": item.get("action_url"),
            "method": item.get("method"),
            "search_field": item.get("search_field") or {},
            "hidden_params": item.get("hidden_params") or {},
            "hardening_reasons": item.get("hardening_reasons") or [],
            "contract_only": True,
            "target_query_executed": False,
            "target_document_evidence": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in hardened_contracts
    ]

    classification_counts = Counter(item.get("classification") for item in records)

    if next_stage_search_contract_pool:
        resolution = "HISTORICAL_SEARCH_CONTRACT_SEMANTIC_HARDENING_COMPLETED"
        next_action = (
            "semantic hardening을 통과한 board-local search contract만 T-4 bounded historical search execution으로 넘긴다. "
            "T-4에서는 실제 field/hidden parameters를 사용해 target query를 실행하되, query 자체는 candidate evidence로 사용하지 않는다."
        )
    else:
        resolution = "HISTORICAL_SEARCH_CONTRACT_SEMANTIC_HARDENING_NO_CONTRACT"
        next_action = (
            "실행 가능한 board-local historical search contract가 남지 않았다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며, "
            "notice-number reverse lookup 또는 별도 official archive family로 진행한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-3-S1 Historical Search Contract Semantic Hardening",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t3_path": str(T3_INPUT_PATH),
            "t3_resolution": data.get("resolution"),
        },
        "method": {
            "t3_recovered_contracts_only": True,
            "global_site_search_rejected": True,
            "satisfaction_form_rejected": True,
            "generic_non_board_form_rejected": True,
            "js_only_contract_execution_disabled": True,
            "board_local_identity_required": True,
            "target_query_execution_enabled": False,
            "query_contamination_disabled": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
        },
        "summary": {
            "t3_contract_count": len(raw),
            "qualified_before_dedupe_count": len(qualified),
            "duplicate_contract_removed": duplicate_count,
            "hardened_contract_count": len(hardened_contracts),
            "rejected_contract_count": len(rejected),
            "next_stage_search_contract_pool_count": len(next_stage_search_contract_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "hardened_search_contracts": hardened_contracts,
        "rejected_contracts": rejected,
        "next_stage_search_contract_pool": next_stage_search_contract_pool,
        "all_records": records,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 60)
    print("HISTORICAL SEARCH CONTRACT SEMANTIC HARDENING RESULT")
    print("=" * 60)
    print("T-3 contract count:", len(raw))
    print("Qualified before dedupe:", len(qualified))
    print("Duplicate contract removed:", duplicate_count)
    print("Hardened contract count:", len(hardened_contracts))
    print("Rejected contract count:", len(rejected))
    print("Next-stage search contract pool count:", len(next_stage_search_contract_pool))

    if hardened_contracts:
        print()
        print("HARDENED BOARD SEARCH CONTRACTS")
        print("-" * 60)
        for index, item in enumerate(hardened_contracts, start=1):
            print(f"[{index}] {item.get('source_family')}")
            print("Regions:", item.get("regions"))
            print("Action:", item.get("action_url"))
            print("Method:", item.get("method"))
            print("Field:", item.get("search_field"))
            print("Hidden params:", item.get("hidden_params"))
            print("Reasons:", item.get("hardening_reasons"))
            print()

    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print()
    print("Output:", OUTPUT_PATH)

    # Validation
    keys = [contract_key(item) for item in hardened_contracts]
    next_keys = [contract_key(item) for item in next_stage_search_contract_pool]

    global_search_leakage = sum(
        1 for item in hardened_contracts
        if any(term in normalized_path_query(item.get("action_url") or "") for term in GLOBAL_SEARCH_PATH_TERMS)
    )
    satisfaction_leakage = sum(
        1 for item in hardened_contracts
        if (
            any(term in normalized_path_query(item.get("action_url") or "") for term in SATISFACTION_PATH_TERMS)
            or normalize_space((item.get("search_field") or {}).get("name")).lower() == "researchcontent"
        )
    )
    js_only_leakage = sum(
        1 for item in hardened_contracts
        if normalize_space(item.get("method")).upper() == "UNKNOWN"
    )
    weak_board_leakage = sum(
        1 for item in hardened_contracts
        if not any(term in normalized_path_query(item.get("action_url") or "") for term in BOARD_ACTION_TERMS)
        and not any(
            any(term in normalized_path_query(url) for term in BOARD_ACTION_TERMS)
            for url in (item.get("source_urls") or [])
        )
    )
    target_query_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    target_document_evidence_leakage = sum(1 for item in records if item.get("target_document_evidence") is True)
    verified_positive_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_registration_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-3 input exists": T3_INPUT_PATH.exists(),
        "T-3 input parsed": isinstance(data, dict),
        "T-3 recovered contracts loaded": len(raw) > 0,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in records),
        "global site search leakage zero": global_search_leakage == 0,
        "satisfaction form leakage zero": satisfaction_leakage == 0,
        "JS-only executable leakage zero": js_only_leakage == 0,
        "weak board identity leakage zero": weak_board_leakage == 0,
        "hardened contracts unique": len(keys) == len(set(keys)),
        "next-stage contracts unique": len(next_keys) == len(set(next_keys)),
        "hardened and next-stage parity": set(keys) == set(next_keys),
        "target query execution leakage zero": target_query_leakage == 0,
        "target document evidence leakage zero": target_document_evidence_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")

    print()
    print("Global search leakage:", global_search_leakage)
    print("Satisfaction leakage:", satisfaction_leakage)
    print("JS-only leakage:", js_only_leakage)
    print("Weak board leakage:", weak_board_leakage)
    print("Target query execution leakage:", target_query_leakage)
    print("Target document evidence leakage:", target_document_evidence_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print()
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "Development density management area historical search contract semantic hardening regression failed"
        )


if __name__ == "__main__":
    main()
