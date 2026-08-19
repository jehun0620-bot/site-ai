import json
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-2B-1A
# VWorld 지구단위계획 API dataset 식별자 / 응답 의미 보정
#
# 핵심 보정
# ------------------------------------------------------------
# 1. SITE Query Context에서 주소 / PNU 읽기
# 2. VWorld 주소검색으로 대표 좌표 확보
# 3. 기존 LT_C_UQ161 대신 공식 서비스 식별자 upisuq161 사용
# 4. HTTP 200만으로 성공 판정하지 않음
# 5. response.status == OK 인 경우에만 Data API 성공
# 6. INVALID_RANGE / API ERROR는 QUERY_FAILED 처리
# 7. 실제 Feature 조회 성공 전에는
#    지구단위계획 TRUE/FALSE를 절대 확정하지 않음
# 8. 실패 시 resolution = UNKNOWN 유지
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
    / "vworld_district_unit_plan_api_test.json"
)

ENV_PATH = (
    PROJECT_ROOT
    / ".env"
)


# ============================================================
# VWorld 설정
# ============================================================

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

# ------------------------------------------------------------
# 기존:
# LT_C_UQ161
#
# 공식 지구단위계획 서비스 식별자:
# upisuq161
# ------------------------------------------------------------

DISTRICT_UNIT_PLAN_DATASET = "upisuq161"

REQUEST_TIMEOUT = 30


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

    print(
        char * width
    )


def safe_preview(
    text: str,
    length: int = 1200,
) -> str:

    if not text:
        return ""

    if len(text) <= length:
        return text

    return (
        text[:length]
        + "..."
    )


def first_nonempty(
    obj: Dict[str, Any],
    keys,
) -> str:

    for key in keys:
        value = obj.get(
            key
        )

        if value not in (
            None,
            "",
        ):
            return str(
                value
            ).strip()

    return ""


