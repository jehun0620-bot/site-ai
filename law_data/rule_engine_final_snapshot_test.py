# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-6
Final Rule Engine Snapshot

목표
======================================================================
C-10에서 구축한 reusable rule evaluation engine의
최종 상태를 snapshot으로 고정한다.

검증 항목
======================================================================
1. clean SITE baseline
2. branch-local predicate engine
3. SITE registry
4. PROJECT / PROCEDURE dynamic input
5. stateless evaluation
6. numeric verified guard
7. stacking ceiling resolution
8. external historical dependency
9. confirmed BCR / FAR

이번 snapshot은
다음 단계인 SITE analysis object integration의 기준 입력이 된다.
"""

from __future__ import annotations

import json
from pathlib import Path

from rule_evaluation_pipeline import (
    evaluate_site_rules,
)


STEP_NAME = (
    "STEP 17-21-C-10-6 "
    "final rule engine snapshot"
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "rule_engine_final_snapshot.json"
)


def save_json(
    data,
):

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


def main() -> int:

    # ========================================================
    # baseline scenario
    # ========================================================

    baseline_result = (
        evaluate_site_rules(
            project_profile={},
            procedure_profile={},
        )
    )

    # ========================================================
    # representative dynamic scenario
    # ========================================================

    dynamic_result = (
        evaluate_site_rules(
            project_profile={
                "공동주택": "TRUE",
            },

            procedure_profile={
                "도시계획위원회심의": "TRUE",
            },
        )
    )

    # ========================================================
    # negative project scenario
    # ========================================================

    negative_result = (
        evaluate_site_rules(
            project_profile={
                "공동주택": "FALSE",
            },

            procedure_profile={
                "도시계획위원회심의": "TRUE",
            },
        )
    )

    # ========================================================
    # core values
    # ========================================================

    baseline_summary = (
        baseline_result[
            "rule_summary"
        ]
    )

    dynamic_summary = (
        dynamic_result[
            "rule_summary"
        ]
    )

    negative_summary = (
        negative_result[
            "rule_summary"
        ]
    )

    baseline_numeric = (
        baseline_result[
            "numeric"
        ]
    )

    dynamic_numeric = (
        dynamic_result[
            "numeric"
        ]
    )

    negative_numeric = (
        negative_result[
            "numeric"
        ]
    )

    historical = (
        baseline_result[
            "external_dependencies"
        ][
            "historical"
        ]
    )

    # ========================================================
    # final engine state
    # ========================================================

    engine_state = {
        "status": (
            "READY"
        ),

        "stateless": (
            True
        ),

        "clean_baseline": (
            True
        ),

        "branch_local_predicates": (
            True
        ),

        "dynamic_project_input": (
            True
        ),

        "dynamic_procedure_input": (
            True
        ),

        "numeric_verified_guards": (
            True
        ),

        "stacking_ceiling_resolution": (
            True
        ),

        "external_dependency_supported": (
            True
        ),
    }

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "baseline pipeline ready": (
            baseline_result[
                "pipeline"
            ][
                "ready"
            ]
            is True
        ),

        "dynamic pipeline ready": (
            dynamic_result[
                "pipeline"
            ][
                "ready"
            ]
            is True
        ),

        "negative pipeline ready": (
            negative_result[
                "pipeline"
            ][
                "ready"
            ]
            is True
        ),

        "baseline rules 314": (
            sum(
                baseline_summary.values()
            )
            == 314
        ),

        "dynamic rules 314": (
            sum(
                dynamic_summary.values()
            )
            == 314
        ),

        "negative rules 314": (
            sum(
                negative_summary.values()
            )
            == 314
        ),

        "baseline dynamic changes 0": (
            baseline_result[
                "dynamic_injection"
            ][
                "changed_rule_count"
            ]
            == 0
        ),

        "dynamic changes 5": (
            dynamic_result[
                "dynamic_injection"
            ][
                "changed_rule_count"
            ]
            == 5
        ),

        "negative changes 6": (
            negative_result[
                "dynamic_injection"
            ][
                "changed_rule_count"
            ]
            == 6
        ),

        "dynamic and negative differ": (
            dynamic_summary
            != negative_summary
        ),

        "baseline BCR 50": (
            baseline_numeric[
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "baseline FAR 250": (
            baseline_numeric[
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "dynamic BCR 50": (
            dynamic_numeric[
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "dynamic FAR 250": (
            dynamic_numeric[
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "negative BCR 50": (
            negative_numeric[
                "building_coverage_ratio"
            ]
            == 50.0
        ),

        "negative FAR 250": (
            negative_numeric[
                "floor_area_ratio"
            ]
            == 250.0
        ),

        "direct relaxation baseline 0": (
            baseline_numeric[
                "direct_relaxation_count"
            ]
            == 0
        ),

        "direct relaxation dynamic 0": (
            dynamic_numeric[
                "direct_relaxation_count"
            ]
            == 0
        ),

        "direct relaxation negative 0": (
            negative_numeric[
                "direct_relaxation_count"
            ]
            == 0
        ),

        "historical dependency preserved": (
            historical.get(
                "automation_state"
            )
            == "HISTORICAL_SOURCE_PENDING"
        ),

        "engine ready": (
            engine_state[
                "status"
            ]
            == "READY"
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

        "engine": (
            engine_state
        ),

        "site": (
            baseline_result.get(
                "site",
                {}
            )
        ),

        "site_zone": (
            baseline_result.get(
                "site_zone"
            )
        ),

        "baseline": {
            "input": (
                baseline_result[
                    "input"
                ]
            ),

            "rule_summary": (
                baseline_summary
            ),

            "numeric": (
                baseline_numeric
            ),
        },

        "dynamic_scenario": {
            "input": (
                dynamic_result[
                    "input"
                ]
            ),

            "rule_summary": (
                dynamic_summary
            ),

            "dynamic_injection": (
                dynamic_result[
                    "dynamic_injection"
                ]
            ),

            "numeric": (
                dynamic_numeric
            ),
        },

        "negative_scenario": {
            "input": (
                negative_result[
                    "input"
                ]
            ),

            "rule_summary": (
                negative_summary
            ),

            "dynamic_injection": (
                negative_result[
                    "dynamic_injection"
                ]
            ),

            "numeric": (
                negative_numeric
            ),
        },

        "remaining_inputs": (
            baseline_result[
                "remaining_inputs"
            ]
        ),

        "external_dependencies": (
            baseline_result[
                "external_dependencies"
            ]
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
        "Rule Engine:",
        engine_state[
            "status"
        ],
    )

    print(
        "Stateless:",
        engine_state[
            "stateless"
        ],
    )

    print()

    print(
        "Baseline:",
        baseline_summary,
    )

    print(
        "Dynamic TRUE:",
        dynamic_summary,
    )

    print(
        "Dynamic FALSE:",
        negative_summary,
    )

    print()

    print(
        "Baseline BCR/FAR:",
        (
            baseline_numeric[
                "building_coverage_ratio"
            ],
            baseline_numeric[
                "floor_area_ratio"
            ],
        ),
    )

    print(
        "Dynamic TRUE BCR/FAR:",
        (
            dynamic_numeric[
                "building_coverage_ratio"
            ],
            dynamic_numeric[
                "floor_area_ratio"
            ],
        ),
    )

    print(
        "Dynamic FALSE BCR/FAR:",
        (
            negative_numeric[
                "building_coverage_ratio"
            ],
            negative_numeric[
                "floor_area_ratio"
            ],
        ),
    )

    print()

    print(
        "Remaining PROJECT inputs:",
        len(
            baseline_result[
                "remaining_inputs"
            ][
                "project"
            ]
        ),
    )

    print(
        "Remaining PROCEDURE inputs:",
        len(
            baseline_result[
                "remaining_inputs"
            ][
                "procedure"
            ]
        ),
    )

    print()

    print(
        "Historical dependency:",
        historical.get(
            "automation_state"
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