import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-2B-2
# VWorld 지구단위계획 Feature / Geometry 분석
#
# 목적
# ------------------------------------------------------------
# 1. 검증 완료 dataset LT_C_UPISUQ161 사용
# 2. 대상 SITE 대표 좌표로 실제 Feature 조회
# 3. FeatureCollection 구조 분석
# 4. geometry 추출
# 5. POINT-IN-POLYGON 1차 판정
# 6. 조회 성공 + feature 존재 + geometry 포함 → TRUE
# 7. 조회 성공 + feature 0건 → FALSE 후보
# 8. API 오류 / geometry 해석 실패 → UNKNOWN
#
# 주의
# ------------------------------------------------------------
# 현재 대표좌표는 주소검색 point이다.
# 최종 단계에서는 필지 polygon과 지구단위계획 polygon의
# 실제 intersection으로 한 번 더 검증한다.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

PROBE_PATH = (
    BASE_DIR
    / "output"
    / "vworld_data_identifier_probe.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "vworld_district_unit_plan_geometry_test.json"
)

ENV_PATH = PROJECT_ROOT / ".env"

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

DATASET = "LT_C_UPISUQ161"

REQUEST_TIMEOUT = 30


# ============================================================
# 공통
# ============================================================

def load_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:
    print(char * width)


def short_text(
    value: Any,
    length: int = 700,
) -> str:
    text = str(value)

    if len(text) <= length:
        return text

    return text[:length] + "..."


def first_nonempty(
    obj: Dict[str, Any],
    keys: List[str],
) -> str:
    for key in keys:
        value = obj.get(key)

        if value not in (
            None,
            "",
        ):
            return str(value).strip()

    return ""


# ============================================================
# Query Context
# ============================================================

def extract_query_context(
    data: Any,
) -> Dict[str, str]:
    if not isinstance(
        data,
        dict,
    ):
        return {}

    site = data.get(
        "site",
        {},
    )

    if not isinstance(
        site,
        dict,
    ):
        site = {}

    query_context = data.get(
        "query_context",
        {},
    )

    if not isinstance(
        query_context,
        dict,
    ):
        query_context = {}

    site_id = (
        first_nonempty(
            site,
            [
                "site_id",
                "id",
            ],
        )
        or first_nonempty(
            data,
            [
                "site_id",
            ],
        )
    )

    address = (
        first_nonempty(
            site,
            [
                "address",
                "주소",
            ],
        )
        or first_nonempty(
            query_context,
            [
                "address",
            ],
        )
        or first_nonempty(
            data,
            [
                "address",
            ],
        )
    )

    pnu = (
        first_nonempty(
            query_context,
            [
                "pnu",
                "PNU",
            ],
        )
        or first_nonempty(
            site,
            [
                "pnu",
                "PNU",
            ],
        )
        or first_nonempty(
            data,
            [
                "pnu",
                "PNU",
            ],
        )
    )

    parcel_key = (
        first_nonempty(
            query_context,
            [
                "parcel_key",
            ],
        )
        or first_nonempty(
            site,
            [
                "parcel_key",
            ],
        )
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": pnu,
        "parcel_key": parcel_key,
    }


# ============================================================
# 주소 좌표
# ============================================================

def query_address(
    api_key: str,
    address: str,
) -> Dict[str, Any]:

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
        "key": api_key,
    }

    try:
        response = requests.get(
            VWORLD_SEARCH_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            body = response.json()
        except Exception:
            body = None

        return {
            "http_status":
                response.status_code,

            "json":
                body,

            "text":
                response.text,
        }

    except requests.RequestException as exc:
        return {
            "http_status": None,
            "json": None,
            "text": "",
            "exception": str(exc),
        }


def extract_coordinate(
    result: Dict[str, Any],
) -> Optional[
    Tuple[
        float,
        float,
    ]
]:

    data = result.get("json")

    if not isinstance(
        data,
        dict,
    ):
        return None

    response = data.get(
        "response",
        {},
    )

    if not isinstance(
        response,
        dict,
    ):
        return None

    if response.get("status") != "OK":
        return None

    result_obj = response.get(
        "result",
        {},
    )

    if not isinstance(
        result_obj,
        dict,
    ):
        return None

    items = result_obj.get(
        "items",
        [],
    )

    if (
        not isinstance(items, list)
        or not items
    ):
        return None

    point = items[0].get(
        "point",
        {},
    )

    try:
        return (
            float(point["x"]),
            float(point["y"]),
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# VWorld Data API
# ============================================================

def query_district_unit_plan(
    api_key: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "version": "2.0",

        "data": DATASET,
        "key": api_key,

        "geometry": "true",
        "attribute": "true",

        "size": 100,
        "page": 1,

        "format": "json",
        "crs": "EPSG:4326",

        "geomFilter":
            f"POINT({x} {y})",
    }

    try:
        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            body = response.json()
        except Exception:
            body = None

        return {
            "http_status":
                response.status_code,

            "content_type":
                response.headers.get(
                    "Content-Type",
                    "",
                ),

            "json":
                body,

            "text":
                response.text,

            "url":
                response.url,
        }

    except requests.RequestException as exc:
        return {
            "http_status": None,
            "content_type": "",
            "json": None,
            "text": "",
            "url": "",
            "exception": str(exc),
        }


# ============================================================
# VWorld Response 분석
# ============================================================

def extract_response_status(
    data: Any,
) -> Tuple[
    str,
    str,
    str,
]:

    if not isinstance(
        data,
        dict,
    ):
        return (
            "",
            "",
            "",
        )

    response = data.get(
        "response",
        {},
    )

    if not isinstance(
        response,
        dict,
    ):
        return (
            "",
            "",
            "",
        )

    status = str(
        response.get(
            "status",
            "",
        )
    )

    error = response.get(
        "error",
        {},
    )

    if not isinstance(
        error,
        dict,
    ):
        error = {}

    return (
        status,
        str(
            error.get(
                "code",
                "",
            )
        ),
        str(
            error.get(
                "text",
                "",
            )
        ),
    )


def recursive_find_feature_collections(
    obj: Any,
) -> List[
    Dict[str, Any]
]:
    """
    VWorld 응답 내부에서 FeatureCollection 구조를
    특정 경로에 의존하지 않고 찾는다.
    """

    found: List[
        Dict[str, Any]
    ] = []

    if isinstance(
        obj,
        dict,
    ):

        if (
            obj.get("type")
            == "FeatureCollection"
            and isinstance(
                obj.get("features"),
                list,
            )
        ):
            found.append(obj)

        for value in obj.values():
            found.extend(
                recursive_find_feature_collections(
                    value
                )
            )

    elif isinstance(
        obj,
        list,
    ):
        for value in obj:
            found.extend(
                recursive_find_feature_collections(
                    value
                )
            )

    return found


def collect_features(
    data: Any,
) -> List[
    Dict[str, Any]
]:

    collections = (
        recursive_find_feature_collections(
            data
        )
    )

    features: List[
        Dict[str, Any]
    ] = []

    seen = set()

    for collection in collections:
        for feature in collection.get(
            "features",
            [],
        ):
            if not isinstance(
                feature,
                dict,
            ):
                continue

            key = json.dumps(
                feature,
                ensure_ascii=False,
                sort_keys=True,
            )

            if key in seen:
                continue

            seen.add(key)
            features.append(feature)

    return features


# ============================================================
# Geometry
# ============================================================

def point_on_segment(
    px: float,
    py: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    epsilon: float = 1e-12,
) -> bool:

    cross = (
        (px - x1)
        * (y2 - y1)
        -
        (py - y1)
        * (x2 - x1)
    )

    if abs(cross) > epsilon:
        return False

    dot = (
        (px - x1)
        * (px - x2)
        +
        (py - y1)
        * (py - y2)
    )

    return dot <= epsilon


def point_in_ring(
    x: float,
    y: float,
    ring: List[Any],
) -> bool:

    if len(ring) < 3:
        return False

    inside = False

    count = len(ring)

    for i in range(count):

        p1 = ring[i]
        p2 = ring[
            (i + 1)
            % count
        ]

        if (
            not isinstance(
                p1,
                (list, tuple),
            )
            or
            not isinstance(
                p2,
                (list, tuple),
            )
            or len(p1) < 2
            or len(p2) < 2
        ):
            continue

        try:
            x1 = float(p1[0])
            y1 = float(p1[1])

            x2 = float(p2[0])
            y2 = float(p2[1])

        except (
            TypeError,
            ValueError,
        ):
            continue

        # 경계 위도 포함으로 간주
        if point_on_segment(
            x,
            y,
            x1,
            y1,
            x2,
            y2,
        ):
            return True

        intersects = (
            (y1 > y)
            !=
            (y2 > y)
        )

        if intersects:
            try:
                cross_x = (
                    (x2 - x1)
                    * (y - y1)
                    /
                    (y2 - y1)
                    +
                    x1
                )
            except ZeroDivisionError:
                continue

            if x < cross_x:
                inside = not inside

    return inside


def point_in_polygon_coordinates(
    x: float,
    y: float,
    coordinates: Any,
) -> bool:

    if (
        not isinstance(
            coordinates,
            list,
        )
        or not coordinates
    ):
        return False

    outer_ring = coordinates[0]

    if not point_in_ring(
        x,
        y,
        outer_ring,
    ):
        return False

    # 내부 hole
    for hole in coordinates[1:]:
        if point_in_ring(
            x,
            y,
            hole,
        ):
            return False

    return True


def point_in_geometry(
    x: float,
    y: float,
    geometry: Any,
) -> Optional[bool]:

    if not isinstance(
        geometry,
        dict,
    ):
        return None

    geometry_type = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if geometry_type == "Polygon":
        return (
            point_in_polygon_coordinates(
                x,
                y,
                coordinates,
            )
        )

    if geometry_type == "MultiPolygon":

        if not isinstance(
            coordinates,
            list,
        ):
            return None

        return any(
            point_in_polygon_coordinates(
                x,
                y,
                polygon,
            )
            for polygon in coordinates
        )

    # Point / LineString 등은
    # 지구단위계획 경계 판정에 사용하지 않음
    return None


# ============================================================
# Feature 분석
# ============================================================

def analyze_features(
    features: List[
        Dict[str, Any]
    ],
    x: float,
    y: float,
) -> Dict[str, Any]:

    analyses: List[
        Dict[str, Any]
    ] = []

    geometry_supported = 0
    contains_count = 0

    for index, feature in enumerate(
        features,
        start=1,
    ):

        geometry = feature.get(
            "geometry"
        )

        properties = feature.get(
            "properties"
        )

        if not isinstance(
            properties,
            dict,
        ):
            properties = {}

        contains = point_in_geometry(
            x=x,
            y=y,
            geometry=geometry,
        )

        if contains is not None:
            geometry_supported += 1

        if contains is True:
            contains_count += 1

        geometry_type = ""

        if isinstance(
            geometry,
            dict,
        ):
            geometry_type = str(
                geometry.get(
                    "type",
                    "",
                )
            )

        analyses.append(
            {
                "index": index,

                "feature_id":
                    feature.get(
                        "id"
                    ),

                "geometry_type":
                    geometry_type,

                "point_inside":
                    contains,

                "properties":
                    properties,
            }
        )

    return {
        "feature_count":
            len(features),

        "supported_geometry_count":
            geometry_supported,

        "point_inside_count":
            contains_count,

        "features":
            analyses,
    }


# ============================================================
# Resolution
# ============================================================

def resolve_condition(
    api_status: str,
    features: List[
        Dict[str, Any]
    ],
    analysis: Dict[str, Any],
) -> Dict[str, str]:

    # API 자체 실패
    if api_status != "OK":
        return {
            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "VWorld Data API 조회가 "
                    "정상 완료되지 않았으므로 "
                    "지구단위계획 TRUE/FALSE를 "
                    "확정하지 않음"
                ),
        }

    feature_count = len(
        features
    )

    supported_geometry_count = (
        analysis.get(
            "supported_geometry_count",
            0,
        )
    )

    point_inside_count = (
        analysis.get(
            "point_inside_count",
            0,
        )
    )

    # point filter에서 feature가 실제 반환되고
    # geometry 내부 포함까지 재검증
    if point_inside_count > 0:
        return {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "TRUE",

            "confidence":
                "HIGH",

            "reason":
                (
                    "VWorld 지구단위계획 "
                    "LT_C_UPISUQ161 공간조회에서 "
                    "대상 SITE 대표좌표를 포함하는 "
                    "Polygon/MultiPolygon Feature가 "
                    "확인됨"
                ),
        }

    # 정상 조회인데 feature 0건
    if feature_count == 0:
        return {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "FALSE",

            "confidence":
                "MEDIUM",

            "reason":
                (
                    "VWorld 지구단위계획 공간조회는 "
                    "정상 완료되었으나 대상 좌표에서 "
                    "Feature가 반환되지 않음. "
                    "다만 필지 polygon 교차 검증 전이므로 "
                    "최종 신뢰도는 MEDIUM"
                ),
        }

    # Feature는 있는데 지원 geometry가 없음
    if supported_geometry_count == 0:
        return {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "Feature는 반환되었으나 "
                    "Polygon/MultiPolygon geometry를 "
                    "해석하지 못해 공간포함 여부를 "
                    "확정할 수 없음"
                ),
        }

    # Feature는 있는데 point가 내부가 아님
    return {
        "query_status":
            "QUERY_SUCCESS",

        "resolution":
            "UNKNOWN",

        "confidence":
            "LOW",

        "reason":
            (
                "Feature는 반환되었으나 "
                "클라이언트 geometry 재검증에서는 "
                "대상 대표좌표 포함이 확인되지 않음. "
                "좌표계 또는 geometry 구조 추가 확인 필요"
            ),
    }


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2B-2 "
        "VWorld 지구단위계획 Feature / Geometry 분석 테스트 ==="
    )

    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )

    print()

    print(
        "Dataset Probe 입력:"
    )
    print(
        PROBE_PATH
    )

    print()

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"Query Context 파일이 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    if not PROBE_PATH.exists():
        raise FileNotFoundError(
            f"Dataset Probe 파일이 없습니다: "
            f"{PROBE_PATH}"
        )

    load_dotenv(
        ENV_PATH
    )

    api_key = (
        os.getenv(
            "VWORLD_API_KEY",
            "",
        )
        .strip()
    )

    query_context_data = load_json(
        QUERY_CONTEXT_PATH
    )

    probe_data = load_json(
        PROBE_PATH
    )

    context = extract_query_context(
        query_context_data
    )

    successful_datasets = (
        probe_data.get(
            "successful_datasets",
            [],
        )
        if isinstance(
            probe_data,
            dict,
        )
        else []
    )

    dataset_verified = (
        DATASET
        in successful_datasets
    )

    address = context.get(
        "address",
        ""
    )

    pnu = context.get(
        "pnu",
        ""
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 대상 SITE ==="
    )
    print_separator()

    print(
        "SITE ID:",
        context.get(
            "site_id"
        )
        or "-"
    )

    print(
        "주소:",
        address
        or "-"
    )

    print(
        "PNU:",
        pnu
        or "-"
    )

    print(
        "dataset:",
        DATASET
    )

    print(
        "dataset probe 검증:",
        "PASS"
        if dataset_verified
        else "FAIL"
    )

    print()

    # --------------------------------------------------------
    # 좌표
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 대표 좌표 확보 ==="
    )
    print_separator()

    address_result = query_address(
        api_key=api_key,
        address=address,
    )

    coordinate = extract_coordinate(
        address_result
    )

    print(
        "HTTP 상태:",
        address_result.get(
            "http_status"
        )
    )

    if coordinate:
        print(
            "X:",
            coordinate[0]
        )
        print(
            "Y:",
            coordinate[1]
        )

    else:
        print(
            "좌표 획득 실패"
        )

    print()

    if coordinate is None:
        raise RuntimeError(
            "대표좌표를 확보하지 못했습니다."
        )

    x, y = coordinate

    # --------------------------------------------------------
    # 실제 Data API
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. 지구단위계획 Feature 조회 ==="
    )
    print_separator()

    data_result = query_district_unit_plan(
        api_key=api_key,
        x=x,
        y=y,
    )

    body = data_result.get(
        "json"
    )

    (
        vworld_status,
        error_code,
        error_text,
    ) = extract_response_status(
        body
    )

    print(
        "HTTP 상태:",
        data_result.get(
            "http_status"
        )
    )

    print(
        "Content-Type:",
        data_result.get(
            "content_type"
        )
    )

    print(
        "VWorld status:",
        vworld_status
        or "-"
    )

    if error_code:
        print(
            "error code:",
            error_code
        )

    if error_text:
        print(
            "error text:",
            error_text
        )

    print()

    # --------------------------------------------------------
    # FeatureCollection
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 3. FeatureCollection 구조 분석 ==="
    )
    print_separator()

    collections = (
        recursive_find_feature_collections(
            body
        )
    )

    features = collect_features(
        body
    )

    print(
        "FeatureCollection 수:",
        len(collections)
    )

    print(
        "Feature 수:",
        len(features)
    )

    print()

    # --------------------------------------------------------
    # Geometry 분석
    # --------------------------------------------------------

    analysis = analyze_features(
        features=features,
        x=x,
        y=y,
    )

    print_separator()
    print(
        "=== 4. Geometry 포함 판정 ==="
    )
    print_separator()

    print(
        "Polygon/MultiPolygon 해석 가능:",
        analysis.get(
            "supported_geometry_count",
            0,
        )
    )

    print(
        "대표좌표 포함 Feature:",
        analysis.get(
            "point_inside_count",
            0,
        )
    )

    print()

    for feature in analysis.get(
        "features",
        [],
    ):

        print(
            "-" * 70
        )

        print(
            "Feature:",
            feature.get(
                "index"
            )
        )

        print(
            "ID:",
            feature.get(
                "feature_id"
            )
        )

        print(
            "geometry:",
            feature.get(
                "geometry_type"
            )
            or "-"
        )

        print(
            "point_inside:",
            feature.get(
                "point_inside"
            )
        )

        properties = feature.get(
            "properties",
            {},
        )

        if properties:
            print(
                "properties:"
            )

            for key, value in (
                list(
                    properties.items()
                )[:20]
            ):
                print(
                    f"  {key}: "
                    f"{short_text(value, 200)}"
                )

        print()

    # --------------------------------------------------------
    # Resolution
    # --------------------------------------------------------

    resolution = resolve_condition(
        api_status=vworld_status,
        features=features,
        analysis=analysis,
    )

    print_separator()
    print(
        "=== 5. 지구단위계획 공간조건 판정 ==="
    )
    print_separator()

    print(
        "query_status:",
        resolution[
            "query_status"
        ]
    )

    print(
        "resolution:",
        resolution[
            "resolution"
        ]
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ]
    )

    print(
        "reason:",
        resolution[
            "reason"
        ]
    )

    print()

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = {
        "VWORLD API Key 존재":
            bool(api_key),

        "검증된 dataset 사용":
            dataset_verified,

        "SITE 주소 존재":
            bool(address),

        "PNU 19자리":
            (
                len(pnu) == 19
                and pnu.isdigit()
            ),

        "대표 좌표 획득":
            coordinate is not None,

        "Data API HTTP 200":
            (
                data_result.get(
                    "http_status"
                )
                == 200
            ),

        "VWorld Data API 정상 응답":
            (
                vworld_status
                == "OK"
            ),

        "resolution 허용값":
            (
                resolution[
                    "resolution"
                ]
                in {
                    "TRUE",
                    "FALSE",
                    "UNKNOWN",
                }
            ),

        "query_status 허용값":
            (
                resolution[
                    "query_status"
                ]
                in {
                    "QUERY_SUCCESS",
                    "QUERY_FAILED",
                }
            ),

        "API 실패 시 TRUE/FALSE 금지":
            (
                vworld_status
                == "OK"
                or
                resolution[
                    "resolution"
                ]
                == "UNKNOWN"
            ),
    }

    print_separator()
    print(
        "=== C-9-2-2B-2 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output_data = {
        "step":
            "STEP 17-21-C-9-2-2B-2",

        "site":
            context,

        "dataset":
            DATASET,

        "dataset_verified":
            dataset_verified,

        "coordinate": {
            "x": x,
            "y": y,
            "crs": "EPSG:4326",
            "source":
                "VWorld address search",
        },

        "api": {
            "http_status":
                data_result.get(
                    "http_status"
                ),

            "vworld_status":
                vworld_status,

            "error_code":
                error_code,

            "error_text":
                error_text,
        },

        "feature_collection_count":
            len(collections),

        "feature_count":
            len(features),

        "geometry_analysis":
            analysis,

        "resolution":
            resolution,

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print_separator()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_separator()

    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-2B-2 완료"
        )

        print()

        print(
            "현재 지구단위계획 판정:"
        )

        print(
            resolution[
                "resolution"
            ]
        )

        print()

        if (
            resolution[
                "resolution"
            ]
            == "TRUE"
        ):

            print(
                "대표좌표가 실제 지구단위계획 "
                "geometry 내부에 포함되었습니다."
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-2B-3"
            )

            print(
                "→ 필지 polygon 확보"
            )

            print(
                "→ 지구단위계획 polygon과 "
                "parcel intersection 재검증"
            )

            print(
                "→ 지구단위계획 TRUE 최종 확정"
            )

        elif (
            resolution[
                "resolution"
            ]
            == "FALSE"
        ):

            print(
                "정상 조회에서 대상 point에 "
                "지구단위계획 Feature가 없었습니다."
            )

            print()

            print(
                "다만 필지 polygon 교차검증 전이므로 "
                "FALSE는 아직 최종 확정하지 않습니다."
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-2B-3"
            )

        else:

            print(
                "현재 응답만으로 공간포함 여부를 "
                "확정할 수 없습니다."
            )

            print()

            print(
                "Feature / geometry 구조를 로그로 "
                "추가 분석해야 합니다."
            )

    else:

        print(
            "STEP 17-21-C-9-2-2B-2 검증 미완료"
        )

        print()

        print(
            "FAIL 항목을 먼저 확인합니다."
        )

        print(
            "지구단위계획은 UNKNOWN을 유지합니다."
        )


if __name__ == "__main__":
    main()