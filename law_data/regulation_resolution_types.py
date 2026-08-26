# -*- coding: utf-8 -*-

"""
Regulation Resolution Type Registry

목적
======================================================================

각 규제가 어떤 방식으로 최종 SITE TRUE / FALSE / UNKNOWN에 도달해야 하는지
공통 resolution policy를 정의한다.

핵심 원칙
======================================================================

1. 모든 규제를 동일한 crawling depth로 처리하지 않는다.

2. 규제별 resolution type을 명시한다.

3. source discovery 실패와 규제 FALSE를 구분한다.

4. historical source 검색 실패만으로 FALSE를 허용하지 않는다.

5. runtime registration / SITE TRUE는 각 규제의 최종 verification stage
   이전에는 허용하지 않는다.

Resolution Types
======================================================================

SPATIAL_DATA_CONFIRMED
    공식 공간데이터 자체로 적용 여부를 확정할 수 있는 규제

NOTICE_CONFIRMED
    공식 지정/변경/해제 고시 identity가 핵심인 규제

LEGAL_RULE_CALCULATED
    법령·조례·별표 등의 규칙을 SITE facts에 적용하여 계산하는 규제

HYBRID_SPATIAL_NOTICE
    지정고시와 공간 포함 여부를 모두 검증해야 하는 규제

EXTERNAL_AUTHORITY_REQUIRED
    외부기관 확인 또는 별도 원천이 필요하여 자동 확정이 제한되는 규제
"""

from __future__ import annotations

from copy import deepcopy
from enum import Enum
from typing import Any, Dict, Iterable, List


# ============================================================
# RESOLUTION TYPES
# ============================================================

class RegulationResolutionType(str, Enum):

    SPATIAL_DATA_CONFIRMED = (
        "SPATIAL_DATA_CONFIRMED"
    )

    NOTICE_CONFIRMED = (
        "NOTICE_CONFIRMED"
    )

    LEGAL_RULE_CALCULATED = (
        "LEGAL_RULE_CALCULATED"
    )

    HYBRID_SPATIAL_NOTICE = (
        "HYBRID_SPATIAL_NOTICE"
    )

    EXTERNAL_AUTHORITY_REQUIRED = (
        "EXTERNAL_AUTHORITY_REQUIRED"
    )


VALID_RESOLUTION_TYPES = {
    item.value
    for item in RegulationResolutionType
}


# ============================================================
# FINAL STATUS
# ============================================================

STATUS_TRUE = "TRUE"
STATUS_FALSE = "FALSE"
STATUS_UNKNOWN = "UNKNOWN"

VALID_FINAL_STATUSES = {
    STATUS_TRUE,
    STATUS_FALSE,
    STATUS_UNKNOWN,
}


# ============================================================
# SOURCE RESULT STATUS
# ============================================================

SOURCE_FOUND = "FOUND"
SOURCE_NOT_FOUND = "NOT_FOUND_IN_THIS_SOURCE"
SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
SOURCE_ERROR = "SOURCE_ERROR"

VALID_SOURCE_RESULTS = {
    SOURCE_FOUND,
    SOURCE_NOT_FOUND,
    SOURCE_UNAVAILABLE,
    SOURCE_ERROR,
}


# ============================================================
# REGISTRY
# ============================================================

REGULATION_RESOLUTION_REGISTRY: Dict[
    str,
    Dict[str, Any],
] = {

    # ========================================================
    # UQQ700
    # 개발밀도관리구역
    # ========================================================

    "UQQ700": {
        "name": "개발밀도관리구역",

        "resolution_type": (
            RegulationResolutionType
            .HYBRID_SPATIAL_NOTICE
            .value
        ),

        # ----------------------------------------------------
        # Source requirements
        # ----------------------------------------------------

        "official_source_required": True,

        "designation_notice_required": True,

        "historical_notice_required": True,

        "spatial_confirmation_required": True,

        "legal_rule_calculation_required": False,

        "external_authority_confirmation_required": False,

        # ----------------------------------------------------
        # Negative evidence policy
        # ----------------------------------------------------

        # 특정 게시판/공보/고시 archive에서 문서가 검색되지 않았다는
        # 이유만으로 UQQ700 = FALSE 처리 금지.
        "negative_evidence_allowed": False,

        "source_not_found_means_false": False,

        # ----------------------------------------------------
        # Promotion guards
        # ----------------------------------------------------

        "discovery_stage_positive_allowed": False,

        "endpoint_stage_positive_allowed": False,

        "document_candidate_positive_allowed": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        # ----------------------------------------------------
        # Final TRUE requirements
        # ----------------------------------------------------

        "true_requirements": [
            "OFFICIAL_DESIGNATION_IDENTITY_VERIFIED",
            "DESIGNATION_VALIDITY_VERIFIED",
            "SITE_SPATIAL_INCLUSION_VERIFIED",
        ],

        # ----------------------------------------------------
        # Final FALSE requirements
        # ----------------------------------------------------

        # 단순 미검색은 포함하지 않는다.
        "false_requirements_any": [
            "OFFICIAL_SPATIAL_EXCLUSION_VERIFIED",
            "OFFICIAL_RELEASE_OR_CANCELLATION_VERIFIED",
            "AUTHORITATIVE_NON_DESIGNATION_VERIFIED",
        ],

        # ----------------------------------------------------
        # UNKNOWN conditions
        # ----------------------------------------------------

        "unknown_conditions": [
            "SOURCE_NOT_FOUND_IN_THIS_SOURCE",
            "HISTORICAL_SOURCE_UNRESOLVED",
            "NOTICE_IDENTITY_UNVERIFIED",
            "SPATIAL_SCOPE_UNVERIFIED",
            "VALIDITY_PERIOD_UNVERIFIED",
        ],
    },
}


