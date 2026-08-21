# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-5C-3
Rule Evaluation Pipeline Stateless Regression Test

목표
======================================================================
evaluate_site_rules()를 여러 번 연속 호출했을 때
이전 호출의 PROJECT / PROCEDURE 입력이나 condition state가
다음 호출에 남지 않는지 검증한다.

각 호출은 반드시:
site_rule_evaluation_site_complete.json
clean baseline에서 새로 시작해야 한다.
"""

from __future__ import annotations

from rule_evaluation_pipeline import (
    evaluate_site_rules,
)


def summarize(
    result,
):

    return {
        "baseline": (
            result[
                "baseline"
            ]
        ),

        "final": (
            result[
                "rule_summary"
            ]
        ),

        "dynamic": (
            result[
                "dynamic_injection"
            ]
        ),

        "numeric": (
            result[
                "numeric"
            ]
        ),
    }


def find_condition_state(
    result,
    clause_index,
    condition_name,
):

    for rule in result.get(
        "rules",
        [],
    ):

        if int(
            rule.get(
                "clause_index",
                -1,
            )
        ) != clause_index:

            continue

        for condition in rule.get(
            "conditions",
            [],
        ):

            if (
                condition.get(
                    "name"
                )
                == condition_name
            ):

                return condition.get(
                    "state"
                )

    return None


def main() -> int:

    # ========================================================
    # Scenario A
    # ========================================================

    scenario_a = (
        evaluate_site_rules(
            project_profile={
                "공동주택": (
                    "TRUE"
                ),
            },

            procedure_profile={
                "도시계획위원회심의": (
                    "TRUE"
                ),
            },
        )
    )

    # ========================================================
    # Scenario B
    # ========================================================

    scenario_b = (
        evaluate_site_rules(
            project_profile={
                "공동주택": (
                    "FALSE"
                ),
            },

            procedure_profile={
                "도시계획위원회심의": (
                    "TRUE"
                ),
            },
        )
    )

    # ========================================================
    # Scenario C
    # ========================================================

    scenario_c = (
        evaluate_site_rules(
            project_profile={},
            procedure_profile={},
        )
    )

    a = summarize(
        scenario_a
    )

    b = summarize(
        scenario_b
    )

    c = summarize(
        scenario_c
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "=== SCENARIO A ==="
    )

    print(
        "Input:",
        scenario_a[
            "input"
        ],
    )

    print(
        "Baseline:",
        a[
            "baseline"
        ],
    )

    print(
        "Final:",
        a[
            "final"
        ],
    )

    print(
        "Changed:",
        a[
            "dynamic"
        ][
            "changed_rule_count"
        ],
    )

    print(
        "Transitions:",
        a[
            "dynamic"
        ][
            "transitions"
        ],
    )

    print(
        "BCR/FAR:",
        (
            a[
                "numeric"
            ][
                "building_coverage_ratio"
            ],
            a[
                "numeric"
            ][
                "floor_area_ratio"
            ],
        ),
    )

    print()

    print(
        "=== SCENARIO B ==="
    )

    print(
        "Input:",
        scenario_b[
            "input"
        ],
    )

    print(
        "Baseline:",
        b[
            "baseline"
        ],
    )

    print(
        "Final:",
        b[
            "final"
        ],
    )

    print(
        "Changed:",
        b[
            "dynamic"
        ][
            "changed_rule_count"
        ],
    )

    print(
        "Transitions:",
        b[
            "dynamic"
        ][
            "transitions"
        ],
    )

    print(
        "BCR/FAR:",
        (
            b[
                "numeric"
            ][
                "building_coverage_ratio"
            ],
            b[
                "numeric"
            ][
                "floor_area_ratio"
            ],
        ),
    )

    print()

    print(
        "=== SCENARIO C ==="
    )

    print(
        "Input:",
        scenario_c[
            "input"
        ],
    )

    print(
        "Baseline:",
        c[
            "baseline"
        ],
    )

    print(
        "Final:",
        c[
            "final"
        ],
    )

    print(
        "Changed:",
        c[
            "dynamic"
        ][
            "changed_rule_count"
        ],
    )

    print(
        "Transitions:",
        c[
            "dynamic"
        ][
            "transitions"
        ],
    )

    print(
        "BCR/FAR:",
        (
            c[
                "numeric"
            ][
                "building_coverage_ratio"
            ],
            c[
                "numeric"
            ][
                "floor_area_ratio"
            ],
        ),
    )

    print()

    # ========================================================
    # baselines
    # ========================================================

    expected_baseline = {
        "APPLICABLE": 58,
        "NOT_APPLICABLE": 211,
        "CONDITIONAL": 43,
        "UNKNOWN": 2,
    }

    # ========================================================
    # sample condition states
    #
    # 공동주택 condition이 실제로 존재하는 첫 rule을 찾기 위해
    # 전체 rules에서 직접 scan
    # ========================================================

    def first_condition_state(
        result,
        condition_name,
    ):

        for rule in result.get(
            "rules",
            [],
        ):

            for condition in rule.get(
                "conditions",
                [],
            ):

                if (
                    condition.get(
                        "name"
                    )
                    == condition_name
                ):

                    return condition.get(
                        "state"
                    )

        return None

    a_multi = (
        first_condition_state(
            scenario_a,
            "공동주택",
        )
    )

    b_multi = (
        first_condition_state(
            scenario_b,
            "공동주택",
        )
    )

    c_multi = (
        first_condition_state(
            scenario_c,
            "공동주택",
        )
    )

    a_review = (
        first_condition_state(
            scenario_a,
            "도시계획위원회심의",
        )
    )

    b_review = (
        first_condition_state(
            scenario_b,
            "도시계획위원회심의",
        )
    )

    c_review = (
        first_condition_state(
            scenario_c,
            "도시계획위원회심의",
        )
    )

    print(
        "Condition states:"
    )

    print(
        "A 공동주택:",
        a_multi,
    )

    print(
        "B 공동주택:",
        b_multi,
    )

    print(
        "C 공동주택:",
        c_multi,
    )

    print(
        "A 도시계획위원회심의:",
        a_review,
    )

    print(
        "B 도시계획위원회심의:",
        b_review,
    )

    print(
        "C 도시계획위원회심의:",
        c_review,
    )

    print()

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "A baseline clean": (
            a[
                "baseline"
            ]
            == expected_baseline
        ),

        "B baseline clean": (
            b[
                "baseline"
            ]
            == expected_baseline
        ),

        "C baseline clean": (
            c[
                "baseline"
            ]
            == expected_baseline
        ),

        "A 공동주택 TRUE": (
            a_multi
            == "TRUE"
        ),

        "B 공동주택 FALSE": (
            b_multi
            == "FALSE"
        ),

        "C 공동주택 reset UNSET": (
            c_multi
            == "UNSET"
        ),

        "A review TRUE": (
            a_review
            == "TRUE"
        ),

        "B review TRUE": (
            b_review
            == "TRUE"
        ),

        "C review reset UNSET": (
            c_review
            == "UNSET"
        ),

        "A changes > 0": (
            a[
                "dynamic"
            ][
                "changed_rule_count"
            ]
            > 0
        ),

        "B changes > 0": (
            b[
                "dynamic"
            ][
                "changed_rule_count"
            ]
            > 0
        ),

        "C dynamic changes 0": (
            c[
                "dynamic"
            ][
                "changed_rule_count"
            ]
            == 0
        ),

        "A and B final differ": (
            a[
                "final"
            ]
            != b[
                "final"
            ]
        ),

        "C different from A": (
            c[
                "final"
            ]
            != a[
                "final"
            ]
        ),

        "C different from B": (
            c[
                "final"
            ]
            != b[
                "final"
            ]
        ),

        "A BCR 50": (
            a[
                "numeric"
            ][
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "A FAR 250": (
            a[
                "numeric"
            ][
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "B BCR 50": (
            b[
                "numeric"
            ][
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "B FAR 250": (
            b[
                "numeric"
            ][
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "C BCR 50": (
            c[
                "numeric"
            ][
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "C FAR 250": (
            c[
                "numeric"
            ][
                "floor_area_ratio"
            ]
            == 250.0
        ),
    }

    all_pass = all(
        validations.values()
    )

    print(
        "all_pass:",
        all_pass,
    )

    if not all_pass:

        print()

        print(
            "FAILED:"
        )

        for name, passed in (
            validations.items()
        ):

            if not passed:

                print(
                    "-",
                    name,
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