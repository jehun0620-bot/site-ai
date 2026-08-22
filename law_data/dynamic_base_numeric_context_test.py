# -*- coding: utf-8 -*-

from __future__ import annotations

from law_data.rule_evaluation_pipeline import (
    evaluate_site_rules,
)


def main() -> int:

    result = evaluate_site_rules(
        project_profile={
            "공동주택": "TRUE",
        },
        procedure_profile={
            "도시계획위원회심의": "TRUE",
        },
        base_numeric_context={
            "building_coverage_ratio": {
                "value": 60.0,
            },
            "floor_area_ratio": {
                "value": 800.0,
            },
        },
    )

    numeric = result.get(
        "numeric",
        {},
    )

    bcr = numeric.get(
        "building_coverage_ratio"
    )

    far = numeric.get(
        "floor_area_ratio"
    )

    print(
        "Confirmed BCR:",
        bcr,
    )

    print(
        "Confirmed FAR:",
        far,
    )

    print(
        "Numeric resolution:",
        numeric.get(
            "resolution"
        ),
    )

    all_pass = (
        bcr == 60.0
        and far == 800.0
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