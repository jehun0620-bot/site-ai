# -*- coding: utf-8 -*-

"""
STEP 17-21-C-15-2
District Unit Plan Runtime LIVE Test

대상:
서울특별시 강남구 개포동 13번지

목표:
C-14에서 확보한 실제 LIVE Parcel Polygon을
C-15 spatial_condition_evaluator에 연결하여
지구단위계획 condition을 runtime에서 판정한다.
"""

from __future__ import annotations

from site_data.site_builder import (
    create_site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)

from law_data.spatial_condition_evaluator import (
    resolve_site_spatial_condition,
)

import os
import requests

from pathlib import Path

from dotenv import load_dotenv


# ============================================================
# PATH / ENV
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

load_dotenv(
    BASE_DIR
    / ".env"
)

SERVICE_KEY = os.getenv(
    "DATA_API_KEY"
)

if not SERVICE_KEY:

    raise RuntimeError(
        "DATA_API_KEY를 찾을 수 없습니다."
    )


# ============================================================
# TEST SITE
# ============================================================

SIGUNGU_CD = "11680"
BJDONG_CD = "10300"
BUN = "0013"
JI = "0000"

EXPECTED_PNU = (
    "1168010300100130000"
)


# ============================================================
# Building HUB
# ============================================================

URL = (
    "http://apis.data.go.kr/"
    "1613000/BldRgstHubService/"
    "getBrTitleInfo"
)

PARAMS = {
    "sigunguCd": SIGUNGU_CD,
    "bjdongCd": BJDONG_CD,
    "bun": BUN,
    "ji": JI,
    "serviceKey": SERVICE_KEY,
    "numOfRows": "100",
    "pageNo": "1",
    "_type": "json",
}


response = requests.get(
    URL,
    params=PARAMS,
    timeout=30,
)

print(
    "Building HTTP:",
    response.status_code,
)

if response.status_code != 200:

    raise SystemExit(
        1
    )


data = response.json()

api_response = (
    data.get(
        "response",
        {}
    )
)

header = (
    api_response.get(
        "header",
        {}
    )
)

if (
    header.get(
        "resultCode"
    )
    != "00"
):

    print(
        "Building API error:",
        header,
    )

    raise SystemExit(
        1
    )


body = (
    api_response.get(
        "body",
        {}
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
        []
    )
)

if isinstance(
    items,
    dict,
):

    items = [
        items
    ]


# ============================================================
# SITE
# ============================================================

site_object = (
    create_site(
        items
    )
)

if site_object is None:

    raise RuntimeError(
        "SITE 생성 실패"
    )


analysis = (
    analyze_site_object(
        site=site_object,

        project_profile={
            "공동주택": "TRUE",
        },

        procedure_profile={
            "도시계획위원회심의":
                "TRUE",
        },
    )
)


analysis_site = (
    analysis.get(
        "site",
        {}
    )
)

parcel = (
    analysis_site
    .get(
        "spatial",
        {}
    )
    .get(
        "parcel",
        {}
    )
)


# ============================================================
# diagnostics
# ============================================================

print()

print(
    "=== SITE ==="
)

print(
    "SITE ID:",
    analysis_site.get(
        "site_id"
    ),
)

print(
    "PNU:",
    analysis_site.get(
        "pnu"
    ),
)

print(
    "Zone:",
    analysis_site.get(
        "zone"
    ),
)

print(
    "Coordinate:",
    analysis_site.get(
        "coordinate"
    ),
)


print()

print(
    "=== PARCEL ==="
)

print(
    "PNU:",
    parcel.get(
        "pnu"
    ),
)

print(
    "Provider:",
    parcel.get(
        "source",
        {}
    ).get(
        "provider"
    ),
)

print(
    "Geometry:",
    parcel.get(
        "geometry_type"
    ),
)

print(
    "Loaded:",
    parcel.get(
        "geometry_loaded"
    ),
)

print(
    "CRS:",
    parcel.get(
        "crs"
    ),
)

print(
    "Bounds:",
    parcel.get(
        "bounds"
    ),
)


# ============================================================
# C-15 runtime condition
# ============================================================

condition = (
    resolve_site_spatial_condition(
        condition_name=(
            "지구단위계획"
        ),

        site=analysis_site,

        parcel=parcel,
    )
)


print()

print(
    "=== DISTRICT UNIT PLAN ==="
)

print(
    "State:",
    condition.get(
        "state"
    ),
)

print(
    "Confidence:",
    condition.get(
        "confidence"
    ),
)

print(
    "Resolution:",
    condition.get(
        "resolution"
    ),
)

print(
    "PNU:",
    condition.get(
        "pnu"
    ),
)

print(
    "Source:",
    condition.get(
        "source"
    ),
)

print(
    "Geometry verified:",
    condition.get(
        "geometry_verified"
    ),
)

print(
    "Evaluation:",
    condition.get(
        "evaluation"
    ),
)

print(
    "Evidence:",
    condition.get(
        "evidence"
    ),
)


# ============================================================
# validation
# ============================================================

evaluation = (
    condition.get(
        "evaluation",
        {}
    )
)

source = (
    condition.get(
        "source",
        {}
    )
)

validations = {

    "site pnu": (
        analysis_site.get(
            "pnu"
        )
        == EXPECTED_PNU
    ),

    "parcel pnu": (
        parcel.get(
            "pnu"
        )
        == EXPECTED_PNU
    ),

    "parcel loaded": (
        parcel.get(
            "geometry_loaded"
        )
        is True
    ),

    "parcel CRS": (
        parcel.get(
            "crs"
        )
        == "EPSG:4326"
    ),

    "parcel provider VWorld": (
        parcel.get(
            "source",
            {}
        ).get(
            "provider"
        )
        == "VWorld"
    ),

    "condition pnu": (
        condition.get(
            "pnu"
        )
        == EXPECTED_PNU
    ),

    "condition dataset": (
        source.get(
            "dataset"
        )
        == "LT_C_UPISUQ161"
    ),

    "condition query success": (
        evaluation.get(
            "query_success"
        )
        is True
    ),

    "condition state resolved": (
        condition.get(
            "state"
        )
        in {
            "TRUE",
            "FALSE",
        }
    ),

    "geometry verified": (
        condition.get(
            "geometry_verified"
        )
        is True
    ),
}


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