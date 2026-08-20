# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-2C
Dynamic Numeric Final Guard Recheck

목표
======================================================================
branch-local condition overlay까지 반영된 rules에 대해
기존 SITE / numeric guard를 최종 재적용한다.

검증 대상
======================================================================
clause 4
    BCR 60%
    upper branch NOT_APPLICABLE

clause 189
    FAR 300%
    방재지구 FALSE / HIGH

clause 205
    FAR 325%
    서울조례 제48조 7~10호 지역 FALSE

추가 정합성
======================================================================
서울도심:
    이미 SITE 단계에서 FALSE / HIGH 확정
    branch-local overlay에서 UNKNOWN으로 새로 생성되었다면
    FALSE / HIGH로 교정

최종 목표
======================================================================
현재 scenario:

PROJECT:
    공동주택 = TRUE

PROCEDURE:
    도시계획위원회심의 = TRUE

에서 즉시 적용할 numeric relaxation이 0인지 확인한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-4B-2C "
    "dynamic numeric final guard recheck"
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

OVERLAY_PATH = (
    OUTPUT_DIR
    / "numeric_branch_local_condition_overlay.json"
)

UPPER_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)

DISASTER_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_resolution.json"
)

CLAUSE_205_PATH = (
    OUTPUT_DIR
    / "clause_205_tourism_branch_guard.json"
)

SEOUL_DOWNTOWN_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
)

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_final_guard_recheck.json"
)


# ============================================================
# util
# ============================================================

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


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# condition refresh
# ============================================================

def refresh_condition_groups(
    rule: Dict[str, Any],
) -> None:

    conditions = rule.get(
        "conditions",
        [],
    )

    rule["required_inputs"] = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNSET"
    ]

    rule["blocked_by"] = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "FALSE"
    ]

    rule["unknown_by"] = [
        item
        for item in conditions
        if isinstance(
            item,
            dict,
        )
        and item.get(
            "state"
        )
        == "UNKNOWN"
    ]


# ============================================================
# applicability recalc
# ============================================================

def recalculate_applicability(
    rule: Dict[str, Any],
) -> Dict[str, str]:

    blocked = rule.get(
        "blocked_by",
        [],
    )

    unknown = rule.get(
        "unknown_by",
        [],
    )

    required = rule.get(
        "required_inputs",
        [],
    )

    if blocked:

        return {
            "applicability": (
                "NOT_APPLICABLE"
            ),

            "reason": (
                "필수조건 FALSE: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in blocked
                )
            ),
        }

    if unknown:

        return {
            "applicability": (
                "UNKNOWN"
            ),

            "reason": (
                "필수조건 미확정: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in unknown
                )
            ),
        }

    if required:

        return {
            "applicability": (
                "CONDITIONAL"
            ),

            "reason": (
                "추가 입력 필요: "
                + ", ".join(
                    safe_string(
                        item.get(
                            "name"
                        )
                    )
                    for item
                    in required
                )
            ),
        }

    if (
        rule.get(
            "zone_relevance"
        )
        == "OTHER_ZONE"
    ):

        return {
            "applicability": (
                "NOT_APPLICABLE"
            ),

            "reason": (
                "현재 SITE 용도지역 불일치"
            ),
        }

    return {
        "applicability": (
            "APPLICABLE"
        ),

        "reason": (
            "모든 필수조건 충족"
        ),
    }


# ============================================================
# numeric refresh
# ============================================================

def refresh_numeric_effect(
    rule: Dict[str, Any],
) -> None:

    numeric_effect = rule.get(
        "numeric_effect"
    )

    if not numeric_effect:
        return

    applicability = rule.get(
        "applicability"
    )

    if applicability == (
        "NOT_APPLICABLE"
    ):

        status = "INACTIVE"

    elif applicability == (
        "CONDITIONAL"
    ):

        status = "POTENTIAL_CONDITIONAL"

    elif applicability == (
        "UNKNOWN"
    ):

        status = "POTENTIAL_UNKNOWN"

    else:

        status = "ACTIVE_CANDIDATE"

    rule[
        "current_numeric_effect"
    ] = {
        "status": status,

        "effect_class": (
            rule.get(
                "numeric_effect_class"
            )
        ),

        "semantic": (
            numeric_effect
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    overlay = load_json(
        OVERLAY_PATH
    )

    upper = load_json(
        UPPER_PATH
    )

    disaster = load_json(
        DISASTER_PATH
    )

    clause_205_guard = load_json(
        CLAUSE_205_PATH
    )

    downtown = load_json(
        SEOUL_DOWNTOWN_PATH
    )

    base = load_json(
        BASE_PATH
    )

    rules = copy.deepcopy(
        overlay.get(
            "rules",
            [],
        )
    )

    # ========================================================
    # 1. SITE resolution registry
    # ========================================================

    downtown_condition = (
        downtown.get(
            "condition",
            {},
        )
    )

    downtown_status = (
        downtown_condition.get(
            "status"
        )
    )

    downtown_confidence = (
        downtown_condition.get(
            "confidence"
        )
    )

    site_registry = {

        "서울도심": {
            "state": (
                downtown_status
            ),

            "confidence": (
                downtown_confidence
            ),

            "source": (
                "SEOUL_DOWNTOWN_CONDITION_RESOLUTION"
            ),
        },
    }

    # ========================================================
    # 2. repair known SITE predicates
    # ========================================================

    repaired_conditions = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        changed = False

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            name = safe_string(
                condition.get(
                    "name"
                )
            )

            registry = (
                site_registry.get(
                    name
                )
            )

            if not registry:
                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            if (
                previous_state
                == registry[
                    "state"
                ]
            ):
                continue

            condition[
                "state"
            ] = (
                registry[
                    "state"
                ]
            )

            condition[
                "confidence"
            ] = (
                registry[
                    "confidence"
                ]
            )

            condition[
                "source"
            ] = (
                registry[
                    "source"
                ]
            )

            repaired_conditions.append(
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "condition": (
                        name
                    ),

                    "before": (
                        previous_state
                    ),

                    "after": (
                        registry[
                            "state"
                        ]
                    ),
                }
            )

            changed = True

        if changed:

            refresh_condition_groups(
                rule
            )

            result = (
                recalculate_applicability(
                    rule
                )
            )

            rule[
                "applicability"
            ] = (
                result[
                    "applicability"
                ]
            )

            rule[
                "applicability_reason"
            ] = (
                result[
                    "reason"
                ]
            )

            refresh_numeric_effect(
                rule
            )

    # ========================================================
    # 3. verified numeric guards
    # ========================================================

    clause_4_resolution = (
        upper.get(
            "resolutions",
            {},
        ).get(
            "clause_4",
            {},
        ).get(
            "resolution"
        )
    )

    disaster_status = (
        disaster.get(
            "current_condition",
            {},
        ).get(
            "status"
        )
    )

    disaster_confidence = (
        disaster.get(
            "current_condition",
            {},
        ).get(
            "confidence"
        )
    )

    clause_189_resolution = (
        disaster.get(
            "numeric_effect",
            {},
        ).get(
            "resolution"
        )
    )

    clause_205_resolution = (
        clause_205_guard.get(
            "resolution",
            {},
        ).get(
            "applicability"
        )
    )

    verified_guards = {

        4: {
            "resolution": (
                clause_4_resolution
            ),

            "allow_numeric": (
                clause_4_resolution
                == "CONFIRMED"
            ),

            "reason": (
                "상위 시행령 branch 불일치"
            ),
        },

        189: {
            "resolution": (
                clause_189_resolution
            ),

            "allow_numeric": (
                clause_189_resolution
                == "CONFIRMED"
                and disaster_status
                == "TRUE"
            ),

            "reason": (
                "방재지구 FALSE"
            ),
        },

        205: {
            "resolution": (
                clause_205_resolution
            ),

            "allow_numeric": (
                clause_205_resolution
                == "APPLICABLE"
            ),

            "reason": (
                "서울조례 제48조 7~10호 지역 branch 불일치"
            ),
        },
    }

    # ========================================================
    # 4. active numeric before final guards
    # ========================================================

    active_before = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        if (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
            == "ACTIVE_CANDIDATE"
        ):

            active_before.append(
                rule
            )

    # ========================================================
    # 5. final guard apply
    # ========================================================

    excluded = []

    retained = []

    for rule in active_before:

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        guard = (
            verified_guards.get(
                clause_index
            )
        )

        if (
            guard
            and not guard[
                "allow_numeric"
            ]
        ):

            excluded.append(
                {
                    "clause_index": (
                        clause_index
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),

                    "guard": (
                        guard
                    ),
                }
            )

            continue

        retained.append(
            rule
        )

    # ========================================================
    # 6. immediate relaxation classification
    #
    # known roles from previous work
    # ========================================================

    DIRECT_RELAXATION_CLAUSES = {
        4,
        189,
        205,
    }

    immediate_relaxations = [
        rule
        for rule
        in retained
        if int(
            rule.get(
                "clause_index"
            )
        )
        in DIRECT_RELAXATION_CLAUSES
    ]

    # ========================================================
    # 7. active role preview
    # ========================================================

    role_counter = Counter()

    for rule in retained:

        index = int(
            rule.get(
                "clause_index"
            )
        )

        title = safe_string(
            rule.get(
                "rule_title"
            )
        )

        if index in {
            61,
            233,
        }:

            role = (
                "NATIONAL_CEILING"
            )

        elif index in {
            50,
            220,
        }:

            role = (
                "DISTRICT_PLAN_CEILING"
            )

        elif index in {
            3,
        }:

            role = (
                "CONDITIONAL_PLAN_RANGE"
            )

        elif index in {
            121,
            262,
        }:

            role = (
                "CONDITIONAL_STRENGTHENING"
            )

        elif index in {
            244,
        }:

            role = (
                "SPECIAL_AREA_REFERENCE"
            )

        elif (
            "완화"
            in title
        ):

            role = (
                "OTHER_ACTIVE_RELAXATION"
            )

        else:

            role = (
                "OTHER_ACTIVE"
            )

        role_counter[
            role
        ] += 1

    # ========================================================
    # 8. base
    # ========================================================

    base_regulation = (
        base.get(
            "current_base_regulation",
            {},
        )
    )

    base_bcr = float(
        base_regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value",
            50.0,
        )
    )

    base_far = float(
        base_regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value",
            250.0,
        )
    )

    # ========================================================
    # 9. confirmed result for this scenario
    # ========================================================

    if immediate_relaxations:

        numeric_resolution = (
            "RECALC_REQUIRED"
        )

        confirmed_bcr = None
        confirmed_far = None

    else:

        numeric_resolution = (
            "BASE_VALUES_RETAINED"
        )

        confirmed_bcr = (
            base_bcr
        )

        confirmed_far = (
            base_far
        )

    # ========================================================
    # 10. validations
    # ========================================================

    excluded_indexes = {
        item[
            "clause_index"
        ]
        for item
        in excluded
    }

    validations = {

        "rules 314": (
            len(
                rules
            )
            == 314
        ),

        "서울도심 resolution FALSE": (
            downtown_status
            == "FALSE"
            and downtown_confidence
            == "HIGH"
        ),

        "서울도심 repair occurred": (
            any(
                item[
                    "condition"
                ]
                == "서울도심"

                for item
                in repaired_conditions
            )
        ),

        "clause4 guard inactive": (
            4
            in excluded_indexes
        ),

        "clause189 guard inactive": (
            189
            in excluded_indexes
        ),

        "clause205 guard inactive": (
            (
                205
                in excluded_indexes
            )
            or not any(
                int(
                    rule.get(
                        "clause_index"
                    )
                )
                == 205
                for rule
                in active_before
            )
        ),

        "immediate relaxation 0": (
            len(
                immediate_relaxations
            )
            == 0
        ),

        "numeric base retained": (
            numeric_resolution
            == "BASE_VALUES_RETAINED"
        ),

        "confirmed BCR 50": (
            confirmed_bcr
            == 50.0
        ),

        "confirmed FAR 250": (
            confirmed_far
            == 250.0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 11. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "input": (
            overlay.get(
                "input",
                {}
            )
        ),

        "site_condition_repair": {
            "registry": (
                site_registry
            ),

            "repaired_conditions": (
                repaired_conditions
            ),
        },

        "verified_numeric_guards": (
            verified_guards
        ),

        "numeric": {
            "active_before_guard": (
                len(
                    active_before
                )
            ),

            "excluded_by_guard": (
                excluded
            ),

            "active_after_guard": (
                len(
                    retained
                )
            ),

            "active_roles": (
                dict(
                    role_counter
                )
            ),

            "immediate_relaxation_count": (
                len(
                    immediate_relaxations
                )
            ),

            "immediate_relaxations": [
                {
                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    "rule_title": (
                        rule.get(
                            "rule_title"
                        )
                    ),
                }

                for rule
                in immediate_relaxations
            ],
        },

        "scenario_result": {
            "numeric_resolution": (
                numeric_resolution
            ),

            "building_coverage_ratio": (
                confirmed_bcr
            ),

            "floor_area_ratio": (
                confirmed_far
            ),
        },

        "rules": (
            rules
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
    # console
    # ========================================================

    print(
        "SITE condition repairs:",
        len(
            repaired_conditions
        ),
    )

    for item in repaired_conditions:

        print(
            f"- clause={item['clause_index']} "
            f"| {item['condition']} "
            f"| {item['before']} -> {item['after']}"
        )

    print()

    print(
        "Active numeric before guard:",
        len(
            active_before
        ),
    )

    print(
        "Excluded:",
        len(
            excluded
        ),
    )

    for item in excluded:

        print(
            f"- clause={item['clause_index']} "
            f"| {item['rule_title']} "
            f"| {item['guard']['resolution']}"
        )

    print()

    print(
        "Active numeric after guard:",
        len(
            retained
        ),
    )

    print(
        "Roles:",
        dict(
            role_counter
        ),
    )

    print()

    print(
        "Immediate relaxation:",
        len(
            immediate_relaxations
        ),
    )

    print()

    print(
        "Numeric resolution:",
        numeric_resolution,
    )

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