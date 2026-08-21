# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-2B
SITE Analysis Land Area Integration Test
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

    land_area = (
        result.get(
            "land_area",
            {},
        )
    )

    official = (
        land_area.get(
            "official",
            {},
        )
    )

    spatial = (
        land_area.get(
            "spatial",
            {},
        )
    )

    difference = (
        land_area.get(
            "difference",
            {},
        )
    )

    print(
        "Official:",
        official,
    )

    print(
        "Spatial:",
        spatial,
    )

    print(
        "Difference:",
        difference,
    )

    print()

    print(
        "Resolution:",
        land_area.get(
            "resolution"
        ),
    )

    print(
        "Primary:",
        land_area.get(
            "primary"
        ),
    )

    validations = {

        "official area": (
            official.get(
                "value"
            )
            == 121040.4
        ),

        "official unit": (
            official.get(
                "unit"
            )
            == "square_meter"
        ),

        "official source": (
            official.get(
                "source"
            )
            == "VWORLD_LAND_CHARACTERISTICS"
        ),

        "spatial area": (
            spatial.get(
                "value"
            )
            == 120945.65223377591
        ),

        "spatial source": (
            spatial.get(
                "source"
            )
            == "MAPPLAN_PARCEL_GEOMETRY"
        ),

        "spatial CRS unresolved": (
            spatial.get(
                "crs"
            )
            is None
        ),

        "spatial CRS status": (
            spatial.get(
                "crs_status"
            )
            == "SOURCE_CRS_NOT_EXPLICIT"
        ),

        "difference exists": (
            difference.get(
                "value"
            )
            is not None
        ),

        "difference ratio small": (
            difference.get(
                "ratio_percent"
            )
            is not None
            and difference.get(
                "ratio_percent"
            )
            < 1.0
        ),

        "keep both": (
            land_area.get(
                "resolution"
            )
            == "KEEP_BOTH_WITH_SOURCE_ROLES"
        ),

        "official primary": (
            land_area.get(
                "primary"
            )
            == "official"
        ),

        "BCR unchanged": (
            result[
                "regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR unchanged": (
            result[
                "regulation"
            ][
                "floor_area_ratio"
            ][
                "value"
            ]
            == 250.0
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