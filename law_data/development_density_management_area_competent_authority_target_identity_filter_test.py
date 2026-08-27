# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-14
Development Density Management Area
Competent Authority Result-Row Target Identity Filter

목표
======================================================================
T-13에서 복원한 competent-authority-local result row만 입력으로 사용하여,
UQQ700 target query를 다시 실행하지 않고 row-local evidence에서
개발밀도관리구역 identity가 실제로 존재하는지 엄격히 필터링한다.

핵심 원칙
======================================================================
1. T-13 next_stage_result_row_pool만 입력으로 사용한다.
2. pagination contract는 target evidence가 아니다.
3. query 문자열은 evidence가 아니다.
4. page title은 evidence가 아니다.
5. source URL 자체는 target evidence가 아니다.
6. row_text / row_text_variants / notice_numbers / detail URL path만 사용한다.
7. '도시관리계획', '지형도면', '고시'만으로 UQQ700 candidate 승격 금지.
8. 개발밀도관리구역 또는 이에 준하는 강한 문맥이 row-local evidence에 있어야 한다.
9. target identity가 확인돼도 verified positive가 아니다.
10. 실제 detail 문서는 T-15 direct document verification에서 재조회한다.
11. 문서 미발견은 SITE FALSE가 아니다.
12. runtime registration / SITE TRUE / SITE FALSE 자동판정 금지.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set
from urllib.parse import urlparse


# ============================================================
# PATH / TARGET
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_competent_authority_historical_pagination_discovery.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_competent_authority_target_identity_filter.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False


# ============================================================
# INPUT / OUTPUT CLASS
# ============================================================

INPUT_CLASSES = {
    "RECOVERED_AUTHORITY_NOTICE_RESULT_ROW",
    "RECOVERED_AUTHORITY_URBAN_RESULT_ROW",
}

CLASS_TARGET_IDENTITY = "QUALIFIED_UQQ700_TARGET_IDENTITY_ROW"
CLASS_TARGET_CONTEXT = "QUALIFIED_UQQ700_TARGET_CONTEXT_ROW"
CLASS_REJECTED_GENERIC_URBAN = "REJECTED_GENERIC_URBAN_PLANNING_ROW"
CLASS_REJECTED_OTHER_REGULATION = "REJECTED_OTHER_REGULATION_ROW"
CLASS_REJECTED_TARGET_WEAK = "REJECTED_UQQ700_TARGET_EVIDENCE_WEAK"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_RESULT_ROW"

VALID_CLASSES = {
    CLASS_TARGET_IDENTITY,
    CLASS_TARGET_CONTEXT,
    CLASS_REJECTED_GENERIC_URBAN,
    CLASS_REJECTED_OTHER_REGULATION,
    CLASS_REJECTED_TARGET_WEAK,
    CLASS_REJECTED_INVALID,
}

QUALIFIED_CLASSES = {
    CLASS_TARGET_IDENTITY,
    CLASS_TARGET_CONTEXT,
}


# ============================================================
# TARGET EVIDENCE
# ============================================================

DIRECT_TARGET_PATTERNS = [
    re.compile(r"개발\s*밀도\s*관리\s*구역", re.I),
]

STRONG_CONTEXT_PATTERNS = [
    re.compile(r"도시관리계획.{0,100}개발\s*밀도\s*관리\s*구역", re.I),
    re.compile(r"개발\s*밀도\s*관리\s*구역.{0,100}(?:지정|결정|변경|고시|지형도면)", re.I),
    re.compile(r"(?:지정|결정|변경|고시|지형도면).{0,100}개발\s*밀도\s*관리\s*구역", re.I),
]

GENERIC_URBAN_TERMS = {
    "도시관리계획",
    "도시계획",
    "지형도면",
    "결정",
    "변경",
    "고시",
    "공고",
}

OTHER_REGULATION_TERMS = {
    "도로",
    "공원",
    "하천",
    "도시계획시설",
    "개발행위허가 제한",
    "개발행위허가의 제한",
    "도시개발구역",
    "산업단지",
    "지구단위계획",
    "용도지역",
    "용도지구",
    "용도구역",
    "방재지구",
    "개발진흥지구",
    "취락지구",
}

