# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14E-1
1989 대치택지개발지구 최초 결정고시 추적

목표
======================================================================
1. 서울시 공식 upisAnnouncement 전체 결정고시를 조회한다.
2. API가 어느 연도까지 과거 자료를 포함하는지 확인한다.
3. 대치택지개발지구 / 개포동 12 관련 고시를 전수 추출한다.
4. 1989-03-21 전후 고시를 별도로 확인한다.
5. 녹지지역 / 개발제한구역 / 시가화조정구역 / 도시지역 편입
   표현이 함께 존재하는지 확인한다.
6. 검색 부재만으로 FALSE 판정하지 않는다.
"""

from __future__ import annotations

import json
import os

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-9-2-14E-1 "
    "1989 대치택지개발지구 최초 결정고시 추적"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_initial_designation_notice_probe.json"
)


# ============================================================
# API
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)

API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

SERVICE_NAME = "upisAnnouncement"

PAGE_SIZE = 1000
TIMEOUT = 30


# ============================================================
# 검색조건
# ============================================================

PROJECT_TERMS = [
    "대치택지개발지구",
    "대치택지",
]

SITE_TERMS = [
    "개포동 12",
    "개포동12",
]

TARGET_HISTORY_TERMS = [
    "개발제한구역",
    "시가화조정구역",
    "녹지지역",
    "자연녹지지역",
    "생산녹지지역",
    "보전녹지지역",
    "도시지역 편입",
    "도시지역편입",
]

KNOWN_INITIAL_DATE = "1989-03-21"


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


def request_page(
    start: int,
    end: int,
) -> Optional[
    Dict[str, Any]
]:

    if not SEOUL_OPEN_API_KEY:
        return None

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

        return response.json()

    except Exception:

        return None


def parse_page(
    payload: Dict[str, Any],
):

    service = payload.get(
        SERVICE_NAME,
        {},
    )

    result = service.get(
        "RESULT",
        {},
    )

    return (
        result.get(
            "CODE"
        ),
        int(
            service.get(
                "list_total_count",
                0,
            )
            or 0
        ),
        service.get(
            "row",
            [],
        )
        or [],
    )


def fetch_all() -> List[
    Dict[str, Any]
]:

    first = request_page(
        1,
        PAGE_SIZE,
    )

    if not first:
        return []

    code, total, rows = parse_page(
        first
    )

    if code != "INFO-000":
        return []

    rows = list(
        rows
    )

    start = PAGE_SIZE + 1

    while start <= total:

        end = min(
            start + PAGE_SIZE - 1,
            total,
        )

        payload = request_page(
            start,
            end,
        )

        if not payload:
            break

        page_code, _, page_rows = (
            parse_page(
                payload
            )
        )

        if page_code != "INFO-000":
            break

        rows.extend(
            page_rows
        )

        start = end + 1

    return rows


# ============================================================
# 날짜
# ============================================================

def parse_date(
    value: Any,
) -> Optional[datetime]:

    text = safe_string(
        value
    )

    if not text:
        return None

    text = text[
        :10
    ]

    try:

        return datetime.strptime(
            text,
            "%Y-%m-%d",
        )

    except Exception:

        return None


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


def matched_terms(
    text: str,
    terms: List[str],
) -> List[str]:

    return [
        term
        for term
        in terms
        if term in text
    ]


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
        "ANCMNT_NO": (
            row.get(
                "ANCMNT_NO"
            )
        ),
        "ANCMNT_YMD": (
            row.get(
                "ANCMNT_YMD"
            )
        ),
        "TKCG_INST": (
            row.get(
                "TKCG_INST"
            )
        ),
        "ANCMNT_INST": (
            row.get(
                "ANCMNT_INST"
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
        "project_terms": (
            matched_terms(
                text,
                PROJECT_TERMS,
            )
        ),
        "site_terms": (
            matched_terms(
                text,
                SITE_TERMS,
            )
        ),
        "history_terms": (
            matched_terms(
                text,
                TARGET_HISTORY_TERMS,
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    rows = fetch_all()

    dated_rows = []

    for row in rows:

        date = parse_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        if date:

            dated_rows.append(
                (
                    date,
                    row,
                )
            )

    dated_rows.sort(
        key=lambda x: x[0]
    )

    oldest_date = (
        dated_rows[0][0]
        if dated_rows
        else None
    )

    newest_date = (
        dated_rows[-1][0]
        if dated_rows
        else None
    )

    # --------------------------------------------------------
    # 대치택지 전체 고시
    # --------------------------------------------------------

    project_hits = []

    site_hits = []

    pre_1997_hits = []

    initial_date_hits = []

    history_project_hits = []

    for row in rows:

        text = row_text(
            row
        )

        project_match = any(
            term in text
            for term
            in PROJECT_TERMS
        )

        site_match = any(
            term in text
            for term
            in SITE_TERMS
        )

        date = parse_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        summary = None

        if project_match:

            summary = summarize(
                row
            )

            project_hits.append(
                summary
            )

            if (
                summary[
                    "history_terms"
                ]
            ):

                history_project_hits.append(
                    summary
                )

        if site_match:

            if summary is None:

                summary = summarize(
                    row
                )

            site_hits.append(
                summary
            )

        if (
            project_match
            and date
            and date.year <= 1996
        ):

            if summary is None:

                summary = summarize(
                    row
                )

            pre_1997_hits.append(
                summary
            )

        if (
            date
            and date.strftime(
                "%Y-%m-%d"
            )
            == KNOWN_INITIAL_DATE
        ):

            if (
                project_match
                or site_match
            ):

                if summary is None:

                    summary = summarize(
                        row
                    )

                initial_date_hits.append(
                    summary
                )

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "도시지역편입해제구역"
        ),

        "known_initial_district_date": (
            KNOWN_INITIAL_DATE
        ),

        "api_profile": {
            "total_rows": (
                len(
                    rows
                )
            ),
            "dated_rows": (
                len(
                    dated_rows
                )
            ),
            "oldest_date": (
                oldest_date.strftime(
                    "%Y-%m-%d"
                )
                if oldest_date
                else None
            ),
            "newest_date": (
                newest_date.strftime(
                    "%Y-%m-%d"
                )
                if newest_date
                else None
            ),
        },

        "search": {
            "project_hit_count": (
                len(
                    project_hits
                )
            ),
            "site_hit_count": (
                len(
                    site_hits
                )
            ),
            "pre_1997_project_hit_count": (
                len(
                    pre_1997_hits
                )
            ),
            "initial_date_hit_count": (
                len(
                    initial_date_hits
                )
            ),
            "history_project_hit_count": (
                len(
                    history_project_hits
                )
            ),
            "project_hits": (
                project_hits
            ),
            "pre_1997_project_hits": (
                pre_1997_hits
            ),
            "initial_date_hits": (
                initial_date_hits
            ),
            "history_project_hits": (
                history_project_hits
            ),
        },

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "1989 최초 대치택지개발지구 결정고시와 "
                "도시지역 편입/해제 사건의 연결 여부를 "
                "검증하는 단계"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # 간략 콘솔
    # ========================================================

    print(
        "Total:",
        len(
            rows
        ),
    )

    print(
        "Oldest notice:",
        (
            oldest_date.strftime(
                "%Y-%m-%d"
            )
            if oldest_date
            else None
        ),
    )

    print(
        "Newest notice:",
        (
            newest_date.strftime(
                "%Y-%m-%d"
            )
            if newest_date
            else None
        ),
    )

    print(
        "Daechi project hits:",
        len(
            project_hits
        ),
    )

    print(
        "Pre-1997 hits:",
        len(
            pre_1997_hits
        ),
    )

    print(
        "1989-03-21 hits:",
        len(
            initial_date_hits
        ),
    )

    print(
        "Project + target-history:",
        len(
            history_project_hits
        ),
    )

    # 과거 고시만 최대 5개
    for index, item in enumerate(
        pre_1997_hits[:5],
        start=1,
    ):

        print(
            f"[OLD {index}]",
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
            "| history:",
            item.get(
                "history_terms"
            ),
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