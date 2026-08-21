# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-1
SITE Analysis Object Integration Test
"""

from __future__ import annotations

import json
from pathlib import Path


from site_analysis_builder import (
    build_site_analysis,
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
    / "site_analysis_snapshot.json"
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
    # representative scenario
    # ========================================================

    result = (
        build_site_analysis(
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

    analysis = (
        result[
            "analysis"
        ]
    )

    site = (
        result[
            "site"
        ]
    )

    regulation = (
        result[
            "regulation"
        ]
    )

    rules = (
        result[
            "rule_evaluation"
        ]
    )

    requirements = (
        result[
            "input_requirements"
        ]
    )

    dependencies = (
        result[
            "external_dependencies"
        ]
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Analysis status:",
        analysis[
            "status"
        ],
    )

    print(
        "Engine:",
        analysis[
            "engine"
        ],
    )

    print()

    print(
        "SITE zone:",
        site.get(
            "zone"
        ),
    )

    print()

    print(
        "Confirmed BCR:",
        regulation[
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "Confirmed FAR:",
        regulation[
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print(
        "Numeric resolution:",
        regulation[
            "numeric_resolution"
        ],
    )

    print()

    print(
        "Rules:",
        rules[
            "total"
        ],
    )

    print(
        "APPLICABLE:",
        rules[
            "applicable"
        ],
    )

    print(
        "NOT_APPLICABLE:",
        rules[
            "not_applicable"
        ],
    )

    print(
        "CONDITIONAL:",
        rules[
            "conditional"
        ],
    )

    print(
        "UNKNOWN:",
        rules[
            "unknown"
        ],
    )

    print()

    print(
        "Remaining PROJECT inputs:",
        requirements[
            "project_count"
        ],
    )

    print(
        "Remaining PROCEDURE inputs:",
        requirements[
            "procedure_count"
        ],
    )

    print()

    print(
        "External dependencies:",
        dependencies[
            "count"
        ],
    )

    for item in dependencies[
        "items"
    ]:

        print(
            "-",
            item[
                "condition"
            ],
            "/",
            item[
                "status"
            ],
            "/",
            item[
                "automation_state"
            ],
        )

    print()

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "analysis ready": (
            analysis[
                "status"
            ]
            == "READY"
        ),

        "engine correct": (
            analysis[
                "engine"
            ]
            == (
                "RULE_EVALUATION_PIPELINE"
            )
        ),

        "SITE zone correct": (
            site.get(
                "zone"
            )
            == "제3종일반주거지역"
        ),

        "BCR 50": (
            regulation[
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR 250": (
            regulation[
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "BCR confirmed": (
            regulation[
                "building_coverage_ratio"
            ][
                "status"
            ]
            == "CONFIRMED"
        ),

        "FAR confirmed": (
            regulation[
                "floor_area_ratio"
            ][
                "status"
            ]
            == "CONFIRMED"
        ),

        "numeric base retained": (
            regulation[
                "numeric_resolution"
            ]
            == "BASE_VALUES_RETAINED"
        ),

        "rules 314": (
            rules[
                "total"
            ]
            == 314
        ),

        "applicable 63": (
            rules[
                "applicable"
            ]
            == 63
        ),

        "not applicable 213": (
            rules[
                "not_applicable"
            ]
            == 213
        ),

        "conditional 36": (
            rules[
                "conditional"
            ]
            == 36
        ),

        "unknown 2": (
            rules[
                "unknown"
            ]
            == 2
        ),

        "project input remains": (
            requirements[
                "project_count"
            ]
            > 0
        ),

        "procedure input remains": (
            requirements[
                "procedure_count"
            ]
            > 0
        ),

        "historical dependency 1": (
            dependencies[
                "count"
            ]
            == 1
        ),

        "historical pending": (
            dependencies[
                "items"
            ][
                0
            ][
                "automation_state"
            ]
            == "HISTORICAL_SOURCE_PENDING"
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # save
    # ========================================================

    output = {
        **result,

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