# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-11A
산업단지 단지경계 공식 source / VWorld layer probe

목표
======================================================================
1. 국토교통부 공식 '단지경계' 공간정보 source를 사용한다.
2. 공공데이터포털에서 확인된 공식 서비스 식별자 damdan과
   VWorld Data API layer 후보의 실제 응답을 비교한다.
3. 후보 layer가 정상응답할 경우 실제 속성/schema를 출력한다.
4. SITE Parcel 주변 공간조회 결과를 수집한다.
5. layer 의미 / geometry가 검증되기 전에는 TRUE/FALSE 판정하지 않는다.

중요
======================================================================
공식 확인값:
- Provider: 국토교통부
- Dataset: 단지경계
- 공식 service identifier: damdan
- 공간범위: 대한민국 전체
- 목적: 산업입지도 내 산업단지 경계

후보 VWorld Data API ID:
- LT_C_DAMDAN

이 후보는 API 정상응답과 feature schema를 통해
이번 단계에서 실제 사용 가능 여부를 검증한다.

판정 원칙
======================================================================
- 후보 ID 문자열만 보고 산업단지 판정 금지
- HTTP/API 실패 -> UNKNOWN
- 정상 geometry 확보 전 TRUE/FALSE 금지
- Feature 존재만으로 TRUE 금지
- 다음 단계에서 Parcel Polygon 실제 intersection 수행
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from dotenv import load_dotenv

from shapely.geometry import shape


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-11A "
    "산업단지 단지경계 공식 source / VWorld layer probe"
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
    BASE_DIR / "law_data"
)

