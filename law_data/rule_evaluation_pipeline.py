# -*- coding: utf-8 -*-

"""
Reusable Rule Evaluation Pipeline

목표
======================================================================
깨끗한 SITE baseline에서 시작하여 다음 순서로 rule evaluation을 수행한다.

1. SITE baseline load
2. 현재 SITE 용도지역 기준 zone relevance 재평가
3. branch-local predicate detection
4. branch-local condition 추가
5. SITE resolution registry 적용
6. PROJECT / PROCEDURE 입력 적용
7. applicability 재평가
8. numeric-specific verified guard 적용
9. dynamic zone base numeric 적용
10. numeric result 확정
11. remaining input / external dependency 반환

중요
======================================================================
이 모듈은 테스트 output JSON의 "판정결과" 자체를 source rule set으로
사용하지 않는다.

항상:

    site_rule_evaluation_site_complete.json

을 clean baseline으로 사용한다.

C-13 Multi-SITE 원칙
======================================================================
기존 snapshot의 zone_relevance는 개포동 12번지 기준으로 생성되었으므로,
현재 SITE zone을 기준으로 zone relevance를 다시 계산한다.

단:

OTHER_ZONE -> DIRECT / GROUP

으로 변경되었다는 이유만으로 모든 rule을 즉시 APPLICABLE 처리하지 않는다.

예:
- 시장정비사업
- 주거복합건물
- 임대주택
- 특례
- 완화
- 강화

등은 별도 PROJECT / PROCEDURE / 문맥 조건이 숨어 있을 수 있다.

따라서 현재 단계에서는 명확하게 확인된
"용도지역 기본 한도/reference rule"만 제한적으로 재활성화한다.

C-15 / C-16 Runtime SITE Condition 원칙
======================================================================
runtime spatial condition은 기존 대표 SITE snapshot보다 우선한다.

TRUE / FALSE / UNKNOWN 모두 overlay 대상이다.

또한 runtime state가 기존 snapshot state와 동일하더라도:

    confidence
    source / provenance

가 다르면 현재 runtime evidence 기준으로 반드시 갱신한다.

예:

    snapshot FALSE
    runtime FALSE

state 값은 같지만 현재 SITE의 판정 근거가 runtime spatial query라면
최종 rule condition source는 SITE_CONDITION_SNAPSHOT이 아니라
RUNTIME_SPATIAL_CONDITION이어야 한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# zone classifier
# ============================================================

try:

    from .law_special_rule_clause_split_test import (
        classify_zone_relevance,
    )

except ImportError:

    from law_special_rule_clause_split_test import (
        classify_zone_relevance,
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

SITE_COMPLETE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_site_complete.json"
)

SEOUL_DOWNTOWN_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
)

UPPER_BRANCH_PATH = (
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

CLAUSE_250_PATH = (
    OUTPUT_DIR
    / "clause_250_stacking_ceiling_resolution.json"
)

BASE_NUMERIC_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)


# ============================================================
# local module
# ============================================================

try:

    from .rule_condition_registry import (
        build_branch_condition,
        find_missing_branch_predicates,
    )

except ImportError:

    from rule_condition_registry import (
        build_branch_condition,
        find_missing_branch_predicates,
    )


# ============================================================
# VALID STATES
# ============================================================

VALID_STATES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
    "UNSET",
}


# ============================================================
# SAFE ZONE REACTIVATION
#
# 현재 C-13에서 실제 조문구조를 검증한 범위만 허용한다.
# ============================================================

SAFE_ZONE_REACTIVATION_RULES = {

    (
        "국토의 계획 및 이용에 관한 법률",
        "용도지역의 건폐율",
    ),

    (
        "국토의 계획 및 이용에 관한 법률",
        "용도지역에서의 용적률",
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


def safe_string(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


def validate_profile(
    profile: Dict[str, str],
    profile_type: str,
) -> None:

    for name, state in (
        profile.items()
    ):

        if state not in VALID_STATES:

            raise ValueError(
                f"{profile_type} 입력 오류: "
                f"{name}={state}"
            )


# ============================================================
# condition groups
# ============================================================

def refresh_condition_groups(
    rule: Dict[str, Any],
) -> None:

    conditions = (
        rule.get(
            "conditions",
            [],
        )
    )

    rule[
        "required_inputs"
    ] = [
        item
        for item
        in conditions
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "state"
            )
            == "UNSET"
        )
    ]

    rule[
        "blocked_by"
    ] = [
        item
        for item
        in conditions
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "state"
            )
            == "FALSE"
        )
    ]

    rule[
        "unknown_by"
    ] = [
        item
        for item
        in conditions
        if (
            isinstance(
                item,
                dict,
            )
            and item.get(
                "state"
            )
            == "UNKNOWN"
        )
    ]


# ============================================================
# applicability
# ============================================================

def recalculate_applicability(
    rule: Dict[str, Any],
) -> Dict[str, str]:

    blocked = (
        rule.get(
            "blocked_by",
            [],
        )
    )

    unknown = (
        rule.get(
            "unknown_by",
            [],
        )
    )

    required = (
        rule.get(
            "required_inputs",
            [],
        )
    )

    # --------------------------------------------------------
    # FALSE condition
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # zone mismatch
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # UNKNOWN condition
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # UNSET condition
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # applicable
    # --------------------------------------------------------

    return {

        "applicability": (
            "APPLICABLE"
        ),

        "reason": (
            "모든 필수조건 충족"
        ),
    }


# ============================================================
# numeric status
# ============================================================

def refresh_numeric_effect(
    rule: Dict[str, Any],
) -> None:

    numeric_effect = (
        rule.get(
            "numeric_effect"
        )
    )

    if not numeric_effect:

        return

    applicability = (
        rule.get(
            "applicability"
        )
    )

    if (
        applicability
        == "NOT_APPLICABLE"
    ):

        status = (
            "INACTIVE"
        )

    elif (
        applicability
        == "CONDITIONAL"
    ):

        status = (
            "POTENTIAL_CONDITIONAL"
        )

    elif (
        applicability
        == "UNKNOWN"
    ):

        status = (
            "POTENTIAL_UNKNOWN"
        )

    else:

        status = (
            "ACTIVE_CANDIDATE"
        )

    rule[
        "current_numeric_effect"
    ] = {

        "status": (
            status
        ),

        "effect_class": (
            rule.get(
                "numeric_effect_class"
            )
        ),

        "semantic": (
            numeric_effect
        ),
    }


def refresh_rule(
    rule: Dict[str, Any],
) -> None:

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


# ============================================================
# SITE registry
# ============================================================

def build_site_registry(
    downtown_data: Dict[str, Any],
) -> Dict[
    str,
    Dict[str, Any]
]:

    downtown_condition = (
        downtown_data.get(
            "condition",
            {},
        )
    )

    return {

        "서울도심": {

            "type": (
                "SITE"
            ),

            "state": (
                downtown_condition.get(
                    "status"
                )
            ),

            "confidence": (
                downtown_condition.get(
                    "confidence"
                )
            ),

            "source": (
                "SEOUL_DOWNTOWN_CONDITION_RESOLUTION"
            ),
        },
    }


def overlay_runtime_site_conditions(
    site_registry: Dict[
        str,
        Dict[str, Any]
    ],
    site_condition_context: Any,
) -> Dict[
    str,
    Dict[str, Any]
]:

    """
    C-15 / C-16 runtime SITE condition 결과를
    기존 SITE registry 위에 덮어쓴다.

    우선순위
    ==================================================================
    runtime SITE condition
        >
    기존 verified SITE registry / snapshot

    중요
    ==================================================================
    TRUE만 overlay하지 않는다.

    runtime FALSE도 반드시 반영한다.

    runtime UNKNOWN도 현재 SITE의 실제 runtime 결과이므로
    기존 BASE snapshot TRUE/FALSE보다 우선한다.

    이를 통해 대표 SITE condition이 다른 PNU에 누수되는 것을 방지한다.
    """

    merged = copy.deepcopy(
        site_registry
    )

    if not isinstance(
        site_condition_context,
        dict,
    ):

        return merged

    for name, raw_condition in (
        site_condition_context.items()
    ):

        condition_name = safe_string(
            name
        )

        if not condition_name:

            continue

        if not isinstance(
            raw_condition,
            dict,
        ):

            continue

        state = safe_string(
            raw_condition.get(
                "state"
            )
        ).upper()

        # ----------------------------------------------------
        # 유효한 runtime state만 registry에 사용
        # ----------------------------------------------------

        if state not in {
            "TRUE",
            "FALSE",
            "UNKNOWN",
        }:

            continue

        confidence = safe_string(
            raw_condition.get(
                "confidence"
            )
        ).upper()

        if not confidence:

            confidence = (
                "LOW"
            )

        runtime_source = (
            raw_condition.get(
                "source"
            )
        )

        merged[
            condition_name
        ] = {

            "type": (
                raw_condition.get(
                    "type"
                )
                or "SITE"
            ),

            "state": (
                state
            ),

            "confidence": (
                confidence
            ),

            # ------------------------------------------------
            # registry-level source는 고정 marker로 둔다.
            # 상세 provider/dataset은 runtime_source에 보존.
            # ------------------------------------------------

            "source": (
                "RUNTIME_SPATIAL_CONDITION"
            ),

            "runtime": (
                True
            ),

            "pnu": (
                raw_condition.get(
                    "pnu"
                )
            ),

            "resolution": (
                raw_condition.get(
                    "resolution"
                )
            ),

            "geometry_verified": (
                raw_condition.get(
                    "geometry_verified"
                )
            ),

            "runtime_source": (
                copy.deepcopy(
                    runtime_source
                )
            ),

            "evaluation": (
                copy.deepcopy(
                    raw_condition.get(
                        "evaluation",
                        {},
                    )
                )
            ),

            "evidence": (
                copy.deepcopy(
                    raw_condition.get(
                        "evidence",
                        {},
                    )
                )
            ),
        }

    return merged


# ============================================================
# branch-local predicates
# ============================================================

def apply_branch_local_conditions(
    rules: List[
        Dict[str, Any]
    ],
    site_zone: str,
    site_registry: Dict[
        str,
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    added = []

    reused = []

    touched = set()

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

        missing = (
            find_missing_branch_predicates(
                rule
            )
        )

        selected = [
            item
            for item
            in missing
            if (
                item.get(
                    "branch_priority"
                )
                == "HIGH"
                and item.get(
                    "direct_in_clause_text"
                )
                is True
            )
        ]

        if not selected:

            continue

        existing_names = {

            safe_string(
                condition.get(
                    "name"
                )
            )

            for condition
            in rule.get(
                "conditions",
                [],
            )

            if isinstance(
                condition,
                dict,
            )
        }

        for predicate in selected:

            name = (
                predicate[
                    "name"
                ]
            )

            if name in existing_names:

                reused.append(
                    {

                        "clause_index": (
                            rule.get(
                                "clause_index"
                            )
                        ),

                        "name": (
                            name
                        ),
                    }
                )

                continue

            condition = (
                build_branch_condition(
                    predicate=(
                        predicate
                    ),

                    site_zone=(
                        site_zone
                    ),

                    site_registry=(
                        site_registry
                    ),
                )
            )

            rule.setdefault(
                "conditions",
                [],
            ).append(
                condition
            )

            added.append(
                {

                    "clause_index": (
                        rule.get(
                            "clause_index"
                        )
                    ),

                    **condition,
                }
            )

            existing_names.add(
                name
            )

            touched.add(
                int(
                    rule.get(
                        "clause_index"
                    )
                )
            )

        refresh_rule(
            rule
        )

    return {

        "added": (
            added
        ),

        "reused": (
            reused
        ),

        "touched_clause_indexes": (
            sorted(
                touched
            )
        ),
    }

# ============================================================
# verified upper-branch conditions
# ============================================================

def apply_verified_upper_branch_conditions(
    rules: List[
        Dict[str, Any]
    ],
    upper_data: Dict[str, Any],
) -> Dict[str, Any]:

    """
    상위 법령 branch 분석에서 이미 검증된 condition을
    clean baseline rule에 복원한다.

    목적
    ==================================================================
    하위 조례 clause 자체 text에는 상위법의 predicate 문자열이
    직접 존재하지 않을 수 있다.

    예:
        서울특별시 도시계획 조례 clause 189
        → "영 제85조제5항"만 직접 참조
        → 실제 상위 branch 조건:
            SITE    방재지구
            PROJECT 재해예방시설

    이 경우 text pattern detector가 조건을 재발견하도록 강제하지 않고,
    검증 완료된 upper_relaxation_branch_resolution.json의
    conditions를 source-of-evidence로 사용한다.

    중요
    ==================================================================
    여기서는 runtime SITE registry를 직접 주입하지 않는다.

    우선 verified branch condition 자체를 rule에 복원하고,
    이후 apply_site_registry()가 현재 SITE runtime 상태를 덮어쓴다.

    따라서 처리 순서는:

        verified branch condition restoration
        ↓
        apply_site_registry()
        ↓
        PROJECT / PROCEDURE injection

    이다.
    """

    added = []

    reused = []

    touched = set()

    resolutions = (
        upper_data.get(
            "resolutions",
            {},
        )
    )

    if not isinstance(
        resolutions,
        dict,
    ):

        return {
            "added":
                [],
            "reused":
                [],
            "touched_clause_indexes":
                [],
        }

    # --------------------------------------------------------
    # clause_index → verified conditions
    # --------------------------------------------------------

    binding_by_clause: Dict[
        int,
        List[
            Dict[str, Any]
        ],
    ] = {}

    for resolution_name, resolution in (
        resolutions.items()
    ):

        if not isinstance(
            resolution,
            dict,
        ):

            continue

        clause_index = (
            resolution.get(
                "clause_index"
            )
        )

        if not isinstance(
            clause_index,
            int,
        ):

            continue

        raw_conditions = (
            resolution.get(
                "conditions",
                [],
            )
        )

        if not isinstance(
            raw_conditions,
            list,
        ):

            continue

        verified_conditions = []

        for raw_condition in raw_conditions:

            if not isinstance(
                raw_condition,
                dict,
            ):

                continue

            name = safe_string(
                raw_condition.get(
                    "name"
                )
            )

            condition_type = safe_string(
                raw_condition.get(
                    "type"
                )
            )

            if not name:

                continue

            if condition_type not in {
                "SITE",
                "SITE_HISTORY",
                "PROJECT",
                "PROCEDURE",
            }:

                continue

            verified_conditions.append(
                {
                    "name":
                        name,

                    "type":
                        condition_type,

                    "state":
                        (
                            safe_string(
                                raw_condition.get(
                                    "state"
                                )
                            )
                            or (
                                "UNSET"
                                if condition_type
                                in {
                                    "PROJECT",
                                    "PROCEDURE",
                                }
                                else "UNKNOWN"
                            )
                        ),

                    "confidence":
                        (
                            safe_string(
                                raw_condition.get(
                                    "confidence"
                                )
                            )
                            or "NONE"
                        ),

                    "source":
                        (
                            safe_string(
                                raw_condition.get(
                                    "source"
                                )
                            )
                            or "VERIFIED_UPPER_BRANCH"
                        ),

                    "upper_branch_verified":
                        True,

                    "upper_branch_resolution":
                        resolution_name,

                    "upper_reference":
                        resolution.get(
                            "upper_reference"
                        ),
                }
            )

        if verified_conditions:

            binding_by_clause[
                clause_index
            ] = (
                verified_conditions
            )

    # --------------------------------------------------------
    # rule restoration
    # --------------------------------------------------------

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        clause_index = (
            rule.get(
                "clause_index"
            )
        )

        if not isinstance(
            clause_index,
            int,
        ):

            continue

        verified_conditions = (
            binding_by_clause.get(
                clause_index
            )
        )

        if not verified_conditions:

            continue

        conditions = (
            rule.setdefault(
                "conditions",
                [],
            )
        )

        existing_names = {

            safe_string(
                condition.get(
                    "name"
                )
            )

            for condition
            in conditions

            if isinstance(
                condition,
                dict,
            )
        }

        changed = False

        for condition in (
            verified_conditions
        ):

            name = condition[
                "name"
            ]

            if name in existing_names:

                reused.append(
                    {
                        "clause_index":
                            clause_index,

                        "name":
                            name,
                    }
                )

                continue

            conditions.append(
                copy.deepcopy(
                    condition
                )
            )

            added.append(
                {
                    "clause_index":
                        clause_index,

                    **copy.deepcopy(
                        condition
                    ),
                }
            )

            existing_names.add(
                name
            )

            touched.add(
                clause_index
            )

            changed = True

        if changed:

            refresh_rule(
                rule
            )

    return {
        "added":
            added,

        "reused":
            reused,

        "touched_clause_indexes":
            sorted(
                touched
            ),
    }

# ============================================================
# global SITE registry
# ============================================================

def apply_site_registry(
    rules: List[
        Dict[str, Any]
    ],
    site_registry: Dict[
        str,
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:

    """
    SITE registry 결과를 모든 rule condition에 반영한다.

    C-16 provenance 정책
    ==================================================================
    state 값만 비교하지 않는다.

    state / confidence / source 중 하나라도 다르면
    현재 registry 기준으로 condition을 갱신한다.

    따라서:

        snapshot FALSE
        runtime FALSE

    처럼 state가 동일한 경우에도 source가 달라지면:

        SITE_CONDITION_SNAPSHOT
        ->
        RUNTIME_SPATIAL_CONDITION

    으로 정상 갱신된다.
    """

    repairs = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        changed = False

        for condition in (
            rule.get(
                "conditions",
                [],
            )
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

            resolved = (
                site_registry.get(
                    name
                )
            )

            if not resolved:

                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            previous_confidence = (
                condition.get(
                    "confidence"
                )
            )

            previous_source = (
                condition.get(
                    "source"
                )
            )

            resolved_state = (
                resolved.get(
                    "state"
                )
            )

            resolved_confidence = (
                resolved.get(
                    "confidence"
                )
            )

            resolved_source = (
                resolved.get(
                    "source"
                )
            )

            state_changed = (
                previous_state
                != resolved_state
            )

            confidence_changed = (
                previous_confidence
                != resolved_confidence
            )

            source_changed = (
                previous_source
                != resolved_source
            )

            # ------------------------------------------------
            # state가 같더라도 runtime provenance가 다르면
            # metadata를 반드시 갱신한다.
            # ------------------------------------------------

            if not (
                state_changed
                or confidence_changed
                or source_changed
            ):

                continue

            condition[
                "state"
            ] = (
                resolved_state
            )

            condition[
                "confidence"
            ] = (
                resolved_confidence
            )

            condition[
                "source"
            ] = (
                resolved_source
            )

            repairs.append(
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
                        resolved_state
                    ),

                    "previous_confidence": (
                        previous_confidence
                    ),

                    "new_confidence": (
                        resolved_confidence
                    ),

                    "previous_source": (
                        previous_source
                    ),

                    "new_source": (
                        resolved_source
                    ),

                    "state_changed": (
                        state_changed
                    ),

                    "confidence_changed": (
                        confidence_changed
                    ),

                    "source_changed": (
                        source_changed
                    ),
                }
            )

            changed = True

        if changed:

            refresh_rule(
                rule
            )

    return repairs


# ============================================================
# PROJECT / PROCEDURE
# ============================================================

def inject_profiles(
    rules: List[
        Dict[str, Any]
    ],
    project_profile: Dict[
        str,
        str
    ],
    procedure_profile: Dict[
        str,
        str
    ],
) -> Dict[str, Any]:

    touched = []

    changes = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        before = (
            rule.get(
                "applicability"
            )
        )

        matched = []

        for condition in (
            rule.get(
                "conditions",
                [],
            )
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

            condition_type = (
                safe_string(
                    condition.get(
                        "type"
                    )
                )
            )

            new_state = None

            if (
                condition_type
                == "PROJECT"
                and name
                in project_profile
            ):

                new_state = (
                    project_profile[
                        name
                    ]
                )

            elif (
                condition_type
                == "PROCEDURE"
                and name
                in procedure_profile
            ):

                new_state = (
                    procedure_profile[
                        name
                    ]
                )

            if new_state is None:

                continue

            previous_state = (
                condition.get(
                    "state"
                )
            )

            condition[
                "state"
            ] = (
                new_state
            )

            condition[
                "confidence"
            ] = (
                "USER_DECLARED"
            )

            condition[
                "source"
            ] = (
                "RULE_EVALUATION_PIPELINE_INPUT"
            )

            matched.append(
                {

                    "name": (
                        name
                    ),

                    "type": (
                        condition_type
                    ),

                    "before": (
                        previous_state
                    ),

                    "after": (
                        new_state
                    ),
                }
            )

        if not matched:

            continue

        refresh_rule(
            rule
        )

        touched.append(
            {

                "clause_index": (
                    rule.get(
                        "clause_index"
                    )
                ),

                "conditions": (
                    matched
                ),
            }
        )

        if (
            before
            != rule.get(
                "applicability"
            )
        ):

            changes.append(
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

                    "before": (
                        before
                    ),

                    "after": (
                        rule.get(
                            "applicability"
                        )
                    ),
                }
            )

    return {

        "touched": (
            touched
        ),

        "changes": (
            changes
        ),
    }


# ============================================================
# numeric guard registry
# ============================================================

def build_numeric_guard_registry(
    upper_data: Dict[str, Any],
    disaster_data: Dict[str, Any],
    clause_205_data: Dict[str, Any],
    clause_250_data: Dict[str, Any],
) -> Dict[
    int,
    Dict[str, Any]
]:

    clause_4_resolution = (
        upper_data.get(
            "resolutions",
            {},
        ).get(
            "clause_4",
            {},
        ).get(
            "resolution"
        )
    )

    disaster_condition = (
        disaster_data.get(
            "current_condition",
            {},
        )
    )

    clause_189_resolution = (
        disaster_data.get(
            "numeric_effect",
            {},
        ).get(
            "resolution"
        )
    )

    clause_205_resolution = (
        clause_205_data.get(
            "resolution",
            {},
        ).get(
            "applicability"
        )
    )

    clause_250_resolution = (
        clause_250_data.get(
            "resolution",
            {},
        )
    )

    return {

        4: {

            "allow_numeric": (
                clause_4_resolution
                == "CONFIRMED"
            ),

            "resolution": (
                clause_4_resolution
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),
        },

        189: {

        # --------------------------------------------------------
        # C-16-7-I
        #
        # 방재지구 / 재해예방시설 여부는 이미 current rule의
        # verified upper-branch conditions에서 평가된다.
        #
        # numeric guard에서 대표 SITE의 static 방재지구 상태를
        # 다시 사용하지 않는다.
        #
        # ACTIVE_CANDIDATE까지 도달했다는 것은:
        #
        #   방재지구 TRUE
        #   재해예방시설 TRUE
        #   zone / branch 조건 충족
        #
        # 이 이미 확인되었다는 뜻이다.
        # --------------------------------------------------------

            "allow_numeric": (
                True
            ),

            "resolution": (
                "RUNTIME_BRANCH_CONDITIONS_SATISFIED"
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),

            "guard_source": (
                "CURRENT_RULE_APPLICABILITY"
            ),
        },

        205: {

            "allow_numeric": (
                clause_205_resolution
                == "APPLICABLE"
            ),

            "resolution": (
                clause_205_resolution
            ),

            "role": (
                "DIRECT_RELAXATION"
            ),
        },

        250: {

            "allow_numeric": (
                clause_250_resolution.get(
                    "allow_numeric_effect"
                )
                is True
            ),

            "resolution": (
                clause_250_resolution.get(
                    "applicability"
                )
            ),

            "role": (
                clause_250_resolution.get(
                    "role"
                )
            ),

            "corrected_numeric_semantic": (
                clause_250_resolution.get(
                    "corrected_numeric_semantic"
                )
            ),
        },
    }


# ============================================================
# numeric guard
# ============================================================

def apply_numeric_guards(
    rules: List[
        Dict[str, Any]
    ],
    guards: Dict[
        int,
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    active = []

    retained = []

    excluded = []

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

        if (
            rule.get(
                "current_numeric_effect",
                {},
            ).get(
                "status"
            )
            != "ACTIVE_CANDIDATE"
        ):

            continue

        active.append(
            rule
        )

    for rule in active:

        clause_index = int(
            rule.get(
                "clause_index"
            )
        )

        guard = (
            guards.get(
                clause_index
            )
        )

        if (
            guard
            and guard.get(
                "allow_numeric"
            )
            is False
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

    return {

        "active": (
            active
        ),

        "excluded": (
            excluded
        ),

        "retained": (
            retained
        ),
    }


# ============================================================
# remaining inputs
# ============================================================

def aggregate_remaining_inputs(
    rules: List[
        Dict[str, Any]
    ],
) -> Dict[
    str,
    List[
        Dict[str, Any]
    ]
]:

    project = Counter()

    procedure = Counter()

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        for condition in (
            rule.get(
                "required_inputs",
                [],
            )
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

            condition_type = (
                safe_string(
                    condition.get(
                        "type"
                    )
                )
            )

            if (
                condition_type
                == "PROJECT"
            ):

                project[
                    name
                ] += 1

            elif (
                condition_type
                == "PROCEDURE"
            ):

                procedure[
                    name
                ] += 1

    return {

        "project": [

            {

                "name": (
                    name
                ),

                "affected_clause_count": (
                    count
                ),

                "state": (
                    "UNSET"
                ),
            }

            for name, count
            in project.most_common()
        ],

        "procedure": [

            {

                "name": (
                    name
                ),

                "affected_clause_count": (
                    count
                ),

                "state": (
                    "UNSET"
                ),
            }

            for name, count
            in procedure.most_common()
        ],
    }


# ============================================================
# zone transition safety
# ============================================================

def is_safe_zone_reactivation_rule(
    rule: Dict[str, Any],
) -> bool:

    law_name = safe_string(
        rule.get(
            "law_name"
        )
    )

    rule_title = safe_string(
        rule.get(
            "rule_title"
        )
    )

    return (
        (
            law_name,
            rule_title,
        )
        in SAFE_ZONE_REACTIVATION_RULES
    )


# ============================================================
# zone relevance transition
# ============================================================

def apply_zone_relevance_transition(
    rule: Dict[str, Any],
    old_zone_relevance: str,
    new_zone_relevance: str,
) -> Dict[str, Any]:

    updated = copy.deepcopy(
        rule
    )

    old_zone_relevance = (
        safe_string(
            old_zone_relevance
        )
    )

    new_zone_relevance = (
        safe_string(
            new_zone_relevance
        )
    )

    old_applicability = (
        safe_string(
            updated.get(
                "applicability"
            )
        )
    )

    old_reason = (
        safe_string(
            updated.get(
                "applicability_reason"
            )
        )
    )

    # ========================================================
    # A.
    # 기존 SITE에서는 적용 zone이었지만
    # 현재 SITE에서는 OTHER_ZONE
    # ========================================================

    if (
        old_zone_relevance
        in {
            "DIRECT",
            "GROUP",
        }
        and new_zone_relevance
        == "OTHER_ZONE"
    ):

        updated[
            "applicability"
        ] = (
            "NOT_APPLICABLE"
        )

        updated[
            "applicability_reason"
        ] = (
            "현재 SITE 용도지역 불일치"
        )

        updated[
            "zone_transition"
        ] = {

            "status": (
                "DEACTIVATED_BY_ZONE"
            ),

            "before": (
                old_zone_relevance
            ),

            "after": (
                new_zone_relevance
            ),

            "previous_applicability": (
                old_applicability
            ),
        }

        refresh_numeric_effect(
            updated
        )

        return updated

    # ========================================================
    # B.
    # 기존 SITE에서는 OTHER_ZONE
    # 현재 SITE에서는 DIRECT / GROUP
    # ========================================================

    if (
        old_zone_relevance
        == "OTHER_ZONE"
        and new_zone_relevance
        in {
            "DIRECT",
            "GROUP",
        }
    ):

        was_zone_only_exclusion = (
            old_applicability
            == "NOT_APPLICABLE"
            and "용도지역 불일치"
            in old_reason
        )

        if not was_zone_only_exclusion:

            updated[
                "zone_transition"
            ] = {

                "status": (
                    "MATCHED_BUT_ORIGINAL_EXCLUSION_PRESERVED"
                ),

                "before": (
                    old_zone_relevance
                ),

                "after": (
                    new_zone_relevance
                ),
            }

            return updated

        if (
            is_safe_zone_reactivation_rule(
                updated
            )
        ):

            refresh_condition_groups(
                updated
            )

            recalculated = (
                recalculate_applicability(
                    updated
                )
            )

            updated[
                "applicability"
            ] = (
                recalculated[
                    "applicability"
                ]
            )

            updated[
                "applicability_reason"
            ] = (
                recalculated[
                    "reason"
                ]
            )

            updated[
                "zone_transition"
            ] = {

                "status": (
                    "REACTIVATED_SAFE_ZONE_REFERENCE"
                ),

                "before": (
                    old_zone_relevance
                ),

                "after": (
                    new_zone_relevance
                ),
            }

            refresh_numeric_effect(
                updated
            )

            return updated

        updated[
            "applicability"
        ] = (
            old_applicability
        )

        updated[
            "applicability_reason"
        ] = (
            "현재 SITE 용도지역은 일치하나 "
            "추가 적용요건 재검증 전까지 "
            "기존 판정 유지"
        )

        updated[
            "zone_transition"
        ] = {

            "status": (
                "REACTIVATION_DEFERRED"
            ),

            "before": (
                old_zone_relevance
            ),

            "after": (
                new_zone_relevance
            ),
        }

        return updated

    # ========================================================
    # C.
    # 기타 변화
    # ========================================================

    updated[
        "zone_transition"
    ] = {

        "status": (
            "NO_APPLICABILITY_TRANSITION"
        ),

        "before": (
            old_zone_relevance
        ),

        "after": (
            new_zone_relevance
        ),
    }

    return updated


# ============================================================
# zone relevance refresh
# ============================================================

def refresh_rule_zone_relevance(
    rule: Dict[str, Any],
    site_zone: str,
) -> Dict[str, Any]:

    own_text = safe_string(
        rule.get(
            "text"
        )
    )

    inherited_context = (
        safe_string(
            rule.get(
                "inherited_text"
            )
        )
    )

    old_zone_relevance = (
        safe_string(
            rule.get(
                "zone_relevance"
            )
        )
    )

    result = (
        classify_zone_relevance(
            target_zone=(
                site_zone
            ),

            own_text=(
                own_text
            ),

            inherited_context=(
                inherited_context
            ),

            law_name=(
                safe_string(
                    rule.get(
                        "law_name"
                    )
                )
            ),

            rule_title=(
                safe_string(
                    rule.get(
                        "rule_title"
                    )
                )
            ),
        )
    )

    new_zone_relevance = (
        safe_string(
            result.get(
                "status"
            )
        )
    )

    refreshed = copy.deepcopy(
        rule
    )

    refreshed[
        "zone_relevance"
    ] = (
        new_zone_relevance
    )

    refreshed[
        "zone_relevance_reason"
    ] = (
        result.get(
            "reason"
        )
    )

    refreshed[
        "zone_relevance_zones"
    ] = (
        result.get(
            "zones",
            [],
        )
    )

    refreshed[
        "zone_relevance_groups"
    ] = (
        result.get(
            "groups",
            [],
        )
    )

    refreshed[
        "zone_relevance_matched_groups"
    ] = (
        result.get(
            "matched_groups",
            [],
        )
    )

    return (
        apply_zone_relevance_transition(
            rule=(
                refreshed
            ),

            old_zone_relevance=(
                old_zone_relevance
            ),

            new_zone_relevance=(
                new_zone_relevance
            ),
        )
    )


# ============================================================
# main API
# ============================================================

def evaluate_site_rules(
    project_profile: Optional[
        Dict[str, str]
    ] = None,
    procedure_profile: Optional[
        Dict[str, str]
    ] = None,
    base_numeric_context: Optional[
        Dict[str, Any]
    ] = None,
    site_zone_context: Optional[
        str
    ] = None,
    site_condition_context: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    project_profile = (
        project_profile
        or {}
    )

    procedure_profile = (
        procedure_profile
        or {}
    )

    base_numeric_context = (
        base_numeric_context
        or {}
    )

    site_condition_context = (
        site_condition_context
        or {}
    )

    site_zone_context = (
        safe_string(
            site_zone_context
        )
    )

    validate_profile(
        project_profile,
        "PROJECT",
    )

    validate_profile(
        procedure_profile,
        "PROCEDURE",
    )

    # ========================================================
    # load source
    # ========================================================

    site_complete = load_json(
        SITE_COMPLETE_PATH
    )

    downtown_data = load_json(
        SEOUL_DOWNTOWN_PATH
    )

    upper_data = load_json(
        UPPER_BRANCH_PATH
    )

    disaster_data = load_json(
        DISASTER_PATH
    )

    clause_205_data = load_json(
        CLAUSE_205_PATH
    )

    clause_250_data = load_json(
        CLAUSE_250_PATH
    )

    base_numeric = load_json(
        BASE_NUMERIC_PATH
    )

    # ========================================================
    # CLEAN baseline
    # ========================================================

    rules = copy.deepcopy(
        site_complete.get(
            "rules",
            [],
        )
    )

    if (
        len(
            rules
        )
        != 314
    ):

        raise ValueError(
            f"rule count 오류: "
            f"{len(rules)}"
        )

    baseline = Counter(
        rule.get(
            "applicability"
        )
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # current SITE zone
    # ========================================================

    site_zone = (
        site_zone_context
        or safe_string(
            base_numeric.get(
                "site_zone"
            )
        )
    )

    if not site_zone:

        raise ValueError(
            "SITE 용도지역을 결정할 수 없습니다."
        )

    # ========================================================
    # dynamic zone relevance
    # ========================================================

    rules = [

        refresh_rule_zone_relevance(
            rule=(
                rule
            ),

            site_zone=(
                site_zone
            ),
        )

        if isinstance(
            rule,
            dict,
        )

        else rule

        for rule
        in rules
    ]

    # ========================================================
    # zone transition audit
    # ========================================================

    zone_transition_summary = Counter()

    zone_transition_changes = []

    for rule in rules:

        if not isinstance(
            rule,
            dict,
        ):

            continue

        transition = (
            rule.get(
                "zone_transition",
                {},
            )
        )

        status = safe_string(
            transition.get(
                "status"
            )
        )

        if status:

            zone_transition_summary[
                status
            ] += 1

        if (
            status
            and status
            != "NO_APPLICABILITY_TRANSITION"
        ):

            zone_transition_changes.append(
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

                    "zone_relevance": (
                        rule.get(
                            "zone_relevance"
                        )
                    ),

                    "applicability": (
                        rule.get(
                            "applicability"
                        )
                    ),

                    "transition": (
                        transition
                    ),
                }
            )

    # ========================================================
    # base SITE registry
    # ========================================================

    site_registry = (
        build_site_registry(
            downtown_data
        )
    )

    # ========================================================
    # C-15 / C-16 runtime SITE condition overlay
    #
    # runtime 결과가 존재하면 기존 대표 SITE registry보다 우선한다.
    #
    # TRUE / FALSE / UNKNOWN 모두 overlay 대상이다.
    # ========================================================

    site_registry = (
        overlay_runtime_site_conditions(
            site_registry=(
                site_registry
            ),

            site_condition_context=(
                site_condition_context
            ),
        )
    )

    # ========================================================
    # branch conditions
    # ========================================================

    branch_result = (
        apply_branch_local_conditions(
            rules=(
                rules
            ),

            site_zone=(
                site_zone
            ),

            site_registry=(
                site_registry
            ),
        )
    )

    # ========================================================
    # C-16-7-G verified upper-branch condition restoration
    #
    # clause 자체 text에는 predicate가 없지만
    # 상위 법령 branch 분석에서 이미 검증된 condition을 복원한다.
    #
    # 예:
    # clause 189
    #   SITE    방재지구
    #   PROJECT 재해예방시설
    # ========================================================

    upper_branch_condition_result = (
     apply_verified_upper_branch_conditions(
            rules=(
                rules
        ),

            upper_data=(
                upper_data
            ),
        )
    )
    
    after_branch = Counter(
        rule.get(
            "applicability"
        )
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # site registry repair
    #
    # 기존 rule condition + 새 branch condition 모두
    # 최종 runtime registry 기준으로 state/confidence/source를 동기화한다.
    # ========================================================

    site_repairs = (
        apply_site_registry(
            rules=(
                rules
            ),

            site_registry=(
                site_registry
            ),
        )
    )

    # ========================================================
    # project / procedure
    # ========================================================

    injection = (
        inject_profiles(
            rules=(
                rules
            ),

            project_profile=(
                project_profile
            ),

            procedure_profile=(
                procedure_profile
            ),
        )
    )

    final_summary = Counter(
        rule.get(
            "applicability"
        )
        for rule
        in rules
        if isinstance(
            rule,
            dict,
        )
    )

    # ========================================================
    # numeric guards
    # ========================================================

    numeric_guards = (
        build_numeric_guard_registry(
            upper_data=(
                upper_data
            ),

            disaster_data=(
                disaster_data
            ),

            clause_205_data=(
                clause_205_data
            ),

            clause_250_data=(
                clause_250_data
            ),
        )
    )

    numeric_guard_result = (
        apply_numeric_guards(
            rules=(
                rules
            ),

            guards=(
                numeric_guards
            ),
        )
    )

    # ========================================================
    # direct relaxation
    # ========================================================

    direct_relaxation_indexes = {
        4,
        189,
        205,
    }

    retained_direct = [

        rule
        for rule
        in numeric_guard_result[
            "retained"
        ]

        if int(
            rule.get(
                "clause_index"
            )
        )
        in direct_relaxation_indexes
    ]

    # ========================================================
    # base numeric
    # ========================================================

    base_regulation = (
        base_numeric.get(
            "current_base_regulation",
            {},
        )
    )

    dynamic_bcr = (
        base_numeric_context.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
    )

    dynamic_far = (
        base_numeric_context.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
    )

    base_bcr = float(
        dynamic_bcr
        if dynamic_bcr is not None
        else (
            base_regulation.get(
                "building_coverage_ratio",
                {},
            ).get(
                "value",
                50.0,
            )
        )
    )

    base_far = float(
        dynamic_far
        if dynamic_far is not None
        else (
            base_regulation.get(
                "floor_area_ratio",
                {},
            ).get(
                "value",
                250.0,
            )
        )
    )

    # ========================================================
    # numeric resolution
    # ========================================================

    if retained_direct:

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
    # PROJECT / PROCEDURE transitions
    # ========================================================

    transitions = Counter(
        (
            item[
                "before"
            ],
            item[
                "after"
            ],
        )

        for item
        in injection[
            "changes"
        ]
    )

    # ========================================================
    # remaining
    # ========================================================

    remaining_inputs = (
        aggregate_remaining_inputs(
            rules
        )
    )

    # ========================================================
    # external dependency
    # ========================================================

    historical_dependency = (
        site_complete.get(
            "historical_dependency",
            {},
        )
    )

    # ========================================================
    # ready
    # ========================================================

    ready = (
        site_complete.get(
            "site_stage",
            {},
        ).get(
            "rule_engine_ready"
        )
        is True
        and numeric_resolution
        in {
            "BASE_VALUES_RETAINED",
            "RECALC_REQUIRED",
        }
    )

    # ========================================================
    # output
    # ========================================================

    return {

        "pipeline": {

            "ready": (
                ready
            ),

            "version": (
                "C-16-RUNTIME-SPATIAL-CONDITION"
            ),
        },

        "input": {

            "project": (
                project_profile
            ),

            "procedure": (
                procedure_profile
            ),

            "site_zone": (
                site_zone
            ),

            "site_conditions": (
                copy.deepcopy(
                    site_condition_context
                )
            ),
        },

        "site": (
            site_complete.get(
                "site",
                {},
            )
        ),

        "site_zone": (
            site_zone
        ),

        "baseline": (
            dict(
                baseline
            )
        ),

        # ----------------------------------------------------
        # dynamic zone evaluation
        # ----------------------------------------------------

        "zone_evaluation": {

            "site_zone": (
                site_zone
            ),

            "transition_summary": (
                dict(
                    zone_transition_summary
                )
            ),

            "changed_rule_count": (
                len(
                    zone_transition_changes
                )
            ),

            "changes": (
                zone_transition_changes
            ),
        },

        "branch_overlay": {

            "added_condition_count": (
                len(
                    branch_result[
                        "added"
                    ]
                )
            ),

            "added_conditions": (
                branch_result[
                    "added"
                ]
            ),

            "verified_upper_branch_added": (
                upper_branch_condition_result[
                    "added"
                ]
            ),

            "verified_upper_branch_reused": (
                upper_branch_condition_result[
                    "reused"
                 ]
            ),

            "verified_upper_branch_touched_clause_indexes": (
                upper_branch_condition_result[
                    "touched_clause_indexes"
                ]
            ),

            "after_branch": (
                dict(
                    after_branch
                )
            ),
        },

        "site_registry": (
            site_registry
        ),

        "site_repairs": (
            site_repairs
        ),

        "dynamic_injection": {

            "touched_rule_count": (
                len(
                    injection[
                        "touched"
                    ]
                )
            ),

            "changed_rule_count": (
                len(
                    injection[
                        "changes"
                    ]
                )
            ),

            "transitions": {

                f"{before} -> {after}": (
                    count
                )

                for (
                    before,
                    after
                ), count
                in transitions.items()
            },

            "changes": (
                injection[
                    "changes"
                ]
            ),
        },

        "rule_summary": (
            dict(
                final_summary
            )
        ),

        "numeric": {

            "active_before_guard": (
                len(
                    numeric_guard_result[
                        "active"
                    ]
                )
            ),

            "excluded_count": (
                len(
                    numeric_guard_result[
                        "excluded"
                    ]
                )
            ),

            "excluded": (
                numeric_guard_result[
                    "excluded"
                ]
            ),

            "retained_count": (
                len(
                    numeric_guard_result[
                        "retained"
                    ]
                )
            ),

            "retained_clause_indexes": [

                rule.get(
                    "clause_index"
                )

                for rule
                in numeric_guard_result[
                    "retained"
                ]
            ],

            "direct_relaxation_count": (
                len(
                    retained_direct
                )
            ),

            "resolution": (
                numeric_resolution
            ),

            "building_coverage_ratio": (
                confirmed_bcr
            ),

            "floor_area_ratio": (
                confirmed_far
            ),

            "base_context": {

                "site_zone": (
                    site_zone
                ),

                "building_coverage_ratio": (
                    base_bcr
                ),

                "floor_area_ratio": (
                    base_far
                ),

                "dynamic_context_used": (
                    bool(
                        base_numeric_context
                    )
                ),
            },
        },

        "remaining_inputs": (
            remaining_inputs
        ),

        "external_dependencies": {

            "historical": (
                historical_dependency
            ),
        },

        "rules": (
            rules
        ),
    }