# ============================================================
# Query Context 추출
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

    query = data.get(
        "query_context",
        {},
    )

    if not isinstance(
        query,
        dict,
    ):
        query = {}

    site_id = (
        first_nonempty(
            site,
            [
                "site_id",
                "SITE ID",
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
                "jibun_address",
            ],
        )
        or first_nonempty(
            query,
            [
                "address",
                "jibun_address",
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
            query,
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
            query,
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
# HTTP 응답 공통 변환
# ============================================================

def response_to_result(
    response: requests.Response,
) -> Dict[str, Any]:

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
    )

    result: Dict[str, Any] = {
        "status_code":
            response.status_code,

        "content_type":
            content_type,

        "url":
            response.url,

        "text_preview":
            safe_preview(
                response.text
            ),

        "json":
            None,

        "request_success":
            False,

        "exception":
            None,
    }

    try:
        result["json"] = (
            response.json()
        )
    except Exception:
        pass

    result["request_success"] = (
        response.status_code
        == 200
    )

    return result


# ============================================================
# VWorld 내부 status 파싱
# ============================================================

def extract_vworld_status(
    result: Dict[str, Any],
) -> Dict[str, Any]:

    data = result.get(
        "json"
    )

    output = {
        "status": "",
        "error_code": "",
        "error_text": "",
    }

    if not isinstance(
        data,
        dict,
    ):
        return output

    response = data.get(
        "response"
    )

    if not isinstance(
        response,
        dict,
    ):
        return output

    status = response.get(
        "status"
    )

    if status is not None:
        output["status"] = str(
            status
        )

    error = response.get(
        "error"
    )

    if isinstance(
        error,
        dict,
    ):
        output["error_code"] = str(
            error.get(
                "code",
                "",
            )
        )

        output["error_text"] = str(
            error.get(
                "text",
                "",
            )
        )

    return output


# ============================================================
# VWorld 주소검색
# ============================================================

def query_vworld_address(
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

        return response_to_result(
            response
        )

    except requests.RequestException as exc:

        return {
            "status_code": None,
            "content_type": "",
            "url": "",
            "text_preview": "",
            "json": None,
            "request_success": False,
            "exception": str(exc),
        }


def extract_address_coordinate(
    result: Dict[str, Any],
) -> Optional[
    Tuple[float, float]
]:

    data = result.get(
        "json"
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    response = data.get(
        "response"
    )

    if not isinstance(
        response,
        dict,
    ):
        return None

    status = response.get(
        "status"
    )

    if status != "OK":
        return None

    result_obj = response.get(
        "result"
    )

    if not isinstance(
        result_obj,
        dict,
    ):
        return None

    items = result_obj.get(
        "items"
    )

    if not isinstance(
        items,
        list,
    ):
        return None

    if not items:
        return None

    first = items[0]

    if not isinstance(
        first,
        dict,
    ):
        return None

    point = first.get(
        "point"
    )

    if not isinstance(
        point,
        dict,
    ):
        return None

    x = point.get(
        "x"
    )

    y = point.get(
        "y"
    )

    try:
        return (
            float(x),
            float(y),
        )

    except (
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# VWorld 지구단위계획 Data API
# ============================================================

def query_district_unit_plan(
    api_key: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    # --------------------------------------------------------
    # 우선 대표 point 주변 feature 조회.
    #
    # B-1A 목적:
    # dataset/service 연결 성공 여부 확인.
    #
    # geometry 실제 교차 판정은 다음 B-2 단계에서 수행.
    # --------------------------------------------------------

    geom_filter = (
        f"POINT({x} {y})"
    )

    params = {
        "service": "data",
        "request": "GetFeature",
        "data":
            DISTRICT_UNIT_PLAN_DATASET,

        "key":
            api_key,

        "domain":
            "localhost",

        "geometry":
            "true",

        "attribute":
            "true",

        "size":
            100,

        "page":
            1,

        "format":
            "json",

        "crs":
            "EPSG:4326",

        "geomFilter":
            geom_filter,
    }

    try:
        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        return response_to_result(
            response
        )

    except requests.RequestException as exc:

        return {
            "status_code": None,
            "content_type": "",
            "url": "",
            "text_preview": "",
            "json": None,
            "request_success": False,
            "exception": str(exc),
        }


# ============================================================
# Feature 수 파악
# ============================================================

def extract_feature_count(
    result: Dict[str, Any],
) -> Optional[int]:

    data = result.get(
        "json"
    )

    if not isinstance(
        data,
        dict,
    ):
        return None

    response = data.get(
        "response"
    )

    if not isinstance(
        response,
        dict,
    ):
        return None

    result_obj = response.get(
        "result"
    )

    if not isinstance(
        result_obj,
        dict,
    ):
        return None

    # VWorld 응답 구조 변형 대응
    feature_collection = (
        result_obj.get(
            "featureCollection"
        )
        or result_obj.get(
            "featurecollection"
        )
    )

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
            return len(
                features
            )

        total = (
            feature_collection.get(
                "totalFeatures"
            )
            or feature_collection.get(
                "numberMatched"
            )
        )

        try:
            if total is not None:
                return int(
                    total
                )
        except (
            TypeError,
            ValueError,
        ):
            pass

    items = result_obj.get(
        "items"
    )

    if isinstance(
        items,
        list,
    ):
        return len(
            items
        )

    return None


# ============================================================
# 개별 검증
# ============================================================

def validation_api_key(
    api_key: str,
) -> bool:

    return bool(
        api_key.strip()
    )


def validation_query_context(
    context: Dict[str, str],
) -> bool:

    return (
        bool(
            context.get(
                "address"
            )
        )
        and len(
            context.get(
                "pnu",
                "",
            )
        )
        == 19
    )


def validation_address_http(
    result: Dict[str, Any],
) -> bool:

    return (
        result.get(
            "status_code"
        )
        == 200
    )


def validation_address_vworld_ok(
    result: Dict[str, Any],
) -> bool:

    status = extract_vworld_status(
        result
    )

    return (
        status.get(
            "status"
        )
        == "OK"
    )


def validation_coordinate(
    coordinate: Optional[
        Tuple[
            float,
            float,
        ]
    ],
) -> bool:

    if coordinate is None:
        return False

    x, y = coordinate

    return (
        124.0
        <= x
        <= 132.0
        and
        33.0
        <= y
        <= 39.5
    )


def validation_data_http(
    result: Dict[str, Any],
) -> bool:

    return (
        result.get(
            "status_code"
        )
        == 200
    )


def validation_data_api(
    result: Dict[str, Any],
) -> bool:
    """
    중요:
    HTTP 200이어도 VWorld JSON 내부가 ERROR일 수 있다.

    따라서 response.status == OK여야만
    실제 Data API 연결 성공으로 본다.
    """

    if (
        result.get(
            "status_code"
        )
        != 200
    ):
        return False

    status = extract_vworld_status(
        result
    )

    return (
        status.get(
            "status"
        )
        == "OK"
    )


def validation_invalid_range_removed(
    result: Dict[str, Any],
) -> bool:

    status = extract_vworld_status(
        result
    )

    return (
        status.get(
            "error_code"
        )
        != "INVALID_RANGE"
    )


# ============================================================
# Query 상태 결정
# ============================================================

def determine_query_status(
    api_key: str,
    coordinate: Optional[
        Tuple[
            float,
            float,
        ]
    ],
    data_result: Dict[str, Any],
) -> str:

    if not api_key:
        return "NOT_CONNECTED"

    if coordinate is None:
        return "QUERY_FAILED"

    if not validation_data_api(
        data_result
    ):
        return "QUERY_FAILED"

    return "QUERY_SUCCESS"


# ============================================================
# Resolution 결정
# ============================================================

def determine_resolution(
    query_status: str,
) -> Dict[str, str]:
    """
    B-1A에서는 dataset 연결까지만 확인한다.

    Feature geometry와 필지 교차 검증 전까지
    TRUE/FALSE를 확정하지 않는다.
    """

    if query_status == "QUERY_SUCCESS":
        return {
            "status": "UNKNOWN",
            "confidence": "NONE",
            "reason": (
                "지구단위계획 Data API 연결은 성공했으나 "
                "아직 Feature geometry와 대상 필지의 실제 공간 포함/"
                "교차 판정을 수행하지 않았으므로 TRUE/FALSE를 "
                "확정하지 않음"
            ),
        }

    return {
        "status": "UNKNOWN",
        "confidence": "NONE",
        "reason": (
            "지구단위계획 실제 공간조회가 성공적으로 완료되지 "
            "않았으므로 TRUE 또는 FALSE로 판정하지 않음"
        ),
    }


# ============================================================
# 로그 출력
# ============================================================

def print_vworld_response_status(
    result: Dict[str, Any],
) -> None:

    print(
        "HTTP 상태:",
        result.get(
            "status_code"
        ),
    )

    print(
        "Content-Type:",
        result.get(
            "content_type",
            "",
        ),
    )

    if result.get(
        "exception"
    ):
        print(
            "request exception:",
            result.get(
                "exception"
            ),
        )

        return

    status = extract_vworld_status(
        result
    )

    if status.get(
        "status"
    ):
        print(
            "VWorld status:",
            status.get(
                "status"
            ),
        )

    if status.get(
        "error_code"
    ):
        print(
            "error code:",
            status.get(
                "error_code"
            ),
        )

    if status.get(
        "error_text"
    ):
        print(
            "error text:",
            status.get(
                "error_text"
            ),
        )


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2B-1A "
        "VWorld 지구단위계획 API dataset / 응답 의미 보정 테스트 ==="
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
            "SITE 공간조회 Query Context 파일이 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    # --------------------------------------------------------
    # 환경변수
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Query Context
    # --------------------------------------------------------

    query_context_data = load_json(
        QUERY_CONTEXT_PATH
    )

    context = extract_query_context(
        query_context_data
    )

    site_id = context.get(
        "site_id",
        ""
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
    # SITE 출력
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 대상 SITE ==="
    )
    print_separator()

    print(
        "SITE ID:",
        site_id
        or "-",
    )

    print(
        "주소:",
        address
        or "-",
    )

    print(
        "PNU:",
        pnu
        or "-",
    )

    print()

    # --------------------------------------------------------
    # 인증
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # 주소 검색
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. VWorld 주소 검색 ==="
    )
    print_separator()

    if api_key and address:

        address_result = (
            query_vworld_address(
                api_key=api_key,
                address=address,
            )
        )

    else:

        address_result = {
            "status_code": None,
            "content_type": "",
            "url": "",
            "text_preview": "",
            "json": None,
            "request_success": False,
            "exception":
                "API Key 또는 주소 없음",
        }

    print_vworld_response_status(
        address_result
    )

    coordinate = (
        extract_address_coordinate(
            address_result
        )
    )

    if coordinate:

        x, y = coordinate

        print(
            "좌표:"
        )

        print(
            "  X:",
            x,
        )

        print(
            "  Y:",
            y,
        )

    else:

        print(
            "좌표: 획득 실패"
        )

    print()

    # --------------------------------------------------------
    # 지구단위계획 Data API
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. 지구단위계획 Data API ==="
    )
    print_separator()

    print(
        "dataset:",
        DISTRICT_UNIT_PLAN_DATASET,
    )

    if (
        api_key
        and coordinate
    ):

        x, y = coordinate

        data_result = (
            query_district_unit_plan(
                api_key=api_key,
                x=x,
                y=y,
            )
        )

    else:

        data_result = {
            "status_code": None,
            "content_type": "",
            "url": "",
            "text_preview": "",
            "json": None,
            "request_success": False,
            "exception":
                "API Key 또는 좌표 없음",
        }

    print_vworld_response_status(
        data_result
    )

    feature_count = (
        extract_feature_count(
            data_result
        )
    )

    if feature_count is not None:
        print(
            "Feature 수:",
            feature_count,
        )

    if not validation_data_api(
        data_result
    ):

        preview = data_result.get(
            "text_preview",
            "",
        )

        if preview:
            print()
            print(
                "응답 preview:"
            )

            print(
                preview
            )

    print()

    # --------------------------------------------------------
    # 상태 결정
    # --------------------------------------------------------

    query_status = (
        determine_query_status(
            api_key=api_key,
            coordinate=coordinate,
            data_result=data_result,
        )
    )

    resolution = (
        determine_resolution(
            query_status
        )
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = {
        "VWORLD API Key 존재":
            validation_api_key(
                api_key
            ),

        "SITE Query Context 정상":
            validation_query_context(
                context
            ),

        "주소검색 HTTP 200":
            validation_address_http(
                address_result
            ),

        "주소검색 VWorld OK":
            validation_address_vworld_ok(
                address_result
            ),

        "주소검색 좌표 획득":
            validation_coordinate(
                coordinate
            ),

        "지구단위계획 API HTTP 200":
            validation_data_http(
                data_result
            ),

        "지구단위계획 API 정상 응답":
            validation_data_api(
                data_result
            ),

        "INVALID_RANGE 제거":
            validation_invalid_range_removed(
                data_result
            ),
    }

    print_separator()
    print(
        "=== C-9-2-2B-1A 검증 ==="
    )
    print_separator()

    for name, passed in validations.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    print_separator()
    print(
        "=== 현재 공간조건 판정 상태 ==="
    )
    print_separator()

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution:",
        resolution[
            "status"
        ],
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        resolution[
            "reason"
        ],
    )

    print()

    # --------------------------------------------------------
    # 결과 저장
    # --------------------------------------------------------

    all_pass = all(
        validations.values()
    )

    address_status = (
        extract_vworld_status(
            address_result
        )
    )

    data_status = (
        extract_vworld_status(
            data_result
        )
    )

    output_data = {
        "step":
            "STEP 17-21-C-9-2-2B-1A",

        "site": {
            "site_id":
                site_id,

            "address":
                address,

            "pnu":
                pnu,

            "parcel_key":
                context.get(
                    "parcel_key",
                    "",
                ),
        },

        "vworld": {
            "api_key_present":
                bool(
                    api_key
                ),

            "address_search": {
                "http_status":
                    address_result.get(
                        "status_code"
                    ),

                "vworld_status":
                    address_status.get(
                        "status"
                    ),

                "x":
                    (
                        coordinate[0]
                        if coordinate
                        else None
                    ),

                "y":
                    (
                        coordinate[1]
                        if coordinate
                        else None
                    ),
            },

            "district_unit_plan": {
                "dataset":
                    DISTRICT_UNIT_PLAN_DATASET,

                "http_status":
                    data_result.get(
                        "status_code"
                    ),

                "vworld_status":
                    data_status.get(
                        "status"
                    ),

                "error_code":
                    data_status.get(
                        "error_code"
                    ),

                "error_text":
                    data_status.get(
                        "error_text"
                    ),

                "feature_count":
                    feature_count,

                "query_status":
                    query_status,
            },
        },

        "resolution": {
            "condition":
                "지구단위계획",

            "status":
                resolution[
                    "status"
                ],

            "confidence":
                resolution[
                    "confidence"
                ],

            "reason":
                resolution[
                    "reason"
                ],
        },

        "validations":
            validations,

        "all_pass":
            all_pass,

        "raw": {
            "address_search":
                address_result,

            "district_unit_plan":
                data_result,
        },
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

    # --------------------------------------------------------
    # 최종 안내
    # --------------------------------------------------------

    if all_pass:

        print(
            "STEP 17-21-C-9-2-2B-1A 완료"
        )

        print()

        print(
            "VWorld 지구단위계획 API 연결 검증: ALL PASS"
        )

        print()

        print(
            "중요:"
        )

        print(
            "- API 연결 성공만 확인했습니다."
        )

        print(
            "- 아직 지구단위계획 TRUE/FALSE는 확정하지 않습니다."
        )

        print(
            "- 현재 resolution은 UNKNOWN을 유지합니다."
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-2B-2"
        )

        print(
            "→ FeatureCollection 구조 분석"
        )

        print(
            "→ geometry 추출"
        )

        print(
            "→ 대표좌표 point-in-polygon 검증"
        )

        print(
            "→ 이후 parcel polygon intersection으로 보강"
        )

        print(
            "→ 공간교차가 확인된 경우에만 TRUE"
        )

        print(
            "→ 조회 성공 + 교차 없음이 확인된 경우에만 FALSE"
        )

    else:

        print(
            "STEP 17-21-C-9-2-2B-1A 검증 미완료"
        )

        print()

        status = extract_vworld_status(
            data_result
        )

        error_code = status.get(
            "error_code",
            "",
        )

        if (
            error_code
            == "INVALID_RANGE"
        ):

            print(
                "현재 dataset 식별자도 "
                "VWorld req/data API에서 "
                "유효한 data 값으로 인정되지 않았습니다."
            )

            print()

            print(
                "이 경우 TRUE/FALSE 판정을 하지 않습니다."
            )

            print(
                "resolution: UNKNOWN"
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-2B-1B"
            )

            print(
                "→ VWorld 현재 Data API 데이터목록 / 서비스 정의 확인"
            )

            print(
                "→ 실제 req/data용 data 식별자 탐색"
            )

        else:

            print(
                "FAIL 항목을 확인한 뒤 "
                "B-2 geometry 판정으로 진행해야 합니다."
            )


if __name__ == "__main__":
    main()