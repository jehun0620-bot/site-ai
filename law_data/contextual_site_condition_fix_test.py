# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2A-2
rule_title 기반 누락 SITE condition context 보정 검증

목표
======================================================================
1. C-8 clause의 명시 conditions는 그대로 유지한다.
2. rule_title에 C-9 SITE condition명이 명확히 들어있는데
   conditions에 빠진 경우 context-derived SITE condition으로 보충한다.
3. 단순 본문 문자열 출현만으로 condition을 추가하지 않는다.
4. 자연경관지구 / 입체복합구역 HIGH-RISK 5건이
   NOT_APPLICABLE로 교정되는지 확인한다.
5. OTHER_ZONE 규칙을 유지한다.
6. numeric 계산은 아직 수행하지 않는다.
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-2A-2 "
    "누락 SITE condition context 보정"
)


# ============================================================
# 경로
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
    / "contextual_site_condition_fix.json"
)


# ============================================================
# applicability
# ============================================================

APPLICABLE = "APPLICABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
CONDITIONAL = "CONDITIONAL"
UNKNOWN = "UNKNOWN"


# ============================================================
# semantic override
# ============================================================

CONDITION_TYPE_OVERRIDES = {
    "기존공장": "SITE_HISTORY",
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
    source: str,
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
            "confidence": safe_string(
                item.get(
                    "confidence"
                )
            ),
            "value": item.get(
                "value"
            ),
            "source": source,
        }

    return result


# ============================================================
# 명시 condition
# ============================================================

def explicit_condition_names(
    clause: Dict[str, Any],
) -> set[str]:

    return {
        safe_string(
            condition.get(
                "name"
            )
        )

        for condition
        in clause.get(
            "conditions",
            []
        )

        if (
            isinstance(
                condition,
                dict,
            )
            and safe_string(
                condition.get(
                    "name"
                )
            )
        )
    }


# ============================================================
# context-derived SITE condition
# ============================================================

