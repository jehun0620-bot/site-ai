# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14C
서울시 도시계획 결정고시(upisAnnouncement)
도시지역 편입/해제 후보 probe

목표
======================================================================
1. 서울시 공식 upisAnnouncement 전체 데이터를 조회한다.
2. 실제 schema를 API 응답에서 직접 복원한다.
3. 개포/강남 관련 결정고시를 찾는다.
4. 아래 이력 관련 결정고시를 별도로 찾는다.

   - 개발제한구역
   - 시가화조정구역
   - 녹지지역
   - 도시지역
   - 도시지역 편입
   - 구역/지역 해제

5. SITE + 이력 조건이 동시에 나타나는 결정고시를 우선 후보로 저장한다.
6. '공원' 단독 문자열은 오탐이 많으므로 사용하지 않는다.
7. 문자열 hit만으로 TRUE/FALSE 판정하지 않는다.
8. 콘솔은 핵심 결과만 출력한다.
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-14C "
    "서울시 도시계획 결정고시 "
    "도시지역 편입/해제 후보 probe"
)


# ============================================================
# 경로
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_announcement_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

SEOUL_OPEN_API_KEY = (
    os.getenv(
        "SEOUL_OPEN_API_KEY"
    )
)


# ============================================================
# 서울 OpenAPI
# ============================================================

API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

SERVICE_NAME = (
    "upisAnnouncement"
)

PAGE_SIZE = 1000

TIMEOUT = 30


# ============================================================
# 검색어
# ============================================================

SITE_TERMS = [
    "개포동",
    "개포",
    "강남구",
    "강남",
]

# 공원 단독은 제외한다.
# 앞 단계에서 지구단위계획 이름 때문에 오탐이 많았음.
HISTORY_TERMS = [
    "개발제한구역",
    "개발제한",
    "시가화조정구역",
    "시가화조정",
    "녹지지역",
    "도시지역",
    "도시지역편입",
    "도시지역 편입",
    "편입",
    "해제",
]

# 좀 더 강한 이벤트 표현
STRONG_HISTORY_TERMS = [
    "개발제한구역 해제",
    "개발제한구역해제",
    "시가화조정구역 해제",
    "시가화조정구역해제",
    "녹지지역 해제",
    "녹지지역해제",
    "도시지역 편입",
    "도시지역편입",
]


# ============================================================
# util
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


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


