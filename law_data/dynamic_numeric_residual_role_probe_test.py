# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-2D
Dynamic Numeric Residual Active Role Probe

목표
======================================================================
4B-2C 이후 verified numeric guard를 통과한 active numeric 9개를
전부 명시적으로 출력하고, OTHER_ACTIVE 1개를 찾아 실제 역할을
확인한다.

중요
======================================================================
이번 단계에서는 숫자를 적용하지 않는다.

확인할 것:
1. active after guard = 9
2. 각 clause index / law / title / path / numeric semantic
3. 기존 known role에 속하지 않는 residual clause 확인
4. residual clause의 text / inherited context 출력
5. 실제 BCR/FAR 계산효과인지 여부를 다음 단계 판단용으로 저장
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-4B-2D "
    "dynamic numeric residual role probe"
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

FINAL_GUARD_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_final_guard_recheck.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_residual_role_probe.json"
)


# ============================================================
# KNOWN ROLE TABLE
# ============================================================

KNOWN_ROLES = {

    # --------------------------------------------------------
    # plan range
    # --------------------------------------------------------

    3: (
        "CONDITIONAL_PLAN_RANGE"
    ),

    # --------------------------------------------------------
    # district-unit-plan ceilings
    # --------------------------------------------------------

    50: (
        "DISTRICT_PLAN_CEILING"
    ),

    220: (
        "DISTRICT_PLAN_CEILING"
    ),

    # --------------------------------------------------------
    # national ceilings
    # --------------------------------------------------------

    61: (
        "NATIONAL_CEILING"
    ),

    233: (
        "NATIONAL_CEILING"
    ),

    # --------------------------------------------------------
    # conditional strengthening
    # --------------------------------------------------------

    121: (
        "CONDITIONAL_STRENGTHENING"
    ),

    262: (
        "CONDITIONAL_STRENGTHENING"
    ),

    # --------------------------------------------------------
    # special-area reference
    # --------------------------------------------------------

    244: (
        "SPECIAL_AREA_REFERENCE"
    ),

    # --------------------------------------------------------
    # already verified direct relaxation guards
    # --------------------------------------------------------

    4: (
        "DIRECT_RELAXATION"
    ),

    189: (
        "DIRECT_RELAXATION"
    ),

    205: (
        "DIRECT_RELAXATION"
    ),
}


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

    return str(
        value
    ).strip()


# ============================================================
# semantic hints
# ============================================================

def detect_language_hints(
    text: str,
    inherited: str,
) -> List[str]:

    context = (
        safe_string(
            inherited
        )
        + " "
        + safe_string(
            text
        )
    )

    hints = []

    if "완화" in context:

        hints.append(
            "RELAXATION_LANGUAGE"
        )

    if "강화" in context:

        hints.append(
            "STRENGTHENING_LANGUAGE"
        )

    if "최대한도" in context:

        hints.append(
            "MAX_LIMIT_LANGUAGE"
        )

    if "초과할 수 없다" in context:

        hints.append(
            "CEILING_LANGUAGE"
        )

    if "이하" in context:

        hints.append(
            "UPPER_LIMIT_LANGUAGE"
        )

    if "이상" in context:

        hints.append(
            "LOWER_LIMIT_LANGUAGE"
        )

    if "지구단위계획" in context:

        hints.append(
            "DISTRICT_UNIT_PLAN"
        )

    if "용도지역" in context:

        hints.append(
            "ZONE_REFERENCE"
        )

    if "개발밀도관리구역" in context:

        hints.append(
            "DEVELOPMENT_DENSITY"
        )

    if "학교이적지" in context:

        hints.append(
            "SCHOOL_RELOCATION"
        )

    if "대통령령으로 정하는" in context:

        hints.append(
            "DELEGATED_STANDARD"
        )

    return hints


# ============================================================
# preliminary residual classification
# ============================================================

def classify_residual(
    rule: Dict[str, Any],
) -> Dict[str, Any]:

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
        inherited
        + " "
        + text
    )

    semantic = (
        rule.get(
            "numeric_effect"
        )
        or {}
    )

    semantic_type = safe_string(
        semantic.get(
            "semantic_type"
        )
    )

    effects = (
        rule.get(
            "effect_targets",
            []
        )
    )

    # --------------------------------------------------------
    # explicit ceiling/reference
    # --------------------------------------------------------

    if (
        "최대한도"
        in context
        and (
            "대통령령으로 정하는"
            in context
            or "조례로 정한다"
            in context
        )
    ):

        return {
            "candidate_role": (
                "REFERENCE_OR_CEILING"
            ),

            "immediate_effect_possible": (
                False
            ),

            "reason": (
                "용도지역 최대한도 또는 위임기준을 정하는 "
                "상위 기준 조문일 가능성이 높음"
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
            "candidate_role": (
                "STRENGTHENING"
            ),

            "immediate_effect_possible": (
                False
            ),

            "reason": (
                "강화 조문으로 별도 적용조건 확인 필요"
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
            "candidate_role": (
                "POTENTIAL_RELAXATION"
            ),

            "immediate_effect_possible": (
                True
            ),

            "reason": (
                "완화 언어가 직접 존재하므로 branch 적용조건 "
                "추가 검증 필요"
            ),
        }

    # --------------------------------------------------------
    # absolute / multiplier numeric but no relaxation language
    # --------------------------------------------------------

    if semantic_type in {
        "ABSOLUTE_MAX",
        "ABSOLUTE_CEILING",
        "BASE_RATIO_MULTIPLIER",
        "MAX_LIMIT_MULTIPLIER",
    }:

        return {
            "candidate_role": (
                "NUMERIC_REFERENCE_OR_EFFECT"
            ),

            "immediate_effect_possible": (
                False
            ),

            "reason": (
                "숫자 semantic은 존재하지만 완화 언어가 없어 "
                "직접 효과인지 기준/참조인지 문맥 검증 필요"
            ),
        }

    return {
        "candidate_role": (
            "UNRESOLVED"
        ),

        "immediate_effect_possible": (
            False
        ),

        "reason": (
            "자동 role 판정 불가"
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    final_guard = load_json(
        FINAL_GUARD_PATH
    )

    rules = (
        final_guard.get(
            "rules",
            []
        )
    )

    verified_guards = (
        final_guard.get(
            "verified_numeric_guards",
            {}
        )
    )

    # JSON 저장 시 int key가 str로 바뀔 수 있으므로 대응
    blocked_indexes = set()

    for key, value in (
        verified_guards.items()
    ):

        try:

            clause_index = int(
                key
            )

        except (
            TypeError,
            ValueError,
        ):

            continue

        if not isinstance(
            value,
            dict,
        ):
            continue

        if (
            value.get(
                "allow_numeric"
            )
            is False
        ):

            blocked_indexes.add(
                clause_index
            )

    # ========================================================
    # active before guards reconstructed
    # ========================================================

    active_before = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):
            continue

        if not rule.get(
            "numeric_effect"
        ):
            continue

        status = (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
        )

        if status != (
            "ACTIVE_CANDIDATE"
        ):
            continue

        active_before.append(
            rule
        )

    # ========================================================
    # apply verified guards
    # ========================================================

    retained = []

    for rule in active_before:

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        if (
            clause_index
            in blocked_indexes
        ):

            continue

        retained.append(
            rule
        )

    # ========================================================
    # explicit role
    # ========================================================

    evaluated = []

    residual = []

    for rule in retained:

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        known_role = (
            KNOWN_ROLES.get(
                clause_index
            )
        )

        hints = detect_language_hints(
            safe_string(
                rule.get(
                    "text"
                )
            ),
            safe_string(
                rule.get(
                    "inherited_context"
                )
            ),
        )

        item = {
            "clause_index": (
                clause_index
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

            "path": {
                "paragraph": (
                    rule.get(
                        "paragraph"
                    )
                ),

                "item": (
                    rule.get(
                        "item"
                    )
                ),

                "subitem": (
                    rule.get(
                        "subitem"
                    )
                ),
            },

            "applicability": (
                rule.get(
                    "applicability"
                )
            ),

            "effect_targets": (
                rule.get(
                    "effect_targets",
                    []
                )
            ),

            "numeric_effect": (
                rule.get(
                    "numeric_effect"
                )
            ),

            "known_role": (
                known_role
            ),

            "language_hints": (
                hints
            ),

            "conditions": (
                rule.get(
                    "conditions",
                    []
                )
            ),

            "text": (
                rule.get(
                    "text"
                )
            ),

            "inherited_context": (
                rule.get(
                    "inherited_context"
                )
            ),
        }

        if known_role:

            item[
                "role_status"
            ] = (
                "KNOWN"
            )

            evaluated.append(
                item
            )

            continue

        residual_classification = (
            classify_residual(
                rule
            )
        )

        item[
            "role_status"
        ] = (
            "RESIDUAL"
        )

        item[
            "residual_classification"
        ] = (
            residual_classification
        )

        evaluated.append(
            item
        )

        residual.append(
            item
        )

    # ========================================================
    # residual risk
    # ========================================================

    residual_immediate_risk = [
        item
        for item
        in residual
        if (
            item.get(
                "residual_classification",
                {},
            ).get(
                "immediate_effect_possible"
            )
            is True
        )
    ]

    # ========================================================
    # validations
    # ========================================================

    validations = {

        "active before guard 11": (
            len(
                active_before
            )
            == 11
        ),

        "blocked guards include 4": (
            4
            in blocked_indexes
        ),

        "blocked guards include 189": (
            189
            in blocked_indexes
        ),

        "active after guard 9": (
            len(
                retained
            )
            == 9
        ),

        "residual role count 1": (
            len(
                residual
            )
            == 1
        ),

        "residual clause identified": (
            len(
                residual
            )
            == 1
            and residual[
                0
            ].get(
                "clause_index"
            )
            is not None
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

        "summary": {
            "active_before_guard": (
                len(
                    active_before
                )
            ),

            "blocked_indexes": (
                sorted(
                    blocked_indexes
                )
            ),

            "active_after_guard": (
                len(
                    retained
                )
            ),

            "known_role_count": (
                len(
                    retained
                )
                - len(
                    residual
                )
            ),

            "residual_role_count": (
                len(
                    residual
                )
            ),

            "residual_immediate_risk_count": (
                len(
                    residual_immediate_risk
                )
            ),
        },

        "active_rules": (
            evaluated
        ),

        "residual_rules": (
            residual
        ),

        "residual_immediate_risk": (
            residual_immediate_risk
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
        "Active before guard:",
        len(
            active_before
        ),
    )

    print(
        "Blocked:",
        sorted(
            blocked_indexes
        ),
    )

    print(
        "Active after guard:",
        len(
            retained
        ),
    )

    print()

    print(
        "=== ACTIVE RULES ==="
    )

    for item in evaluated:

        print(
            f"clause={item['clause_index']} "
            f"| role={item['known_role'] or 'RESIDUAL'} "
            f"| {item['rule_title']}"
        )

    print()

    print(
        "Residual roles:",
        len(
            residual
        ),
    )

    print(
        "Residual immediate risk:",
        len(
            residual_immediate_risk
        ),
    )

    print()

    for item in residual:

        print(
            "=== RESIDUAL CLAUSE ==="
        )

        print(
            "Clause:",
            item[
                "clause_index"
            ],
        )

        print(
            "Law:",
            item[
                "law_name"
            ],
        )

        print(
            "Title:",
            item[
                "rule_title"
            ],
        )

        print(
            "Path:",
            (
                item[
                    "path"
                ][
                    "paragraph"
                ],
                item[
                    "path"
                ][
                    "item"
                ],
                item[
                    "path"
                ][
                    "subitem"
                ],
            ),
        )

        print(
            "Effect:",
            item[
                "effect_targets"
            ],
        )

        print(
            "Numeric:",
            item[
                "numeric_effect"
            ],
        )

        print(
            "Hints:",
            item[
                "language_hints"
            ],
        )

        print(
            "Conditions:",
            [
                (
                    condition.get(
                        "name"
                    ),
                    condition.get(
                        "type"
                    ),
                    condition.get(
                        "state"
                    ),
                )

                for condition
                in item[
                    "conditions"
                ]

                if isinstance(
                    condition,
                    dict,
                )
            ],
        )

        print(
            "Preliminary:",
            item[
                "residual_classification"
            ],
        )

        print(
            "Text:",
            item[
                "text"
            ],
        )

        print(
            "Inherited:",
            item[
                "inherited_context"
            ],
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