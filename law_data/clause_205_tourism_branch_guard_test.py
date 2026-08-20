# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-4B-1S
clause 205 관광숙박시설 FAR 130% branch guard

목표
======================================================================
dynamic numeric에서 활성화된 clause 205가
현재 SITE에 실제 적용 가능한지 상위 branch 조건을 검증한다.

clause 205
======================================================================
서울특별시 도시계획 조례
제51조제2항제1호사목

다목에도 불구하고 제48조제7호부터 제10호까지의 지역에서
관광숙박시설을 건축하는 경우 용적률 130% 완화.

현재 SITE
======================================================================
제3종일반주거지역

서울시 조례 제48조:
제5호 = 제3종일반주거지역 250%

따라서 제48조제7호~제10호에 해당하지 않는다.

판정
======================================================================
clause 205 = NOT_APPLICABLE / HIGH

관광숙박시설 여부를 추가 확인할 필요 없이
용도지역 branch FALSE로 종료 가능.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-4B-1S "
    "clause 205 tourism branch guard"
)


# ============================================================
# PATH
# ============================================================

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

GUARD_PATH = (
    OUTPUT_DIR
    / "dynamic_numeric_guard_reconciliation.json"
)

BASE_PATH = (
    OUTPUT_DIR
    / "base_numeric_regulation_hierarchy.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "clause_205_tourism_branch_guard.json"
)


# ============================================================
# 서울시 조례 제48조 zone mapping
# ============================================================

SEOUL_ARTICLE_48_ZONE_MAP = {

    "제1종전용주거지역": 1,
    "제2종전용주거지역": 2,

    "제1종일반주거지역": 3,
    "제2종일반주거지역": 4,
    "제3종일반주거지역": 5,

    "준주거지역": 6,

    "중심상업지역": 7,
    "일반상업지역": 8,
    "근린상업지역": 9,
    "유통상업지역": 10,
}


TARGET_BRANCH_NUMBERS = {
    7,
    8,
    9,
    10,
}


# ============================================================
# util
# ============================================================

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
# main
# ============================================================

def main() -> int:

    guard = load_json(
        GUARD_PATH
    )

    base = load_json(
        BASE_PATH
    )

    # ========================================================
    # 1. SITE zone
    # ========================================================

    site_zone = (
        base.get(
            "site_zone"
        )
    )

    article_48_number = (
        SEOUL_ARTICLE_48_ZONE_MAP.get(
            site_zone
        )
    )

    target_branch_match = (
        article_48_number
        in TARGET_BRANCH_NUMBERS
    )

    # ========================================================
    # 2. clause 205 previous detail
    # ========================================================

    detail = (
        guard.get(
            "clause_205_detail"
        )
        or {}
    )

    clause_exists = (
        detail.get(
            "clause_index"
        )
        == 205
    )

    previous_applicability = (
        detail.get(
            "applicability"
        )
    )

    previous_projected = (
        (
            detail.get(
                "comparison"
            )
            or {}
        ).get(
            "projected_value"
        )
    )

    text = str(
        detail.get(
            "text",
            ""
        )
    )

    # ========================================================
    # 3. statutory branch checks
    # ========================================================

    text_has_target_zone_branch = (
        "제48조제7호부터 제10호까지"
        in text
    )

    text_has_tourism_branch = (
        "관광숙박시설"
        in text
    )

    # --------------------------------------------------------
    # 현재 SITE는 제5호
    # target은 제7~10호
    # --------------------------------------------------------

    zone_condition = {
        "name": (
            "서울조례제48조7호부터10호지역"
        ),

        "type": (
            "SITE"
        ),

        "state": (
            "TRUE"
            if target_branch_match
            else "FALSE"
        ),

        "confidence": (
            "HIGH"
        ),

        "site_zone": (
            site_zone
        ),

        "site_article_48_number": (
            article_48_number
        ),

        "required_article_48_numbers": (
            sorted(
                TARGET_BRANCH_NUMBERS
            )
        ),
    }

    # --------------------------------------------------------
    # 관광숙박시설 조건은 현재 user input에 없음.
    #
    # 하지만 zone FALSE이므로 applicability 판정에는
    # 추가 확인이 필요하지 않음.
    # --------------------------------------------------------

    tourism_condition = {
        "name": (
            "관광숙박시설"
        ),

        "type": (
            "PROJECT"
        ),

        "state": (
            "UNSET"
        ),

        "confidence": (
            "NONE"
        ),

        "required_for_branch": (
            True
        ),

        "evaluation_required_now": (
            False
            if not target_branch_match
            else True
        ),
    }

    # ========================================================
    # 4. resolution
    # ========================================================

    if not target_branch_match:

        resolution = (
            "NOT_APPLICABLE"
        )

        confidence = (
            "HIGH"
        )

        allow_numeric_effect = (
            False
        )

        reason = (
            "clause 205는 서울특별시 도시계획 조례 "
            "제48조제7호부터 제10호까지의 지역에서 "
            "관광숙박시설을 건축하는 경우 적용되는 "
            "용적률 130% 특례다. 현재 SITE는 "
            f"{site_zone}으로 제48조제{article_48_number}호에 "
            "해당하므로 대상 용도지역 branch가 FALSE이다."
        )

    else:

        resolution = (
            "CONDITIONAL"
        )

        confidence = (
            "HIGH"
        )

        allow_numeric_effect = (
            False
        )

        reason = (
            "대상 용도지역 branch에는 해당하나 "
            "관광숙박시설 PROJECT 조건 확인 필요"
        )

    # ========================================================
    # 5. resulting numeric state
    # ========================================================

    if allow_numeric_effect:

        numeric_status = (
            "ACTIVE_CANDIDATE"
        )

    else:

        numeric_status = (
            "INACTIVE_BY_VERIFIED_BRANCH_GUARD"
        )

    # ========================================================
    # 6. final immediate candidates
    #
    # previous reconciliation에서 immediate는 clause205 하나뿐.
    # 이 조문도 제외되므로 immediate numeric = 0
    # ========================================================

    previous_immediate = (
        guard.get(
            "immediate_candidates",
            []
        )
    )

    final_immediate = [
        item
        for item
        in previous_immediate
        if int(
            item.get(
                "clause_index",
                -1,
            )
        )
        != 205
    ]

    # ========================================================
    # 7. validations
    # ========================================================

    validations = {

        "clause 205 exists": (
            clause_exists
        ),

        "previous clause205 APPLICABLE": (
            previous_applicability
            == "APPLICABLE"
        ),

        "previous projected FAR 325": (
            previous_projected
            == 325.0
        ),

        "SITE 제3종일반주거지역": (
            site_zone
            == "제3종일반주거지역"
        ),

        "SITE article48 no5": (
            article_48_number
            == 5
        ),

        "target branch is 7-10": (
            TARGET_BRANCH_NUMBERS
            == {
                7,
                8,
                9,
                10,
            }
        ),

        "SITE target branch mismatch": (
            target_branch_match
            is False
        ),

        "text target zone branch detected": (
            text_has_target_zone_branch
        ),

        "text tourism branch detected": (
            text_has_tourism_branch
        ),

        "clause205 NOT_APPLICABLE": (
            resolution
            == "NOT_APPLICABLE"
        ),

        "numeric effect inactive": (
            allow_numeric_effect
            is False
        ),

        "final immediate numeric 0": (
            len(
                final_immediate
            )
            == 0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 8. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": {
            "zone": (
                site_zone
            ),

            "seoul_article_48_number": (
                article_48_number
            ),
        },

        "clause": {
            "clause_index": (
                205
            ),

            "previous_applicability": (
                previous_applicability
            ),

            "previous_projected_far": (
                previous_projected
            ),

            "text": (
                text
            ),
        },

        "branch_conditions": {
            "zone": (
                zone_condition
            ),

            "tourism_accommodation": (
                tourism_condition
            ),
        },

        "resolution": {
            "applicability": (
                resolution
            ),

            "confidence": (
                confidence
            ),

            "allow_numeric_effect": (
                allow_numeric_effect
            ),

            "numeric_status": (
                numeric_status
            ),

            "reason": (
                reason
            ),
        },

        "numeric_reconciliation": {
            "previous_immediate_count": (
                len(
                    previous_immediate
                )
            ),

            "final_immediate_count": (
                len(
                    final_immediate
                )
            ),

            "final_immediate_candidates": (
                final_immediate
            ),
        },

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "SITE zone:",
        site_zone,
    )

    print(
        "Article 48 number:",
        article_48_number,
    )

    print(
        "Required branch:",
        "7-10",
    )

    print(
        "Zone match:",
        target_branch_match,
    )

    print()

    print(
        "Tourism condition:",
        tourism_condition[
            "state"
        ],
    )

    print(
        "Tourism evaluation required now:",
        tourism_condition[
            "evaluation_required_now"
        ],
    )

    print()

    print(
        "clause 205:",
        resolution,
        "/",
        confidence,
    )

    print(
        "Previous projected FAR:",
        previous_projected,
    )

    print(
        "Numeric active:",
        allow_numeric_effect,
    )

    print()

    print(
        "Immediate numeric before:",
        len(
            previous_immediate
        ),
    )

    print(
        "Immediate numeric after:",
        len(
            final_immediate
        ),
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )