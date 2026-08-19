# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-5A
서울시 자연경관지구 공식 Source 탐색 / 의미 검증

목표
------------------------------------------------------------
1. 서울 열린데이터광장 SearchCatalogService 조회
2. '서울시 용도지구(경관지구) 공간정보' 공식 dataset 확인
3. 자연경관지구가 별도 dataset인지,
   경관지구 dataset 내부 속성 분류인지 확인
4. OpenAPI service / 공간정보 코드 후보를 추측하지 않고
   공식 카탈로그 정보만 저장
5. geometry 공간교차 전에는 SITE TRUE/FALSE 판정 금지

현재 대상 SITE
------------------------------------------------------------
서울특별시 강남구 개포동 12번지
PNU: 1168010300100120000
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


# ============================================================
# 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

SOURCE_REGISTRY_PATH = (
    OUTPUT_DIR
    / "site_spatial_source_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_natural_landscape_district_source_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(BASE_DIR / ".env")

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)


# ============================================================
# 서울 열린데이터광장
# ============================================================

SEOUL_API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

CATALOG_SERVICE = "SearchCatalogService"

REQUEST_TIMEOUT = 30


# ============================================================
# 검색어
# ============================================================

TARGET_CONDITION = "자연경관지구"

SEARCH_KEYWORDS = [
    "자연경관지구",
    "경관지구",
    "용도지구(경관지구)",
]


# ============================================================
# 공통 함수
# ============================================================

def load_json(path: Path) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Dict[str, Any],
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


def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    text = (
        text
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def first_nonempty(
    *values: Any,
) -> Any:

    for value in values:

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


# ============================================================
# SITE Context
# ============================================================

def extract_site_context(
    context: Dict[str, Any],
) -> Dict[str, str]:

    candidates = [
        context,
        context.get("site", {}),
        context.get("query_context", {}),
        context.get("target_site", {}),
    ]

    site_id = None
    address = None
    zoning = None
    pnu = None
    sigungu_code = None

    for item in candidates:

        if not isinstance(
            item,
            dict,
        ):
            continue

        site_id = first_nonempty(
            site_id,
            item.get("site_id"),
            item.get("SITE_ID"),
            item.get("parcel_key"),
        )

        address = first_nonempty(
            address,
            item.get("address"),
            item.get("jibun_address"),
        )

        zoning = first_nonempty(
            zoning,
            item.get("zoning"),
            item.get("use_zone"),
            item.get("land_use_zone"),
        )

        pnu = first_nonempty(
            pnu,
            item.get("pnu"),
            item.get("PNU"),
        )

        sigungu_code = first_nonempty(
            sigungu_code,
            item.get("sigungu_code"),
            item.get("sgg_code"),
        )

    if (
        not sigungu_code
        and isinstance(pnu, str)
        and len(pnu) >= 5
    ):
        sigungu_code = pnu[:5]

    return {
        "site_id": str(site_id or "-"),
        "address": str(address or "-"),
        "zoning": str(zoning or "-"),
        "pnu": str(pnu or "-"),
        "sigungu_code":
            str(sigungu_code or "-"),
    }


# ============================================================
# 서울 API
# ============================================================

def call_seoul_api(
    service: str,
    start_index: int,
    end_index: int,
) -> Dict[str, Any]:

    if not SEOUL_OPEN_API_KEY:
        raise RuntimeError(
            "SEOUL_OPEN_API_KEY를 "
            "환경변수에서 찾을 수 없습니다."
        )

    url = (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{service}/"
        f"{start_index}/"
        f"{end_index}/"
    )

    try:

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        try:
            payload = response.json()
        except Exception:
            payload = {}

        return {
            "url": url,
            "http_status":
                response.status_code,
            "content_type":
                content_type,
            "payload":
                payload,
            "text_preview":
                response.text[:1000],
            "error":
                None,
        }

    except requests.RequestException as exc:

        return {
            "url": url,
            "http_status":
                None,
            "content_type":
                None,
            "payload":
                {},
            "text_preview":
                "",
            "error":
                str(exc),
        }


def extract_service_object(
    payload: Dict[str, Any],
    service: str,
) -> Optional[Dict[str, Any]]:

    obj = payload.get(service)

    if isinstance(
        obj,
        dict,
    ):
        return obj

    # 대소문자 차이를 방어
    for key, value in payload.items():

        if (
            str(key).lower()
            == service.lower()
            and isinstance(
                value,
                dict,
            )
        ):
            return value

    return None


def load_catalog_rows() -> Dict[str, Any]:

    first = call_seoul_api(
        CATALOG_SERVICE,
        1,
        1000,
    )

    service_obj = (
        extract_service_object(
            first["payload"],
            CATALOG_SERVICE,
        )
    )

    if not service_obj:

        return {
            "success": False,
            "first": first,
            "rows": [],
            "total_count": 0,
            "reason":
                "SearchCatalogService 객체를 "
                "응답에서 찾지 못함",
        }

    result = service_obj.get(
        "RESULT",
        {},
    )

    code = result.get(
        "CODE"
    )

    total_count = int(
        service_obj.get(
            "list_total_count",
            0,
        )
        or 0
    )

    if code != "INFO-000":

        return {
            "success": False,
            "first": first,
            "rows": [],
            "total_count":
                total_count,
            "reason":
                result.get(
                    "MESSAGE",
                    "서울 API 오류",
                ),
        }

    rows: List[Dict[str, Any]] = []

    # 전체 catalog을 가져온다.
    #
    # 서울 API는 일반적으로 한 번에
    # 너무 큰 범위를 주기보다 chunk 조회가 안전하다.
    chunk_size = 1000

    for start in range(
        1,
        total_count + 1,
        chunk_size,
    ):

        end = min(
            start + chunk_size - 1,
            total_count,
        )

        result_part = call_seoul_api(
            CATALOG_SERVICE,
            start,
            end,
        )

        obj = extract_service_object(
            result_part["payload"],
            CATALOG_SERVICE,
        )

        if not obj:
            continue

        part_rows = obj.get(
            "row",
            [],
        )

        if isinstance(
            part_rows,
            list,
        ):
            rows.extend(
                part_rows
            )

    return {
        "success": True,
        "first": first,
        "rows": rows,
        "total_count":
            total_count,
        "reason":
            "정상 처리",
    }


# ============================================================
# Catalog 분석
# ============================================================

def row_search_text(
    row: Dict[str, Any],
) -> str:

    important_fields = [
        "INF_ID",
        "INF_NM",
        "CATE_NM",
        "DITC_NM",
        "MAP_CATE_NM",
        "MNG_ORGAN_NAME",
        "MNG_STATION_NAME",
        "LINK_DESC",
        "LINK_INFO",
        "SRV_TYPE",
    ]

    values = []

    for field in important_fields:

        value = row.get(field)

        if value is not None:
            values.append(
                normalize_text(value)
            )

    return " ".join(values)


def score_candidate(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = row_search_text(
        row
    )

    name = normalize_text(
        row.get(
            "INF_NM"
        )
    )

    score = 0

    explicit_natural = False
    landscape_dataset = False

    if TARGET_CONDITION in text:
        score += 100
        explicit_natural = True

    if "용도지구(경관지구)" in text:
        score += 80
        landscape_dataset = True

    elif "경관지구" in text:
        score += 50
        landscape_dataset = True

    if "공간정보" in name:
        score += 20

    if (
        "서울특별시"
        in text
        or "서울시"
        in text
    ):
        score += 10

    if "도시관리" in text:
        score += 5

    return {
        "score":
            score,

        "explicit_natural_landscape":
            explicit_natural,

        "landscape_district_dataset":
            landscape_dataset,
    }


def find_candidates(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    candidates = []

    for row in rows:

        result = score_candidate(
            row
        )

        if result["score"] <= 0:
            continue

        candidates.append(
            {
                "score":
                    result["score"],

                "explicit_natural_landscape":
                    result[
                        "explicit_natural_landscape"
                    ],

                "landscape_district_dataset":
                    result[
                        "landscape_district_dataset"
                    ],

                "record":
                    row,
            }
        )

    candidates.sort(
        key=lambda x: (
            x["score"],
            normalize_text(
                x[
                    "record"
                ].get(
                    "INF_NM"
                )
            ),
        ),
        reverse=True,
    )

    return candidates


# ============================================================
# Source 판정
# ============================================================

def determine_source(
    candidates: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    # 1순위:
    # 자연경관지구라는 명칭을 직접 가진 dataset
    explicit = [
        item
        for item
        in candidates
        if item[
            "explicit_natural_landscape"
        ]
    ]

    if explicit:

        best = explicit[0]

        return {
            "source_status":
                "EXPLICIT_DATASET_FOUND",

            "catalog_record":
                best["record"],

            "source_role":
                "DIRECT",

            "reason":
                "서울 열린데이터 카탈로그에서 "
                "'자연경관지구'를 명시적으로 "
                "나타내는 공식 dataset 후보를 확인함",
        }

    # 2순위:
    # 경관지구 전체 dataset
    landscape = [
        item
        for item
        in candidates
        if item[
            "landscape_district_dataset"
        ]
    ]

    if landscape:

        best = landscape[0]

        return {
            "source_status":
                "LANDSCAPE_DISTRICT_DATASET_FOUND",

            "catalog_record":
                best["record"],

            "source_role":
                "PARENT_LAYER",

            "reason":
                "서울시 공식 '용도지구(경관지구)' "
                "공간정보 dataset을 확인함. "
                "다만 이 dataset 전체를 "
                "자연경관지구로 볼 수 없으므로 "
                "Feature 속성에서 자연경관지구 "
                "분류값을 추가 검증해야 함",
        }

    return {
        "source_status":
            "UNRESOLVED",

        "catalog_record":
            None,

        "source_role":
            None,

        "reason":
            "서울 열린데이터 카탈로그에서 "
            "자연경관지구 또는 경관지구의 "
            "공식 공간정보 dataset을 "
            "확정하지 못함",
    }


# ============================================================
# SITE resolution
# ============================================================

def build_resolution(
    source_result: Dict[str, Any],
) -> Dict[str, Any]:

    status = source_result[
        "source_status"
    ]

    if status in (
        "EXPLICIT_DATASET_FOUND",
        "LANDSCAPE_DISTRICT_DATASET_FOUND",
    ):

        query_status = (
            "NOT_QUERIED"
        )

        reason = (
            "자연경관지구 판정을 위한 "
            "공식 공간정보 source 후보는 "
            "확인했으나 대상 Parcel Polygon과 "
            "자연경관지구 Polygon의 실제 "
            "공간교차를 아직 수행하지 않았으므로 "
            "TRUE/FALSE를 확정하지 않음"
        )

    else:

        query_status = (
            "NOT_CONNECTED"
        )

        reason = (
            "자연경관지구 공식 공간정보 "
            "source가 아직 확정되지 않아 "
            "실제 공간조회를 수행하지 않음"
        )

    return {
        "condition":
            TARGET_CONDITION,

        "query_status":
            query_status,

        "resolution":
            "UNKNOWN",

        "confidence":
            "NONE",

        "reason":
            reason,

        "evidence":
            [],
    }


# ============================================================
# 검증
# ============================================================

def build_validation(
    site: Dict[str, str],
    catalog: Dict[str, Any],
    candidates: List[
        Dict[str, Any]
    ],
    source_result: Dict[str, Any],
    resolution: Dict[str, Any],
) -> Dict[str, bool]:

    pnu = site.get(
        "pnu",
        "",
    )

    source_found = (
        source_result[
            "source_status"
        ]
        != "UNRESOLVED"
    )

    return {
        "서울 OpenAPI Key 존재":
            bool(
                SEOUL_OPEN_API_KEY
            ),

        "SITE 주소 존재":
            (
                site.get(
                    "address"
                )
                not in (
                    None,
                    "",
                    "-",
                )
            ),

        "PNU 19자리":
            (
                len(pnu) == 19
                and pnu.isdigit()
            ),

        "서울 카탈로그 조회 실행":
            catalog[
                "success"
            ],

        "카탈로그 row 확보":
            len(
                catalog[
                    "rows"
                ]
            ) > 0,

        "경관지구 source 후보 검색":
            len(
                candidates
            ) > 0,

        "source 후보만으로 SITE TRUE 금지":
            resolution[
                "resolution"
            ]
            != "TRUE",

        "source 후보만으로 SITE FALSE 금지":
            resolution[
                "resolution"
            ]
            != "FALSE",

        "공간교차 전 UNKNOWN 유지":
            resolution[
                "resolution"
            ]
            == "UNKNOWN",

        "source 확정은 공식 카탈로그 기반":
            (
                source_found
                or source_result[
                    "source_status"
                ]
                == "UNRESOLVED"
            ),

        "경관지구 전체를 자연경관지구로 자동판정 안 함":
            (
                source_result.get(
                    "source_role"
                )
                != "PARENT_LAYER"
                or resolution[
                    "resolution"
                ]
                == "UNKNOWN"
            ),
    }


# ============================================================
# 출력
# ============================================================

def print_candidate(
    index: int,
    item: Dict[str, Any],
) -> None:

    record = item[
        "record"
    ]

    print()
    print(
        "-" * 70
    )

    print(
        f"후보 {index}"
    )

    print(
        "score:",
        item["score"],
    )

    print(
        "자연경관지구 명시:",
        item[
            "explicit_natural_landscape"
        ],
    )

    print(
        "경관지구 dataset:",
        item[
            "landscape_district_dataset"
        ],
    )

    fields = [
        "INF_ID",
        "INF_NM",
        "CATE_NM",
        "DITC_NM",
        "MAP_CATE_NM",
        "MNG_ORGAN_NAME",
        "MNG_STATION_NAME",
        "CHNG_LOAD_NM",
        "DATA_LT_NM",
        "SRV_TYPE",
        "LINK_DESC",
        "LINK_INFO",
        "SHORT_URL",
    ]

    for field in fields:

        value = record.get(
            field
        )

        if value not in (
            None,
            "",
        ):

            print(
                f"{field}: "
                f"{normalize_text(value)}"
            )


# ============================================================
# main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-5A "
        "자연경관지구 공식 Source 탐색 / "
        "의미 검증 ==="
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

    context = load_json(
        QUERY_CONTEXT_PATH
    )

    # Registry는 현 상태 확인용
    if SOURCE_REGISTRY_PATH.exists():
        registry = load_json(
            SOURCE_REGISTRY_PATH
        )
    else:
        registry = {}

    site = extract_site_context(
        context
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 대상 SITE ==="
    )
    print(
        "=" * 70
    )

    print(
        "SITE ID:",
        site["site_id"],
    )

    print(
        "주소:",
        site["address"],
    )

    print(
        "용도지역:",
        site["zoning"],
    )

    print(
        "시군구코드:",
        site["sigungu_code"],
    )

    print(
        "PNU:",
        site["pnu"],
    )

    # --------------------------------------------------------
    # 인증
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 서울 OpenAPI 인증 ==="
    )
    print(
        "=" * 70
    )

    if SEOUL_OPEN_API_KEY:

        print(
            "SEOUL_OPEN_API_KEY: "
            "정상적으로 읽었습니다."
        )

    else:

        print(
            "SEOUL_OPEN_API_KEY: "
            "없음"
        )

    # --------------------------------------------------------
    # Catalog
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 1. 서울 열린데이터 "
        "카탈로그 조회 ==="
    )
    print(
        "=" * 70
    )

    catalog = (
        load_catalog_rows()
    )

    print(
        "service:",
        CATALOG_SERVICE,
    )

    print(
        "정상 응답:",
        catalog[
            "success"
        ],
    )

    print(
        "전체 데이터 수:",
        catalog[
            "total_count"
        ],
    )

    print(
        "현재 확보 row 수:",
        len(
            catalog[
                "rows"
            ]
        ),
    )

    if not catalog[
        "success"
    ]:

        print(
            "reason:",
            catalog[
                "reason"
            ],
        )

    # --------------------------------------------------------
    # Candidate
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 2. 자연경관지구 / "
        "경관지구 후보 검색 ==="
    )
    print(
        "=" * 70
    )

    candidates = find_candidates(
        catalog[
            "rows"
        ]
    )

    print(
        "후보 수:",
        len(candidates),
    )

    for index, item in enumerate(
        candidates[:20],
        start=1,
    ):

        print_candidate(
            index,
            item,
        )

    # --------------------------------------------------------
    # Source 의미 판정
    # --------------------------------------------------------

    source_result = (
        determine_source(
            candidates
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== 3. 자연경관지구 "
        "Source 의미 판정 ==="
    )
    print(
        "=" * 70
    )

    print(
        "source_status:",
        source_result[
            "source_status"
        ],
    )

    print(
        "source_role:",
        source_result.get(
            "source_role"
        )
        or "-",
    )

    print(
        "reason:",
        source_result[
            "reason"
        ],
    )

    record = source_result.get(
        "catalog_record"
    )

    if record:

        print()

        print(
            "선택 catalog:"
        )

        print(
            "INF_ID:",
            record.get(
                "INF_ID",
                "-",
            ),
        )

        print(
            "INF_NM:",
            record.get(
                "INF_NM",
                "-",
            ),
        )

        print(
            "SRV_TYPE:",
            record.get(
                "SRV_TYPE",
                "-",
            ),
        )

    # --------------------------------------------------------
    # SITE resolution
    # --------------------------------------------------------

    resolution = (
        build_resolution(
            source_result
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== 4. 현재 자연경관지구 "
        "SITE 판정 ==="
    )
    print(
        "=" * 70
    )

    print(
        "query_status:",
        resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        resolution[
            "resolution"
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

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validation = (
        build_validation(
            site,
            catalog,
            candidates,
            source_result,
            resolution,
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== C-9-2-5A 검증 ==="
    )
    print(
        "=" * 70
    )

    for key, value in (
        validation.items()
    ):

        print(
            f"{key}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output = {
        "step":
            "STEP 17-21-C-9-2-5A",

        "condition":
            TARGET_CONDITION,

        "site":
            site,

        "search_keywords":
            SEARCH_KEYWORDS,

        "catalog": {
            "service":
                CATALOG_SERVICE,

            "success":
                catalog[
                    "success"
                ],

            "total_count":
                catalog[
                    "total_count"
                ],

            "received_rows":
                len(
                    catalog[
                        "rows"
                    ]
                ),
        },

        "candidates":
            candidates[:100],

        "source_result":
            source_result,

        "site_resolution":
            resolution,

        "validation":
            validation,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print(
        "=" * 70
    )
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 최종
    # --------------------------------------------------------

    if all(
        validation.values()
    ):

        print()
        print(
            "STEP 17-21-C-9-2-5A 완료"
        )

        print()

        if (
            source_result[
                "source_status"
            ]
            ==
            "LANDSCAPE_DISTRICT_DATASET_FOUND"
        ):

            print(
                "서울시 공식 경관지구 "
                "공간정보 source를 확인했습니다."
            )

            print()

            print(
                "중요:"
            )
            print(
                "경관지구 전체를 자연경관지구로 "
                "판정하지 않습니다."
            )

            print()

            print(
                "다음 단계:"
            )
            print(
                "STEP 17-21-C-9-2-5B"
            )

            print(
                "→ 경관지구 OpenAPI / "
                "공간파일 schema 분석"
            )

            print(
                "→ 자연경관지구 분류 코드 / "
                "속성값 확인"
            )

            print(
                "→ 경관지구 SHP 확보"
            )

            print(
                "→ 자연경관지구 Feature만 필터"
            )

            print(
                "→ Parcel Polygon × "
                "자연경관지구 Polygon intersection"
            )

        elif (
            source_result[
                "source_status"
            ]
            ==
            "EXPLICIT_DATASET_FOUND"
        ):

            print(
                "자연경관지구 전용 공식 "
                "dataset 후보를 확인했습니다."
            )

            print()

            print(
                "다음 단계:"
            )
            print(
                "STEP 17-21-C-9-2-5B"
            )
            print(
                "→ OpenAPI / SHP geometry 연결"
            )
            print(
                "→ Parcel Polygon 실제 교차판정"
            )

        else:

            print(
                "자연경관지구 source가 "
                "아직 미확정입니다."
            )

            print(
                "resolution: UNKNOWN"
            )

    else:

        print()
        print(
            "STEP 17-21-C-9-2-5A "
            "검증 미완료"
        )

        print()
        print(
            "FAIL 항목을 보정한 뒤 "
            "공간교차 단계로 진행합니다."
        )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print()
        print(
            "사용자에 의해 중단되었습니다."
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 70
        )
        print(
            "ERROR"
        )
        print(
            "=" * 70
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        raise