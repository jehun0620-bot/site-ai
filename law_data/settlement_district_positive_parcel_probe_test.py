# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-6-B
Settlement District Precise Positive Parcel Probe

목표
======================================================================
서울시 공식 취락지구 지정 자료에서 직접 확인되는
연지마을 개별 필지를 이용해 VWorld LT_C_UQ128
positive response를 검증한다.

후보 필지
======================================================================
- 서울특별시 구로구 천왕동 10-39
- 서울특별시 구로구 천왕동 10-42
- 서울특별시 구로구 천왕동 7-9
- 서울특별시 구로구 천왕동 7-8

안전 원칙
======================================================================
'천왕동 10번지 일대'라는 대표주소만으로 TRUE 판정하지 않는다.

주소검색으로 실제 PNU / 좌표를 확보한 후
LT_C_UQ128 POINT query의 Feature를 직접 확인한다.
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
# TARGET PARCELS
# ============================================================

TARGETS = [

    "서울특별시 구로구 천왕동 10-39",

    "서울특별시 구로구 천왕동 10-42",

    "서울특별시 구로구 천왕동 7-9",

    "서울특별시 구로구 천왕동 7-8",
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

    # --------------------------------------------------------
    # exact parcel candidate 우선
    # --------------------------------------------------------

    selected = None

    normalized_target = (
        address
        .replace(
            "번지",
            "",
        )
        .strip()
    )

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        item_address = safe_dict(
            item.get(
                "address"
            )
        )

        parcel_text = str(
            item_address.get(
                "parcel"
            )
            or ""
        ).strip()

        normalized_parcel = (
            parcel_text
            .replace(
                "번지",
                "",
            )
            .strip()
        )

        if (
            normalized_parcel
            == normalized_target
        ):

            selected = (
                item
            )

            break

    if selected is None:

        selected = safe_dict(
            items[
                0
            ]
        )

    pnu = (
        str(
            selected.get(
                "id"
            )
            or ""
        ).strip()
        or None
    )

    point = safe_dict(
        selected.get(
            "point"
        )
    )

    selected_address = safe_dict(
        selected.get(
            "address"
        )
    )

    print(
        "Selected parcel:",
        selected_address.get(
            "parcel"
        ),
    )

    print(
        "Resolved PNU:",
        pnu,
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

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        return {

            "http_status":
                response.status_code,

            "payload":
                None,

            "json_error":
                repr(
                    exc
                ),
        }

    return {

        "http_status":
            response.status_code,

        "payload":
            payload,

        "json_error":
            None,
    }


# ============================================================
# RUN
# ============================================================

positive_candidates = []


print(
    "============================================================"
)

print(
    "C-16-6-B SETTLEMENT DISTRICT POSITIVE PARCEL PROBE"
)

print(
    "Dataset:",
    DATASET,
)

print(
    "============================================================"
)


for address in TARGETS:

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        address
    )

    print(
        "------------------------------------------------------------"
    )

    pnu, x, y = (
        resolve_address(
            address
        )
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

    payload = (
        result.get(
            "payload"
        )
    )

    if not isinstance(
        payload,
        dict,
    ):

        print(
            "JSON failed:",
            result.get(
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

    if (
        result.get(
            "http_status"
        )
        == 200
        and status
        == "OK"
        and features
    ):

        positive_candidates.append(
            {
                "address":
                    address,

                "pnu":
                    pnu,

                "x":
                    x,

                "y":
                    y,

                "feature_count":
                    len(
                        features
                    ),
            }
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
    "POSITIVE CANDIDATES"
)

print(
    "============================================================"
)

for item in positive_candidates:

    print(
        item
    )


print()

print(
    "Positive candidate count:",
    len(
        positive_candidates
    ),
)


if positive_candidates:

    print(
        "POSITIVE_DATASET_RESPONSE_CONFIRMED"
    )

else:

    print(
        "NO_POSITIVE_PARCEL_CONFIRMED"
    )

    print(
        "Do not implement LT_C_UQ128 runtime FALSE yet."
    )