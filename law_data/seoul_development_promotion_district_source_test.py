import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-3A-3
# 서울시 개발진흥지구 전용 Source 연결 / 의미 검증
#
# 핵심 목적
# ------------------------------------------------------------
# 1. VWorld dataset 번호 추측 탐색 종료
# 2. 서울 열린데이터광장 공식 개발진흥지구 source 사용
# 3. 공식 공간정보 코드 UQ129 확인
# 4. OpenAPI service = upiSCUq129 연결
# 5. OpenAPI 응답 schema 분석
# 6. 개발진흥지구 전용 source라는 의미 검증
# 7. OpenAPI 속성조회와 공간교차 판정을 분리
# 8. 공간 geometry 미확보 상태에서는 TRUE/FALSE 판정 금지
#
# 중요
# ------------------------------------------------------------
# 서울 OpenAPI 응답은 속성정보 조회 source로 사용한다.
#
# 실제 parcel polygon × 개발진흥지구 polygon intersection은
# 다음 단계에서 UQ129 SHP 공간파일을 확보하여 수행한다.
#
# 따라서 이번 단계 SITE resolution은 UNKNOWN을 유지한다.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

SEMANTIC_PROBE_PATH = (
    BASE_DIR
    / "output"
    / "vworld_upis_dataset_semantic_probe.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "seoul_development_promotion_district_source_test.json"
)

ENV_PATH = BASE_DIR.parent / ".env"


# ============================================================
# 서울 열린데이터광장 공식 Source
# ============================================================

SEOUL_API_BASE_URL = (
    "http://openapi.seoul.go.kr:8088"
)

SEOUL_SERVICE_NAME = "upiSCUq129"

SEOUL_DATASET_CODE = "UQ129"

SEOUL_DATASET_NAME = (
    "서울시 용도지구(개발진흥지구) 공간정보"
)

SEOUL_DATASET_CRS = "EPSG:5174"

SEOUL_SOURCE_TYPE = (
    "SEOUL_OPEN_DATA"
)

SEOUL_SPATIAL_FILE_PATTERN = (
    "UQ129_용도지구(개발진흥지구)_*.zip"
)


# ============================================================
# API 페이징
# ============================================================

API_START_INDEX = 1
API_END_INDEX = 1000


# ============================================================
# 허용 상태
# ============================================================

QUERY_STATUS_VALUES = {
    "NOT_CONNECTED",
    "NOT_QUERIED",
    "QUERY_FAILED",
    "QUERY_SUCCESS",
}

RESOLUTION_VALUES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
}

CONFIDENCE_VALUES = {
    "NONE",
    "LOW",
    "MEDIUM",
    "HIGH",
}


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


def clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def first_nonempty(
    obj: Dict[str, Any],
    keys: List[str],
) -> str:
    for key in keys:
        value = obj.get(
            key
        )

        value = clean_text(
            value
        )

        if value:
            return value

    return ""


# ============================================================
# Query Context 읽기
# ============================================================

