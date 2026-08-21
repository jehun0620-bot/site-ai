# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-5C-2
Reusable Rule Evaluation Pipeline module regression test
"""

from __future__ import annotations

from rule_evaluation_pipeline import (
    evaluate_site_rules,
)


def main() -> int:

    result = (
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

    baseline = (
        result[
            "baseline"
        ]
    )

    summary = (
        result[
            "rule_summary"
        ]
    )

    numeric = (
        result[
            "numeric"
        ]
    )

    injection = (
        result[
            "dynamic_injection"
        ]
    )

    historical = (
        result[
            "external_dependencies"
        ][
            "historical"
        ]
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Pipeline ready:",
        result[
            "pipeline"
        ][
            "ready"
        ],
    )

    print()

    print(
        "Baseline:",
        baseline,
    )

    print()

    print(
        "Branch conditions added:",
        result[
            "branch_overlay"
        ][
            "added_condition_count"
        ],
    )

    print()

    print(
        "Dynamic touched:",
        injection[
            "touched_rule_count"
        ],
    )

    print(
        "Dynamic changed:",
        injection[
            "changed_rule_count"
        ],
    )

    print(
        "Transitions:",
        injection[
            "transitions"
        ],
    )

    print()

    print(
        "Final:",
        summary,
    )

    print()

    print(
        "Numeric active:",
        numeric[
            "active_before_guard"
        ],
    )

    print(
        "Numeric excluded:",
        numeric[
            "excluded_count"
        ],
    )

    print(
        "Numeric retained:",
        numeric[
            "retained_count"
        ],
    )

    print()

    print(
        "Direct relaxation:",
        numeric[
            "direct_relaxation_count"
        ],
    )

    print(
        "Numeric resolution:",
        numeric[
            "resolution"
        ],
    )

    print(
        "Confirmed BCR:",
        numeric[
            "building_coverage_ratio"
        ],
    )

    print(
        "Confirmed FAR:",
        numeric[
            "floor_area_ratio"
        ],
    )

    print()

    print(
        "Historical dependency:",
        historical.get(
            "automation_state"
        ),
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "pipeline ready": (
            result[
                "pipeline"
            ][
                "ready"
            ]
            is True
        ),

        "baseline applicable 58": (
            baseline.get(
                "APPLICABLE"
            )
            == 58
        ),

        "baseline not applicable 211": (
            baseline.get(
                "NOT_APPLICABLE"
            )
            == 211
        ),

        "baseline conditional 43": (
            baseline.get(
                "CONDITIONAL"
            )
            == 43
        ),

        "baseline unknown 2": (
            baseline.get(
                "UNKNOWN"
            )
            == 2
        ),

        "branch conditions 7": (
            result[
                "branch_overlay"
            ][
                "added_condition_count"
            ]
            == 7
        ),

        "dynamic touched 16": (
            injection[
                "touched_rule_count"
            ]
            == 16
        ),

        "dynamic changed 5": (
            injection[
                "changed_rule_count"
            ]
            == 5
        ),

        "conditional to applicable 5": (
            injection[
                "transitions"
            ].get(
                "CONDITIONAL -> APPLICABLE"
            )
            == 5
        ),

        "final applicable 63": (
            summary.get(
                "APPLICABLE"
            )
            == 63
        ),

        "final not applicable 213": (
            summary.get(
                "NOT_APPLICABLE"
            )
            == 213
        ),

        "final conditional 36": (
            summary.get(
                "CONDITIONAL"
            )
            == 36
        ),

        "final unknown 2": (
            summary.get(
                "UNKNOWN"
            )
            == 2
        ),

        "direct relaxation 0": (
            numeric[
                "direct_relaxation_count"
            ]
            == 0
        ),

        "numeric base retained": (
            numeric[
                "resolution"
            ]
            == "BASE_VALUES_RETAINED"
        ),

        "BCR 50": (
            numeric[
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "FAR 250": (
            numeric[
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "history preserved": (
            historical.get(
                "automation_state"
            )
            == "HISTORICAL_SOURCE_PENDING"
        ),
    }

    all_pass = all(
        validations.values()
    )

    print()

    print(
        "all_pass:",
        all_pass,
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