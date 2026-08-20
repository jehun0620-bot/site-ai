# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14F
1989 대치지구 실시계획승인(서울시고시 제534호)
본문 / 토지이용 / 용도지역 관련 내용 정밀 분석

목표
======================================================================
1. 서울시 upisAnnouncement에서 1989-534 row를 정확히 찾는다.
2. CN 전체 본문을 저장한다.
3. 다음 키워드 주변 문맥을 추출한다.

   - 용도지역
   - 주거지역
   - 녹지지역
   - 자연녹지
   - 도시지역
   - 택지
   - 주택용지
   - 공원
   - 토지이용
   - 개발제한구역
   - 시가화조정구역

4. 키워드가 없어도 본문 전체는 JSON에 저장한다.
5. 콘솔에는 발견된 키워드와 짧은 문맥만 출력한다.
6. 이 단계만으로 TRUE/FALSE 판정하지 않는다.
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
    "STEP 17-21-C-9-2-14F "
    "1989-534 대치지구 실시계획승인 본문 정밀 분석"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_1989_534_content_profile.json"
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
# target
# ============================================================

TARGET_DATE = "1989-12-22"
TARGET_NO = "1989-534"

TERMS = [
    "용도지역",
    "주거지역",
    "녹지지역",
    "자연녹지",
    "생산녹지",
    "보전녹지",
    "도시지역",
    "개발제한구역",
    "시가화조정구역",
    "토지이용",
    "택지",
    "주택용지",
    "공동주택",
    "공원",
    "녹지",
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


def normalize_notice_no(
    value: Any,
) -> str:

    text = safe_string(
        value
    )

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

        payload = request_page(
            start,
            end,
        )

        if not payload:
            break

        code, _, page_rows = parse_page(
            payload
        )

        if code != "INFO-000":
            break

        rows.extend(
            page_rows
        )

        start = end + 1

    return rows


# ============================================================
# context extraction
# ============================================================

def extract_contexts(
    text: str,
    term: str,
    radius: int = 180,
) -> List[str]:

    results = []

    start = 0

    while True:

        index = text.find(
            term,
            start,
        )

        if index < 0:
            break

        left = max(
            0,
            index - radius,
        )

        right = min(
            len(text),
            index
            + len(term)
            + radius,
        )

        context = normalize_space(
            text[
                left:right
            ]
        )

        if context not in results:

            results.append(
                context
            )

        start = (
            index
            + len(term)
        )

    return results


# ============================================================
# main
# ============================================================

def main() -> int:

    rows = fetch_all()

    matches = []

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        number = normalize_notice_no(
            row.get(
                "ANCMNT_NO"
            )
        )

        if (
            date != TARGET_DATE
            or number != TARGET_NO
        ):
            continue

        text = (
            normalize_space(
                row.get(
                    "TTL"
                )
            )
            + " "
            + normalize_space(
                row.get(
                    "CN"
                )
            )
        )

        term_results = {}

        for term in TERMS:

            contexts = extract_contexts(
                text,
                term,
            )

            if contexts:

                term_results[
                    term
                ] = contexts

        matches.append(
            {
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
                "text_length": (
                    len(
                        text
                    )
                ),
                "term_results": (
                    term_results
                ),
            }
        )

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "target": {
            "date": (
                TARGET_DATE
            ),
            "notice_no": (
                TARGET_NO
            ),
        },

        "match_count": (
            len(
                matches
            )
        ),

        "matches": (
            matches
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "1989 대치지구 실시계획승인 본문의 "
                "용도지역·토지이용 내용을 분석하는 단계"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # concise console
    # ========================================================

    print(
        "Notice matches:",
        len(
            matches
        ),
    )

    for item in matches:

        print(
            "Title:",
            safe_string(
                item.get(
                    "TTL"
                )
            ),
        )

        print(
            "Text length:",
            item[
                "text_length"
            ],
        )

        print(
            "Terms:",
            list(
                item[
                    "term_results"
                ].keys()
            ),
        )

        for (
            term,
            contexts,
        ) in item[
            "term_results"
        ].items():

            print()

            print(
                f"[{term}]"
            )

            for context in contexts[
                :2
            ]:

                print(
                    "-",
                    context[
                        :350
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