# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16
Real Multi-SITE + Runtime Spatial Condition Regression

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
PNU-aware spatial resolver
    ↓
VWorld live Parcel geometry fallback
    ↓
Runtime SITE Spatial Conditions
    ↓
Rule Engine overlay
    ↓
Final SITE Analysis Object

까지 정상적으로 이어지는지 검증한다.

현재 실제 테스트 SITE
======================================================================
서울특별시 강남구 개포동 13번지

SITE ID:
    11680-10300-0013-0000

PNU:
    1168010300100130000

Zone:
    제1종일반주거지역

C-14 안전 정책
======================================================================
1. 다른 PNU에 대표 SITE Parcel snapshot 재사용 금지
2. snapshot PNU 불일치 시 VWorld live provider fallback
3. LP_PA_CBND_BUBUN dataset 사용
4. Polygon / MultiPolygon만 허용
5. Feature PNU와 target PNU 직접 일치 필수
6. live geometry는 EPSG:4326
7. EPSG:4326 좌표에서 parcel area를 임의 계산하지 않음

C-16 Runtime SITE Condition 정책
======================================================================
현재 지원:

- 지구단위계획
- 개발진흥지구
- 취락지구
- 방재지구

현재 LIVE SITE 기대값:

지구단위계획
    TRUE / HIGH
    LT_C_UPISUQ161

개발진흥지구
    FALSE / HIGH
    LT_C_UQ129

취락지구
    FALSE / HIGH
    LT_C_UQ128

방재지구
    FALSE / HIGH
    LT_C_UQ125

C-16-7 방재지구 반영
======================================================================
방재지구 runtime FALSE가 clause 189 상위 branch에 연결되므로
기존 LIVE rule summary:

    63 / 215 / 34 / 2

에서:

    62 / 216 / 34 / 2

로 변경된다.

BCR/FAR:

    60 / 150

은 그대로 유지되어야 한다.
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

EXPECTED_ZONE = (
    "제1종일반주거지역"
)

EXPECTED_BCR = (
    60.0
)

EXPECTED_FAR = (
    150.0
)


EXPECTED_RULE_SUMMARY = {

    "total":
        314,

    "applicable":
        62,

    "not_applicable":
        216,

    "conditional":
        34,

    "unknown":
        2,
}


# ============================================================
# EXPECTED RUNTIME CONDITIONS
# ============================================================

EXPECTED_RUNTIME_CONDITIONS = {

    "지구단위계획": {

        "state":
            "TRUE",

        "confidence":
            "HIGH",

        "dataset":
            "LT_C_UPISUQ161",
    },

    "개발진흥지구": {

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "dataset":
            "LT_C_UQ129",
    },

    "취락지구": {

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "dataset":
            "LT_C_UQ128",
    },

    "방재지구": {

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "dataset":
            "LT_C_UQ125",
    },
}


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

