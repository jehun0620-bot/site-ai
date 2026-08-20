# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1E
SITE + ProjectProfile + ProcedureProfile
Full Clause Applicability 통합 검증

입력
======================================================================
1. law_special_rule_clauses.json
2. site_spatial_condition_final_snapshot.json
3. project_profile_template.json
4. procedure_profile_template.json

semantic override
======================================================================
기존공장:
    parser PROJECT
    -> effective SITE_HISTORY

판정 우선순위
======================================================================
1. OTHER_ZONE
   -> NOT_APPLICABLE

2. 하나 이상의 필수조건 FALSE
   -> NOT_APPLICABLE

3. 하나 이상의 필수조건 UNKNOWN
   -> UNKNOWN

4. 하나 이상의 PROJECT / PROCEDURE 조건 UNSET
   -> CONDITIONAL

5. 모든 필수조건 TRUE
   -> APPLICABLE

주의
======================================================================
- UNSET != FALSE
- UNKNOWN != FALSE
- PROJECT/PROCEDURE TRUE 하나만으로 APPLICABLE 보장 안 됨
- OTHER_ZONE은 다른 조건 입력으로 뒤집을 수 없음
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-1E "
    "Full Clause Applicability 통합 검증"
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
    / "full_condition_applicability_integration.json"
)


# ============================================================
# 상태
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

            result[
                name
            ] = {
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
# generic profile index
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

        result[
            name
        ] = {
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

            "field": safe_string(
                item.get(
                    "field"
                )
            ),

            "source": (
                source_name
            ),
        }

    return result


# ============================================================
# scenario input
# ============================================================

def apply_scenario(
    profile: Dict[str, Any],
    values: Dict[str, bool],
    source_name: str,
) -> Dict[str, Any]:

    result = copy.deepcopy(
        profile
    )

    for item in result.get(
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

        if name not in values:
            continue

        value = bool(
            values[
                name
            ]
        )

        item[
            "value"
        ] = value

        item[
            "state"
        ] = (
            "TRUE"
            if value
            else "FALSE"
        )

        item[
            "confidence"
        ] = "HIGH"

        item[
            "source"
        ] = source_name

    return result


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
                "declared_type": (
                    declared_type
                ),
                "effective_type": (
                    effective_type
                ),
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
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
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
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
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
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
                **value,
            }

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
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
        "state": "UNKNOWN",
        "confidence": "NONE",
        "source": (
            "UNKNOWN_CONDITION_TYPE"
        ),
    }


# ============================================================
# Clause evaluate
# ============================================================

def evaluate_clause(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
    procedure_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    zone_relevance = safe_string(
        clause.get(
            "zone_relevance"
        )
    )

    # --------------------------------------------------------
    # OTHER_ZONE
    # --------------------------------------------------------

    if zone_relevance == (
        "OTHER_ZONE"
    ):

        return {
            "applicability": (
                NOT_APPLICABLE
            ),

            "reason": (
                "현재 SITE 용도지역과 "
                "clause 적용 용도지역 불일치"
            ),

            "condition_results": [],
        }

    conditions = clause.get(
        "conditions",
        [],
    )

    if not isinstance(
        conditions,
        list,
    ):

        conditions = []

    results = [
        evaluate_condition(
            condition,
            site_index,
            project_index,
            procedure_index,
        )

        for condition
        in conditions

        if isinstance(
            condition,
            dict,
        )
    ]

    # --------------------------------------------------------
    # FALSE
    # --------------------------------------------------------

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

            "condition_results": (
                results
            ),
        }

    # --------------------------------------------------------
    # UNKNOWN
    # --------------------------------------------------------

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
                "필수조건 사실관계 미확정: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in unknown_values
                )
            ),

            "condition_results": (
                results
            ),
        }

    # --------------------------------------------------------
    # UNSET
    # --------------------------------------------------------

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

            "condition_results": (
                results
            ),
        }

    # --------------------------------------------------------
    # all TRUE / no condition
    # --------------------------------------------------------

    return {
        "applicability": (
            APPLICABLE
        ),

        "reason": (
            "현재 용도지역 및 모든 필수조건 충족"
        ),

        "condition_results": (
            results
        ),
    }


# ============================================================
# 전체 실행
# ============================================================

def evaluate_all(
    clauses: List[Dict[str, Any]],
    site_index: Dict[str, Dict[str, Any]],
    project_profile: Dict[str, Any],
    procedure_profile: Dict[str, Any],
) -> Dict[str, Any]:

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

        results.append(
            {
                "clause_index": index,

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

                "zone_relevance": (
                    clause.get(
                        "zone_relevance"
                    )
                ),

                "conditions": (
                    clause.get(
                        "conditions",
                        [],
                    )
                ),

                **evaluation,
            }
        )

    counter = Counter(
        item[
            "applicability"
        ]
        for item
        in results
    )

    return {
        "summary": {
            "total": (
                len(
                    results
                )
            ),

            "applicable": (
                counter[
                    APPLICABLE
                ]
            ),

            "not_applicable": (
                counter[
                    NOT_APPLICABLE
                ]
            ),

            "conditional": (
                counter[
                    CONDITIONAL
                ]
            ),

            "unknown": (
                counter[
                    UNKNOWN
                ]
            ),
        },

        "clauses": (
            results
        ),
    }


# ============================================================
# 변화
# ============================================================

def compare_results(
    before: Dict[str, Any],
    after: Dict[str, Any],
) -> Dict[str, Any]:

    transitions = Counter()

    changed = []

    for old, new in zip(
        before[
            "clauses"
        ],
        after[
            "clauses"
        ],
    ):

        old_state = old[
            "applicability"
        ]

        new_state = new[
            "applicability"
        ]

        if old_state == new_state:
            continue

        key = (
            f"{old_state}"
            f" -> "
            f"{new_state}"
        )

        transitions[
            key
        ] += 1

        changed.append(
            {
                "clause_index": (
                    old[
                        "clause_index"
                    ]
                ),

                "rule_title": (
                    old.get(
                        "rule_title"
                    )
                ),

                "before": (
                    old_state
                ),

                "after": (
                    new_state
                ),
            }
        )

    return {
        "changed_count": (
            len(
                changed
            )
        ),

        "transitions": (
            dict(
                transitions
            )
        ),

        "preview": (
            changed[:30]
        ),
    }


# ============================================================
# condition injection
# ============================================================