def load_site() -> Dict[str, str]:

    data = load_json(
        QUERY_CONTEXT_PATH
    )

    context = data.get(
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
# API
# ============================================================

def request_page(
    start: int,
    end: int,
) -> Dict[str, Any]:

    if not SEOUL_OPEN_API_KEY:

        return {
            "http_status": None,
            "payload": None,
            "error": (
                "SEOUL_OPEN_API_KEY 없음"
            ),
        }

    url = (
        f"{API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{SERVICE_NAME}/"
        f"{start}/{end}/"
    )

    try:

        response = requests.get(
            url,
            timeout=TIMEOUT,
        )

        return {
            "http_status": (
                response.status_code
            ),
            "payload": (
                response.json()
            ),
            "error": None,
        }

    except Exception as exc:

        return {
            "http_status": None,
            "payload": None,
            "error": str(
                exc
            ),
        }


def parse_page(
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    service = payload.get(
        SERVICE_NAME,
        {},
    )

    result = service.get(
        "RESULT",
        {},
    )

    rows = service.get(
        "row",
        [],
    )

    return {
        "result_code": (
            result.get(
                "CODE"
            )
        ),
        "result_message": (
            result.get(
                "MESSAGE"
            )
        ),
        "total_count": int(
            service.get(
                "list_total_count",
                0,
            )
            or 0
        ),
        "rows": (
            rows
            if isinstance(
                rows,
                list,
            )
            else []
        ),
    }


def fetch_all_rows() -> Dict[str, Any]:

    first = request_page(
        1,
        PAGE_SIZE,
    )

    payload = first.get(
        "payload"
    )

    if not isinstance(
        payload,
        dict,
    ):

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "http_status": (
                first.get(
                    "http_status"
                )
            ),
            "result_code": None,
            "total_count": 0,
            "rows": [],
            "error": (
                first.get(
                    "error"
                )
            ),
        }

    parsed = parse_page(
        payload
    )

    if (
        parsed[
            "result_code"
        ]
        != "INFO-000"
    ):

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "http_status": (
                first.get(
                    "http_status"
                )
            ),
            "result_code": (
                parsed[
                    "result_code"
                ]
            ),
            "total_count": (
                parsed[
                    "total_count"
                ]
            ),
            "rows": [],
            "error": (
                parsed[
                    "result_message"
                ]
            ),
        }

    rows = list(
        parsed[
            "rows"
        ]
    )

    total = (
        parsed[
            "total_count"
        ]
    )

    start = (
        PAGE_SIZE + 1
    )

    while (
        start
        <= total
    ):

        end = min(
            start
            + PAGE_SIZE
            - 1,
            total,
        )

        page = request_page(
            start,
            end,
        )

        payload = page.get(
            "payload"
        )

        if not isinstance(
            payload,
            dict,
        ):
            break

        parsed_page = parse_page(
            payload
        )

        if (
            parsed_page[
                "result_code"
            ]
            != "INFO-000"
        ):
            break

        rows.extend(
            parsed_page[
                "rows"
            ]
        )

        start = (
            end + 1
        )

    return {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "http_status": (
            first.get(
                "http_status"
            )
        ),
        "result_code": (
            parsed[
                "result_code"
            ]
        ),
        "result_message": (
            parsed[
                "result_message"
            ]
        ),
        "total_count": (
            total
        ),
        "rows": (
            rows
        ),
        "error": None,
    }


# ============================================================
# Row 검색
# ============================================================

def row_search_text(
    row: Dict[str, Any],
) -> str:

    """
    필드명을 미리 추정하지 않는다.
    모든 non-empty field 값을 하나의 검색 문자열로 만든다.
    """

    values = []

    for (
        key,
        value,
    ) in row.items():

        text = safe_string(
            value
        )

        if not text:
            continue

        values.append(
            text
        )

    return " | ".join(
        values
    )


def find_terms(
    text: str,
    terms: List[str],
) -> List[str]:

    return [
        term
        for term
        in terms
        if term in text
    ]


def find_matching_fields(
    row: Dict[str, Any],
    terms: List[str],
) -> Dict[str, str]:

    matches = {}

    for (
        key,
        value,
    ) in row.items():

        text = safe_string(
            value
        )

        if not text:
            continue

        if any(
            term in text
            for term
            in terms
        ):

            matches[
                key
            ] = text

    return matches


