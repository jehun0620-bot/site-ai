import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-2B-1B
# VWorld 지구단위계획 Data API 실제 data 식별자 탐색
#
# 목적
# ------------------------------------------------------------
# 1. upisuq161 = 안내페이지 svcIde임을 분리
# 2. req/data API가 실제 허용하는 data 값을 탐색
# 3. 후보별 HTTP / VWorld status / error 기록
# 4. QUERY_SUCCESS 후보만 별도 저장
# 5. 여기서는 지구단위계획 TRUE/FALSE 판정하지 않음
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
    / "vworld_data_identifier_probe.json"
)

ENV_PATH = (
    PROJECT_ROOT
    / ".env"
)


VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

REQUEST_TIMEOUT = 30


# ============================================================
# 후보 식별자
#
# 주의:
# 아래는 "정답" 목록이 아니라 탐색용 후보군이다.
# 성공 여부는 반드시 API 응답으로 확인한다.
# ============================================================

DATASET_CANDIDATES = [
    # 기존 시도
    "LT_C_UQ161",
    "upisuq161",
    "UPISUQ161",

    # VWorld/UPIS 계열에서 흔히 나타나는 표기 변형 탐색
    "LT_C_UPISUQ161",
    "LT_C_UPIS_UQ161",
    "LT_C_UQ_161",
    "LT_C_UQ161_1",

    # 숫자 코드 계열 가능성 진단
    "UQ161",
    "UQ_161",

    # 서비스명이 직접 등록된 경우 대비
    "district_unit_plan",
    "DISTRICT_UNIT_PLAN",
]


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
    length: int = 500,
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
    keys: List[str],
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
# HTTP
# ============================================================

def request_result(
    response: requests.Response,
) -> Dict[str, Any]:

    result = {
        "status_code":
            response.status_code,

        "content_type":
            response.headers.get(
                "Content-Type",
                "",
            ),

        "url":
            response.url,

        "json":
            None,

        "preview":
            safe_preview(
                response.text
            ),

        "exception":
            None,
    }

    try:

        result["json"] = (
            response.json()
        )

    except Exception:
        pass

    return result


# ============================================================
# VWorld status
# ============================================================

def extract_vworld_status(
    result: Dict[str, Any],
) -> Dict[str, str]:

    output = {
        "status": "",
        "error_code": "",
        "error_text": "",
    }

    data = result.get(
        "json"
    )

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
# 주소검색
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

        return request_result(
            response
        )

    except requests.RequestException as exc:

        return {
            "status_code": None,
            "content_type": "",
            "url": "",
            "json": None,
            "preview": "",
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

    if response.get(
        "status"
    ) != "OK":
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

    try:

        return (
            float(
                point["x"]
            ),
            float(
                point["y"]
            ),
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ):
        return None


# ============================================================
# Data API 후보 조회
# ============================================================

def probe_dataset(
    api_key: str,
    dataset: str,
    x: float,
    y: float,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "version": "2.0",

        "data": dataset,

        "key": api_key,

        "geometry": "true",
        "attribute": "true",

        "size": 10,
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

        result = request_result(
            response
        )

    except requests.RequestException as exc:

        result = {
            "status_code": None,
            "content_type": "",
            "url": "",
            "json": None,
            "preview": "",
            "exception": str(exc),
        }

    status = extract_vworld_status(
        result
    )

    return {
        "dataset": dataset,

        "http_status":
            result.get(
                "status_code"
            ),

        "vworld_status":
            status.get(
                "status"
            ),

        "error_code":
            status.get(
                "error_code"
            ),

        "error_text":
            status.get(
                "error_text"
            ),

        "preview":
            result.get(
                "preview",
                "",
            ),

        "url":
            result.get(
                "url",
                "",
            ),

        "exception":
            result.get(
                "exception"
            ),

        "success":
            (
                result.get(
                    "status_code"
                )
                == 200
                and
                status.get(
                    "status"
                )
                == "OK"
            ),
    }


# ============================================================
# 오류 유형 분류
# ============================================================

def classify_probe_result(
    probe: Dict[str, Any],
) -> str:

    if probe.get(
        "exception"
    ):
        return "REQUEST_EXCEPTION"

    if probe.get(
        "http_status"
    ) != 200:
        return "HTTP_ERROR"

    if probe.get(
        "success"
    ):
        return "QUERY_SUCCESS"

    error_code = probe.get(
        "error_code"
    )

    if error_code == "INVALID_RANGE":
        return "INVALID_DATA_IDENTIFIER"

    if error_code:
        return (
            "VWORLD_ERROR_"
            + error_code
        )

    return "UNKNOWN_RESPONSE"


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-2B-1B "
        "VWorld Data API 실제 data 식별자 탐색 ==="
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

    context = extract_query_context(
        query_context_data
    )

    address = context.get(
        "address",
        ""
    )

    pnu = context.get(
        "pnu",
        ""
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

    print()

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
            "VWORLD_API_KEY: 없음"
        )

    print()

    # --------------------------------------------------------
    # 주소 좌표 확보
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 대표 좌표 확보 ==="
    )
    print_separator()

    if (
        api_key
        and address
    ):

        address_result = query_address(
            api_key=api_key,
            address=address,
        )

    else:

        address_result = {
            "status_code": None,
            "json": None,
            "exception":
                "API KEY 또는 주소 없음",
        }

    coordinate = extract_coordinate(
        address_result
    )

    address_status = extract_vworld_status(
        address_result
    )

    print(
        "HTTP 상태:",
        address_result.get(
            "status_code"
        )
    )

    print(
        "VWorld status:",
        address_status.get(
            "status"
        )
        or "-"
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

    if not coordinate:

        raise RuntimeError(
            "대표좌표를 얻지 못했으므로 "
            "dataset 탐색을 진행할 수 없습니다."
        )

    x, y = coordinate

    # --------------------------------------------------------
    # 후보 dataset 탐색
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. Data API 식별자 후보 탐색 ==="
    )
    print_separator()

    print(
        "후보 수:",
        len(
            DATASET_CANDIDATES
        )
    )

    print()

    probes: List[
        Dict[str, Any]
    ] = []

    for index, dataset in enumerate(
        DATASET_CANDIDATES,
        start=1,
    ):

        print(
            "-" * 70
        )

        print(
            f"[{index}] dataset: "
            f"{dataset}"
        )

        probe = probe_dataset(
            api_key=api_key,
            dataset=dataset,
            x=x,
            y=y,
        )

        probe[
            "classification"
        ] = classify_probe_result(
            probe
        )

        probes.append(
            probe
        )

        print(
            "HTTP:",
            probe.get(
                "http_status"
            )
        )

        print(
            "VWorld status:",
            probe.get(
                "vworld_status"
            )
            or "-"
        )

        print(
            "classification:",
            probe.get(
                "classification"
            )
        )

        if probe.get(
            "error_code"
        ):

            print(
                "error code:",
                probe.get(
                    "error_code"
                )
            )

        if probe.get(
            "error_text"
        ):

            print(
                "error text:",
                probe.get(
                    "error_text"
                )
            )

        if probe.get(
            "success"
        ):

            print(
                ">>> QUERY_SUCCESS 후보 발견"
            )

        print()

    # --------------------------------------------------------
    # 결과 분석
    # --------------------------------------------------------

    successful = [
        probe
        for probe in probes
        if probe.get(
            "success"
        )
    ]

    invalid = [
        probe
        for probe in probes
        if probe.get(
            "classification"
        )
        == "INVALID_DATA_IDENTIFIER"
    ]

    other_errors = [
        probe
        for probe in probes
        if (
            not probe.get(
                "success"
            )
            and probe.get(
                "classification"
            )
            != "INVALID_DATA_IDENTIFIER"
        )
    ]

    print_separator()
    print(
        "=== 탐색 결과 요약 ==="
    )
    print_separator()

    print(
        "전체 후보:",
        len(
            probes
        )
    )

    print(
        "QUERY_SUCCESS:",
        len(
            successful
        )
    )

    print(
        "INVALID_DATA_IDENTIFIER:",
        len(
            invalid
        )
    )

    print(
        "기타 오류:",
        len(
            other_errors
        )
    )

    print()

    if successful:

        print(
            "성공 후보:"
        )

        for probe in successful:

            print(
                "-",
                probe.get(
                    "dataset"
                )
            )

    else:

        print(
            "성공 후보: 없음"
        )

    print()

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = {
        "VWORLD API Key 존재":
            bool(
                api_key
            ),

        "SITE 주소 존재":
            bool(
                address
            ),

        "PNU 19자리":
            (
                len(
                    pnu
                )
                == 19
                and pnu.isdigit()
            ),

        "대표 좌표 획득":
            coordinate is not None,

        "후보 전체 조회 실행":
            (
                len(
                    probes
                )
                ==
                len(
                    DATASET_CANDIDATES
                )
            ),

        "각 후보 응답 분류 완료":
            all(
                bool(
                    probe.get(
                        "classification"
                    )
                )
                for probe in probes
            ),

        "실패 후보 TRUE/FALSE 판정 없음":
            True,
    }

    print_separator()
    print(
        "=== C-9-2-2B-1B 검증 ==="
    )
    print_separator()

    for name, passed in validations.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # resolution
    # --------------------------------------------------------

    resolution = {
        "condition":
            "지구단위계획",

        "status":
            "UNKNOWN",

        "confidence":
            "NONE",

        "reason":
            (
                "실제 지구단위계획 도형과 "
                "대상 필지의 공간교차 검증 전이므로 "
                "TRUE/FALSE를 확정하지 않음"
            ),
    }

    # --------------------------------------------------------
    # 결과 저장
    # --------------------------------------------------------

    output_data = {
        "step":
            "STEP 17-21-C-9-2-2B-1B",

        "site": context,

        "coordinate": {
            "x": x,
            "y": y,
        },

        "candidate_count":
            len(
                DATASET_CANDIDATES
            ),

        "successful_datasets": [
            probe.get(
                "dataset"
            )
            for probe in successful
        ],

        "probes":
            probes,

        "validations":
            validations,

        "all_pass":
            all_pass,

        "resolution":
            resolution,
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
    # 다음 단계 판단
    # --------------------------------------------------------

    if successful:

        print(
            "STEP 17-21-C-9-2-2B-1B 완료"
        )

        print()

        print(
            "req/data에서 허용되는 후보를 찾았습니다."
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-2B-2"
        )

        print(
            "→ 성공 dataset FeatureCollection 구조 분석"
        )

        print(
            "→ geometry 추출"
        )

        print(
            "→ 대상 좌표 point-in-polygon 확인"
        )

        print(
            "→ 필지 polygon 확보 후 실제 intersection으로 보강"
        )

        print(
            "→ 교차 확인 시에만 TRUE"
        )

        print(
            "→ 정상 조회 + 교차 없음 확인 시에만 FALSE"
        )

    else:

        print(
            "STEP 17-21-C-9-2-2B-1B 탐색 종료"
        )

        print()

        print(
            "현재 후보군에서는 req/data용 "
            "유효 식별자를 찾지 못했습니다."
        )

        print()

        print(
            "지구단위계획 상태는 UNKNOWN 유지"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-2B-1C"
        )

        print(
            "→ VWorld req/data 방식 중단 여부 판단"
        )

        print(
            "→ WFS/WMS 또는 현재 데이터 API 서비스 목록 기반 조회로 전환"
        )

        print(
            "→ 서울시 도시계획 공간정보를 병행 source로 검토"
        )


if __name__ == "__main__":
    main()