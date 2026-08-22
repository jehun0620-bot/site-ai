# -*- coding: utf-8 -*-

"""
C-14 Live Parcel Geometry Provider

목표
======================================================================
현재 SITE의:

- PNU
- longitude / latitude

를 사용하여 VWorld parcel dataset에서 실제 Polygon을 조회한다.

중요 원칙
======================================================================
1. Polygon / MultiPolygon만 허용
2. target PNU와 Feature property PNU가 직접 일치해야 함
3. 단순 조회 성공만으로 geometry를 채택하지 않음
4. PNU direct match가 없으면 geometry_loaded=False
"""

from __future__ import annotations

import json
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
# ENV
# ============================================================

load_dotenv(
    BASE_DIR
    / ".env"
)


# ============================================================
# CONFIG
# ============================================================

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)

PNU_PROPERTY_KEYS = [
    "pnu",
    "PNU",
    "pnu_cd",
    "PNU_CD",
    "pnu_code",
    "PNU_CODE",
    "parcel_pnu",
    "PARCEL_PNU",
]


# ============================================================
# util
# ============================================================

def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def load_vworld_key() -> str:

    candidates = [
        "VWORLD_API_KEY",
        "VWORLD_KEY",
        "DATA_API_KEY",
    ]

    for name in candidates:

        value = normalize_text(
            os.getenv(
                name
            )
        )

        if value:
            return value

    return ""

