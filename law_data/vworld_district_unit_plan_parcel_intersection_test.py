import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv

try:
    from shapely.geometry import shape, Point
    from shapely.geometry.base import BaseGeometry

except ImportError as exc:
    raise ImportError(
        "shapely가 필요합니다. "
        "pip install shapely 로 설치해 주세요."
    ) from exc


# ============================================================
# STEP 17-21-C-9-2-2B-3B-1
#
# Parcel Polygon × 지구단위계획 Polygon 교차검증
#
# 핵심 보정
# ------------------------------------------------------------
# 1. Parcel dataset은 B-3A에서 검증한
#    LP_PA_CBND_BUBUN 사용
#
# 2. Parcel 조회 시 attrFilter(pnu:=...)를 사용하지 않음
#
# 3. B-3A에서 실제 성공한 방식 유지
#
#       주소검색
#          ↓
#       대표좌표
#          ↓
#       geomFilter=POINT(x y)
#          ↓
#       반환 Feature
#          ↓
#       Feature PNU == SITE PNU 직접 검증
#
# 4. PNU가 직접 일치하는 Polygon/MultiPolygon만
#    대상 Parcel geometry로 인정
#
# 5. 지구단위계획 geometry 재조회
#
# 6. Parcel × District intersection 수행
#
# 7. 실제 교차면적 > 0인 경우에만 TRUE
#
# 8. API 실패 / geometry 확보 실패 시 UNKNOWN
#
# 9. 정상 조회 + 교차 없음이 명확한 경우에만 FALSE
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

PARCEL_PROBE_PATH = (
    BASE_DIR
    / "output"
    / "vworld_parcel_polygon_identifier_probe.json"
)

DISTRICT_GEOMETRY_PATH = (
    BASE_DIR
    / "output"
    / "vworld_district_unit_plan_geometry_test.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "vworld_district_unit_plan_parcel_intersection_test.json"
)


VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)


DEFAULT_PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)

DEFAULT_DISTRICT_DATASET = (
    "LT_C_UPISUQ161"
)


# ============================================================
# 공통 유틸
# ============================================================

def load_json(
    path: Path,
) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(
            f
        )


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


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:

    print(
        char * width
    )


# ============================================================
# Query Context 추출
# ============================================================

def extract_query_context(
    data: Dict[str, Any],
) -> Dict[str, Any]:

    site = safe_dict(
        data.get(
            "site"
        )
    )

    query = safe_dict(
        data.get(
            "query_context"
        )
    )

    # 구조 변경 가능성 대응
    address = (
        normalize_text(
            site.get(
                "address"
            )
        )
        or normalize_text(
            data.get(
                "address"
            )
        )
        or normalize_text(
            query.get(
                "address"
            )
        )
    )

    pnu = (
        normalize_text(
            query.get(
                "pnu"
            )
        )
        or normalize_text(
            data.get(
                "pnu"
            )
        )
    )

    site_id = (
        normalize_text(
            site.get(
                "site_id"
            )
        )
        or normalize_text(
            data.get(
                "site_id"
            )
        )
        or normalize_text(
            query.get(
                "parcel_key"
            )
        )
    )

    zone = (
        normalize_text(
            site.get(
                "zone"
            )
        )
        or normalize_text(
            data.get(
                "zone"
            )
        )
    )

    return {
        "site_id":
            site_id,

        "address":
            address,

        "zone":
            zone,

        "pnu":
            pnu,
    }


# ============================================================
# Probe 결과에서 Dataset 추출
# ============================================================

