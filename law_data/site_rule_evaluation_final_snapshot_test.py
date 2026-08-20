# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3A
SITE Final Rule Evaluation Snapshot

목표
======================================================================
지금까지 분리되어 있던 다음 결과를 하나의 시스템 소비용 snapshot으로 통합한다.

1. SITE spatial condition
2. PROJECT profile
3. PROCEDURE profile
4. Clause applicability
5. Numeric regulation
6. 원 조문 metadata

최종 clause 구조
======================================================================
{
    clause_index,
    law_name,
    rule_title,

    applicability,
    applicability_reason,

    effect_targets,

    conditions,
    required_inputs,
    blocked_by,
    unknown_by,

    numeric_effect,

    current_effect,

    text
}

중요 정책
======================================================================
- 기존 probe 결과를 재판정하지 않는다.
- applicability는 branch_local_predicate_applicability_fix를 source of truth로 사용.
- numeric confirmed BCR/FAR는 site_numeric_regulation_final_snapshot을 사용.
- CONDITIONAL은 PROJECT/PROCEDURE 입력 필요 상태로 유지.
- UNKNOWN은 SITE/history 등 unresolved 상태로 유지.
- NOT_APPLICABLE 조문은 current effect에 반영하지 않는다.
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-3A "
    "SITE final rule evaluation snapshot"
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

APPLICABILITY_PATH = (
    OUTPUT_DIR
    / "branch_local_predicate_applicability_fix.json"
)

NUMERIC_PATH = (
    OUTPUT_DIR
    / "site_numeric_regulation_final_snapshot.json"
)

SEMANTIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_final_snapshot.json"
)


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


# ============================================================
# generic clause index
# ============================================================