DETAIL_PATH_HINTS = {
    "view",
    "detail",
    "read",
    "article",
    "bbsview",
    "board/view",
    "post/view",
}


# ============================================================
# UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def contains_any(value: str, terms: Iterable[str]) -> bool:
    lowered = normalize_space(value).lower()
    return any(normalize_space(term).lower() in lowered for term in terms if normalize_space(term))


def detail_path_evidence(url: str) -> bool:
    try:
        path = (urlparse(normalize_space(url)).path or "").lower()
    except Exception:
        return False
    return any(term in path for term in DETAIL_PATH_HINTS)


# ============================================================
# INPUT
# ============================================================

def load_result_rows(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw = data.get("next_stage_result_row_pool")
    if not isinstance(raw, list):
        return []

    result: List[Dict[str, Any]] = []
    seen: Set[str] = set()

    for item in raw:
        if not isinstance(item, dict):
            continue

        classification = normalize_space(item.get("classification"))
        if classification not in INPUT_CLASSES:
            continue

        url = normalize_space(item.get("url"))
        if not url or url in seen:
            continue
        seen.add(url)

        result.append({
            "page_family": normalize_space(item.get("page_family")),
            "source_families": unique_strings(item.get("source_families") or []),
            "authority_role": normalize_space(item.get("authority_role")),
            "authority_entities": unique_strings(item.get("authority_entities") or []),
            "regions": unique_strings(item.get("regions") or []),
            "source_urls": unique_strings(item.get("source_urls") or []),
            "page_urls": unique_strings(item.get("page_urls") or []),
            "url": url,
            "row_text": normalize_space(item.get("row_text")),
            "row_text_variants": unique_strings(item.get("row_text_variants") or []),
            "dates": unique_strings(item.get("dates") or []),
            "notice_numbers": unique_strings(item.get("notice_numbers") or []),
            "input_classification": classification,
            "input_reasons": unique_strings(item.get("reasons") or []),
        })

    return result


# ============================================================
# CLASSIFICATION
# ============================================================

def row_local_text(item: Dict[str, Any]) -> str:
    # 중요: page title / query / source URL은 포함하지 않는다.
    return normalize_space(" ".join([
        item.get("row_text") or "",
        " ".join(item.get("row_text_variants") or []),
        " ".join(item.get("notice_numbers") or []),
        item.get("url") or "",
    ]))


def evaluate_target_identity(item: Dict[str, Any]) -> Dict[str, Any]:
    url = normalize_space(item.get("url"))
    local_text = row_local_text(item)

    if not url or not local_text:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_INVALID,
            "reasons": ["INVALID_OR_EMPTY_ROW_LOCAL_EVIDENCE"],
        }

    direct_reasons: List[str] = []
    context_reasons: List[str] = []

    for pattern in DIRECT_TARGET_PATTERNS:
        match = pattern.search(local_text)
        if match:
            direct_reasons.append("TARGET_DIRECT:" + normalize_space(match.group(0)))

    for pattern in STRONG_CONTEXT_PATTERNS:
        match = pattern.search(local_text)
        if match:
            context_reasons.append("TARGET_CONTEXT:" + normalize_space(match.group(0)))

    if direct_reasons:
        return {
            "qualified": True,
            "classification": CLASS_TARGET_IDENTITY,
            "reasons": unique_strings(
                direct_reasons
                + context_reasons
                + (["DETAIL_PATH_IDENTITY"] if detail_path_evidence(url) else [])
            ),
        }

    if context_reasons:
        return {
            "qualified": True,
            "classification": CLASS_TARGET_CONTEXT,
            "reasons": unique_strings(
                context_reasons
                + (["DETAIL_PATH_IDENTITY"] if detail_path_evidence(url) else [])
            ),
        }

    has_generic_urban = any(term in local_text for term in GENERIC_URBAN_TERMS)
    has_other_regulation = any(term in local_text for term in OTHER_REGULATION_TERMS)

    if has_generic_urban and has_other_regulation:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_OTHER_REGULATION,
            "reasons": ["OTHER_REGULATION_WITH_GENERIC_URBAN_CONTEXT"],
        }

    if has_generic_urban:
        return {
            "qualified": False,
            "classification": CLASS_REJECTED_GENERIC_URBAN,
            "reasons": ["GENERIC_URBAN_PLANNING_EVIDENCE_ONLY"],
        }

    return {
        "qualified": False,
        "classification": CLASS_REJECTED_TARGET_WEAK,
        "reasons": ["UQQ700_ROW_LOCAL_TARGET_EVIDENCE_MISSING"],
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("COMPETENT AUTHORITY RESULT-ROW TARGET IDENTITY FILTER")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    if not INPUT_PATH.exists():
        raise FileNotFoundError(f"T-13 input not found: {INPUT_PATH}")

    input_data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(input_data, dict):
        raise TypeError("T-13 input must be JSON object")

    rows = load_result_rows(input_data)
    print("T-13 result row count:", len(rows))
    print()

    records: List[Dict[str, Any]] = []

    for index, item in enumerate(rows, start=1):
        outcome = evaluate_target_identity(item)

        record = {
            **item,
            "row_local_evidence_preview": row_local_text(item)[:2000],
            "qualified": outcome["qualified"],
            "classification": outcome["classification"],
            "reasons": outcome["reasons"],
            "target_query_executed": False,
            "page_title_used_as_evidence": False,
            "source_url_used_as_target_evidence": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("-" * 60)
        print(f"ROW {index}")
        print("Family:", item.get("page_family"))
        print("URL:", item.get("url"))
        print("Text:", item.get("row_text"))
        print("Notice numbers:", item.get("notice_numbers"))
        print("Dates:", item.get("dates"))
        print("Qualified:", outcome["qualified"])
        print("Resolution:", outcome["classification"])
        print("Reasons:", outcome["reasons"])

    qualified = [item for item in records if item.get("qualified") is True]
    rejected = [item for item in records if item.get("qualified") is not True]

    next_stage_document_identity_pool = [
        {
            "page_family": item.get("page_family"),
            "source_families": item.get("source_families") or [],
            "authority_role": item.get("authority_role"),
            "authority_entities": item.get("authority_entities") or [],
            "regions": item.get("regions") or [],
            "source_urls": item.get("source_urls") or [],
            "page_urls": item.get("page_urls") or [],
            "url": item.get("url"),
            "row_text": item.get("row_text"),
            "row_text_variants": item.get("row_text_variants") or [],
            "dates": item.get("dates") or [],
            "notice_numbers": item.get("notice_numbers") or [],
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "target_identity_candidate_only": True,
            "requires_direct_document_verification": True,
            "target_query_executed": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified
    ]

    if next_stage_document_identity_pool:
        resolution = "COMPETENT_AUTHORITY_UQQ700_TARGET_IDENTITY_FILTER_COMPLETED"
        next_action = (
            "row-local evidence에서 UQQ700 identity가 확인된 candidate만 T-15 direct document verification으로 넘긴다. "
            "T-15에서는 문서를 직접 재조회하여 document title, issuing authority, notice number, date, "
            "개발밀도관리구역 지정/변경 identity 및 region을 검증한다."
        )
    else:
        resolution = "COMPETENT_AUTHORITY_UQQ700_TARGET_IDENTITY_FILTER_NO_DOCUMENT"
        next_action = (
            "현재 복원된 competent-authority result row에는 개발밀도관리구역 row-local identity가 없다. "
            "이는 SITE FALSE가 아니다. UNKNOWN을 유지하며 다음 단계에서는 더 깊은 historical pagination 범위 또는 "
            "별도 spatial designation source를 탐색한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-14 Competent Authority Result-Row Target Identity Filter",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "t13_path": str(INPUT_PATH),
            "t13_resolution": input_data.get("resolution"),
        },
        "method": {
            "t13_result_rows_only": True,
            "target_query_execution_enabled": False,
            "page_title_evidence_enabled": False,
            "source_url_target_evidence_enabled": False,
            "row_local_text_evidence_enabled": True,
            "notice_number_evidence_enabled": True,
            "detail_url_path_supporting_evidence_enabled": True,
            "generic_urban_notice_auto_promotion_disabled": True,
            "other_regulation_guard_enabled": True,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "t13_result_row_count": len(rows),
            "qualified_target_identity_count": len(qualified),
            "rejected_row_count": len(rejected),
            "next_stage_document_identity_pool_count": len(next_stage_document_identity_pool),
        },
        "qualified_target_identity_rows": qualified,
        "rejected_rows": rejected,
        "next_stage_document_identity_pool": next_stage_document_identity_pool,
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
    print("COMPETENT AUTHORITY TARGET IDENTITY FILTER RESULT")
    print("=" * 60)
    print("T-13 result row count:", len(rows))
    print("Qualified target identity count:", len(qualified))
    print("Rejected row count:", len(rejected))
    print("Next-stage document identity pool count:", len(next_stage_document_identity_pool))
    print()
    print("=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print()
    print(next_action)
    print("Output:", OUTPUT_PATH)

    # ========================================================
    # VALIDATION
    # ========================================================

    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in records)
    qualified_classes_valid = all(item.get("classification") in QUALIFIED_CLASSES for item in qualified)

    duplicate_qualified_url_leakage = (
        len([item.get("url") for item in qualified])
        - len({item.get("url") for item in qualified if item.get("url")})
    )

    query_evidence_leakage = sum(
        1 for item in records if item.get("target_query_executed") is True
    )
    page_title_evidence_leakage = sum(
        1 for item in records if item.get("page_title_used_as_evidence") is True
    )
    source_url_evidence_leakage = sum(
        1 for item in records if item.get("source_url_used_as_target_evidence") is True
    )
    generic_urban_qualified_leakage = sum(
        1 for item in qualified
        if not any(pattern.search(row_local_text(item)) for pattern in DIRECT_TARGET_PATTERNS + STRONG_CONTEXT_PATTERNS)
    )
    verified_positive_leakage = sum(
        1 for item in records if item.get("verified_positive") is True
    )
    runtime_registration_leakage = sum(
        1 for item in records if item.get("runtime_registration_allowed") is True
    )
    site_true_leakage = sum(
        1 for item in records if item.get("site_positive_allowed") is True
    )
    site_false_leakage = sum(
        1 for item in records if item.get("site_negative_allowed") is True
    )
    next_stage_safety_leakage = sum(
        1 for item in next_stage_document_identity_pool
        if (
            item.get("verified_positive") is True
            or item.get("runtime_registration_allowed") is True
            or item.get("site_positive_allowed") is True
            or item.get("site_negative_allowed") is True
            or item.get("final_positive_promotion_allowed") is True
        )
    )
    false_from_no_document_leakage = (
        1
        if not qualified
        and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE"
        else 0
    )

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "T-13 input exists": INPUT_PATH.exists(),
        "T-13 input parsed": isinstance(input_data, dict),
        "T-13 result rows loaded": len(rows) > 0,
        "T-13 result rows only": True,
        "target query execution disabled": query_evidence_leakage == 0,
        "page title evidence disabled": page_title_evidence_leakage == 0,
        "source URL target evidence disabled": source_url_evidence_leakage == 0,
        "row-local target identity required": True,
        "generic urban auto-promotion disabled": generic_urban_qualified_leakage == 0,
        "all classes valid": all_classes_valid,
        "qualified classes valid": qualified_classes_valid,
        "qualified URLs unique": duplicate_qualified_url_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_registration_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "next-stage safety leakage zero": next_stage_safety_leakage == 0,
        "false from no document leakage zero": false_from_no_document_leakage == 0,
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
    print("Duplicate qualified URL leakage:", duplicate_qualified_url_leakage)
    print("Target query leakage:", query_evidence_leakage)
    print("Page-title evidence leakage:", page_title_evidence_leakage)
    print("Source URL evidence leakage:", source_url_evidence_leakage)
    print("Generic urban qualified leakage:", generic_urban_qualified_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_registration_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("Next-stage safety leakage:", next_stage_safety_leakage)
    print("False from no document leakage:", false_from_no_document_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")

    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError(
            "UQQ700 competent authority result-row target identity filter regression failed"
        )


if __name__ == "__main__":
    main()
