# -*- coding: utf-8 -*-

"""
STEP 17-21-C-15-1
Runtime Spatial Condition Evaluator

목표
======================================================================
현재 분석 SITE의 Parcel Polygon을 이용하여 SITE 공간조건을
runtime에서 독립적으로 판정한다.

첫 번째 지원 condition:

    지구단위계획

핵심 원칙
======================================================================
1. 대표 SITE의 기존 C-9 snapshot 결과를 다른 SITE에 재사용하지 않는다.
2. 현재 SITE의 Parcel geometry를 사용한다.
3. Parcel과 조회 layer의 CRS가 확인되어야 geometry intersection을 수행한다.
4. 조회 실패는 FALSE가 아니라 UNKNOWN이다.
5. 정상조회 + 유효 geometry + 교차 없음만 FALSE로 판정한다.
6. 실제 geometry intersection이 확인된 경우 TRUE로 판정한다.
7. EPSG:4326 geometry의 degree² 면적을 법정 면적 또는 면적비로 사용하지 않는다.
"""

from __future__ import annotations

import copy
import os

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from dotenv import load_dotenv

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry

try:

    from .parcel_geometry_provider import (
        resolve_live_parcel_geometry,
    )

except ImportError:

    from parcel_geometry_provider import (
        resolve_live_parcel_geometry,
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
# VWorld
# ============================================================

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

DISTRICT_UNIT_PLAN_DATASET = (
    "LT_C_UPISUQ161"
)

REQUEST_TIMEOUT = 30


# ============================================================
# util
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


def load_vworld_api_key() -> str:

    load_dotenv(
        BASE_DIR
        / ".env"
    )

    return (
        os.getenv(
            "VWORLD_API_KEY"
        )
        or os.getenv(
            "VWORLD_KEY"
        )
        or ""
    ).strip()


# ============================================================
# FeatureCollection
# ============================================================

def collect_features(
    payload: Any,
) -> List[Dict[str, Any]]:

    """
    VWorld Data API 응답에서 Feature 목록을 추출한다.

    여러 response wrapper 구조를 방어적으로 처리한다.
    """

    if not isinstance(
        payload,
        dict,
    ):
        return []

    candidates: List[Any] = []

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

    feature_collection = result.get(
        "featureCollection"
    )

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

    # --------------------------------------------------------
    # 혹시 일반 GeoJSON 형태가 직접 반환되는 경우
    # --------------------------------------------------------

    candidates.extend(
        safe_list(
            payload.get(
                "features"
            )
        )
    )

    features: List[Dict[str, Any]] = []

    for feature in candidates:

        if isinstance(
            feature,
            dict,
        ):
            features.append(
                feature
            )

    return features


# ============================================================
# VWorld response status
# ============================================================

def get_vworld_status(
    payload: Any,
) -> Optional[str]:

    if not isinstance(
        payload,
        dict,
    ):
        return None

    return (
        safe_dict(
            payload.get(
                "response"
            )
        ).get(
            "status"
        )
    )


def get_vworld_error(
    payload: Any,
) -> Dict[str, Any]:

    if not isinstance(
        payload,
        dict,
    ):
        return {}

    response = safe_dict(
        payload.get(
            "response"
        )
    )

    return safe_dict(
        response.get(
            "error"
        )
    )


# ============================================================
# Geometry
# ============================================================

def geometry_to_shape(
    geometry: Any,
) -> Optional[BaseGeometry]:

    if not isinstance(
        geometry,
        dict,
    ):
        return None

    if not geometry.get(
        "type"
    ):
        return None

    if not geometry.get(
        "coordinates"
    ):
        return None

    try:

        result = shape(
            geometry
        )

    except Exception:

        return None

    if result.is_empty:

        return None

    return result


def parcel_to_shape(
    parcel: Dict[str, Any],
) -> Optional[BaseGeometry]:

    return geometry_to_shape(
        parcel.get(
            "geometry"
        )
    )


# ============================================================
# representative point
# ============================================================

def resolve_query_point(
    site: Dict[str, Any],
    parcel: Dict[str, Any],
) -> Tuple[
    Optional[float],
    Optional[float],
    Optional[str],
]:

    """
    Query POINT는 현재 SITE representative coordinate를 우선한다.

    없으면 live Parcel source가 보유한 coordinate를 사용한다.
    """

    coordinate = safe_dict(
        site.get(
            "coordinate"
        )
    )

    x = coordinate.get(
        "x"
    )

    y = coordinate.get(
        "y"
    )

    crs = safe_string(
        coordinate.get(
            "crs"
        )
    )

    if (
        isinstance(
            x,
            (
                int,
                float,
            ),
        )
        and isinstance(
            y,
            (
                int,
                float,
            ),
        )
    ):

        return (
            float(
                x
            ),
            float(
                y
            ),
            crs
            or None,
        )

    # --------------------------------------------------------
    # parcel live source coordinate fallback
    # --------------------------------------------------------

    source = safe_dict(
        parcel.get(
            "source"
        )
    )

    live = safe_dict(
        source.get(
            "live"
        )
    )

    live_coordinate = safe_dict(
        live.get(
            "coordinate"
        )
    )

    x = live_coordinate.get(
        "x"
    )

    y = live_coordinate.get(
        "y"
    )

    crs = safe_string(
        live_coordinate.get(
            "crs"
        )
    )

    if (
        isinstance(
            x,
            (
                int,
                float,
            ),
        )
        and isinstance(
            y,
            (
                int,
                float,
            ),
        )
    ):

        return (
            float(
                x
            ),
            float(
                y
            ),
            crs
            or None,
        )

    return (
        None,
        None,
        None,
    )

def resolve_evaluation_parcel(
    *,
    site: Dict[str, Any],
    parcel: Dict[str, Any],
) -> Dict[str, Any]:

    """
    Spatial condition intersection에 사용할 compatible Parcel geometry를
    결정한다.

    우선순위
    ==================================================================
    1. 현재 parcel이 EPSG:4326이면 그대로 사용
    2. CRS 미확정/비호환이면 동일 PNU를 VWorld live provider로 재조회
    3. live PNU 직접 검증이 성공한 경우에만 fallback geometry 사용

    중요
    ==================================================================
    이 함수는 primary parcel source를 바꾸지 않는다.

    즉 BASE SITE의 공식 analysis parcel은 계속 MapPlan일 수 있으며,
    여기서 확보한 VWorld geometry는 spatial condition evaluation에만
    사용한다.
    """

    pnu = safe_string(
        site.get(
            "pnu"
        )
        or parcel.get(
            "pnu"
        )
    )

    address = safe_string(
        site.get(
            "address"
        )
    )

    parcel_loaded = (
        parcel.get(
            "geometry_loaded"
        )
        is True
    )

    parcel_crs = safe_string(
        parcel.get(
            "crs"
        )
    )

    parcel_geometry = (
        parcel_to_shape(
            parcel
        )
    )

    # ========================================================
    # primary parcel directly usable
    # ========================================================

    if (
        parcel_loaded
        and parcel_geometry is not None
        and parcel_crs == "EPSG:4326"
    ):

        return {
            "resolved": True,

            "geometry": (
                parcel_geometry
            ),

            "geometry_geojson": copy.deepcopy(
                parcel.get(
                    "geometry"
                )
            ),

            "crs": (
                "EPSG:4326"
            ),

            "source": {
                "mode":
                    "PRIMARY_PARCEL",

                "provider":
                    safe_dict(
                        parcel.get(
                            "source"
                        )
                    ).get(
                        "provider"
                    ),

                "pnu":
                    pnu,
            },

            "fallback_used":
                False,
        }

    # ========================================================
    # compatible live fallback
    # ========================================================

    live_result = (
        resolve_live_parcel_geometry(
            pnu=pnu,
            address=address,
        )
    )

    live_loaded = (
        live_result.get(
            "geometry_loaded"
        )
        is True
    )

    strict_pnu_verified = (
        live_result.get(
            "strict_pnu_verified"
        )
        is True
    )

    live_geometry_geojson = (
        live_result.get(
            "geometry"
        )
    )

    live_geometry = (
        geometry_to_shape(
            live_geometry_geojson
        )
    )

    live_source = safe_dict(
        live_result.get(
            "source"
        )
    )

    live_crs = safe_string(
        live_source.get(
            "crs"
        )
    )

    if (
        live_loaded
        and strict_pnu_verified
        and live_geometry is not None
        and live_crs == "EPSG:4326"
    ):

        return {
            "resolved": True,

            "geometry": (
                live_geometry
            ),

            "geometry_geojson":
                copy.deepcopy(
                    live_geometry_geojson
                ),

            "crs":
                "EPSG:4326",

            "source": {
                "mode":
                    "LIVE_COMPATIBLE_FALLBACK",

                "provider":
                    live_source.get(
                        "provider"
                    )
                    or "VWorld",

                "dataset":
                    live_source.get(
                        "dataset"
                    ),

                "pnu":
                    pnu,

                "resolution":
                    live_result.get(
                        "resolution"
                    ),

                "feature_pnu":
                    live_result.get(
                        "feature_pnu"
                    ),
            },

            "fallback_used":
                True,

            "live_result": {
                "resolution":
                    live_result.get(
                        "resolution"
                    ),

                "feature_pnu":
                    live_result.get(
                        "feature_pnu"
                    ),

                "strict_pnu_verified":
                    strict_pnu_verified,

                "query":
                    copy.deepcopy(
                        live_result.get(
                            "query"
                        )
                    ),
            },
        }

    # ========================================================
    # unresolved
    # ========================================================

    return {
        "resolved": False,

        "geometry": None,

        "geometry_geojson": None,

        "crs": None,

        "source": {
            "mode":
                "UNRESOLVED",

            "primary_parcel_crs":
                parcel_crs
                or None,

            "pnu":
                pnu,
        },

        "fallback_used":
            True,

        "live_result": {
            "resolution":
                live_result.get(
                    "resolution"
                ),

            "feature_pnu":
                live_result.get(
                    "feature_pnu"
                ),

            "strict_pnu_verified":
                strict_pnu_verified,

            "query":
                copy.deepcopy(
                    live_result.get(
                        "query"
                    )
                ),
        },
    }
# ============================================================
# district-unit-plan query
# ============================================================

def query_district_unit_plan(
    *,
    api_key: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {

        "service":
            "data",

        "request":
            "GetFeature",

        "data":
            DISTRICT_UNIT_PLAN_DATASET,

        "key":
            api_key,

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

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except requests.RequestException as exc:

        return {
            "http_status": None,
            "vworld_status": None,
            "classification": (
                "TRANSPORT_ERROR"
            ),
            "transport_error": repr(
                exc
            ),
            "feature_count": 0,
            "geometry_feature_count": 0,
            "features": [],
            "request": {
                "dataset": (
                    DISTRICT_UNIT_PLAN_DATASET
                ),
                "x": x,
                "y": y,
                "crs": "EPSG:4326",
            },
        }

    try:

        payload = response.json()

    except Exception:

        return {
            "http_status": (
                response.status_code
            ),
            "vworld_status": None,
            "classification": (
                "JSON_PARSE_ERROR"
            ),
            "transport_error": None,
            "feature_count": 0,
            "geometry_feature_count": 0,
            "features": [],
            "request": {
                "dataset": (
                    DISTRICT_UNIT_PLAN_DATASET
                ),
                "x": x,
                "y": y,
                "crs": "EPSG:4326",
            },
        }

    status = get_vworld_status(
        payload
    )

    features = collect_features(
        payload
    )

    geometry_features: List[
        Dict[str, Any]
    ] = []

    for feature in features:

        geometry = feature.get(
            "geometry"
        )

        geometry_shape = (
            geometry_to_shape(
                geometry
            )
        )

        if geometry_shape is None:
            continue

        geometry_features.append(
            {
                "feature": copy.deepcopy(
                    feature
                ),
                "geometry": geometry_shape,
            }
        )

    if response.status_code != 200:

        classification = (
            "HTTP_ERROR"
        )

    elif status != "OK":

        classification = (
            "QUERY_FAILED"
        )

    else:

        classification = (
            "QUERY_SUCCESS"
        )

    return {
        "http_status": (
            response.status_code
        ),
        "vworld_status": (
            status
        ),
        "classification": (
            classification
        ),
        "transport_error": None,
        "error": get_vworld_error(
            payload
        ),
        "feature_count": len(
            features
        ),
        "geometry_feature_count": len(
            geometry_features
        ),
        "features": (
            geometry_features
        ),
        "request": {
            "dataset": (
                DISTRICT_UNIT_PLAN_DATASET
            ),
            "x": x,
            "y": y,
            "crs": "EPSG:4326",
        },
    }


# ============================================================
# geometry intersection
# ============================================================

def compute_intersections(
    parcel_geometry: BaseGeometry,
    district_items: List[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    """
    EPSG:4326 geometry intersection 여부만 판정한다.

    degree² 기반 area/ratio는 공식 판정값으로 사용하지 않는다.
    """

    results: List[
        Dict[str, Any]
    ] = []

    for index, item in enumerate(
        district_items,
        start=1,
    ):

        feature = safe_dict(
            item.get(
                "feature"
            )
        )

        district_geometry = item.get(
            "geometry"
        )

        if district_geometry is None:
            continue

        try:

            intersects = (
                parcel_geometry.intersects(
                    district_geometry
                )
            )

        except Exception as exc:

            results.append(
                {
                    "index": index,
                    "feature_id": (
                        feature.get(
                            "id"
                        )
                    ),
                    "intersects": None,
                    "geometry_error": repr(
                        exc
                    ),
                }
            )

            continue

        properties = safe_dict(
            feature.get(
                "properties"
            )
        )

        results.append(
            {
                "index": index,

                "feature_id": (
                    feature.get(
                        "id"
                    )
                ),

                "district_name": (
                    properties.get(
                        "dgm_nm"
                    )
                    or properties.get(
                        "DGM_NM"
                    )
                    or ""
                ),

                "geometry_type": (
                    district_geometry.geom_type
                ),

                "intersects": bool(
                    intersects
                ),
            }
        )

    return results


# ============================================================
# condition resolution
# ============================================================

def resolve_district_unit_plan_condition(
    *,
    site: Dict[str, Any],
    parcel: Dict[str, Any],
) -> Dict[str, Any]:

    """
    현재 SITE의 지구단위계획 공간조건을 runtime에서 판정한다.
    """

    pnu = safe_string(
        site.get(
            "pnu"
        )
        or parcel.get(
            "pnu"
        )
    )

    result_base: Dict[
        str,
        Any
    ] = {

        "name":
            "지구단위계획",

        "type":
            "SITE",

        "pnu":
            pnu,

        "source": {
            "provider":
                "VWorld",

            "dataset":
                DISTRICT_UNIT_PLAN_DATASET,

            "crs":
                "EPSG:4326",
        },
    }

    # ========================================================
    # parcel validation
    # ========================================================

        # ========================================================
    # evaluation-compatible Parcel
    # ========================================================

    evaluation_parcel = (
        resolve_evaluation_parcel(
            site=site,
            parcel=parcel,
        )
    )

    if (
        evaluation_parcel.get(
            "resolved"
        )
        is not True
    ):

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "LOW",

            "resolution":
                "COMPATIBLE_PARCEL_GEOMETRY_UNAVAILABLE",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    False,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {
                "primary_parcel": {
                    "pnu":
                        parcel.get(
                            "pnu"
                        ),

                    "provider":
                        safe_dict(
                            parcel.get(
                                "source"
                            )
                        ).get(
                            "provider"
                        ),

                    "geometry_loaded":
                        parcel.get(
                            "geometry_loaded"
                        ),

                    "crs":
                        parcel.get(
                            "crs"
                        ),
                },

                "evaluation_parcel":
                    copy.deepcopy(
                        {
                            key: value
                            for key, value
                            in evaluation_parcel.items()
                            if key not in {
                                "geometry",
                                "geometry_geojson",
                            }
                        }
                    ),
            },
        }

    parcel_geometry = (
        evaluation_parcel.get(
            "geometry"
        )
    )

    parcel_crs = (
        evaluation_parcel.get(
            "crs"
        )
    )

    # ========================================================
    # query point
    # ========================================================

    x, y, coordinate_crs = (
        resolve_query_point(
            site=site,
            parcel=parcel,
        )
    )

    if (
        x is None
        or y is None
    ):

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "LOW",

            "resolution":
                "REPRESENTATIVE_COORDINATE_UNAVAILABLE",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    False,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {
                "parcel_loaded":
                    True,

                "parcel_crs":
                    parcel_crs,

                "coordinate_crs":
                    coordinate_crs,
            },
        }

    if (
        coordinate_crs
        and coordinate_crs
        != "EPSG:4326"
    ):

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "LOW",

            "resolution":
                "COORDINATE_CRS_NOT_COMPATIBLE",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    False,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {
                "coordinate": {
                    "x": x,
                    "y": y,
                    "crs": (
                        coordinate_crs
                    ),
                },
            },
        }

    # ========================================================
    # VWorld query
    # ========================================================

    api_key = load_vworld_api_key()

    if not api_key:

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "LOW",

            "resolution":
                "VWORLD_API_KEY_MISSING",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    False,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {},
        }

    query_result = (
        query_district_unit_plan(
            api_key=api_key,
            x=x,
            y=y,
        )
    )

    query_success = (
        query_result.get(
            "classification"
        )
        == "QUERY_SUCCESS"
        and query_result.get(
            "http_status"
        )
        == 200
        and query_result.get(
            "vworld_status"
        )
        == "OK"
    )

    if not query_success:

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "MEDIUM",

            "resolution":
                "DISTRICT_UNIT_PLAN_QUERY_FAILED",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    False,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {
                "coordinate": {
                    "x": x,
                    "y": y,
                    "crs": "EPSG:4326",
                },

                "query": {
                    key: value
                    for key, value
                    in query_result.items()
                    if key != "features"
                },
            },
        }

    district_items = (
        query_result.get(
            "features",
            []
        )
    )

    # ========================================================
    # successful query with no matching features
    # ========================================================

    if not district_items:

        return {
            **result_base,

            "state":
                "FALSE",

            "confidence":
                "HIGH",

            "resolution":
                "QUERY_SUCCESS_NO_DISTRICT_FEATURE",

            "geometry_verified":
                True,

            "evaluation": {
                "query_success":
                    True,

                "intersects":
                    False,

                "intersection_count":
                    0,
            },

            "evidence": {
                "coordinate": {
                    "x": x,
                    "y": y,
                    "crs": "EPSG:4326",
                },

                "query": {
                    key: value
                    for key, value
                    in query_result.items()
                    if key != "features"
                },
            },
        }

    # ========================================================
    # intersection
    # ========================================================

    intersections = compute_intersections(
        parcel_geometry=parcel_geometry,
        district_items=district_items,
    )

    positive = [
        item
        for item in intersections
        if item.get(
            "intersects"
        )
        is True
    ]

    geometry_errors = [
        item
        for item in intersections
        if item.get(
            "intersects"
        )
        is None
    ]

    # --------------------------------------------------------
    # TRUE
    # --------------------------------------------------------

    if positive:

        return {
            **result_base,

            "state":
                "TRUE",

            "confidence":
                "HIGH",

            "resolution":
                "PARCEL_INTERSECTS_DISTRICT_UNIT_PLAN",

            "geometry_verified":
                True,

            "evaluation": {
                "query_success":
                    True,

                "intersects":
                    True,

                "intersection_count":
                    len(
                        positive
                    ),
            },

            "evidence": {
                "coordinate": {
                    "x": x,
                    "y": y,
                    "crs": "EPSG:4326",
                    "evaluation_parcel": {
    key: value
    for key, value
    in evaluation_parcel.items()
    if key not in {
        "geometry",
        "geometry_geojson",
    }
},
                
                },

                "query": {
                    key: value
                    for key, value
                    in query_result.items()
                    if key != "features"
                },

                "intersections":
                    copy.deepcopy(
                        intersections
                    ),
            },
        }

    # --------------------------------------------------------
    # geometry evaluation error
    # --------------------------------------------------------

    if geometry_errors:

        return {
            **result_base,

            "state":
                "UNKNOWN",

            "confidence":
                "MEDIUM",

            "resolution":
                "GEOMETRY_INTERSECTION_ERROR",

            "geometry_verified":
                False,

            "evaluation": {
                "query_success":
                    True,

                "intersects":
                    None,

                "intersection_count":
                    None,
            },

            "evidence": {
                "intersections":
                    copy.deepcopy(
                        intersections
                    ),
                    "evaluation_parcel": {
    key: value
    for key, value
    in evaluation_parcel.items()
    if key not in {
        "geometry",
        "geometry_geojson",
    }
},
            },
        }

    # --------------------------------------------------------
    # FALSE
    # --------------------------------------------------------

    return {
        **result_base,

        "state":
            "FALSE",

        "confidence":
            "HIGH",

        "resolution":
            "PARCEL_DOES_NOT_INTERSECT_DISTRICT_UNIT_PLAN",

        "geometry_verified":
            True,

        "evaluation": {
            "query_success":
                True,

            "intersects":
                False,

            "intersection_count":
                0,
        },

        "evidence": {
            "coordinate": {
                "x": x,
                "y": y,
                "crs": "EPSG:4326",
            },

            "query": {
                key: value
                for key, value
                in query_result.items()
                if key != "features"
            },

            "intersections":
                copy.deepcopy(
                    intersections
                ),
        },
    }


# ============================================================
# generic public API
# ============================================================

def resolve_site_spatial_condition(
    *,
    condition_name: str,
    site: Dict[str, Any],
    parcel: Dict[str, Any],
) -> Dict[str, Any]:

    normalized_name = safe_string(
        condition_name
    )

    if normalized_name == "지구단위계획":

        return (
            resolve_district_unit_plan_condition(
                site=site,
                parcel=parcel,
            )
        )

    return {
        "name": normalized_name,
        "type": "SITE",
        "state": "UNKNOWN",
        "confidence": "LOW",
        "pnu": safe_string(
            site.get(
                "pnu"
            )
        ),
        "resolution": (
            "UNSUPPORTED_SPATIAL_CONDITION"
        ),
        "geometry_verified": False,
        "source": {},
        "evaluation": {
            "query_success": False,
            "intersects": None,
            "intersection_count": None,
        },
        "evidence": {},
    }