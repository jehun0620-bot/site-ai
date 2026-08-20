# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-15A
개발밀도관리구역 서울시 공식 결정고시 전수 probe

목표
======================================================================
1. 서울시 공식 upisAnnouncement 전체 DB 조회
2. "개발밀도관리구역" 정확 명칭 검색
3. 지정 / 변경 / 해제 관련 고시 분류
4. 강남 / 개포 관련 후보 별도 분류
5. 정확 명칭이 없는 일반 "개발밀도" 문자열도 보조 검색
6. 문자열 부재만으로 FALSE 판정하지 않음
7. 콘솔은 핵심 숫자만 출력
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-9-2-15A "
    "개발밀도관리구역 서울시 결정고시 전수 probe"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = BASE_DIR / "law_data" / "output"

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_announcement_full_probe.json"
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

SERVICE_NAME = "upisAnnouncement"

PAGE_SIZE = 1000
TIMEOUT = 30


# ============================================================
# 검색어
# ============================================================

EXACT_TERM = (
    "개발밀도관리구역"
)

BROAD_TERMS = [
    "개발밀도",
    "밀도관리구역",
]

ACTION_TERMS = [
    "지정",
    "변경",
    "해제",
]

SITE_TERMS = [
    "강남",
    "강남구",
    "개포",
    "개포동",
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

        page_parsed = (
            load_rows_from_payload(
                payload
            )
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
# 검색
# ============================================================

def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        safe_string(
            value
        )
        for value
        in row.values()
        if safe_string(
            value
        )
    )


def summarize(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = row_text(
        row
    )

    return {
        "ANCMNT_MNG_CD": (
            row.get(
                "ANCMNT_MNG_CD"
            )
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

        "action_terms": [
            term
            for term
            in ACTION_TERMS
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
# main
# ============================================================

def main() -> int:

    api = fetch_all()

    rows = api.get(
        "rows",
        [],
    )

    exact_hits = []

    broad_hits = []

    site_exact_hits = []

    for row in rows:

        text = row_text(
            row
        )

        exact = (
            EXACT_TERM
            in text
        )

        broad = any(
            term in text
            for term
            in BROAD_TERMS
        )

        site = any(
            term in text
            for term
            in SITE_TERMS
        )

        if exact:

            item = summarize(
                row
            )

            exact_hits.append(
                item
            )

            if site:

                site_exact_hits.append(
                    item
                )

        elif broad:

            broad_hits.append(
                summarize(
                    row
                )
            )

    result = {
        "step": STEP_NAME,

        "condition": (
            "개발밀도관리구역"
        ),

        "legal_basis": {
            "law": (
                "국토의 계획 및 이용에 관한 법률"
            ),
            "article": (
                "제66조"
            ),
            "requirement": (
                "지정 또는 변경 시 고시"
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
            "exact_term": (
                EXACT_TERM
            ),

            "exact_hit_count": (
                len(
                    exact_hits
                )
            ),

            "site_exact_hit_count": (
                len(
                    site_exact_hits
                )
            ),

            "broad_hit_count": (
                len(
                    broad_hits
                )
            ),

            "exact_hits": (
                exact_hits
            ),

            "site_exact_hits": (
                site_exact_hits
            ),

            "broad_hits": (
                broad_hits
            ),
        },

        "resolution": {
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
                "개발밀도관리구역은 국토계획법 제66조에 "
                "따른 별도 지정·고시 대상이므로 서울시 "
                "공식 결정고시 DB에서 정확 명칭 및 "
                "SITE 관련 후보를 전수 탐색한 단계. "
                "검색 부재만으로 FALSE 판정하지 않음"
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
    # concise output
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
        "Exact hits:",
        len(
            exact_hits
        ),
    )

    print(
        "SITE exact hits:",
        len(
            site_exact_hits
        ),
    )

    print(
        "Broad hits:",
        len(
            broad_hits
        ),
    )

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
            safe_string(
                item.get(
                    "TTL"
                )
            ),
            "| site:",
            item[
                "site_terms"
            ],
        )

    print(
        "resolution: UNKNOWN"
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