def resolve_address_coordinate(
    address: str,
    api_key: str,
) -> Dict[str, Any]:

    normalized_address = (
        normalize_text(
            address
        )
    )

    if not normalized_address:

        return {
            "resolved": False,
            "resolution": (
                "ADDRESS_MISSING"
            ),
            "x": None,
            "y": None,
        }

    url = (
        "https://api.vworld.kr/req/search"
    )

    params = {
        "service": (
            "search"
        ),

        "request": (
            "search"
        ),

        "version": (
            "2.0"
        ),

        "crs": (
            "EPSG:4326"
        ),

        "size": (
            10
        ),

        "page": (
            1
        ),

        "query": (
            normalized_address
        ),

        "type": (
            "address"
        ),

        "category": (
            "parcel"
        ),

        "format": (
            "json"
        ),

        "errorformat": (
            "json"
        ),

        "key": (
            api_key
        ),
    }

    (
        response,
        data,
        transport_error,
    ) = request_json(
        url,
        params,
    )

    if transport_error:

        return {
            "resolved": False,
            "resolution": (
                "ADDRESS_SEARCH_FAILED"
            ),
            "transport_error": (
                transport_error
            ),
            "x": None,
            "y": None,
        }

    http_status = (
        response.status_code
        if response is not None
        else None
    )

    response_data = (
        data.get(
            "response",
            {},
        )
        if isinstance(
            data,
            dict,
        )
        else {}
    )

    status = (
        normalize_text(
            response_data.get(
                "status"
            )
        ).upper()
    )

    if (
        http_status
        != 200
        or status
        != "OK"
    ):

        return {
            "resolved": False,
            "resolution": (
                "ADDRESS_SEARCH_NOT_OK"
            ),
            "http_status": (
                http_status
            ),
            "vworld_status": (
                status
            ),
            "x": None,
            "y": None,
        }

    result = (
        response_data.get(
            "result",
            {},
        )
    )

    items = (
        result.get(
            "items",
            [],
        )
        if isinstance(
            result,
            dict,
        )
        else []
    )

    if not items:

        return {
            "resolved": False,
            "resolution": (
                "ADDRESS_RESULT_EMPTY"
            ),
            "http_status": (
                http_status
            ),
            "vworld_status": (
                status
            ),
            "x": None,
            "y": None,
        }

    first = (
        items[0]
        if isinstance(
            items[0],
            dict,
        )
        else {}
    )

    point = (
        first.get(
            "point",
            {},
        )
        if isinstance(
            first,
            dict,
        )
        else {}
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

        return {
            "resolved": False,
            "resolution": (
                "ADDRESS_POINT_INVALID"
            ),
            "http_status": (
                http_status
            ),
            "vworld_status": (
                status
            ),
            "x": None,
            "y": None,
        }

    return {
        "resolved": True,
        "resolution": (
            "ADDRESS_POINT_RESOLVED"
        ),
        "http_status": (
            http_status
        ),
        "vworld_status": (
            status
        ),
        "address": (
            normalized_address
        ),
        "x": (
            x
        ),
        "y": (
            y
        ),
        "crs": (
            "EPSG:4326"
        ),
    }

def normalize_pnu_candidate(
    value: Any,
) -> str:

    text = normalize_text(
        value
    )

    if not text:
        return ""

    digits = "".join(
        char
        for char
        in text
        if char.isdigit()
    )

    if len(
        digits
    ) == 19:

        return digits

    return ""


# ============================================================
# HTTP
# ============================================================

def request_json(
    url: str,
    params: Dict[str, Any],
) -> Tuple[
    Optional[requests.Response],
    Dict[str, Any],
    Optional[str],
]:

    try:

        response = requests.get(
            url,
            params=params,
            timeout=30,
        )

    except requests.RequestException as exc:

        return (
            None,
            {},
            repr(
                exc
            ),
        )

    try:

        data = response.json()

    except (
        requests.exceptions.JSONDecodeError,
        json.JSONDecodeError,
    ):

        return (
            response,
            {},
            "JSON_DECODE_ERROR",
        )

    if not isinstance(
        data,
        dict,
    ):

        return (
            response,
            {},
            "INVALID_JSON_ROOT",
        )

    return (
        response,
        data,
        None,
    )


# ============================================================
# VWorld response
# ============================================================

def get_vworld_response(
    data: Dict[str, Any],
) -> Dict[str, Any]:

    response = data.get(
        "response"
    )

    if isinstance(
        response,
        dict,
    ):

        return response

    return {}


def get_vworld_status(
    data: Dict[str, Any],
) -> str:

    response = get_vworld_response(
        data
    )

    status = response.get(
        "status"
    )

    return normalize_text(
        status
    ).upper()


def get_vworld_error(
    data: Dict[str, Any],
) -> Dict[str, Any]:

    response = get_vworld_response(
        data
    )

    error = response.get(
        "error"
    )

    if isinstance(
        error,
        dict,
    ):

        return error

    return {}


# ============================================================
# FeatureCollection
# ============================================================

def collect_features(
    data: Any,
) -> List[
    Dict[str, Any]
]:

    collected: List[
        Dict[str, Any]
    ] = []

    def walk(
        value: Any,
    ) -> None:

        if isinstance(
            value,
            dict,
        ):

            if (
                value.get(
                    "type"
                )
                == "FeatureCollection"
            ):

                features = value.get(
                    "features",
                    [],
                )

                if isinstance(
                    features,
                    list,
                ):

                    for feature in features:

                        if isinstance(
                            feature,
                            dict,
                        ):

                            collected.append(
                                feature
                            )

            feature_collection = (
                value.get(
                    "featureCollection"
                )
            )

            if isinstance(
                feature_collection,
                dict,
            ):

                features = (
                    feature_collection.get(
                        "features",
                        [],
                    )
                )

                if isinstance(
                    features,
                    list,
                ):

                    for feature in features:

                        if isinstance(
                            feature,
                            dict,
                        ):

                            collected.append(
                                feature
                            )

            for child in (
                value.values()
            ):

                walk(
                    child
                )

        elif isinstance(
            value,
            list,
        ):

            for child in value:

                walk(
                    child
                )

    walk(
        data
    )

    # 중복 제거
    unique = []

    seen = set()

    for feature in collected:

        marker = (
            normalize_text(
                feature.get(
                    "id"
                )
            ),
            json.dumps(
                feature.get(
                    "geometry"
                ),
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

        if marker in seen:
            continue

        seen.add(
            marker
        )

        unique.append(
            feature
        )

    return unique


# ============================================================
# Geometry
# ============================================================

def geometry_type(
    feature: Dict[str, Any],
) -> str:

    geometry = (
        feature.get(
            "geometry"
        )
    )

    if not isinstance(
        geometry,
        dict,
    ):

        return ""

    return normalize_text(
        geometry.get(
            "type"
        )
    )


def is_polygon_geometry(
    feature: Dict[str, Any],
) -> bool:

    return (
        geometry_type(
            feature
        )
        in {
            "Polygon",
            "MultiPolygon",
        }
    )


# ============================================================
# PNU
# ============================================================

def find_feature_pnu(
    feature: Dict[str, Any],
) -> Tuple[
    Optional[str],
    str,
]:

    properties = (
        feature.get(
            "properties"
        )
    )

    if not isinstance(
        properties,
        dict,
    ):

        return (
            None,
            "",
        )

    # --------------------------------------------------------
    # 알려진 PNU property
    # --------------------------------------------------------

    for key in PNU_PROPERTY_KEYS:

        if key not in properties:
            continue

        value = (
            normalize_pnu_candidate(
                properties.get(
                    key
                )
            )
        )

        if value:

            return (
                key,
                value,
            )

    # --------------------------------------------------------
    # property 이름에 pnu 포함
    # --------------------------------------------------------

    for key, raw_value in (
        properties.items()
    ):

        if (
            "pnu"
            not in str(
                key
            ).lower()
        ):

            continue

        value = (
            normalize_pnu_candidate(
                raw_value
            )
        )

        if value:

            return (
                str(
                    key
                ),
                value,
            )

    # --------------------------------------------------------
    # 마지막 fallback:
    # 19자리 숫자 property 탐색
    # --------------------------------------------------------

    for key, raw_value in (
        properties.items()
    ):

        value = (
            normalize_pnu_candidate(
                raw_value
            )
        )

        if value:

            return (
                str(
                    key
                ),
                value,
            )

    return (
        None,
        "",
    )


# ============================================================
# query
# ============================================================

def query_dataset_by_point(
    api_key: str,
    dataset: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {

        "service": (
            "data"
        ),

        "request": (
            "GetFeature"
        ),

        "data": (
            dataset
        ),

        "key": (
            api_key
        ),

        "format": (
            "json"
        ),

        "geometry": (
            "true"
        ),

        "attribute": (
            "true"
        ),

        "crs": (
            "EPSG:4326"
        ),

        "geomFilter": (
            f"POINT({x} {y})"
        ),

        "size": (
            100
        ),

        "page": (
            1
        ),
    }

    (
        response,
        data,
        transport_error,
    ) = request_json(
        VWORLD_DATA_URL,
        params,
    )

    http_status = (
        response.status_code
        if response is not None
        else None
    )

    status = (
        get_vworld_status(
            data
        )
    )

    vworld_error = (
        get_vworld_error(
            data
        )
    )

    features = (
        collect_features(
            data
        )
    )

    polygon_features = [
        feature
        for feature
        in features
        if is_polygon_geometry(
            feature
        )
    ]

    if transport_error:

        classification = (
            "QUERY_FAILED"
        )

    elif (
        http_status
        != 200
    ):

        classification = (
            "HTTP_ERROR"
        )

    elif (
        status
        == "ERROR"
        and vworld_error.get(
            "code"
        )
        == "INVALID_RANGE"
    ):

        classification = (
            "INVALID_DATA_IDENTIFIER"
        )

    elif (
        status
        != "OK"
    ):

        classification = (
            "QUERY_FAILED"
        )

    else:

        classification = (
            "QUERY_SUCCESS"
        )

    return {

        "dataset": (
            dataset
        ),

        "http_status": (
            http_status
        ),

        "content_type": (
            response.headers.get(
                "Content-Type",
                "",
            )
            if response is not None
            else ""
        ),

        "vworld_status": (
            status
        ),

        "classification": (
            classification
        ),

        "transport_error": (
            transport_error
        ),

        "error": (
            vworld_error
        ),

        "feature_count": (
            len(
                features
            )
        ),

        "polygon_feature_count": (
            len(
                polygon_features
            )
        ),

        "features": (
            features
        ),
    }


# ============================================================
# analysis
# ============================================================

def analyze_features(
    features: List[
        Dict[str, Any]
    ],
    target_pnu: str,
) -> Dict[str, Any]:

    analyzed = []

    pnu_matches = []

    polygon_count = 0

    for index, feature in enumerate(
        features,
        start=1,
    ):

        geom_type = (
            geometry_type(
                feature
            )
        )

        polygon = (
            geom_type
            in {
                "Polygon",
                "MultiPolygon",
            }
        )

        if polygon:

            polygon_count += 1

        (
            pnu_key,
            feature_pnu,
        ) = (
            find_feature_pnu(
                feature
            )
        )

        pnu_match = (
            bool(
                target_pnu
            )
            and bool(
                feature_pnu
            )
            and feature_pnu
            == target_pnu
        )

        info = {

            "index": (
                index
            ),

            "id": (
                normalize_text(
                    feature.get(
                        "id"
                    )
                )
            ),

            "geometry_type": (
                geom_type
            ),

            "is_polygon": (
                polygon
            ),

            "pnu_property_key": (
                pnu_key
            ),

            "feature_pnu": (
                feature_pnu
            ),

            "target_pnu": (
                target_pnu
            ),

            "pnu_match": (
                pnu_match
            ),

            "properties": (
                feature.get(
                    "properties"
                )
                if isinstance(
                    feature.get(
                        "properties"
                    ),
                    dict,
                )
                else {}
            ),

            "geometry": (
                feature.get(
                    "geometry"
                )
            ),
        }

        analyzed.append(
            info
        )

        if (
            polygon
            and pnu_match
        ):

            pnu_matches.append(
                info
            )

    return {

        "feature_count": (
            len(
                features
            )
        ),

        "polygon_count": (
            polygon_count
        ),

        "pnu_polygon_match_count": (
            len(
                pnu_matches
            )
        ),

        "features": (
            analyzed
        ),

        "pnu_polygon_matches": (
            pnu_matches
        ),
    }


# ============================================================
# public provider
# ============================================================

def resolve_live_parcel_geometry(
    pnu: str,
    x: Optional[float] = None,
    y: Optional[float] = None,
    address: str = "",
) -> Dict[str, Any]:

    target_pnu = (
        normalize_pnu_candidate(
            pnu
        )
    )

    if not target_pnu:

        return {

            "geometry_loaded": (
                False
            ),

            "resolution": (
                "INVALID_PNU"
            ),

            "pnu": (
                pnu
            ),
        }

    api_key = (
        load_vworld_key()
    )
    coordinate_source = (
        "CALLER"
    )

    resolved_x = (
        x
    )

    resolved_y = (
        y
    )

    if (
        resolved_x is None
        or resolved_y is None
    ):

        coordinate = (
            resolve_address_coordinate(
                address=(
                    address
                ),
                api_key=(
                    api_key
                ),
            )
        )

        if not coordinate.get(
            "resolved"
        ):

            return {
                "geometry_loaded": (
                    False
                ),

                "resolution": (
                    "COORDINATE_UNRESOLVED"
                ),

                "pnu": (
                    target_pnu
                ),

                "coordinate": (
                    coordinate
                ),
            }

        resolved_x = (
            coordinate.get(
                "x"
            )
        )

        resolved_y = (
            coordinate.get(
                "y"
            )
        )

        coordinate_source = (
            "VWORLD_ADDRESS_SEARCH"
        )

    if not api_key:

        return {

            "geometry_loaded": (
                False
            ),

            "resolution": (
                "VWORLD_KEY_MISSING"
            ),

            "pnu": (
                target_pnu
            ),
        }

    query = (
        query_dataset_by_point(
            api_key=(
                api_key
            ),

            dataset=(
                PARCEL_DATASET
            ),

            x=float(
    resolved_x
),

y=float(
    resolved_y
),
        )
    )

    analysis = (
        analyze_features(
            features=(
                query.get(
                    "features",
                    [],
                )
            ),

            target_pnu=(
                target_pnu
            ),
        )
    )

    matches = (
        analysis.get(
            "pnu_polygon_matches",
            [],
        )
    )

    if not matches:

        return {

            "geometry_loaded": (
                False
            ),

            "resolution": (
                "PNU_POLYGON_NOT_FOUND"
            ),

            "pnu": (
                target_pnu
            ),

            "dataset": (
                PARCEL_DATASET
            ),

            "query": {

                "http_status": (
                    query.get(
                        "http_status"
                    )
                ),

                "vworld_status": (
                    query.get(
                        "vworld_status"
                    )
                ),

                "classification": (
                    query.get(
                        "classification"
                    )
                ),

                "feature_count": (
                    query.get(
                        "feature_count"
                    )
                ),

                "polygon_feature_count": (
                    query.get(
                        "polygon_feature_count"
                    )
                ),

                "error": (
                    query.get(
                        "error"
                    )
                ),
            },

            "analysis": {

                "pnu_polygon_match_count": (
                    analysis.get(
                        "pnu_polygon_match_count"
                    )
                ),
            },
        }

    selected = (
        matches[
            0
        ]
    )

    geometry = (
        selected.get(
            "geometry"
        )
    )

    return {

        "geometry_loaded": (
            True
        ),

        "resolution": (
            "PNU_POLYGON_VERIFIED"
        ),

        "pnu": (
            target_pnu
        ),

        "dataset": (
            PARCEL_DATASET
        ),

        "geometry_type": (
            selected.get(
                "geometry_type"
            )
        ),

        "geometry": (
            geometry
        ),

        "feature_id": (
            selected.get(
                "id"
            )
        ),

        "pnu_property_key": (
            selected.get(
                "pnu_property_key"
            )
        ),

        "feature_pnu": (
            selected.get(
                "feature_pnu"
            )
        ),

        "strict_pnu_verified": (
            True
        ),

        "source": {

            "provider": (
                "VWorld"
            ),

            "dataset": (
                PARCEL_DATASET
            ),

            "query_mode": (
                "POINT"
            ),

            "crs": (
                "EPSG:4326"
            ),

            "coordinate_source": (
                 coordinate_source
            ),
        },

        "coordinate": {
            "x": (
                resolved_x
            ),

            "y": (
                resolved_y
            ),

            "crs": (
                "EPSG:4326"
            ),

            "source": (
                coordinate_source
            ),
        },
        
        "query": {

            "http_status": (
                query.get(
                    "http_status"
                )
            ),

            "vworld_status": (
                query.get(
                    "vworld_status"
                )
            ),

            "classification": (
                query.get(
                    "classification"
                )
            ),

            "feature_count": (
                query.get(
                    "feature_count"
                )
            ),

            "polygon_feature_count": (
                query.get(
                    "polygon_feature_count"
                )
            ),
        },
    }