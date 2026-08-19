import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-2B-3A
# VWorld 필지 Polygon dataset 식별 / PNU 검증
#
# 목적
# ------------------------------------------------------------
# 1. SITE Query Context에서 주소 / PNU 확보
# 2. VWorld 주소검색으로 대표좌표 확보
# 3. 연속지적도 / 필지 Polygon dataset 후보 실제 조회
# 4. INVALID_RANGE / QUERY_FAILED / QUERY_SUCCESS 구분
# 5. Polygon / MultiPolygon geometry 존재 확인
# 6. Feature property에서 대상 PNU 일치 여부 확인
# 7. 실제 검증된 dataset만 다음 B-3B에 전달
#
# 중요
# ------------------------------------------------------------
# - dataset 이름을 추측만으로 확정하지 않는다.
# - HTTP 200만으로 QUERY_SUCCESS 처리하지 않는다.
# - VWorld response.status == OK 여야 한다.
# - Polygon/MultiPolygon이 있어야 parcel geometry 후보이다.
# - 가능하면 대상 PNU가 property와 직접 일치해야 한다.
# - 실패하더라도 지구단위계획 TRUE/FALSE 판정은 변경하지 않는다.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "vworld_parcel_polygon_identifier_probe.json"
)


# ============================================================
# VWorld API
# ============================================================

VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"


# ============================================================
# Parcel dataset 후보
#
# 여기서는 후보일 뿐이다.
# 실제 API에서 OK 응답 + Polygon geometry를 확인해야 채택한다.
# ============================================================

PARCEL_DATASET_CANDIDATES = [
    "LP_PA_CBND_BUBUN",
    "LP_PA_CBND_BONBUN",
    "LT_C_LANDINFO",
    "LT_C_LANDINFO_1",
    "LT_C_LANDINFO_2",
    "LT_C_LANDINFO_BUBUN",
    "LT_C_LANDINFO_BONBUN",
    "LT_C_PARCEL",
    "LT_C_CADASTRAL",
    "LT_C_JIJUK",
    "LT_C_JIJUK_BUBUN",
    "LT_C_JIJUK_BONBUN",
]


# ============================================================
# 공통
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:
    print(
        char * width
    )


def load_json(
    path: Path,
) -> Any:
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


def safe_dict(
    value: Any,
) -> Dict[str, Any]:
    if isinstance(
        value,
        dict,
    ):
        return value

    return {}


def normalize_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


# ============================================================
# Query Context
# ============================================================

def get_query_context(
    raw: Dict[str, Any],
) -> Dict[str, str]:

    # 이전 단계 구조 변화에도 대응
    site = safe_dict(
        raw.get(
            "site"
        )
    )

    query = safe_dict(
        raw.get(
            "query_context"
        )
    )

    parcel = safe_dict(
        raw.get(
            "parcel"
        )
    )

    def first_value(
        *values: Any,
    ) -> str:
        for value in values:
            text = normalize_text(
                value
            )

            if text:
                return text

        return ""

    return {
        "site_id": first_value(
            raw.get("site_id"),
            site.get("site_id"),
            query.get("site_id"),
            parcel.get("parcel_key"),
        ),
        "address": first_value(
            raw.get("address"),
            site.get("address"),
            query.get("address"),
        ),
        "zone": first_value(
            raw.get("zone"),
            site.get("zone"),
            query.get("zone"),
        ),
        "pnu": first_value(
            raw.get("pnu"),
            site.get("pnu"),
            query.get("pnu"),
            parcel.get("pnu"),
        ),
    }


# ============================================================
# VWorld 인증
# ============================================================

def load_vworld_key() -> str:
    load_dotenv(
        PROJECT_ROOT
        / ".env"
    )

    key = (
        os.getenv(
            "VWORLD_API_KEY"
        )
        or os.getenv(
            "VWORLD_KEY"
        )
        or ""
    ).strip()

    return key


# ============================================================
# HTTP / JSON
# ============================================================

def request_json(
    url: str,
    params: Dict[str, Any],
    timeout: int = 30,
) -> Tuple[
    Optional[requests.Response],
    Optional[Dict[str, Any]],
    Optional[str],
]:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
        )
    except requests.RequestException as exc:
        return (
            None,
            None,
            str(exc),
        )

    try:
        data = response.json()
    except ValueError:
        return (
            response,
            None,
            "JSON 파싱 실패",
        )

    if not isinstance(
        data,
        dict,
    ):
        return (
            response,
            None,
            "JSON 최상위가 object가 아님",
        )

    return (
        response,
        data,
        None,
    )


# ============================================================
# VWorld 응답 구조
# ============================================================

def get_vworld_response(
    data: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    if not data:
        return {}

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
    data: Optional[Dict[str, Any]],
) -> str:
    response = get_vworld_response(
        data
    )

    return normalize_text(
        response.get(
            "status"
        )
    ).upper()


def get_vworld_error(
    data: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    response = get_vworld_response(
        data
    )

    error = safe_dict(
        response.get(
            "error"
        )
    )

    return {
        "level": normalize_text(
            error.get(
                "level"
            )
        ),
        "code": normalize_text(
            error.get(
                "code"
            )
        ),
        "text": normalize_text(
            error.get(
                "text"
            )
        ),
    }


# ============================================================
# 주소검색
# ============================================================

def search_address_point(
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

    response, data, error = request_json(
        VWORLD_SEARCH_URL,
        params,
    )

    result = {
        "http_status": (
            response.status_code
            if response is not None
            else None
        ),
        "content_type": (
            response.headers.get(
                "Content-Type",
                "",
            )
            if response is not None
            else ""
        ),
        "status": get_vworld_status(
            data
        ),
        "x": None,
        "y": None,
        "error": error,
        "raw": data,
    }

    if error:
        return result

    if result[
        "status"
    ] != "OK":
        vworld_error = get_vworld_error(
            data
        )

        result[
            "error"
        ] = (
            vworld_error.get(
                "text"
            )
            or vworld_error.get(
                "code"
            )
            or "VWorld search status != OK"
        )

        return result

    response_obj = get_vworld_response(
        data
    )

    result_obj = safe_dict(
        response_obj.get(
            "result"
        )
    )

    items = result_obj.get(
        "items"
    )

    if not isinstance(
        items,
        list,
    ):
        items = []

    for item in items:
        if not isinstance(
            item,
            dict,
        ):
            continue

        point = safe_dict(
            item.get(
                "point"
            )
        )

        x = point.get(
            "x"
        )

        y = point.get(
            "y"
        )

        try:
            x_float = float(
                x
            )
            y_float = float(
                y
            )
        except (
            TypeError,
            ValueError,
        ):
            continue

        result[
            "x"
        ] = x_float

        result[
            "y"
        ] = y_float

        break

    return result


# ============================================================
# FeatureCollection 추출
# ============================================================

def collect_features(
    data: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    response = get_vworld_response(
        data
    )

    result = response.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        return []

    feature_collection = result.get(
        "featureCollection"
    )

    if not isinstance(
        feature_collection,
        dict,
    ):
        return []

    features = feature_collection.get(
        "features"
    )

    if not isinstance(
        features,
        list,
    ):
        return []

    return [
        feature
        for feature in features
        if isinstance(
            feature,
            dict,
        )
    ]


# ============================================================
# Geometry
# ============================================================

def geometry_type(
    feature: Dict[str, Any],
) -> str:
    geometry = feature.get(
        "geometry"
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
    return geometry_type(
        feature
    ) in {
        "Polygon",
        "MultiPolygon",
    }


# ============================================================
# PNU property 탐색
# ============================================================

PNU_PROPERTY_KEYS = [
    "pnu",
    "PNU",

    "pnu_cd",
    "PNU_CD",

    "pnu_code",
    "PNU_CODE",

    "parcel_pnu",
    "PARCEL_PNU",

    "a1",
]


def normalize_pnu_candidate(
    value: Any,
) -> str:
    text = normalize_text(
        value
    )

    # 숫자가 아닌 문자가 섞여 있을 가능성 방어
    digits = "".join(
        ch
        for ch in text
        if ch.isdigit()
    )

    if len(
        digits
    ) == 19:
        return digits

    return text


def find_feature_pnu(
    feature: Dict[str, Any],
) -> Tuple[
    Optional[str],
    Optional[str],
]:

    properties = feature.get(
        "properties"
    )

    if not isinstance(
        properties,
        dict,
    ):
        return (
            None,
            None,
        )

    # 우선 알려진 PNU key
    for key in PNU_PROPERTY_KEYS:
        if key not in properties:
            continue

        value = normalize_pnu_candidate(
            properties.get(
                key
            )
        )

        if value:
            return (
                key,
                value,
            )

    # 이름에 pnu가 포함된 property 자동 탐색
    for key, raw_value in properties.items():
        if "pnu" not in str(
            key
        ).lower():
            continue

        value = normalize_pnu_candidate(
            raw_value
        )

        if value:
            return (
                str(key),
                value,
            )

    # 마지막으로 19자리 숫자 property 탐색
    for key, raw_value in properties.items():
        value = normalize_pnu_candidate(
            raw_value
        )

        if (
            len(value) == 19
            and value.isdigit()
        ):
            return (
                str(key),
                value,
            )

    return (
        None,
        None,
    )


# ============================================================
# dataset 조회
# ============================================================

def query_dataset_by_point(
    api_key: str,
    dataset: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": dataset,
        "key": api_key,
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

    response, data, transport_error = request_json(
        VWORLD_DATA_URL,
        params,
    )

    http_status = (
        response.status_code
        if response is not None
        else None
    )

    status = get_vworld_status(
        data
    )

    vworld_error = get_vworld_error(
        data
    )

    features = collect_features(
        data
    )

    polygon_features = [
        feature
        for feature in features
        if is_polygon_geometry(
            feature
        )
    ]

    if transport_error:
        classification = (
            "QUERY_FAILED"
        )

    elif http_status != 200:
        classification = (
            "HTTP_ERROR"
        )

    elif (
        status == "ERROR"
        and vworld_error.get(
            "code"
        )
        == "INVALID_RANGE"
    ):
        classification = (
            "INVALID_DATA_IDENTIFIER"
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
        "dataset": dataset,
        "http_status": http_status,
        "content_type": (
            response.headers.get(
                "Content-Type",
                "",
            )
            if response is not None
            else ""
        ),
        "vworld_status": status,
        "classification": classification,
        "transport_error": transport_error,
        "error": vworld_error,
        "feature_count": len(
            features
        ),
        "polygon_feature_count": len(
            polygon_features
        ),
        "features": features,
        "raw": data,
    }


# ============================================================
# Feature 분석
# ============================================================

def analyze_features(
    features: List[Dict[str, Any]],
    target_pnu: str,
) -> Dict[str, Any]:

    analyzed = []

    pnu_matches = []

    polygon_count = 0

    for index, feature in enumerate(
        features,
        start=1,
    ):

        geom_type = geometry_type(
            feature
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

        pnu_key, feature_pnu = (
            find_feature_pnu(
                feature
            )
        )

        pnu_match = (
            bool(target_pnu)
            and bool(feature_pnu)
            and feature_pnu
            == target_pnu
        )

        info = {
            "index": index,
            "id": normalize_text(
                feature.get(
                    "id"
                )
            ),
            "geometry_type": geom_type,
            "is_polygon": polygon,
            "pnu_property_key": pnu_key,
            "feature_pnu": feature_pnu,
            "target_pnu": target_pnu,
            "pnu_match": pnu_match,
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
        "feature_count": len(
            features
        ),
        "polygon_count": polygon_count,
        "pnu_polygon_match_count": len(
            pnu_matches
        ),
        "features": analyzed,
        "pnu_polygon_matches": pnu_matches,
    }


# ============================================================
# dataset 후보 점수
# ============================================================

def dataset_score(
    query: Dict[str, Any],
    analysis: Dict[str, Any],
) -> int:

    if query.get(
        "classification"
    ) != "QUERY_SUCCESS":
        return 0

    score = 10

    if analysis.get(
        "feature_count",
        0,
    ) > 0:
        score += 20

    if analysis.get(
        "polygon_count",
        0,
    ) > 0:
        score += 30

    if analysis.get(
        "pnu_polygon_match_count",
        0,
    ) > 0:
        score += 100

    return score


# ============================================================
# 검증
# ============================================================

def run_validations(
    api_key: str,
    context: Dict[str, str],
    address_result: Dict[str, Any],
    probe_results: List[Dict[str, Any]],
    selected_dataset: Optional[str],
) -> Dict[str, bool]:

    valid_pnu = (
        len(
            context.get(
                "pnu",
                "",
            )
        )
        == 19
        and context.get(
            "pnu",
            "",
        ).isdigit()
    )

    all_classified = all(
        result.get(
            "classification"
        )
        in {
            "QUERY_SUCCESS",
            "QUERY_FAILED",
            "HTTP_ERROR",
            "INVALID_DATA_IDENTIFIER",
        }
        for result in probe_results
    )

    success_does_not_mean_polygon = all(
        not (
            result.get(
                "classification"
            )
            == "QUERY_SUCCESS"
            and result.get(
                "usable_as_parcel_polygon"
            )
            and result.get(
                "analysis",
                {},
            ).get(
                "polygon_count",
                0,
            )
            == 0
        )
        for result in probe_results
    )

    selected_is_verified = True

    if selected_dataset:
        selected = next(
            (
                result
                for result in probe_results
                if result.get(
                    "dataset"
                )
                == selected_dataset
            ),
            None,
        )

        selected_is_verified = bool(
            selected
            and selected.get(
                "classification"
            )
            == "QUERY_SUCCESS"
            and selected.get(
                "analysis",
                {},
            ).get(
                "polygon_count",
                0,
            )
            > 0
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
            valid_pnu,

        "대표 좌표 획득":
            (
                address_result.get(
                    "x"
                )
                is not None
                and address_result.get(
                    "y"
                )
                is not None
            ),

        "후보 전체 조회 실행":
            (
                len(
                    probe_results
                )
                == len(
                    PARCEL_DATASET_CANDIDATES
                )
            ),

        "각 후보 응답 분류 완료":
            all_classified,

        "QUERY_SUCCESS만으로 parcel 확정하지 않음":
            success_does_not_mean_polygon,

        "선택 dataset geometry 검증":
            selected_is_verified,
    }


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2B-3A "
        "VWorld 필지 Polygon dataset 식별 / PNU 검증 ==="
    )
    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )
    print()

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            f"Query Context 파일이 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    raw_context = load_json(
        QUERY_CONTEXT_PATH
    )

    if not isinstance(
        raw_context,
        dict,
    ):
        raise ValueError(
            "Query Context JSON 최상위 구조가 object가 아닙니다."
        )

    context = get_query_context(
        raw_context
    )

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
        or "-",
    )

    print(
        "주소:",
        context.get(
            "address"
        )
        or "-",
    )

    print(
        "용도지역:",
        context.get(
            "zone"
        )
        or "-",
    )

    print(
        "PNU:",
        context.get(
            "pnu"
        )
        or "-",
    )

    print()

    api_key = load_vworld_key()

    print_separator()
    print(
        "=== VWorld 인증 ==="
    )
    print_separator()

    if api_key:
        print(
            "VWORLD_API_KEY: 정상적으로 읽었습니다."
        )
    else:
        print(
            "VWORLD_API_KEY: 찾을 수 없습니다."
        )

    print()

    if not api_key:
        raise RuntimeError(
            "VWORLD_API_KEY가 없습니다."
        )

    address = context.get(
        "address",
        ""
    )

    if not address:
        raise ValueError(
            "SITE 주소가 없습니다."
        )

    target_pnu = context.get(
        "pnu",
        ""
    )

    if (
        len(
            target_pnu
        )
        != 19
        or not target_pnu.isdigit()
    ):
        raise ValueError(
            f"PNU가 올바르지 않습니다: "
            f"{target_pnu}"
        )

    # ========================================================
    # 1. 대표좌표
    # ========================================================

    print_separator()
    print(
        "=== 1. 대표 좌표 확보 ==="
    )
    print_separator()

    address_result = search_address_point(
        api_key=api_key,
        address=address,
    )

    print(
        "HTTP 상태:",
        address_result.get(
            "http_status"
        ),
    )

    print(
        "VWorld status:",
        address_result.get(
            "status"
        )
        or "-",
    )

    x = address_result.get(
        "x"
    )

    y = address_result.get(
        "y"
    )

    if (
        x is not None
        and y is not None
    ):
        print(
            "X:",
            x,
        )

        print(
            "Y:",
            y,
        )
    else:
        print(
            "좌표 획득 실패"
        )

        print(
            "error:",
            address_result.get(
                "error"
            )
            or "-",
        )

    print()

    if (
        x is None
        or y is None
    ):
        raise RuntimeError(
            "대표좌표를 확보하지 못했습니다."
        )

    # ========================================================
    # 2. Dataset Probe
    # ========================================================

    print_separator()
    print(
        "=== 2. Parcel Polygon Data API 식별자 탐색 ==="
    )
    print_separator()

    print(
        "후보 수:",
        len(
            PARCEL_DATASET_CANDIDATES
        ),
    )

    print()

    probe_results = []

    for index, dataset in enumerate(
        PARCEL_DATASET_CANDIDATES,
        start=1,
    ):

        print(
            "-" * 70
        )

        print(
            f"[{index}] dataset: {dataset}"
        )

        query_result = query_dataset_by_point(
            api_key=api_key,
            dataset=dataset,
            x=float(x),
            y=float(y),
        )

        analysis = analyze_features(
            features=query_result.get(
                "features",
                [],
            ),
            target_pnu=target_pnu,
        )

        score = dataset_score(
            query_result,
            analysis,
        )

        usable = (
            query_result.get(
                "classification"
            )
            == "QUERY_SUCCESS"
            and analysis.get(
                "polygon_count",
                0,
            )
            > 0
        )

        strict_pnu_verified = (
            analysis.get(
                "pnu_polygon_match_count",
                0,
            )
            > 0
        )

        result = {
            "dataset": dataset,

            "http_status":
                query_result.get(
                    "http_status"
                ),

            "vworld_status":
                query_result.get(
                    "vworld_status"
                ),

            "classification":
                query_result.get(
                    "classification"
                ),

            "error":
                query_result.get(
                    "error"
                ),

            "feature_count":
                query_result.get(
                    "feature_count",
                    0,
                ),

            "polygon_feature_count":
                query_result.get(
                    "polygon_feature_count",
                    0,
                ),

            "analysis":
                analysis,

            "usable_as_parcel_polygon":
                usable,

            "strict_pnu_verified":
                strict_pnu_verified,

            "score":
                score,
        }

        probe_results.append(
            result
        )

        print(
            "HTTP:",
            result.get(
                "http_status"
            ),
        )

        print(
            "VWorld status:",
            result.get(
                "vworld_status"
            )
            or "-",
        )

        print(
            "classification:",
            result.get(
                "classification"
            ),
        )

        if (
            result.get(
                "classification"
            )
            == "INVALID_DATA_IDENTIFIER"
        ):
            error = result.get(
                "error",
                {},
            )

            print(
                "error code:",
                error.get(
                    "code"
                )
                or "-",
            )

            print(
                "error text:",
                error.get(
                    "text"
                )
                or "-",
            )

            print()

            continue

        if (
            result.get(
                "classification"
            )
            != "QUERY_SUCCESS"
        ):
            error = result.get(
                "error",
                {},
            )

            print(
                "error code:",
                error.get(
                    "code"
                )
                or "-",
            )

            print(
                "error text:",
                error.get(
                    "text"
                )
                or "-",
            )

            print()

            continue

        print(
            "Feature 수:",
            analysis.get(
                "feature_count"
            ),
        )

        print(
            "Polygon/MultiPolygon 수:",
            analysis.get(
                "polygon_count"
            ),
        )

        print(
            "PNU 일치 Polygon 수:",
            analysis.get(
                "pnu_polygon_match_count"
            ),
        )

        print(
            "parcel polygon 후보:",
            usable,
        )

        print(
            "PNU 직접 검증:",
            strict_pnu_verified,
        )

        print(
            "score:",
            score,
        )

        features_for_log = analysis.get(
            "features",
            [],
        )

        for feature_info in features_for_log[
            :5
        ]:
            print()

            print(
                "  Feature:",
                feature_info.get(
                    "index"
                ),
            )

            print(
                "  ID:",
                feature_info.get(
                    "id"
                )
                or "-",
            )

            print(
                "  geometry:",
                feature_info.get(
                    "geometry_type"
                )
                or "-",
            )

            print(
                "  PNU key:",
                feature_info.get(
                    "pnu_property_key"
                )
                or "-",
            )

            print(
                "  Feature PNU:",
                feature_info.get(
                    "feature_pnu"
                )
                or "-",
            )

            print(
                "  PNU match:",
                feature_info.get(
                    "pnu_match"
                ),
            )

            properties = feature_info.get(
                "properties",
                {},
            )

            if properties:
                print(
                    "  properties preview:"
                )

                count = 0

                for key, value in properties.items():
                    print(
                        f"    {key}: {value}"
                    )

                    count += 1

                    if count >= 15:
                        break

        print()

    # ========================================================
    # 3. 결과 선택
    # ========================================================

    print_separator()
    print(
        "=== 3. 탐색 결과 요약 ==="
    )
    print_separator()

    classification_counts = {}

    for result in probe_results:
        classification = result.get(
            "classification",
            "UNKNOWN",
        )

        classification_counts[
            classification
        ] = (
            classification_counts.get(
                classification,
                0,
            )
            + 1
        )

    print(
        "전체 후보:",
        len(
            probe_results
        ),
    )

    for key in [
        "QUERY_SUCCESS",
        "INVALID_DATA_IDENTIFIER",
        "QUERY_FAILED",
        "HTTP_ERROR",
    ]:
        print(
            f"{key}:",
            classification_counts.get(
                key,
                0,
            ),
        )

    polygon_candidates = [
        result
        for result in probe_results
        if result.get(
            "usable_as_parcel_polygon"
        )
    ]

    strict_candidates = [
        result
        for result in polygon_candidates
        if result.get(
            "strict_pnu_verified"
        )
    ]

    print()

    print(
        "Polygon dataset 후보:",
        len(
            polygon_candidates
        ),
    )

    print(
        "PNU 직접 검증 후보:",
        len(
            strict_candidates
        ),
    )

    # PNU 일치 후보 우선
    if strict_candidates:
        ranked = sorted(
            strict_candidates,
            key=lambda item: (
                item.get(
                    "score",
                    0,
                )
            ),
            reverse=True,
        )

    else:
        ranked = sorted(
            polygon_candidates,
            key=lambda item: (
                item.get(
                    "score",
                    0,
                )
            ),
            reverse=True,
        )

    selected_dataset = (
        ranked[0].get(
            "dataset"
        )
        if ranked
        else None
    )

    selected_strict = (
        bool(
            ranked
            and ranked[0].get(
                "strict_pnu_verified"
            )
        )
    )

    print()

    if selected_dataset:
        print(
            "최우선 후보:"
        )

        print(
            "- dataset:",
            selected_dataset,
        )

        print(
            "- PNU 직접 검증:",
            selected_strict,
        )

        print(
            "- score:",
            ranked[0].get(
                "score"
            ),
        )
    else:
        print(
            "사용 가능한 parcel Polygon dataset을 찾지 못했습니다."
        )

    # ========================================================
    # 4. 검증
    # ========================================================

    validations = run_validations(
        api_key=api_key,
        context=context,
        address_result=address_result,
        probe_results=probe_results,
        selected_dataset=selected_dataset,
    )

    print()
    print_separator()
    print(
        "=== C-9-2-2B-3A 검증 ==="
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

    # ========================================================
    # 저장
    # ========================================================

    output_data = {
        "step":
            "STEP 17-21-C-9-2-2B-3A",

        "site": {
            "site_id":
                context.get(
                    "site_id"
                ),

            "address":
                context.get(
                    "address"
                ),

            "zone":
                context.get(
                    "zone"
                ),

            "pnu":
                context.get(
                    "pnu"
                ),

            "point": {
                "x": x,
                "y": y,
                "crs":
                    "EPSG:4326",
            },
        },

        "candidate_count":
            len(
                PARCEL_DATASET_CANDIDATES
            ),

        "probe_results":
            probe_results,

        "polygon_candidates": [
            {
                "dataset":
                    result.get(
                        "dataset"
                    ),

                "strict_pnu_verified":
                    result.get(
                        "strict_pnu_verified"
                    ),

                "score":
                    result.get(
                        "score"
                    ),

                "feature_count":
                    result.get(
                        "analysis",
                        {},
                    ).get(
                        "feature_count"
                    ),

                "polygon_count":
                    result.get(
                        "analysis",
                        {},
                    ).get(
                        "polygon_count"
                    ),

                "pnu_polygon_match_count":
                    result.get(
                        "analysis",
                        {},
                    ).get(
                        "pnu_polygon_match_count"
                    ),
            }
            for result in ranked
        ],

        "selected": {
            "dataset":
                selected_dataset,

            "strict_pnu_verified":
                selected_strict,

            "status": (
                "VERIFIED"
                if (
                    selected_dataset
                    and selected_strict
                )
                else (
                    "GEOMETRY_VERIFIED_PNU_UNVERIFIED"
                    if selected_dataset
                    else "NOT_FOUND"
                )
            ),
        },

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

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

    # ========================================================
    # 최종 상태
    # ========================================================

    if not all_pass:
        print(
            "STEP 17-21-C-9-2-2B-3A 검증 실패"
        )
        print()

        print(
            "필지 Polygon dataset 식별 구조 자체에 "
            "검증 실패 항목이 있습니다."
        )

        print()

        print(
            "B-3B intersection 단계로 진행하지 않습니다."
        )

        return

    if not selected_dataset:
        print(
            "STEP 17-21-C-9-2-2B-3A 탐색 완료"
        )
        print()

        print(
            "현재 후보군에서는 사용할 수 있는 "
            "parcel Polygon dataset을 찾지 못했습니다."
        )

        print()

        print(
            "지구단위계획 현재 판정은 변경하지 않습니다."
        )

        print(
            "대표점 기준 TRUE는 유지하되 "
            "parcel intersection 최종검증은 미완료 상태입니다."
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "→ VWorld 공식 데이터목록 또는 "
            "연속지적도 WFS/API source 추가 탐색"
        )

        return

    print(
        "STEP 17-21-C-9-2-2B-3A 완료"
    )
    print()

    print(
        "필지 Polygon dataset 후보:"
    )

    print(
        selected_dataset
    )

    print()

    if selected_strict:
        print(
            "대상 PNU와 직접 일치하는 Polygon/MultiPolygon "
            "Feature가 확인되었습니다."
        )
    else:
        print(
            "Polygon/MultiPolygon Feature는 확인되었으나 "
            "property에서 대상 PNU 직접 일치는 확인되지 않았습니다."
        )

        print(
            "따라서 B-3B에서 geometry 위치와 "
            "추가 property를 다시 검증해야 합니다."
        )

    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-9-2-2B-3B"
    )

    print(
        "→ 검증된 parcel Polygon geometry 추출"
    )

    print(
        "→ LT_C_UPISUQ161 지구단위계획 geometry 재조회"
    )

    print(
        "→ parcel polygon × district-unit-plan polygon intersection"
    )

    print(
        "→ 교차 geometry 면적 / 비율 계산"
    )

    print(
        "→ 실제 필지 교차 확인 시 지구단위계획 TRUE 최종 확정"
    )


if __name__ == "__main__":
    main()