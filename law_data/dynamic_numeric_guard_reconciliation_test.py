# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-1R
Dynamic Numeric Guard Reconciliation

목표
======================================================================
PROJECT / PROCEDURE 동적 입력 후 ACTIVE_CANDIDATE가 된 numeric clause에
이미 SITE 단계에서 확정한 numeric-specific guard를 다시 적용한다.

핵심 문제
======================================================================
dynamic_active_numeric_context_probe 결과:

Active numeric: 12

Immediate candidates:
- clause 4   BCR 60
- clause 189 FAR 300
- clause 205 FAR 325

그러나 기존 검증에서:

clause 4
    -> upper branch NOT_APPLICABLE
    -> 현재 SITE는 제3종일반주거지역
    -> 영 제84조제6항제2호 대상 아님

clause 189
    -> 방재지구 FALSE / HIGH
    -> NOT_APPLICABLE

따라서 두 조문은 dynamic input으로 다시 살아나면 안 된다.

이번 단계:
1. clause 4 numeric guard 재적용
2. clause 189 numeric guard 재적용
3. 실제 남는 active numeric 후보 재집계
4. clause 205 전체 context 출력
5. 아직 BCR/FAR 최종 재계산은 하지 않음
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-4B-1R "
    "dynamic numeric guard reconciliation"
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

CONTEXT_PATH = (
    OUTPUT_DIR
    / "dynamic_active_numeric_context_probe.json"
)

UPPER_BRANCH_PATH = (
    OUTPUT_DIR
    / "upper_relaxation_branch_resolution.json"
)

DISASTER_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_resolution.json"
)

DISASTER_REDESIGNATION_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_redesignation_probe.json"
)

DYNAMIC_PATH = (
    OUTPUT_DIR
    / "project_procedure_dynamic_rule_evaluation.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_guard_reconciliation.json"
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
# main
# ============================================================

def main() -> int:

    context = load_json(
        CONTEXT_PATH
    )

    upper = load_json(
        UPPER_BRANCH_PATH
    )

    disaster = load_json(
        DISASTER_PATH
    )

    disaster_redesignation = load_json(
        DISASTER_REDESIGNATION_PATH
    )

    dynamic = load_json(
        DYNAMIC_PATH
    )

    active_rules = list(
        context.get(
            "active_rules",
            [],
        )
    )

    # ========================================================
    # 1. existing guards
    # ========================================================

    upper_resolutions = (
        upper.get(
            "resolutions",
            {},
        )
    )

    clause_4_resolution = (
        upper_resolutions.get(
            "clause_4",
            {},
        ).get(
            "resolution"
        )
    )

    disaster_condition = (
        disaster.get(
            "current_condition",
            {},
        )
    )

    disaster_status = (
        disaster_condition.get(
            "status"
        )
    )

    disaster_confidence = (
        disaster_condition.get(
            "confidence"
        )
    )

    disaster_numeric = (
        disaster.get(
            "numeric_effect",
            {},
        )
    )

    clause_189_resolution = (
        disaster_numeric.get(
            "resolution"
        )
    )

    redesignation_resolution = (
        disaster_redesignation.get(
            "resolution",
            {},
        )
    )

    no_redesignation = (
        redesignation_resolution.get(
            "resolution"
        )
        == "NO_REDESIGNATION_EVIDENCE"
    )

    # ========================================================
    # 2. guard table
    # ========================================================

    guards = {

        4: {
            "guard_type": (
                "UPPER_BRANCH"
            ),

            "resolution": (
                clause_4_resolution
            ),

            "allow_active": (
                clause_4_resolution
                == "CONFIRMED"
            ),

            "reason": (
                "영 제84조제6항제2호의 대상 용도지역이 아니므로 "
                "서울 조례 BCR 120% 완화경로 적용 불가"
            ),
        },

        189: {
            "guard_type": (
                "SITE_CONDITION"
            ),

            "resolution": (
                clause_189_resolution
            ),

            "allow_active": (
                clause_189_resolution
                == "CONFIRMED"
                and disaster_status
                == "TRUE"
            ),

            "reason": (
                "영 제85조제5항은 방재지구를 전제로 하나 "
                "현재 방재지구 FALSE / HIGH이며 "
                "2019년 이후 재지정 evidence도 없음"
            ),
        },
    }

    # ========================================================
    # 3. reconcile
    # ========================================================

    retained = []
    excluded = []

    for item in active_rules:

        clause_index = int(
            item.get(
                "clause_index"
            )
        )

        guard = guards.get(
            clause_index
        )

        if (
            guard
            and not guard[
                "allow_active"
            ]
        ):

            excluded.append(
                {
                    **item,

                    "guard": (
                        guard
                    ),

                    "reconciled_status": (
                        "INACTIVE_BY_VERIFIED_GUARD"
                    ),
                }
            )

            continue

        retained.append(
            {
                **item,

                "reconciled_status": (
                    "ACTIVE_AFTER_GUARD"
                ),
            }
        )

    # ========================================================
    # 4. role summary after guard
    # ========================================================

    role_counter = Counter(
        item.get(
            "role"
        )
        for item
        in retained
    )

    immediate_candidates = [
        item
        for item
        in retained
        if (
            item.get(
                "role"
            )
            == "DIRECT_RELAXATION"
            and item.get(
                "comparison",
                {},
            ).get(
                "status"
            )
            == "COMPARABLE"
        )
    ]

    # ========================================================
    # 5. clause 205 full context
    # ========================================================

    clause_205 = next(
        (
            item
            for item
            in retained
            if int(
                item.get(
                    "clause_index"
                )
            )
            == 205
        ),
        None,
    )

    dynamic_rule_205 = next(
        (
            rule
            for rule
            in dynamic.get(
                "rules",
                [],
            )
            if int(
                rule.get(
                    "clause_index",
                    -1,
                )
            )
            == 205
        ),
        None,
    )

    if dynamic_rule_205:

        clause_205_detail = {
            "clause_index": (
                205
            ),

            "law_name": (
                dynamic_rule_205.get(
                    "law_name"
                )
            ),

            "rule_title": (
                dynamic_rule_205.get(
                    "rule_title"
                )
            ),

            "paragraph": (
                dynamic_rule_205.get(
                    "paragraph"
                )
            ),

            "item": (
                dynamic_rule_205.get(
                    "item"
                )
            ),

            "subitem": (
                dynamic_rule_205.get(
                    "subitem"
                )
            ),

            "applicability": (
                dynamic_rule_205.get(
                    "applicability"
                )
            ),

            "applicability_reason": (
                dynamic_rule_205.get(
                    "applicability_reason"
                )
            ),

            "effect_targets": (
                dynamic_rule_205.get(
                    "effect_targets",
                    [],
                )
            ),

            "numeric_effect": (
                dynamic_rule_205.get(
                    "numeric_effect"
                )
            ),

            "conditions": (
                dynamic_rule_205.get(
                    "conditions",
                    [],
                )
            ),

            "required_inputs": (
                dynamic_rule_205.get(
                    "required_inputs",
                    [],
                )
            ),

            "blocked_by": (
                dynamic_rule_205.get(
                    "blocked_by",
                    [],
                )
            ),

            "unknown_by": (
                dynamic_rule_205.get(
                    "unknown_by",
                    [],
                )
            ),

            "text": (
                dynamic_rule_205.get(
                    "text"
                )
            ),

            "inherited_context": (
                dynamic_rule_205.get(
                    "inherited_context"
                )
            ),

            "comparison": (
                clause_205.get(
                    "comparison"
                )
                if clause_205
                else None
            ),

            "role": (
                clause_205.get(
                    "role"
                )
                if clause_205
                else None
            ),
        }

    else:

        clause_205_detail = None

    # ========================================================
    # 6. guard validation
    # ========================================================

    excluded_indexes = {
        int(
            item.get(
                "clause_index"
            )
        )
        for item
        in excluded
    }

    retained_indexes = {
        int(
            item.get(
                "clause_index"
            )
        )
        for item
        in retained
    }

    immediate_indexes = {
        int(
            item.get(
                "clause_index"
            )
        )
        for item
        in immediate_candidates
    }

    validations = {

        "input active numeric 12": (
            len(
                active_rules
            )
            == 12
        ),

        "clause 4 previous resolution NOT_APPLICABLE": (
            clause_4_resolution
            == "NOT_APPLICABLE"
        ),

        "방재지구 FALSE HIGH": (
            disaster_status
            == "FALSE"
            and disaster_confidence
            == "HIGH"
        ),

        "clause 189 previous resolution NOT_APPLICABLE": (
            clause_189_resolution
            == "NOT_APPLICABLE"
        ),

        "방재지구 재지정 evidence 없음": (
            no_redesignation
        ),

        "clause 4 excluded": (
            4
            in excluded_indexes
        ),

        "clause 189 excluded": (
            189
            in excluded_indexes
        ),

        "clause 4 not retained": (
            4
            not in retained_indexes
        ),

        "clause 189 not retained": (
            189
            not in retained_indexes
        ),

        "active after guard 10": (
            len(
                retained
            )
            == 10
        ),

        "clause 205 retained": (
            205
            in retained_indexes
        ),

        "only immediate clause 205": (
            immediate_indexes
            == {
                205
            }
        ),

        "clause 205 detail exists": (
            clause_205_detail
            is not None
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 7. output
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

        "before_guard": {
            "active_numeric_count": (
                len(
                    active_rules
                )
            ),

            "immediate_candidate_count": (
                context.get(
                    "summary",
                    {},
                ).get(
                    "immediate_candidate_count"
                )
            ),
        },

        "verified_guards": (
            guards
        ),

        "excluded_by_guard": (
            excluded
        ),

        "after_guard": {
            "active_numeric_count": (
                len(
                    retained
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

            "immediate_clause_indexes": (
                sorted(
                    immediate_indexes
                )
            ),
        },

        "active_rules": (
            retained
        ),

        "immediate_candidates": (
            immediate_candidates
        ),

        "clause_205_detail": (
            clause_205_detail
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
            active_rules
        ),
    )

    print(
        "Excluded by verified guard:",
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
        "Active after guard:",
        len(
            retained
        ),
    )

    print(
        "Roles after guard:",
        dict(
            role_counter
        ),
    )

    print()

    print(
        "Immediate candidates after guard:",
        len(
            immediate_candidates
        ),
    )

    for item in immediate_candidates:

        print(
            f"- clause={item['clause_index']} "
            f"| {item['rule_title']} "
            f"| projected="
            f"{item['comparison']['projected_value']}"
        )

    print()

    print(
        "=== CLAUSE 205 ==="
    )

    if clause_205_detail:

        print(
            "Law:",
            clause_205_detail[
                "law_name"
            ],
        )

        print(
            "Path:",
            (
                clause_205_detail[
                    "paragraph"
                ],
                clause_205_detail[
                    "item"
                ],
                clause_205_detail[
                    "subitem"
                ],
            ),
        )

        print(
            "Applicability:",
            clause_205_detail[
                "applicability"
            ],
        )

        print(
            "Conditions:",
            [
                (
                    item.get(
                        "name"
                    ),
                    item.get(
                        "type"
                    ),
                    item.get(
                        "state"
                    ),
                )

                for item
                in clause_205_detail[
                    "conditions"
                ]
            ],
        )

        print(
            "Numeric:",
            clause_205_detail[
                "numeric_effect"
            ],
        )

        print(
            "Text:",
            clause_205_detail[
                "text"
            ],
        )

        print(
            "Inherited:",
            clause_205_detail[
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