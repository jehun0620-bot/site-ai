# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-3
SITE Spatial Payload Integration Test
"""

from __future__ import annotations

from site_analysis_builder import (
    build_site_analysis,
)


def main() -> int:

    result = build_site_analysis(
        project_profile={
            "공동주택": "TRUE",
        },
        procedure_profile={
            "도시계획위원회심의": "TRUE",
        },
    )

    site = result[
        "site"
    ]

    spatial = site.get(
        "spatial",
        {},
    )

    parcel = spatial.get(
        "parcel",
        {},
    )

    area = parcel.get(
        "area",
        {},
    )

    source = parcel.get(
        "source",
        {},
    )

    geometry = parcel.get(
        "geometry"
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "SITE ID:",
        site.get(
            "site_id"
        ),
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print()

    print(
        "Parcel PNU:",
        parcel.get(
            "pnu"
        ),
    )

    print(
        "Geometry type:",
        parcel.get(
            "geometry_type"
        ),
    )

    print(
        "Geometry loaded:",
        parcel.get(
            "geometry_loaded"
        ),
    )

    print()

    print(
        "Area:",
        area.get(
            "value"
        ),
    )

    print(
        "Area unit:",
        area.get(
            "unit"
        ),
    )

    print()

    print(
        "Bounds:",
        parcel.get(
            "bounds"
        ),
    )

    print()

    print(
        "CRS:",
        parcel.get(
            "crs"
        ),
    )

    print(
        "CRS status:",
        parcel.get(
            "crs_status"
        ),
    )

    print()

    print(
        "Source verified:",
        source.get(
            "verified"
        ),
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

    # ========================================================
    # validation
    # ========================================================

    validations = {

        "SITE PNU": (
            site.get(
                "pnu"
            )
            == "1168010300100120000"
        ),

        "parcel PNU": (
            parcel.get(
                "pnu"
            )
            == "1168010300100120000"
        ),

        "geometry loaded": (
            parcel.get(
                "geometry_loaded"
            )
            is True
        ),

        "geometry Polygon": (
            parcel.get(
                "geometry_type"
            )
            == "Polygon"
        ),

        "geometry coordinates": (
            isinstance(
                geometry,
                dict,
            )
            and bool(
                geometry.get(
                    "coordinates"
                )
            )
        ),

        "area": (
            area.get(
                "value"
            )
            == 120945.65223377591
        ),

        "bounds": (
            parcel.get(
                "bounds"
            )
            == [
                962201.02522,
                1943722.58159,
                962711.06096,
                1944220.16506,
            ]
        ),

        "CRS unknown preserved": (
            parcel.get(
                "crs"
            )
            is None
        ),

        "CRS status": (
            parcel.get(
                "crs_status"
            )
            == "SOURCE_CRS_NOT_EXPLICIT"
        ),

        "source verified": (
            source.get(
                "verified"
            )
            is True
        ),

        "BCR retained": (
            result[
                "regulation"
            ][
                "building_coverage_ratio"
            ][
                "value"
            ]
            == 50.0
        ),

        "FAR retained": (
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

        for name, passed in validations.items():

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