# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-6-A
Settlement District Dataset Live Probe

목표
======================================================================
VWorld LT_C_UQ128 취락지구 dataset의 실제 runtime 응답 구조를 검증한다.

검증 SITE
======================================================================
1. BASE
   서울특별시 강남구 개포동 12번지
   expected negative candidate

2. LIVE
   서울특별시 강남구 개포동 13번지
   expected negative candidate

3. POSITIVE
   서울특별시 구로구 천왕동 10번지
   서울시 공식 취락지구 지정 사례
   expected positive candidate

중요
======================================================================
이 probe 단계에서는 아직 Rule Engine TRUE/FALSE를 확정하지 않는다.

확인 대상:
- 주소검색
- coordinate
- HTTP status
- VWorld status
- feature count
- geometry type
- properties
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
    "LT_C_UQ128"
)

REQUEST_TIMEOUT = 30


# ============================================================
# TEST SITES
# ============================================================

SITES = [

    {
        "name":
            "BASE",

        "address":
            "서울특별시 강남구 개포동 12번지",

        "pnu":
            "1168010300100120000",

        "coordinate": {
            "x":
                127.07539280356858,

            "y":
                37.494197498186885,
        },
    },

    {
        "name":
            "LIVE",

        "address":
            "서울특별시 강남구 개포동 13번지",

        "pnu":
            "1168010300100130000",

        "coordinate": {
            "x":
                127.07804416954306,

            "y":
                37.49668484241573,
        },
    },

    {
        "name":
            "POSITIVE",

        "address":
            "서울특별시 구로구 천왕동 10번지",

        "pnu":
            None,

        "coordinate":
            None,
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
        for feature
        in candidates
        if isinstance(
            feature,
            dict,
        )
    ]


# ============================================================
# ADDRESS SEARCH
# ============================================================

def resolve_address(
    address: str,
) -> Tuple[
    Optional[str],
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

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        print(
            "Address JSON error:",
            repr(
                exc
            ),
        )

        return (
            None,
            None,
            None,
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
            None,
        )

    first = safe_dict(
        items[
            0
        ]
    )

    pnu = (
        str(
            first.get(
                "id"
            )
            or ""
        ).strip()
        or None
    )

    point = safe_dict(
        first.get(
            "point"
        )
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
            pnu,
            None,
            None,
        )

    print(
        "Resolved PNU:",
        pnu,
    )

    print(
        "Resolved coordinate:",
        x,
        y,
    )

    return (
        pnu,
        x,
        y,
    )


# ============================================================
# DATA QUERY
# ============================================================

def query_dataset(
    *,
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

    result: Dict[str, Any] = {

        "http_status":
            response.status_code,

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

print(
    "============================================================"
)

print(
    "C-16-6-A SETTLEMENT DISTRICT DATASET PROBE"
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

    pnu = site.get(
        "pnu"
    )

    coordinate = site.get(
        "coordinate"
    )

    if not isinstance(
        coordinate,
        dict,
    ):

        resolved_pnu, x, y = (
            resolve_address(
                site[
                    "address"
                ]
            )
        )

        pnu = (
            pnu
            or resolved_pnu
        )

    else:

        x = coordinate.get(
            "x"
        )

        y = coordinate.get(
            "y"
        )

    print(
        "PNU:",
        pnu,
    )

    print(
        "Coordinate:",
        x,
        y,
    )

    if (
        x is None
        or y is None
    ):

        print(
            "Coordinate unavailable"
        )

        continue

    query_result = (
        query_dataset(
            x=float(
                x
            ),
            y=float(
                y
            ),
        )
    )

    print(
        "HTTP:",
        query_result.get(
            "http_status"
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
            "JSON parse failed:",
            query_result.get(
                "json_error"
            ),
        )

        continue

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    status = (
        response_obj.get(
            "status"
        )
    )

    error = safe_dict(
        response_obj.get(
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
    "IMPORTANT"
)

print(
    "============================================================"
)

print(
    "이 probe는 dataset semantic/response 구조 확인용이다."
)

print(
    "positive/negative evidence 확인 후 runtime FALSE/TRUE 계약을 확정한다."
)