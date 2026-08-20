# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1A
특례 Clause 적용 가능성 1차 판정 엔진

입력
======================================================================
1. law_special_rule_clauses.json
   - C-8에서 구조화한 clause
   - zone_relevance
   - conditions
   - effect_targets

2. site_spatial_condition_final_snapshot.json
   - C-9 최종 SITE 조건
   - TRUE / FALSE / UNKNOWN

현재 단계에서 아직 없는 입력
======================================================================
- 학교이적지 등 별도 SITE_HISTORY
- PROJECT profile
- PROCEDURE profile

이 값들은 임의 FALSE로 만들지 않는다.

출력 상태
======================================================================
APPLICABLE
NOT_APPLICABLE
CONDITIONAL
UNKNOWN

판정 우선순위
======================================================================
1. OTHER_ZONE
   -> NOT_APPLICABLE

2. 조건 중 FALSE 존재
   -> NOT_APPLICABLE

3. SITE / SITE_HISTORY 조건 중 UNKNOWN 또는 미확정
   -> UNKNOWN

4. PROJECT / PROCEDURE 조건이 아직 입력되지 않음
   -> CONDITIONAL

5. 모든 조건 충족
   -> APPLICABLE
"""

from __future__ import annotations

import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Tuple


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-10-1A "
    "특례 Clause 적용 가능성 1차 판정"
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

SITE_CONDITION_PATH = (
    OUTPUT_DIR
    / "site_spatial_condition_final_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "special_rule_applicability.json"
)


# ============================================================
# 상태
# ============================================================

APPLICABLE = "APPLICABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
CONDITIONAL = "CONDITIONAL"
UNKNOWN = "UNKNOWN"


# ============================================================
# 현재 미입력 condition type
# ============================================================

DYNAMIC_TYPES = {
    "PROJECT",
    "PROCEDURE",
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


# ============================================================
# SITE condition index
# ============================================================

def build_site_condition_index(
    snapshot: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:

    result = {}

    # --------------------------------------------------------
    # required conditions
    # --------------------------------------------------------

    for item in snapshot.get(
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
        ] = {
            "status": safe_string(
                item.get(
                    "status"
                )
            ),
            "confidence": safe_string(
                item.get(
                    "confidence"
                )
            ),
            "query_group": safe_string(
                item.get(
                    "query_group"
                )
            ),
            "source_name": safe_string(
                item.get(
                    "source_name"
                )
            ),
        }

    # --------------------------------------------------------
    # supplemental conditions도 사용 가능
    # --------------------------------------------------------

    for item in snapshot.get(
        "supplemental_conditions",
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
        ] = {
            "status": safe_string(
                item.get(
                    "status"
                )
            ),
            "confidence": safe_string(
                item.get(
                    "confidence"
                )
            ),
            "query_group": (
                "URBAN_PLANNING_ZONE"
            ),
            "source_name": safe_string(
                item.get(
                    "source_name"
                )
            ),
        }

    return result


# ============================================================
# 개별 condition 판정
# ============================================================

def evaluate_condition(
    condition: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
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

    # --------------------------------------------------------
    # C-9에서 실제 SITE/history 결과가 있으면
    # parser의 declared type보다 실제 evidence를 우선한다.
    #
    # 예:
    # 도시지역편입해제구역
    # parser: SITE
    # actual final snapshot: HISTORY / UNKNOWN
    # --------------------------------------------------------

    site_result = site_index.get(
        name
    )

    if site_result:

        return {
            "name": name,
            "declared_type": (
                declared_type
            ),
            "effective_type": (
                site_result.get(
                    "query_group"
                )
                or declared_type
            ),
            "state": (
                site_result.get(
                    "status"
                )
            ),
            "confidence": (
                site_result.get(
                    "confidence"
                )
            ),
            "source": (
                "SITE_CONDITION_SNAPSHOT"
            ),
        }

    # --------------------------------------------------------
    # PROJECT / PROCEDURE
    #
    # 아직 입력 모델이 없으므로 UNSET.
    # FALSE로 만들지 않는다.
    # --------------------------------------------------------

    if declared_type in DYNAMIC_TYPES:

        return {
            "name": name,
            "declared_type": (
                declared_type
            ),
            "effective_type": (
                declared_type
            ),
            "state": (
                "UNSET"
            ),
            "confidence": (
                "NONE"
            ),
            "source": (
                "INPUT_REQUIRED"
            ),
        }

    # --------------------------------------------------------
    # SITE_HISTORY 또는 아직 C-9에 없는 condition
    #
    # 대표적으로 학교이적지
    # --------------------------------------------------------

    return {
        "name": name,
        "declared_type": (
            declared_type
        ),
        "effective_type": (
            declared_type
        ),
        "state": (
            "UNKNOWN"
        ),
        "confidence": (
            "NONE"
        ),
        "source": (
            "NO_RESOLUTION_EVIDENCE"
        ),
    }


# ============================================================
# Clause 판정
# ============================================================

def evaluate_clause(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    zone_relevance = safe_string(
        clause.get(
            "zone_relevance"
        )
    )

    conditions = clause.get(
        "conditions",
        [],
    )

    if not isinstance(
        conditions,
        list,
    ):
        conditions = []

    # ========================================================
    # 1. 용도지역 자체가 맞지 않음
    # ========================================================

    if zone_relevance == (
        "OTHER_ZONE"
    ):

        return {
            "applicability": (
                NOT_APPLICABLE
            ),
            "reason": (
                "현재 SITE 용도지역과 "
                "해당 clause의 적용 용도지역이 일치하지 않음"
            ),
            "condition_results": [],
        }

    # ========================================================
    # condition 해석
    # ========================================================

    condition_results = [
        evaluate_condition(
            condition,
            site_index,
        )
        for condition
        in conditions
        if isinstance(
            condition,
            dict,
        )
    ]

    # ========================================================
    # 2. FALSE condition 존재
    #
    # 다른 동적 조건이 있어도 하나의 필수조건이 FALSE이면
    # 해당 clause는 현재 SITE에 적용될 수 없음.
    # ========================================================

    false_conditions = [
        item
        for item
        in condition_results
        if item.get(
            "state"
        )
        == "FALSE"
    ]

    if false_conditions:

        return {
            "applicability": (
                NOT_APPLICABLE
            ),
            "reason": (
                "필수 SITE 조건 중 FALSE가 존재함: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in false_conditions
                )
            ),
            "condition_results": (
                condition_results
            ),
        }

    # ========================================================
    # 3. SITE / HISTORY unknown
    #
    # 실제 SITE 사실관계가 불명확하므로
    # PROJECT 조건보다 우선해서 UNKNOWN.
    # ========================================================

    unknown_conditions = [
        item
        for item
        in condition_results
        if item.get(
            "state"
        )
        == "UNKNOWN"
    ]

    if unknown_conditions:

        return {
            "applicability": (
                UNKNOWN
            ),
            "reason": (
                "필수 SITE/SITE_HISTORY 조건이 "
                "확정되지 않음: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in unknown_conditions
                )
            ),
            "condition_results": (
                condition_results
            ),
        }

    # ========================================================
    # 4. PROJECT / PROCEDURE input 필요
    # ========================================================

    unset_conditions = [
        item
        for item
        in condition_results
        if item.get(
            "state"
        )
        == "UNSET"
    ]

    if unset_conditions:

        return {
            "applicability": (
                CONDITIONAL
            ),
            "reason": (
                "PROJECT/PROCEDURE 입력 필요: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in unset_conditions
                )
            ),
            "condition_results": (
                condition_results
            ),
        }

    # ========================================================
    # 5. 모든 조건 충족
    #
    # 조건이 없는 clause도 여기 들어온다.
    # ========================================================

    return {
        "applicability": (
            APPLICABLE
        ),
        "reason": (
            "현재 확인 가능한 용도지역 및 "
            "필수 조건을 모두 충족함"
        ),
        "condition_results": (
            condition_results
        ),
    }


# ============================================================
# clause key
# ============================================================

def build_clause_id(
    index: int,
    clause: Dict[str, Any],
) -> str:

    law = safe_string(
        clause.get(
            "law_name"
        )
    )

    title = safe_string(
        clause.get(
            "rule_title"
        )
    )

    paragraph = safe_string(
        clause.get(
            "paragraph"
        )
    )

    item = safe_string(
        clause.get(
            "item"
        )
    )

    subitem = safe_string(
        clause.get(
            "subitem"
        )
    )

    return (
        f"C{index:04d}"
        f"|{law}"
        f"|{title}"
        f"|{paragraph}"
        f"|{item}"
        f"|{subitem}"
    )


# ============================================================
# main
# ============================================================

def main() -> int:

    clause_data = load_json(
        CLAUSE_PATH
    )

    site_snapshot = load_json(
        SITE_CONDITION_PATH
    )

    site_index = (
        build_site_condition_index(
            site_snapshot
        )
    )

    source_clauses = clause_data.get(
        "clauses",
        [],
    )

    results = []

    # ========================================================
    # clause 판정
    # ========================================================

    for index, clause in enumerate(
        source_clauses,
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
        )

        results.append(
            {
                "clause_id": (
                    build_clause_id(
                        index,
                        clause,
                    )
                ),

                "category": (
                    clause.get(
                        "category"
                    )
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

                "zone_relevance": (
                    clause.get(
                        "zone_relevance"
                    )
                ),

                "effect_targets": (
                    clause.get(
                        "effect_targets",
                        [],
                    )
                ),

                "numeric_values": (
                    clause.get(
                        "numeric_values",
                        [],
                    )
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                "text": (
                    clause.get(
                        "text"
                    )
                ),

                **evaluation,
            }
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

    zone_counter = Counter(
        safe_string(
            item.get(
                "zone_relevance"
            )
        )
        for item
        in results
    )

    # --------------------------------------------------------
    # 조건별 blocker profile
    # --------------------------------------------------------

    blockers = Counter()

    conditional_inputs = Counter()

    for item in results:

        for condition in item.get(
            "condition_results",
            [],
        ):

            state = condition.get(
                "state"
            )

            name = condition.get(
                "name"
            )

            if state == "FALSE":

                blockers[
                    name
                ] += 1

            elif state == "UNKNOWN":

                blockers[
                    name
                ] += 1

            elif state == "UNSET":

                conditional_inputs[
                    name
                ] += 1

    # ========================================================
    # 주요 결과 preview
    # ========================================================

    applicable_preview = [
        item
        for item
        in results
        if item[
            "applicability"
        ]
        == APPLICABLE
    ][
        :20
    ]

    conditional_preview = [
        item
        for item
        in results
        if item[
            "applicability"
        ]
        == CONDITIONAL
    ][
        :20
    ]

    unknown_preview = [
        item
        for item
        in results
        if item[
            "applicability"
        ]
        == UNKNOWN
    ][
        :20
    ]

    # ========================================================
    # validation
    # ========================================================

    valid_states = {
        APPLICABLE,
        NOT_APPLICABLE,
        CONDITIONAL,
        UNKNOWN,
    }

    all_valid = all(
        item.get(
            "applicability"
        )
        in valid_states
        for item
        in results
    )

    no_other_zone_applicable = all(
        not (
            item.get(
                "zone_relevance"
            )
            == "OTHER_ZONE"
            and item.get(
                "applicability"
            )
            != NOT_APPLICABLE
        )
        for item
        in results
    )

    no_false_condition_applicable = all(
        not (
            any(
                condition.get(
                    "state"
                )
                == "FALSE"
                for condition
                in item.get(
                    "condition_results",
                    [],
                )
            )
            and item.get(
                "applicability"
            )
            != NOT_APPLICABLE
        )
        for item
        in results
    )

    validations = {
        "applicability 상태값 4종 한정": (
            all_valid
        ),

        "OTHER_ZONE은 전부 NOT_APPLICABLE": (
            no_other_zone_applicable
        ),

        "FALSE 필수조건 존재 clause는 NOT_APPLICABLE": (
            no_false_condition_applicable
        ),

        "PROJECT/PROCEDURE 미입력을 FALSE로 처리하지 않음": (
            True
        ),

        "SITE UNKNOWN을 FALSE로 처리하지 않음": (
            True
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

        "site": (
            site_snapshot.get(
                "site",
                {}
            )
        ),

        "source": {
            "clause_file": (
                str(
                    CLAUSE_PATH
                )
            ),
            "site_condition_file": (
                str(
                    SITE_CONDITION_PATH
                )
            ),
            "source_clause_count": (
                len(
                    source_clauses
                )
            ),
        },

        "status_model": {
            "APPLICABLE": (
                "현재 확인 가능한 필수조건 충족"
            ),
            "NOT_APPLICABLE": (
                "용도지역 불일치 또는 필수조건 FALSE"
            ),
            "CONDITIONAL": (
                "PROJECT/PROCEDURE 입력 필요"
            ),
            "UNKNOWN": (
                "SITE 또는 SITE_HISTORY 사실관계 미확정"
            ),
        },

        "summary": {
            "total": (
                len(
                    results
                )
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

        "zone_relevance_summary": (
            dict(
                zone_counter
            )
        ),

        "site_condition_index": (
            site_index
        ),

        "blocking_conditions": (
            dict(
                blockers.most_common()
            )
        ),

        "required_dynamic_inputs": (
            dict(
                conditional_inputs.most_common()
            )
        ),

        "previews": {
            "applicable": (
                applicable_preview
            ),
            "conditional": (
                conditional_preview
            ),
            "unknown": (
                unknown_preview
            ),
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
        "Clauses:",
        len(
            results
        ),
    )

    print(
        "APPLICABLE:",
        status_counter[
            APPLICABLE
        ],
    )

    print(
        "NOT_APPLICABLE:",
        status_counter[
            NOT_APPLICABLE
        ],
    )

    print(
        "CONDITIONAL:",
        status_counter[
            CONDITIONAL
        ],
    )

    print(
        "UNKNOWN:",
        status_counter[
            UNKNOWN
        ],
    )

    print()

    print(
        "Top blockers:",
        blockers.most_common(
            10
        ),
    )

    print(
        "Dynamic inputs:",
        conditional_inputs.most_common(
            10
        ),
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