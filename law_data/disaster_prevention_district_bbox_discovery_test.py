# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-7-B
Disaster Prevention District BBOX Discovery

목표
======================================================================
VWorld LT_C_UQ125 방재지구 레이어에서 현재 살아 있는 positive feature를
주소 가정 없이 dataset 자체에서 직접 탐색한다.

탐색 지역
======================================================================
1. 전라남도 목포시
2. 경상남도 산청군

방법
======================================================================
큰 행정구역 BBOX를 작은 grid cell로 분할하여
각 cell마다:

    geomFilter = BOX(minx,miny,maxx,maxy)

GetFeature를 실행한다.

positive feature 발견 시:
- feature id
- geometry
- properties
- representative point

를 출력한다.

중요
======================================================================
이 단계는 discovery다.

feature를 찾은 뒤 다음 단계에서:
representative point
→ Parcel PNU
→ Parcel Polygon
→ LT_C_UQ125 intersection

까지 다시 검증한다.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from dotenv import load_dotenv

from shapely.geometry import shape


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
    "LT_C_UQ125"
)

REQUEST_TIMEOUT = 30


# ============================================================
# SEARCH REGIONS
#
# 넓은 지역 전체가 아니라 대략적인 행정구역 bounds.
# 각 region은 grid로 다시 분할한다.
# ============================================================

SEARCH_REGIONS = {

    "MOKPO": {

        "name":
            "전라남도 목포시",

        "bounds": (
            126.33,
            34.73,
            126.47,
            34.86,
        ),

        # 약 0.02도 단위
        "step_x":
            0.02,

        "step_y":
            0.02,
    },

    "SANCHEONG": {

        "name":
            "경상남도 산청군",

        "bounds": (
            127.62,
            35.28,
            127.98,
            35.57,
        ),

        "step_x":
            0.02,

        "step_y":
            0.02,
    },
}


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


def generate_grid(
    *,
    bounds: Tuple[
        float,
        float,
        float,
        float,
    ],
    step_x: float,
    step_y: float,
):

    minx, miny, maxx, maxy = (
        bounds
    )

    y = miny

    while y < maxy:

        x = minx

        while x < maxx:

            cell_maxx = min(
                x + step_x,
                maxx,
            )

            cell_maxy = min(
                y + step_y,
                maxy,
            )

            yield (
                x,
                y,
                cell_maxx,
                cell_maxy,
            )

            x += step_x

        y += step_y


# ============================================================
# QUERY
# ============================================================

