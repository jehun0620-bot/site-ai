# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-1
Dynamic Active Numeric Context Probe

목표
======================================================================
PROJECT / PROCEDURE 입력 후 ACTIVE_CANDIDATE가 된 numeric clause를
정확히 분리하여 다음 단계의 실제 BCR/FAR 재계산 대상 후보를 만든다.

입력
======================================================================
project_procedure_dynamic_rule_evaluation.json
numeric_semantic_override_finalize.json
current_numeric_effect_candidate_finalize.json
base_numeric_regulation_hierarchy.json

핵심
======================================================================
Active numeric != 즉시 적용 numeric

다음 role을 구분해야 한다.

- DIRECT_RELAXATION
- NATIONAL_CEILING
- DISTRICT_PLAN_CEILING
- CONDITIONAL_PLAN_RANGE
- CONDITIONAL_STRENGTHENING
- SPECIAL_AREA_REFERENCE
- OTHER_EFFECT
- NON_EFFECT
- UNCLASSIFIED_ACTIVE

이번 단계에서는 실제 값을 최종 반영하지 않는다.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-4B-1 "
    "dynamic active numeric context probe"
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

DYNAMIC_PATH = (
    OUTPUT_DIR
    / "project_procedure_dynamic_rule_evaluation.json"
)

SEMANTIC_PATH = (
    OUTPUT_DIR
    / "numeric_semantic_override_finalize.json"
)

STATIC_ROLE_PATH = (
    OUTPUT_DIR
    / "current_numeric_effect_candidate_finalize.json"
)

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "dynamic_active_numeric_context_probe.json"
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


def safe_float(
    value: Any,
) -> float | None:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# semantic index
# ============================================================

def build_semantic_index(
    data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    for key in (
        "candidates",
        "calculable_now",
        "conditional_effects",
        "unknown_effects",
        "non_effects",
    ):

        for item in data.get(
            key,
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
# previous static role index
# ============================================================

def build_static_role_index(
    data: Dict[str, Any],
) -> Dict[int, Dict[str, Any]]:

    result = {}

    collections = [
        data.get(
            "apply_now",
            [],
        ),
        data.get(
            "deferred_effects",
            [],
        ),
        data.get(
            "candidates",
            [],
        ),
    ]

    # dict 형태도 대응
    for key in (
        "immediate_bcr_candidates",
        "immediate_far_candidates",
    ):

        value = data.get(
            key,
            [],
        )

        if isinstance(
            value,
            list,
        ):
            collections.append(
                value
            )

    for collection in collections:

        if not isinstance(
            collection,
            list,
        ):
            continue

        for item in collection:

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
# role classification
# ============================================================

def classify_role(
    rule: Dict[str, Any],
    semantic_item: Dict[str, Any],
    static_item: Dict[str, Any],
) -> Dict[str, Any]:

    clause_index = int(
        rule.get(
            "clause_index"
        )
    )

    title = safe_string(
        rule.get(
            "rule_title"
        )
    )

    text = safe_string(
        rule.get(
            "text"
        )
    )

    inherited = safe_string(
        rule.get(
            "inherited_context"
        )
    )

    context = (
        title
        + " "
        + text
        + " "
        + inherited
    )

    semantic = (
        rule.get(
            "numeric_effect"
        )
        or semantic_item.get(
            "semantic",
            {}
        )
        or {}
    )

    semantic_type = safe_string(
        semantic.get(
            "semantic_type"
        )
    )

    # --------------------------------------------------------
    # 기존 static classification이 있으면 최우선 재사용
    # --------------------------------------------------------

    static_role = (
        static_item.get(
            "final_role"
        )
        or static_item.get(
            "role"
        )
    )

    if static_role:

        return {
            "role": (
                static_role
            ),

            "source": (
                "STATIC_ROLE_REUSE"
            ),
        }

    # --------------------------------------------------------
    # known clause overrides
    # --------------------------------------------------------

    known_roles = {

        3: "CONDITIONAL_PLAN_RANGE",

        4: "DIRECT_RELAXATION",

        50: "DISTRICT_PLAN_CEILING",

        61: "NATIONAL_CEILING",

        189: "DIRECT_RELAXATION",

        220: "DISTRICT_PLAN_CEILING",

        233: "NATIONAL_CEILING",

        244: "SPECIAL_AREA_REFERENCE",

        251: "NON_EFFECT",

        262: "CONDITIONAL_STRENGTHENING",
    }

    if clause_index in known_roles:

        return {
            "role": (
                known_roles[
                    clause_index
                ]
            ),

            "source": (
                "KNOWN_CLAUSE_OVERRIDE"
            ),
        }

    # --------------------------------------------------------
    # NON EFFECT
    # --------------------------------------------------------

    if semantic_type == (
        "NON_EFFECT_THRESHOLD"
    ):

        return {
            "role": (
                "NON_EFFECT"
            ),

            "source": (
                "SEMANTIC_TYPE"
            ),
        }

    # --------------------------------------------------------
    # national ceiling
    # --------------------------------------------------------

    if (
        "용도지역에서의 건폐율"
        in title
        or "용도지역에서의 용적률"
        in title
    ):

        if (
            "최대한도"
            in context
            and "대통령령"
            in context
        ):

            return {
                "role": (
                    "NATIONAL_CEILING"
                ),

                "source": (
                    "TEXT_HEURISTIC"
                ),
            }

    # --------------------------------------------------------
    # strengthening
    # --------------------------------------------------------

    if (
        "강화"
        in title
        or "강화"
        in text
    ):

        return {
            "role": (
                "CONDITIONAL_STRENGTHENING"
            ),

            "source": (
                "TEXT_HEURISTIC"
            ),
        }

    # --------------------------------------------------------
    # district plan ceiling
    # --------------------------------------------------------

    if (
        "지구단위계획"
        in context
        and (
            "초과할 수 없다"
            in context
            or "범위에서"
            in context
        )
    ):

        return {
            "role": (
                "DISTRICT_PLAN_CEILING"
            ),

            "source": (
                "TEXT_HEURISTIC"
            ),
        }

    # --------------------------------------------------------
    # relaxation
    # --------------------------------------------------------

    if (
        "완화"
        in title
        or "완화"
        in text
    ):

        return {
            "role": (
                "DIRECT_RELAXATION"
            ),

            "source": (
                "TEXT_HEURISTIC"
            ),
        }

    return {
        "role": (
            "UNCLASSIFIED_ACTIVE"
        ),

        "source": (
            "UNRESOLVED"
        ),
    }


# ============================================================
# projected value
# ============================================================

def projected_value(
    rule: Dict[str, Any],
    base_bcr: float,
    base_far: float,
) -> Dict[str, Any]:

    semantic = (
        rule.get(
            "numeric_effect"
        )
        or {}
    )

    effects = rule.get(
        "effect_targets",
        [],
    )

    semantic_type = safe_string(
        semantic.get(
            "semantic_type"
        )
    )

    target = None
    base = None

    if (
        "building_coverage_ratio"
        in effects
    ):

        target = (
            "building_coverage_ratio"
        )

        base = (
            base_bcr
        )

    elif (
        "floor_area_ratio"
        in effects
    ):

        target = (
            "floor_area_ratio"
        )

        base = (
            base_far
        )

    if target is None:

        return {
            "target": None,
            "base": None,
            "projected_value": None,
            "status": (
                "NO_TARGET"
            ),
        }

    # --------------------------------------------------------
    # multiplier
    # --------------------------------------------------------

    if semantic_type in {
        "BASE_RATIO_MULTIPLIER",
        "MAX_LIMIT_MULTIPLIER",
    }:

        factor = safe_float(
            semantic.get(
                "factor"
            )
        )

        if factor is None:

            value = safe_float(
                semantic.get(
                    "value"
                )
            )

            if value is not None:

                factor = (
                    value
                    / 100.0
                )

        if factor is not None:

            return {
                "target": target,
                "base": base,
                "projected_value": (
                    base
                    * factor
                ),
                "status": (
                    "COMPARABLE"
                ),
            }

    # --------------------------------------------------------
    # absolute max
    # --------------------------------------------------------

    if semantic_type in {
        "ABSOLUTE_MAX",
        "ABSOLUTE_CEILING",
    }:

        value = safe_float(
            semantic.get(
                "value"
            )
        )

        return {
            "target": target,
            "base": base,
            "projected_value": (
                value
            ),
            "status": (
                "COMPARABLE"
                if value is not None
                else "VALUE_MISSING"
            ),
        }

    # --------------------------------------------------------
    # range
    # --------------------------------------------------------

    if semantic_type == (
        "RANGE"
    ):

        return {
            "target": target,
            "base": base,
            "projected_value": None,
            "status": (
                "PLAN_RANGE"
            ),
        }

    return {
        "target": target,
        "base": base,
        "projected_value": None,
        "status": (
            "SEMANTIC_NOT_DIRECTLY_COMPARABLE"
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    dynamic = load_json(
        DYNAMIC_PATH
    )

    semantic_data = load_json(
        SEMANTIC_PATH
    )

    static_data = load_json(
        STATIC_ROLE_PATH
    )

    base_data = load_json(
        BASE_PATH
    )

    rules = dynamic.get(
        "rules",
        [],
    )

    semantic_index = (
        build_semantic_index(
            semantic_data
        )
    )

    static_index = (
        build_static_role_index(
            static_data
        )
    )

    # ========================================================
    # base
    # ========================================================

    base_regulation = (
        base_data.get(
            "current_base_regulation",
            {}
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
    # active numeric
    # ========================================================

    active_rules = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        current = rule.get(
            "current_numeric_effect",
            {},
        )

        if (
            current.get(
                "status"
            )
            != "ACTIVE_CANDIDATE"
        ):
            continue

        index = int(
            rule.get(
                "clause_index"
            )
        )

        semantic_item = (
            semantic_index.get(
                index,
                {}
            )
        )

        static_item = (
            static_index.get(
                index,
                {}
            )
        )

        role_result = classify_role(
            rule,
            semantic_item,
            static_item,
        )

        comparison = projected_value(
            rule,
            base_bcr,
            base_far,
        )

        active_rules.append(
            {
                "clause_index": (
                    index
                ),

                "law_name": (
                    rule.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    rule.get(
                        "rule_title"
                    )
                ),

                "applicability": (
                    rule.get(
                        "applicability"
                    )
                ),

                "effect_targets": (
                    rule.get(
                        "effect_targets",
                        [],
                    )
                ),

                "numeric_effect": (
                    rule.get(
                        "numeric_effect"
                    )
                ),

                "role": (
                    role_result[
                        "role"
                    ]
                ),

                "role_source": (
                    role_result[
                        "source"
                    ]
                ),

                "comparison": (
                    comparison
                ),

                "conditions": (
                    rule.get(
                        "conditions",
                        [],
                    )
                ),

                "text": (
                    rule.get(
                        "text"
                    )
                ),
            }
        )

    # ========================================================
    # role groups
    # ========================================================

    role_counter = Counter(
        item[
            "role"
        ]
        for item
        in active_rules
    )

    immediate_candidates = [
        item
        for item
        in active_rules
        if item[
            "role"
        ]
        == "DIRECT_RELAXATION"
        and item[
            "comparison"
        ][
            "status"
        ]
        == "COMPARABLE"
    ]

    reference_only = [
        item
        for item
        in active_rules
        if item[
            "role"
        ]
        in {
            "NATIONAL_CEILING",
            "DISTRICT_PLAN_CEILING",
            "SPECIAL_AREA_REFERENCE",
            "NON_EFFECT",
        }
    ]

    strengthening = [
        item
        for item
        in active_rules
        if item[
            "role"
        ]
        == "CONDITIONAL_STRENGTHENING"
    ]

    unresolved_roles = [
        item
        for item
        in active_rules
        if item[
            "role"
        ]
        == "UNCLASSIFIED_ACTIVE"
    ]

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "active numeric 12": (
            len(
                active_rules
            )
            == 12
        ),

        "base BCR 50": (
            base_bcr
            == 50.0
        ),

        "base FAR 250": (
            base_far
            == 250.0
        ),

        "all active applicable": (
            all(
                item[
                    "applicability"
                ]
                == "APPLICABLE"

                for item
                in active_rules
            )
        ),

        "role classification complete": (
            len(
                unresolved_roles
            )
            == 0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "input": (
            dynamic.get(
                "input",
                {}
            )
        ),

        "base": {
            "building_coverage_ratio": (
                base_bcr
            ),

            "floor_area_ratio": (
                base_far
            ),
        },

        "summary": {
            "active_numeric_count": (
                len(
                    active_rules
                )
            ),

            "roles": (
                dict(
                    role_counter
                )
            ),

            "immediate_candidate_count": (
                len(
                    immediate_candidates
                )
            ),

            "reference_only_count": (
                len(
                    reference_only
                )
            ),

            "strengthening_count": (
                len(
                    strengthening
                )
            ),

            "unclassified_count": (
                len(
                    unresolved_roles
                )
            ),
        },

        "immediate_candidates": (
            immediate_candidates
        ),

        "reference_only": (
            reference_only
        ),

        "strengthening": (
            strengthening
        ),

        "unclassified": (
            unresolved_roles
        ),

        "active_rules": (
            active_rules
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
        "Base BCR:",
        base_bcr,
    )

    print(
        "Base FAR:",
        base_far,
    )

    print()

    print(
        "Active numeric:",
        len(
            active_rules
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
        "Immediate candidates:",
        len(
            immediate_candidates
        ),
    )

    for item in immediate_candidates:

        print(
            f"- clause={item['clause_index']} "
            f"| {item['rule_title']} "
            f"| target={item['comparison']['target']} "
            f"| projected={item['comparison']['projected_value']}"
        )

    print()

    print(
        "Reference only:",
        len(
            reference_only
        ),
    )

    print(
        "Strengthening:",
        len(
            strengthening
        ),
    )

    print(
        "Unclassified:",
        len(
            unresolved_roles
        ),
    )

    if unresolved_roles:

        print()

        for item in unresolved_roles:

            print(
                f"[UNCLASSIFIED] "
                f"clause={item['clause_index']} "
                f"| {item['rule_title']} "
                f"| semantic={item['numeric_effect']}"
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