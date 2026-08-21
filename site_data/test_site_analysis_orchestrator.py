# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-4
SITE Analysis Orchestrator End-to-End Test
"""

from __future__ import annotations

import json


from site_data.site_analysis_orchestrator import (
    analyze_site_by_parcel,
)


def main() -> int:

    result = (
        analyze_site_by_parcel(
            sigungu_cd=(
                "11680"
            ),

            bjdong_cd=(
                "10300"
            ),

            bun=(
                "0012"
            ),

            ji=(
                "0000"
            ),

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

            include_debug=(
                False
            ),
        )
    )

    # ========================================================
    # JSON-safe regression
    # ========================================================

    encoded = json.dumps(
        result,
        ensure_ascii=False,
    )

    decoded = json.loads(
        encoded
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Schema:",
        result.get(
            "schema_version"
        ),
    )

    print(
        "Status:",
        result.get(
            "status"
        ),
    )

    print()

    print(
        "SITE ID:",
        result[
            "site"
        ][
            "site_id"
        ],
    )

    print(
        "Address:",
        result[
            "site"
        ][
            "address"
        ],
    )

    print(
        "Road address:",
        result[
            "site"
        ][
            "road_address"
        ],
    )

    print(
        "PNU:",
        result[
            "site"
        ][
            "pnu"
        ],
    )

    print()

    print(
        "Official area:",
        result[
            "land_area"
        ][
            "official"
        ][
            "value"
        ],
    )

    print(
        "Spatial area:",
        result[
            "land_area"
        ][
            "spatial"
        ][
            "value"
        ],
    )

    print()

    print(
        "BCR:",
        result[
            "regulation"
        ][
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "FAR:",
        result[
            "regulation"
        ][
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print()

    print(
        "Rules:",
        result[
            "rule_evaluation"
        ],
    )

    print()

    print(
        "Building count:",
        result[
            "service"
        ][
            "building_count"
        ],
    )

    print(
        "Building total:",
        result[
            "service"
        ][
            "building_total_count"
        ],
    )

    print(
        "Building API:",
        result[
            "service"
        ][
            "building_api_status"
        ],
    )

    print()

    print(
        "Debug included:",
        (
            "debug"
            in result
        ),
    )

    print(
        "JSON bytes:",
        len(
            encoded.encode(
                "utf-8"
            )
        ),
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "schema": (
            result.get(
                "schema_version"
            )
            == "SITE_ANALYSIS_API_V1"
        ),

        "ready": (
            result.get(
                "status"
            )
            == "READY"
        ),

        "site": (
            result[
                "site"
            ][
                "site_id"
            ]
            == "11680-10300-0012-0000"
        ),

        "road address": (
            bool(
                result[
                    "site"
                ][
                    "road_address"
                ]
            )
        ),

        "pnu": (
            result[
                "site"
            ][
                "pnu"
            ]
            == "1168010300100120000"
        ),

        "official area": (
            result[
                "land_area"
            ][
                "official"
            ][
                "value"
            ]
            == 121040.4
        ),

        "parcel loaded": (
            result[
                "spatial"
            ][
                "parcel"
            ][
                "geometry_loaded"
            ]
            is True
        ),

        "BCR": (
            result[
                "regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR": (
            result[
                "regulation"
            ][
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "rules": (
            result[
                "rule_evaluation"
            ][
                "total"
            ]
            == 314
        ),

        "34 buildings": (
            result[
                "service"
            ][
                "building_count"
            ]
            == 34
        ),

        "API status": (
            result[
                "service"
            ][
                "building_api_status"
            ]
            == "00"
        ),

        "debug excluded": (
            "debug"
            not in result
        ),

        "JSON round trip": (
            decoded
            == result
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