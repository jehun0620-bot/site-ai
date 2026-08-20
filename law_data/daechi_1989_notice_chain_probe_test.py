# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14E-3
1989 대치택지개발 고시 chain 직접 검증

검증 대상
======================================================================
A. 1989-04-21 건설부 고시 제123호
   수서·대치지구 택지개발예정지구 지정

B. 1989-10-27 건설부 고시 제608호
   대치지구 택지개발계획 승인

C. 1989-12-22 서울특별시 고시 제534호
   대치지구 택지개발사업 실시계획 승인

목표
======================================================================
1. 서울시 upisAnnouncement 43,508건에서 정확한 날짜/번호를 조회한다.
2. 동일 번호 오탐을 막기 위해 날짜 + 번호 + 대치/수서 문맥을 함께 검증한다.
3. 각 고시의 실제 title/content/provider를 출력한다.
4. 개발제한구역/시가화조정구역/녹지지역/도시지역 편입 표현을 확인한다.
5. API 본문이 비어 있으면 MISSING_CONTENT로 명확히 기록한다.
6. 자료 부재 자체를 FALSE 근거로 사용하지 않는다.
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
    "STEP 17-21-C-9-2-14E-3 "
    "1989 대치택지개발 고시 chain 직접 검증"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_1989_notice_chain_probe.json"
)


# ============================================================
# 환경
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
# 검증 대상
# ============================================================

TARGETS = [
    {
        "key": "INITIAL_DESIGNATION",
        "date": "1989-04-21",
        "notice_no": "1989-123",
        "expected_terms": [
            "대치",
            "수서",
            "택지",
        ],
        "expected_event": (
            "택지개발예정지구 지정"
        ),
    },
    {
        "key": "DEVELOPMENT_PLAN",
        "date": "1989-10-27",
        "notice_no": "1989-608",
        "expected_terms": [
            "대치",
            "택지",
        ],
        "expected_event": (
            "택지개발계획 승인"
        ),
    },
    {
        "key": "IMPLEMENTATION_PLAN",
        "date": "1989-12-22",
        "notice_no": "1989-534",
        "expected_terms": [
            "대치",
            "택지",
        ],
        "expected_event": (
            "택지개발사업 실시계획 승인"
        ),
    },
]


HISTORY_TERMS = [
    "개발제한구역",
    "시가화조정구역",
    "녹지지역",
    "자연녹지지역",
    "생산녹지지역",
    "보전녹지지역",
    "공원 해제",
    "공원에서 해제",
    "도시지역 편입",
    "도시지역편입",
    "도시지역으로 편입",
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


def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(value),
    ).strip()


