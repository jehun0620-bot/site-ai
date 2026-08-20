# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14B-2
서울시 upisHistory 분류·면적증감 기반 도시지역 편입/해제 정밀 필터

목표
======================================================================
1. upisHistory 전체 6,105건을 다시 조회한다.
2. 분류(LCLSF/MCLSF/SCLSF) 자체가 용도지역/용도구역 관련인 행만 추린다.
3. 개발제한구역, 시가화조정구역, 녹지지역, 도시지역 관련 이력을 찾는다.
4. 공원 '명칭' 때문에 잡히는 지구단위계획 오탐은 제외한다.
5. 강남/개포 관련 여부를 별도 집계한다.
6. 아직 TRUE/FALSE 판정하지 않는다.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


STEP_NAME = (
    "STEP 17-21-C-9-2-14B-2 "
    "도시지역 편입/해제 이력 정밀 필터"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_history_precise_filter.json"
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
# 실제 분류 기준
# ============================================================

CLASS_TERMS = [
    "용도지역",
    "용도구역",
    "개발제한구역",
    "시가화조정구역",
    "녹지지역",
    "도시지역",
]

TARGET_TERMS = [
    "개발제한구역",
    "시가화조정구역",
    "녹지지역",
    "도시지역",
]

SITE_TERMS = [
    "개포",
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

    if not SEOUL_OPEN_API_KEY:

        return {
            "payload": None,
            "error": "SEOUL_OPEN_API_KEY 없음",
        }

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
            service.get(
                "row",
                []
            )
            or []
        ),
    }


def fetch_all_rows() -> List[
    Dict[str, Any]
]:

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

        start = (
            end + 1
        )

    return rows


# ============================================================
# 필터
# ============================================================

def classification_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        [
            safe_string(
                row.get(
                    "LCLSF"
                )
            ),
            safe_string(
                row.get(
                    "MCLSF"
                )
            ),
            safe_string(
                row.get(
                    "SCLSF"
                )
            ),
        ]
    )


def location_text(
    row: Dict[str, Any],
) -> str:

    return " | ".join(
        [
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
            safe_string(
                row.get(
                    "LOGVM"
                )
            ),
        ]
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

    cls = classification_text(
        row
    )

    loc = location_text(
        row
    )

    return {
        "class_matches": (
            matched_terms(
                cls,
                TARGET_TERMS,
            )
        ),

        "site_matches": (
            matched_terms(
                loc,
                SITE_TERMS,
            )
        ),

        "RPT_MNG_CD": (
            row.get(
                "RPT_MNG_CD"
            )
        ),

        "BFR_RPT_MNG_CD": (
            row.get(
                "BFR_RPT_MNG_CD"
            )
        ),

        "HGHRK_RPT_MNG_CD": (
            row.get(
                "HGHRK_RPT_MNG_CD"
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

    class_candidates = []

    target_candidates = []

    site_target_candidates = []

    for row in rows:

        cls = classification_text(
            row
        )

        # ----------------------------------------------------
        # 분류 자체가 용도지역/구역 계열인 것만
        # ----------------------------------------------------

        if not any(
            term in cls
            for term
            in CLASS_TERMS
        ):
            continue

        summary = summarize(
            row
        )

        class_candidates.append(
            summary
        )

        if summary[
            "class_matches"
        ]:

            target_candidates.append(
                summary
            )

            if summary[
                "site_matches"
            ]:

                site_target_candidates.append(
                    summary
                )

    # --------------------------------------------------------
    # 코드 분포
    # --------------------------------------------------------

    area_icdc_values = sorted(
        {
            safe_string(
                item.get(
                    "AREA_ICDC_CD"
                )
            )
            for item
            in target_candidates
            if safe_string(
                item.get(
                    "AREA_ICDC_CD"
                )
            )
        }
    )

    # --------------------------------------------------------
    # 결과
    # --------------------------------------------------------

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

        "classification_candidate_count": (
            len(
                class_candidates
            )
        ),

        "target_candidate_count": (
            len(
                target_candidates
            )
        ),

        "site_target_candidate_count": (
            len(
                site_target_candidates
            )
        ),

        "AREA_ICDC_CD_values": (
            area_icdc_values
        ),

        "target_candidates": (
            target_candidates
        ),

        "site_target_candidates": (
            site_target_candidates
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "서울시 공식 도시계획이력 DB에서 "
                "용도지역/용도구역 분류 기반 후보를 "
                "정밀 필터링한 단계이며 "
                "Parcel 및 결정고시 연결 전"
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
        "Total:",
        len(
            rows
        ),
    )

    print(
        "Planning class candidates:",
        len(
            class_candidates
        ),
    )

    print(
        "Target class candidates:",
        len(
            target_candidates
        ),
    )

    print(
        "SITE target candidates:",
        len(
            site_target_candidates
        ),
    )

    print(
        "AREA_ICDC_CD:",
        area_icdc_values,
    )

    # SITE 관련만 최대 10개
    for index, item in enumerate(
        site_target_candidates[
            :10
        ],
        start=1,
    ):

        print(
            f"[SITE {index}]",
            ",".join(
                item[
                    "class_matches"
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
            "| change:",
            safe_string(
                item.get(
                    "AREA_ICDC_CD"
                )
            ),
            "| notice:",
            safe_string(
                item.get(
                    "DCSN_ANCMNT_MNG_CD"
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