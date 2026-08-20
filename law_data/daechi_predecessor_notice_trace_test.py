# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14E-2
1995·1996 대치택지개발 변경고시에서 최초 지정 근거 역추적

목표
======================================================================
1. upisAnnouncement 전체 결정고시 조회
2. 대치택지 관련 1995-63 / 1996-65 고시 원문 확보
3. 본문에서 과거 고시번호/승인번호/날짜 후보 추출
4. 추출된 고시번호가 upisAnnouncement에 존재하는지 재검색
5. predecessor 고시 본문에서 다음 표현 확인
   - 개발제한구역
   - 시가화조정구역
   - 녹지지역
   - 도시지역 편입
   - 공원 해제
6. 문자열만으로 최종 판정하지 않음
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
    "STEP 17-21-C-9-2-14E-2 "
    "대치택지 변경고시 predecessor trace"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_predecessor_notice_trace.json"
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
# 기준 고시
# ============================================================

TARGET_NOTICE_NUMBERS = [
    "1995-63",
    "1996-65",
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
    "공원에서 해제",
    "공원 해제",
]


# ============================================================
# util
# ============================================================

def safe_string(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


def save_json(data: Dict[str, Any]) -> None:

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
) -> Dict[str, Any] | None:

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
        result.get("CODE"),
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


def fetch_all() -> List[Dict[str, Any]]:

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

    rows = list(rows)

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
# predecessor extraction
# ============================================================

def normalize_notice_number(
    value: str,
) -> str:

    text = safe_string(value)

    text = text.replace(
        "제",
        "",
    )

    text = text.replace(
        "호",
        "",
    )

    text = re.sub(
        r"\s+",
        "",
        text,
    )

    return text


def extract_notice_references(
    text: str,
) -> List[str]:

    """
    예:
    서울특별시고시 제1989-123호
    건설부고시 제456호
    서울시고시 1990-123호
    """

    patterns = [
        r"(?:서울특별시|서울시|건설부|건설교통부|국토교통부)?"
        r"\s*고시\s*제?\s*(\d{2,4}-\d+)\s*호?",

        r"(?:서울특별시|서울시|건설부|건설교통부|국토교통부)?"
        r"\s*고시\s*제?\s*(\d+)\s*호",
    ]

    results = []

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            value = normalize_notice_number(
                match
            )

            if value and value not in results:

                results.append(value)

    return results


def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        safe_string(value)
        for value in row.values()
        if safe_string(value)
    )


def matched_history_terms(
    text: str,
) -> List[str]:

    return [
        term
        for term in TARGET_HISTORY_TERMS
        if term in text
    ]


def summarize_notice(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    title = safe_string(
        row.get("TTL")
    )

    content = safe_string(
        row.get("CN")
    )

    text = (
        title
        + " "
        + content
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
        "TTL": title,
        "CN": content,
        "notice_references": (
            extract_notice_references(
                text
            )
        ),
        "history_terms": (
            matched_history_terms(
                text
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    rows = fetch_all()

    # --------------------------------------------------------
    # 1995 / 1996 고시 찾기
    # --------------------------------------------------------

    target_rows = []

    for row in rows:

        number = normalize_notice_number(
            safe_string(
                row.get(
                    "ANCMNT_NO"
                )
            )
        )

        if number in TARGET_NOTICE_NUMBERS:

            text = row_text(
                row
            )

            if (
                "대치"
                in text
                and "택지"
                in text
            ):

                target_rows.append(
                    row
                )

    target_notices = [
        summarize_notice(row)
        for row in target_rows
    ]

    # --------------------------------------------------------
    # predecessor 후보
    # --------------------------------------------------------

    predecessor_numbers = []

    for notice in target_notices:

        for ref in notice[
            "notice_references"
        ]:

            if (
                ref not in TARGET_NOTICE_NUMBERS
                and ref not in predecessor_numbers
            ):

                predecessor_numbers.append(
                    ref
                )

    # --------------------------------------------------------
    # predecessor 번호를 전체 DB에서 재검색
    # --------------------------------------------------------

    predecessor_matches = []

    for candidate in predecessor_numbers:

        for row in rows:

            row_number = (
                normalize_notice_number(
                    safe_string(
                        row.get(
                            "ANCMNT_NO"
                        )
                    )
                )
            )

            if row_number != candidate:
                continue

            summary = summarize_notice(
                row
            )

            predecessor_matches.append(
                summary
            )

    # --------------------------------------------------------
    # 1980~1994 대치택지 관련 넓은 검색도 같이 수행
    # --------------------------------------------------------

    older_daechi_hits = []

    for row in rows:

        text = row_text(
            row
        )

        if (
            "대치"
            not in text
            or "택지"
            not in text
        ):

            continue

        date = safe_string(
            row.get(
                "ANCMNT_YMD"
            )
        )

        year = None

        if len(date) >= 4:

            try:
                year = int(
                    date[:4]
                )
            except Exception:
                pass

        if (
            year is not None
            and 1980 <= year <= 1994
        ):

            older_daechi_hits.append(
                summarize_notice(
                    row
                )
            )

    # --------------------------------------------------------
    # 결과
    # --------------------------------------------------------

    result = {
        "step": STEP_NAME,

        "target_notice_count": (
            len(
                target_notices
            )
        ),

        "target_notices": (
            target_notices
        ),

        "predecessor_numbers": (
            predecessor_numbers
        ),

        "predecessor_match_count": (
            len(
                predecessor_matches
            )
        ),

        "predecessor_matches": (
            predecessor_matches
        ),

        "older_daechi_hit_count": (
            len(
                older_daechi_hits
            )
        ),

        "older_daechi_hits": (
            older_daechi_hits
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "1995·1996 대치택지 변경고시에서 "
                "최초 지정 근거와 이전 고시를 "
                "역추적하는 단계"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # 초간략 출력
    # ========================================================

    print(
        "Target notices:",
        len(
            target_notices
        ),
    )

    for notice in target_notices:

        print(
            safe_string(
                notice.get(
                    "ANCMNT_NO"
                )
            ),
            "| refs:",
            notice[
                "notice_references"
            ],
            "| history:",
            notice[
                "history_terms"
            ],
        )

    print()

    print(
        "Predecessor numbers:",
        predecessor_numbers,
    )

    print(
        "Predecessor matches:",
        len(
            predecessor_matches
        ),
    )

    for index, item in enumerate(
        predecessor_matches[
            :10
        ],
        start=1,
    ):

        print(
            f"[REF {index}]",
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
            item[
                "history_terms"
            ],
        )

    print()

    print(
        "1980-1994 Daechi hits:",
        len(
            older_daechi_hits
        ),
    )

    for index, item in enumerate(
        older_daechi_hits[
            :10
        ],
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
            item[
                "history_terms"
            ],
        )

    print()

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