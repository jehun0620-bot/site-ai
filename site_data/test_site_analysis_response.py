# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-3
SITE Analysis API Response Test
"""

from __future__ import annotations

import json

from site_data.site_data_model import (
    Land,
    Site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)

from site_data.site_analysis_response import (
    build_site_analysis_response,
)


def main() -> int:

    # ========================================================
    # representative Site
    # ========================================================

    site = Site(
        site_id=(
            "11680-10300-0012-0000"
        ),

        address=(
            "서울특별시 강남구 개포동 12번지"
        ),

        road_address=(
            "서울특별시 강남구 개포로109길 21 (개포동)"
        ),

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
    )

    site.land = Land(
        land_area=(
            121040.4
        ),

        land_category=(
            "대"
        ),

        zoning=(
            "제3종일반주거지역"
        ),
    )

    # ========================================================
    # internal analysis
    # ========================================================

    analysis = analyze_site_object(
        site=site,

        project_profile={
            "공동주택": "TRUE",
        },

        procedure_profile={
            "도시계획위원회심의": "TRUE",
        },
    )

    # ========================================================
    # public API response
    # ========================================================

    response = (
        build_site_analysis_response(
            analysis,
            include_debug=False,
        )
    )

    # 실제 JSON 직렬화 검증
    encoded = json.dumps(
        response,
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
        response.get(
            "schema_version"
        ),
    )

    print(
        "Status:",
        response.get(
            "status"
        ),
    )

    print()

    print(
        "SITE ID:",
        response[
            "site"
        ][
            "site_id"
        ],
    )

    print(
        "Road address:",
        response[
            "site"
        ][
            "road_address"
        ],
    )

    print(
        "PNU:",
        response[
            "site"
        ][
            "pnu"
        ],
    )

    print()

    print(
        "Official area:",
        response[
            "land_area"
        ][
            "official"
        ][
            "value"
        ],
    )

    print(
        "Spatial area:",
        response[
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
        response[
            "regulation"
        ][
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "FAR:",
        response[
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
        response[
            "rule_evaluation"
        ],
    )

    print()

    print(
        "PROJECT requirements:",
        response[
            "requirements"
        ][
            "project_count"
        ],
    )

    print(
        "PROCEDURE requirements:",
        response[
            "requirements"
        ][
            "procedure_count"
        ],
    )

    print()

    print(
        "Debug included:",
        (
            "debug"
            in response
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
            response.get(
                "schema_version"
            )
            == "SITE_ANALYSIS_API_V1"
        ),

        "ready": (
            response.get(
                "status"
            )
            == "READY"
        ),

        "site id": (
            response[
                "site"
            ][
                "site_id"
            ]
            == "11680-10300-0012-0000"
        ),

        "road address": (
            response[
                "site"
            ][
                "road_address"
            ]
            == (
                "서울특별시 강남구 개포로109길 21 (개포동)"
            )
        ),

        "pnu": (
            response[
                "site"
            ][
                "pnu"
            ]
            == "1168010300100120000"
        ),

        "official area": (
            response[
                "land_area"
            ][
                "official"
            ][
                "value"
            ]
            == 121040.4
        ),

        "spatial area": (
            response[
                "land_area"
            ][
                "spatial"
            ][
                "value"
            ]
            == 120945.65223377591
        ),

        "BCR": (
            response[
                "regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR": (
            response[
                "regulation"
            ][
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "rules 314": (
            response[
                "rule_evaluation"
            ][
                "total"
            ]
            == 314
        ),

        "debug excluded": (
            "debug"
            not in response
        ),

        "JSON round trip": (
            decoded
            == response
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