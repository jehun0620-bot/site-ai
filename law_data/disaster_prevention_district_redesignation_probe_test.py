# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-10B-1
2019년 방재지구 전면폐지 이후 서울시 재지정 여부 전수 probe

목표
======================================================================
1. 기존 프로젝트에서 검증된 서울시 공식 upisAnnouncement 전체 DB 조회
2. 2019-04-25 이후 고시만 대상으로 검색
3. "방재지구" 정확 문자열 전수 검색
4. 지정 / 신설 / 결정 / 변경 / 폐지 / 해제 문맥 분류
5. 단순 과거 이력 인용과 실제 재지정 후보를 구분
6. 강남구 / 개포동 관련 후보 별도 확인
7. 검색 결과를 간략하게 출력

중요
======================================================================
- 2019-04-25 당시 서울시 기존 방재지구는 전부 폐지
- 이후 "방재지구" 재지정 고시가 존재하는지를 확인하는 단계
- 문자열 hit가 있다고 곧바로 재지정으로 판정하지 않음
- 실제 지정/신설 문맥 후보를 별도 추출
"""

from __future__ import annotations

import json
import os
import re

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-10-2B-10B-1 "
    "서울 방재지구 2019 이후 재지정 전수 probe"
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
    / "disaster_prevention_district_redesignation_probe.json"
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
# 서울시 OpenAPI
#
# 기존 프로젝트의 검증된 announcement DB와 동일
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
# 기준일
#
# 서울특별시 고시 제2019-133호 방재지구 폐지일
# ============================================================

ABOLITION_DATE = (
    "2019-04-25"
)

ABOLITION_DATE_INT = (
    20190425
)


# ============================================================
# 검색어
# ============================================================

TARGET_TERM = (
    "방재지구"
)

REDESIGNATION_TERMS = [
    "지정",
    "신설",
    "신규",
    "결정",
]

CHANGE_TERMS = [
    "변경",
    "변경결정",
]

RELEASE_TERMS = [
    "폐지",
    "해제",
    "폐지결정",
    "해제결정",
]

SITE_TERMS = [
    "강남구",
    "강남",
    "개포동",
    "개포",
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
        safe_string(value),
    ).strip()


def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        normalize_text(value)
        for value
        in row.values()
        if normalize_text(value)
    )


# ============================================================
# 날짜
# ============================================================

def parse_date_value(
    value: Any,
) -> Optional[int]:

    text = safe_string(
        value
    )

    if not text:
        return None

    # --------------------------------------------------------
    # 2026-08-01T00:00:00.000
    # 2026-08-01
    # 20260801
    # 모두 처리
    # --------------------------------------------------------

    digits = re.sub(
        r"[^0-9]",
        "",
        text,
    )

    if len(digits) >= 8:

        try:
            return int(
                digits[:8]
            )

        except Exception:
            return None

    return None


def get_row_date(
    row: Dict[str, Any],
) -> Optional[int]:

    # 기존 UPIS 필드 우선
    candidate_fields = [
        "ANCMNT_YMD",
        "ANCMNT_DT",
        "NTFC_YMD",
        "NTFC_DT",
    ]

    for field in candidate_fields:

        value = parse_date_value(
            row.get(
                field
            )
        )

        if value:
            return value

    return None


# ============================================================
# API parser
# ============================================================

def load_rows_from_payload(
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

    parsed = load_rows_from_payload(
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

        parsed_page = (
            load_rows_from_payload(
                payload
            )
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

        start = end + 1

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
# 요약
# ============================================================

def summarize(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = row_text(
        row
    )

    date_value = get_row_date(
        row
    )

    return {
        "date": (
            date_value
        ),

        "ANCMNT_YMD": (
            row.get(
                "ANCMNT_YMD"
            )
        ),

        "ANCMNT_MNG_CD": (
            row.get(
                "ANCMNT_MNG_CD"
            )
        ),

        "ANCMNT_NO": (
            row.get(
                "ANCMNT_NO"
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

        "redesignation_terms": [
            term
            for term
            in REDESIGNATION_TERMS
            if term in text
        ],

        "change_terms": [
            term
            for term
            in CHANGE_TERMS
            if term in text
        ],

        "release_terms": [
            term
            for term
            in RELEASE_TERMS
            if term in text
        ],

        "site_terms": [
            term
            for term
            in SITE_TERMS
            if term in text
        ],
    }


# ============================================================
# 실제 재지정 후보 분류
# ============================================================

def classify_hit(
    item: Dict[str, Any],
) -> str:

    title = normalize_text(
        item.get(
            "TTL"
        )
    )

    content = normalize_text(
        item.get(
            "CN"
        )
    )

    text = (
        title
        + " "
        + content
    )

    # --------------------------------------------------------
    # 폐지 / 해제 문맥
    # --------------------------------------------------------

    if any(
        term in text
        for term
        in RELEASE_TERMS
    ):

        return (
            "RELEASE_OR_HISTORY"
        )

    # --------------------------------------------------------
    # 제목에 방재지구 + 지정/신설
    #
    # 가장 강한 재지정 evidence
    # --------------------------------------------------------

    if (
        TARGET_TERM
        in title
        and any(
            term in title
            for term
            in (
                "지정",
                "신설",
                "결정",
            )
        )
    ):

        return (
            "STRONG_REDESIGNATION_CANDIDATE"
        )

    # --------------------------------------------------------
    # 내용상 지정/신설
    # --------------------------------------------------------

    if any(
        term in text
        for term
        in (
            "방재지구 지정",
            "방재지구를 지정",
            "방재지구 신설",
            "방재지구를 신설",
        )
    ):

        return (
            "STRONG_REDESIGNATION_CANDIDATE"
        )

    # --------------------------------------------------------
    # 변경
    # --------------------------------------------------------

    if any(
        term in text
        for term
        in CHANGE_TERMS
    ):

        return (
            "CHANGE_OR_REFERENCE"
        )

    # --------------------------------------------------------
    # 단순 언급
    # --------------------------------------------------------

    return (
        "REFERENCE_ONLY"
    )


# ============================================================
# main
# ============================================================

def main() -> int:

    api = fetch_all()

    rows = api.get(
        "rows",
        [],
    )

    post_abolition_rows = []

    exact_hits = []

    strong_redesignation = []

    site_hits = []

    classifications = {}

    # ========================================================
    # 2019-04-25 이후 전수검색
    # ========================================================

    for row in rows:

        row_date = get_row_date(
            row
        )

        if (
            row_date is None
            or row_date
            <= ABOLITION_DATE_INT
        ):
            continue

        post_abolition_rows.append(
            row
        )

        text = row_text(
            row
        )

        if TARGET_TERM not in text:
            continue

        item = summarize(
            row
        )

        classification = (
            classify_hit(
                item
            )
        )

        item[
            "classification"
        ] = (
            classification
        )

        exact_hits.append(
            item
        )

        classifications[
            classification
        ] = (
            classifications.get(
                classification,
                0,
            )
            + 1
        )

        if (
            classification
            == "STRONG_REDESIGNATION_CANDIDATE"
        ):

            strong_redesignation.append(
                item
            )

        if item[
            "site_terms"
        ]:

            site_hits.append(
                item
            )

    # ========================================================
    # 판정
    # ========================================================

    api_success = (
        api.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
    )

    if not api_success:

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "서울시 공식 upisAnnouncement "
            "전체 DB 조회 실패"
        )

    elif strong_redesignation:

        resolution = (
            "REDESIGNATION_CANDIDATE_FOUND"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "2019-04-25 이후 서울시 공식 "
            "결정고시 DB에서 방재지구 지정/신설 "
            "문맥 후보가 확인되어 개별 고시 원문 검증 필요"
        )

    else:

        resolution = (
            "NO_REDESIGNATION_EVIDENCE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "서울시 공식 upisAnnouncement 전체 DB에서 "
            "2019-04-25 이후 방재지구 관련 고시를 "
            "전수 검색했으나 실제 지정 또는 신설로 "
            "분류되는 재지정 evidence가 확인되지 않음"
        )

    # ========================================================
    # 종합 current-state recommendation
    # ========================================================

    if (
        resolution
        == "NO_REDESIGNATION_EVIDENCE"
    ):

        current_state_recommendation = (
            "FALSE_HIGH_READY"
        )

    else:

        current_state_recommendation = (
            "HOLD"
        )

    # ========================================================
    # output
    # ========================================================

    result = {
        "step": STEP_NAME,

        "official_baseline": {
            "abolition_notice": (
                "서울특별시 고시 제2019-133호"
            ),

            "abolition_date": (
                ABOLITION_DATE
            ),

            "baseline_state": (
                "서울시 기존 방재지구 전부 폐지"
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

            "post_abolition_rows": (
                len(
                    post_abolition_rows
                )
            ),
        },

        "search": {
            "target_term": (
                TARGET_TERM
            ),

            "exact_hit_count": (
                len(
                    exact_hits
                )
            ),

            "strong_redesignation_count": (
                len(
                    strong_redesignation
                )
            ),

            "gangnam_gaepo_hit_count": (
                len(
                    site_hits
                )
            ),

            "classification_counts": (
                classifications
            ),

            "exact_hits": (
                exact_hits
            ),

            "strong_redesignation_candidates": (
                strong_redesignation
            ),

            "site_hits": (
                site_hits
            ),
        },

        "resolution": {
            "resolution": (
                resolution
            ),

            "confidence": (
                confidence
            ),

            "reason": (
                reason
            ),

            "current_state_recommendation": (
                current_state_recommendation
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

    print(
        "Post-2019-04-25:",
        len(
            post_abolition_rows
        ),
    )

    print()

    print(
        "방재지구 hits:",
        len(
            exact_hits
        ),
    )

    print(
        "Strong redesignation:",
        len(
            strong_redesignation
        ),
    )

    print(
        "Gangnam/Gaepo hits:",
        len(
            site_hits
        ),
    )

    print(
        "Classifications:",
        classifications,
    )

    print()

    for index, item in enumerate(
        exact_hits[:10],
        start=1,
    ):

        print(
            f"[{index}]",
            safe_string(
                item.get(
                    "ANCMNT_YMD"
                )
            ),
            "|",
            safe_string(
                item.get(
                    "ANCMNT_NO"
                )
            ),
            "|",
            item[
                "classification"
            ],
            "|",
            safe_string(
                item.get(
                    "TTL"
                )
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
        "current state:",
        current_state_recommendation,
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