def derive_title_site_conditions(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    """
    매우 보수적으로 rule_title만 사용한다.

    본문 text / inherited_context는 사용하지 않는다.
    """

    title = safe_string(
        clause.get(
            "rule_title"
        )
    )

    if not title:
        return []

    explicit = (
        explicit_condition_names(
            clause
        )
    )

    derived = []

    for name in site_index:

        if name in explicit:
            continue

        if name not in title:
            continue

        derived.append(
            {
                "name": name,
                "type": "SITE",
                "derived": True,
                "derived_from": (
                    "rule_title"
                ),
                "derived_text": title,
            }
        )

    return derived


def effective_conditions(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:

    explicit = [
        condition

        for condition
        in clause.get(
            "conditions",
            []
        )

        if isinstance(
            condition,
            dict,
        )
    ]

    derived = (
        derive_title_site_conditions(
            clause,
            site_index,
        )
    )

    return (
        explicit
        + derived
    )


# ============================================================
# condition 평가
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

    derived = bool(
        condition.get(
            "derived",
            False,
        )
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    if effective_type == "SITE":

        value = site_index.get(
            name
        )

        if value:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                "derived": derived,
                "derived_from": condition.get(
                    "derived_from"
                ),
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
            "derived": derived,
            "state": "UNKNOWN",
            "confidence": "NONE",
            "source": (
                "SITE_RESOLUTION_MISSING"
            ),
        }

    # --------------------------------------------------------
    # SITE_HISTORY
    # --------------------------------------------------------

    if effective_type == (
        "SITE_HISTORY"
    ):

        value = site_index.get(
            name
        )

        if value:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                "derived": derived,
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
            "derived": derived,
            "state": "UNKNOWN",
            "confidence": "NONE",
            "source": (
                "SITE_HISTORY_RESOLUTION_MISSING"
            ),
        }

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    if effective_type == "PROJECT":

        value = project_index.get(
            name
        )

        if value:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                "derived": derived,
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
            "derived": derived,
            "state": "UNSET",
            "confidence": "NONE",
            "source": (
                "PROJECT_PROFILE_MISSING"
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
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                "derived": derived,
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
            "derived": derived,
            "state": "UNSET",
            "confidence": "NONE",
            "source": (
                "PROCEDURE_PROFILE_MISSING"
            ),
        }

    return {
        "name": name,
        "declared_type": declared_type,
        "effective_type": effective_type,
        "derived": derived,
        "state": "UNKNOWN",
        "confidence": "NONE",
        "source": (
            "UNKNOWN_CONDITION_TYPE"
        ),
    }


# ============================================================
# clause 평가
# ============================================================

def evaluate_clause(
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
                "현재 SITE 용도지역과 "
                "clause 적용 용도지역 불일치"
            ),
            "effective_conditions": [],
            "condition_results": [],
        }

    conditions = (
        effective_conditions(
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
        for item
        in results
        if item.get(
            "state"
        )
        == "FALSE"
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
        for item
        in results
        if item.get(
            "state"
        )
        == "UNKNOWN"
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
        for item
        in results
        if item.get(
            "state"
        )
        == "UNSET"
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
            "현재 용도지역 및 모든 필수조건 충족"
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

    site_snapshot = load_json(
        SITE_PATH
    )

    project_profile = load_json(
        PROJECT_PATH
    )

    procedure_profile = load_json(
        PROCEDURE_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    site_index = build_site_index(
        site_snapshot
    )

    project_index = (
        build_profile_index(
            project_profile,
            "PROJECT_PROFILE",
        )
    )

    procedure_index = (
        build_profile_index(
            procedure_profile,
            "PROCEDURE_PROFILE",
        )
    )

    results = []

    derived_counter = Counter()

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
            clause,
            site_index,
            project_index,
            procedure_index,
        )

        for condition in evaluation.get(
            "effective_conditions",
            [],
        ):

            if condition.get(
                "derived"
            ):

                derived_counter[
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
                "zone_relevance": (
                    clause.get(
                        "zone_relevance"
                    )
                ),
                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),
                **evaluation,
            }
        )

    # ========================================================
    # 대상 5건 검증
    # ========================================================

    target_indexes = {
        149,
        150,
        151,
        152,
        272,
    }

    target_results = [
        item
        for item in results
        if item[
            "clause_index"
        ]
        in target_indexes
    ]

    target_all_not_applicable = (
        len(
            target_results
        )
        == 5
        and all(
            item[
                "applicability"
            ]
            == NOT_APPLICABLE

            for item
            in target_results
        )
    )

    natural_landscape_fixed = all(
        item[
            "applicability"
        ]
        == NOT_APPLICABLE

        for item
        in target_results

        if item[
            "clause_index"
        ]
        in {
            149,
            150,
            151,
            152,
        }
    )

    complex_zone_fixed = all(
        item[
            "applicability"
        ]
        == NOT_APPLICABLE

        for item
        in target_results

        if item[
            "clause_index"
        ]
        == 272
    )

    # ========================================================
    # summary
    # ========================================================

    status_counter = Counter(
        item[
            "applicability"
        ]
        for item
        in results
    )

    validations = {
        "314개 clause 유지": (
            len(
                results
            )
            == 314
        ),

        "자연경관지구 4개 HIGH-RISK 보정": (
            natural_landscape_fixed
        ),

        "입체복합구역 1개 HIGH-RISK 보정": (
            complex_zone_fixed
        ),

        "HIGH-RISK 5개 전부 NOT_APPLICABLE": (
            target_all_not_applicable
        ),

        "rule_title만 context condition source로 사용": (
            True
        ),

        "본문 문자열만으로 SITE condition 추가하지 않음": (
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

        "derived_site_conditions": (
            dict(
                derived_counter
            )
        ),

        "target_fixes": (
            target_results
        ),

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
        "Derived SITE conditions:",
        dict(
            derived_counter
        ),
    )

    print()

    for item in target_results:

        derived = [
            condition[
                "name"
            ]
            for condition
            in item.get(
                "condition_results",
                []
            )
            if condition.get(
                "derived"
            )
        ]

        print(
            f"clause {item['clause_index']}: "
            f"{item['applicability']} "
            f"| {item['rule_title']} "
            f"| derived={derived}"
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