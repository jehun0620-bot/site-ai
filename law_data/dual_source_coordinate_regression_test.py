# -*- coding: utf-8 -*-

"""
STEP 17-21-C-14-5
Dual-Source Coordinate Regression

목표
======================================================================
대표 SITE와 다른 실제 SITE의 representative coordinate가
서로 오염되지 않는지 검증한다.

BASE SITE
----------------------------------------------------------------------
서울특별시 강남구 개포동 12번지
PNU: 1168010300100120000

예상 coordinate:
x = 127.07539280356858
y = 37.494197498186885

LIVE SITE
----------------------------------------------------------------------
서울특별시 강남구 개포동 13번지
PNU: 1168010300100130000

예상 coordinate:
VWorld live address search 결과를 사용하고,
BASE SITE coordinate를 재사용하지 않는다.
"""

from __future__ import annotations

from law_data.site_analysis_builder import (
    build_site_analysis,
)


BASE_SITE = {
    "site_id": "11680-10300-0012-0000",
    "address": "서울특별시 강남구 개포동 12번지",
    "road_address": "서울특별시 강남구 개포로109길 21 (개포동)",
    "sigungu_cd": "11680",
    "bjdong_cd": "10300",
    "bun": "0012",
    "ji": "0000",
    "sigungu_code": "11680",
    "bjdong_code": "10300",
    "main_no": "0012",
    "sub_no": "0000",
    "pnu": "1168010300100120000",
    "zone": "제3종일반주거지역",
    "land_use_zone": "제3종일반주거지역",
}


LIVE_SITE = {
    "site_id": "11680-10300-0013-0000",
    "address": "서울특별시 강남구 개포동 13번지",
    "road_address": "서울특별시 강남구 개포로109길 74 (개포동)",
    "sigungu_cd": "11680",
    "bjdong_cd": "10300",
    "bun": "0013",
    "ji": "0000",
    "sigungu_code": "11680",
    "bjdong_code": "10300",
    "main_no": "0013",
    "sub_no": "0000",
    "pnu": "1168010300100130000",
    "zone": "제1종일반주거지역",
    "land_use_zone": "제1종일반주거지역",
}


def main() -> None:

    base_analysis = (
        build_site_analysis(
            site_input=BASE_SITE,

            project_profile={
                "공동주택": "TRUE",
            },

            procedure_profile={
                "도시계획위원회심의": "TRUE",
            },
        )
    )

    live_analysis = (
        build_site_analysis(
            site_input=LIVE_SITE,

            project_profile={
                "공동주택": "TRUE",
            },

            procedure_profile={
                "도시계획위원회심의": "TRUE",
            },
        )
    )

    base_site = (
        base_analysis.get(
            "site",
            {},
        )
    )

    live_site = (
        live_analysis.get(
            "site",
            {},
        )
    )

    base_coordinate = (
        base_site.get(
            "coordinate",
            {},
        )
    )

    live_coordinate = (
        live_site.get(
            "coordinate",
            {},
        )
    )

    live_parcel = (
        live_site.get(
            "spatial",
            {},
        ).get(
            "parcel",
            {},
        )
    )

    live_parcel_coordinate = (
        live_parcel.get(
            "source",
            {},
        ).get(
            "live",
            {},
        ).get(
            "coordinate",
            {},
        )
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "=== BASE SITE ==="
    )

    print(
        "SITE ID:",
        base_site.get(
            "site_id"
        ),
    )

    print(
        "PNU:",
        base_site.get(
            "pnu"
        ),
    )

    print(
        "Coordinate:",
        base_coordinate,
    )

    print()

    print(
        "=== LIVE SITE ==="
    )

    print(
        "SITE ID:",
        live_site.get(
            "site_id"
        ),
    )

    print(
        "PNU:",
        live_site.get(
            "pnu"
        ),
    )

    print(
        "Coordinate:",
        live_coordinate,
    )

    print(
        "Parcel coordinate:",
        live_parcel_coordinate,
    )

    # ========================================================
    # validations
    # ========================================================

    validations = {

        "base site id": (
            base_site.get(
                "site_id"
            )
            == BASE_SITE[
                "site_id"
            ]
        ),

        "live site id": (
            live_site.get(
                "site_id"
            )
            == LIVE_SITE[
                "site_id"
            ]
        ),

        "different site id": (
            base_site.get(
                "site_id"
            )
            != live_site.get(
                "site_id"
            )
        ),

        "different pnu": (
            base_site.get(
                "pnu"
            )
            != live_site.get(
                "pnu"
            )
        ),

        # ----------------------------------------------------
        # BASE representative coordinate
        # ----------------------------------------------------

        "base coordinate x": (
            base_coordinate.get(
                "x"
            )
            == 127.07539280356858
        ),

        "base coordinate y": (
            base_coordinate.get(
                "y"
            )
            == 37.494197498186885
        ),

        "base coordinate CRS": (
            base_coordinate.get(
                "crs"
            )
            == "EPSG:4326"
        ),

        # ----------------------------------------------------
        # LIVE representative coordinate
        # ----------------------------------------------------

        "live coordinate exists": (
            isinstance(
                live_coordinate.get(
                    "x"
                ),
                (
                    int,
                    float,
                ),
            )
            and isinstance(
                live_coordinate.get(
                    "y"
                ),
                (
                    int,
                    float,
                ),
            )
        ),

        "live coordinate CRS": (
            live_coordinate.get(
                "crs"
            )
            == "EPSG:4326"
        ),

        "live coordinate source": (
            live_coordinate.get(
                "source"
            )
            == "VWORLD_ADDRESS_SEARCH"
        ),

        "live coordinate confirmed": (
            live_coordinate.get(
                "status"
            )
            == "CONFIRMED"
        ),

        # ----------------------------------------------------
        # parcel -> representative promotion
        # ----------------------------------------------------

        "live coordinate matches parcel x": (
            live_coordinate.get(
                "x"
            )
            == live_parcel_coordinate.get(
                "x"
            )
        ),

        "live coordinate matches parcel y": (
            live_coordinate.get(
                "y"
            )
            == live_parcel_coordinate.get(
                "y"
            )
        ),

        # ----------------------------------------------------
        # contamination guard
        # ----------------------------------------------------

        "coordinate x differs": (
            base_coordinate.get(
                "x"
            )
            != live_coordinate.get(
                "x"
            )
        ),

        "coordinate y differs": (
            base_coordinate.get(
                "y"
            )
            != live_coordinate.get(
                "y"
            )
        ),

        "live not base coordinate": (
            (
                live_coordinate.get(
                    "x"
                ),
                live_coordinate.get(
                    "y"
                ),
            )
            != (
                127.07539280356858,
                37.494197498186885,
            )
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # result
    # ========================================================

    print()

    print(
        "=== VALIDATION ==="
    )

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}:",
            passed,
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

    raise SystemExit(
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    main()