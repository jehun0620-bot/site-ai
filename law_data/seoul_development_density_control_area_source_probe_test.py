import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-4A
# 개발밀도관리구역 공식 Source 탐색
#
# 핵심 원칙
# ------------------------------------------------------------
# 1. VWorld dataset 코드번호를 추측하지 않는다.
# 2. 서울시 공식 공간정보 목록 / 데이터 카탈로그를 조회한다.
# 3. "개발밀도관리구역" 의미가 명시적으로 확인된 후보만 저장한다.
# 4. source 탐색 단계에서는 SITE TRUE/FALSE를 판정하지 않는다.
# 5. source 미확정 시 UNKNOWN 유지.
# 6. OpenAPI / SHP / 공간정보 코드 등 후속 연결정보를 최대한 수집.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

SOURCE_REGISTRY_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_source_snapshot.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "seoul_development_density_control_area_source_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

PROJECT_ROOT = BASE_DIR.parent

load_dotenv(
    PROJECT_ROOT / ".env"
)

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)


# ============================================================
# 서울 OpenAPI
# ============================================================

SEOUL_API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

SPACE_INFO_SERVICE = "spaceInfoList"

CATALOG_SERVICE = "SearchCatalogService"


# ============================================================
# 탐색 키워드
# ============================================================

PRIMARY_KEYWORDS = [
    "개발밀도관리구역",
]

SECONDARY_KEYWORDS = [
    "개발밀도",
    "밀도관리구역",
    "개발 밀도 관리",
]

RELATED_KEYWORDS = [
    "도시계획",
    "공간정보",
    "용도구역",
    "용도지구",
]


# ============================================================
# 상수
# ============================================================

HTTP_TIMEOUT = 30

PAGE_SIZE = 1000

MAX_PAGES = 30

ALLOWED_QUERY_STATUS = {
    "NOT_CONNECTED",
    "NOT_QUERIED",
    "QUERY_FAILED",
    "QUERY_SUCCESS",
}

ALLOWED_RESOLUTION = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
}