def normalize_notice_number(
    value: Any,
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


def normalize_date(
    value: Any,
) -> str:

    text = safe_string(value)

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
# row 분석
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


def find_history_terms(
    text: str,
) -> List[str]:

    return [
        term
        for term
        in HISTORY_TERMS
        if term in text
    ]


def content_status(
    row: Dict[str, Any],
) -> str:

    title = normalize_space(
        row.get("TTL")
    )

    content = normalize_space(
        row.get("CN")
    )

    combined = (
        title
        + " "
        + content
    )

    if (
        not title
        and not content
    ):

        return (
            "MISSING_CONTENT"
        )

    if (
        "기구축내용없음"
        in combined
    ):

        return (
            "MISSING_CONTENT"
        )

    return (
        "CONTENT_AVAILABLE"
    )


def summarize(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    title = normalize_space(
        row.get("TTL")
    )

    content = normalize_space(
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
        "ANCMNT_TYPE": (
            row.get(
                "ANCMNT_TYPE"
            )
        ),
        "TTL": (
            title
        ),
        "CN": (
            content
        ),
        "content_status": (
            content_status(
                row
            )
        ),
        "history_terms": (
            find_history_terms(
                text
            )
        ),
    }


# ============================================================
# target search
# ============================================================

def find_target_rows(
    rows: List[
        Dict[str, Any]
    ],
    target: Dict[str, Any],
) -> Dict[str, Any]:

    target_date = (
        target[
            "date"
        ]
    )

    target_number = (
        target[
            "notice_no"
        ]
    )

    exact_date_number = []

    context_matches = []

    # --------------------------------------------------------
    # 1. 날짜 + 고시번호 정확 일치
    # --------------------------------------------------------

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        number = (
            normalize_notice_number(
                row.get(
                    "ANCMNT_NO"
                )
            )
        )

        if (
            date
            != target_date
        ):

            continue

        if (
            number
            != target_number
        ):

            continue

        exact_date_number.append(
            summarize(
                row
            )
        )

    # --------------------------------------------------------
    # 2. 번호가 API 표기와 다를 가능성에 대비
    #    같은 날짜 + 대치/수서/택지 문맥
    # --------------------------------------------------------

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        if date != target_date:
            continue

        text = row_text(
            row
        )

        matched = [
            term
            for term
            in target[
                "expected_terms"
            ]
            if term in text
        ]

        if len(matched) < 2:
            continue

        summary = summarize(
            row
        )

        summary[
            "matched_context_terms"
        ] = (
            matched
        )

        context_matches.append(
            summary
        )

    return {
        "target": (
            target
        ),
        "exact_date_number_count": (
            len(
                exact_date_number
            )
        ),
        "exact_date_number": (
            exact_date_number
        ),
        "date_context_count": (
            len(
                context_matches
            )
        ),
        "date_context_matches": (
            context_matches
        ),
    }


# ============================================================
# 1989 대치 전체 관련 자료
# ============================================================

def find_1989_daechi_rows(
    rows: List[
        Dict[str, Any]
    ],
) -> List[
    Dict[str, Any]
]:

    results = []

    for row in rows:

        date = normalize_date(
            row.get(
                "ANCMNT_YMD"
            )
        )

        if not date.startswith(
            "1989-"
        ):

            continue

        text = row_text(
            row
        )

        if (
            "대치"
            not in text
        ):

            continue

        results.append(
            summarize(
                row
            )
        )

    return results


# ============================================================
# main
# ============================================================

def main() -> int:

    rows = fetch_all()

    target_results = []

    for target in TARGETS:

        target_results.append(
            find_target_rows(
                rows,
                target,
            )
        )

    daechi_1989 = (
        find_1989_daechi_rows(
            rows
        )
    )

    # --------------------------------------------------------
    # target history 발견 여부
    # --------------------------------------------------------

    history_evidence_count = 0

    missing_content_count = 0

    for result in target_results:

        combined_rows = (
            result[
                "exact_date_number"
            ]
            + result[
                "date_context_matches"
            ]
        )

        seen = set()

        for item in combined_rows:

            key = (
                safe_string(
                    item.get(
                        "ANCMNT_MNG_CD"
                    )
                )
                or (
                    safe_string(
                        item.get(
                            "ANCMNT_YMD"
                        )
                    )
                    + "|"
                    + safe_string(
                        item.get(
                            "ANCMNT_NO"
                        )
                    )
                )
            )

            if key in seen:
                continue

            seen.add(key)

            if (
                item[
                    "history_terms"
                ]
            ):

                history_evidence_count += 1

            if (
                item[
                    "content_status"
                ]
                == "MISSING_CONTENT"
            ):

                missing_content_count += 1

    # --------------------------------------------------------
    # JSON
    # --------------------------------------------------------

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "도시지역편입해제구역"
        ),

        "total_rows": (
            len(
                rows
            )
        ),

        "targets": (
            target_results
        ),

        "1989_daechi_rows": (
            daechi_1989
        ),

        "history_evidence_count": (
            history_evidence_count
        ),

        "missing_content_count": (
            missing_content_count
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "1989 최초 지정·개발계획·실시계획 "
                "공식 고시 chain의 실제 API 수록 상태와 "
                "target history 표현을 검증하는 단계"
            ),
        },

        "next_step": (
            "1989-123/608/534 중 본문 미수록 고시가 있으면 "
            "토지이음 고시 원문/첨부도면 source에서 직접 검증"
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 간략 출력
    # ========================================================

    print(
        "Total:",
        len(
            rows
        ),
    )

    for result in target_results:

        target = result[
            "target"
        ]

        print()

        print(
            f"[{target['key']}]"
        )

        print(
            "Date:",
            target[
                "date"
            ],
        )

        print(
            "Expected notice:",
            target[
                "notice_no"
            ],
        )

        print(
            "Exact:",
            result[
                "exact_date_number_count"
            ],
        )

        print(
            "Date/context:",
            result[
                "date_context_count"
            ],
        )

        candidates = (
            result[
                "exact_date_number"
            ]
            if result[
                "exact_date_number"
            ]
            else result[
                "date_context_matches"
            ]
        )

        for item in candidates[
            :3
        ]:

            print(
                "  Found:",
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
                "  Content:",
                item[
                    "content_status"
                ],
            )

            print(
                "  History:",
                item[
                    "history_terms"
                ],
            )

    print()

    print(
        "1989 Daechi rows:",
        len(
            daechi_1989
        ),
    )

    for item in daechi_1989[
        :10
    ]:

        print(
            "-",
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
            "|",
            item[
                "content_status"
            ],
        )

    print()

    print(
        "Target history evidence:",
        history_evidence_count,
    )

    print(
        "Missing-content notices:",
        missing_content_count,
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