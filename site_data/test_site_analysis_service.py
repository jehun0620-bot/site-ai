# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-1
SITE Analysis Service Adapter Test
"""

from __future__ import annotations

from site_data.site_data_model import (
    Land,
    Site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
    site_to_analysis_input,
)


def main() -> int:

    # ========================================================
    # 실제 create_site()가 생성하는 형태와 동일한 test Site
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
            120945.65223377591
        ),

        zoning=(
            "제3종일반주거지역"
        ),

        land_category=(
            "대"
        ),
    )

    # ========================================================
    # adapter input
    # ========================================================

    site_input = (
        site_to_analysis_input(
            site
        )
    )

    print(
        "=== SITE INPUT ==="
    )

    print(
        site_input
    )

    print()

    # ========================================================
    # final analysis
    # ========================================================

    result = (
        analyze_site_object(
            site=site,

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

    result_site = (
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

    # ========================================================
    # console
    # ========================================================

    print(
        "Analysis:",
        result[
            "analysis"
        ][
            "status"
        ],
    )

    print()

    print(
        "SITE ID:",
        result_site.get(
            "site_id"
        ),
    )

    print(
        "Address:",
        result_site.get(
            "address"
        ),
    )

    print(
        "Road address:",
        result_site.get(
            "road_address"
        ),
    )

    print(
        "PNU:",
        result_site.get(
            "pnu"
        ),
    )

    print(
        "Zone:",
        result_site.get(
            "zone"
        ),
    )

    print()

    print(
        "BCR:",
        regulation[
            "building_coverage_ratio"
        ][
            "value"
        ],
    )

    print(
        "FAR:",
        regulation[
            "floor_area_ratio"
        ][
            "value"
        ],
    )

    print()

    print(
        "Rules:",
        rules,
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "adapter site id": (
            site_input.get(
                "site_id"
            )
            == (
                "11680-10300-0012-0000"
            )
        ),

        "adapter road address": (
            site_input.get(
                "road_address"
            )
            == (
                "서울특별시 강남구 개포로109길 21 (개포동)"
            )
        ),

        "adapter zone": (
            site_input.get(
                "zone"
            )
            == (
                "제3종일반주거지역"
            )
        ),

        "analysis ready": (
            result[
                "analysis"
            ][
                "status"
            ]
            == "READY"
        ),

        "site id": (
            result_site.get(
                "site_id"
            )
            == (
                "11680-10300-0012-0000"
            )
        ),

        # 매우 중요:
        # 지금까지 None이던 도로명주소가
        # Site Builder input에서 실제로 들어오는지 검증
        "road address integrated": (
            result_site.get(
                "road_address"
            )
            == (
                "서울특별시 강남구 개포로109길 21 (개포동)"
            )
        ),

        "pnu": (
            result_site.get(
                "pnu"
            )
            == (
                "1168010300100120000"
            )
        ),

        "identity complete": (
            result_site.get(
                "identity_status"
            )
            == "COMPLETE"
        ),

        "parcel loaded": (
            result_site.get(
                "spatial",
                {},
            ).get(
                "parcel",
                {},
            ).get(
                "geometry_loaded"
            )
            is True
        ),

        "BCR": (
            regulation[
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR": (
            regulation[
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
        ),

        "rules": (
            rules.get(
                "total"
            )
            == 314
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