def compact_row(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    """
    상세 JSON에는 전체 row를 보관하되,
    후보 식별에 자주 쓰일 만한 값도 별도로 뽑는다.

    필드명이 실제로 존재하지 않아도 안전하게 동작한다.
    """

    likely_keys = [
        "DCSN_ANCMNT_MNG_CD",
        "ANCMNT_MNG_CD",
        "ANCMNT_NO",
        "ANCMNT_NM",
        "ANCMNT_SJ",
        "TITLE",
        "SJ",
        "LOGVM",
        "PSTN_NM",
        "RGN_NM",
        "DCSN_DT",
        "ANCMNT_DT",
        "DE",
    ]

    important = {}

    for key in likely_keys:

        if (
            key in row
            and safe_string(
                row.get(
                    key
                )
            )
        ):

            important[
                key
            ] = row[
                key
            ]

    return {
        "important": (
            important
        ),
        "row": (
            row
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    site = load_site()

    api = fetch_all_rows()

    rows = api.get(
        "rows",
        [],
    )

    # --------------------------------------------------------
    # 실제 schema
    # --------------------------------------------------------

    schema = sorted(
        {
            key
            for row in rows
            if isinstance(
                row,
                dict,
            )
            for key in row.keys()
        }
    )

    # --------------------------------------------------------
    # 후보 분리
    # --------------------------------------------------------

    site_hits = []

    history_hits = []

    strong_history_hits = []

    combined_hits = []

    strong_combined_hits = []

    exact_address_hits = []

    site_address = safe_string(
        site.get(
            "address"
        )
    )

    pnu = safe_string(
        site.get(
            "pnu"
        )
    )

    for row in rows:

        if not isinstance(
            row,
            dict,
        ):
            continue

        text = row_search_text(
            row
        )

        site_terms = find_terms(
            text,
            SITE_TERMS,
        )

        history_terms = find_terms(
            text,
            HISTORY_TERMS,
        )

        strong_terms = find_terms(
            text,
            STRONG_HISTORY_TERMS,
        )

        # SITE 후보
        if site_terms:

            site_hits.append(
                {
                    "site_terms": (
                        site_terms
                    ),
                    "matched_fields": (
                        find_matching_fields(
                            row,
                            SITE_TERMS,
                        )
                    ),
                    **compact_row(
                        row
                    ),
                }
            )

        # 이력 후보
        if history_terms:

            history_hits.append(
                {
                    "history_terms": (
                        history_terms
                    ),
                    "matched_fields": (
                        find_matching_fields(
                            row,
                            HISTORY_TERMS,
                        )
                    ),
                    **compact_row(
                        row
                    ),
                }
            )

        # 강한 이력 표현
        if strong_terms:

            strong_history_hits.append(
                {
                    "history_terms": (
                        strong_terms
                    ),
                    "matched_fields": (
                        find_matching_fields(
                            row,
                            STRONG_HISTORY_TERMS,
                        )
                    ),
                    **compact_row(
                        row
                    ),
                }
            )

        # SITE + 이력
        if (
            site_terms
            and history_terms
        ):

            combined_hits.append(
                {
                    "site_terms": (
                        site_terms
                    ),
                    "history_terms": (
                        history_terms
                    ),
                    "site_fields": (
                        find_matching_fields(
                            row,
                            SITE_TERMS,
                        )
                    ),
                    "history_fields": (
                        find_matching_fields(
                            row,
                            HISTORY_TERMS,
                        )
                    ),
                    **compact_row(
                        row
                    ),
                }
            )

        # SITE + 강한 이력
        if (
            site_terms
            and strong_terms
        ):

            strong_combined_hits.append(
                {
                    "site_terms": (
                        site_terms
                    ),
                    "history_terms": (
                        strong_terms
                    ),
                    "site_fields": (
                        find_matching_fields(
                            row,
                            SITE_TERMS,
                        )
                    ),
                    "history_fields": (
                        find_matching_fields(
                            row,
                            STRONG_HISTORY_TERMS,
                        )
                    ),
                    **compact_row(
                        row
                    ),
                }
            )

        # 주소/PNU 직접 문자열은 보조 확인
        direct_match = False

        if (
            site_address
            and site_address
            in text
        ):
            direct_match = True

        if (
            pnu
            and pnu in text
        ):
            direct_match = True

        if direct_match:

            exact_address_hits.append(
                compact_row(
                    row
                )
            )

    # --------------------------------------------------------
    # 판정은 계속 UNKNOWN
    # --------------------------------------------------------

    resolution = {
        "query_status": (
            api.get(
                "query_status"
            )
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "MEDIUM"
            if api.get(
                "query_status"
            )
            == "QUERY_SUCCESS"
            else "NONE"
        ),
        "reason": (
            "서울시 공식 도시관리계획 결정고시 전체 DB에서 "
            "SITE 및 도시지역 편입/해제 관련 후보를 탐색한 단계. "
            "결정고시 후보가 있더라도 대상 Parcel의 실제 적용범위 "
            "검증 전에는 TRUE/FALSE를 확정하지 않음"
        ),
    }

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    evidence = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "condition_type": (
            "HISTORY"
        ),

        "site": (
            site
        ),

        "official_source": {
            "provider": (
                "서울특별시"
            ),
            "dataset": (
                "서울시 도시계획 결정고시 정보"
            ),
            "service": (
                SERVICE_NAME
            ),
            "source_system": (
                "서울도시공간포털"
            ),
        },

        "api": {
            "http_status": (
                api.get(
                    "http_status"
                )
            ),
            "result_code": (
                api.get(
                    "result_code"
                )
            ),
            "result_message": (
                api.get(
                    "result_message"
                )
            ),
            "total_count": (
                api.get(
                    "total_count"
                )
            ),
            "received_rows": (
                len(
                    rows
                )
            ),
            "schema": (
                schema
            ),
        },

        "search": {
            "site_terms": (
                SITE_TERMS
            ),
            "history_terms": (
                HISTORY_TERMS
            ),
            "strong_history_terms": (
                STRONG_HISTORY_TERMS
            ),

            "site_hit_count": (
                len(
                    site_hits
                )
            ),
            "history_hit_count": (
                len(
                    history_hits
                )
            ),
            "strong_history_hit_count": (
                len(
                    strong_history_hits
                )
            ),
            "combined_hit_count": (
                len(
                    combined_hits
                )
            ),
            "strong_combined_hit_count": (
                len(
                    strong_combined_hits
                )
            ),
            "direct_address_hit_count": (
                len(
                    exact_address_hits
                )
            ),

            "site_hits": (
                site_hits
            ),
            "history_hits": (
                history_hits
            ),
            "strong_history_hits": (
                strong_history_hits
            ),
            "combined_hits": (
                combined_hits
            ),
            "strong_combined_hits": (
                strong_combined_hits
            ),
            "direct_address_hits": (
                exact_address_hits
            ),
        },

        "resolution": (
            resolution
        ),

        "next_step": (
            "결정고시 후보의 실제 schema와 고시관리코드를 "
            "검토하고 현행 UQ111 도시지역 및 관련 용도구역 "
            "공간정보와 연결하여 대상 Parcel 이력 검증"
        ),
    }

    save_json(
        evidence
    )

    # ========================================================
    # 초간략 콘솔
    # ========================================================

    print(
        "API:",
        api.get(
            "result_code"
        ),
    )

    print(
        "Total:",
        api.get(
            "total_count"
        ),
    )

    print(
        "Received:",
        len(
            rows
        ),
    )

    print(
        "Schema fields:",
        len(
            schema
        ),
    )

    print(
        "SITE hits:",
        len(
            site_hits
        ),
    )

    print(
        "History hits:",
        len(
            history_hits
        ),
    )

    print(
        "Strong history:",
        len(
            strong_history_hits
        ),
    )

    print(
        "Combined:",
        len(
            combined_hits
        ),
    )

    print(
        "Strong combined:",
        len(
            strong_combined_hits
        ),
    )

    print(
        "Direct address/PNU:",
        len(
            exact_address_hits
        ),
    )

    # 강한 결합 후보가 있으면 최대 5건의 matched field만 출력
    for index, item in enumerate(
        strong_combined_hits[
            :5
        ],
        start=1,
    ):

        print(
            f"Candidate {index}:",
            item.get(
                "site_fields"
            ),
            "|",
            item.get(
                "history_fields"
            ),
        )

    # 강한 후보가 없고 일반 combined만 있으면 최대 5건
    if (
        not strong_combined_hits
        and combined_hits
    ):

        for index, item in enumerate(
            combined_hits[
                :5
            ],
            start=1,
        ):

            print(
                f"Candidate {index}:",
                item.get(
                    "site_fields"
                ),
                "|",
                item.get(
                    "history_fields"
                ),
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
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )