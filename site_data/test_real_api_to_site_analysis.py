# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-2
Real API -> Site -> Final SITE Analysis End-to-End Test

흐름
======================================================================
건축HUB 실제 API
    ↓
create_site()
    ↓
Site 객체
    ↓
analyze_site_object()
    ↓
Final SITE Analysis Object
"""

from __future__ import annotations

import os
import sys

from pathlib import Path

import requests
from dotenv import load_dotenv


from site_data.site_builder import (
    create_site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)


# ============================================================
# ENV
# ============================================================

load_dotenv(
    BASE_DIR
    / ".env"
)

SERVICE_KEY = os.getenv(
    "DATA_API_KEY"
)

if not SERVICE_KEY:

    print(
        "ERROR: API 인증키를 찾을 수 없습니다."
    )

    raise SystemExit(1)


print(
    "API 인증키를 정상적으로 읽었습니다."
)


# ============================================================
# Building HUB API
# ============================================================

URL = (
    "http://apis.data.go.kr/"
    "1613000/BldRgstHubService/"
    "getBrTitleInfo"
)


PARAMS = {
    "sigunguCd": (
        "11680"
    ),

    "bjdongCd": (
        "10300"
    ),

    "bun": (
        "0012"
    ),

    "ji": (
        "0000"
    ),

    "serviceKey": (
        SERVICE_KEY
    ),

    "numOfRows": (
        "100"
    ),

    "pageNo": (
        "1"
    ),

    "_type": (
        "json"
    ),
}


# ============================================================
# request
# ============================================================

response = requests.get(
    URL,
    params=PARAMS,
    timeout=30,
)


print(
    "HTTP 상태 코드:",
    response.status_code,
)


if (
    response.status_code
    != 200
):

    print(
        "API 요청 실패"
    )

    raise SystemExit(1)


# ============================================================
# JSON
# ============================================================

data = response.json()


if (
    "response"
    not in data
):

    print(
        "ERROR: response가 없습니다."
    )

    raise SystemExit(1)


api_response = (
    data[
        "response"
    ]
)

header = (
    api_response[
        "header"
    ]
)


print()

print(
    "API 상태"
)

print(
    "--------------------------------"
)

print(
    "resultCode:",
    header.get(
        "resultCode"
    ),
)

print(
    "resultMsg :",
    header.get(
        "resultMsg"
    ),
)


if (
    header.get(
        "resultCode"
    )
    != "00"
):

    print(
        "API 오류"
    )

    raise SystemExit(1)


# ============================================================
# Building data
# ============================================================

body = (
    api_response[
        "body"
    ]
)

items_data = (
    body.get(
        "items"
    )
    or {}
)

items = (
    items_data.get(
        "item",
        [],
    )
)


if isinstance(
    items,
    dict,
):

    items = [
        items
    ]


print()

print(
    "건축물 조회"
)

print(
    "--------------------------------"
)

print(
    "전체 데이터 수:",
    body.get(
        "totalCount"
    ),
)

print(
    "현재 받은 건축물 수:",
    len(
        items
    ),
)


# ============================================================
# create Site
# ============================================================

site = create_site(
    items
)


if site is None:

    print(
        "ERROR: Site 생성 실패"
    )

    raise SystemExit(1)


print()

print(
    "SITE 생성"
)

print(
    "--------------------------------"
)

print(
    "SITE ID:",
    site.site_id,
)

print(
    "주소:",
    site.address,
)

print(
    "도로명주소:",
    site.road_address,
)

print(
    "시군구코드:",
    site.sigungu_cd,
)

print(
    "법정동코드:",
    site.bjdong_cd,
)

print(
    "본번:",
    site.bun,
)

print(
    "부번:",
    site.ji,
)

print(
    "건축물 수:",
    len(
        site.buildings
    ),
)


# ============================================================
# land
# ============================================================

print()

print(
    "토지 데이터"
)

print(
    "--------------------------------"
)


if site.land:

    print(
        "토지면적:",
        site.land.land_area,
    )

    print(
        "지목:",
        site.land.land_category,
    )

    print(
        "용도지역:",
        site.land.zoning,
    )

else:

    print(
        "토지정보 없음"
    )


# ============================================================
# Final SITE Analysis
# ============================================================

analysis = (
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


analysis_site = (
    analysis[
        "site"
    ]
)

regulation = (
    analysis[
        "regulation"
    ]
)

rules = (
    analysis[
        "rule_evaluation"
    ]
)

requirements = (
    analysis[
        "input_requirements"
    ]
)

dependencies = (
    analysis[
        "external_dependencies"
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


# ============================================================
# console
# ============================================================

print()

print(
    "FINAL SITE ANALYSIS"
)

print(
    "========================================"
)

print(
    "Analysis status:",
    analysis[
        "analysis"
    ][
        "status"
    ],
)

print()

print(
    "SITE ID:",
    analysis_site.get(
        "site_id"
    ),
)

print(
    "주소:",
    analysis_site.get(
        "address"
    ),
)

print(
    "도로명주소:",
    analysis_site.get(
        "road_address"
    ),
)

print(
    "PNU:",
    analysis_site.get(
        "pnu"
    ),
)

print(
    "용도지역:",
    analysis_site.get(
        "zone"
    ),
)

print()

print(
    "Parcel geometry:",
    parcel.get(
        "geometry_type"
    ),
)

print(
    "Parcel loaded:",
    parcel.get(
        "geometry_loaded"
    ),
)

print()

print(
    "확정 건폐율:",
    regulation[
        "building_coverage_ratio"
    ][
        "value"
    ],
)

print(
    "확정 용적률:",
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

print()

print(
    "Remaining PROJECT:",
    requirements.get(
        "project_count"
    ),
)

print(
    "Remaining PROCEDURE:",
    requirements.get(
        "procedure_count"
    ),
)

print(
    "External dependencies:",
    dependencies.get(
        "count"
    ),
)


# ============================================================
# validations
# ============================================================

validations = {

    "API success": (
        header.get(
            "resultCode"
        )
        == "00"
    ),

    "building items exist": (
        len(
            items
        )
        > 0
    ),

    "site id": (
        site.site_id
        == (
            "11680-10300-0012-0000"
        )
    ),

    "road address": (
        bool(
            site.road_address
        )
    ),

    "analysis ready": (
        analysis[
            "analysis"
        ][
            "status"
        ]
        == "READY"
    ),

    "analysis site id": (
        analysis_site.get(
            "site_id"
        )
        == site.site_id
    ),

    "road address propagated": (
        analysis_site.get(
            "road_address"
        )
        == site.road_address
    ),

    "pnu": (
        analysis_site.get(
            "pnu"
        )
        == (
            "1168010300100120000"
        )
    ),

    "parcel loaded": (
        parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "parcel polygon": (
        parcel.get(
            "geometry_type"
        )
        == "Polygon"
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


raise SystemExit(
    0
    if all_pass
    else 1
)