def extract_parcel_dataset(
    data: Dict[str, Any],
) -> str:

    candidates = [
        data.get(
            "selected_dataset"
        ),
        data.get(
            "best_dataset"
        ),
        data.get(
            "dataset"
        ),
    ]

    result = safe_dict(
        data.get(
            "result"
        )
    )

    candidates.extend(
        [
            result.get(
                "selected_dataset"
            ),
            result.get(
                "best_dataset"
            ),
            result.get(
                "dataset"
            ),
        ]
    )

    for value in candidates:

        text = normalize_text(
            value
        )

        if text:
            return text

    # probe candidates 안에서
    # parcel polygon 후보를 다시 찾는다.
    for item in safe_list(
        data.get(
            "candidates"
        )
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        dataset = normalize_text(
            item.get(
                "dataset"
            )
        )

        if (
            dataset
            and (
                item.get(
                    "parcel_polygon_candidate"
                ) is True
                or item.get(
                    "pnu_direct_verified"
                ) is True
                or item.get(
                    "pnu_match"
                ) is True
            )
        ):
            return dataset

    return (
        DEFAULT_PARCEL_DATASET
    )


def extract_district_dataset(
    data: Dict[str, Any],
) -> str:

    candidates = [
        data.get(
            "dataset"
        ),
        data.get(
            "selected_dataset"
        ),
    ]

    result = safe_dict(
        data.get(
            "result"
        )
    )

    candidates.extend(
        [
            result.get(
                "dataset"
            ),
            result.get(
                "selected_dataset"
            ),
        ]
    )

    for value in candidates:

        text = normalize_text(
            value
        )

        if text:
            return text

    return (
        DEFAULT_DISTRICT_DATASET
    )


# ============================================================
# VWorld 응답 유틸
# ============================================================

def get_status(
    data: Any,
) -> str:

    if not isinstance(
        data,
        dict,
    ):
        return ""

    response = safe_dict(
        data.get(
            "response"
        )
    )

    return normalize_text(
        response.get(
            "status"
        )
    ).upper()


def get_error(
    data: Any,
) -> Dict[str, Any]:

    if not isinstance(
        data,
        dict,
    ):
        return {}

    response = safe_dict(
        data.get(
            "response"
        )
    )

    return safe_dict(
        response.get(
            "error"
        )
    )


def request_json(
    params: Dict[str, Any],
) -> Tuple[
    Optional[requests.Response],
    Optional[Dict[str, Any]],
    Optional[str],
]:

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=30,
        )

    except requests.RequestException as exc:

        return (
            None,
            None,
            str(
                exc
            ),
        )

    try:

        data = response.json()

    except ValueError:

        return (
            response,
            None,
            "JSON 파싱 실패",
        )

    return (
        response,
        data,
        None,
    )


# ============================================================
# FeatureCollection 수집
# ============================================================

def collect_features(
    data: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(
        data,
        dict,
    ):
        return []

    response = safe_dict(
        data.get(
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

    # 일반 FeatureCollection
    if isinstance(
        feature_collection,
        dict,
    ):

        features = feature_collection.get(
            "features"
        )

        if isinstance(
            features,
            list,
        ):

            return [
                feature
                for feature in features
                if isinstance(
                    feature,
                    dict,
                )
            ]

    # 혹시 featureCollection 배열
    if isinstance(
        feature_collection,
        list,
    ):

        found = []

        for collection in feature_collection:

            if not isinstance(
                collection,
                dict,
            ):
                continue

            features = collection.get(
                "features"
            )

            if not isinstance(
                features,
                list,
            ):
                continue

            found.extend(
                feature
                for feature in features
                if isinstance(
                    feature,
                    dict,
                )
            )

        return found

    # 일부 응답 구조 대응
    features = result.get(
        "features"
    )

    if isinstance(
        features,
        list,
    ):

        return [
            feature
            for feature in features
            if isinstance(
                feature,
                dict,
            )
        ]

    return []


# ============================================================
# 주소 → 대표좌표
# ============================================================

def query_address_point(
    api_key: str,
    address: str,
) -> Dict[str, Any]:

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
            api_key,
    }

    try:

        response = requests.get(
            VWORLD_SEARCH_URL,
            params=params,
            timeout=30,
        )

    except requests.RequestException as exc:

        return {
            "http_status":
                None,

            "status":
                "",

            "x":
                None,

            "y":
                None,

            "error":
                str(
                    exc
                ),

            "raw":
                None,
        }

    try:

        data = response.json()

    except ValueError:

        return {
            "http_status":
                response.status_code,

            "status":
                "",

            "x":
                None,

            "y":
                None,

            "error":
                "JSON 파싱 실패",

            "raw":
                None,
        }

    response_obj = safe_dict(
        data.get(
            "response"
        )
    )

    status = normalize_text(
        response_obj.get(
            "status"
        )
    ).upper()

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

    x = None
    y = None

    if items:

        first = safe_dict(
            items[0]
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

            x = None
            y = None

    return {
        "http_status":
            response.status_code,

        "status":
            status,

        "x":
            x,

        "y":
            y,

        "error":
            None,

        "raw":
            data,
    }


# ============================================================
# Feature PNU
# ============================================================

PNU_PROPERTY_KEYS = [
    "pnu",
    "PNU",
    "pnu_cd",
    "pnu_code",
    "parcel_pnu",
]


def feature_pnu(
    feature: Dict[str, Any],
) -> str:

    properties = safe_dict(
        feature.get(
            "properties"
        )
    )

    for key in PNU_PROPERTY_KEYS:

        value = normalize_text(
            properties.get(
                key
            )
        )

        if value:
            return value

    return ""


# ============================================================
# GeoJSON → Shapely
# ============================================================

def feature_to_geometry(
    feature: Dict[str, Any],
) -> Optional[BaseGeometry]:

    geometry = feature.get(
        "geometry"
    )

    if not isinstance(
        geometry,
        dict,
    ):
        return None

    geometry_type = normalize_text(
        geometry.get(
            "type"
        )
    )

    if geometry_type not in {
        "Polygon",
        "MultiPolygon",
    }:
        return None

    try:

        geom = shape(
            geometry
        )

    except Exception:
        return None

    if geom.is_empty:
        return None

    if not geom.is_valid:

        try:
            geom = geom.buffer(
                0
            )

        except Exception:
            return None

    if geom.is_empty:
        return None

    return geom


# ============================================================
# Parcel 조회
# ============================================================

def query_parcel(
    api_key: str,
    dataset: str,
    pnu: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service":
            "data",

        "request":
            "GetFeature",

        "data":
            dataset,

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

        # ----------------------------------------------
        # 중요:
        # B-3A 성공 방식 그대로 사용
        # ----------------------------------------------
        "geomFilter":
            f"POINT({x} {y})",

        "size":
            100,

        "page":
            1,
    }

    response, data, transport_error = (
        request_json(
            params
        )
    )

    features = collect_features(
        data
    )

    matched_features = []

    for feature in features:

        if (
            feature_pnu(
                feature
            )
            == pnu
        ):

            matched_features.append(
                feature
            )

    return {
        "http_status":
            (
                response.status_code
                if response is not None
                else None
            ),

        "status":
            get_status(
                data
            ),

        "error":
            get_error(
                data
            ),

        "transport_error":
            transport_error,

        "features":
            features,

        "pnu_matched_features":
            matched_features,

        "raw":
            data,
    }


# ============================================================
# 지구단위계획 조회
# ============================================================

def query_district_unit_plan(
    api_key: str,
    dataset: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service":
            "data",

        "request":
            "GetFeature",

        "data":
            dataset,

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

    response, data, transport_error = (
        request_json(
            params
        )
    )

    features = collect_features(
        data
    )

    geometry_features = []

    for feature in features:

        geom = feature_to_geometry(
            feature
        )

        if geom is None:
            continue

        geometry_features.append(
            {
                "feature":
                    feature,

                "geometry":
                    geom,
            }
        )

    return {
        "http_status":
            (
                response.status_code
                if response is not None
                else None
            ),

        "status":
            get_status(
                data
            ),

        "error":
            get_error(
                data
            ),

        "transport_error":
            transport_error,

        "features":
            features,

        "geometry_features":
            geometry_features,

        "raw":
            data,
    }


# ============================================================
# 면적/교차 계산
# ============================================================

def compute_intersections(
    parcel_geom: BaseGeometry,
    district_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    results = []

    parcel_area = float(
        parcel_geom.area
    )

    for index, item in enumerate(
        district_items,
        start=1,
    ):

        feature = safe_dict(
            item.get(
                "feature"
            )
        )

        district_geom = item.get(
            "geometry"
        )

        if district_geom is None:
            continue

        try:

            intersects = parcel_geom.intersects(
                district_geom
            )

        except Exception:
            intersects = False

        intersection_geom = None
        intersection_area = 0.0

        if intersects:

            try:

                intersection_geom = parcel_geom.intersection(
                    district_geom
                )

            except Exception:
                intersection_geom = None

        if (
            intersection_geom is not None
            and not intersection_geom.is_empty
        ):

            try:

                intersection_area = float(
                    intersection_geom.area
                )

            except Exception:

                intersection_area = 0.0

        if parcel_area > 0:

            ratio = (
                intersection_area
                / parcel_area
            )

        else:

            ratio = 0.0

        properties = safe_dict(
            feature.get(
                "properties"
            )
        )

        results.append(
            {
                "index":
                    index,

                "feature_id":
                    feature.get(
                        "id"
                    ),

                "district_name":
                    (
                        properties.get(
                            "dgm_nm"
                        )
                        or properties.get(
                            "DGM_NM"
                        )
                        or ""
                    ),

                "geometry_type":
                    (
                        district_geom.geom_type
                        if district_geom is not None
                        else None
                    ),

                "intersects":
                    bool(
                        intersects
                    ),

                "intersection_area_degree2":
                    intersection_area,

                "parcel_area_degree2":
                    parcel_area,

                "intersection_ratio":
                    ratio,
            }
        )

    return results


# ============================================================
# 최종 판정
# ============================================================

def resolve_status(
    parcel_query: Dict[str, Any],
    parcel_geom: Optional[BaseGeometry],
    district_query: Dict[str, Any],
    intersection_results: List[Dict[str, Any]],
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # Parcel API 실패
    # --------------------------------------------------------

    if (
        parcel_query.get(
            "status"
        )
        != "OK"
    ):

        return {
            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "필지 Polygon 공간조회가 정상 완료되지 않아 "
                    "지구단위계획 교차 여부를 확정하지 않음"
                ),
        }

    # --------------------------------------------------------
    # PNU 직접 일치 geometry 확보 실패
    # --------------------------------------------------------

    if parcel_geom is None:

        return {
            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "대표좌표 주변 Parcel Feature 조회는 수행했으나 "
                    "대상 PNU와 직접 일치하는 유효한 "
                    "Polygon/MultiPolygon geometry를 확보하지 못함"
                ),
        }

    # --------------------------------------------------------
    # District API 실패
    # --------------------------------------------------------

    if (
        district_query.get(
            "status"
        )
        != "OK"
    ):

        return {
            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "지구단위계획 공간조회가 정상 완료되지 않아 "
                    "TRUE 또는 FALSE로 판정하지 않음"
                ),
        }

    # --------------------------------------------------------
    # 실제 면적 교차
    # --------------------------------------------------------

    positive = [
        item
        for item in intersection_results
        if (
            item.get(
                "intersects"
            )
            and float(
                item.get(
                    "intersection_area_degree2"
                )
                or 0.0
            )
            > 0.0
        )
    ]

    if positive:

        best_ratio = max(
            float(
                item.get(
                    "intersection_ratio"
                )
                or 0.0
            )
            for item in positive
        )

        return {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "TRUE",

            "confidence":
                "HIGH",

            "reason":
                (
                    "대상 PNU와 직접 일치하는 Parcel Polygon과 "
                    "VWorld 지구단위계획 Polygon 사이에 "
                    "실제 면적 교차가 확인됨"
                ),

            "max_intersection_ratio":
                best_ratio,
        }

    # --------------------------------------------------------
    # District 조회가 정상인데 geometry 자체가 없음
    #
    # 이 경우 POINT query 특성상 완전한 주변 coverage를
    # 보장한다고 단정하기 어렵기 때문에 UNKNOWN 유지
    # --------------------------------------------------------

    if not district_query.get(
        "geometry_features"
    ):

        return {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "UNKNOWN",

            "confidence":
                "LOW",

            "reason":
                (
                    "지구단위계획 API는 정상 응답했으나 "
                    "교차검증 가능한 Polygon/MultiPolygon Feature를 "
                    "확보하지 못해 FALSE로 확정하지 않음"
                ),
        }

    # --------------------------------------------------------
    # geometry까지 정상 확보했으나 parcel과 교차 없음
    # --------------------------------------------------------

    return {
        "query_status":
            "QUERY_SUCCESS",

        "resolution":
            "FALSE",

        "confidence":
            "HIGH",

        "reason":
            (
                "대상 PNU Parcel Polygon과 정상 조회된 "
                "지구단위계획 Polygon/MultiPolygon 사이에 "
                "공간 교차가 확인되지 않음"
            ),
    }


# ============================================================
# 검증
# ============================================================

def run_validations(
    api_key: str,
    context: Dict[str, Any],
    parcel_dataset: str,
    district_dataset: str,
    point_result: Dict[str, Any],
    parcel_query: Dict[str, Any],
    parcel_feature: Optional[Dict[str, Any]],
    parcel_geom: Optional[BaseGeometry],
    district_query: Dict[str, Any],
    final_resolution: Dict[str, Any],
) -> Dict[str, bool]:

    pnu = normalize_text(
        context.get(
            "pnu"
        )
    )

    parcel_pnu = (
        feature_pnu(
            parcel_feature
        )
        if parcel_feature
        else ""
    )

    status = final_resolution.get(
        "resolution"
    )

    query_status = final_resolution.get(
        "query_status"
    )

    return {
        "VWORLD API Key 존재":
            bool(
                api_key
            ),

        "SITE 주소 존재":
            bool(
                context.get(
                    "address"
                )
            ),

        "PNU 19자리":
            (
                len(
                    pnu
                )
                == 19
                and pnu.isdigit()
            ),

        "Parcel dataset 검증값 사용":
            bool(
                parcel_dataset
            ),

        "District dataset 검증값 사용":
            bool(
                district_dataset
            ),

        "대표좌표 획득":
            (
                point_result.get(
                    "status"
                )
                == "OK"
                and point_result.get(
                    "x"
                )
                is not None
                and point_result.get(
                    "y"
                )
                is not None
            ),

        "Parcel API HTTP 200":
            (
                parcel_query.get(
                    "http_status"
                )
                == 200
            ),

        "Parcel PNU 직접 검증":
            (
                parcel_feature is None
                or parcel_pnu
                == pnu
            ),

        "Parcel geometry 검증":
            (
                parcel_geom is None
                or parcel_geom.geom_type
                in {
                    "Polygon",
                    "MultiPolygon",
                }
            ),

        "District API HTTP 200":
            (
                district_query.get(
                    "http_status"
                )
                == 200
            ),

        "resolution 허용값":
            status
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            },

        "query_status 허용값":
            query_status
            in {
                "QUERY_SUCCESS",
                "QUERY_FAILED",
            },

        "API 실패 시 TRUE/FALSE 금지":
            not (
                query_status
                == "QUERY_FAILED"
                and status
                in {
                    "TRUE",
                    "FALSE",
                }
            ),

        "PNU 불일치 Parcel 사용 금지":
            not (
                parcel_feature is not None
                and parcel_pnu
                != pnu
            ),
    }


# ============================================================
# Main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2B-3B-1 "
        "Parcel Polygon × 지구단위계획 Polygon "
        "교차검증 보정 테스트 ==="
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
        "Parcel Probe 입력:"
    )
    print(
        PARCEL_PROBE_PATH
    )
    print()

    print(
        "District Geometry 입력:"
    )
    print(
        DISTRICT_GEOMETRY_PATH
    )
    print()

    # --------------------------------------------------------
    # 파일 검사
    # --------------------------------------------------------

    for path in [
        QUERY_CONTEXT_PATH,
        PARCEL_PROBE_PATH,
        DISTRICT_GEOMETRY_PATH,
    ]:

        if not path.exists():

            raise FileNotFoundError(
                f"입력 파일이 없습니다: {path}"
            )

    context_data = load_json(
        QUERY_CONTEXT_PATH
    )

    parcel_probe_data = load_json(
        PARCEL_PROBE_PATH
    )

    district_geometry_data = load_json(
        DISTRICT_GEOMETRY_PATH
    )

    context = extract_query_context(
        context_data
    )

    parcel_dataset = extract_parcel_dataset(
        parcel_probe_data
    )

    district_dataset = extract_district_dataset(
        district_geometry_data
    )

    # --------------------------------------------------------
    # 환경변수
    # --------------------------------------------------------

    load_dotenv(
        BASE_DIR.parent
        / ".env"
    )

    api_key = normalize_text(
        os.getenv(
            "VWORLD_API_KEY"
        )
    )

    if not api_key:

        raise RuntimeError(
            "VWORLD_API_KEY를 찾을 수 없습니다."
        )

    # --------------------------------------------------------
    # SITE 출력
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
        context.get(
            "address"
        )
        or "-"
    )

    print(
        "용도지역:",
        context.get(
            "zone"
        )
        or "-"
    )

    print(
        "PNU:",
        context.get(
            "pnu"
        )
        or "-"
    )

    print()

    print(
        "Parcel dataset:",
        parcel_dataset
    )

    print(
        "District dataset:",
        district_dataset
    )

    old_resolution = normalize_text(
        district_geometry_data.get(
            "resolution"
        )
    )

    if not old_resolution:

        old_resolution = normalize_text(
            safe_dict(
                district_geometry_data.get(
                    "result"
                )
            ).get(
                "resolution"
            )
        )

    print()
    print(
        "기존 대표점 기준 판정:",
        old_resolution
        or "UNKNOWN"
    )
    print()

    # --------------------------------------------------------
    # 1. 대표좌표
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 대표좌표 재확보 ==="
    )
    print_separator()

    point_result = query_address_point(
        api_key=api_key,
        address=context.get(
            "address",
            "",
        ),
    )

    print(
        "HTTP 상태:",
        point_result.get(
            "http_status"
        ),
    )

    print(
        "VWorld status:",
        point_result.get(
            "status"
        ),
    )

    x = point_result.get(
        "x"
    )

    y = point_result.get(
        "y"
    )

    print(
        "X:",
        x,
    )

    print(
        "Y:",
        y,
    )

    print()

    if (
        point_result.get(
            "status"
        )
        != "OK"
        or x is None
        or y is None
    ):

        output_data = {
            "step":
                "STEP 17-21-C-9-2-2B-3B-1",

            "site":
                context,

            "parcel_dataset":
                parcel_dataset,

            "district_dataset":
                district_dataset,

            "point_query":
                point_result,

            "query_status":
                "QUERY_FAILED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                "대표좌표를 확보하지 못해 공간교차 검증을 수행하지 않음",
        }

        save_json(
            OUTPUT_PATH,
            output_data,
        )

        print(
            "지구단위계획 최종 판정: UNKNOWN"
        )

        print(
            "대표좌표 확보 실패로 "
            "교차검증을 수행하지 않았습니다."
        )

        return

    # --------------------------------------------------------
    # 2. Parcel Polygon
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. 대상 필지 Polygon 공간조회 ==="
    )
    print_separator()

    parcel_query = query_parcel(
        api_key=api_key,
        dataset=parcel_dataset,
        pnu=context.get(
            "pnu",
            "",
        ),
        x=x,
        y=y,
    )

    print(
        "HTTP 상태:",
        parcel_query.get(
            "http_status"
        ),
    )

    print(
        "VWorld status:",
        parcel_query.get(
            "status"
        ),
    )

    if (
        parcel_query.get(
            "status"
        )
        != "OK"
    ):

        error = parcel_query.get(
            "error",
            {},
        )

        print(
            "error code:",
            error.get(
                "code"
            ),
        )

        print(
            "error text:",
            error.get(
                "text"
            ),
        )

    parcel_features = parcel_query.get(
        "features",
        [],
    )

    matched_features = parcel_query.get(
        "pnu_matched_features",
        [],
    )

    print(
        "전체 Feature 수:",
        len(
            parcel_features
        ),
    )

    print(
        "대상 PNU 일치 Feature 수:",
        len(
            matched_features
        ),
    )

    parcel_feature = (
        matched_features[0]
        if matched_features
        else None
    )

    parcel_geom = None

    if parcel_feature is None:

        print(
            "대상 PNU 직접 일치 Feature: 없음"
        )

    else:

        print(
            "대상 PNU 직접 일치 Feature: 확인"
        )

        print(
            "Feature ID:",
            parcel_feature.get(
                "id"
            ),
        )

        print(
            "Feature PNU:",
            feature_pnu(
                parcel_feature
            ),
        )

        parcel_geom = feature_to_geometry(
            parcel_feature
        )

        if parcel_geom is not None:

            print(
                "geometry:",
                parcel_geom.geom_type,
            )

            print(
                "bounds:",
                parcel_geom.bounds,
            )

            representative_point = Point(
                x,
                y,
            )

            try:

                point_inside_parcel = (
                    parcel_geom.contains(
                        representative_point
                    )
                    or parcel_geom.touches(
                        representative_point
                    )
                )

            except Exception:

                point_inside_parcel = False

            print(
                "대표좌표가 Parcel 내부:",
                point_inside_parcel,
            )

        else:

            print(
                "Polygon/MultiPolygon geometry 해석 실패"
            )

    print()

    # --------------------------------------------------------
    # 3. District Polygon
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 3. 지구단위계획 Polygon 재조회 ==="
    )
    print_separator()

    district_query = query_district_unit_plan(
        api_key=api_key,
        dataset=district_dataset,
        x=x,
        y=y,
    )

    print(
        "HTTP 상태:",
        district_query.get(
            "http_status"
        ),
    )

    print(
        "VWorld status:",
        district_query.get(
            "status"
        ),
    )

    if (
        district_query.get(
            "status"
        )
        != "OK"
    ):

        error = district_query.get(
            "error",
            {},
        )

        print(
            "error code:",
            error.get(
                "code"
            ),
        )

        print(
            "error text:",
            error.get(
                "text"
            ),
        )

    district_features = district_query.get(
        "features",
        [],
    )

    district_geometry_features = district_query.get(
        "geometry_features",
        [],
    )

    print(
        "Feature 수:",
        len(
            district_features
        ),
    )

    print(
        "Polygon/MultiPolygon 수:",
        len(
            district_geometry_features
        ),
    )

    for index, item in enumerate(
        district_geometry_features,
        start=1,
    ):

        feature = item.get(
            "feature",
            {},
        )

        geom = item.get(
            "geometry"
        )

        properties = safe_dict(
            feature.get(
                "properties"
            )
        )

        print()
        print(
            f"Feature {index}"
        )

        print(
            "ID:",
            feature.get(
                "id"
            ),
        )

        print(
            "geometry:",
            (
                geom.geom_type
                if geom is not None
                else "-"
            ),
        )

        print(
            "dgm_nm:",
            properties.get(
                "dgm_nm"
            )
            or "-"
        )

    print()

    # --------------------------------------------------------
    # 4. Intersection
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 4. Parcel × 지구단위계획 교차분석 ==="
    )
    print_separator()

    intersection_results = []

    if parcel_geom is None:

        print(
            "Parcel geometry가 없어 "
            "교차분석을 수행하지 않습니다."
        )

    else:

        intersection_results = compute_intersections(
            parcel_geom=parcel_geom,
            district_items=district_geometry_features,
        )

        if not intersection_results:

            print(
                "교차분석 대상 지구단위계획 geometry가 없습니다."
            )

        for result in intersection_results:

            print()
            print(
                f"Feature {result['index']}"
            )

            print(
                "ID:",
                result.get(
                    "feature_id"
                ),
            )

            print(
                "지구명:",
                result.get(
                    "district_name"
                )
                or "-"
            )

            print(
                "intersects:",
                result.get(
                    "intersects"
                ),
            )

            print(
                "교차 면적(degree²):",
                result.get(
                    "intersection_area_degree2"
                ),
            )

            print(
                "필지 면적(degree²):",
                result.get(
                    "parcel_area_degree2"
                ),
            )

            print(
                "교차 비율:",
                result.get(
                    "intersection_ratio"
                ),
            )

    print()

    # --------------------------------------------------------
    # 5. 최종 판정
    # --------------------------------------------------------

    final_resolution = resolve_status(
        parcel_query=parcel_query,
        parcel_geom=parcel_geom,
        district_query=district_query,
        intersection_results=intersection_results,
    )

    print_separator()
    print(
        "=== 5. 지구단위계획 공간조건 최종 판정 ==="
    )
    print_separator()

    print(
        "query_status:",
        final_resolution.get(
            "query_status"
        ),
    )

    print(
        "resolution:",
        final_resolution.get(
            "resolution"
        ),
    )

    print(
        "confidence:",
        final_resolution.get(
            "confidence"
        ),
    )

    print(
        "reason:",
        final_resolution.get(
            "reason"
        ),
    )

    if (
        "max_intersection_ratio"
        in final_resolution
    ):

        print(
            "최대 필지 교차 비율:",
            final_resolution.get(
                "max_intersection_ratio"
            ),
        )

    print()

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = run_validations(
        api_key=api_key,
        context=context,
        parcel_dataset=parcel_dataset,
        district_dataset=district_dataset,
        point_result=point_result,
        parcel_query=parcel_query,
        parcel_feature=parcel_feature,
        parcel_geom=parcel_geom,
        district_query=district_query,
        final_resolution=final_resolution,
    )

    print_separator()
    print(
        "=== C-9-2-2B-3B-1 검증 ==="
    )
    print_separator()

    for name, passed in validations.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    parcel_feature_summary = None

    if parcel_feature:

        parcel_feature_summary = {
            "id":
                parcel_feature.get(
                    "id"
                ),

            "pnu":
                feature_pnu(
                    parcel_feature
                ),

            "geometry_type":
                (
                    parcel_geom.geom_type
                    if parcel_geom is not None
                    else None
                ),

            "bounds":
                (
                    list(
                        parcel_geom.bounds
                    )
                    if parcel_geom is not None
                    else None
                ),
        }

    district_summary = []

    for item in district_geometry_features:

        feature = safe_dict(
            item.get(
                "feature"
            )
        )

        geom = item.get(
            "geometry"
        )

        properties = safe_dict(
            feature.get(
                "properties"
            )
        )

        district_summary.append(
            {
                "id":
                    feature.get(
                        "id"
                    ),

                "geometry_type":
                    (
                        geom.geom_type
                        if geom is not None
                        else None
                    ),

                "dgm_nm":
                    properties.get(
                        "dgm_nm"
                    ),

                "present_sn":
                    properties.get(
                        "present_sn"
                    ),

                "wtnnc_sn":
                    properties.get(
                        "wtnnc_sn"
                    ),

                "ntfc_sn":
                    properties.get(
                        "ntfc_sn"
                    ),
            }
        )

    output_data = {
        "step":
            "STEP 17-21-C-9-2-2B-3B-1",

        "site":
            context,

        "datasets": {
            "parcel":
                parcel_dataset,

            "district_unit_plan":
                district_dataset,
        },

        "representative_point": {
            "x":
                x,

            "y":
                y,
        },

        "parcel_query": {
            "http_status":
                parcel_query.get(
                    "http_status"
                ),

            "vworld_status":
                parcel_query.get(
                    "status"
                ),

            "feature_count":
                len(
                    parcel_features
                ),

            "pnu_match_count":
                len(
                    matched_features
                ),

            "selected_feature":
                parcel_feature_summary,
        },

        "district_query": {
            "http_status":
                district_query.get(
                    "http_status"
                ),

            "vworld_status":
                district_query.get(
                    "status"
                ),

            "feature_count":
                len(
                    district_features
                ),

            "geometry_feature_count":
                len(
                    district_geometry_features
                ),

            "features":
                district_summary,
        },

        "intersection_results":
            intersection_results,

        "query_status":
            final_resolution.get(
                "query_status"
            ),

        "resolution":
            final_resolution.get(
                "resolution"
            ),

        "confidence":
            final_resolution.get(
                "confidence"
            ),

        "reason":
            final_resolution.get(
                "reason"
            ),

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

    if (
        "max_intersection_ratio"
        in final_resolution
    ):

        output_data[
            "max_intersection_ratio"
        ] = final_resolution[
            "max_intersection_ratio"
        ]

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print()
    print_separator()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_separator()
    print()

    # --------------------------------------------------------
    # 종료 메시지
    # --------------------------------------------------------

    if all_pass:

        print(
            "STEP 17-21-C-9-2-2B-3B-1 완료"
        )
        print()

        print(
            "지구단위계획 최종 판정:"
        )

        print(
            final_resolution.get(
                "resolution"
            )
        )

        print()

        if (
            final_resolution.get(
                "resolution"
            )
            == "TRUE"
        ):

            print(
                "대상 PNU Parcel Polygon과 "
                "지구단위계획 Polygon의 실제 면적 교차가 "
                "확인되었습니다."
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-3"
            )

            print(
                "→ 개발진흥지구 실제 공간조회"
            )

            print(
                "→ 동일 Parcel Polygon 기반 교차판정 구조 재사용"
            )

            print(
                "→ 개발밀도관리구역 / 자연경관지구 등 "
                "URBAN_PLANNING_ZONE 조건 순차 확정"
            )

        elif (
            final_resolution.get(
                "resolution"
            )
            == "FALSE"
        ):

            print(
                "정상 조회된 지구단위계획 geometry와 "
                "대상 Parcel Polygon의 교차가 확인되지 않았습니다."
            )

        else:

            print(
                "조회 또는 geometry 검증이 완전하지 않아 "
                "UNKNOWN을 유지합니다."
            )

    else:

        print(
            "STEP 17-21-C-9-2-2B-3B-1 검증 실패"
        )

        print()

        print(
            "FAIL 항목을 먼저 확인한 뒤 "
            "다음 공간조건 조회로 진행합니다."
        )


if __name__ == "__main__":
    main()