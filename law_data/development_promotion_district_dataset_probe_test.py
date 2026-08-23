# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-2-A
Development Promotion District Dataset Live Probe

목표
======================================================================
VWorld 공식 dataset LT_C_UQ129가 실제 runtime에서
개발진흥지구 데이터를 반환하는지 확인한다.

중요
======================================================================
이 테스트는 아직 SITE condition TRUE/FALSE를 판정하지 않는다.

검증 대상:
1. HTTP 상태
2. VWorld response.status
3. 실제 Feature 반환 여부
4. Feature ID
5. properties 구조
6. geometry 존재 여부

안전 원칙:
HTTP 200 ≠ 의미 검증 완료
QUERY_SUCCESS ≠ SITE TRUE
feature 없음은 이 probe 단계에서 바로 FALSE로 승격하지 않는다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


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
# CONFIG
# ============================================================

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

DATASET = (
    "LT_C_UQ129"
)

REQUEST_TIMEOUT = 30


# ============================================================
# SITES
# ============================================================

SITES = [

    {
        "name":
            "BASE",

        "address":
            "서울특별시 강남구 개포동 12번지",

        "pnu":
            "1168010300100120000",

        "x":
            127.07539280356858,

        "y":
            37.494197498186885,
    },

    {
        "name":
            "LIVE",

        "address":
            "서울특별시 강남구 개포동 13번지",

        "pnu":
            "1168010300100130000",

        "x":
            127.07804416954306,

        "y":
            37.49668484241573,
    },
]


# ============================================================
# ENV
# ============================================================

load_dotenv(
    BASE_DIR
    / ".env"
)

API_KEY = (
    os.getenv(
        "VWORLD_API_KEY"
    )
    or os.getenv(
        "VWORLD_KEY"
    )
    or ""
).strip()


if not API_KEY:

    raise RuntimeError(
        "VWORLD API key not found"
    )


# ============================================================
# UTIL
# ============================================================

def safe_dict(
    value: Any,
) -> Dict[str, Any]:

    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def safe_list(
    value: Any,
) -> List[Any]:

    if isinstance(
        value,
        list,
    ):
        return value

    return []


def collect_features(
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:

    response = safe_dict(
        payload.get(
            "response"
        )
    )

    result = safe_dict(
        response.get(
            "result"
        )
    )

    feature_collection = (
        result.get(
            "featureCollection"
        )
    )

    candidates: List[Any] = []

    if isinstance(
        feature_collection,
        dict,
    ):

        candidates.extend(
            safe_list(
                feature_collection.get(
                    "features"
                )
            )
        )

    elif isinstance(
        feature_collection,
        list,
    ):

        for item in feature_collection:

            if not isinstance(
                item,
                dict,
            ):
                continue

            candidates.extend(
                safe_list(
                    item.get(
                        "features"
                    )
                )
            )

    return [
        feature
        for feature in candidates
        if isinstance(
            feature,
            dict,
        )
    ]


# ============================================================
# QUERY
# ============================================================

def query_site(
    site: Dict[str, Any],
) -> Dict[str, Any]:

    x = site[
        "x"
    ]

    y = site[
        "y"
    ]

    params = {

        "service":
            "data",

        "request":
            "GetFeature",

        "data":
            DATASET,

        "key":
            API_KEY,

        "format":
            "json",

        "geometry":
            "true",

        "attribute":
            "true",

        "crs":
            "EPSG:4326",

        "geomFilter":
            f"POINT({x} {y})",

        "size":
            100,

        "page":
            1,
    }

    response = requests.get(
        VWORLD_DATA_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    result: Dict[str, Any] = {

        "http_status":
            response.status_code,

        "content_type":
            response.headers.get(
                "Content-Type"
            ),

        "payload":
            None,

        "json_error":
            None,
    }

    try:

        result[
            "payload"
        ] = response.json()

    except Exception as exc:

        result[
            "json_error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# RUN
# ============================================================

all_probe_ok = True


print(
    "============================================================"
)

print(
    "C-16-2-A DEVELOPMENT PROMOTION DISTRICT DATASET PROBE"
)

print(
    "Dataset:",
    DATASET,
)

print(
    "============================================================"
)


for site in SITES:

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        site[
            "name"
        ]
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        "Address:",
        site[
            "address"
        ],
    )

    print(
        "PNU:",
        site[
            "pnu"
        ],
    )

    print(
        "Coordinate:",
        site[
            "x"
        ],
        site[
            "y"
        ],
    )

    query_result = (
        query_site(
            site
        )
    )

    print(
        "HTTP:",
        query_result.get(
            "http_status"
        ),
    )

    print(
        "Content-Type:",
        query_result.get(
            "content_type"
        ),
    )

    payload = (
        query_result.get(
            "payload"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):

        print(
            "JSON parse:",
            "FAILED",
        )

        print(
            "Error:",
            query_result.get(
                "json_error"
            ),
        )

        all_probe_ok = False

        continue

    response = safe_dict(
        payload.get(
            "response"
        )
    )

    status = (
        response.get(
            "status"
        )
    )

    error = safe_dict(
        response.get(
            "error"
        )
    )

    features = (
        collect_features(
            payload
        )
    )

    print(
        "VWorld status:",
        status,
    )

    print(
        "Error:",
        error,
    )

    print(
        "Feature count:",
        len(
            features
        ),
    )

    if (
        query_result.get(
            "http_status"
        )
        != 200
    ):

        all_probe_ok = False

    if status != "OK":

        all_probe_ok = False

    for index, feature in enumerate(
        features,
        start=1,
    ):

        geometry = safe_dict(
            feature.get(
                "geometry"
            )
        )

        properties = safe_dict(
            feature.get(
                "properties"
            )
        )

        print()

        print(
            f"[FEATURE {index}]"
        )

        print(
            "ID:",
            feature.get(
                "id"
            ),
        )

        print(
            "Geometry type:",
            geometry.get(
                "type"
            ),
        )

        print(
            "Properties:"
        )

        for key in sorted(
            properties.keys()
        ):

            print(
                f"  {key}:",
                properties.get(
                    key
                ),
            )


print()

print(
    "============================================================"
)

print(
    "Probe transport/query pass:",
    all_probe_ok,
)

print(
    "IMPORTANT:"
)

print(
    "Feature 존재 여부만으로 아직 SITE TRUE/FALSE를 확정하지 않는다."
)

print(
    "properties 의미와 geometry를 검증한 뒤 runtime evaluator에 연결한다."
)

print(
    "============================================================"
)