def analyze_injection(
    result: Dict[str, Any],
    condition_name: str,
    expected_state: str,
) -> Dict[str, Any]:

    declared_count = 0
    evaluated_count = 0
    matching_count = 0

    for clause in result[
        "clauses"
    ]:

        has_condition = any(
            isinstance(
                condition,
                dict,
            )
            and safe_string(
                condition.get(
                    "name"
                )
            )
            == condition_name

            for condition
            in clause.get(
                "conditions",
                [],
            )
        )

        if not has_condition:
            continue

        declared_count += 1

        for condition in clause.get(
            "condition_results",
            [],
        ):

            if condition.get(
                "name"
            ) != condition_name:
                continue

            evaluated_count += 1

            if condition.get(
                "state"
            ) == expected_state:

                matching_count += 1

    return {
        "declared_clause_count": (
            declared_count
        ),

        "evaluated_count": (
            evaluated_count
        ),

        "matching_count": (
            matching_count
        ),

        "all_evaluated_match": (
            evaluated_count > 0
            and evaluated_count
            == matching_count
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

    project_template = load_json(
        PROJECT_PATH
    )

    procedure_template = load_json(
        PROCEDURE_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    site_index = build_site_index(
        site_snapshot
    )

    # ========================================================
    # BASELINE
    # ========================================================

    baseline = evaluate_all(
        clauses,
        site_index,
        project_template,
        procedure_template,
    )

    # ========================================================
    # SCENARIO 1
    #
    # 공동주택 TRUE
    # 도시계획위원회심의 TRUE
    # ========================================================

    project_s1 = apply_scenario(
        project_template,
        {
            "공동주택": True,
        },
        "TEST_PROJECT_INPUT",
    )

    procedure_s1 = apply_scenario(
        procedure_template,
        {
            "도시계획위원회심의": True,
        },
        "TEST_PROCEDURE_INPUT",
    )

    scenario_1 = evaluate_all(
        clauses,
        site_index,
        project_s1,
        procedure_s1,
    )

    scenario_1_change = (
        compare_results(
            baseline,
            scenario_1,
        )
    )

    project_true_injection = (
        analyze_injection(
            scenario_1,
            "공동주택",
            "TRUE",
        )
    )

    procedure_true_injection = (
        analyze_injection(
            scenario_1,
            "도시계획위원회심의",
            "TRUE",
        )
    )

    # ========================================================
    # SCENARIO 2
    #
    # 공동주택 TRUE
    # 도시계획위원회심의 FALSE
    # ========================================================

    project_s2 = apply_scenario(
        project_template,
        {
            "공동주택": True,
        },
        "TEST_PROJECT_INPUT",
    )

    procedure_s2 = apply_scenario(
        procedure_template,
        {
            "도시계획위원회심의": False,
        },
        "TEST_PROCEDURE_INPUT",
    )

    scenario_2 = evaluate_all(
        clauses,
        site_index,
        project_s2,
        procedure_s2,
    )

    scenario_2_change = (
        compare_results(
            baseline,
            scenario_2,
        )
    )

    procedure_false_injection = (
        analyze_injection(
            scenario_2,
            "도시계획위원회심의",
            "FALSE",
        )
    )

    # ========================================================
    # OTHER_ZONE 보호
    # ========================================================

    no_other_zone_flip = all(
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
        in (
            scenario_1[
                "clauses"
            ]
            + scenario_2[
                "clauses"
            ]
        )
    )

    # ========================================================
    # FALSE procedure exclusion
    # ========================================================

    false_exclusion = any(
        key.endswith(
            "-> NOT_APPLICABLE"
        )

        for key
        in scenario_2_change[
            "transitions"
        ]
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {
        "baseline 314 clauses 유지": (
            baseline[
                "summary"
            ][
                "total"
            ]
            == 314
        ),

        "공동주택 TRUE 주입 성공": (
            project_true_injection[
                "all_evaluated_match"
            ]
        ),

        "도시계획위원회심의 TRUE 주입 성공": (
            procedure_true_injection[
                "all_evaluated_match"
            ]
        ),

        "도시계획위원회심의 FALSE 주입 성공": (
            procedure_false_injection[
                "all_evaluated_match"
            ]
        ),

        "PROCEDURE FALSE가 최소 하나의 clause를 배제": (
            false_exclusion
        ),

        "PROJECT/PROCEDURE 입력으로 OTHER_ZONE 뒤집힘 없음": (
            no_other_zone_flip
        ),

        "semantic override 기존공장=SITE_HISTORY": (
            CONDITION_TYPE_OVERRIDES.get(
                "기존공장"
            )
            == "SITE_HISTORY"
        ),
    }

    all_pass = all(
        validations.values()
    )

    output = {
        "step": (
            STEP_NAME
        ),

        "baseline": {
            "summary": (
                baseline[
                    "summary"
                ]
            ),
        },

        "scenario_1": {
            "inputs": {
                "PROJECT": {
                    "공동주택": True,
                },

                "PROCEDURE": {
                    "도시계획위원회심의": True,
                },
            },

            "summary": (
                scenario_1[
                    "summary"
                ]
            ),

            "change": (
                scenario_1_change
            ),

            "project_injection": (
                project_true_injection
            ),

            "procedure_injection": (
                procedure_true_injection
            ),
        },

        "scenario_2": {
            "inputs": {
                "PROJECT": {
                    "공동주택": True,
                },

                "PROCEDURE": {
                    "도시계획위원회심의": False,
                },
            },

            "summary": (
                scenario_2[
                    "summary"
                ]
            ),

            "change": (
                scenario_2_change
            ),

            "procedure_injection": (
                procedure_false_injection
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
    # concise console
    # ========================================================

    print(
        "Baseline:",
        baseline[
            "summary"
        ],
    )

    print()

    print(
        "Scenario 1 "
        "(공동주택 TRUE / 심의 TRUE):",
        scenario_1[
            "summary"
        ],
    )

    print(
        "Changed:",
        scenario_1_change[
            "changed_count"
        ],
    )

    print(
        "Transitions:",
        scenario_1_change[
            "transitions"
        ],
    )

    print()

    print(
        "Scenario 2 "
        "(공동주택 TRUE / 심의 FALSE):",
        scenario_2[
            "summary"
        ],
    )

    print(
        "Changed:",
        scenario_2_change[
            "changed_count"
        ],
    )

    print(
        "Transitions:",
        scenario_2_change[
            "transitions"
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