runtime_conditions = (
    analysis_site.get(
        "runtime_conditions",
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

parcel_crs = (
    parcel.get(
        "crs"
    )
)

parcel_crs_status = (
    parcel.get(
        "crs_status"
    )
)

parcel_source = (
    parcel.get(
        "source",
        {},
    )
)

live_source = (
    parcel_source.get(
        "live",
        {},
    )
)

live_coordinate = (
    live_source.get(
        "coordinate",
        {},
    )
)

live_query = (
    live_source.get(
        "query",
        {},
    )
)


# ============================================================
# runtime condition helpers
# ============================================================

def get_runtime_condition(
    name: str,
) -> Dict[str, Any]:

    value = (
        runtime_conditions.get(
            name,
            {},
        )
    )

    if isinstance(
        value,
        dict,
    ):

        return value

    return {}


district_unit_plan = (
    get_runtime_condition(
        "지구단위계획"
    )
)

development_promotion = (
    get_runtime_condition(
        "개발진흥지구"
    )
)

settlement_district = (
    get_runtime_condition(
        "취락지구"
    )
)

disaster_prevention_district = (
    get_runtime_condition(
        "방재지구"
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

print(
    "Parcel CRS:",
    parcel_crs,
)

print(
    "Parcel CRS status:",
    parcel_crs_status,
)

print(
    "Parcel source:",
    parcel_source,
)

print()

print(
    "Runtime conditions:"
)

for name, condition in (
    runtime_conditions.items()
):

    print(
        name,
        "=>",
        condition.get(
            "state"
        ),
        "/",
        condition.get(
            "confidence"
        ),
        "/",
        condition.get(
            "source",
            {},
        ).get(
            "dataset"
        ),
        "/",
        condition.get(
            "resolution"
        ),
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
# Multi-SITE diagnostics
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

print(
    "Parcel provider:",
    parcel_source.get(
        "provider"
    ),
)

print(
    "Live coordinate:",
    live_coordinate,
)

print(
    "Live query:",
    live_query,
)

print(
    "Runtime condition names:",
    list(
        runtime_conditions.keys()
    ),
)


# ============================================================
# validations
# ============================================================

validations = {

    # --------------------------------------------------------
    # API
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # SITE identity
    # --------------------------------------------------------

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
    # Parcel identity
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
    # Live Parcel geometry
    # --------------------------------------------------------

    "parcel loaded": (
        parcel_loaded
        is True
    ),

    "parcel multipolygon": (
        parcel_geometry_type
        == "MultiPolygon"
    ),

    "parcel bounds resolved": (
        isinstance(
            parcel_bounds,
            list,
        )
        and len(
            parcel_bounds
        )
        == 4
    ),

    "parcel CRS": (
        parcel_crs
        == "EPSG:4326"
    ),

    "parcel CRS confirmed": (
        parcel_crs_status
        == "CONFIRMED"
    ),

    # --------------------------------------------------------
    # source metadata
    # --------------------------------------------------------

    "parcel provider VWorld": (
        parcel_source.get(
            "provider"
        )
        == "VWorld"
    ),

    "parcel dataset": (
        parcel_source.get(
            "dataset"
        )
        == "LP_PA_CBND_BUBUN"
    ),

    "parcel source verified": (
        parcel_source.get(
            "verified"
        )
        is True
    ),

    "snapshot mismatch confirmed": (
        parcel_source.get(
            "pnu_match"
        )
        is False
    ),

    "live PNU verified": (
        live_source.get(
            "feature_pnu"
        )
        == EXPECTED_PNU
    ),

    "live dataset": (
        live_source.get(
            "dataset"
        )
        == "LP_PA_CBND_BUBUN"
    ),

    "live query success": (
        live_query.get(
            "classification"
        )
        == "QUERY_SUCCESS"
    ),

    "live query HTTP 200": (
        live_query.get(
            "http_status"
        )
        == 200
    ),

    "live VWorld status OK": (
        live_query.get(
            "vworld_status"
        )
        == "OK"
    ),

    "live coordinate resolved": (
        live_coordinate.get(
            "crs"
        )
        == "EPSG:4326"
        and isinstance(
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

    "live coordinate source": (
        live_coordinate.get(
            "source"
        )
        == "VWORLD_ADDRESS_SEARCH"
    ),

    # --------------------------------------------------------
    # runtime condition collection
    # --------------------------------------------------------

    "runtime conditions exists": (
        isinstance(
            runtime_conditions,
            dict,
        )
        and bool(
            runtime_conditions
        )
    ),

    "runtime condition count >= 4": (
        len(
            runtime_conditions
        )
        >= 4
    ),

    "runtime expected keys": (
        set(
            EXPECTED_RUNTIME_CONDITIONS.keys()
        ).issubset(
            set(
                runtime_conditions.keys()
            )
        )
    ),

    # --------------------------------------------------------
    # district unit plan
    # --------------------------------------------------------

    "district unit plan TRUE": (
        district_unit_plan.get(
            "state"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "지구단위계획"
        ][
            "state"
        ]
    ),

    "district unit plan confidence HIGH": (
        district_unit_plan.get(
            "confidence"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "지구단위계획"
        ][
            "confidence"
        ]
    ),

    "district unit plan dataset": (
        district_unit_plan.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "지구단위계획"
        ][
            "dataset"
        ]
    ),

    # --------------------------------------------------------
    # development promotion
    # --------------------------------------------------------

    "development promotion FALSE": (
        development_promotion.get(
            "state"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "개발진흥지구"
        ][
            "state"
        ]
    ),

    "development promotion confidence HIGH": (
        development_promotion.get(
            "confidence"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "개발진흥지구"
        ][
            "confidence"
        ]
    ),

    "development promotion dataset": (
        development_promotion.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "개발진흥지구"
        ][
            "dataset"
        ]
    ),

    # --------------------------------------------------------
    # settlement district
    # --------------------------------------------------------

    "settlement district FALSE": (
        settlement_district.get(
            "state"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "취락지구"
        ][
            "state"
        ]
    ),

    "settlement district confidence HIGH": (
        settlement_district.get(
            "confidence"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "취락지구"
        ][
            "confidence"
        ]
    ),

    "settlement district dataset": (
        settlement_district.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "취락지구"
        ][
            "dataset"
        ]
    ),

    # --------------------------------------------------------
    # disaster prevention district
    # --------------------------------------------------------

    "disaster prevention FALSE": (
        disaster_prevention_district.get(
            "state"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "방재지구"
        ][
            "state"
        ]
    ),

    "disaster prevention confidence HIGH": (
        disaster_prevention_district.get(
            "confidence"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "방재지구"
        ][
            "confidence"
        ]
    ),

    "disaster prevention dataset": (
        disaster_prevention_district.get(
            "source",
            {},
        ).get(
            "dataset"
        )
        == EXPECTED_RUNTIME_CONDITIONS[
            "방재지구"
        ][
            "dataset"
        ]
    ),

    "disaster prevention query success": (
        disaster_prevention_district.get(
            "evaluation",
            {},
        ).get(
            "query_success"
        )
        is True
    ),

    "disaster prevention no intersection": (
        disaster_prevention_district.get(
            "evaluation",
            {},
        ).get(
            "intersects"
        )
        is False
    ),

    "disaster prevention geometry verified": (
        disaster_prevention_district.get(
            "geometry_verified"
        )
        is True
    ),

    # --------------------------------------------------------
    # zone / numeric
    # --------------------------------------------------------

    "zone exists": (
        bool(
            resolved_zone
        )
    ),

    "zone expected": (
        resolved_zone
        == EXPECTED_ZONE
    ),

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

    "BCR expected": (
        resolved_bcr
        == EXPECTED_BCR
    ),

    "FAR expected": (
        resolved_far
        == EXPECTED_FAR
    ),

    # --------------------------------------------------------
    # rules
    # --------------------------------------------------------

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

    "rule summary expected": (
        rules
        == EXPECTED_RULE_SUMMARY
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
    "Expected rule summary:",
    EXPECTED_RULE_SUMMARY,
)

print(
    "Actual rule summary:",
    rules,
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


print(
    "Analysis coordinate:",
    analysis_site.get(
        "coordinate"
    ),
)


raise SystemExit(
    0
    if all_pass
    else 1
)