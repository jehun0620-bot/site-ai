# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-A
Development Density Management Area Source Discovery

개발밀도관리구역 source discovery

목표
======================================================================
Rule Condition Registry에 이미 존재하는 SITE predicate:

    개발밀도관리구역

을 runtime spatial condition으로 연결하기 전에,
실제 공간 polygon source가 존재하는지 검증한다.

현재 유력 구조
======================================================================
표준 토지이용계획 분류상:

    UQ141
        구역

    UQQ700
        개발밀도관리구역

따라서 독립 dataset:

    LT_C_UQQ700
    LT_C_UQ700

등을 임의로 runtime registry에 등록하지 않는다.

우선 VWorld:

    LT_C_UQ141

레이어를 실제 조회하여 feature properties 안에:

    UQQ700
    개발밀도관리구역

이 존재하는지 탐색한다.

안전 원칙
======================================================================
1. dataset 이름을 추정만으로 runtime registry에 등록하지 않는다.
2. QUERY_EMPTY를 곧바로 SITE FALSE로 해석하지 않는다.
3. source discovery 단계에서는 판정하지 않는다.
4. 실제 Polygon / MultiPolygon feature를 확인해야 한다.
5. 개발밀도관리구역 식별 속성을 확인해야 한다.
6. positive feature 발견 후 별도 단계에서:
       representative point
       -> Parcel PNU
       -> Parcel Polygon
       -> 실제 geometry intersection
   을 검증한다.
7. API key는 출력하지 않는다.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

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
# VWorld
# ============================================================

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

REQUEST_TIMEOUT = 30


# ============================================================
# CANDIDATE SOURCE
# ============================================================
#
# 표준분류:
#
# UQ141
#   구역
#
# UQQ700
#   개발밀도관리구역
#
# VWorld layer naming convention상
# LT_C_UQ141을 우선 검증한다.
# ============================================================

PRIMARY_DATASET = (
    "LT_C_UQ141"
)

TARGET_STANDARD_CODE = (
    "UQQ700"
)

TARGET_NAME = (
    "개발밀도관리구역"
)


# ============================================================
# OPTIONAL DATASET PROBES
# ============================================================
#
# 아래 후보는 존재한다고 가정하지 않는다.
#
# 잘못된 dataset 추정이 runtime evaluator에 들어가는 것을 막기 위해
# 단순 probe만 수행한다.
# ============================================================

DATASET_PROBES = [
    "LT_C_UQ141",
    "LT_C_UQQ700",
    "LT_C_UQ700",
]


# ============================================================
# SEARCH REGIONS
# ============================================================
#
# 1차 목적은 source structure 확인이다.
#
# 전국을 너무 작은 grid로 탐색하면 호출량이 커지므로
# 주요 도시권을 비교적 큰 cell로 탐색한다.
#
# 필요하면 실행 결과를 본 뒤 특정 지역을 추가한다.
# ============================================================

