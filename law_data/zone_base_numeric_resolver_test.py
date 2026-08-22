# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4F
Zone Base Numeric Resolver Test
"""

from __future__ import annotations

from law_data.zone_base_numeric_resolver import (
    resolve_zone_base_numeric,
)


def main() -> int:

    cases = {

        "제3종일반주거지역": (
            50.0,
            250.0,
        ),

        "일반상업지역": (
            60.0,
            800.0,
        ),

        "자연녹지지역": (
            20.0,
            50.0,
        ),

        "준주거지역": (
            60.0,
            400.0,
        ),

        "준공업지역": (
            60.0,
            400.0,
        ),
    }

    validations = {}

    for zone, expected in (
        cases.items()
    ):

        result = (
            resolve_zone_base_numeric(
                zone
            )
        )

        bcr = (
            result[
                "building_coverage_ratio"
            ][
                "value"
            ]
        )

        far = (
            result[
                "floor_area_ratio"
            ][
                "value"
            ]
        )

        print(
            zone,
            "=>",
            "BCR:",
            bcr,
            "| FAR:",
            far,
        )

        validations[
            zone
        ] = (
            bcr
            == expected[
                0
            ]
            and far
            == expected[
                1
            ]
        )

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