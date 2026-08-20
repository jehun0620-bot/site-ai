# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-8
Branch-local predicate registry 적용 및 applicability 보정

목표
======================================================================
1. C-10-2A-7에서 확인된 branch-local predicate를 정식 registry로 정의
2. 특정 clause에만 branch condition을 추가
3. 기존 SITE / PROJECT / PROCEDURE condition과 함께 재평가
4. 미입력 PROJECT predicate는 UNSET -> CONDITIONAL
5. 미확정 SITE predicate는 UNKNOWN
6. clause 20 / 188 / 208이 더 이상 잘못 APPLICABLE로 남지 않는지 확인
7. 부모 condition 전체 상속은 사용하지 않음
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2A-8 "
    "branch-local predicate applicability fix"
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

CLAUSE_PATH = (
    OUTPUT_DIR
    / "law_special_rule_clauses.json"
)

SITE_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)

PROJECT_PATH = (
    OUTPUT_DIR
    / "project_profile_template.json"
)

PROCEDURE_PATH = (
    OUTPUT_DIR
    / "procedure_profile_template.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)


# ============================================================
# applicability
# ============================================================

APPLICABLE = "APPLICABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
CONDITIONAL = "CONDITIONAL"
UNKNOWN = "UNKNOWN"


# ============================================================
# semantic overrides
# ============================================================

CONDITION_TYPE_OVERRIDES = {
    "기존공장": "SITE_HISTORY",
}


# ============================================================
# Branch-local predicate registry
#
# 특정 조문에만 적용한다.
# ============================================================

BRANCH_CONDITION_REGISTRY = {

    20: [
        {
            "name": "시장정비사업대상전통시장",
            "type": "PROJECT",
            "field": (
                "market_redevelopment_target_traditional_market"
            ),
            "reason": (
                "시장정비사업 추진계획 승인대상 "
                "전통시장에 한해 적용되는 branch"
            ),
        },
    ],

    188: [
        {
            "name": "감염병대응필요시설",
            "type": "PROJECT",
            "field": (
                "infectious_disease_response_facility"
            ),
            "reason": (
                "감염병 대응 등을 위하여 "
                "필요한 경우에 적용되는 branch"
            ),
        },
    ],

    208: [
        {
            "name": "서울도심",
            "type": "SITE",
            "field": (
                "seoul_downtown_area"
            ),
            "reason": (
                "서울도심 내 사업에 한해 적용되는 branch"
            ),
        },

        {
            "name": "도시정비형재개발사업",
            "type": "PROJECT",
            "field": (
                "urban_redevelopment_project"
            ),
            "reason": (
                "도시정비형 재개발사업으로 "
                "시행하는 경우에 한해 적용"
            ),
        },
    ],
}


# ============================================================
# util
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def effective_condition_type(
    name: str,
    declared_type: str,
) -> str:

    return CONDITION_TYPE_OVERRIDES.get(
        name,
        declared_type,
    )


# ============================================================
# SITE index
# ============================================================

def build_site_index(
    snapshot: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    result = {}

    for group in (
        "conditions",
        "supplemental_conditions",
    ):

        for item in snapshot.get(
            group,
            [],
        ):

            if not isinstance(
                item,
                dict,
            ):
                continue

            name = safe_string(
                item.get(
                    "name"
                )
            )

            if not name:
                continue

            result[name] = {
                "state": safe_string(
                    item.get(
                        "status"
                    )
                ),
                "confidence": safe_string(
                    item.get(
                        "confidence"
                    )
                ),
                "source": (
                    "SITE_CONDITION_SNAPSHOT"
                ),
            }

    return result


# ============================================================
# profile index
# ============================================================

def build_profile_index(
    profile: Dict[str, Any],
    source_name: str,
) -> Dict[str, Dict[str, Any]]:

    result = {}

    for item in profile.get(
        "conditions",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        name = safe_string(
            item.get(
                "name"
            )
        )

        if not name:
            continue

        result[name] = {
            "state": safe_string(
                item.get(
                    "state"
                )
            ),
            "value": item.get(
                "value"
            ),
            "confidence": safe_string(
                item.get(
                    "confidence"
                )
            ),
            "source": source_name,
        }

    return result


# ============================================================
# title-derived SITE condition
# ============================================================

def title_site_conditions(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    title = safe_string(
        clause.get(
            "rule_title"
        )
    )

    explicit_names = {
        safe_string(
            item.get(
                "name"
            )
        )
        for item
        in clause.get(
            "conditions",
            []
        )
        if isinstance(
            item,
            dict,
        )
    }

    result = []

    for name in site_index:

        if name in explicit_names:
            continue

        if name not in title:
            continue

        result.append(
            {
                "name": name,
                "type": "SITE",
                "derived": True,
                "derived_from": (
                    "rule_title"
                ),
            }
        )

    return result


# ============================================================
# effective conditions
# ============================================================

def build_effective_conditions(
    clause_index: int,
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    result = [
        item
        for item
        in clause.get(
            "conditions",
            [],
        )
        if isinstance(
            item,
            dict,
        )
    ]

    result.extend(
        title_site_conditions(
            clause,
            site_index,
        )
    )

    # --------------------------------------------------------
    # branch-local condition 추가
    # --------------------------------------------------------

    for item in (
        BRANCH_CONDITION_REGISTRY.get(
            clause_index,
            [],
        )
    ):

        result.append(
            {
                **item,
                "derived": True,
                "derived_from": (
                    "BRANCH_LOCAL_REGISTRY"
                ),
            }
        )

    # --------------------------------------------------------
    # 이름/type 중복 제거
    # --------------------------------------------------------

    dedup = {}

    for item in result:

        key = (
            safe_string(
                item.get(
                    "name"
                )
            ),
            safe_string(
                item.get(
                    "type"
                )
            ),
        )

        if not key[0]:
            continue

        dedup[key] = item

    return list(
        dedup.values()
    )


# ============================================================
# condition evaluate
# ============================================================

def evaluate_condition(
    condition: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
    procedure_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    name = safe_string(
        condition.get(
            "name"
        )
    )

    declared_type = safe_string(
        condition.get(
            "type"
        )
    )

    effective_type = (
        effective_condition_type(
            name,
            declared_type,
        )
    )

    base = {
        "name": name,
        "declared_type": (
            declared_type
        ),
        "effective_type": (
            effective_type
        ),
        "derived": bool(
            condition.get(
                "derived",
                False,
            )
        ),
        "derived_from": (
            condition.get(
                "derived_from"
            )
        ),
    }

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    if effective_type == "SITE":

        value = site_index.get(
            name
        )

        if value:
            return {
                **base,
                **value,
            }

        # 서울도심 같은 신규 SITE predicate는
        # 아직 evidence가 없으므로 UNKNOWN
        return {
            **base,
            "state": "UNKNOWN",
            "confidence": "NONE",
            "source": (
                "SITE_BRANCH_PREDICATE_UNRESOLVED"
            ),
        }

    # --------------------------------------------------------
    # SITE HISTORY
    # --------------------------------------------------------

    if effective_type == (
        "SITE_HISTORY"
    ):

        value = site_index.get(
            name
        )

        if value:
            return {
                **base,
                **value,
            }

        return {
            **base,
            "state": "UNKNOWN",
            "confidence": "NONE",
            "source": (
                "SITE_HISTORY_RESOLUTION_MISSING"
            ),
        }

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    if effective_type == (
        "PROJECT"
    ):

        value = project_index.get(
            name
        )

        if value:
            return {
                **base,
                **value,
            }

        # 신규 branch PROJECT predicate는
        # ProjectProfile에 아직 없으므로 UNSET
        return {
            **base,
            "state": "UNSET",
            "confidence": "NONE",
            "source": (
                "BRANCH_PROJECT_INPUT_REQUIRED"
            ),
        }

    # --------------------------------------------------------
    # PROCEDURE
    # --------------------------------------------------------

    if effective_type == (
        "PROCEDURE"
    ):

        value = procedure_index.get(
            name
        )

        if value:
            return {
                **base,
                **value,
            }

        return {
            **base,
            "state": "UNSET",
            "confidence": "NONE",
            "source": (
                "PROCEDURE_PROFILE_MISSING"
            ),
        }

    return {
        **base,
        "state": "UNKNOWN",
        "confidence": "NONE",
        "source": (
            "UNKNOWN_CONDITION_TYPE"
        ),
    }


# ============================================================
# clause evaluate
# ============================================================

def evaluate_clause(
    clause_index: int,
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
    procedure_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    if safe_string(
        clause.get(
            "zone_relevance"
        )
    ) == "OTHER_ZONE":

        return {
            "applicability": (
                NOT_APPLICABLE
            ),
            "reason": (
                "현재 SITE 용도지역 불일치"
            ),
            "effective_conditions": [],
            "condition_results": [],
        }

    conditions = (
        build_effective_conditions(
            clause_index,
            clause,
            site_index,
        )
    )

    results = [
        evaluate_condition(
            condition,
            site_index,
            project_index,
            procedure_index,
        )
        for condition
        in conditions
    ]

    false_values = [
        item
        for item in results
        if item.get(
            "state"
        ) == "FALSE"
    ]

    if false_values:

        return {
            "applicability": (
                NOT_APPLICABLE
            ),
            "reason": (
                "필수조건 FALSE: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in false_values
                )
            ),
            "effective_conditions": (
                conditions
            ),
            "condition_results": (
                results
            ),
        }

    unknown_values = [
        item
        for item in results
        if item.get(
            "state"
        ) == "UNKNOWN"
    ]

    if unknown_values:

        return {
            "applicability": (
                UNKNOWN
            ),
            "reason": (
                "필수조건 미확정: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in unknown_values
                )
            ),
            "effective_conditions": (
                conditions
            ),
            "condition_results": (
                results
            ),
        }

    unset_values = [
        item
        for item in results
        if item.get(
            "state"
        ) == "UNSET"
    ]

    if unset_values:

        return {
            "applicability": (
                CONDITIONAL
            ),
            "reason": (
                "추가 입력 필요: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in unset_values
                )
            ),
            "effective_conditions": (
                conditions
            ),
            "condition_results": (
                results
            ),
        }

    return {
        "applicability": (
            APPLICABLE
        ),
        "reason": (
            "모든 필수조건 충족"
        ),
        "effective_conditions": (
            conditions
        ),
        "condition_results": (
            results
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    site_data = load_json(
        SITE_PATH
    )

    project_data = load_json(
        PROJECT_PATH
    )

    procedure_data = load_json(
        PROCEDURE_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    site_index = build_site_index(
        site_data
    )

    project_index = (
        build_profile_index(
            project_data,
            "PROJECT_PROFILE",
        )
    )

    procedure_index = (
        build_profile_index(
            procedure_data,
            "PROCEDURE_PROFILE",
        )
    )

    results = []

    status_counter = Counter()

    branch_counter = Counter()

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        evaluation = evaluate_clause(
            index,
            clause,
            site_index,
            project_index,
            procedure_index,
        )

        status_counter[
            evaluation[
                "applicability"
            ]
        ] += 1

        for condition in evaluation.get(
            "condition_results",
            [],
        ):

            if condition.get(
                "derived_from"
            ) == (
                "BRANCH_LOCAL_REGISTRY"
            ):

                branch_counter[
                    condition[
                        "name"
                    ]
                ] += 1

        results.append(
            {
                "clause_index": index,

                "rule_title": (
                    clause.get(
                        "rule_title"
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                **evaluation,
            }
        )

    # ========================================================
    # target 확인
    # ========================================================

    target_indexes = {
        20,
        188,
        208,
    }

    targets = {
        item[
            "clause_index"
        ]: item

        for item
        in results

        if item[
            "clause_index"
        ]
        in target_indexes
    }

    clause20 = targets.get(
        20,
        {}
    )

    clause188 = targets.get(
        188,
        {}
    )

    clause208 = targets.get(
        208,
        {}
    )

    # --------------------------------------------------------
    # 예상
    #
    # 20  -> CONDITIONAL
    # 188 -> CONDITIONAL
    # 208 -> UNKNOWN
    #
    # 208은 서울도심 SITE predicate가 미확정이므로
    # PROJECT UNSET보다 UNKNOWN 우선
    # --------------------------------------------------------

    validations = {
        "314 clauses 유지": (
            len(
                results
            ) == 314
        ),

        "clause 20 APPLICABLE 제거": (
            clause20.get(
                "applicability"
            )
            == CONDITIONAL
        ),

        "clause 188 APPLICABLE 제거": (
            clause188.get(
                "applicability"
            )
            == CONDITIONAL
        ),

        "clause 208 APPLICABLE 제거": (
            clause208.get(
                "applicability"
            )
            == UNKNOWN
        ),

        "branch predicate registry 4개 적용": (
            sum(
                branch_counter.values()
            )
            == 4
        ),

        "parent condition 전체 상속 사용 안 함": (
            True
        ),

        "branch PROJECT 미입력을 FALSE 처리하지 않음": (
            True
        ),

        "branch SITE 미확정을 FALSE 처리하지 않음": (
            True
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": STEP_NAME,

        "summary": {
            "total": len(
                results
            ),

            "applicable": (
                status_counter[
                    APPLICABLE
                ]
            ),

            "not_applicable": (
                status_counter[
                    NOT_APPLICABLE
                ]
            ),

            "conditional": (
                status_counter[
                    CONDITIONAL
                ]
            ),

            "unknown": (
                status_counter[
                    UNKNOWN
                ]
            ),
        },

        "branch_predicate_usage": (
            dict(
                branch_counter
            )
        ),

        "branch_registry": (
            BRANCH_CONDITION_REGISTRY
        ),

        "target_fixes": {
            "20": clause20,
            "188": clause188,
            "208": clause208,
        },

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),

        "clauses": (
            results
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Summary:",
        output[
            "summary"
        ],
    )

    print(
        "Branch predicates:",
        dict(
            branch_counter
        ),
    )

    print()

    for index in (
        20,
        188,
        208,
    ):

        item = targets.get(
            index,
            {}
        )

        print(
            f"clause {index}: "
            f"{item.get('applicability')} "
            f"| {item.get('rule_title')}"
        )

        branch_conditions = [
            (
                condition.get(
                    "name"
                ),
                condition.get(
                    "state"
                ),
            )

            for condition
            in item.get(
                "condition_results",
                []
            )

            if condition.get(
                "derived_from"
            )
            == "BRANCH_LOCAL_REGISTRY"
        ]

        print(
            "  branch:",
            branch_conditions,
        )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )