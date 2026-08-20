# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14E-5
건설부고시 제123호(1989) 정확 row / 날짜 식별

목표
======================================================================
1. upisAnnouncement 43,508건 전체를 조회한다.
2. 1989년 3~4월의 고시번호 123 관련 row를 전부 찾는다.
3. 날짜를 3/21, 3/28, 4/21 중 하나로 미리 가정하지 않는다.
4. 건설부 / 수서 / 대치 / 택지개발예정지구 문맥을 확인한다.
5. ANCMNT_NO 표기가 1989-123이 아닌 경우도 대응한다.
6. 본문 누락 여부를 확인한다.
7. 검색 실패/본문 부재만으로 FALSE 판정하지 않는다.
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
    "STEP 17-21-C-9-2-14E-5 "
    "건설부고시 제123호 정확 식별"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_notice_123_exact_probe.json"
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
# 기간
# ============================================================

START_DATE = "1989-03-01"
END_DATE = "1989-04-30"


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


def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(
            value
        ),
    ).strip()


def normalize_date(
    value: Any,
) -> str:

    text = safe_string(
        value
    )

    if len(text) >= 10:
        return text[:10]

    return text


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


# ============================================================
# API
# ============================================================

def request_page(
    start: int,
    end: int,
):

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

    if not SEOUL_OPEN_API_KEY:
        return []

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

        if not page:
            break

        code, _, page_rows = (
            parse_page(
                page
            )
        )

        if code != "INFO-000":
            break

        rows.extend(
            page_rows
        )

        start = end + 1

    return rows


# ============================================================
# 검색
# ============================================================

def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        normalize_space(
            value
        )
        for value
        in row.values()
        if normalize_space(
            value
        )
    )


def looks_like_notice_123(
    row: Dict[str, Any],
) -> bool:

    number = normalize_space(
        row.get(
            "ANCMNT_NO"
        )
    )

    title = normalize_space(
        row.get(
            "TTL"
        )
    )

    content = normalize_space(
        row.get(
            "CN"
        )
    )

    text = (
        number
        + " "
        + title
        + " "
        + content
    )

    patterns = [
        r"(^|[^0-9])1989[\-\s]*123([^0-9]|$)",
        r"제\s*123\s*호",
        r"고시\s*123\s*호",
        r"고시\s*제\s*123\s*호",
    ]

    return any(
        re.search(
            pattern,
            text,
        )
        for pattern
        in patterns
    )


def content_status(
    row: Dict[str, Any],
) -> str:

    title = normalize_space(
        row.get(
            "TTL"
        )
    )

    content = normalize_space(
        row.get(
            "CN"
        )
    )

    if (
        not title
        and not content
    ):
        return "MISSING_CONTENT"

    if (
        "기구축내용없음"
        in (
            title
            + " "
            + content
        )
    ):
        return "MISSING_CONTENT"

    return "CONTENT_AVAILABLE"


def summarize(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = row_text(
        row
    )

    context_terms = [
        term
        for term
        in (
            "건설부",
            "수서",
            "대치",
            "개포",
            "택지개발",
            "택지개발예정지구",
        )
        if term in text
    ]

    history_terms = [
        term
        for term
        in (
            "개발제한구역",
            "시가화조정구역",
            "녹지지역",
            "자연녹지지역",
            "보전녹지지역",
            "생산녹지지역",
            "공원 해제",
            "도시지역 편입",
            "도시지역편입",
        )
        if term in text
    ]

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
        "content_status": (
            content_status(
                row
            )
        ),
        "context_terms": (
            context_terms
        ),
        "history_terms": (
            history_terms
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    rows = fetch_all()

    period_rows = []

    notice_123_hits = []

    context_hits = []

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        if not (
            START_DATE
            <= date
            <= END_DATE
        ):
            continue

        period_rows.append(
            row
        )

        if looks_like_notice_123(
            row
        ):

            notice_123_hits.append(
                summarize(
                    row
                )
            )

        text = row_text(
            row
        )

        if (
            (
                "수서"
                in text
                or "대치"
                in text
                or "개포"
                in text
            )
            and "택지"
            in text
        ):

            context_hits.append(
                summarize(
                    row
                )
            )

    # ========================================================
    # 후속 고시의 제123호 참조도 별도 수집
    # ========================================================

    later_reference_hits = []

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        if date <= END_DATE:
            continue

        text = row_text(
            row
        )

        if (
            "건설부"
            not in text
            or "123"
            not in text
        ):
            continue

        if not (
            "수서"
            in text
            or "대치"
            in text
        ):
            continue

        if not (
            "택지"
            in text
        ):
            continue

        later_reference_hits.append(
            summarize(
                row
            )
        )

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "total_rows": (
            len(
                rows
            )
        ),

        "period": {
            "start": (
                START_DATE
            ),
            "end": (
                END_DATE
            ),
            "row_count": (
                len(
                    period_rows
                )
            ),
        },

        "notice_123_hit_count": (
            len(
                notice_123_hits
            )
        ),

        "notice_123_hits": (
            notice_123_hits
        ),

        "period_context_hit_count": (
            len(
                context_hits
            )
        ),

        "period_context_hits": (
            context_hits
        ),

        "later_reference_hit_count": (
            len(
                later_reference_hits
            )
        ),

        "later_reference_hits": (
            later_reference_hits
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "건설부고시 제123호의 정확한 "
                "고시일자와 API 수록 여부를 "
                "1989년 3~4월 전체 범위에서 "
                "검증한 단계"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # 짧은 콘솔
    # ========================================================

    print(
        "Period rows:",
        len(
            period_rows
        ),
    )

    print(
        "Notice 123 hits:",
        len(
            notice_123_hits
        ),
    )

    for index, item in enumerate(
        notice_123_hits[
            :10
        ],
        start=1,
    ):

        print(
            f"[123-{index}]",
            normalize_date(
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
                    "ANCMNT_INST"
                )
            ),
            "|",
            safe_string(
                item.get(
                    "TTL"
                )
            ),
        )

        print(
            "  status:",
            item[
                "content_status"
            ],
            "| context:",
            item[
                "context_terms"
            ],
            "| history:",
            item[
                "history_terms"
            ],
        )

    print(
        "Period Daechi/Suseo hits:",
        len(
            context_hits
        ),
    )

    for index, item in enumerate(
        context_hits[
            :10
        ],
        start=1,
    ):

        print(
            f"[CTX-{index}]",
            normalize_date(
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
        )

    print(
        "Later references:",
        len(
            later_reference_hits
        ),
    )

    # 후속 참조는 날짜/제목만 5개
    for index, item in enumerate(
        later_reference_hits[
            :5
        ],
        start=1,
    ):

        print(
            f"[REF-{index}]",
            normalize_date(
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