SEARCH_REGIONS: Dict[
    str,
    Dict[str, Any],
] = {

    "SEOUL": {

        "name":
            "서울특별시",

        "bounds": (
            126.75,
            37.40,
            127.20,
            37.72,
        ),

        "step_x":
            0.05,

        "step_y":
            0.05,
    },

    "BUSAN": {

        "name":
            "부산광역시",

        "bounds": (
            128.75,
            34.95,
            129.35,
            35.40,
        ),

        "step_x":
            0.06,

        "step_y":
            0.05,
    },

    "DAEGU": {

        "name":
            "대구광역시",

        "bounds": (
            128.35,
            35.70,
            128.80,
            36.05,
        ),

        "step_x":
            0.05,

        "step_y":
            0.05,
    },

    "DAEJEON": {

        "name":
            "대전광역시",

        "bounds": (
            127.25,
            36.20,
            127.55,
            36.50,
        ),

        "step_x":
            0.05,

        "step_y":
            0.05,
    },

    "GWANGJU": {

        "name":
            "광주광역시",

        "bounds": (
            126.70,
            35.00,
            127.05,
            35.30,
        ),

        "step_x":
            0.05,

        "step_y":
            0.05,
    },

    "INCHEON": {

        "name":
            "인천광역시",

        "bounds": (
            126.35,
            37.30,
            126.85,
            37.70,
        ),

        "step_x":
            0.06,

        "step_y":
            0.05,
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
# SAFE HELPERS
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


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


# ============================================================
# FEATURE COLLECTION
# ============================================================

def collect_features(
    payload: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(
        payload,
        dict,
    ):

        return []

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

        for item in (
            feature_collection
        ):

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

    # --------------------------------------------------------
    # GeoJSON direct response fallback
    # --------------------------------------------------------

    candidates.extend(
        safe_list(
            payload.get(
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
# GRID
# ============================================================

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
) -> Iterable[
    Tuple[
        float,
        float,
        float,
        float,
    ]
]:

    minx, miny, maxx, maxy = (
        bounds
    )

    y = miny

    while (
        y < maxy
    ):

        x = minx

        while (
            x < maxx
        ):

            cell_maxx = min(
                x + step_x,
                maxx,
            )

            cell_maxy = min(
                y + step_y,
                maxy,
            )

            yield (
                round(
                    x,
                    8,
                ),
                round(
                    y,
                    8,
                ),
                round(
                    cell_maxx,
                    8,
                ),
                round(
                    cell_maxy,
                    8,
                ),
            )

            x += step_x

        y += step_y


# ============================================================
# QUERY
# ============================================================

def query_dataset_bbox(
    *,
    dataset: str,
    bbox: Tuple[
        float,
        float,
        float,
        float,
    ],
    size: int = 100,
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
            dataset,

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
            size,

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

            "dataset":
                dataset,

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

            "feature_count":
                0,

            "features":
                [],
        }

    text = (
        response.text
        or ""
    )

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        return {

            "dataset":
                dataset,

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

            "content_type":
                response.headers.get(
                    "Content-Type"
                ),

            "response_length":
                len(
                    text
                ),

            "response_preview":
                text[
                    :500
                ],

            "feature_count":
                0,

            "features":
                [],
        }

    response_obj = safe_dict(
        payload.get(
            "response"
        )
    )

    status = safe_string(
        response_obj.get(
            "status"
        )
    )

    features = (
        collect_features(
            payload
        )
    )

    error = safe_dict(
        response_obj.get(
            "error"
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

    elif (
        response.status_code
        == 200
        and status
        in {
            "ERROR",
            "FAIL",
        }
    ):

        classification = (
            "QUERY_REJECTED"
        )

    else:

        classification = (
            "QUERY_FAILED"
        )

    return {

        "dataset":
            dataset,

        "http_status":
            response.status_code,

        "status":
            status,

        "classification":
            classification,

        "error":
            error,

        "content_type":
            response.headers.get(
                "Content-Type"
            ),

        "feature_count":
            len(
                features
            ),

        "features":
            features,
    }


# ============================================================
# PROPERTY NORMALIZATION
# ============================================================

def flatten_property_text(
    properties: Dict[str, Any],
) -> str:

    parts: List[str] = []

    for key, value in (
        properties.items()
    ):

        parts.append(
            safe_string(
                key
            )
        )

        parts.append(
            safe_string(
                value
            )
        )

    return (
        " ".join(
            parts
        )
        .upper()
    )


def feature_matches_target(
    feature: Dict[str, Any],
) -> bool:

    properties = safe_dict(
        feature.get(
            "properties"
        )
    )

    text = (
        flatten_property_text(
            properties
        )
    )

    if (
        TARGET_STANDARD_CODE
        in text
    ):

        return True

    if (
        TARGET_NAME.upper()
        in text
    ):

        return True

    return False


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

    representative_point: Dict[
        str,
        Any
    ] = {}

    geometry_valid = False

    geometry_type = safe_string(
        geometry.get(
            "type"
        )
    )

    try:

        geom = (
            shape(
                geometry
            )
        )

        if (
            not geom.is_empty
        ):

            geometry_valid = True

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

                "crs":
                    "EPSG:4326",
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
            geometry_type,

        "geometry_valid":
            geometry_valid,

        "polygon_geometry":
            (
                geometry_type
                in {
                    "Polygon",
                    "MultiPolygon",
                }
            ),

        "properties":
            properties,

        "representative_point":
            representative_point,
    }


# ============================================================
# DATASET PROBE
# ============================================================

def probe_dataset(
    dataset: str,
) -> Dict[str, Any]:

    # 서울 중심부 작은 bbox
    bbox = (
        126.95,
        37.50,
        127.05,
        37.60,
    )

    result = (
        query_dataset_bbox(
            dataset=dataset,
            bbox=bbox,
            size=10,
        )
    )

    return {

        "dataset":
            dataset,

        "http_status":
            result.get(
                "http_status"
            ),

        "status":
            result.get(
                "status"
            ),

        "classification":
            result.get(
                "classification"
            ),

        "feature_count":
            result.get(
                "feature_count"
            ),

        "error":
            result.get(
                "error"
            ),
    }


# ============================================================
# RUN - DATASET PROBE
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA SOURCE DISCOVERY"
)

print(
    "============================================================"
)

print()

print(
    "Target condition:",
    TARGET_NAME,
)

print(
    "Target standard code:",
    TARGET_STANDARD_CODE,
)

print(
    "Primary candidate dataset:",
    PRIMARY_DATASET,
)

print()


dataset_probe_results: Dict[
    str,
    Dict[str, Any],
] = {}


print(
    "------------------------------------------------------------"
)

print(
    "DATASET PROBES"
)

print(
    "------------------------------------------------------------"
)


for dataset in (
    DATASET_PROBES
):

    probe = (
        probe_dataset(
            dataset
        )
    )

    dataset_probe_results[
        dataset
    ] = (
        probe
    )

    print()

    print(
        dataset
    )

    print(
        "  HTTP:",
        probe.get(
            "http_status"
        ),
    )

    print(
        "  Status:",
        probe.get(
            "status"
        ),
    )

    print(
        "  Classification:",
        probe.get(
            "classification"
        ),
    )

    print(
        "  Feature count:",
        probe.get(
            "feature_count"
        ),
    )

    if (
        probe.get(
            "error"
        )
    ):

        print(
            "  Error:",
            probe.get(
                "error"
            ),
        )


# ============================================================
# PRIMARY DATASET DISCOVERY
# ============================================================

print()

print(
    "============================================================"
)

print(
    "PRIMARY DATASET FEATURE DISCOVERY"
)

print(
    "Dataset:",
    PRIMARY_DATASET,
)

print(
    "============================================================"
)


query_count = 0

successful_query_count = 0

empty_query_count = 0

failed_query_count = 0

raw_feature_count = 0


target_features: Dict[
    str,
    Dict[str, Any],
] = {}


sample_property_keys: set[str] = set()

sample_property_values: Dict[
    str,
    Any,
] = {}


# ============================================================
# SEARCH
# ============================================================

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
        region.get(
            "name"
        ),
    )

    print(
        "------------------------------------------------------------"
    )

    region_feature_count = 0

    region_target_count = 0

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
            query_dataset_bbox(
                dataset=(
                    PRIMARY_DATASET
                ),
                bbox=bbox,
                size=100,
            )
        )

        classification = (
            result.get(
                "classification"
            )
        )

        if (
            classification
            == "QUERY_SUCCESS"
        ):

            successful_query_count += 1

        elif (
            classification
            == "QUERY_EMPTY"
        ):

            empty_query_count += 1

        else:

            failed_query_count += 1

            print(
                "CELL",
                cell_index,
                bbox,
                "=>",
                classification,
                "/",
                result.get(
                    "status"
                ),
                "/",
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

        raw_feature_count += (
            len(
                features
            )
        )

        region_feature_count += (
            len(
                features
            )
        )

        for feature in (
            features
        ):

            properties = safe_dict(
                feature.get(
                    "properties"
                )
            )

            # ------------------------------------------------
            # 실제 property schema 학습
            # ------------------------------------------------

            for key, value in (
                properties.items()
            ):

                sample_property_keys.add(
                    safe_string(
                        key
                    )
                )

                if (
                    key
                    not in sample_property_values
                ):

                    sample_property_values[
                        safe_string(
                            key
                        )
                    ] = (
                        value
                    )

            # ------------------------------------------------
            # target detection
            # ------------------------------------------------

            if not (
                feature_matches_target(
                    feature
                )
            ):

                continue

            summary = (
                summarize_feature(
                    feature
                )
            )

            feature_id = safe_string(
                summary.get(
                    "feature_id"
                )
            )

            if not feature_id:

                feature_id = (
                    f"{region_key}-"
                    f"{cell_index}-"
                    f"{region_target_count + 1}"
                )

            if (
                feature_id
                not in target_features
            ):

                target_features[
                    feature_id
                ] = {

                    "region":
                        region_key,

                    "region_name":
                        region.get(
                            "name"
                        ),

                    "bbox":
                        bbox,

                    **summary,
                }

                region_target_count += 1

                print()

                print(
                    "TARGET FEATURE FOUND"
                )

                print(
                    "Feature ID:",
                    feature_id,
                )

                print(
                    "BBOX:",
                    bbox,
                )

                print(
                    "Geometry:",
                    summary.get(
                        "geometry_type"
                    ),
                )

                print(
                    "Polygon:",
                    summary.get(
                        "polygon_geometry"
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

                for key in sorted(
                    summary.get(
                        "properties",
                        {}
                    ).keys()
                ):

                    print(
                        f"  {key}:",
                        summary[
                            "properties"
                        ].get(
                            key
                        ),
                    )

        # ----------------------------------------------------
        # 한 지역에서 target 발견 시
        # source discovery 목적상 그 지역의 추가 탐색 중단
        # ----------------------------------------------------

        if (
            region_target_count
            > 0
        ):

            break

    print(
        "Region raw features:",
        region_feature_count,
    )

    print(
        "Region target features:",
        region_target_count,
    )


# ============================================================
# SOURCE STRUCTURE DIAGNOSTICS
# ============================================================

print()

print(
    "============================================================"
)

print(
    "SOURCE STRUCTURE DIAGNOSTICS"
)

print(
    "============================================================"
)

print(
    "Observed property keys:"
)

for key in sorted(
    sample_property_keys
):

    print(
        "-",
        key,
    )


print()

print(
    "First observed property values:"
)

for key in sorted(
    sample_property_values.keys()
):

    print(
        f"{key}:",
        sample_property_values.get(
            key
        ),
    )


# ============================================================
# FINAL
# ============================================================

primary_probe = (
    dataset_probe_results.get(
        PRIMARY_DATASET,
        {},
    )
)

primary_dataset_reachable = (
    primary_probe.get(
        "classification"
    )
    in {
        "QUERY_SUCCESS",
        "QUERY_EMPTY",
    }
)

target_found = (
    len(
        target_features
    )
    > 0
)

polygon_target_found = any(

    item.get(
        "polygon_geometry"
    )
    is True

    and item.get(
        "geometry_valid"
    )
    is True

    for item
    in target_features.values()
)


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
    "Primary dataset:",
    PRIMARY_DATASET,
)

print(
    "Primary dataset reachable:",
    primary_dataset_reachable,
)

print(
    "Total queries:",
    query_count,
)

print(
    "Successful queries:",
    successful_query_count,
)

print(
    "Empty queries:",
    empty_query_count,
)

print(
    "Failed queries:",
    failed_query_count,
)

print(
    "Raw feature count:",
    raw_feature_count,
)

print(
    "Target feature count:",
    len(
        target_features
    ),
)

print(
    "Polygon target found:",
    polygon_target_found,
)


for feature_id, item in (
    target_features.items()
):

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        feature_id
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        "Region:",
        item.get(
            "region_name"
        ),
    )

    print(
        "BBOX:",
        item.get(
            "bbox"
        ),
    )

    print(
        "Geometry:",
        item.get(
            "geometry_type"
        ),
    )

    print(
        "Representative point:",
        item.get(
            "representative_point"
        ),
    )

    print(
        "Properties:",
        item.get(
            "properties"
        ),
    )


# ============================================================
# RESOLUTION
# ============================================================

print()

print(
    "============================================================"
)

print(
    "RESOLUTION"
)

print(
    "============================================================"
)


if (
    polygon_target_found
):

    print(
        "DEVELOPMENT_DENSITY_MANAGEMENT_POLYGON_SOURCE_DISCOVERED"
    )

    print()

    print(
        "Next:"
    )

    print(
        "representative point"
    )

    print(
        "-> address / PNU"
    )

    print(
        "-> LP_PA_CBND_BUBUN Parcel"
    )

    print(
        "-> LT_C_UQ141 target feature intersection"
    )

    print(
        "-> positive parcel regression"
    )

elif (
    target_found
):

    print(
        "TARGET_ATTRIBUTE_FOUND_BUT_POLYGON_NOT_VERIFIED"
    )

    print()

    print(
        "Do not add runtime spatial condition yet."
    )

elif (
    primary_dataset_reachable
):

    print(
        "LT_C_UQ141_REACHABLE_BUT_UQQ700_NOT_DISCOVERED"
    )

    print()

    print(
        "Do not interpret this result as SITE FALSE."
    )

    print(
        "Expand search regions or inspect another official source."
    )

else:

    print(
        "LT_C_UQ141_SOURCE_NOT_VERIFIED"
    )

    print()

    print(
        "Do not register 개발밀도관리구역 in spatial evaluator."
    )


# ============================================================
# VALIDATION
# ============================================================
#
# discovery 테스트의 all_pass는
# "positive를 반드시 발견했는가"가 아니다.
#
# 중요한 것은:
#
# - API key 확보
# - candidate dataset probe 수행
# - discovery process 자체 정상 완료
# - 임의 runtime 등록을 하지 않음
#
# 이다.
# ============================================================

validations = {

    "API key loaded": (
        bool(
            API_KEY
        )
    ),

    "primary dataset probed": (
        PRIMARY_DATASET
        in dataset_probe_results
    ),

    "standard code UQQ700": (
        TARGET_STANDARD_CODE
        == "UQQ700"
    ),

    "target name": (
        TARGET_NAME
        == "개발밀도관리구역"
    ),

    "search executed": (
        query_count
        > 0
    ),

    "query accounting": (
        (
            successful_query_count
            + empty_query_count
            + failed_query_count
        )
        == query_count
    ),

    "target results are unique": (
        len(
            target_features
        )
        == len(
            set(
                target_features.keys()
            )
        )
    ),
}


all_pass = all(
    validations.values()
)


print()

print(
    "============================================================"
)

print(
    "VALIDATION"
)

print(
    "============================================================"
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

    raise AssertionError(
        "Development density management area source discovery failed"
    )