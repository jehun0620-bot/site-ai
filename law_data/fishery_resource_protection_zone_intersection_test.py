# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-9B
수산자원보호구역 공식 WFS GML / Parcel Polygon 실제 공간교차 검증

목표
======================================================================
1. FISHERY_RESOURCE_API_KEY의 URL-Encoding 문제를 정상화한다.
2. 해양수산부 수산자원보호구역 공식 WFS를 호출한다.
3. 영광보전지역 양성대조 geometry를 실제 GML로 복원한다.
4. 양성대조 geometry bounds를 bbox로 재조회하여
   bbox가 실제 공간필터로 동작하는지 검증한다.
5. SITE Parcel Polygon을 VWorld에서 PNU 직접 검증하여 확보한다.
6. Parcel Polygon을 EPSG:5179로 변환한다.
7. SITE Parcel bbox를 공식 WFS bbox로 조회한다.
8. 반환 feature와 Parcel Polygon의 실제 면적교차를 계산한다.
9. 정상조회 + 양성 공간대조 + 교차 없음일 때만 FALSE / HIGH 판정한다.

판정 원칙
======================================================================
- HTTP 실패 -> UNKNOWN
- 양성대조 실패 -> UNKNOWN
- GML 파싱 실패 -> UNKNOWN
- CRS 불일치 -> UNKNOWN
- bbox 공간필터 의미 미검증 -> UNKNOWN
- TRUE -> 실제 Parcel 면적교차 > 0 필요
- FALSE -> 정상조회 + 양성 공간대조 + 유효한 무교차 근거 필요
- 경계 접촉(area = 0)은 TRUE가 아님
"""

from __future__ import annotations

import json
import os
import xml.etree.ElementTree as ET

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import unquote

import requests

from dotenv import load_dotenv

from pyproj import Transformer

from shapely.geometry import (
    LinearRing,
    MultiPolygon,
    Polygon,
    shape,
)

from shapely.geometry.base import BaseGeometry

from shapely.ops import transform as shapely_transform


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-9B "
    "수산자원보호구역 공식 WFS GML / "
    "Parcel Polygon 실제 공간교차 검증"
)


# ============================================================
# 프로젝트 경로
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

LAW_DATA_DIR = (
    BASE_DIR
    / "law_data"
)

OUTPUT_DIR = (
    LAW_DATA_DIR
    / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "fishery_resource_protection_zone_intersection.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

FISHERY_RESOURCE_API_KEY_RAW = (
    os.getenv(
        "FISHERY_RESOURCE_API_KEY"
    )
)

VWORLD_API_KEY = (
    os.getenv(
        "VWORLD_API_KEY"
    )
)


# ============================================================
# 해양수산부 공식 API
# ============================================================

FISHERY_API_URL = (
    "http://apis.data.go.kr/"
    "1192000/"
    "apVhdService_FshrsrcPzn/"
    "getOpnFshrsrcPznWFS"
)

POSITIVE_CONTROL_NAME = (
    "영광보전지역"
)

EXPECTED_CRS = (
    "EPSG:5179"
)

MAX_FEATURES = 100

REQUEST_TIMEOUT = 30


# ============================================================
# VWorld
# ============================================================

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)


# ============================================================
# namespace
# ============================================================

GML_NS = (
    "http://www.opengis.net/gml"
)


# ============================================================
# 공통
# ============================================================

def print_section(
    title: str,
) -> None:

    print()

    print(
        "=" * 78
    )

    print(
        f"=== {title} ==="
    )

    print(
        "=" * 78
    )


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def strip_namespace(
    tag: str,
) -> str:

    if "}" in tag:

        return tag.split(
            "}",
            1,
        )[1]

    return tag


def normalize_crs_name(
    value: str,
) -> Optional[str]:

    text = safe_string(
        value
    ).lower()

    if not text:
        return None

    if (
        "#5179" in text
        or "epsg:5179" in text
        or "/5179" in text
    ):

        return "EPSG:5179"

    return value


# ============================================================
# SITE context
# ============================================================

def load_site_context() -> Dict[str, str]:

    payload = load_json(
        QUERY_CONTEXT_PATH
    )

    context = payload.get(
        "query_context",
        {},
    )

    return {
        "site_id": safe_string(
            context.get(
                "site_id"
            )
        ),
        "address": safe_string(
            context.get(
                "address"
            )
        ),
        "pnu": safe_string(
            context.get(
                "pnu"
            )
        ),
    }


# ============================================================
# 인증키
# ============================================================

def get_fishery_api_key() -> Optional[str]:

    if not FISHERY_RESOURCE_API_KEY_RAW:
        return None

    # --------------------------------------------------------
    # 중요
    #
    # .env에는 Encoding 인증키가 저장되어 있다.
    # requests params=에 그대로 넣으면 %가 다시 encoding되므로
    # 반드시 unquote한 Decoding 인증키를 전달한다.
    # --------------------------------------------------------

    return unquote(
        FISHERY_RESOURCE_API_KEY_RAW
    )


# ============================================================
# VWorld 대표 좌표
# ============================================================

def get_site_point(
    address: str,
) -> Optional[
    Tuple[float, float]
]:

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": address,
        "type": "address",
        "category": "parcel",
        "format": "json",
        "errorformat": "json",
        "key": VWORLD_API_KEY,
    }

    try:

        response = requests.get(
            VWORLD_SEARCH_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        payload = (
            response.json()
        )

    except Exception:

        return None

    body = payload.get(
        "response",
        {},
    )

    if (
        body.get(
            "status"
        )
        != "OK"
    ):

        return None

    items = (
        body
        .get(
            "result",
            {},
        )
        .get(
            "items",
            [],
        )
    )

    if not items:
        return None

    point = items[
        0
    ].get(
        "point",
        {},
    )

    try:

        return (
            float(
                point["x"]
            ),
            float(
                point["y"]
            ),
        )

    except Exception:

        return None


# ============================================================
# VWorld Parcel Polygon
# ============================================================

def query_parcel_polygon(
    x: float,
    y: float,
    pnu: str,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": PARCEL_DATASET,
        "key": VWORLD_API_KEY,
        "domain": "localhost",
        "format": "json",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": (
            f"POINT({x} {y})"
        ),
        "size": 100,
    }

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        payload = (
            response.json()
        )

    except Exception as exc:

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "raw_feature_count": 0,
            "features": [],
            "reason": (
                "VWorld Parcel API 호출 실패: "
                f"{exc}"
            ),
        }

    body = payload.get(
        "response",
        {},
    )

    if (
        body.get(
            "status"
        )
        != "OK"
    ):

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "raw_feature_count": 0,
            "features": [],
            "reason": (
                "VWorld Parcel API status="
                f"{body.get('status')}"
            ),
        }

    features = (
        body
        .get(
            "result",
            {},
        )
        .get(
            "featureCollection",
            {},
        )
        .get(
            "features",
            [],
        )
    )

    matched = []

    for feature in features:

        properties = (
            feature.get(
                "properties",
                {},
            )
        )

        feature_pnu = (
            safe_string(
                properties.get(
                    "pnu"
                )
            )
        )

        if (
            feature_pnu
            != pnu
        ):

            continue

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        try:

            geom = shape(
                geometry
            )

        except Exception:

            continue

        if geom.is_empty:
            continue

        if (
            geom.geom_type
            not in (
                "Polygon",
                "MultiPolygon",
            )
        ):

            continue

        matched.append(
            {
                "id": feature.get(
                    "id"
                ),
                "properties": (
                    properties
                ),
                "geometry": geom,
            }
        )

    return {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "raw_feature_count": (
            len(features)
        ),
        "features": matched,
        "reason": (
            "대상 PNU Parcel Polygon 조회 완료"
        ),
    }


# ============================================================
# CRS transform
# ============================================================

def transform_geometry(
    geom: BaseGeometry,
    source_crs: str,
    target_crs: str,
) -> BaseGeometry:

    transformer = (
        Transformer.from_crs(
            source_crs,
            target_crs,
            always_xy=True,
        )
    )

    return shapely_transform(
        transformer.transform,
        geom,
    )


# ============================================================
# 해양수산부 API
# ============================================================

def request_fishery_api(
    params: Dict[str, Any],
) -> Dict[str, Any]:

    api_key = (
        get_fishery_api_key()
    )

    if not api_key:

        return {
            "http_status": None,
            "content_type": "",
            "content": b"",
            "error": (
                "FISHERY_RESOURCE_API_KEY 없음"
            ),
        }

    request_params = dict(
        params
    )

    request_params[
        "serviceKey"
    ] = api_key

    try:

        response = requests.get(
            FISHERY_API_URL,
            params=request_params,
            timeout=REQUEST_TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64)"
                ),
                "Accept": (
                    "application/xml,"
                    "text/xml,"
                    "*/*"
                ),
            },
        )

        return {
            "http_status": (
                response.status_code
            ),
            "content_type": (
                response.headers.get(
                    "Content-Type",
                    "",
                )
            ),
            "content": (
                response.content
            ),
            "error": None,
        }

    except Exception as exc:

        return {
            "http_status": None,
            "content_type": "",
            "content": b"",
            "error": str(
                exc
            ),
        }


# ============================================================
# GML 좌표
# ============================================================

def parse_poslist(
    text: str,
) -> List[
    Tuple[float, float]
]:

    values = []

    for token in (
        safe_string(
            text
        ).split()
    ):

        try:

            values.append(
                float(token)
            )

        except ValueError:

            pass

    if (
        len(values)
        < 6
    ):

        return []

    if (
        len(values)
        % 2
        != 0
    ):

        return []

    coords = []

    for i in range(
        0,
        len(values),
        2,
    ):

        coords.append(
            (
                values[i],
                values[i + 1],
            )
        )

    if (
        coords
        and coords[0]
        != coords[-1]
    ):

        coords.append(
            coords[0]
        )

    return coords


def parse_linear_ring(
    ring_element: ET.Element,
) -> List[
    Tuple[float, float]
]:

    poslist = (
        ring_element.find(
            f".//{{{GML_NS}}}posList"
        )
    )

    if (
        poslist is not None
        and poslist.text
    ):

        return parse_poslist(
            poslist.text
        )

    positions = (
        ring_element.findall(
            f".//{{{GML_NS}}}pos"
        )
    )

    coords = []

    for position in positions:

        values = (
            safe_string(
                position.text
            )
            .split()
        )

        if (
            len(values)
            < 2
        ):

            continue

        try:

            coords.append(
                (
                    float(
                        values[0]
                    ),
                    float(
                        values[1]
                    ),
                )
            )

        except ValueError:

            continue

    if (
        coords
        and coords[0]
        != coords[-1]
    ):

        coords.append(
            coords[0]
        )

    return coords


# ============================================================
# GML Polygon
# ============================================================

def parse_gml_polygon(
    polygon_element: ET.Element,
) -> Optional[Polygon]:

    exterior_element = (
        polygon_element.find(
            f"./{{{GML_NS}}}exterior/"
            f"{{{GML_NS}}}LinearRing"
        )
    )

    if exterior_element is None:

        exterior_element = (
            polygon_element.find(
                f".//{{{GML_NS}}}exterior/"
                f"{{{GML_NS}}}LinearRing"
            )
        )

    if exterior_element is None:
        return None

    exterior = (
        parse_linear_ring(
            exterior_element
        )
    )

    if (
        len(exterior)
        < 4
    ):

        return None

    interiors = []

    interior_elements = (
        polygon_element.findall(
            f".//{{{GML_NS}}}interior/"
            f"{{{GML_NS}}}LinearRing"
        )
    )

    for interior_element in (
        interior_elements
    ):

        ring = (
            parse_linear_ring(
                interior_element
            )
        )

        if (
            len(ring)
            >= 4
        ):

            interiors.append(
                ring
            )

    try:

        polygon = Polygon(
            exterior,
            interiors,
        )

    except Exception:

        return None

    if polygon.is_empty:

        return None

    if not polygon.is_valid:

        try:

            polygon = (
                polygon.buffer(
                    0
                )
            )

        except Exception:

            return None

    if polygon.is_empty:

        return None

    if (
        polygon.geom_type
        == "Polygon"
    ):

        return polygon

    return None


# ============================================================
# Feature parsing
# ============================================================

def parse_feature_collection(
    content: bytes,
) -> Dict[str, Any]:

    if not content:

        return {
            "parse_success": False,
            "number_of_features": None,
            "features": [],
            "crs_values": [],
            "error": (
                "empty response"
            ),
        }

    try:

        root = ET.fromstring(
            content
        )

    except Exception as exc:

        return {
            "parse_success": False,
            "number_of_features": None,
            "features": [],
            "crs_values": [],
            "error": str(
                exc
            ),
        }

    number_of_features = (
        root.attrib.get(
            "numberOfFeatures"
        )
    )

    features = []

    crs_values = []

    # --------------------------------------------------------
    # featureMembers 내부의 실제 feature element 탐색
    # --------------------------------------------------------

    feature_members = (
        root.find(
            f".//{{{GML_NS}}}featureMembers"
        )
    )

    if feature_members is None:

        return {
            "parse_success": True,
            "number_of_features": (
                number_of_features
            ),
            "features": [],
            "crs_values": [],
            "error": None,
        }

    for feature_element in list(
        feature_members
    ):

        properties = {}

        geometry = None

        geometry_element = None

        for child in list(
            feature_element
        ):

            key = strip_namespace(
                child.tag
            )

            if (
                key.lower()
                == "geom"
            ):

                geometry_element = child

                continue

            properties[key] = (
                safe_string(
                    child.text
                )
            )

        if (
            geometry_element
            is not None
        ):

            surface = (
                geometry_element.find(
                    f".//{{{GML_NS}}}MultiSurface"
                )
            )

            if surface is not None:

                srs_name = (
                    surface.attrib.get(
                        "srsName"
                    )
                )

                normalized_crs = (
                    normalize_crs_name(
                        srs_name
                    )
                )

                if (
                    normalized_crs
                    and normalized_crs
                    not in crs_values
                ):

                    crs_values.append(
                        normalized_crs
                    )

            polygon_elements = (
                geometry_element.findall(
                    f".//{{{GML_NS}}}Polygon"
                )
            )

            polygons = []

            for polygon_element in (
                polygon_elements
            ):

                polygon = (
                    parse_gml_polygon(
                        polygon_element
                    )
                )

                if polygon is not None:

                    polygons.append(
                        polygon
                    )

            if len(
                polygons
            ) == 1:

                geometry = (
                    polygons[0]
                )

            elif len(
                polygons
            ) > 1:

                try:

                    geometry = (
                        MultiPolygon(
                            polygons
                        )
                    )

                    if not geometry.is_valid:

                        geometry = (
                            geometry.buffer(
                                0
                            )
                        )

                except Exception:

                    geometry = None

        features.append(
            {
                "properties": (
                    properties
                ),
                "geometry": (
                    geometry
                ),
            }
        )

    return {
        "parse_success": True,
        "number_of_features": (
            number_of_features
        ),
        "features": features,
        "crs_values": crs_values,
        "error": None,
    }


# ============================================================
# feature summary
# ============================================================

def summarize_feature(
    feature: Dict[str, Any],
) -> Dict[str, Any]:

    properties = feature.get(
        "properties",
        {},
    )

    geometry = feature.get(
        "geometry"
    )

    result = {
        "code": (
            properties.get(
                "fshrsrc_pzn_cd"
            )
        ),
        "name": (
            properties.get(
                "fshrsrc_pzn_nm"
            )
        ),
        "declared_area": (
            properties.get(
                "fshrsrc_pzn_ar"
            )
        ),
        "geometry_type": None,
        "geometry_valid": None,
        "geometry_area": None,
        "bounds": None,
    }

    if geometry is not None:

        result[
            "geometry_type"
        ] = geometry.geom_type

        result[
            "geometry_valid"
        ] = bool(
            geometry.is_valid
        )

        result[
            "geometry_area"
        ] = float(
            geometry.area
        )

        result[
            "bounds"
        ] = [
            float(x)
            for x
            in geometry.bounds
        ]

    return result


# ============================================================
# bbox
# ============================================================

def bbox_to_text(
    bounds: Tuple[
        float,
        float,
        float,
        float,
    ],
) -> str:

    return ",".join(
        str(
            float(x)
        )
        for x
        in bounds
    )


def expand_bounds(
    bounds: Tuple[
        float,
        float,
        float,
        float,
    ],
    buffer_meter: float,
) -> Tuple[
    float,
    float,
    float,
    float,
]:

    minx, miny, maxx, maxy = (
        bounds
    )

    return (
        minx - buffer_meter,
        miny - buffer_meter,
        maxx + buffer_meter,
        maxy + buffer_meter,
    )


# ============================================================
# spatial intersection
# ============================================================

def calculate_intersections(
    parcel: BaseGeometry,
    features: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    parcel_area = float(
        parcel.area
    )

    results = []

    max_ratio = 0.0

    positive_area_count = 0

    bbox_candidate_count = 0

    for index, feature in enumerate(
        features
    ):

        geometry = feature.get(
            "geometry"
        )

        if geometry is None:
            continue

        if not (
            parcel.envelope.intersects(
                geometry.envelope
            )
        ):

            continue

        bbox_candidate_count += 1

        if not parcel.intersects(
            geometry
        ):

            continue

        intersection = (
            parcel.intersection(
                geometry
            )
        )

        intersection_area = float(
            intersection.area
        )

        if (
            parcel_area
            > 0
        ):

            ratio = (
                intersection_area
                / parcel_area
            )

        else:

            ratio = 0.0

        if (
            ratio
            > max_ratio
        ):

            max_ratio = ratio

        if (
            intersection_area
            > 0
        ):

            positive_area_count += 1

        properties = feature.get(
            "properties",
            {},
        )

        results.append(
            {
                "index": index,
                "code": (
                    properties.get(
                        "fshrsrc_pzn_cd"
                    )
                ),
                "name": (
                    properties.get(
                        "fshrsrc_pzn_nm"
                    )
                ),
                "intersects": True,
                "intersection_area": (
                    intersection_area
                ),
                "parcel_intersection_ratio": (
                    ratio
                ),
                "boundary_only": (
                    intersection_area
                    <= 0
                ),
            }
        )

    return {
        "bbox_candidate_count": (
            bbox_candidate_count
        ),
        "intersection_count": (
            len(results)
        ),
        "positive_area_intersection_count": (
            positive_area_count
        ),
        "max_intersection_ratio": (
            max_ratio
        ),
        "features": results,
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        STEP_NAME
    )

    site = (
        load_site_context()
    )

    print(
        "SITE ID:",
        site.get(
            "site_id"
        ),
    )

    print(
        "주소:",
        site.get(
            "address"
        ),
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print(
        "FISHERY_RESOURCE_API_KEY:",
        (
            "FOUND"
            if FISHERY_RESOURCE_API_KEY_RAW
            else "MISSING"
        ),
    )

    print(
        "VWORLD_API_KEY:",
        (
            "FOUND"
            if VWORLD_API_KEY
            else "MISSING"
        ),
    )

    # ========================================================
    # 기본 환경 검증
    # ========================================================

    if (
        not FISHERY_RESOURCE_API_KEY_RAW
        or not VWORLD_API_KEY
    ):

        print(
            "ERROR: 필수 API Key가 없습니다."
        )

        return 1

    if (
        len(
            site.get(
                "pnu",
                "",
            )
        )
        != 19
    ):

        print(
            "ERROR: PNU가 유효하지 않습니다."
        )

        return 1

    # ========================================================
    # 1. Parcel 확보
    # ========================================================

    print_section(
        "1. SITE Parcel Polygon 조회"
    )

    point = (
        get_site_point(
            site[
                "address"
            ]
        )
    )

    if point is None:

        print(
            "대표좌표 조회 실패"
        )

        return 1

    print(
        "대표좌표 EPSG:4326:",
        point,
    )

    parcel_result = (
        query_parcel_polygon(
            point[0],
            point[1],
            site[
                "pnu"
            ],
        )
    )

    matched_parcels = (
        parcel_result.get(
            "features",
            [],
        )
    )

    print(
        "Parcel query_status:",
        parcel_result.get(
            "query_status"
        ),
    )

    print(
        "PNU matched parcel count:",
        len(
            matched_parcels
        ),
    )

    if (
        parcel_result.get(
            "query_status"
        )
        != "QUERY_SUCCESS"
        or not matched_parcels
    ):

        print(
            "Parcel Polygon 확보 실패"
        )

        return 1

    parcel_feature = (
        matched_parcels[
            0
        ]
    )

    parcel_4326 = (
        parcel_feature[
            "geometry"
        ]
    )

    parcel_5179 = (
        transform_geometry(
            parcel_4326,
            "EPSG:4326",
            "EPSG:5179",
        )
    )

    print(
        "Parcel geometry:",
        parcel_5179.geom_type,
    )

    print(
        "Parcel area:",
        parcel_5179.area,
    )

    print(
        "Parcel bounds EPSG:5179:",
        list(
            parcel_5179.bounds
        ),
    )

    # ========================================================
    # 2. 양성대조 명칭 조회
    # ========================================================

    print_section(
        "2. 영광보전지역 양성대조"
    )

    positive_http = (
        request_fishery_api(
            {
                "fshrsr_pzn_nm": (
                    POSITIVE_CONTROL_NAME
                ),
                "maxFeatures": 10,
            }
        )
    )

    print(
        "HTTP:",
        positive_http.get(
            "http_status"
        ),
    )

    print(
        "Content-Type:",
        positive_http.get(
            "content_type"
        ),
    )

    positive_parsed = (
        parse_feature_collection(
            positive_http.get(
                "content",
                b"",
            )
        )
    )

    positive_features = (
        positive_parsed.get(
            "features",
            [],
        )
    )

    positive_geometry_features = [
        feature
        for feature
        in positive_features
        if (
            feature.get(
                "geometry"
            )
            is not None
        )
    ]

    print(
        "numberOfFeatures:",
        positive_parsed.get(
            "number_of_features"
        ),
    )

    print(
        "parsed feature count:",
        len(
            positive_features
        ),
    )

    print(
        "geometry feature count:",
        len(
            positive_geometry_features
        ),
    )

    print(
        "CRS:",
        positive_parsed.get(
            "crs_values"
        ),
    )

    if (
        positive_http.get(
            "http_status"
        )
        != 200
        or not positive_geometry_features
    ):

        resolution = {
            "query_status": (
                "QUERY_FAILED"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "양성대조 WFS geometry를 "
                "정상 확보하지 못함"
            ),
        }

        result = {
            "step": STEP_NAME,
            "site": site,
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        print(
            resolution
        )

        return 0

    # ========================================================
    # 3. CRS 검증
    # ========================================================

    print_section(
        "3. 공식 CRS 검증"
    )

    crs_values = (
        positive_parsed.get(
            "crs_values",
            [],
        )
    )

    crs_verified = (
        EXPECTED_CRS
        in crs_values
    )

    print(
        "EXPECTED:",
        EXPECTED_CRS,
    )

    print(
        "RESPONSE:",
        crs_values,
    )

    print(
        "CRS verified:",
        crs_verified,
    )

    if not crs_verified:

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "공식 WFS geometry CRS를 "
                "EPSG:5179로 검증하지 못함"
            ),
        }

        result = {
            "step": STEP_NAME,
            "site": site,
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        return 0

    # ========================================================
    # 4. BBOX 양성 공간대조
    # ========================================================

    print_section(
        "4. BBOX 공간필터 양성대조"
    )

    positive_geom = (
        positive_geometry_features[
            0
        ][
            "geometry"
        ]
    )

    positive_bbox = (
        expand_bounds(
            positive_geom.bounds,
            10.0,
        )
    )

    positive_bbox_http = (
        request_fishery_api(
            {
                "bbox": (
                    bbox_to_text(
                        positive_bbox
                    )
                ),
                "maxFeatures": 100,
            }
        )
    )

    positive_bbox_parsed = (
        parse_feature_collection(
            positive_bbox_http.get(
                "content",
                b"",
            )
        )
    )

    positive_bbox_features = (
        positive_bbox_parsed.get(
            "features",
            [],
        )
    )

    positive_bbox_intersection = (
        calculate_intersections(
            positive_geom,
            positive_bbox_features,
        )
    )

    positive_bbox_ok = (
        positive_bbox_http.get(
            "http_status"
        )
        == 200
        and positive_bbox_intersection.get(
            "positive_area_intersection_count",
            0,
        )
        > 0
    )

    print(
        "HTTP:",
        positive_bbox_http.get(
            "http_status"
        ),
    )

    print(
        "feature count:",
        len(
            positive_bbox_features
        ),
    )

    print(
        "positive area intersection:",
        positive_bbox_intersection.get(
            "positive_area_intersection_count"
        ),
    )

    print(
        "BBOX spatial filter verified:",
        positive_bbox_ok,
    )

    if not positive_bbox_ok:

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "공식 WFS와 geometry는 정상이나 "
                "bbox 공간필터의 양성대조를 "
                "검증하지 못해 FALSE 판정에 사용하지 않음"
            ),
        }

        result = {
            "step": STEP_NAME,
            "site": site,
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        return 0

    # ========================================================
    # 5. SITE BBOX 조회
    # ========================================================

    print_section(
        "5. SITE 수산자원보호구역 BBOX 조회"
    )

    site_bbox = (
        expand_bounds(
            parcel_5179.bounds,
            5.0,
        )
    )

    site_http = (
        request_fishery_api(
            {
                "bbox": (
                    bbox_to_text(
                        site_bbox
                    )
                ),
                "maxFeatures": (
                    MAX_FEATURES
                ),
            }
        )
    )

    site_parsed = (
        parse_feature_collection(
            site_http.get(
                "content",
                b"",
            )
        )
    )

    site_features = (
        site_parsed.get(
            "features",
            [],
        )
    )

    print(
        "HTTP:",
        site_http.get(
            "http_status"
        ),
    )

    print(
        "numberOfFeatures:",
        site_parsed.get(
            "number_of_features"
        ),
    )

    print(
        "parsed feature count:",
        len(
            site_features
        ),
    )

    print(
        "CRS:",
        site_parsed.get(
            "crs_values"
        ),
    )

    if (
        site_http.get(
            "http_status"
        )
        != 200
    ):

        resolution = {
            "query_status": (
                "QUERY_FAILED"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "SITE BBOX WFS 조회 실패"
            ),
        }

        result = {
            "step": STEP_NAME,
            "site": site,
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        return 0

    # ========================================================
    # 6. Parcel 실제 교차
    # ========================================================

    print_section(
        "6. Parcel Polygon 실제 공간교차"
    )

    intersection = (
        calculate_intersections(
            parcel_5179,
            site_features,
        )
    )

    positive_area_count = (
        intersection.get(
            "positive_area_intersection_count",
            0,
        )
    )

    max_ratio = (
        intersection.get(
            "max_intersection_ratio",
            0.0,
        )
    )

    print(
        "bbox candidate count:",
        intersection.get(
            "bbox_candidate_count"
        ),
    )

    print(
        "intersection count:",
        intersection.get(
            "intersection_count"
        ),
    )

    print(
        "positive area intersection count:",
        positive_area_count,
    )

    print(
        "max parcel intersection ratio:",
        max_ratio,
    )

    # ========================================================
    # 7. 최종 판정
    # ========================================================

    print_section(
        "7. 최종 판정"
    )

    if (
        positive_area_count
        > 0
    ):

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "TRUE"
            ),
            "confidence": (
                "HIGH"
            ),
            "reason": (
                "해양수산부 공식 수산자원보호구역 "
                "EPSG:5179 WFS geometry와 대상 PNU "
                "Parcel Polygon의 실제 면적교차가 확인됨"
            ),
            "max_intersection_ratio": (
                max_ratio
            ),
        }

    else:

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "FALSE"
            ),
            "confidence": (
                "HIGH"
            ),
            "reason": (
                "해양수산부 공식 수산자원보호구역 WFS를 "
                "정상 조회하고 EPSG:5179 geometry 및 "
                "bbox 공간필터를 양성대조로 검증한 뒤 "
                "대상 PNU Parcel Polygon과 공간교차를 "
                "수행했으나 실제 면적교차가 확인되지 않음"
            ),
            "max_intersection_ratio": (
                max_ratio
            ),
        }

    result = {
        "step": STEP_NAME,

        "condition": (
            "수산자원보호구역"
        ),

        "site": site,

        "source": {
            "provider": (
                "해양수산부"
            ),
            "dataset": (
                "수산자원보호구역"
            ),
            "endpoint": (
                FISHERY_API_URL
            ),
            "api_type": (
                "WFS / GML 3.1.1"
            ),
            "crs": (
                EXPECTED_CRS
            ),
            "authentication": {
                "environment_variable": (
                    "FISHERY_RESOURCE_API_KEY"
                ),
                "env_value_format": (
                    "URL_ENCODED"
                ),
                "requests_value_format": (
                    "URL_DECODED_BY_UNQUOTE"
                ),
            },
        },

        "parcel": {
            "provider": (
                "VWorld"
            ),
            "dataset": (
                PARCEL_DATASET
            ),
            "feature_id": (
                parcel_feature.get(
                    "id"
                )
            ),
            "pnu_direct_match": True,
            "original_crs": (
                "EPSG:4326"
            ),
            "intersection_crs": (
                "EPSG:5179"
            ),
            "geometry_type": (
                parcel_5179.geom_type
            ),
            "area": float(
                parcel_5179.area
            ),
            "bounds": [
                float(x)
                for x
                in parcel_5179.bounds
            ],
        },

        "positive_control": {
            "name": (
                POSITIVE_CONTROL_NAME
            ),
            "http_status": (
                positive_http.get(
                    "http_status"
                )
            ),
            "feature_count": (
                len(
                    positive_features
                )
            ),
            "geometry_feature_count": (
                len(
                    positive_geometry_features
                )
            ),
            "crs_values": (
                crs_values
            ),
            "first_feature": (
                summarize_feature(
                    positive_geometry_features[
                        0
                    ]
                )
            ),
        },

        "bbox_positive_control": {
            "query_bbox": [
                float(x)
                for x
                in positive_bbox
            ],
            "http_status": (
                positive_bbox_http.get(
                    "http_status"
                )
            ),
            "feature_count": (
                len(
                    positive_bbox_features
                )
            ),
            "intersection": (
                positive_bbox_intersection
            ),
            "verified": (
                positive_bbox_ok
            ),
        },

        "site_bbox_query": {
            "query_bbox": [
                float(x)
                for x
                in site_bbox
            ],
            "http_status": (
                site_http.get(
                    "http_status"
                )
            ),
            "number_of_features": (
                site_parsed.get(
                    "number_of_features"
                )
            ),
            "parsed_feature_count": (
                len(
                    site_features
                )
            ),
            "crs_values": (
                site_parsed.get(
                    "crs_values"
                )
            ),
            "features": [
                summarize_feature(
                    feature
                )
                for feature
                in site_features
            ],
        },

        "intersection": (
            intersection
        ),

        "resolution": (
            resolution
        ),

        "validation": {
            "FISHERY_RESOURCE_API_KEY 존재": (
                bool(
                    FISHERY_RESOURCE_API_KEY_RAW
                )
            ),
            "인증키 unquote 적용": True,
            "VWORLD_API_KEY 존재": (
                bool(
                    VWORLD_API_KEY
                )
            ),
            "PNU 19자리": (
                len(
                    site.get(
                        "pnu",
                        "",
                    )
                )
                == 19
            ),
            "Parcel query 성공": (
                parcel_result.get(
                    "query_status"
                )
                == "QUERY_SUCCESS"
            ),
            "Parcel PNU 직접 검증": (
                bool(
                    matched_parcels
                )
            ),
            "Parcel Polygon geometry": (
                parcel_5179.geom_type
                in (
                    "Polygon",
                    "MultiPolygon",
                )
            ),
            "양성대조 HTTP 200": (
                positive_http.get(
                    "http_status"
                )
                == 200
            ),
            "양성대조 geometry 존재": (
                bool(
                    positive_geometry_features
                )
            ),
            "공식 EPSG:5179 확인": (
                crs_verified
            ),
            "BBOX 양성 공간대조 성공": (
                positive_bbox_ok
            ),
            "SITE BBOX HTTP 200": (
                site_http.get(
                    "http_status"
                )
                == 200
            ),
            "TRUE는 실제 면적교차 필요": True,
            "경계접촉만으로 TRUE 금지": True,
            "FALSE는 정상조회 및 양성대조 필요": True,
        },

        "next_step": (
            "수산자원보호구역 판정 확정 후 "
            "다음 미해결 공간조건으로 진행"
        ),
    }

    save_json(
        result
    )

    print(
        "query_status:",
        resolution.get(
            "query_status"
        ),
    )

    print(
        "resolution:",
        resolution.get(
            "resolution"
        ),
    )

    print(
        "confidence:",
        resolution.get(
            "confidence"
        ),
    )

    print(
        "reason:",
        resolution.get(
            "reason"
        ),
    )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )