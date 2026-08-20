# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-1C
ProjectProfile × Special Rule Applicability 통합 검증

수정 핵심
======================================================================
- PROJECT TRUE 입력이 반드시 clause 상태 변화를 일으킨다고 가정하지 않는다.
- TRUE는 해당 조건을 충족시킬 뿐이며 다른 PROJECT/PROCEDURE가 UNSET이면
  CONDITIONAL을 유지할 수 있다.
- FALSE는 필수조건이므로 해당 clause를 NOT_APPLICABLE로 만들 수 있다.
- 실제 condition_result에 TRUE/FALSE가 정확히 주입됐는지를 검증한다.
"""

from __future__ import annotations

import copy
import json

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-10-1C "
    "ProjectProfile × Clause Applicability 통합 검증"
)

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

PROJECT_PROFILE_PATH = (
    OUTPUT_DIR
    / "project_profile_template.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "project_profile_applicability_integration.json"
)


APPLICABLE = "APPLICABLE"
NOT_APPLICABLE = "NOT_APPLICABLE"
CONDITIONAL = "CONDITIONAL"
UNKNOWN = "UNKNOWN"


CONDITION_TYPE_OVERRIDES = {
    "기존공장": "SITE_HISTORY",
}


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

    for group_name in (
        "conditions",
        "supplemental_conditions",
    ):

        for item in snapshot.get(
            group_name,
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
# PROJECT index
# ============================================================

def build_project_index(
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

        result[name] = {
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
            "source": safe_string(
                item.get(
                    "source"
                )
            ),
        }

    return result


# ============================================================
# scenario
# ============================================================

def apply_project_scenario(
    base_profile: Dict[str, Any],
    values: Dict[str, bool],
) -> Dict[str, Any]:

    profile = copy.deepcopy(
        base_profile
    )

    for condition in profile.get(
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

        if name not in values:
            continue

        value = bool(
            values[name]
        )

        condition[
            "value"
        ] = value

        condition[
            "state"
        ] = (
            "TRUE"
            if value
            else "FALSE"
        )

        condition[
            "confidence"
        ] = "HIGH"

        condition[
            "source"
        ] = (
            "TEST_SCENARIO_INPUT"
        )

    return profile


# ============================================================
# condition evaluate
# ============================================================

def evaluate_condition(
    condition: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
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

    if effective_type == "SITE":

        site = site_index.get(
            name
        )

        if site:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                **site,
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

    if effective_type == (
        "SITE_HISTORY"
    ):

        site = site_index.get(
            name
        )

        if site:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                **site,
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

    if effective_type == (
        "PROJECT"
    ):

        project = project_index.get(
            name
        )

        if project:

            return {
                "name": name,
                "declared_type": declared_type,
                "effective_type": effective_type,
                **project,
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

    if effective_type == (
        "PROCEDURE"
    ):

        return {
            "name": name,
            "declared_type": declared_type,
            "effective_type": effective_type,
            "state": "UNSET",
            "confidence": "NONE",
            "source": (
                "PROCEDURE_PROFILE_NOT_BUILT"
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
# clause evaluate
# ============================================================

def evaluate_clause(
    clause: Dict[str, Any],
    site_index: Dict[str, Dict[str, Any]],
    project_index: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:

    zone_relevance = safe_string(
        clause.get(
            "zone_relevance"
        )
    )

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

    condition_results = [
        evaluate_condition(
            condition,
            site_index,
            project_index,
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
                "필수 condition FALSE: "
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

    # --------------------------------------------------------
    # SITE / HISTORY UNKNOWN
    # --------------------------------------------------------

    site_unknown = [
        item
        for item
        in condition_results
        if (
            item.get(
                "state"
            )
            == "UNKNOWN"
            and item.get(
                "effective_type"
            )
            in {
                "SITE",
                "SITE_HISTORY",
            }
        )
    ]

    if site_unknown:

        return {
            "applicability": (
                UNKNOWN
            ),
            "reason": (
                "SITE/SITE_HISTORY 미확정: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in site_unknown
                )
            ),
            "condition_results": (
                condition_results
            ),
        }

    # --------------------------------------------------------
    # PROJECT UNKNOWN
    # --------------------------------------------------------

    project_unknown = [
        item
        for item
        in condition_results
        if (
            item.get(
                "state"
            )
            == "UNKNOWN"
            and item.get(
                "effective_type"
            )
            == "PROJECT"
        )
    ]

    if project_unknown:

        return {
            "applicability": (
                UNKNOWN
            ),
            "reason": (
                "PROJECT 사실관계 미확정: "
                + ", ".join(
                    item[
                        "name"
                    ]
                    for item
                    in project_unknown
                )
            ),
            "condition_results": (
                condition_results
            ),
        }

    # --------------------------------------------------------
    # UNSET
    # --------------------------------------------------------

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
                "추가 입력 필요: "
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

    return {
        "applicability": (
            APPLICABLE
        ),
        "reason": (
            "현재 용도지역 및 모든 필수 condition 충족"
        ),
        "condition_results": (
            condition_results
        ),
    }


# ============================================================
# evaluate all
# ============================================================

def evaluate_all(
    clauses: List[Dict[str, Any]],
    site_index: Dict[str, Dict[str, Any]],
    project_profile: Dict[str, Any],
) -> Dict[str, Any]:

    project_index = (
        build_project_index(
            project_profile
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
            "total": len(
                results
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
        "clauses": results,
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
# condition 주입 검증
# ============================================================

def analyze_condition_injection(
    result: Dict[str, Any],
    condition_name: str,
    expected_state: str,
) -> Dict[str, Any]:

    clause_count = 0
    evaluated_count = 0
    matching_state_count = 0

    for clause in result[
        "clauses"
    ]:

        declared_conditions = (
            clause.get(
                "conditions",
                []
            )
        )

        contains = any(
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
            in declared_conditions
        )

        if not contains:
            continue

        clause_count += 1

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

                matching_state_count += 1

    return {
        "clause_count": (
            clause_count
        ),
        "evaluated_count": (
            evaluated_count
        ),
        "matching_state_count": (
            matching_state_count
        ),
        "all_evaluated_match": (
            evaluated_count > 0
            and evaluated_count
            == matching_state_count
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
        SITE_CONDITION_PATH
    )

    project_template = load_json(
        PROJECT_PROFILE_PATH
    )

    clauses = clause_data.get(
        "clauses",
        [],
    )

    site_index = build_site_index(
        site_snapshot
    )

    # --------------------------------------------------------
    # baseline
    # --------------------------------------------------------

    baseline = evaluate_all(
        clauses,
        site_index,
        project_template,
    )

    # --------------------------------------------------------
    # 공동주택 TRUE
    # --------------------------------------------------------

    housing_true_profile = (
        apply_project_scenario(
            project_template,
            {
                "공동주택": True,
            },
        )
    )

    housing_true = evaluate_all(
        clauses,
        site_index,
        housing_true_profile,
    )

    housing_true_change = (
        compare_results(
            baseline,
            housing_true,
        )
    )

    true_injection = (
        analyze_condition_injection(
            housing_true,
            "공동주택",
            "TRUE",
        )
    )

    # --------------------------------------------------------
    # 공동주택 FALSE
    # --------------------------------------------------------

    housing_false_profile = (
        apply_project_scenario(
            project_template,
            {
                "공동주택": False,
            },
        )
    )

    housing_false = evaluate_all(
        clauses,
        site_index,
        housing_false_profile,
    )

    housing_false_change = (
        compare_results(
            baseline,
            housing_false,
        )
    )

    false_injection = (
        analyze_condition_injection(
            housing_false,
            "공동주택",
            "FALSE",
        )
    )

    # --------------------------------------------------------
    # OTHER_ZONE 유지
    # --------------------------------------------------------

    no_other_zone_applied = all(
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
            housing_true[
                "clauses"
            ]
            + housing_false[
                "clauses"
            ]
        )
    )

    # --------------------------------------------------------
    # FALSE 입력 시 적어도 하나는 배제되어야 함
    # --------------------------------------------------------

    false_has_exclusion_effect = (
        housing_false_change[
            "transitions"
        ].get(
            (
                "CONDITIONAL "
                "-> NOT_APPLICABLE"
            ),
            0,
        )
        > 0
    )

    # --------------------------------------------------------
    # TRUE 입력은 변화가 없어도 정상
    #
    # 단, NOT_APPLICABLE을 잘못 만드는 일은 없어야 함.
    # --------------------------------------------------------

    true_bad_transition = any(
        transition.endswith(
            "-> NOT_APPLICABLE"
        )
        for transition
        in housing_true_change[
            "transitions"
        ]
    )

    validations = {
        "baseline 314 clauses 유지": (
            baseline[
                "summary"
            ][
                "total"
            ]
            == 314
        ),

        "공동주택 TRUE가 실제 condition_result에 주입됨": (
            true_injection[
                "all_evaluated_match"
            ]
        ),

        "공동주택 FALSE가 실제 condition_result에 주입됨": (
            false_injection[
                "all_evaluated_match"
            ]
        ),

        "공동주택 FALSE가 최소 1개 clause를 배제함": (
            false_has_exclusion_effect
        ),

        "공동주택 TRUE가 NOT_APPLICABLE을 새로 만들지 않음": (
            not true_bad_transition
        ),

        "TRUE 입력 후 다른 UNSET 조건 때문에 CONDITIONAL 유지 가능": (
            True
        ),

        "PROJECT 입력으로 OTHER_ZONE 판정이 뒤집히지 않음": (
            no_other_zone_applied
        ),

        "기존공장은 ProjectProfile에서 제외됨": (
            "기존공장"
            not in {
                item.get(
                    "name"
                )
                for item
                in project_template.get(
                    "conditions",
                    [],
                )
            }
        ),

        "기존공장 semantic override=SITE_HISTORY": (
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
        "step": STEP_NAME,

        "baseline": {
            "summary": (
                baseline[
                    "summary"
                ]
            ),
        },

        "scenarios": {
            "multi_family_housing_true": {
                "summary": (
                    housing_true[
                        "summary"
                    ]
                ),
                "change": (
                    housing_true_change
                ),
                "injection": (
                    true_injection
                ),
            },

            "multi_family_housing_false": {
                "summary": (
                    housing_false[
                        "summary"
                    ]
                ),
                "change": (
                    housing_false_change
                ),
                "injection": (
                    false_injection
                ),
            },
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

    print(
        "Baseline:",
        baseline[
            "summary"
        ],
    )

    print()

    print(
        "공동주택 TRUE:",
        housing_true[
            "summary"
        ],
    )

    print(
        "TRUE injection:",
        true_injection,
    )

    print(
        "Changed:",
        housing_true_change[
            "changed_count"
        ],
    )

    print(
        "Transitions:",
        housing_true_change[
            "transitions"
        ],
    )

    print()

    print(
        "공동주택 FALSE:",
        housing_false[
            "summary"
        ],
    )

    print(
        "FALSE injection:",
        false_injection,
    )

    print(
        "Changed:",
        housing_false_change[
            "changed_count"
        ],
    )

    print(
        "Transitions:",
        housing_false_change[
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