def query_bbox(
    *,
    bbox: Tuple[
        float,
        float,
        float,
        float,
    ],
) -> Dict[str, Any]:

    minx, miny, maxx, maxy = (
        bbox
    )

    params = {

        "service":
            "data",

        "version":
            "2.0",

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
            (
                f"BOX("
                f"{minx},"
                f"{miny},"
                f"{maxx},"
                f"{maxy}"
                f")"
            ),

        "size":
            100,

        "page":
            1,
    }

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:

        return {

            "http_status":
                None,

            "status":
                None,

            "classification":
                "TRANSPORT_ERROR",

            "error":
                repr(
                    exc
                ),

            "features":
                [],
        }

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        return {

            "http_status":
                response.status_code,

            "status":
                None,

            "classification":
                "JSON_ERROR",

            "error":
                repr(
                    exc
                ),

            "features":
                [],
        }

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

    features = (
        collect_features(
            payload
        )
    )

    if (
        response.status_code
        == 200
        and status
        == "OK"
    ):

        classification = (
            "QUERY_SUCCESS"
        )

    elif (
        response.status_code
        == 200
        and status
        == "NOT_FOUND"
        and not features
    ):

        classification = (
            "QUERY_EMPTY"
        )

    else:

        classification = (
            "QUERY_FAILED"
        )

    return {

        "http_status":
            response.status_code,

        "status":
            status,

        "classification":
            classification,

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
# FEATURE SUMMARY
# ============================================================

def summarize_feature(
    feature: Dict[str, Any],
) -> Dict[str, Any]:

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

    representative_point = None

    try:

        geom = (
            shape(
                geometry
            )
        )

        if (
            not geom.is_empty
        ):

            point = (
                geom.representative_point()
            )

            representative_point = {

                "x":
                    float(
                        point.x
                    ),

                "y":
                    float(
                        point.y
                    ),
            }

    except Exception as exc:

        representative_point = {

            "error":
                repr(
                    exc
                ),
        }

    return {

        "feature_id":
            feature.get(
                "id"
            ),

        "geometry_type":
            geometry.get(
                "type"
            ),

        "properties":
            properties,

        "representative_point":
            representative_point,
    }


# ============================================================
# RUN
# ============================================================

found: Dict[
    str,
    Dict[str, Any],
] = {}

query_count = 0


print(
    "============================================================"
)

print(
    "C-16-7-B DISASTER PREVENTION DISTRICT BBOX DISCOVERY"
)

print(
    "Dataset:",
    DATASET,
)

print(
    "============================================================"
)


for region_key, region in (
    SEARCH_REGIONS.items()
):

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        region_key,
        "/",
        region[
            "name"
        ],
    )

    print(
        "------------------------------------------------------------"
    )

    region_found = False

    for cell_index, bbox in enumerate(
        generate_grid(
            bounds=(
                region[
                    "bounds"
                ]
            ),

            step_x=(
                region[
                    "step_x"
                ]
            ),

            step_y=(
                region[
                    "step_y"
                ]
            ),
        ),
        start=1,
    ):

        query_count += 1

        result = (
            query_bbox(
                bbox=bbox
            )
        )

        features = (
            result.get(
                "features",
                []
            )
        )

        # ----------------------------------------------------
        # 너무 많은 empty 출력은 생략
        # ----------------------------------------------------

        if not features:

            if (
                result.get(
                    "classification"
                )
                not in {
                    "QUERY_EMPTY",
                    "QUERY_SUCCESS",
                }
            ):

                print(
                    "CELL",
                    cell_index,
                    "BBOX",
                    bbox,
                    "=>",
                    result.get(
                        "classification"
                    ),
                    result.get(
                        "status"
                    ),
                    result.get(
                        "error"
                    ),
                )

            continue

        print()

        print(
            "POSITIVE CELL"
        )

        print(
            "Index:",
            cell_index,
        )

        print(
            "BBOX:",
            bbox,
        )

        print(
            "HTTP:",
            result.get(
                "http_status"
            ),
        )

        print(
            "Status:",
            result.get(
                "status"
            ),
        )

        print(
            "Feature count:",
            len(
                features
            ),
        )

        for feature in features:

            summary = (
                summarize_feature(
                    feature
                )
            )

            feature_id = str(
                summary.get(
                    "feature_id"
                )
                or ""
            )

            print()

            print(
                "Feature:",
                feature_id,
            )

            print(
                "Geometry:",
                summary.get(
                    "geometry_type"
                ),
            )

            print(
                "Representative point:",
                summary.get(
                    "representative_point"
                ),
            )

            print(
                "Properties:"
            )

            properties = (
                summary.get(
                    "properties",
                    {}
                )
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

            if (
                feature_id
                and feature_id
                not in found
            ):

                found[
                    feature_id
                ] = {

                    "region":
                        region_key,

                    "bbox":
                        bbox,

                    **summary,
                }

        region_found = True

        # ----------------------------------------------------
        # discovery 목적:
        # 한 지역에서 positive를 찾으면 추가 grid 탐색 중단
        # ----------------------------------------------------

        if region_found:

            break


# ============================================================
# FINAL
# ============================================================

print()

print(
    "============================================================"
)

print(
    "DISCOVERY RESULT"
)

print(
    "============================================================"
)

print(
    "Query count:",
    query_count,
)

print(
    "Unique feature count:",
    len(
        found
    ),
)


for feature_id, item in (
    found.items()
):

    print()

    print(
        feature_id,
        "=>",
        item
    )


print()


if found:

    print(
        "CURRENT_POSITIVE_FEATURE_DISCOVERED"
    )

else:

    print(
        "NO_CURRENT_POSITIVE_FEATURE_DISCOVERED"
    )

    print(
        "Do not register LT_C_UQ125 runtime FALSE policy yet."
    )