# ============================================================
# ACCESSORS
# ============================================================

def get_regulation_resolution_policy(
    standard_code: str,
) -> Dict[str, Any]:

    code = str(
        standard_code
        or ""
    ).strip().upper()

    if not code:

        raise ValueError(
            "standard_code is required."
        )

    policy = (
        REGULATION_RESOLUTION_REGISTRY
        .get(
            code
        )
    )

    if policy is None:

        raise KeyError(
            "Unknown regulation standard code: "
            f"{code}"
        )

    result = deepcopy(
        policy
    )

    result[
        "standard_code"
    ] = code

    return result


def get_resolution_type(
    standard_code: str,
) -> str:

    policy = (
        get_regulation_resolution_policy(
            standard_code
        )
    )

    return str(
        policy[
            "resolution_type"
        ]
    )


def negative_evidence_allowed(
    standard_code: str,
) -> bool:

    policy = (
        get_regulation_resolution_policy(
            standard_code
        )
    )

    return bool(
        policy.get(
            "negative_evidence_allowed",
            False,
        )
    )


def source_not_found_means_false(
    standard_code: str,
) -> bool:

    policy = (
        get_regulation_resolution_policy(
            standard_code
        )
    )

    return bool(
        policy.get(
            "source_not_found_means_false",
            False,
        )
    )


# ============================================================
# FINAL STATUS GUARD
# ============================================================

def can_source_failure_produce_false(
    standard_code: str,
) -> bool:

    """
    특정 source에서 문서를 찾지 못한 사실만으로
    규제 FALSE를 생성할 수 있는지 반환한다.
    """

    policy = (
        get_regulation_resolution_policy(
            standard_code
        )
    )

    return bool(
        policy.get(
            "negative_evidence_allowed",
            False,
        )
        and policy.get(
            "source_not_found_means_false",
            False,
        )
    )


def resolve_source_failure_status(
    standard_code: str,
) -> str:

    """
    source discovery 결과가 0건일 때의 SITE-level 의미.

    현재 UQQ700:
        NOT_FOUND_IN_THIS_SOURCE
        -> UNKNOWN

    절대로 자동 FALSE가 아니다.
    """

    if can_source_failure_produce_false(
        standard_code
    ):

        return STATUS_FALSE

    return STATUS_UNKNOWN


# ============================================================
# VALIDATION
# ============================================================

def validate_policy(
    standard_code: str,
) -> List[str]:

    policy = (
        get_regulation_resolution_policy(
            standard_code
        )
    )

    errors: List[str] = []

    resolution_type = str(
        policy.get(
            "resolution_type"
        )
        or ""
    )

    if (
        resolution_type
        not in VALID_RESOLUTION_TYPES
    ):

        errors.append(
            "INVALID_RESOLUTION_TYPE"
        )

    if (
        policy.get(
            "site_positive_allowed"
        )
        is True
        and policy.get(
            "runtime_registration_allowed"
        )
        is not True
    ):

        errors.append(
            "SITE_POSITIVE_WITHOUT_RUNTIME_REGISTRATION_POLICY"
        )

    if (
        policy.get(
            "source_not_found_means_false"
        )
        is True
        and policy.get(
            "negative_evidence_allowed"
        )
        is not True
    ):

        errors.append(
            "SOURCE_NOT_FOUND_FALSE_WITHOUT_NEGATIVE_EVIDENCE_POLICY"
        )

    if (
        resolution_type
        == (
            RegulationResolutionType
            .HYBRID_SPATIAL_NOTICE
            .value
        )
    ):

        if not policy.get(
            "designation_notice_required"
        ):

            errors.append(
                "HYBRID_TYPE_REQUIRES_DESIGNATION_NOTICE"
            )

        if not policy.get(
            "spatial_confirmation_required"
        ):

            errors.append(
                "HYBRID_TYPE_REQUIRES_SPATIAL_CONFIRMATION"
            )

    return errors


def validate_registry() -> Dict[str, List[str]]:

    result: Dict[
        str,
        List[str],
    ] = {}

    for standard_code in sorted(
        REGULATION_RESOLUTION_REGISTRY
    ):

        errors = validate_policy(
            standard_code
        )

        if errors:

            result[
                standard_code
            ] = errors

    return result


# ============================================================
# DEBUG
# ============================================================

def print_registry_summary() -> None:

    print(
        "=" * 60
    )

    print(
        "REGULATION RESOLUTION REGISTRY"
    )

    print(
        "=" * 60
    )

    for standard_code, policy in sorted(
        REGULATION_RESOLUTION_REGISTRY.items()
    ):

        print()

        print(
            "Standard code:",
            standard_code,
        )

        print(
            "Name:",
            policy.get(
                "name"
            ),
        )

        print(
            "Resolution type:",
            policy.get(
                "resolution_type"
            ),
        )

        print(
            "Negative evidence allowed:",
            policy.get(
                "negative_evidence_allowed"
            ),
        )

        print(
            "Historical notice required:",
            policy.get(
                "historical_notice_required"
            ),
        )

        print(
            "Spatial confirmation required:",
            policy.get(
                "spatial_confirmation_required"
            ),
        )

    errors = validate_registry()

    print()

    print(
        "=" * 60
    )

    print(
        "VALIDATION"
    )

    print(
        "=" * 60
    )

    print(
        "Registry valid:",
        not bool(
            errors
        ),
    )

    if errors:

        print(
            errors
        )


if __name__ == "__main__":

    print_registry_summary()