def recursive_find_value(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(
        obj,
        dict,
    ):
        for key in keys:
            if (
                key in obj
                and obj[key]
                not in (
                    None,
                    "",
                )
            ):
                return obj[key]

        for value in obj.values():
            found = recursive_find_value(
                value,
                keys,
            )

            if found not in (
                None,
                "",
            ):
                return found

    elif isinstance(
        obj,
        list,
    ):
        for item in obj:
            found = recursive_find_value(
                item,
                keys,
            )

            if found not in (
                None,
                "",
            ):
                return found

    return None


def extract_query_context(
    data: Any,
) -> Dict[str, str]:

    site_id = recursive_find_value(
        data,
        [
            "site_id",
            "SITE ID",
            "parcel_key",
        ],
    )

    address = recursive_find_value(
        data,
        [
            "address",
            "주소",
        ],
    )

    pnu = recursive_find_value(
        data,
        [
            "pnu",
            "PNU",
        ],
    )

    zone = recursive_find_value(
        data,
        [
            "zone",
            "용도지역",
        ],
    )

    sigungu_code = recursive_find_value(
        data,
        [
            "sigungu_code",
            "sgg_code",
            "시군구코드",
        ],
    )

    bjdong_code = recursive_find_value(
        data,
        [
            "bjdong_code",
            "법정동코드",
        ],
    )

    return {
        "site_id":
            clean_text(
                site_id
            ),
        "address":
            clean_text(
                address
            ),
        "pnu":
            clean_text(
                pnu
            ),
        "zone":
            clean_text(
                zone
            ),
        "sigungu_code":
            clean_text(
                sigungu_code
            ),
        "bjdong_code":
            clean_text(
                bjdong_code
            ),
    }


# ============================================================
# 서울 OpenAPI Key
# ============================================================

def find_seoul_api_key() -> Tuple[
    str,
    str,
]:
    """
    프로젝트마다 환경변수명이 다를 수 있으므로
    몇 가지 안전한 후보를 순차 검사한다.
    """

    candidates = [
        "SEOUL_OPEN_API_KEY",
        "SEOUL_API_KEY",
        "SEOUL_DATA_API_KEY",
        "SEOUL_OPEN_DATA_API_KEY",
    ]

    for env_name in candidates:
        value = clean_text(
            os.getenv(
                env_name
            )
        )

        if value:
            return (
                env_name,
                value,
            )

    return (
        "",
        "",
    )


# ============================================================
# 서울 OpenAPI 요청
# ============================================================

def build_api_url(
    api_key: str,
    start_index: int,
    end_index: int,
) -> str:

    return (
        f"{SEOUL_API_BASE_URL}/"
        f"{api_key}/"
        f"json/"
        f"{SEOUL_SERVICE_NAME}/"
        f"{start_index}/"
        f"{end_index}/"
    )


def query_seoul_api(
    api_key: str,
) -> Dict[str, Any]:

    url = build_api_url(
        api_key=api_key,
        start_index=API_START_INDEX,
        end_index=API_END_INDEX,
    )

    try:
        response = requests.get(
            url,
            timeout=30,
        )

    except requests.RequestException as exc:
        return {
            "http_status": None,
            "content_type": "",
            "query_status":
                "QUERY_FAILED",
            "error":
                str(exc),
            "raw":
                None,
        }

    http_status = (
        response.status_code
    )

    content_type = response.headers.get(
        "Content-Type",
        "",
    )

    try:
        data = response.json()

    except ValueError:
        return {
            "http_status":
                http_status,
            "content_type":
                content_type,
            "query_status":
                "QUERY_FAILED",
            "error":
                "JSON 파싱 실패",
            "response_preview":
                response.text[
                    :1500
                ],
            "raw":
                None,
        }

    return {
        "http_status":
            http_status,
        "content_type":
            content_type,
        "query_status":
            (
                "QUERY_SUCCESS"
                if http_status
                == 200
                else
                "QUERY_FAILED"
            ),
        "raw":
            data,
    }


# ============================================================
# 서울 API 구조 파싱
# ============================================================

def extract_service_object(
    data: Any,
) -> Optional[Dict[str, Any]]:

    if not isinstance(
        data,
        dict,
    ):
        return None

    # 정상적인 서울 OpenAPI 응답
    service = data.get(
        SEOUL_SERVICE_NAME
    )

    if isinstance(
        service,
        dict,
    ):
        return service

    # 서비스명 case가 바뀌는 경우 대비
    target_lower = (
        SEOUL_SERVICE_NAME.lower()
    )

    for key, value in data.items():
        if (
            str(key).lower()
            == target_lower
            and isinstance(
                value,
                dict,
            )
        ):
            return value

    return None


def extract_api_error(
    data: Any,
) -> Dict[str, str]:

    if not isinstance(
        data,
        dict,
    ):
        return {
            "code": "",
            "message": "",
        }

    # 서울 OpenAPI 오류 형태
    result = data.get(
        "RESULT"
    )

    if isinstance(
        result,
        dict,
    ):
        return {
            "code":
                clean_text(
                    result.get(
                        "CODE"
                    )
                ),
            "message":
                clean_text(
                    result.get(
                        "MESSAGE"
                    )
                ),
        }

    return {
        "code": "",
        "message": "",
    }


def extract_rows(
    service: Optional[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    if not isinstance(
        service,
        dict,
    ):
        return []

    rows = service.get(
        "row"
    )

    if not isinstance(
        rows,
        list,
    ):
        return []

    return [
        row
        for row in rows
        if isinstance(
            row,
            dict,
        )
    ]


def extract_total_count(
    service: Optional[
        Dict[str, Any]
    ],
) -> int:

    if not isinstance(
        service,
        dict,
    ):
        return 0

    value = service.get(
        "list_total_count"
    )

    try:
        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):
        return 0


def extract_result_info(
    service: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, str]:

    if not isinstance(
        service,
        dict,
    ):
        return {
            "code": "",
            "message": "",
        }

    result = service.get(
        "RESULT"
    )

    if not isinstance(
        result,
        dict,
    ):
        return {
            "code": "",
            "message": "",
        }

    return {
        "code":
            clean_text(
                result.get(
                    "CODE"
                )
            ),
        "message":
            clean_text(
                result.get(
                    "MESSAGE"
                )
            ),
    }


# ============================================================
# Schema 분석
# ============================================================

EXPECTED_FIELDS = [
    "OBJT_ID",
    "STUT_FIG_MNG_NO",
    "FIG_LCLSF_CD",
    "FIG_MCLSF_CD",
    "FIG_SCLSF_CD",
    "FIG_ATRB_CD",
    "FIG_RPT_MNG_CD",
    "DCSN_ANCMNT_MNG_CD",
    "LBL_NM",
    "SGG_CD",
    "FLRPLN_NO",
    "STUT_FIG_CRT_DT",
    "AREA",
    "LEN",
]


def collect_schema_fields(
    rows: List[
        Dict[str, Any]
    ],
) -> List[str]:

    fields = set()

    for row in rows:
        fields.update(
            str(key)
            for key
            in row.keys()
        )

    return sorted(
        fields
    )


def normalize_sgg_code(
    value: Any,
) -> str:

    text = clean_text(
        value
    )

    digits = "".join(
        char
        for char in text
        if char.isdigit()
    )

    if len(
        digits
    ) >= 5:
        return digits[
            :5
        ]

    return digits


# ============================================================
# 대상 시군구 행 분석
# ============================================================

def filter_target_sigungu_rows(
    rows: List[
        Dict[str, Any]
    ],
    sigungu_code: str,
) -> List[
    Dict[str, Any]
]:

    if not sigungu_code:
        return []

    target = normalize_sgg_code(
        sigungu_code
    )

    result = []

    for row in rows:

        row_code = normalize_sgg_code(
            row.get(
                "SGG_CD"
            )
        )

        if (
            row_code
            and target
            and row_code
            == target
        ):
            result.append(
                row
            )

    return result


# ============================================================
# Feature preview
# ============================================================

def summarize_row(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        field:
            row.get(
                field
            )
        for field in EXPECTED_FIELDS
        if field in row
    }


# ============================================================
# 공간 geometry 존재 여부
# ============================================================

GEOMETRY_FIELD_HINTS = {
    "geometry",
    "geom",
    "shape",
    "the_geom",
    "wkt",
    "geojson",
    "coordinates",
}


def has_geometry_field(
    rows: List[
        Dict[str, Any]
    ],
) -> bool:

    for row in rows:

        for key in row.keys():
            if (
                str(key).lower()
                in GEOMETRY_FIELD_HINTS
            ):
                return True

    return False


# ============================================================
# 기존 semantic probe 상태 확인
# ============================================================

def extract_previous_resolution(
    data: Any,
) -> Dict[str, str]:

    if not isinstance(
        data,
        dict,
    ):
        return {
            "resolution": "",
            "query_status": "",
        }

    resolution_obj = data.get(
        "site_resolution"
    )

    if isinstance(
        resolution_obj,
        dict,
    ):
        return {
            "resolution":
                clean_text(
                    resolution_obj.get(
                        "resolution"
                    )
                ),
            "query_status":
                clean_text(
                    resolution_obj.get(
                        "query_status"
                    )
                ),
        }

    return {
        "resolution": "",
        "query_status": "",
    }


# ============================================================
# 검증
# ============================================================

def run_validations(
    api_key_exists: bool,
    query_context:
        Dict[str, str],
    http_status:
        Optional[int],
    query_status: str,
    service_found: bool,
    api_result_code: str,
    rows:
        List[Dict[str, Any]],
    schema_fields:
        List[str],
    geometry_available:
        bool,
    resolution: str,
) -> Dict[str, bool]:

    pnu = query_context.get(
        "pnu",
        "",
    )

    return {
        "서울 OpenAPI Key 존재":
            api_key_exists,

        "SITE 주소 존재":
            bool(
                query_context.get(
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

        "개발진흥지구 공식 dataset 코드 UQ129":
            (
                SEOUL_DATASET_CODE
                == "UQ129"
            ),

        "서울 OpenAPI service upiSCUq129":
            (
                SEOUL_SERVICE_NAME
                == "upiSCUq129"
            ),

        "서울 OpenAPI HTTP 200":
            (
                http_status
                == 200
            ),

        "서울 OpenAPI service 객체 확인":
            service_found,

        "서울 OpenAPI 정상 결과":
            (
                query_status
                == "QUERY_SUCCESS"
                and (
                    api_result_code
                    in {
                        "",
                        "INFO-000",
                    }
                )
            ),

        "개발진흥지구 row 확보":
            bool(
                rows
            ),

        "공식 schema 주요 필드 확인":
            all(
                field
                in schema_fields
                for field
                in [
                    "OBJT_ID",
                    "FIG_ATRB_CD",
                    "LBL_NM",
                    "SGG_CD",
                ]
            ),

        "OpenAPI geometry 없으면 공간판정 금지":
            (
                geometry_available
                or resolution
                == "UNKNOWN"
            ),

        "현재 SITE TRUE/FALSE 미확정":
            (
                resolution
                == "UNKNOWN"
            ),

        "resolution 허용값":
            (
                resolution
                in RESOLUTION_VALUES
            ),

        "query_status 허용값":
            (
                query_status
                in QUERY_STATUS_VALUES
            ),
    }


# ============================================================
# 로그
# ============================================================

def print_row(
    row: Dict[str, Any],
    index: int,
) -> None:

    print(
        "-" * 70
    )

    print(
        f"Row {index}"
    )

    summary = summarize_row(
        row
    )

    for key, value in (
        summary.items()
    ):
        print(
            f"{key}: {value}"
        )


# ============================================================
# 메인
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-9-2-3A-3 "
        "서울시 개발진흥지구 전용 Source 연결 / 의미 검증 ==="
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
        "Semantic Probe 입력:"
    )
    print(
        SEMANTIC_PROBE_PATH
    )
    print()

    if not QUERY_CONTEXT_PATH.exists():
        raise FileNotFoundError(
            "Query Context 파일이 없습니다: "
            f"{QUERY_CONTEXT_PATH}"
        )

    if not SEMANTIC_PROBE_PATH.exists():
        raise FileNotFoundError(
            "Semantic Probe 파일이 없습니다: "
            f"{SEMANTIC_PROBE_PATH}"
        )

    query_context_data = (
        load_json(
            QUERY_CONTEXT_PATH
        )
    )

    semantic_probe_data = (
        load_json(
            SEMANTIC_PROBE_PATH
        )
    )

    context = (
        extract_query_context(
            query_context_data
        )
    )

    previous_resolution = (
        extract_previous_resolution(
            semantic_probe_data
        )
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
        "시군구코드:",
        context.get(
            "sigungu_code"
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

    print(
        "이전 개발진흥지구 resolution:",
        previous_resolution.get(
            "resolution"
        )
        or "-",
    )

    # --------------------------------------------------------
    # 공식 Source
    # --------------------------------------------------------

    print()
    print_separator()
    print(
        "=== 1. 공식 개발진흥지구 Source ==="
    )
    print_separator()

    print(
        "제공기관: 서울특별시"
    )

    print(
        "데이터셋:",
        SEOUL_DATASET_NAME,
    )

    print(
        "공간정보 코드:",
        SEOUL_DATASET_CODE,
    )

    print(
        "OpenAPI service:",
        SEOUL_SERVICE_NAME,
    )

    print(
        "공간파일 좌표계:",
        SEOUL_DATASET_CRS,
    )

    print(
        "공간파일 패턴:",
        SEOUL_SPATIAL_FILE_PATTERN,
    )

    print()

    print(
        "VWorld 코드번호 추측 탐색:"
    )
    print(
        "종료"
    )

    print()

    print(
        "LT_C_UPISUQ161:"
    )
    print(
        "지구단위계획구역 전용 source로 유지"
    )

    print()

    print(
        "개발진흥지구:"
    )
    print(
        "서울시 UQ129 전용 source로 분리"
    )

    # --------------------------------------------------------
    # API Key
    # --------------------------------------------------------

    load_dotenv(
        ENV_PATH
    )

    env_name, api_key = (
        find_seoul_api_key()
    )

    print()
    print_separator()
    print(
        "=== 2. 서울 OpenAPI 인증 ==="
    )
    print_separator()

    if api_key:
        print(
            f"{env_name}: "
            "정상적으로 읽었습니다."
        )

    else:
        print(
            "서울 OpenAPI 인증키를 찾을 수 없습니다."
        )

        print(
            "확인한 환경변수:"
        )

        for name in [
            "SEOUL_OPEN_API_KEY",
            "SEOUL_API_KEY",
            "SEOUL_DATA_API_KEY",
            "SEOUL_OPEN_DATA_API_KEY",
        ]:
            print(
                f"- {name}"
            )

        print()
        print(
            "개발진흥지구 resolution은 UNKNOWN을 유지합니다."
        )

        return

    # --------------------------------------------------------
    # OpenAPI
    # --------------------------------------------------------

    print()
    print_separator()
    print(
        "=== 3. 서울 개발진흥지구 OpenAPI 조회 ==="
    )
    print_separator()

    api_result = (
        query_seoul_api(
            api_key
        )
    )

    http_status = (
        api_result.get(
            "http_status"
        )
    )

    print(
        "HTTP 상태:",
        http_status,
    )

    print(
        "Content-Type:",
        api_result.get(
            "content_type"
        )
        or "-",
    )

    raw = api_result.get(
        "raw"
    )

    service = (
        extract_service_object(
            raw
        )
    )

    if service:
        print(
            "service 객체:",
            SEOUL_SERVICE_NAME,
            "확인"
        )

    else:
        print(
            "service 객체:",
            "미확인"
        )

    error = (
        extract_api_error(
            raw
        )
    )

    if (
        not service
        and (
            error.get(
                "code"
            )
            or error.get(
                "message"
            )
        )
    ):
        print(
            "API error code:",
            error.get(
                "code"
            )
        )

        print(
            "API error message:",
            error.get(
                "message"
            )
        )

    result_info = (
        extract_result_info(
            service
        )
    )

    if result_info.get(
        "code"
    ):
        print(
            "RESULT.CODE:",
            result_info.get(
                "code"
            ),
        )

    if result_info.get(
        "message"
    ):
        print(
            "RESULT.MESSAGE:",
            result_info.get(
                "message"
            ),
        )

    rows = extract_rows(
        service
    )

    total_count = (
        extract_total_count(
            service
        )
    )

    print(
        "전체 데이터 수:",
        total_count,
    )

    print(
        "현재 받은 row 수:",
        len(
            rows
        ),
    )

    # --------------------------------------------------------
    # Schema
    # --------------------------------------------------------

    print()
    print_separator()
    print(
        "=== 4. 개발진흥지구 API Schema ==="
    )
    print_separator()

    schema_fields = (
        collect_schema_fields(
            rows
        )
    )

    print(
        "필드 수:",
        len(
            schema_fields
        ),
    )

    if schema_fields:
        for field in (
            schema_fields
        ):
            print(
                f"- {field}"
            )

    else:
        print(
            "- 없음"
        )

    geometry_available = (
        has_geometry_field(
            rows
        )
    )

    print()
    print(
        "OpenAPI geometry 필드:",
        (
            "있음"
            if geometry_available
            else "없음"
        ),
    )

    # --------------------------------------------------------
    # 강남구 행
    # --------------------------------------------------------

    target_sigungu_rows = (
        filter_target_sigungu_rows(
            rows=rows,
            sigungu_code=
                context.get(
                    "sigungu_code",
                    "",
                ),
        )
    )

    print()
    print_separator()
    print(
        "=== 5. 대상 시군구 개발진흥지구 Row ==="
    )
    print_separator()

    print(
        "대상 시군구코드:",
        context.get(
            "sigungu_code"
        )
        or "-",
    )

    print(
        "일치 Row:",
        len(
            target_sigungu_rows
        ),
    )

    print()

    # 이 결과는 "강남구 안에 개발진흥지구 자료가 있는가" 정도만
    # 보여준다.
    #
    # 절대로 해당 필지 포함 여부로 해석하지 않는다.

    preview_rows = (
        target_sigungu_rows[
            :10
        ]
        if target_sigungu_rows
        else rows[
            :10
        ]
    )

    for index, row in enumerate(
        preview_rows,
        start=1,
    ):
        print_row(
            row,
            index,
        )
        print()

    # --------------------------------------------------------
    # 공간판정 상태
    # --------------------------------------------------------

    #
    # 중요:
    #
    # OpenAPI에 공간도형이 없다면
    # SGG_CD가 강남구라고 하더라도
    # SITE가 개발진흥지구라는 뜻이 아니다.
    #
    # 따라서 공간파일 확보 전에는 UNKNOWN.
    #

    query_status = (
        "QUERY_SUCCESS"
        if (
            http_status == 200
            and service is not None
        )
        else
        "QUERY_FAILED"
    )

    resolution = "UNKNOWN"
    confidence = "NONE"

    if (
        query_status
        == "QUERY_SUCCESS"
    ):
        reason = (
            "서울 열린데이터광장 개발진흥지구 전용 "
            "UQ129 OpenAPI source 연결 및 속성정보 조회에 성공했으나, "
            "현재 OpenAPI 응답만으로 대상 Parcel Polygon과 "
            "개발진흥지구 Polygon의 실제 공간교차를 검증하지 않았으므로 "
            "SITE TRUE/FALSE를 확정하지 않음"
        )

    else:
        reason = (
            "서울 개발진흥지구 전용 source 조회가 완료되지 않았으므로 "
            "SITE TRUE/FALSE를 확정하지 않음"
        )

    print()
    print_separator()
    print(
        "=== 6. 현재 개발진흥지구 SITE 판정 ==="
    )
    print_separator()

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
    )

    print(
        "reason:",
        reason,
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = (
        run_validations(
            api_key_exists=
                bool(
                    api_key
                ),
            query_context=
                context,
            http_status=
                http_status,
            query_status=
                query_status,
            service_found=
                service
                is not None,
            api_result_code=
                result_info.get(
                    "code",
                    "",
                ),
            rows=
                rows,
            schema_fields=
                schema_fields,
            geometry_available=
                geometry_available,
            resolution=
                resolution,
        )
    )

    print()
    print_separator()
    print(
        "=== C-9-2-3A-3 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):
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

    output_data = {
        "step":
            "STEP 17-21-C-9-2-3A-3",

        "site":
            context,

        "source": {
            "provider":
                "서울특별시",
            "source_type":
                SEOUL_SOURCE_TYPE,
            "dataset_name":
                SEOUL_DATASET_NAME,
            "dataset_code":
                SEOUL_DATASET_CODE,
            "service_name":
                SEOUL_SERVICE_NAME,
            "spatial_crs":
                SEOUL_DATASET_CRS,
            "spatial_file_pattern":
                SEOUL_SPATIAL_FILE_PATTERN,
            "vworld_guess_probe":
                "STOPPED",
        },

        "api": {
            "environment_variable":
                env_name,
            "http_status":
                http_status,
            "query_status":
                query_status,
            "result_code":
                result_info.get(
                    "code",
                    "",
                ),
            "result_message":
                result_info.get(
                    "message",
                    "",
                ),
            "list_total_count":
                total_count,
            "received_rows":
                len(
                    rows
                ),
            "schema_fields":
                schema_fields,
            "geometry_available":
                geometry_available,
        },

        "target_sigungu": {
            "sigungu_code":
                context.get(
                    "sigungu_code",
                    "",
                ),
            "row_count":
                len(
                    target_sigungu_rows
                ),
            "rows": [
                summarize_row(
                    row
                )
                for row
                in target_sigungu_rows
            ],
        },

        "resolution": {
            "query_status":
                query_status,
            "resolution":
                resolution,
            "confidence":
                confidence,
            "reason":
                reason,
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

    if all_pass:

        print(
            "STEP 17-21-C-9-2-3A-3 완료"
        )

        print()

        print(
            "개발진흥지구 전용 Source 검증: ALL PASS"
        )

        print()

        print(
            "확정 Source:"
        )

        print(
            f"- 서울특별시 {SEOUL_DATASET_NAME}"
        )

        print(
            f"- 공간정보 코드: {SEOUL_DATASET_CODE}"
        )

        print(
            f"- OpenAPI service: {SEOUL_SERVICE_NAME}"
        )

        print(
            f"- 공간파일 CRS: {SEOUL_DATASET_CRS}"
        )

        print()

        print(
            "현재 개발진흥지구 resolution:"
        )

        print(
            "UNKNOWN"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-3B-1"
        )

        print(
            "→ 서울시 UQ129 개발진흥지구 SHP 공간파일 확보"
        )

        print(
            "→ EPSG:5174 → EPSG:4326 좌표계 변환"
        )

        print(
            "→ 기존 PNU Parcel Polygon 재사용"
        )

        print(
            "→ Parcel Polygon × 개발진흥지구 Polygon 실제 intersection"
        )

        print(
            "→ 실제 면적 교차 확인 시 TRUE"
        )

        print(
            "→ 전체 UQ129 공간레이어 정상 로드 + 교차 없음 확인 시 FALSE"
        )

    else:

        print(
            "STEP 17-21-C-9-2-3A-3 검증 미완료"
        )

        print()

        print(
            "FAIL 항목을 확인해야 합니다."
        )

        print()

        print(
            "개발진흥지구 resolution은 UNKNOWN을 유지합니다."
        )


if __name__ == "__main__":
    main()