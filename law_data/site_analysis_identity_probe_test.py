# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2A
SITE Analysis Identity/Data Probe

목표
======================================================================
build_site_analysis()가 반환하는 site 객체에
서비스에서 필요한 핵심 SITE identity/data가 얼마나 포함되어 있는지 점검한다.

이번 단계에서는 값을 억지로 채우지 않는다.

1. 현재 site_analysis 객체 조사
2. 필요한 표준 key 존재 여부 확인
3. 누락 key 목록 생성
4. 기존 SITE Builder 연결 필요 여부 판정
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


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
    / "site_analysis_identity_probe.json"
)


# ============================================================
# REQUIRED SITE FIELDS
# ============================================================

FIELD_ALIASES = {

    "address": [
        "address",
        "jibun_address",
        "parcel_address",
        "주소",
    ],

    "road_address": [
        "road_address",
        "road_name_address",
        "도로명주소",
    ],

    "site_id": [
        "site_id",
        "SITE_ID",
        "id",
    ],

    "pnu": [
        "pnu",
        "PNU",
    ],

    "sigungu_code": [
        "sigungu_code",
        "sgg_cd",
        "시군구코드",
    ],

    "bjdong_code": [
        "bjdong_code",
        "bjd_cd",
        "법정동코드",
    ],

    "main_no": [
        "main_no",
        "bonbun",
        "본번",
    ],

    "sub_no": [
        "sub_no",
        "bubun",
        "부번",
    ],

    "x": [
        "x",
        "lon",
        "longitude",
        "representative_x",
    ],

    "y": [
        "y",
        "lat",
        "latitude",
        "representative_y",
    ],

    "zone": [
        "zone",
        "land_use_zone",
        "용도지역",
    ],

    "parcel_area": [
        "parcel_area",
        "area",
        "land_area",
    ],

    "geometry": [
        "geometry",
        "parcel_geometry",
    ],
}


# ============================================================
# util
# ============================================================

def save_json(
    data: Dict[str, Any],
) -> None:

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


def resolve_field(
    site: Dict[str, Any],
    aliases: list[str],
) -> Dict[str, Any]:

    for key in aliases:

        if key not in site:
            continue

        value = site.get(
            key
        )

        if value is None:
            continue

        if (
            isinstance(
                value,
                str,
            )
            and not value.strip()
        ):
            continue

        return {
            "found": True,
            "source_key": key,
            "value": value,
        }

    return {
        "found": False,
        "source_key": None,
        "value": None,
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    analysis = (
        build_site_analysis(
            project_profile={
                "공동주택": "TRUE",
            },

            procedure_profile={
                "도시계획위원회심의": "TRUE",
            },
        )
    )

    site = (
        analysis.get(
            "site",
            {},
        )
    )

    field_status = {}

    for standard_name, aliases in (
        FIELD_ALIASES.items()
    ):

        field_status[
            standard_name
        ] = (
            resolve_field(
                site,
                aliases,
            )
        )

    found = [
        name
        for name, result
        in field_status.items()
        if result[
            "found"
        ]
    ]

    missing = [
        name
        for name, result
        in field_status.items()
        if not result[
            "found"
        ]
    ]

    identity_fields = {
        "address",
        "site_id",
        "pnu",
        "sigungu_code",
        "bjdong_code",
        "main_no",
        "sub_no",
    }

    spatial_fields = {
        "x",
        "y",
        "parcel_area",
        "geometry",
    }

    missing_identity = sorted(
        identity_fields
        & set(
            missing
        )
    )

    missing_spatial = sorted(
        spatial_fields
        & set(
            missing
        )
    )

    requires_site_builder_integration = bool(
        missing_identity
        or missing_spatial
    )

    output = {
        "step": (
            "STEP 17-21-C-11-2A "
            "SITE analysis identity probe"
        ),

        "site_keys": (
            sorted(
                site.keys()
            )
        ),

        "field_status": (
            field_status
        ),

        "summary": {
            "required_field_count": (
                len(
                    FIELD_ALIASES
                )
            ),

            "found_count": (
                len(
                    found
                )
            ),

            "missing_count": (
                len(
                    missing
                )
            ),

            "found": (
                sorted(
                    found
                )
            ),

            "missing": (
                sorted(
                    missing
                )
            ),

            "missing_identity": (
                missing_identity
            ),

            "missing_spatial": (
                missing_spatial
            ),

            "requires_site_builder_integration": (
                requires_site_builder_integration
            ),
        },

        "site": (
            site
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "SITE keys:",
        len(
            site
        ),
    )

    print()

    print(
        "Required fields:",
        len(
            FIELD_ALIASES
        ),
    )

    print(
        "Found:",
        len(
            found
        ),
    )

    print(
        "Missing:",
        len(
            missing
        ),
    )

    print()

    print(
        "Found fields:",
        sorted(
            found
        ),
    )

    print()

    print(
        "Missing fields:",
        sorted(
            missing
        ),
    )

    print()

    print(
        "Missing identity:",
        missing_identity,
    )

    print(
        "Missing spatial:",
        missing_spatial,
    )

    print()

    print(
        "Requires SITE Builder integration:",
        requires_site_builder_integration,
    )

    print()

    print(
        "=== CURRENT SITE ==="
    )

    for key, value in (
        site.items()
    ):

        print(
            f"{key}: {value}"
        )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    # Probe 단계이므로 누락이 있어도 테스트 실패로 처리하지 않는다.
    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )