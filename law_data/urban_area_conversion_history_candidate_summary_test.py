# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14B-1
도시지역편입해제구역 upisHistory 18개 이력 후보 요약

목표
======================================================================
1. 직전 14B JSON을 읽는다.
2. 전체 6,105건을 다시 호출하지 않는다.
3. history 관련 후보만 다시 복원한다.
4. 위치 / 지역 / 분류 / 결정고시관리코드만 간략 출력한다.
5. 문자열 후보만으로 TRUE/FALSE 판정하지 않는다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-9-2-14B-1 "
    "도시지역 편입/해제 이력 후보 요약"
)

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

PREVIOUS_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_upis_history_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_candidate_summary.json"
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

SERVICE_NAME = "upisHistory"

PAGE_SIZE = 1000

TIMEOUT = 30


# ============================================================
# 이력 조건
# ============================================================

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


def fetch_all_rows() -> List[
    Dict[str, Any]
]:

    if not SEOUL_OPEN_API_KEY:

        return []

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
        return []

    parsed = parse_page(
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
        return []

    rows = list(
        parsed[
            "rows"
        ]
    )

    total_count = (
        parsed[
            "total_count"
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

        parsed_page = parse_page(
            page[
                "payload"
            ]
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

    return rows


# ============================================================
# candidate
# ============================================================

def row_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        safe_string(
            row.get(
                key
            )
        )
        for key in (
            "LOGVM",
            "RPT_TYPE",
            "LCLSF",
            "MCLSF",
            "SCLSF",
            "PSTN_NM",
            "RGN_NM",
        )
    )


def matched_terms(
    text: str,
) -> List[str]:

    return [
        term
        for term
        in HISTORY_TERMS
        if term in text
    ]


def summarize(
    row: Dict[str, Any],
) -> Dict[str, Any]:

    text = row_text(
        row
    )

    return {
        "matched_terms": (
            matched_terms(
                text
            )
        ),

        "RPT_MNG_CD": (
            row.get(
                "RPT_MNG_CD"
            )
        ),

        "RPT_TYPE": (
            row.get(
                "RPT_TYPE"
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

        "LOGVM": (
            row.get(
                "LOGVM"
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

    rows = fetch_all_rows()

    candidates = []

    for row in rows:

        text = row_text(
            row
        )

        if not any(
            term in text
            for term
            in HISTORY_TERMS
        ):
            continue

        candidates.append(
            summarize(
                row
            )
        )

    # --------------------------------------------------------
    # 구/동 관련 간단 분류
    # --------------------------------------------------------

    gangnam_candidates = []

    gaepo_candidates = []

    for item in candidates:

        location_text = " ".join(
            [
                safe_string(
                    item.get(
                        "PSTN_NM"
                    )
                ),
                safe_string(
                    item.get(
                        "RGN_NM"
                    )
                ),
                safe_string(
                    item.get(
                        "LOGVM"
                    )
                ),
            ]
        )

        if (
            "강남"
            in location_text
        ):

            gangnam_candidates.append(
                item
            )

        if (
            "개포"
            in location_text
        ):

            gaepo_candidates.append(
                item
            )

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "candidate_count": (
            len(
                candidates
            )
        ),

        "gangnam_candidate_count": (
            len(
                gangnam_candidates
            )
        ),

        "gaepo_candidate_count": (
            len(
                gaepo_candidates
            )
        ),

        "candidates": (
            candidates
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "서울시 공식 도시계획이력 중 "
                "관련 후보를 분류한 단계. "
                "Parcel 및 결정고시 연결 전"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # 간략 출력
    # ========================================================

    print(
        "History candidates:",
        len(
            candidates
        ),
    )

    print(
        "Gangnam candidates:",
        len(
            gangnam_candidates
        ),
    )

    print(
        "Gaepo candidates:",
        len(
            gaepo_candidates
        ),
    )

    print()

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        print(
            f"[{index}]",
            ",".join(
                item[
                    "matched_terms"
                ]
            ),
            "|",
            safe_string(
                item.get(
                    "PSTN_NM"
                )
            ),
            "|",
            safe_string(
                item.get(
                    "RGN_NM"
                )
            ),
            "|",
            safe_string(
                item.get(
                    "LCLSF"
                )
            ),
            "/",
            safe_string(
                item.get(
                    "MCLSF"
                )
            ),
            "/",
            safe_string(
                item.get(
                    "SCLSF"
                )
            ),
            "| notice:",
            safe_string(
                item.get(
                    "DCSN_ANCMNT_MNG_CD"
                )
            ),
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