ALLOWED_CONFIDENCE = {
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


def compact_spaces(
    text: Any,
) -> str:

    if text is None:
        return ""

    if not isinstance(
        text,
        str,
    ):
        text = str(text)

    text = text.replace(
        "\r",
        " ",
    )

    text = text.replace(
        "\n",
        " ",
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


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

            result = recursive_find_value(
                value,
                keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            result = recursive_find_value(
                value,
                keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    return None


def normalize_dict_keys(
    item: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        str(key).strip():
        value
        for key, value
        in item.items()
    }


def stringify_record(
    record: Dict[str, Any],
) -> str:

    parts = []

    for key, value in record.items():

        if isinstance(
            value,
            (
                dict,
                list,
            ),
        ):
            try:
                value_text = json.dumps(
                    value,
                    ensure_ascii=False,
                )
            except Exception:
                value_text = str(value)

        else:
            value_text = str(
                value
            )

        parts.append(
            f"{key}: {value_text}"
        )

    return compact_spaces(
        " ".join(
            parts
        )
    )


# ============================================================
# Query Context
# ============================================================

def extract_site_context(
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

    zone = recursive_find_value(
        data,
        [
            "zone",
            "용도지역",
        ],
    )

    pnu = recursive_find_value(
        data,
        [
            "pnu",
            "PNU",
        ],
    )

    sigungu_code = recursive_find_value(
        data,
        [
            "sigungu_code",
            "시군구코드",
        ],
    )

    return {
        "site_id": str(
            site_id or ""
        ),
        "address": str(
            address or ""
        ),
        "zone": str(
            zone or ""
        ),
        "pnu": str(
            pnu or ""
        ),
        "sigungu_code": str(
            sigungu_code or ""
        ),
    }


# ============================================================
# 서울 OpenAPI 공통
# ============================================================

def build_seoul_url(
    service: str,
    start_index: int,
    end_index: int,
) -> str:

    return (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{service}/"
        f"{start_index}/"
        f"{end_index}/"
    )


def request_json(
    url: str,
) -> Tuple[
    Optional[Dict[str, Any]],
    Dict[str, Any],
]:

    meta: Dict[str, Any] = {
        "url_masked": "",
        "http_status": None,
        "content_type": "",
        "error": "",
    }

    if SEOUL_OPEN_API_KEY:
        meta["url_masked"] = (
            url.replace(
                SEOUL_OPEN_API_KEY,
                "[HIDDEN]",
            )
        )
    else:
        meta["url_masked"] = url

    try:
        response = requests.get(
            url,
            timeout=HTTP_TIMEOUT,
        )

    except Exception as exc:

        meta["error"] = str(
            exc
        )

        return (
            None,
            meta,
        )

    meta["http_status"] = (
        response.status_code
    )

    meta["content_type"] = (
        response.headers.get(
            "Content-Type",
            "",
        )
    )

    if response.status_code != 200:

        meta["error"] = (
            f"HTTP {response.status_code}"
        )

        return (
            None,
            meta,
        )

    try:
        data = response.json()

    except Exception as exc:

        meta["error"] = (
            f"JSON parse error: {exc}"
        )

        return (
            None,
            meta,
        )

    return (
        data,
        meta,
    )


# ============================================================
# 서울 응답 구조 분석
# ============================================================

def find_service_object(
    data: Dict[str, Any],
    service_name: str,
) -> Optional[Dict[str, Any]]:

    if not isinstance(
        data,
        dict,
    ):
        return None

    # 정확 키 우선
    if (
        service_name in data
        and isinstance(
            data[service_name],
            dict,
        )
    ):
        return data[
            service_name
        ]

    # 대소문자 보정
    wanted = (
        service_name.lower()
    )

    for key, value in data.items():

        if (
            str(key).lower()
            == wanted
            and isinstance(
                value,
                dict,
            )
        ):
            return value

    return None


def get_result_info(
    service_obj: Dict[str, Any],
) -> Dict[str, str]:

    result = service_obj.get(
        "RESULT",
        {},
    )

    if not isinstance(
        result,
        dict,
    ):
        result = {}

    return {
        "code": str(
            result.get(
                "CODE",
                "",
            )
        ),
        "message": str(
            result.get(
                "MESSAGE",
                "",
            )
        ),
    }


def get_rows(
    service_obj: Dict[str, Any],
) -> List[Dict[str, Any]]:

    rows = service_obj.get(
        "row",
        [],
    )

    if isinstance(
        rows,
        dict,
    ):
        rows = [
            rows
        ]

    if not isinstance(
        rows,
        list,
    ):
        return []

    return [
        normalize_dict_keys(
            row
        )
        for row in rows
        if isinstance(
            row,
            dict,
        )
    ]


def get_total_count(
    service_obj: Dict[str, Any],
) -> int:

    raw = service_obj.get(
        "list_total_count",
        0,
    )

    try:
        return int(
            raw
        )

    except Exception:
        return 0


# ============================================================
# 전체 페이지 조회
# ============================================================

def fetch_all_rows(
    service_name: str,
) -> Dict[str, Any]:

    all_rows: List[
        Dict[str, Any]
    ] = []

    pages = []

    total_count = None

    service_confirmed = False

    normal_result_seen = False

    for page_index in range(
        MAX_PAGES
    ):

        start = (
            page_index
            * PAGE_SIZE
            + 1
        )

        end = (
            start
            + PAGE_SIZE
            - 1
        )

        url = build_seoul_url(
            service=service_name,
            start_index=start,
            end_index=end,
        )

        data, meta = request_json(
            url
        )

        page_info = {
            "page": page_index + 1,
            "start": start,
            "end": end,
            "http_status":
                meta.get(
                    "http_status"
                ),
            "content_type":
                meta.get(
                    "content_type"
                ),
            "error":
                meta.get(
                    "error"
                ),
            "url":
                meta.get(
                    "url_masked"
                ),
        }

        if data is None:

            pages.append(
                page_info
            )

            break

        service_obj = (
            find_service_object(
                data,
                service_name,
            )
        )

        if service_obj is None:

            page_info[
                "service_found"
            ] = False

            page_info[
                "response_preview"
            ] = compact_spaces(
                json.dumps(
                    data,
                    ensure_ascii=False,
                )
            )[:1000]

            pages.append(
                page_info
            )

            break

        service_confirmed = True

        page_info[
            "service_found"
        ] = True

        result_info = (
            get_result_info(
                service_obj
            )
        )

        page_info[
            "result_code"
        ] = result_info[
            "code"
        ]

        page_info[
            "result_message"
        ] = result_info[
            "message"
        ]

        if (
            result_info["code"]
            == "INFO-000"
        ):
            normal_result_seen = True

        rows = get_rows(
            service_obj
        )

        page_info[
            "row_count"
        ] = len(
            rows
        )

        current_total = (
            get_total_count(
                service_obj
            )
        )

        if (
            total_count is None
            and current_total
        ):
            total_count = (
                current_total
            )

        all_rows.extend(
            rows
        )

        pages.append(
            page_info
        )

        if not rows:
            break

        if (
            total_count is not None
            and len(
                all_rows
            )
            >= total_count
        ):
            break

        if len(
            rows
        ) < PAGE_SIZE:
            break

    return {
        "service": service_name,
        "service_confirmed":
            service_confirmed,
        "normal_result_seen":
            normal_result_seen,
        "total_count":
            total_count
            if total_count
            is not None
            else len(
                all_rows
            ),
        "received_count":
            len(
                all_rows
            ),
        "pages":
            pages,
        "rows":
            all_rows,
    }


# ============================================================
# 키워드 점수
# ============================================================

def keyword_match_detail(
    record: Dict[str, Any],
) -> Dict[str, Any]:

    text = stringify_record(
        record
    )

    primary_hits = [
        keyword
        for keyword
        in PRIMARY_KEYWORDS
        if keyword in text
    ]

    secondary_hits = [
        keyword
        for keyword
        in SECONDARY_KEYWORDS
        if keyword in text
    ]

    related_hits = [
        keyword
        for keyword
        in RELATED_KEYWORDS
        if keyword in text
    ]

    score = 0

    score += (
        len(
            primary_hits
        )
        * 100
    )

    score += (
        len(
            secondary_hits
        )
        * 30
    )

    score += (
        len(
            related_hits
        )
        * 5
    )

    explicit_semantic_match = (
        len(
            primary_hits
        )
        > 0
    )

    return {
        "score": score,
        "explicit_semantic_match":
            explicit_semantic_match,
        "primary_hits":
            primary_hits,
        "secondary_hits":
            secondary_hits,
        "related_hits":
            related_hits,
        "search_text":
            text,
    }


def collect_candidates(
    source_name: str,
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    candidates = []

    for index, row in enumerate(
        rows,
        start=1,
    ):

        detail = (
            keyword_match_detail(
                row
            )
        )

        if detail["score"] <= 0:
            continue

        candidates.append(
            {
                "source":
                    source_name,
                "row_index":
                    index,
                "score":
                    detail[
                        "score"
                    ],
                "explicit_semantic_match":
                    detail[
                        "explicit_semantic_match"
                    ],
                "primary_hits":
                    detail[
                        "primary_hits"
                    ],
                "secondary_hits":
                    detail[
                        "secondary_hits"
                    ],
                "related_hits":
                    detail[
                        "related_hits"
                    ],
                "record":
                    row,
            }
        )

    candidates.sort(
        key=lambda x: (
            0
            if x[
                "explicit_semantic_match"
            ]
            else 1,
            -x["score"],
            x["row_index"],
        )
    )

    return candidates


# ============================================================
# 후보 정보 추출
# ============================================================

NAME_KEYS = [
    "NAME",
    "DATA_NM",
    "DATA_NAME",
    "DATASET_NM",
    "DATASET_NAME",
    "SVC_NM",
    "SERVICE_NM",
    "TITLE",
    "SUBJECT",
    "목록명",
    "서비스명",
    "데이터셋명",
    "공간정보명",
]

SERVICE_KEYS = [
    "SERVICE",
    "SERVICE_NAME",
    "SVC_NM",
    "SVC_NAME",
    "OPENAPI_SERVICE",
    "API_SERVICE",
    "서비스명",
]

CODE_KEYS = [
    "CODE",
    "DATA_CD",
    "DATA_CODE",
    "LAYER_CD",
    "LAYER_CODE",
    "SPATIAL_CD",
    "공간정보코드",
]

URL_KEYS = [
    "URL",
    "LINK",
    "DATA_URL",
    "API_URL",
    "FILE_URL",
    "다운로드URL",
]


def find_value_from_record(
    record: Dict[str, Any],
    candidate_keys: List[str],
) -> str:

    upper_map = {
        str(key).upper():
        value
        for key, value
        in record.items()
    }

    for key in candidate_keys:

        value = upper_map.get(
            key.upper()
        )

        if value not in (
            None,
            "",
        ):
            return compact_spaces(
                value
            )

    return ""


def summarize_candidate(
    candidate: Dict[str, Any],
) -> Dict[str, Any]:

    record = candidate[
        "record"
    ]

    return {
        "source":
            candidate[
                "source"
            ],
        "row_index":
            candidate[
                "row_index"
            ],
        "score":
            candidate[
                "score"
            ],
        "explicit_semantic_match":
            candidate[
                "explicit_semantic_match"
            ],
        "name":
            find_value_from_record(
                record,
                NAME_KEYS,
            ),
        "service_name":
            find_value_from_record(
                record,
                SERVICE_KEYS,
            ),
        "spatial_code":
            find_value_from_record(
                record,
                CODE_KEYS,
            ),
        "url":
            find_value_from_record(
                record,
                URL_KEYS,
            ),
        "primary_hits":
            candidate[
                "primary_hits"
            ],
        "secondary_hits":
            candidate[
                "secondary_hits"
            ],
        "related_hits":
            candidate[
                "related_hits"
            ],
        "record":
            record,
    }


# ============================================================
# Source 확정 규칙
# ============================================================

def resolve_source_candidate(
    candidates: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    explicit = [
        candidate
        for candidate
        in candidates
        if candidate.get(
            "explicit_semantic_match"
        )
    ]

    if not explicit:

        return {
            "source_status":
                "UNRESOLVED",
            "selected":
                None,
            "reason":
                (
                    "서울시 공식 공간정보 목록 및 "
                    "데이터 카탈로그에서 "
                    "'개발밀도관리구역'을 명시적으로 "
                    "나타내는 전용 source를 찾지 못함"
                ),
        }

    # 가장 높은 점수 후보
    explicit.sort(
        key=lambda x: (
            -x.get(
                "score",
                0,
            ),
            x.get(
                "source",
                "",
            ),
            x.get(
                "row_index",
                0,
            ),
        )
    )

    selected = (
        explicit[0]
    )

    # 탐색 단계에서는 이름 명시만으로
    # 실제 공간판정 가능 source라고 단정하지 않는다.
    return {
        "source_status":
            "CANDIDATE_FOUND",
        "selected":
            selected,
        "reason":
            (
                "서울시 공식 목록에서 "
                "'개발밀도관리구역'이 명시된 "
                "후보 source를 발견함. "
                "다음 단계에서 OpenAPI 또는 "
                "공간파일 geometry 제공 여부를 "
                "별도로 검증해야 함"
            ),
    }


# ============================================================
# Registry 기존 상태
# ============================================================

def find_registry_condition(
    registry: Any,
    condition_name: str,
) -> Optional[Dict[str, Any]]:

    if isinstance(
        registry,
        dict,
    ):

        # 현재 node 자체 검사
        name = registry.get(
            "condition"
        )

        if (
            name
            == condition_name
        ):
            return registry

        name = registry.get(
            "name"
        )

        if (
            name
            == condition_name
            and (
                "query_status"
                in registry
                or "resolution"
                in registry
            )
        ):
            return registry

        for value in registry.values():

            result = (
                find_registry_condition(
                    value,
                    condition_name,
                )
            )

            if result is not None:
                return result

    elif isinstance(
        registry,
        list,
    ):

        for value in registry:

            result = (
                find_registry_condition(
                    value,
                    condition_name,
                )
            )

            if result is not None:
                return result

    return None


# ============================================================
# 로그
# ============================================================

def print_candidate(
    candidate: Dict[str, Any],
    index: int,
) -> None:

    print(
        "-" * 70
    )

    print(
        f"후보 {index}"
    )

    print(
        "source:",
        candidate.get(
            "source",
            "",
        ),
    )

    print(
        "score:",
        candidate.get(
            "score",
            0,
        ),
    )

    print(
        "explicit semantic match:",
        candidate.get(
            "explicit_semantic_match",
            False,
        ),
    )

    if candidate.get(
        "name"
    ):
        print(
            "name:",
            candidate[
                "name"
            ],
        )

    if candidate.get(
        "service_name"
    ):
        print(
            "service:",
            candidate[
                "service_name"
            ],
        )

    if candidate.get(
        "spatial_code"
    ):
        print(
            "spatial code:",
            candidate[
                "spatial_code"
            ],
        )

    if candidate.get(
        "url"
    ):
        print(
            "url:",
            candidate[
                "url"
            ],
        )

    if candidate.get(
        "primary_hits"
    ):
        print(
            "primary keyword:",
            ", ".join(
                candidate[
                    "primary_hits"
                ]
            ),
        )

    if candidate.get(
        "secondary_hits"
    ):
        print(
            "secondary keyword:",
            ", ".join(
                candidate[
                    "secondary_hits"
                ]
            ),
        )

    print(
        "record:"
    )

    record = candidate.get(
        "record",
        {},
    )

    for key, value in record.items():

        print(
            f"  {key}: {value}"
        )


# ============================================================
# 검증
# ============================================================

def run_validations(
    site: Dict[str, str],
    space_result: Dict[str, Any],
    catalog_result: Dict[str, Any],
    source_resolution:
        Dict[str, Any],
    final_status:
        Dict[str, Any],
) -> Dict[str, bool]:

    selected = (
        source_resolution.get(
            "selected"
        )
    )

    return {
        "서울 OpenAPI Key 존재":
            bool(
                SEOUL_OPEN_API_KEY
            ),

        "SITE 주소 존재":
            bool(
                site.get(
                    "address"
                )
            ),

        "PNU 19자리":
            (
                len(
                    site.get(
                        "pnu",
                        "",
                    )
                )
                == 19
                and site[
                    "pnu"
                ].isdigit()
            ),

        "서울 공간정보 목록 조회 실행":
            bool(
                space_result.get(
                    "pages"
                )
            ),

        "서울 카탈로그 조회 실행":
            bool(
                catalog_result.get(
                    "pages"
                )
            ),

        "source 미확정 시 UNKNOWN 유지":
            (
                source_resolution.get(
                    "source_status"
                )
                != "UNRESOLVED"
                or final_status.get(
                    "resolution"
                )
                == "UNKNOWN"
            ),

        "source 후보만으로 SITE TRUE 금지":
            (
                final_status.get(
                    "resolution"
                )
                != "TRUE"
            ),

        "source 후보만으로 SITE FALSE 금지":
            (
                final_status.get(
                    "resolution"
                )
                != "FALSE"
            ),

        "후보 선택 시 명시적 semantic match":
            (
                selected is None
                or selected.get(
                    "explicit_semantic_match"
                )
                is True
            ),

        "resolution 허용값":
            (
                final_status.get(
                    "resolution"
                )
                in ALLOWED_RESOLUTION
            ),

        "query_status 허용값":
            (
                final_status.get(
                    "query_status"
                )
                in ALLOWED_QUERY_STATUS
            ),

        "confidence 허용값":
            (
                final_status.get(
                    "confidence"
                )
                in ALLOWED_CONFIDENCE
            ),
    }


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-4A "
        "개발밀도관리구역 공식 Source 탐색 ==="
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
        "Source Registry 입력:"
    )
    print(
        SOURCE_REGISTRY_PATH
    )
    print()

    if not QUERY_CONTEXT_PATH.exists():

        raise FileNotFoundError(
            (
                "Query Context 파일이 없습니다: "
                f"{QUERY_CONTEXT_PATH}"
            )
        )

    query_context = load_json(
        QUERY_CONTEXT_PATH
    )

    site = extract_site_context(
        query_context
    )

    registry = {}

    if SOURCE_REGISTRY_PATH.exists():

        registry = load_json(
            SOURCE_REGISTRY_PATH
        )

    existing_condition = (
        find_registry_condition(
            registry,
            "개발밀도관리구역",
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
        site.get(
            "site_id"
        )
        or "-",
    )

    print(
        "주소:",
        site.get(
            "address"
        )
        or "-",
    )

    print(
        "용도지역:",
        site.get(
            "zone"
        )
        or "-",
    )

    print(
        "시군구코드:",
        site.get(
            "sigungu_code"
        )
        or "-",
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        )
        or "-",
    )
    print()

    if existing_condition:

        print(
            "기존 개발밀도관리구역 상태:"
        )

        print(
            "query_status:",
            existing_condition.get(
                "query_status",
                "-",
            ),
        )

        print(
            "resolution:",
            existing_condition.get(
                "resolution",
                "-",
            ),
        )

        print()

    # --------------------------------------------------------
    # 인증
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 서울 OpenAPI 인증 ==="
    )
    print_separator()

    if SEOUL_OPEN_API_KEY:

        print(
            "SEOUL_OPEN_API_KEY: "
            "정상적으로 읽었습니다."
        )

    else:

        print(
            "SEOUL_OPEN_API_KEY: 없음"
        )

        raise RuntimeError(
            (
                "SEOUL_OPEN_API_KEY를 "
                ".env에서 찾을 수 없습니다."
            )
        )

    print()

    # --------------------------------------------------------
    # 1. 서울 공간정보 목록
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 서울시 공간정보 목록 조회 ==="
    )
    print_separator()

    space_result = (
        fetch_all_rows(
            SPACE_INFO_SERVICE
        )
    )

    print(
        "service:",
        SPACE_INFO_SERVICE,
    )

    print(
        "service 확인:",
        space_result[
            "service_confirmed"
        ],
    )

    print(
        "정상 응답 확인:",
        space_result[
            "normal_result_seen"
        ],
    )

    print(
        "전체 데이터 수:",
        space_result[
            "total_count"
        ],
    )

    print(
        "현재 받은 row 수:",
        space_result[
            "received_count"
        ],
    )
    print()

    # --------------------------------------------------------
    # 2. 서울 데이터 카탈로그
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. 서울 열린데이터 카탈로그 조회 ==="
    )
    print_separator()

    catalog_result = (
        fetch_all_rows(
            CATALOG_SERVICE
        )
    )

    print(
        "service:",
        CATALOG_SERVICE,
    )

    print(
        "service 확인:",
        catalog_result[
            "service_confirmed"
        ],
    )

    print(
        "정상 응답 확인:",
        catalog_result[
            "normal_result_seen"
        ],
    )

    print(
        "전체 데이터 수:",
        catalog_result[
            "total_count"
        ],
    )

    print(
        "현재 받은 row 수:",
        catalog_result[
            "received_count"
        ],
    )
    print()

    # --------------------------------------------------------
    # 3. 개발밀도관리구역 후보 검색
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 3. 개발밀도관리구역 후보 검색 ==="
    )
    print_separator()

    space_candidates_raw = (
        collect_candidates(
            SPACE_INFO_SERVICE,
            space_result[
                "rows"
            ],
        )
    )

    catalog_candidates_raw = (
        collect_candidates(
            CATALOG_SERVICE,
            catalog_result[
                "rows"
            ],
        )
    )

    all_candidates_raw = (
        space_candidates_raw
        + catalog_candidates_raw
    )

    all_candidates_raw.sort(
        key=lambda x: (
            0
            if x[
                "explicit_semantic_match"
            ]
            else 1,
            -x["score"],
            x["source"],
            x["row_index"],
        )
    )

    summarized_candidates = [
        summarize_candidate(
            candidate
        )
        for candidate
        in all_candidates_raw
    ]

    explicit_candidates = [
        candidate
        for candidate
        in summarized_candidates
        if candidate[
            "explicit_semantic_match"
        ]
    ]

    print(
        "전체 관련 후보:",
        len(
            summarized_candidates
        ),
    )

    print(
        "'개발밀도관리구역' 명시 후보:",
        len(
            explicit_candidates
        ),
    )
    print()

    for index, candidate in enumerate(
        summarized_candidates[:20],
        start=1,
    ):

        print_candidate(
            candidate,
            index,
        )

        print()

    # --------------------------------------------------------
    # 4. Source 후보 판정
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 4. Source 의미 판정 ==="
    )
    print_separator()

    source_resolution = (
        resolve_source_candidate(
            summarized_candidates
        )
    )

    print(
        "source_status:",
        source_resolution[
            "source_status"
        ],
    )

    print(
        "reason:",
        source_resolution[
            "reason"
        ],
    )

    selected = (
        source_resolution.get(
            "selected"
        )
    )

    if selected:

        print()

        print(
            "선택 후보:"
        )

        print(
            "source:",
            selected.get(
                "source",
                "-",
            ),
        )

        print(
            "name:",
            selected.get(
                "name",
                "-",
            )
            or "-",
        )

        print(
            "service:",
            selected.get(
                "service_name",
                "-",
            )
            or "-",
        )

        print(
            "spatial code:",
            selected.get(
                "spatial_code",
                "-",
            )
            or "-",
        )

    print()

    # --------------------------------------------------------
    # 5. SITE 상태
    #
    # Source 탐색만 했으므로 무조건 UNKNOWN.
    # --------------------------------------------------------

    if (
        source_resolution[
            "source_status"
        ]
        == "CANDIDATE_FOUND"
    ):

        query_status = (
            "NOT_QUERIED"
        )

        reason = (
            "개발밀도관리구역 공식 source 후보를 "
            "발견했으나 geometry 제공 여부와 "
            "대상 Parcel Polygon 공간교차를 아직 "
            "검증하지 않았으므로 TRUE/FALSE를 "
            "판정하지 않음"
        )

    else:

        query_status = (
            "NOT_CONNECTED"
        )

        reason = (
            "서울시 공식 공간정보 목록 및 "
            "데이터 카탈로그에서 "
            "개발밀도관리구역 전용 source가 "
            "확정되지 않아 실제 공간조회를 "
            "수행하지 않음"
        )

    final_status = {
        "condition":
            "개발밀도관리구역",
        "query_group":
            "URBAN_PLANNING_ZONE",
        "query_status":
            query_status,
        "resolution":
            "UNKNOWN",
        "confidence":
            "NONE",
        "reason":
            reason,
    }

    print_separator()
    print(
        "=== 5. 현재 개발밀도관리구역 SITE 판정 ==="
    )
    print_separator()

    print(
        "query_status:",
        final_status[
            "query_status"
        ],
    )

    print(
        "resolution:",
        final_status[
            "resolution"
        ],
    )

    print(
        "confidence:",
        final_status[
            "confidence"
        ],
    )

    print(
        "reason:",
        final_status[
            "reason"
        ],
    )
    print()

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = (
        run_validations(
            site=site,
            space_result=
                space_result,
            catalog_result=
                catalog_result,
            source_resolution=
                source_resolution,
            final_status=
                final_status,
        )
    )

    print_separator()
    print(
        "=== C-9-2-4A 검증 ==="
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
    # 저장용으로 API 원문 전체 row는 지나치게 크므로
    # 탐색 metadata + 후보만 저장한다.
    # --------------------------------------------------------

    output_data = {
        "step":
            "STEP 17-21-C-9-2-4A",

        "site":
            site,

        "target_condition":
            "개발밀도관리구역",

        "search_policy": {
            "vworld_numeric_guessing":
                False,
            "official_catalog_first":
                True,
            "true_false_during_source_probe":
                False,
        },

        "official_sources": {
            "space_info": {
                "provider":
                    "서울특별시",
                "service":
                    SPACE_INFO_SERVICE,
                "service_confirmed":
                    space_result[
                        "service_confirmed"
                    ],
                "normal_result_seen":
                    space_result[
                        "normal_result_seen"
                    ],
                "total_count":
                    space_result[
                        "total_count"
                    ],
                "received_count":
                    space_result[
                        "received_count"
                    ],
                "pages":
                    space_result[
                        "pages"
                    ],
            },

            "catalog": {
                "provider":
                    "서울특별시",
                "service":
                    CATALOG_SERVICE,
                "service_confirmed":
                    catalog_result[
                        "service_confirmed"
                    ],
                "normal_result_seen":
                    catalog_result[
                        "normal_result_seen"
                    ],
                "total_count":
                    catalog_result[
                        "total_count"
                    ],
                "received_count":
                    catalog_result[
                        "received_count"
                    ],
                "pages":
                    catalog_result[
                        "pages"
                    ],
            },
        },

        "keywords": {
            "primary":
                PRIMARY_KEYWORDS,
            "secondary":
                SECONDARY_KEYWORDS,
            "related":
                RELATED_KEYWORDS,
        },

        "candidate_summary": {
            "total":
                len(
                    summarized_candidates
                ),
            "explicit":
                len(
                    explicit_candidates
                ),
        },

        "candidates":
            summarized_candidates[:100],

        "source_resolution":
            source_resolution,

        "site_resolution":
            final_status,

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

    # --------------------------------------------------------
    # 다음 단계 안내
    # --------------------------------------------------------

    if not all_pass:

        print(
            "STEP 17-21-C-9-2-4A "
            "검증 실패"
        )

        print()

        print(
            "FAIL 항목을 먼저 확인합니다."
        )

        return

    print(
        "STEP 17-21-C-9-2-4A 완료"
    )
    print()

    print(
        "개발밀도관리구역 공식 Source "
        "탐색 프레임 검증: ALL PASS"
    )
    print()

    if (
        source_resolution[
            "source_status"
        ]
        == "CANDIDATE_FOUND"
    ):

        print(
            "공식 Source 후보가 발견되었습니다."
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-4B"
        )

        print(
            "→ 후보 데이터셋 상세 schema 확인"
        )

        print(
            "→ OpenAPI service / 공간정보 코드 확인"
        )

        print(
            "→ SHP/GeoJSON geometry 확보 가능 여부 확인"
        )

        print(
            "→ 기존 PNU Parcel Polygon과 intersection"
        )

        print(
            "→ 실제 교차 시 TRUE"
        )

        print(
            "→ 전체 레이어 정상조회 + 교차 없음 시 FALSE"
        )

    else:

        print(
            "개발밀도관리구역 전용 Source는 "
            "아직 확정되지 않았습니다."
        )

        print()

        print(
            "현재 resolution:"
        )

        print(
            "UNKNOWN"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-4A-1"
        )

        print(
            "→ 국가공간정보 / 토지이용규제정보 "
            "공식 source 확장 탐색"
        )

        print(
            "→ 서울시 카탈로그에 없는 경우 "
            "국가 단위 source로 전환"
        )

        print(
            "→ source 확보 전까지 UNKNOWN 유지"
        )


if __name__ == "__main__":
    main()