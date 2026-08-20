# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14B
서울시 도시계획이력(upisHistory) 공식 source/schema 및 SITE 후보 probe

목표
======================================================================
1. 서울시 공식 upisHistory OpenAPI를 호출한다.
2. 전체 건수 및 schema를 검증한다.
3. SITE 관련 지역명(개포/강남) 후보를 찾는다.
4. 다음 이력 유형 관련 후보를 찾는다.

   - 개발제한구역 해제
   - 시가화조정구역 해제
   - 녹지지역 해제/변경
   - 공원 해제
   - 도시지역 신규 편입

5. 문자열 hit는 후보일 뿐 TRUE/FALSE 판정에 사용하지 않는다.
6. 결정고시관리코드는 다음 단계에서 upisAnnouncement와 연결한다.
7. 콘솔은 핵심값만 출력한다.
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-14B "
    "서울시 upisHistory 공식 source/schema 및 SITE 후보 probe"
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
    / "urban_area_conversion_upis_history_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)


# ============================================================
# 서울 OpenAPI
# ============================================================

API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

SERVICE_NAME = (
    "upisHistory"
)

PAGE_SIZE = 1000

TIMEOUT = 30


# ============================================================
# 검색 기준
# ============================================================

SITE_TERMS = [
    "개포",
    "강남",
]

HISTORY_TERMS = [
    "개발제한",
    "시가화조정",
    "녹지",
    "공원",
    "도시지역",
    "편입",
    "해제",
]


# ============================================================
# 공통
# ============================================================

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

        payload = response.json()

        return {
            "http_status": (
                response.status_code
            ),
            "payload": (
                payload
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


def parse_service(
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

    if not isinstance(
        first.get(
            "payload"
        ),
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
            "total_count": 0,
            "rows": [],
            "error": (
                first.get(
                    "error"
                )
            ),
        }

    parsed = parse_service(
        first[
            "payload"
        ]
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

    total_count = (
        parsed[
            "total_count"
        ]
    )

    rows = list(
        parsed[
            "rows"
        ]
    )

    start = (
        PAGE_SIZE + 1
    )

    while (
        start
        <= total_count
    ):

        end = min(
            start
            + PAGE_SIZE
            - 1,
            total_count,
        )

        page = request_page(
            start,
            end,
        )

        if not isinstance(
            page.get(
                "payload"
            ),
            dict,
        ):
            break

        page_parsed = parse_service(
            page[
                "payload"
            ]
        )

        if (
            page_parsed[
                "result_code"
            ]
            != "INFO-000"
        ):
            break

        rows.extend(
            page_parsed[
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
            total_count
        ),
        "rows": (
            rows
        ),
        "error": None,
    }


# ============================================================
# 후보 탐색
# ============================================================

def row_text(
    row: Dict[str, Any],
) -> str:

    fields = [
        "LOGVM",
        "RPT_TYPE",
        "LCLSF",
        "MCLSF",
        "SCLSF",
        "PSTN_NM",
        "RGN_NM",
    ]

    return " | ".join(
        safe_string(
            row.get(
                field
            )
        )
        for field in fields
    )


def contains_any(
    text: str,
    terms: List[str],
) -> bool:

    return any(
        term in text
        for term in terms
    )


def summarize_row(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "RPT_MNG_CD": (
            row.get(
                "RPT_MNG_CD"
            )
        ),
        "PRJC_CD": (
            row.get(
                "PRJC_CD"
            )
        ),
        "LOGVM": (
            row.get(
                "LOGVM"
            )
        ),
        "RPT_TYPE": (
            row.get(
                "RPT_TYPE"
            )
        ),
        "BFR_RPT_MNG_CD": (
            row.get(
                "BFR_RPT_MNG_CD"
            )
        ),
        "HGHRK_RPT_MNG_CD": (
            row.get(
                "HGHRK_RPT_MNG_CD"
            )
        ),
        "LCLSF": (
            row.get(
                "LCLSF"
            )
        ),
        "MCLSF": (
            row.get(
                "MCLSF"
            )
        ),
        "SCLSF": (
            row.get(
                "SCLSF"
            )
        ),
        "PSTN_NM": (
            row.get(
                "PSTN_NM"
            )
        ),
        "RGN_NM": (
            row.get(
                "RGN_NM"
            )
        ),
        "AREA_EXS": (
            row.get(
                "AREA_EXS"
            )
        ),
        "AREA_ICDC_CD": (
            row.get(
                "AREA_ICDC_CD"
            )
        ),
        "AREA_CHG": (
            row.get(
                "AREA_CHG"
            )
        ),
        "AREA_CHG_AFTR": (
            row.get(
                "AREA_CHG_AFTR"
            )
        ),
        "DCSN_ANCMNT_MNG_CD": (
            row.get(
                "DCSN_ANCMNT_MNG_CD"
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    site = load_site()

    result = fetch_all_rows()

    rows = result.get(
        "rows",
        [],
    )

    schema = (
        sorted(
            rows[0].keys()
        )
        if rows
        else []
    )

    site_hits = []

    history_hits = []

    combined_hits = []

    for row in rows:

        text = row_text(
            row
        )

        site_match = (
            contains_any(
                text,
                SITE_TERMS,
            )
        )

        history_match = (
            contains_any(
                text,
                HISTORY_TERMS,
            )
        )

        if site_match:

            site_hits.append(
                summarize_row(
                    row
                )
            )

        if history_match:

            history_hits.append(
                summarize_row(
                    row
                )
            )

        if (
            site_match
            and history_match
        ):

            combined_hits.append(
                summarize_row(
                    row
                )
            )

    # --------------------------------------------------------
    # 아직 판정 금지
    # --------------------------------------------------------

    resolution = {
        "query_status": (
            result.get(
                "query_status"
            )
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "MEDIUM"
            if result.get(
                "query_status"
            )
            == "QUERY_SUCCESS"
            else "NONE"
        ),
        "reason": (
            "서울시 공식 upisHistory 이력 DB를 "
            "정상 조회하고 SITE/이력 후보를 탐색함. "
            "후보 문자열만으로 판정하지 않고 "
            "결정고시 및 대상 Parcel 연결 검증 필요"
        ),
    }

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
                "서울시 도시계획이력 정보"
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
                result.get(
                    "http_status"
                )
            ),
            "result_code": (
                result.get(
                    "result_code"
                )
            ),
            "result_message": (
                result.get(
                    "result_message"
                )
            ),
            "total_count": (
                result.get(
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
            "combined_hit_count": (
                len(
                    combined_hits
                )
            ),
            "site_hits": (
                site_hits
            ),
            "combined_hits": (
                combined_hits
            ),
        },

        "resolution": (
            resolution
        ),

        "next_step": (
            "combined 후보의 DCSN_ANCMNT_MNG_CD를 "
            "upisAnnouncement 결정고시와 연결하고 "
            "개포동 12번지 Parcel 관련성 검증"
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
        result.get(
            "result_code"
        ),
    )

    print(
        "Total rows:",
        result.get(
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
        "Combined hits:",
        len(
            combined_hits
        ),
    )

    # combined 후보는 최대 5개만 콘솔 출력
    for index, hit in enumerate(
        combined_hits[
            :5
        ],
        start=1,
    ):

        print(
            f"Candidate {index}:",
            safe_string(
                hit.get(
                    "PSTN_NM"
                )
            ),
            "/",
            safe_string(
                hit.get(
                    "RGN_NM"
                )
            ),
            "/",
            safe_string(
                hit.get(
                    "LCLSF"
                )
            ),
            "/",
            safe_string(
                hit.get(
                    "MCLSF"
                )
            ),
            "/",
            safe_string(
                hit.get(
                    "SCLSF"
                )
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