# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-5A
학교이적지 SITE history 전수 probe

목표
======================================================================
대상:
서울특별시 강남구 개포동 12번지

학교이적지 정의:
학교 전체가 이전하고 남은 부지

검증 방법
======================================================================
서울시 공식 upisAnnouncement 전체 DB를 전수검색하여:

1. 개포동 12번지 직접 hit
2. 개포동 12 일대 hit
3. PNU 직접 hit
4. 학교 + 개포동 문맥
5. 학교시설 폐지
6. 학교 이전
7. 학교이적지 / 학교이전적지
8. 과거 학교부지

를 각각 분류한다.

중요
======================================================================
- 단순 "학교" 언급으로 학교이적지 TRUE 처리 금지
- 학교시설 결정/변경만으로 TRUE 처리 금지
- "학교 전체가 이전한 부지" evidence가 필요
- 정확 evidence가 없으면 이 단계에서는 UNKNOWN 유지
"""

from __future__ import annotations

import json
import os
import re

from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-10-3B-5A "
    "학교이적지 SITE history probe"
)


# ============================================================
# PATH
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "school_relocation_site_history_probe.json"
)


# ============================================================
# ENV
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)


# ============================================================
# API
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
# SITE
# ============================================================

SITE = {
    "site_id": (
        "11680-10300-0012-0000"
    ),

    "pnu": (
        "1168010300100120000"
    ),

    "address": (
        "서울특별시 강남구 개포동 12번지"
    ),

    "sigungu": (
        "강남구"
    ),

    "dong": (
        "개포동"
    ),

    "bonbun": (
        "12"
    ),
}


# ============================================================
# TERMS
# ============================================================

DIRECT_ADDRESS_TERMS = [
    "개포동 12번지",
    "개포동 12 번지",
    "개포동12번지",
    "개포동 12",
]

SCHOOL_TERMS = [
    "학교",
    "초등학교",
    "중학교",
    "고등학교",
]

STRONG_RELOCATION_TERMS = [
    "학교이적지",
    "학교 이적지",
    "학교이전적지",
    "학교 이전적지",
    "학교 이전 부지",
    "학교이전부지",
    "학교 전체가 이전",
]

RELOCATION_TERMS = [
    "학교 이전",
    "학교이전",
    "이전적지",
    "이적지",
]

FACILITY_RELEASE_TERMS = [
    "학교시설 폐지",
    "학교 폐지",
    "도시계획시설(학교) 폐지",
    "도시계획시설 학교 폐지",
    "학교 결정 폐지",
]

GAEPO_TERMS = [
    "개포동",
    "개포",
]

GANGNAM_TERMS = [
    "강남구",
    "강남",
]


# ============================================================
# util
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(
            value
        ),
    ).strip()


def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        normalize_text(
            value
        )
        for value
        in row.values()
        if normalize_text(
            value
        )
    )


# ============================================================
# API
# ============================================================

def parse_payload(
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


def request_page(
    start: int,
    end: int,
) -> Dict[str, Any]:

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
            "error": str(exc),
        }


def fetch_all() -> Dict[str, Any]:

    if not SEOUL_OPEN_API_KEY:

        return {
            "query_status": (
                "QUERY_FAILED"
            ),

            "rows": [],

            "error": (
                "SEOUL_OPEN_API_KEY 없음"
            ),
        }

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

            "rows": [],

            "error": (
                first.get(
                    "error"
                )
            ),
        }

    parsed = parse_payload(
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

    while start <= total:

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

        parsed_page = parse_payload(
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

        "result_code": (
            parsed[
                "result_code"
            ]
        ),

        "total_count": (
            total
        ),

        "rows": (
            rows
        ),
    }


# ============================================================
# classification
# ============================================================

def summarize(
    row: Dict[str, Any],
    classification: str,
) -> Dict[str, Any]:

    text = row_text(
        row
    )

    return {
        "classification": (
            classification
        ),

        "ANCMNT_YMD": (
            row.get(
                "ANCMNT_YMD"
            )
        ),

        "ANCMNT_NO": (
            row.get(
                "ANCMNT_NO"
            )
        ),

        "ANCMNT_MNG_CD": (
            row.get(
                "ANCMNT_MNG_CD"
            )
        ),

        "ANCMNT_INST": (
            row.get(
                "ANCMNT_INST"
            )
        ),

        "TKCG_INST": (
            row.get(
                "TKCG_INST"
            )
        ),

        "TTL": (
            row.get(
                "TTL"
            )
        ),

        "CN": (
            row.get(
                "CN"
            )
        ),

        "direct_address_terms": [
            term
            for term
            in DIRECT_ADDRESS_TERMS
            if term in text
        ],

        "strong_relocation_terms": [
            term
            for term
            in STRONG_RELOCATION_TERMS
            if term in text
        ],

        "relocation_terms": [
            term
            for term
            in RELOCATION_TERMS
            if term in text
        ],

        "facility_release_terms": [
            term
            for term
            in FACILITY_RELEASE_TERMS
            if term in text
        ],
    }


def classify(
    text: str,
) -> str | None:

    direct_address = any(
        term in text
        for term
        in DIRECT_ADDRESS_TERMS
    )

    pnu_match = (
        SITE[
            "pnu"
        ]
        in text
    )

    gaepo = any(
        term in text
        for term
        in GAEPO_TERMS
    )

    gangnam = any(
        term in text
        for term
        in GANGNAM_TERMS
    )

    school = any(
        term in text
        for term
        in SCHOOL_TERMS
    )

    strong_relocation = any(
        term in text
        for term
        in STRONG_RELOCATION_TERMS
    )

    relocation = any(
        term in text
        for term
        in RELOCATION_TERMS
    )

    facility_release = any(
        term in text
        for term
        in FACILITY_RELEASE_TERMS
    )

    # --------------------------------------------------------
    # strongest
    # --------------------------------------------------------

    if (
        (direct_address or pnu_match)
        and strong_relocation
    ):

        return (
            "DIRECT_STRONG_SCHOOL_RELOCATION"
        )

    if (
        direct_address
        and school
        and (
            relocation
            or facility_release
        )
    ):

        return (
            "DIRECT_SCHOOL_HISTORY"
        )

    # --------------------------------------------------------
    # 개포동 학교이전 문맥
    # --------------------------------------------------------

    if (
        gaepo
        and strong_relocation
    ):

        return (
            "GAEPO_STRONG_RELOCATION"
        )

    if (
        gaepo
        and school
        and (
            relocation
            or facility_release
        )
    ):

        return (
            "GAEPO_SCHOOL_HISTORY"
        )

    # --------------------------------------------------------
    # 강남구 broader
    # --------------------------------------------------------

    if (
        gangnam
        and strong_relocation
    ):

        return (
            "GANGNAM_STRONG_RELOCATION"
        )

    if (
        gangnam
        and school
        and facility_release
    ):

        return (
            "GANGNAM_SCHOOL_RELEASE"
        )

    # --------------------------------------------------------
    # direct address, but no school history
    # --------------------------------------------------------

    if direct_address or pnu_match:

        return (
            "DIRECT_ADDRESS_NON_SCHOOL"
        )

    return None


# ============================================================
# main
# ============================================================

def main() -> int:

    api = fetch_all()

    rows = api.get(
        "rows",
        [],
    )

    classified = []

    counts = {}

    direct_school_history = []

    strong_candidates = []

    gaepo_school_history = []

    for row in rows:

        text = row_text(
            row
        )

        classification = classify(
            text
        )

        if not classification:
            continue

        item = summarize(
            row,
            classification,
        )

        classified.append(
            item
        )

        counts[
            classification
        ] = (
            counts.get(
                classification,
                0,
            )
            + 1
        )

        if classification in {
            "DIRECT_STRONG_SCHOOL_RELOCATION",
            "DIRECT_SCHOOL_HISTORY",
        }:

            direct_school_history.append(
                item
            )

        if classification in {
            "DIRECT_STRONG_SCHOOL_RELOCATION",
            "GAEPO_STRONG_RELOCATION",
            "GANGNAM_STRONG_RELOCATION",
        }:

            strong_candidates.append(
                item
            )

        if classification in {
            "GAEPO_STRONG_RELOCATION",
            "GAEPO_SCHOOL_HISTORY",
        }:

            gaepo_school_history.append(
                item
            )

    # ========================================================
    # resolution
    # ========================================================

    api_success = (
        api.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
        and api.get(
            "result_code"
        )
        == "INFO-000"
        and len(
            rows
        )
        == api.get(
            "total_count"
        )
    )

    if not api_success:

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "서울시 공식 고시 DB 전체조회 실패"
        )

    elif any(
        item[
            "classification"
        ]
        == "DIRECT_STRONG_SCHOOL_RELOCATION"

        for item
        in direct_school_history
    ):

        resolution = (
            "TRUE_CANDIDATE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "대상 주소/PNU와 학교이적지 직접 문맥이 "
            "동시에 확인되어 원 고시 검증 필요"
        )

    elif direct_school_history:

        resolution = (
            "HISTORY_CANDIDATE"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "대상 주소에서 학교 이전/폐지 관련 "
            "고시 문맥이 확인되어 상세 고시 검증 필요"
        )

    else:

        resolution = (
            "NO_DIRECT_HISTORY_EVIDENCE"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "서울시 공식 결정고시 전체 DB에서 "
            "개포동 12번지/PNU와 학교이전ㆍ학교이적지 "
            "문맥이 결합된 직접 evidence가 확인되지 않음. "
            "다만 학교이적지는 과거 교육청 재산이력도 "
            "확인할 필요가 있으므로 아직 FALSE 확정하지 않음"
        )

    # ========================================================
    # output
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "site": (
            SITE
        ),

        "definition": {
            "condition": (
                "학교이적지"
            ),

            "meaning": (
                "학교 전체가 이전하고 남은 부지"
            ),
        },

        "api": {
            "query_status": (
                api.get(
                    "query_status"
                )
            ),

            "result_code": (
                api.get(
                    "result_code"
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
        },

        "search": {
            "classification_counts": (
                counts
            ),

            "direct_school_history_count": (
                len(
                    direct_school_history
                )
            ),

            "strong_candidate_count": (
                len(
                    strong_candidates
                )
            ),

            "gaepo_school_history_count": (
                len(
                    gaepo_school_history
                )
            ),

            "direct_school_history": (
                direct_school_history
            ),

            "strong_candidates": (
                strong_candidates
            ),

            "gaepo_school_history": (
                gaepo_school_history
            ),

            "all_classified": (
                classified
            ),
        },

        "resolution": {
            "status": (
                resolution
            ),

            "confidence": (
                confidence
            ),

            "reason": (
                reason
            ),
        },
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            result,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )

    # ========================================================
    # concise console
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

    print()

    print(
        "Direct school history:",
        len(
            direct_school_history
        ),
    )

    print(
        "Strong relocation candidates:",
        len(
            strong_candidates
        ),
    )

    print(
        "Gaepo school history:",
        len(
            gaepo_school_history
        ),
    )

    print(
        "Classifications:",
        counts,
    )

    print()

    for index, item in enumerate(
        direct_school_history[:10],
        start=1,
    ):

        print(
            f"[DIRECT {index}]",
            item.get(
                "ANCMNT_YMD"
            ),
            "|",
            item.get(
                "ANCMNT_NO"
            ),
            "|",
            item.get(
                "classification"
            ),
            "|",
            item.get(
                "TTL"
            ),
        )

    print()

    for index, item in enumerate(
        gaepo_school_history[:10],
        start=1,
    ):

        print(
            f"[GAEPO {index}]",
            item.get(
                "ANCMNT_YMD"
            ),
            "|",
            item.get(
                "ANCMNT_NO"
            ),
            "|",
            item.get(
                "classification"
            ),
            "|",
            item.get(
                "TTL"
            ),
        )

    print()

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
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