def build_clause_index(
    data: Dict[str, Any],
    collection_name: str = "clauses",
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for item in data.get(
        collection_name,
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        index = item.get(
            "clause_index"
        )

        if index is None:
            continue

        result[
            int(index)
        ] = item

    return result


# ============================================================
# semantic index
# ============================================================

def build_semantic_index(
    data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for item in data.get(
        "candidates",
        [],
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        index = item.get(
            "clause_index"
        )

        if index is None:
            continue

        result[
            int(index)
        ] = item

    return result


# ============================================================
# profile indexes
# ============================================================

def build_profile_index(
    profile: Dict[str, Any],
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

        result[
            name
        ] = item

    return result


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

            result[
                name
            ] = item

    return result


# ============================================================
# condition helpers
# ============================================================

def normalize_condition_result(
    item: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "name": (
            item.get(
                "name"
            )
        ),

        "type": (
            item.get(
                "effective_type"
            )
            or item.get(
                "declared_type"
            )
            or item.get(
                "type"
            )
        ),

        "state": (
            item.get(
                "state"
            )
        ),

        "confidence": (
            item.get(
                "confidence"
            )
        ),

        "source": (
            item.get(
                "source"
            )
        ),

        "derived": (
            item.get(
                "derived",
                False,
            )
        ),

        "derived_from": (
            item.get(
                "derived_from"
            )
        ),
    }


def split_conditions(
    results: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:

    normalized = [
        normalize_condition_result(
            item
        )
        for item in results
        if isinstance(
            item,
            dict,
        )
    ]

    required_inputs = [
        item
        for item in normalized
        if item.get(
            "state"
        )
        == "UNSET"
    ]

    blocked_by = [
        item
        for item in normalized
        if item.get(
            "state"
        )
        == "FALSE"
    ]

    unknown_by = [
        item
        for item in normalized
        if item.get(
            "state"
        )
        == "UNKNOWN"
    ]

    satisfied = [
        item
        for item in normalized
        if item.get(
            "state"
        )
        == "TRUE"
    ]

    return {
        "all": normalized,
        "required_inputs": (
            required_inputs
        ),
        "blocked_by": (
            blocked_by
        ),
        "unknown_by": (
            unknown_by
        ),
        "satisfied": (
            satisfied
        ),
    }


# ============================================================
# numeric current effect
# ============================================================

def determine_current_numeric_effect(
    clause_index: int,
    applicability: str,
    semantic_item: Dict[str, Any],
) -> Dict[str, Any]:

    if not semantic_item:

        return {
            "status": (
                "NO_NUMERIC_EFFECT"
            ),
        }

    semantic = semantic_item.get(
        "semantic",
        {}
    )

    effect_class = semantic_item.get(
        "effect_class"
    )

    if applicability == (
        "NOT_APPLICABLE"
    ):

        return {
            "status": (
                "INACTIVE"
            ),

            "effect_class": (
                effect_class
            ),

            "semantic": (
                semantic
            ),
        }

    if applicability == (
        "CONDITIONAL"
    ):

        return {
            "status": (
                "POTENTIAL_CONDITIONAL"
            ),

            "effect_class": (
                effect_class
            ),

            "semantic": (
                semantic
            ),
        }

    if applicability == (
        "UNKNOWN"
    ):

        return {
            "status": (
                "POTENTIAL_UNKNOWN"
            ),

            "effect_class": (
                effect_class
            ),

            "semantic": (
                semantic
            ),
        }

    return {
        "status": (
            "ACTIVE_CANDIDATE"
        ),

        "effect_class": (
            effect_class
        ),

        "semantic": (
            semantic
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

    applicability_data = load_json(
        APPLICABILITY_PATH
    )

    numeric_data = load_json(
        NUMERIC_PATH
    )

    semantic_data = load_json(
        SEMANTIC_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    applicability_index = (
        build_clause_index(
            applicability_data
        )
    )

    semantic_index = (
        build_semantic_index(
            semantic_data
        )
    )

    site_index = (
        build_site_index(
            site_data
        )
    )

    project_index = (
        build_profile_index(
            project_data
        )
    )

    procedure_index = (
        build_profile_index(
            procedure_data
        )
    )

    # ========================================================
    # final numeric regulation
    # ========================================================

    confirmed_regulation = (
        numeric_data.get(
            "confirmed_regulation",
            {}
        )
    )

    confirmed_bcr = (
        confirmed_regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
    )

    confirmed_far = (
        confirmed_regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
    )

    # ========================================================
    # clause evaluation merge
    # ========================================================

    evaluations = []

    applicability_counter = Counter()

    clauses_with_numeric = 0

    clauses_with_required_input = 0

    clauses_with_unknown = 0

    clauses_with_blocker = 0

    for index, clause in enumerate(
        clauses,
        start=1,
    ):

        if not isinstance(
            clause,
            dict,
        ):
            continue

        app = (
            applicability_index.get(
                index,
                {}
            )
        )

        applicability = (
            app.get(
                "applicability",
                "UNKNOWN",
            )
        )

        applicability_counter[
            applicability
        ] += 1

        condition_split = (
            split_conditions(
                app.get(
                    "condition_results",
                    [],
                )
            )
        )

        if condition_split[
            "required_inputs"
        ]:

            clauses_with_required_input += 1

        if condition_split[
            "unknown_by"
        ]:

            clauses_with_unknown += 1

        if condition_split[
            "blocked_by"
        ]:

            clauses_with_blocker += 1

        semantic_item = (
            semantic_index.get(
                index,
                {}
            )
        )

        if semantic_item:

            clauses_with_numeric += 1

        numeric_effect = (
            semantic_item.get(
                "semantic"
            )
            if semantic_item
            else None
        )

        current_numeric_effect = (
            determine_current_numeric_effect(
                index,
                applicability,
                semantic_item,
            )
        )

        evaluations.append(
            {
                "clause_index": (
                    index
                ),

                "law_name": (
                    clause.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    clause.get(
                        "rule_title"
                    )
                ),

                "paragraph": (
                    clause.get(
                        "paragraph"
                    )
                ),

                "item": (
                    clause.get(
                        "item"
                    )
                ),

                "subitem": (
                    clause.get(
                        "subitem"
                    )
                ),

                "category": (
                    clause.get(
                        "category"
                    )
                ),

                "zone_relevance": (
                    clause.get(
                        "zone_relevance"
                    )
                ),

                "applicability": (
                    applicability
                ),

                "applicability_reason": (
                    app.get(
                        "reason"
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                "conditions": (
                    condition_split[
                        "all"
                    ]
                ),

                "required_inputs": (
                    condition_split[
                        "required_inputs"
                    ]
                ),

                "blocked_by": (
                    condition_split[
                        "blocked_by"
                    ]
                ),

                "unknown_by": (
                    condition_split[
                        "unknown_by"
                    ]
                ),

                "numeric_effect": (
                    numeric_effect
                ),

                "numeric_effect_class": (
                    semantic_item.get(
                        "effect_class"
                    )
                    if semantic_item
                    else None
                ),

                "current_numeric_effect": (
                    current_numeric_effect
                ),

                "text": (
                    clause.get(
                        "text"
                    )
                ),

                "inherited_context": (
                    clause.get(
                        "inherited_context"
                    )
                ),
            }
        )

    # ========================================================
    # input requirements aggregation
    # ========================================================

    project_required = Counter()

    procedure_required = Counter()

    unresolved_site = Counter()

    for item in evaluations:

        for condition in item[
            "required_inputs"
        ]:

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            condition_type = safe_string(
                condition.get(
                    "type"
                )
            )

            if condition_type == (
                "PROJECT"
            ):

                project_required[
                    name
                ] += 1

            elif condition_type == (
                "PROCEDURE"
            ):

                procedure_required[
                    name
                ] += 1

        for condition in item[
            "unknown_by"
        ]:

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            if name:

                unresolved_site[
                    name
                ] += 1

    # ========================================================
    # active / conditional / unknown groups
    # ========================================================

    applicable_rules = [
        item
        for item in evaluations
        if item[
            "applicability"
        ]
        == "APPLICABLE"
    ]

    conditional_rules = [
        item
        for item in evaluations
        if item[
            "applicability"
        ]
        == "CONDITIONAL"
    ]

    unknown_rules = [
        item
        for item in evaluations
        if item[
            "applicability"
        ]
        == "UNKNOWN"
    ]

    not_applicable_rules = [
        item
        for item in evaluations
        if item[
            "applicability"
        ]
        == "NOT_APPLICABLE"
    ]

    # ========================================================
    # high-level result
    # ========================================================

    result_summary = {
        "confirmed_building_coverage_ratio": (
            confirmed_bcr
        ),

        "confirmed_floor_area_ratio": (
            confirmed_far
        ),

        "total_clauses": (
            len(
                evaluations
            )
        ),

        "applicable": (
            len(
                applicable_rules
            )
        ),

        "not_applicable": (
            len(
                not_applicable_rules
            )
        ),

        "conditional": (
            len(
                conditional_rules
            )
        ),

        "unknown": (
            len(
                unknown_rules
            )
        ),

        "numeric_clause_candidates": (
            clauses_with_numeric
        ),

        "rules_requiring_input": (
            clauses_with_required_input
        ),

        "rules_with_unknown_condition": (
            clauses_with_unknown
        ),

        "rules_with_false_blocker": (
            clauses_with_blocker
        ),
    }

    # ========================================================
    # validation
    # ========================================================

    total_count_ok = (
        len(
            evaluations
        )
        == 314
    )

    applicability_total_ok = (
        sum(
            applicability_counter.values()
        )
        ==
        len(
            evaluations
        )
    )

    numeric_ready = (
        numeric_data.get(
            "summary",
            {},
        ).get(
            "numeric_engine_status"
        )
        == "READY"
    )

    bcr_ok = (
        confirmed_bcr
        == 50.0
    )

    far_ok = (
        confirmed_far
        == 250.0
    )

    no_semantic_unresolved = (
        semantic_data.get(
            "summary",
            {},
        ).get(
            "semantic_unresolved"
        )
        == 0
    )

    validations = {

        "314 clauses 통합": (
            total_count_ok
        ),

        "applicability count 일치": (
            applicability_total_ok
        ),

        "numeric engine READY": (
            numeric_ready
        ),

        "confirmed BCR 50": (
            bcr_ok
        ),

        "confirmed FAR 250": (
            far_ok
        ),

        "numeric semantic unresolved 0": (
            no_semantic_unresolved
        ),

        "PROJECT profile 로드": (
            len(
                project_index
            )
            > 0
        ),

        "PROCEDURE profile 로드": (
            len(
                procedure_index
            )
            > 0
        ),

        "SITE condition snapshot 로드": (
            len(
                site_index
            )
            > 0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # final output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": (
            numeric_data.get(
                "site",
                {}
            )
        ),

        "confirmed_regulation": (
            confirmed_regulation
        ),

        "rule_evaluation_summary": (
            result_summary
        ),

        "input_requirements": {

            "project": [
                {
                    "name": name,
                    "affected_clause_count": (
                        count
                    ),

                    "profile_state": (
                        project_index.get(
                            name,
                            {},
                        ).get(
                            "state",
                            "UNSET",
                        )
                    ),
                }

                for name, count
                in project_required.most_common()
            ],

            "procedure": [
                {
                    "name": name,
                    "affected_clause_count": (
                        count
                    ),

                    "profile_state": (
                        procedure_index.get(
                            name,
                            {},
                        ).get(
                            "state",
                            "UNSET",
                        )
                    ),
                }

                for name, count
                in procedure_required.most_common()
            ],

            "unresolved_site_conditions": [
                {
                    "name": name,
                    "affected_clause_count": (
                        count
                    ),

                    "site_state": (
                        site_index.get(
                            name,
                            {},
                        ).get(
                            "status",
                            "UNKNOWN",
                        )
                    ),
                }

                for name, count
                in unresolved_site.most_common()
            ],
        },

        "rule_groups": {

            "applicable_clause_indexes": [
                item[
                    "clause_index"
                ]
                for item in applicable_rules
            ],

            "conditional_clause_indexes": [
                item[
                    "clause_index"
                ]
                for item in conditional_rules
            ],

            "unknown_clause_indexes": [
                item[
                    "clause_index"
                ]
                for item in unknown_rules
            ],

            "not_applicable_clause_indexes": [
                item[
                    "clause_index"
                ]
                for item in not_applicable_rules
            ],
        },

        "rules": (
            evaluations
        ),

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "SITE:",
        output.get(
            "site",
            {}
        ).get(
            "address"
        ),
    )

    print()

    print(
        "Confirmed BCR:",
        confirmed_bcr,
    )

    print(
        "Confirmed FAR:",
        confirmed_far,
    )

    print()

    print(
        "Rules:",
        len(
            evaluations
        ),
    )

    print(
        "APPLICABLE:",
        len(
            applicable_rules
        ),
    )

    print(
        "NOT_APPLICABLE:",
        len(
            not_applicable_rules
        ),
    )

    print(
        "CONDITIONAL:",
        len(
            conditional_rules
        ),
    )

    print(
        "UNKNOWN:",
        len(
            unknown_rules
        ),
    )

    print()

    print(
        "Numeric candidates:",
        clauses_with_numeric,
    )

    print(
        "Rules requiring input:",
        clauses_with_required_input,
    )

    print(
        "Rules with unknown condition:",
        clauses_with_unknown,
    )

    print()

    print(
        "PROJECT inputs:",
        len(
            project_required
        ),
    )

    print(
        "PROCEDURE inputs:",
        len(
            procedure_required
        ),
    )

    print(
        "Unresolved SITE conditions:",
        len(
            unresolved_site
        ),
    )

    print()

    if project_required:

        print(
            "Top PROJECT inputs:",
            project_required.most_common(
                8
            ),
        )

    if procedure_required:

        print(
            "PROCEDURE inputs:",
            procedure_required.most_common()
        )

    if unresolved_site:

        print(
            "Unresolved SITE:",
            unresolved_site.most_common()
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