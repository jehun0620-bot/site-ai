# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-A
Disaster Prevention District Dataset Probe

목표
======================================================================
VWorld LT_C_UQ125 방재지구 dataset의 실제 runtime response를 검증한다.

검증
======================================================================
NEGATIVE 후보
- 강남구 개포동 12
- 강남구 개포동 13

KNOWN-POSITIVE 후보
- 구로구 개봉동 90-22
- 구로구 개봉동 138-2
- 구로구 개봉동 133-11
- 노원구 월계동 487-17

중요
======================================================================
과거 지정기록만으로 현재 TRUE를 확정하지 않는다.

실제 VWorld 현재 dataset에서:
HTTP
status
feature
geometry
properties

를 직접 확인한다.
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
    "LT_C_UQ125"
)

REQUEST_TIMEOUT = 30


# ============================================================
# TARGETS
# ============================================================

TARGETS = [

    {
        "name":
            "BASE",

        "address":
            "서울특별시 강남구 개포동 12번지",

        "known_coordinate": {
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

        "known_coordinate": {
            "x":
                127.07804416954306,

            "y":
                37.49668484241573,
        },
    },

    {
        "name":
            "CANDIDATE_GAE BONG_90_22".replace(
                " ",
                "",
            ),

        "address":
            "서울특별시 구로구 개봉동 90-22",

        "known_coordinate":
            None,
    },

    {
        "name":
            "CANDIDATE_GAE BONG_138_2".replace(
                " ",
                "",
            ),

        "address":
            "서울특별시 구로구 개봉동 138-2",

        "known_coordinate":
            None,
    },

    {
        "name":
            "CANDIDATE_GAE BONG_133_11".replace(
                " ",
                "",
            ),

        "address":
            "서울특별시 구로구 개봉동 133-11",

        "known_coordinate":
            None,
    },

    {
        "name":
            "CANDIDATE_WOLGYE_487_17",

        "address":
            "서울특별시 노원구 월계동 487-17",

        "known_coordinate":
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

    # --------------------------------------------------------
    # exact parcel match 우선
    # --------------------------------------------------------

    target_normalized = (
        address
        .replace(
            "번지",
            "",
        )
        .strip()
    )

    selected = None

    for item in items:

        if not isinstance(
            item,
            dict,
        ):

            continue

        parcel_address = (
            safe_dict(
                item.get(
                    "address"
                )
            ).get(
                "parcel"
            )
        )

        parcel_normalized = str(
            parcel_address
            or ""
        ).replace(
            "번지",
            "",
        ).strip()

        if (
            parcel_normalized
            == target_normalized
        ):

            selected = item

            break

    if selected is None:

        selected = safe_dict(
            items[
                0
            ]
        )

    address_obj = safe_dict(
        selected.get(
            "address"
        )
    )

    point = safe_dict(
        selected.get(
            "point"
        )
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

    print(
        "Selected parcel:",
        address_obj.get(
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
    "C-16-7-A DISASTER PREVENTION DISTRICT DATASET PROBE"
)

print(
    "Dataset:",
    DATASET,
)

print(
    "============================================================"
)


for target in TARGETS:

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        target[
            "name"
        ]
    )

    print(
        "------------------------------------------------------------"
    )

    address = (
        target[
            "address"
        ]
    )

    print(
        "Address:",
        address,
    )

    known_coordinate = (
        target.get(
            "known_coordinate"
        )
    )

    pnu = None

    if isinstance(
        known_coordinate,
        dict,
    ):

        x = known_coordinate.get(
            "x"
        )

        y = known_coordinate.get(
            "y"
        )

        print(
            "Using known coordinate:",
            x,
            y,
        )

    else:

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
            x=float(
                x
            ),

            y=float(
                y
            ),
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

                "name":
                    target[
                        "name"
                    ],

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
        "NO_POSITIVE_DATASET_RESPONSE_CONFIRMED"
    )

    print(
        "Do not register LT_C_UQ125 runtime condition yet."
    )