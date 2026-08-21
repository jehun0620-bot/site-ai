# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-2A
Land Area Source Reconciliation

목표
======================================================================
현재 SITE에 존재하는 두 면적 source를 비교하고
각각의 역할을 명확히 분리한다.

1. VWorld land characteristic area
2. MapPlan parcel polygon geometry area

이번 단계에서는 어느 값을 억지로 삭제하지 않는다.
두 값을 모두 보존하고 source role을 구분한다.
"""

from __future__ import annotations

from site_data.site_data_model import (
    Land,
    Site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)


def main() -> int:

    # ========================================================
    # 실제 API 결과와 동일한 representative Site
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

    result = analyze_site_object(
        site=site,

        project_profile={
            "공동주택": "TRUE",
        },

        procedure_profile={
            "도시계획위원회심의": "TRUE",
        },
    )

    analysis_site = (
        result[
            "site"
        ]
    )

    site_input = (
        result[
            "input"
        ][
            "site"
        ]
    )

    parcel = (
        analysis_site.get(
            "spatial",
            {},
        ).get(
            "parcel",
            {},
        )
    )

    # ========================================================
    # values
    # ========================================================

    official_land_area = (
        site_input.get(
            "land_area"
        )
    )

    parcel_geometry_area = (
        parcel.get(
            "area",
            {},
        ).get(
            "value"
        )
    )

    difference = None
    difference_ratio = None

    if (
        official_land_area
        is not None
        and parcel_geometry_area
        is not None
    ):

        difference = (
            official_land_area
            - parcel_geometry_area
        )

        if official_land_area:

            difference_ratio = (
                abs(
                    difference
                )
                / official_land_area
                * 100.0
            )

    # ========================================================
    # role decision
    # ========================================================

    reconciliation = {

        "official_land_area": {
            "value": (
                official_land_area
            ),

            "unit": (
                "square_meter"
            ),

            "source": (
                "VWORLD_LAND_CHARACTERISTICS"
            ),

            "role": (
                "LEGAL_OR_ATTRIBUTE_LAND_AREA"
            ),
        },

        "parcel_geometry_area": {
            "value": (
                parcel_geometry_area
            ),

            "unit": (
                "native_crs_square_units"
            ),

            "source": (
                "MAPPLAN_PARCEL_GEOMETRY"
            ),

            "role": (
                "SPATIAL_GEOMETRY_AREA"
            ),
        },

        "difference": {
            "value": (
                difference
            ),

            "ratio_percent": (
                difference_ratio
            ),
        },

        "resolution": (
            "KEEP_BOTH_WITH_SOURCE_ROLES"
        ),

        "recommended_primary_land_area": (
            "VWORLD_LAND_CHARACTERISTICS"
        ),

        "recommended_spatial_area": (
            "MAPPLAN_PARCEL_GEOMETRY"
        ),
    }

    # ========================================================
    # console
    # ========================================================

    print(
        "Official land area:",
        official_land_area,
    )

    print(
        "Parcel geometry area:",
        parcel_geometry_area,
    )

    print()

    print(
        "Difference:",
        difference,
    )

    print(
        "Difference ratio (%):",
        difference_ratio,
    )

    print()

    print(
        "Resolution:",
        reconciliation[
            "resolution"
        ],
    )

    print(
        "Primary land area:",
        reconciliation[
            "recommended_primary_land_area"
        ],
    )

    print(
        "Spatial area:",
        reconciliation[
            "recommended_spatial_area"
        ],
    )

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "official land area exists": (
            official_land_area
            == 121040.4
        ),

        "spatial area exists": (
            parcel_geometry_area
            == 120945.65223377591
        ),

        "areas differ": (
            difference
            is not None
            and abs(
                difference
            )
            > 0
        ),

        "difference small": (
            difference_ratio
            is not None
            and difference_ratio
            < 1.0
        ),

        "keep both": (
            reconciliation[
                "resolution"
            ]
            == "KEEP_BOTH_WITH_SOURCE_ROLES"
        ),

        "official primary": (
            reconciliation[
                "recommended_primary_land_area"
            ]
            == "VWORLD_LAND_CHARACTERISTICS"
        ),

        "spatial geometry separate": (
            reconciliation[
                "recommended_spatial_area"
            ]
            == "MAPPLAN_PARCEL_GEOMETRY"
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