OUTPUT_DIR = (
    LAW_DATA_DIR / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "industrial_complex_boundary_source_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

VWORLD_API_KEY = (
    os.getenv(
        "VWORLD_API_KEY"
    )
)


# ============================================================
# 공식 source
# ============================================================

OFFICIAL_PROVIDER = (
    "국토교통부"
)

OFFICIAL_DATASET_NAME = (
    "단지경계"
)

OFFICIAL_SERVICE_IDENTIFIER = (
    "damdan"
)


# ============================================================
# VWorld
# ============================================================

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

# 아직 '확정 코드'로 취급하지 않는다.
# 이번 probe에서 실제 API 응답을 통해 검증한다.
VWORLD_DATASET_CANDIDATE = (
    "LT_C_DAMDAN"
)

REQUEST_TIMEOUT = 30


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


# ============================================================
# SITE
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
# 대표좌표
# ============================================================

def get_site_point(
    address: str,
) -> Optional[
    Tuple[
        float,
        float,
    ]
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

    point = (
        items[
            0
        ].get(
            "point",
            {},
        )
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
# VWorld layer query
# ============================================================

def query_layer(
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": (
            VWORLD_DATASET_CANDIDATE
        ),
        "key": (
            VWORLD_API_KEY
        ),
        "domain": "localhost",
        "format": "json",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": (
            f"POINT({x} {y})"
        ),
        "size": 100,
        "page": 1,
    }

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

    except Exception as exc:

        return {
            "http_status": None,
            "payload": None,
            "error": str(
                exc
            ),
        }

    try:

        payload = (
            response.json()
        )

    except Exception as exc:

        return {
            "http_status": (
                response.status_code
            ),
            "payload": None,
            "text_preview": (
                response.text[
                    :1000
                ]
            ),
            "error": (
                "JSON parse 실패: "
                f"{exc}"
            ),
        }

    return {
        "http_status": (
            response.status_code
        ),
        "payload": (
            payload
        ),
        "error": None,
    }


# ============================================================
# VWorld response parsing
# ============================================================

def parse_vworld_response(
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    body = payload.get(
        "response",
        {},
    )

    status = body.get(
        "status"
    )

    error = body.get(
        "error"
    )

    result = body.get(
        "result",
        {},
    )

    feature_collection = (
        result.get(
            "featureCollection",
            {}
        )
        if isinstance(
            result,
            dict,
        )
        else {}
    )

    features = (
        feature_collection.get(
            "features",
            []
        )
        if isinstance(
            feature_collection,
            dict,
        )
        else []
    )

    parsed_features = []

    for feature in features:

        geometry_data = (
            feature.get(
                "geometry"
            )
        )

        geometry_summary = {
            "present": False,
            "type": None,
            "valid": None,
            "bounds": None,
            "area": None,
        }

        if geometry_data:

            try:

                geom = shape(
                    geometry_data
                )

                geometry_summary = {
                    "present": True,
                    "type": (
                        geom.geom_type
                    ),
                    "valid": (
                        bool(
                            geom.is_valid
                        )
                    ),
                    "bounds": [
                        float(
                            value
                        )
                        for value
                        in geom.bounds
                    ],
                    # EPSG:4326이므로 이 area는
                    # 판정용 면적이 아니라 geometry 진단값
                    "area": (
                        float(
                            geom.area
                        )
                    ),
                }

            except Exception as exc:

                geometry_summary = {
                    "present": True,
                    "type": None,
                    "valid": False,
                    "bounds": None,
                    "area": None,
                    "error": str(
                        exc
                    ),
                }

        properties = (
            feature.get(
                "properties",
                {},
            )
        )

        parsed_features.append(
            {
                "id": (
                    feature.get(
                        "id"
                    )
                ),
                "properties": (
                    properties
                ),
                "property_keys": (
                    sorted(
                        properties.keys()
                    )
                    if isinstance(
                        properties,
                        dict,
                    )
                    else []
                ),
                "geometry": (
                    geometry_summary
                ),
            }
        )

    return {
        "status": (
            status
        ),
        "error": (
            error
        ),
        "feature_count": (
            len(
                features
            )
        ),
        "features": (
            parsed_features
        ),
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
        "VWORLD_API_KEY:",
        (
            "FOUND"
            if VWORLD_API_KEY
            else "MISSING"
        ),
    )

    print(
        "공식 source:",
        OFFICIAL_PROVIDER,
        "/",
        OFFICIAL_DATASET_NAME,
    )

    print(
        "공식 service identifier:",
        OFFICIAL_SERVICE_IDENTIFIER,
    )

    print(
        "VWorld dataset candidate:",
        VWORLD_DATASET_CANDIDATE,
    )

    # ========================================================
    # 환경검증
    # ========================================================

    if not VWORLD_API_KEY:

        print(
            "ERROR: VWORLD_API_KEY 없음"
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
            "ERROR: SITE PNU 검증 실패"
        )

        return 1

    # ========================================================
    # 1. 대표좌표
    # ========================================================

    print_section(
        "1. SITE 대표좌표 조회"
    )

    point = (
        get_site_point(
            site[
                "address"
            ]
        )
    )

    print(
        "point:",
        point,
    )

    if point is None:

        result = {
            "step": STEP_NAME,
            "condition": (
                "산업단지"
            ),
            "site": site,
            "resolution": {
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
                    "SITE 대표좌표 조회 실패"
                ),
            },
        }

        save_json(
            result
        )

        return 0

    # ========================================================
    # 2. layer probe
    # ========================================================

    print_section(
        "2. VWorld 단지경계 layer probe"
    )

    query_result = (
        query_layer(
            point[
                0
            ],
            point[
                1
            ],
        )
    )

    print(
        "HTTP:",
        query_result.get(
            "http_status"
        ),
    )

    if not isinstance(
        query_result.get(
            "payload"
        ),
        dict,
    ):

        print(
            "ERROR:",
            query_result.get(
                "error"
            ),
        )

        print(
            "preview:",
            query_result.get(
                "text_preview"
            ),
        )

        result = {
            "step": STEP_NAME,
            "condition": (
                "산업단지"
            ),
            "site": site,
            "source": {
                "official_provider": (
                    OFFICIAL_PROVIDER
                ),
                "official_dataset": (
                    OFFICIAL_DATASET_NAME
                ),
                "official_service_identifier": (
                    OFFICIAL_SERVICE_IDENTIFIER
                ),
                "vworld_dataset_candidate": (
                    VWORLD_DATASET_CANDIDATE
                ),
            },
            "resolution": {
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
                    "VWorld 후보 layer 응답을 "
                    "정상 파싱하지 못함"
                ),
            },
        }

        save_json(
            result
        )

        return 0

    parsed = (
        parse_vworld_response(
            query_result[
                "payload"
            ]
        )
    )

    print(
        "VWorld status:",
        parsed.get(
            "status"
        ),
    )

    print(
        "VWorld error:",
        parsed.get(
            "error"
        ),
    )

    print(
        "feature count:",
        parsed.get(
            "feature_count"
        ),
    )

    # ========================================================
    # 3. schema 출력
    # ========================================================

    print_section(
        "3. 응답 feature / schema"
    )

    features = (
        parsed.get(
            "features",
            [],
        )
    )

    if not features:

        print(
            "SITE point 결과 Feature: 0"
        )

    for index, feature in enumerate(
        features
    ):

        print()
        print(
            f"--- Feature {index + 1} ---"
        )

        print(
            "id:",
            feature.get(
                "id"
            ),
        )

        print(
            "property keys:",
            feature.get(
                "property_keys"
            ),
        )

        print(
            "properties:",
            feature.get(
                "properties"
            ),
        )

        print(
            "geometry:",
            feature.get(
                "geometry"
            ),
        )

    # ========================================================
    # 4. layer 사용 가능성
    # ========================================================

    print_section(
        "4. 현재 판정 상태"
    )

    api_success = (
        query_result.get(
            "http_status"
        )
        == 200
        and parsed.get(
            "status"
        )
        == "OK"
    )

    # Feature 0은 layer 실패가 아니다.
    # 해당 SITE point가 산업단지 밖이면 정상적으로 0일 수 있음.
    if api_success:

        layer_status = (
            "API_RESPONDED"
        )

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
                "국토교통부 공식 단지경계 source에 대응하는 "
                "VWorld layer 후보가 정상 API 응답함. "
                "SITE Point 결과만으로 FALSE를 확정하지 않고 "
                "다음 단계에서 layer 의미 양성대조 및 "
                "Parcel Polygon 공간교차를 검증해야 함"
            ),
        }

        next_step = (
            "STEP 17-21-C-9-2-11B "
            "단지경계 양성대조 + Parcel Polygon 실제 공간교차"
        )

    else:

        layer_status = (
            "UNVERIFIED"
        )

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
                "VWorld 단지경계 layer 후보의 "
                "정상 API 응답을 확인하지 못함"
            ),
        }

        next_step = (
            "단지경계 VWorld layer ID/endpoint 재검증"
        )

    print(
        "layer status:",
        layer_status,
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

    # ========================================================
    # 저장
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "산업단지"
        ),

        "site": (
            site
        ),

        "official_source": {
            "provider": (
                OFFICIAL_PROVIDER
            ),
            "dataset": (
                OFFICIAL_DATASET_NAME
            ),
            "official_service_identifier": (
                OFFICIAL_SERVICE_IDENTIFIER
            ),
            "coverage": (
                "대한민국 전체"
            ),
            "purpose": (
                "산업입지도 산업단지 단지경계"
            ),
        },

        "vworld_probe": {
            "dataset_candidate": (
                VWORLD_DATASET_CANDIDATE
            ),
            "http_status": (
                query_result.get(
                    "http_status"
                )
            ),
            "status": (
                parsed.get(
                    "status"
                )
            ),
            "error": (
                parsed.get(
                    "error"
                )
            ),
            "feature_count": (
                parsed.get(
                    "feature_count"
                )
            ),
            "features": (
                features
            ),
            "layer_status": (
                layer_status
            ),
        },

        "resolution": (
            resolution
        ),

        "validation": {
            "VWORLD_API_KEY 존재": (
                bool(
                    VWORLD_API_KEY
                )
            ),
            "SITE PNU 19자리": (
                len(
                    site.get(
                        "pnu",
                        "",
                    )
                )
                == 19
            ),
            "공식 provider 국토교통부": (
                True
            ),
            "공식 dataset 단지경계": (
                True
            ),
            "공식 service identifier damdan": (
                True
            ),
            "Point 결과만으로 FALSE 금지": (
                True
            ),
            "geometry intersection 전 TRUE 금지": (
                True
            ),
        },

        "next_step": (
            next_step
        ),
    }

    save_json(
        result
    )

    print()

    print(
        "NEXT:",
        next_step,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )