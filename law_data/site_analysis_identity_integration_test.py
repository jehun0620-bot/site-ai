# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2B-2
SITE Analysis Identity Integration Regression

목표
======================================================================
site_analysis_builder.py가 실제로 site_identity_resolver.py 결과를
최종 SITE Analysis 객체의 site 영역에 반영하는지 검증한다.

검증 대상
======================================================================
- SITE ID
- 주소
- PNU
- 시군구코드
- 법정동코드
- 본번 / 부번
- 용도지역
- 대표 좌표
- CRS
- parcel reference
- 기존 Rule Engine 결과 보존
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
    / "site_analysis_identity_integration.json"
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
    # build analysis
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

    site = (
        result.get(
            "site",
            {},
        )
    )

    regulation = (
        result.get(
            "regulation",
            {},
        )
    )

    rules = (
        result.get(
            "rule_evaluation",
            {},
        )
    )

    coordinate = (
        site.get(
            "coordinate",
            {},
        )
    )

    parcel_reference = (
        site.get(
            "parcel_reference",
            {},
        )
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
        site.get(
            "site_id"
        ),
    )

    print(
        "Address:",
        site.get(
            "address"
        ),
    )

    print(
        "Road address:",
        site.get(
            "road_address"
        ),
    )

    print()

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print(
        "Sigungu:",
        site.get(
            "sigungu_code"
        ),
    )

    print(
        "Bjdong:",
        site.get(
            "bjdong_code"
        ),
    )

    print(
        "Main/Sub:",
        (
            site.get(
                "main_no"
            ),
            site.get(
                "sub_no"
            ),
        ),
    )

    print()

    print(
        "Zone:",
        site.get(
            "zone"
        ),
    )

    print(
        "Identity status:",
        site.get(
            "identity_status"
        ),
    )

    print(
        "Coordinate status:",
        site.get(
            "coordinate_status"
        ),
    )

    print()

    print(
        "Coordinate:",
        coordinate,
    )

    print()

    print(
        "Parcel reference:",
        parcel_reference,
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

        "analysis ready": (
            result[
                "analysis"
            ][
                "status"
            ]
            == "READY"
        ),

        "site id": (
            site.get(
                "site_id"
            )
            == (
                "11680-10300-0012-0000"
            )
        ),

        "address": (
            site.get(
                "address"
            )
            == (
                "서울특별시 강남구 개포동 12번지"
            )
        ),

        "pnu": (
            site.get(
                "pnu"
            )
            == (
                "1168010300100120000"
            )
        ),

        "sigungu": (
            site.get(
                "sigungu_code"
            )
            == "11680"
        ),

        "bjdong": (
            site.get(
                "bjdong_code"
            )
            == "10300"
        ),

        "main": (
            site.get(
                "main_no"
            )
            == "0012"
        ),

        "sub": (
            site.get(
                "sub_no"
            )
            == "0000"
        ),

        "zone": (
            site.get(
                "zone"
            )
            == "제3종일반주거지역"
        ),

        "identity complete": (
            site.get(
                "identity_status"
            )
            == "COMPLETE"
        ),

        "coordinate confirmed": (
            site.get(
                "coordinate_status"
            )
            == "CONFIRMED"
        ),

        "x": (
            coordinate.get(
                "x"
            )
            == (
                127.07539280356858
            )
        ),

        "y": (
            coordinate.get(
                "y"
            )
            == (
                37.494197498186885
            )
        ),

        "crs": (
            coordinate.get(
                "crs"
            )
            == "EPSG:4326"
        ),

        "parcel dataset": (
            parcel_reference.get(
                "dataset"
            )
            == "LP_PA_CBND_BUBUN"
        ),

        "parcel verified": (
            parcel_reference.get(
                "strict_pnu_verified"
            )
            is True
        ),

        "geometry not yet loaded": (
            parcel_reference.get(
                "geometry_loaded"
            )
            is False
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
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            "STEP 17-21-C-11-2B-2 "
            "SITE analysis identity integration"
        ),

        "site": (
            site
        ),

        "regulation": (
            regulation
        ),

        "rule_evaluation": (
            rules
        ),

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

    print()

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