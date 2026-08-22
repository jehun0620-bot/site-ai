# -*- coding: utf-8 -*-

"""
STEP 17-21-C-14-1
Real Multi-SITE Validation

목표
======================================================================
대표 SITE가 아닌 실제 다른 필지를 Building HUB API에서 조회한 뒤,

건축HUB 실제 API
    ↓
create_site()
    ↓
Site 객체
    ↓
실제 토지정보 / 용도지역
    ↓
analyze_site_object()
    ↓
dynamic zone numeric
    ↓
dynamic rule evaluation
    ↓
Final SITE Analysis Object

까지 정상적으로 이어지는지 검증한다.

중요
======================================================================
이 테스트는 기존 대표 SITE:

    서울특별시 강남구 개포동 12번지
    SITE ID: 11680-10300-0012-0000
    PNU: 1168010300100120000

와 다른 실제 SITE를 사용한다.

현재 C-14 첫 real SITE:

    서울특별시 강남구 개포동 13번지
    SITE ID: 11680-10300-0013-0000
    PNU: 1168010300100130000

C-13 정책에 따라 다른 PNU에 대표 SITE의 Parcel snapshot을
재사용해서는 안 된다.

따라서 현재 runtime에서 해당 PNU의 geometry source가 확보되지 않았다면:

    geometry_loaded = False

는 정상 상태일 수 있다.
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict

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
# TEST SITE
# ============================================================

TARGET_SIGUNGU_CD = (
    "11680"
)

TARGET_BJDONG_CD = (
    "10300"
)

TARGET_BUN = (
    "0013"
)

TARGET_JI = (
    "0000"
)

EXPECTED_SITE_ID = (
    "11680-10300-0013-0000"
)

EXPECTED_PNU = (
    "1168010300100130000"
)

BASE_SITE_ID = (
    "11680-10300-0012-0000"
)

BASE_PNU = (
    "1168010300100120000"
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

    raise SystemExit(
        1
    )


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
        TARGET_SIGUNGU_CD
    ),

    "bjdongCd": (
        TARGET_BJDONG_CD
    ),

    "bun": (
        TARGET_BUN
    ),

    "ji": (
        TARGET_JI
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

try:

    response = requests.get(
        URL,
        params=PARAMS,
        timeout=30,
    )

except requests.RequestException as exc:

    print(
        "Building HUB 요청 자체가 실패했습니다."
    )

    print(
        "ERROR:",
        repr(
            exc
        ),
    )

    raise SystemExit(
        1
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

    print(
        "Content-Type:",
        response.headers.get(
            "Content-Type"
        ),
    )

    print(
        "Response preview:",
        repr(
            response.text[
                :1000
            ]
        ),
    )

    raise SystemExit(
        1
    )


# ============================================================
# response diagnostics
# ============================================================

content_type = (
    response.headers.get(
        "Content-Type",
        "",
    )
)

response_text = (
    response.text
    or ""
)


print(
    "Content-Type:",
    content_type,
)

print(
    "Response length:",
    len(
        response_text
    ),
)


if not response_text.strip():

    print(
        "ERROR: HTTP 200이지만 응답 본문이 비어 있습니다."
    )

    raise SystemExit(
        1
    )


# ============================================================
# JSON
# ============================================================

try:

    data: Dict[
        str,
        Any
    ] = (
        response.json()
    )

except requests.exceptions.JSONDecodeError:

    print()

    print(
        "ERROR: HTTP 200 응답을 JSON으로 파싱하지 못했습니다."
    )

    print(
        "Content-Type:",
        content_type,
    )

    print(
        "Response length:",
        len(
            response_text
        ),
    )

    print(
        "Response preview:",
        repr(
            response_text[
                :1200
            ]
        ),
    )

    # --------------------------------------------------------
    # requests 버전에 따라 JSONDecodeError alias가
    # 다르게 동작할 가능성에 대비하여 여기서 종료
    # --------------------------------------------------------

    raise SystemExit(
        1
    )

except json.JSONDecodeError:

    print()

    print(
        "ERROR: JSON decoding 실패"
    )

    print(
        "Content-Type:",
        content_type,
    )

    print(
        "Response length:",
        len(
            response_text
        ),
    )

    print(
        "Response preview:",
        repr(
            response_text[
                :1200
            ]
        ),
    )

    raise SystemExit(
        1
    )


if not isinstance(
    data,
    dict,
):

    print(
        "ERROR: API 최상위 응답이 dict가 아닙니다."
    )

    print(
        "TYPE:",
        type(
            data
        ),
    )

    raise SystemExit(
        1
    )


if (
    "response"
    not in data
):

    print(
        "ERROR: response가 없습니다."
    )

    print(
        "Top keys:",
        list(
            data.keys()
        ),
    )

    print(
        "Response preview:",
        repr(
            response_text[
                :1200
            ]
        ),
    )

    raise SystemExit(
        1
    )


api_response = (
    data[
        "response"
    ]
)

header = (
    api_response.get(
        "header",
        {},
    )
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

    raise SystemExit(
        1
    )


# ============================================================
# Building data
# ============================================================

body = (
    api_response.get(
        "body",
        {},
    )
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


if items is None:

    items = []


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


if not items:

    print(
        "ERROR: 대상 필지의 건축물 데이터가 없습니다."
    )

    raise SystemExit(
        1
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

    raise SystemExit(
        1
    )


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

print(
    "좌표 X:",
    getattr(
        site,
        "x",
        None,
    ),
)

print(
    "좌표 Y:",
    getattr(
        site,
        "y",
        None,
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

spatial = (
    analysis_site.get(
        "spatial",
        {},
    )
)

parcel = (
    spatial.get(
        "parcel",
        {},
    )
)


# ============================================================
# resolved values
# ============================================================

resolved_site_id = (
    analysis_site.get(
        "site_id"
    )
)

resolved_pnu = (
    analysis_site.get(
        "pnu"
    )
)

resolved_zone = (
    analysis_site.get(
        "zone"
    )
)

resolved_bcr = (
    regulation.get(
        "building_coverage_ratio",
        {},
    ).get(
        "value"
    )
)

resolved_far = (
    regulation.get(
        "floor_area_ratio",
        {},
    ).get(
        "value"
    )
)

parcel_pnu = (
    parcel.get(
        "pnu"
    )
)

parcel_loaded = (
    parcel.get(
        "geometry_loaded"
    )
)

parcel_geometry_type = (
    parcel.get(
        "geometry_type"
    )
)

parcel_bounds = (
    parcel.get(
        "bounds"
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
    resolved_site_id,
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
    resolved_pnu,
)

print(
    "용도지역:",
    resolved_zone,
)

print()

print(
    "Parcel PNU:",
    parcel_pnu,
)

print(
    "Parcel geometry:",
    parcel_geometry_type,
)

print(
    "Parcel loaded:",
    parcel_loaded,
)

print(
    "Parcel bounds:",
    parcel_bounds,
)

print()

print(
    "확정 건폐율:",
    resolved_bcr,
)

print(
    "확정 용적률:",
    resolved_far,
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
# C-14 Multi-SITE diagnostics
# ============================================================

print()

print(
    "MULTI-SITE DIAGNOSTICS"
)

print(
    "========================================"
)

print(
    "Different SITE from BASE:",
    resolved_site_id
    != BASE_SITE_ID,
)

print(
    "Different PNU from BASE:",
    resolved_pnu
    != BASE_PNU,
)

print(
    "Expected SITE ID:",
    EXPECTED_SITE_ID,
)

print(
    "Expected PNU:",
    EXPECTED_PNU,
)

print(
    "Resolved zone:",
    resolved_zone,
)

print(
    "Resolved BCR/FAR:",
    (
        resolved_bcr,
        resolved_far,
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
        == EXPECTED_SITE_ID
    ),

    "site differs from base": (
        site.site_id
        != BASE_SITE_ID
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
        resolved_site_id
        == site.site_id
    ),

    "analysis site differs from base": (
        resolved_site_id
        != BASE_SITE_ID
    ),

    "road address propagated": (
        analysis_site.get(
            "road_address"
        )
        == site.road_address
    ),

    "pnu": (
        resolved_pnu
        == EXPECTED_PNU
    ),

    "pnu differs from base": (
        resolved_pnu
        != BASE_PNU
    ),

    # --------------------------------------------------------
    # 다른 PNU에 대표 SITE snapshot이 누수되면 안 된다.
    #
    # 현재 runtime source가 없으면 geometry_loaded=False도 정상.
    # 중요한 것은 parcel의 PNU context가 현재 SITE와 일치하는 것.
    # --------------------------------------------------------

    "parcel pnu matches site": (
        parcel_pnu
        == resolved_pnu
    ),

    "parcel not base pnu": (
        parcel_pnu
        != BASE_PNU
    ),

    # --------------------------------------------------------
    # 실제 토지 API에서 zone이 확보되어야
    # dynamic base numeric 검증이 가능하다.
    # --------------------------------------------------------

    "zone exists": (
        bool(
            resolved_zone
        )
    ),

    # --------------------------------------------------------
    # C-14에서는 특정 zone/BCR/FAR을 미리 가정하지 않는다.
    #
    # 실제 토지정보로 결정된 zone에 따라 resolver가
    # 유효한 numeric을 반환했는지만 확인한다.
    # --------------------------------------------------------

    "BCR resolved": (
        isinstance(
            resolved_bcr,
            (
                int,
                float,
            ),
        )
    ),

    "FAR resolved": (
        isinstance(
            resolved_far,
            (
                int,
                float,
            ),
        )
    ),

    "BCR positive": (
        isinstance(
            resolved_bcr,
            (
                int,
                float,
            ),
        )
        and resolved_bcr
        > 0
    ),

    "FAR positive": (
        isinstance(
            resolved_far,
            (
                int,
                float,
            ),
        )
        and resolved_far
        > 0
    ),

    "rules 314": (
        rules.get(
            "total"
        )
        == 314
    ),

    "rule summary complete": (
        sum(
            (
                rules.get(
                    "applicable",
                    0,
                ),
                rules.get(
                    "not_applicable",
                    0,
                ),
                rules.get(
                    "conditional",
                    0,
                ),
                rules.get(
                    "unknown",
                    0,
                ),
            )
        )
        == 314
    ),
    "zone expected": (
        resolved_zone
        == "제1종일반주거지역"
    ),

    "BCR expected": (
        resolved_bcr
        == 60.0
    ),

    "FAR expected": (
        resolved_far
        == 150.0
    ),

    "rule summary expected": (
        rules
        == {
            "total": 314,
            "applicable": 63,
            "not_applicable": 215,
            "conditional": 34,
            "unknown": 2,
        }
    ),
}



all_pass = all(
    validations.values()
)


# ============================================================
# result
# ============================================================

print()

print(
    "VALIDATION"
)

print(
    "========================================"
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