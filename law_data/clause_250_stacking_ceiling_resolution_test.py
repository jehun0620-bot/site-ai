# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-2E
Clause 250 stacking ceiling resolution

목표
======================================================================
Residual numeric clause 250의 역할을 최종 확정한다.

법적 구조
======================================================================
국토의 계획 및 이용에 관한 법률 제78조제7항

여러 법률에 따른 용적률 완화 규정은 중첩 적용할 수 있으나
지역 유형에 따라 중첩 상한이 다르다.

1. 지구단위계획구역
   -> 제52조제3항에 따라 지구단위계획으로 정하는 범위

2. 지구단위계획구역 외의 지역
   -> 해당 용도지역별 용적률 최대한도의 120% 이하

clause 250
======================================================================
제78조제7항제2호

"지구단위계획구역 외의 지역:
 해당 용도지역별 용적률 최대한도의 120퍼센트 이하"

따라서:
- 직접 FAR 완화가 아님
- base FAR × 1.2 계산식이 아님
- 여러 완화 규정 중첩 시 적용되는 ceiling
- 현재 SITE는 지구단위계획 TRUE이므로 제2호 branch는 불일치

최종 role
======================================================================
STACKING_CEILING_OUTSIDE_DISTRICT_PLAN

현재 SITE:
NOT_APPLICABLE / HIGH
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-4B-2E "
    "clause 250 stacking ceiling resolution"
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

RESIDUAL_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_residual_role_probe.json"
)

SITE_COMPLETE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "clause_250_stacking_ceiling_resolution.json"
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


# ============================================================
# main
# ============================================================

def main() -> int:

    residual = load_json(
        RESIDUAL_PATH
    )

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    # ========================================================
    # 1. residual clause 250
    # ========================================================

    residual_rules = (
        residual.get(
            "residual_rules",
            [],
        )
    )

    clause_250 = next(
        (
            item
            for item
            in residual_rules
            if int(
                item.get(
                    "clause_index",
                    -1,
                )
            )
            == 250
        ),
        None,
    )

    if clause_250 is None:

        raise ValueError(
            "Residual clause 250을 찾을 수 없음"
        )

    text = str(
        clause_250.get(
            "text",
            ""
        )
    )

    inherited = str(
        clause_250.get(
            "inherited_context",
            ""
        )
    )

    # ========================================================
    # 2. SITE 지구단위계획 상태
    # ========================================================

    site_rules = (
        site_complete.get(
            "rules",
            [],
        )
    )

    district_plan_states = []

    for rule in site_rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        for condition in rule.get(
            "conditions",
            [],
        ):

            if not isinstance(
                condition,
                dict,
            ):
                continue

            if (
                condition.get(
                    "name"
                )
                != "지구단위계획"
            ):
                continue

            district_plan_states.append(
                condition.get(
                    "state"
                )
            )

    district_plan_true = (
        "TRUE"
        in district_plan_states
    )

    # ========================================================
    # 3. legal text checks
    # ========================================================

    outside_district_plan_text = (
        "지구단위계획구역 외의 지역"
        in text
    )

    stacking_language = (
        "중첩하여 적용"
        in inherited
    )

    ceiling_language = (
        "최대한도의 120퍼센트 이하"
        in text
    )

    # ========================================================
    # 4. branch state
    # ========================================================

    outside_district_plan_condition = {
        "name": (
            "지구단위계획구역외지역"
        ),

        "type": (
            "SITE"
        ),

        "state": (
            "FALSE"
            if district_plan_true
            else "UNKNOWN"
        ),

        "confidence": (
            "HIGH"
            if district_plan_true
            else "NONE"
        ),
    }

    # ========================================================
    # 5. semantic correction
    # ========================================================

    corrected_semantic = {
        "semantic_type": (
            "STACKING_CEILING_MULTIPLIER"
        ),

        "value": (
            120.0
        ),

        "factor": (
            1.2
        ),

        "unit": (
            "percent_of_statutory_max"
        ),

        "formula": (
            "statutory_zone_max * 1.2"
        ),

        "direct_base_effect": (
            False
        ),

        "requires_existing_relaxation_stack": (
            True
        ),

        "confidence": (
            "HIGH"
        ),
    }

    # ========================================================
    # 6. role
    # ========================================================

    role = (
        "STACKING_CEILING_OUTSIDE_DISTRICT_PLAN"
    )

    if district_plan_true:

        applicability = (
            "NOT_APPLICABLE"
        )

        allow_numeric_effect = (
            False
        )

        reason = (
            "clause 250은 용적률 완화 자체가 아니라 "
            "복수 완화규정을 중첩 적용할 때의 상한이며, "
            "제78조제7항제2호는 지구단위계획구역 외의 "
            "지역에만 적용된다. 현재 SITE는 "
            "지구단위계획구역이므로 해당 branch는 적용되지 않는다."
        )

    else:

        applicability = (
            "CONDITIONAL"
        )

        allow_numeric_effect = (
            False
        )

        reason = (
            "지구단위계획구역 외 여부 및 실제 중첩되는 "
            "용적률 완화규정 존재 여부 확인 필요"
        )

    # ========================================================
    # 7. validations
    # ========================================================

    validations = {

        "residual clause 250": (
            clause_250.get(
                "clause_index"
            )
            == 250
        ),

        "outside district-plan text": (
            outside_district_plan_text
        ),

        "stacking language": (
            stacking_language
        ),

        "120 ceiling language": (
            ceiling_language
        ),

        "SITE district plan TRUE": (
            district_plan_true
        ),

        "outside branch FALSE": (
            outside_district_plan_condition[
                "state"
            ]
            == "FALSE"
        ),

        "role stacking ceiling": (
            role
            == (
                "STACKING_CEILING_OUTSIDE_DISTRICT_PLAN"
            )
        ),

        "not direct numeric effect": (
            corrected_semantic[
                "direct_base_effect"
            ]
            is False
        ),

        "clause250 NOT_APPLICABLE": (
            applicability
            == "NOT_APPLICABLE"
        ),

        "numeric inactive": (
            allow_numeric_effect
            is False
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 8. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "clause": {
            "clause_index": (
                250
            ),

            "law_name": (
                clause_250.get(
                    "law_name"
                )
            ),

            "rule_title": (
                clause_250.get(
                    "rule_title"
                )
            ),

            "path": (
                clause_250.get(
                    "path"
                )
            ),

            "original_numeric_effect": (
                clause_250.get(
                    "numeric_effect"
                )
            ),

            "text": (
                text
            ),

            "inherited_context": (
                inherited
            ),
        },

        "branch_condition": (
            outside_district_plan_condition
        ),

        "resolution": {
            "role": (
                role
            ),

            "applicability": (
                applicability
            ),

            "confidence": (
                "HIGH"
            ),

            "allow_numeric_effect": (
                allow_numeric_effect
            ),

            "corrected_numeric_semantic": (
                corrected_semantic
            ),

            "reason": (
                reason
            ),
        },

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
        "Clause:",
        250,
    )

    print(
        "SITE district plan:",
        district_plan_true,
    )

    print(
        "Required branch:",
        "지구단위계획구역 외의 지역",
    )

    print(
        "Branch match:",
        (
            outside_district_plan_condition[
                "state"
            ]
            == "TRUE"
        ),
    )

    print()

    print(
        "Role:",
        role,
    )

    print(
        "Applicability:",
        applicability,
    )

    print(
        "Direct numeric effect:",
        corrected_semantic[
            "direct_base_effect"
        ],
    )

    print(
        "Numeric active:",
        allow_numeric_effect,
    )

    print()

    print(
        "Original semantic:",
        clause_250.get(
            "numeric_effect"
        ),
    )

    print(
        "Corrected semantic:",
        corrected_semantic,
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