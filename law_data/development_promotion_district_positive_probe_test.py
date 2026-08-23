# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-2-B
Development Promotion District Known-Positive Probe

목표
======================================================================
공식적으로 개발진흥지구로 지정된 주소를 기준으로
VWorld LT_C_UQ129 dataset의 positive response 구조를 검증한다.

이 테스트의 목적은 SITE rule 판정이 아니라 다음을 확인하는 것이다.

1. 주소 → representative coordinate
2. LT_C_UQ129 query
3. HTTP / VWorld status
4. feature 존재 여부
5. properties 구조
6. geometry 존재 여부

안전 원칙
======================================================================
HTTP 200 ≠ 의미 검증 완료
NOT_FOUND ≠ 자동 FALSE
known-positive에서도 feature가 나오지 않으면
VWorld layer freshness / coverage / query 방식 문제를 의심한다.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

DATASET = (
    "LT_C_UQ129"
)

REQUEST_TIMEOUT = 30


# ============================================================
# KNOWN POSITIVE
# ============================================================

TARGET_ADDRESS = (
    "서울특별시 동대문구 제기동 1082"
)


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
# ADDRESS SEARCH
# ============================================================

def resolve_coordinate(
    address: str,
) -> Tuple[
    Optional[float],
    Optional[float],
]:

    params = {

        "service":
            "search",

        "request":
            "search",

        "version":
            "2.0",

        "crs":
            "EPSG:4326",

        "size":
            10,

        "page":
            1,

        "query":
            address,

        "type":
            "address",

        "category":
            "parcel",

        "format":
            "json",

        "errorformat":
            "json",

        "key":
            API_KEY,
    }

    response = requests.get(
        VWORLD_SEARCH_URL,
        params=params,
        timeout=REQUEST_TIMEOUT,
    )

    print(
        "Address HTTP:",
        response.status_code,
    )

    payload = (
        response.json()
    )

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    print(
        "Address VWorld status:",
        response_obj.get(
            "status"
        ),
    )

    result = safe_dict(
        response_obj.get(
            "result"
        )
    )

    items = safe_list(
        result.get(
            "items"
        )
    )

    print(
        "Address result count:",
        len(
            items
        ),
    )

    if not items:

        return (
            None,
            None,
        )

    first = safe_dict(
        items[
            0
        ]
    )

    point = safe_dict(
        first.get(
            "point"
        )
    )

    print(
        "Resolved item:",
        first,
    )

    try:

        x = float(
            point.get(
                "x"
            )
        )

        y = float(
            point.get(
                "y"
            )
        )

    except (
        TypeError,
        ValueError,
    ):

        return (
            None,
            None,
        )

    return (
        x,
        y,
    )


# ============================================================
# DATA QUERY
# ============================================================

def query_dataset(
    x: float,
    y: float,
) -> Dict[str, Any]:

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

    payload = (
        response.json()
    )

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    features = (
        collect_features(
            payload
        )
    )

    return {

        "http_status":
            response.status_code,

        "vworld_status":
            response_obj.get(
                "status"
            ),

        "error":
            safe_dict(
                response_obj.get(
                    "error"
                )
            ),

        "features":
            features,
    }


# ============================================================
# RUN
# ============================================================

print(
    "============================================================"
)

print(
    "C-16-2-B DEVELOPMENT PROMOTION DISTRICT POSITIVE PROBE"
)

print(
    "Dataset:",
    DATASET,
)

print(
    "Target:",
    TARGET_ADDRESS,
)

print(
    "============================================================"
)


x, y = (
    resolve_coordinate(
        TARGET_ADDRESS
    )
)


print()

print(
    "Coordinate:",
    x,
    y,
)


if (
    x is None
    or y is None
):

    raise RuntimeError(
        "Known-positive address coordinate could not be resolved"
    )


result = (
    query_dataset(
        x=x,
        y=y,
    )
)


print(
    "Data HTTP:",
    result.get(
        "http_status"
    ),
)

print(
    "Data VWorld status:",
    result.get(
        "vworld_status"
    ),
)

print(
    "Error:",
    result.get(
        "error"
    ),
)


features = (
    result.get(
        "features",
        []
    )
)


print(
    "Feature count:",
    len(
        features
    ),
)


for index, feature in enumerate(
    features,
    start=1,
):

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
    "Interpretation"
)

print(
    "============================================================"
)

if (
    result.get(
        "http_status"
    )
    == 200
    and result.get(
        "vworld_status"
    )
    == "OK"
    and features
):

    print(
        "POSITIVE_DATASET_RESPONSE_CONFIRMED"
    )

elif (
    result.get(
        "http_status"
    )
    == 200
    and result.get(
        "vworld_status"
    )
    == "NOT_FOUND"
    and not features
):

    print(
        "KNOWN_POSITIVE_NOT_FOUND"
    )

    print(
        "Do NOT implement runtime FALSE yet."
    )

    print(
        "Check dataset freshness, coverage, or query semantics."
    )

else:

    print(
        "UNRESOLVED_RESPONSE"
    )