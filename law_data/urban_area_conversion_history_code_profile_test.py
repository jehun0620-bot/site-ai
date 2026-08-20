# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14B-3
서울시 upisHistory 실제 코드/분류값 분포 복원

목표
======================================================================
1. upisHistory 전체 데이터를 조회한다.
2. RPT_TYPE / LCLSF / MCLSF / SCLSF / AREA_ICDC_CD
   실제 고유값 및 빈도를 확인한다.
3. SITE(강남/개포) 관련 행에서도 동일 분포를 따로 확인한다.
4. 상위 빈도만 콘솔에 출력한다.
5. 코드 의미는 아직 추정하지 않는다.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-9-2-14B-3 "
    "upisHistory 코드/분류값 분포 복원"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_code_profile.json"
)

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

FIELDS = [
    "RPT_TYPE",
    "LCLSF",
    "MCLSF",
    "SCLSF",
    "AREA_ICDC_CD",
]

SITE_TERMS = [
    "강남",
    "개포",
]


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
            "payload": response.json(),
            "error": None,
        }

    except Exception as exc:

        return {
            "payload": None,
            "error": str(exc),
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

    return {
        "result_code": (
            result.get("CODE")
        ),
        "total_count": int(
            service.get(
                "list_total_count",
                0,
            )
            or 0
        ),
        "rows": (
            service.get(
                "row",
                [],
            )
            or []
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

    payload = first.get(
        "payload"
    )

    if not isinstance(
        payload,
        dict,
    ):
        return []

    parsed = parse_page(
        payload
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

    total = parsed[
        "total_count"
    ]

    start = PAGE_SIZE + 1

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

        parsed_page = parse_page(
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

        start = end + 1

    return rows


def is_site_row(
    row: Dict[str, Any],
) -> bool:

    text = " | ".join(
        [
            safe_string(
                row.get(
                    "LOGVM"
                )
            ),
            safe_string(
                row.get(
                    "PSTN_NM"
                )
            ),
            safe_string(
                row.get(
                    "RGN_NM"
                )
            ),
        ]
    )

    return any(
        term in text
        for term
        in SITE_TERMS
    )


def profile_field(
    rows: List[
        Dict[str, Any]
    ],
    field: str,
) -> Dict[str, Any]:

    counter = Counter()

    for row in rows:

        value = safe_string(
            row.get(
                field
            )
        )

        if not value:
            value = "<EMPTY>"

        counter[
            value
        ] += 1

    return {
        "unique_count": len(
            counter
        ),
        "counts": dict(
            counter.most_common()
        ),
        "top20": [
            {
                "value": value,
                "count": count,
            }
            for (
                value,
                count,
            )
            in counter.most_common(
                20
            )
        ],
    }


def main() -> int:

    rows = fetch_all_rows()

    site_rows = [
        row
        for row
        in rows
        if is_site_row(
            row
        )
    ]

    full_profile = {}

    site_profile = {}

    for field in FIELDS:

        full_profile[
            field
        ] = profile_field(
            rows,
            field,
        )

        site_profile[
            field
        ] = profile_field(
            site_rows,
            field,
        )

    result = {
        "step": STEP_NAME,

        "total_rows": len(
            rows
        ),

        "site_rows": len(
            site_rows
        ),

        "fields": FIELDS,

        "full_profile": (
            full_profile
        ),

        "site_profile": (
            site_profile
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "upisHistory의 실제 코드/분류값 "
                "분포를 복원하는 단계"
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
        "Total rows:",
        len(
            rows
        ),
    )

    print(
        "SITE rows:",
        len(
            site_rows
        ),
    )

    print()

    for field in FIELDS:

        info = full_profile[
            field
        ]

        print(
            f"{field}: "
            f"unique={info['unique_count']}"
        )

        print(
            "  TOP:",
            [
                (
                    item[
                        "value"
                    ],
                    item[
                        "count"
                    ],
                )
                for item
                in info[
                    "top20"
                ][
                    :8
                ]
            ],
        )

    print()

    print(
        "--- SITE rows ---"
    )

    for field in FIELDS:

        info = site_profile[
            field
        ]

        print(
            f"{field}: "
            f"unique={info['unique_count']}"
        )

        print(
            "  TOP:",
            [
                (
                    item[
                        "value"
                    ],
                    item[
                        "count"
                    ],
                )
                for item
                in info[
                    "top20"
                ][
                    :8
                ]
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