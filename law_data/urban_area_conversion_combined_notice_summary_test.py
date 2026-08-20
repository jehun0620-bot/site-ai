# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14C-2
도시지역편입해제구역 Combined 결정고시 최종 분류

목표
======================================================================
1. 14C의 combined 후보만 읽는다.
2. 강남/개포라는 이유로 잡힌 일반 '해제' 오탐을 제거한다.
3. 다음 target history만 별도 분류한다.

   A. 개발제한구역 해제
   B. 시가화조정구역 해제
   C. 녹지지역 해제/변경
   D. 도시지역 신규 편입

4. 도시개발구역 / 개발행위허가제한 / 하천 / 시설 해제는 제외한다.
5. 콘솔 출력은 최대 8건으로 제한한다.
6. 아직 최종 TRUE/FALSE 판정은 하지 않는다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List


STEP_NAME = (
    "STEP 17-21-C-9-2-14C-2 "
    "Combined 결정고시 최종 분류"
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

INPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_announcement_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_combined_notice_summary.json"
)


# ============================================================
# target 분류
# ============================================================

TARGET_PATTERNS = {

    "GREENBELT_RELEASE": [
        r"개발제한구역.{0,30}해제",
        r"해제.{0,30}개발제한구역",
    ],

    "ADJUSTMENT_ZONE_RELEASE": [
        r"시가화조정구역.{0,30}해제",
        r"해제.{0,30}시가화조정구역",
    ],

    "GREEN_ZONE_CHANGE": [
        r"녹지지역.{0,40}(?:해제|변경)",
        r"(?:해제|변경).{0,40}녹지지역",
        r"자연녹지지역.{0,40}(?:변경|해제)",
        r"생산녹지지역.{0,40}(?:변경|해제)",
        r"보전녹지지역.{0,40}(?:변경|해제)",
    ],

    "URBAN_AREA_INCLUSION": [
        r"도시지역.{0,30}편입",
        r"편입.{0,30}도시지역",
        r"비도시지역.{0,50}도시지역",
        r"도시지역으로.{0,30}(?:변경|편입)",
    ],
}


# ============================================================
# 명확한 오탐 유형
# ============================================================

EXCLUSION_TERMS = [
    "개발행위허가의 제한 해제",
    "개발행위허가제한",
    "도시개발구역",
    "하천구역",
    "하천 결정",
    "도시계획시설",
    "지구단위계획구역",
    "특별계획구역",
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


def compact(
    text: str,
    limit: int = 260,
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        safe_string(
            text
        ),
    )

    if len(
        text
    ) > limit:

        return (
            text[
                :limit
            ]
            + "..."
        )

    return text


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


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
# classification
# ============================================================

def classify_target(
    text: str,
) -> List[str]:

    matches = []

    for (
        category,
        patterns,
    ) in TARGET_PATTERNS.items():

        for pattern in patterns:

            if re.search(
                pattern,
                text,
                flags=re.IGNORECASE
                | re.DOTALL,
            ):

                matches.append(
                    category
                )

                break

    return matches


def find_exclusions(
    text: str,
) -> List[str]:

    return [
        term
        for term
        in EXCLUSION_TERMS
        if term in text
    ]


# ============================================================
# main
# ============================================================

def main() -> int:

    data = load_json(
        INPUT_PATH
    )

    search = data.get(
        "search",
        {},
    )

    combined_hits = search.get(
        "combined_hits",
        [],
    )

    results = []

    target_results = []

    excluded_results = []

    uncertain_results = []

    for index, item in enumerate(
        combined_hits,
        start=1,
    ):

        row = item.get(
            "row",
            {},
        )

        title = safe_string(
            row.get(
                "TTL"
            )
        )

        content = safe_string(
            row.get(
                "CN"
            )
        )

        text = (
            title
            + " "
            + content
        )

        target_categories = (
            classify_target(
                text
            )
        )

        exclusions = (
            find_exclusions(
                text
            )
        )

        # ----------------------------------------------------
        # target pattern이 있으면 exclusion보다 target 우선
        # ----------------------------------------------------

        if target_categories:

            status = (
                "TARGET_HISTORY_CANDIDATE"
            )

        elif exclusions:

            status = (
                "EXCLUDED_OTHER_RELEASE"
            )

        else:

            status = (
                "UNRESOLVED"
            )

        record = {
            "index": (
                index
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

            "TTL": (
                title
            ),

            "target_categories": (
                target_categories
            ),

            "exclusion_terms": (
                exclusions
            ),

            "status": (
                status
            ),

            "content_preview": (
                compact(
                    content
                )
            ),
        }

        results.append(
            record
        )

        if (
            status
            == "TARGET_HISTORY_CANDIDATE"
        ):

            target_results.append(
                record
            )

        elif (
            status
            == "EXCLUDED_OTHER_RELEASE"
        ):

            excluded_results.append(
                record
            )

        else:

            uncertain_results.append(
                record
            )

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "도시지역편입해제구역"
        ),

        "input_combined_count": (
            len(
                combined_hits
            )
        ),

        "target_candidate_count": (
            len(
                target_results
            )
        ),

        "excluded_count": (
            len(
                excluded_results
            )
        ),

        "unresolved_count": (
            len(
                uncertain_results
            )
        ),

        "target_candidates": (
            target_results
        ),

        "excluded": (
            excluded_results
        ),

        "unresolved": (
            uncertain_results
        ),

        "all_results": (
            results
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "서울시 공식 결정고시 중 SITE 관련 "
                "편입/해제 후보를 법적 사건 유형별로 "
                "분류한 단계이며 Parcel 적용범위 확인 전"
            ),
        },
    }

    save_json(
        result
    )

    # ========================================================
    # compact console
    # ========================================================

    print(
        "Combined:",
        len(
            combined_hits
        ),
    )

    print(
        "Target candidates:",
        len(
            target_results
        ),
    )

    print(
        "Excluded:",
        len(
            excluded_results
        ),
    )

    print(
        "Unresolved:",
        len(
            uncertain_results
        ),
    )

    print()

    for item in results:

        print(
            f"[{item['index']}]",
            item[
                "status"
            ],
            "|",
            ",".join(
                item[
                    "target_categories"
                ]
            )
            if item[
                "target_categories"
            ]
            else "-",
            "|",
            safe_string(
                item.get(
                    "ANCMNT_YMD"
                )
            ),
            "|",
            compact(
                item.get(
                    "TTL"
                ),
                100,
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