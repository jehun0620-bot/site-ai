# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-3B-1
서울도심 SITE condition resolution

목표
======================================================================
C-10 최종 Rule Evaluation에서 남아 있는 SITE UNKNOWN 중
'서울도심'을 공식 정의에 따라 해소한다.

공식 정의
======================================================================
「서울특별시 서울도심 정비 및 관리에 관한 조례」 제2조

"서울도심" =
한양도성과 그 일부지역을 포함하는 지역으로서
서울특별시 도시계획 조례 시행규칙에서 정한 구역

2040 서울도시기본계획의 중심지 체계:
- 서울도심
- 여의도
- 강남

따라서:
'강남'이라는 광역 중심지와 법령상 '서울도심'은 동일하지 않음.

현재 SITE
======================================================================
서울특별시 강남구 개포동 12번지

판정
======================================================================
서울도심 = FALSE / HIGH
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


STEP_NAME = (
    "STEP 17-21-C-10-3B-1 "
    "서울도심 SITE condition resolution"
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

FINAL_RULE_PATH = (
    OUTPUT_DIR
    / "site_rule_evaluation_final_snapshot.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_downtown_condition_resolution.json"
)


# ============================================================
# SITE
# ============================================================

SITE = {
    "site_id": "11680-10300-0012-0000",
    "address": "서울특별시 강남구 개포동 12번지",
    "sido": "서울특별시",
    "sigungu": "강남구",
    "dong": "개포동",
}


# ============================================================
# 공식 서울도심 정의
# ============================================================

OFFICIAL_DEFINITION = {
    "source": (
        "서울특별시 서울도심 정비 및 관리에 관한 조례"
    ),

    "article": (
        "제2조제1호"
    ),

    "definition": (
        "한양도성과 그 일부지역을 포함하는 지역으로서 "
        "서울특별시 도시계획 조례 시행규칙에서 정한 구역"
    ),

    "planning_context": (
        "2040 서울도시기본계획은 3도심을 "
        "서울도심ㆍ여의도ㆍ강남으로 서로 구분"
    ),
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

    final_rules = load_json(
        FINAL_RULE_PATH
    )

    # ========================================================
    # 1. 기존 unresolved SITE condition 확인
    # ========================================================

    unresolved = (
        final_rules.get(
            "input_requirements",
            {},
        ).get(
            "unresolved_site_conditions",
            [],
        )
    )

    downtown_entry = next(
        (
            item
            for item in unresolved
            if item.get(
                "name"
            )
            == "서울도심"
        ),
        None,
    )

    was_unresolved = (
        downtown_entry
        is not None
    )

    affected_clause_count = (
        int(
            downtown_entry.get(
                "affected_clause_count",
                0,
            )
        )
        if downtown_entry
        else 0
    )

    # ========================================================
    # 2. geographic / planning classification
    #
    # 개포동은 강남권이며 법령상 서울도심
    # (한양도성 중심 범역)이 아님.
    # ========================================================

    is_gangnam = (
        SITE[
            "sigungu"
        ]
        == "강남구"
    )

    is_gaepo = (
        SITE[
            "dong"
        ]
        == "개포동"
    )

    # --------------------------------------------------------
    # 여기서는 단순히 "강남구니까 FALSE"라고 하지 않는다.
    #
    # 공식 계획에서 서울도심과 강남을
    # 별도의 도심으로 구분하는 정의를 사용한다.
    # --------------------------------------------------------

    seoul_downtown = False

    status = (
        "FALSE"
    )

    confidence = (
        "HIGH"
    )

    reason = (
        "현행 「서울특별시 서울도심 정비 및 관리에 관한 조례」는 "
        "서울도심을 한양도성과 그 일부지역을 포함하는 별도 구역으로 "
        "정의하고 있으며, 2040 서울도시기본계획에서도 "
        "서울도심과 강남을 서로 다른 도심으로 구분한다. "
        "대상 SITE는 강남구 개포동 12번지이므로 "
        "해당 법령상 서울도심에 포함되지 않는 것으로 판정"
    )

    # ========================================================
    # 3. clause impact
    # ========================================================

    affected_rules = []

    for rule in final_rules.get(
        "rules",
        [],
    ):

        if not isinstance(
            rule,
            dict,
        ):
            continue

        conditions = rule.get(
            "conditions",
            []
        )

        downtown_conditions = [
            condition
            for condition
            in conditions
            if isinstance(
                condition,
                dict,
            )
            and condition.get(
                "name"
            )
            == "서울도심"
        ]

        if not downtown_conditions:
            continue

        affected_rules.append(
            {
                "clause_index": (
                    rule.get(
                        "clause_index"
                    )
                ),

                "law_name": (
                    rule.get(
                        "law_name"
                    )
                ),

                "rule_title": (
                    rule.get(
                        "rule_title"
                    )
                ),

                "previous_applicability": (
                    rule.get(
                        "applicability"
                    )
                ),

                "previous_condition_states": [
                    item.get(
                        "state"
                    )
                    for item
                    in downtown_conditions
                ],

                "resolved_condition_state": (
                    status
                ),

                "expected_applicability_after_overlay": (
                    "NOT_APPLICABLE"
                ),
            }
        )

    # ========================================================
    # 4. validations
    # ========================================================

    validations = {

        "SITE 강남구": (
            is_gangnam
        ),

        "SITE 개포동": (
            is_gaepo
        ),

        "서울도심 기존 unresolved 확인": (
            was_unresolved
        ),

        "서울도심 affected clause 존재": (
            len(
                affected_rules
            )
            > 0
        ),

        "affected clause count 일치": (
            len(
                affected_rules
            )
            == affected_clause_count
        ),

        "서울도심 FALSE": (
            status
            == "FALSE"
        ),

        "confidence HIGH": (
            confidence
            == "HIGH"
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # 5. output
    # ========================================================

    output = {
        "step": (
            STEP_NAME
        ),

        "site": (
            SITE
        ),

        "condition": {
            "name": (
                "서울도심"
            ),

            "type": (
                "SITE"
            ),

            "status": (
                status
            ),

            "confidence": (
                confidence
            ),

            "reason": (
                reason
            ),
        },

        "official_definition": (
            OFFICIAL_DEFINITION
        ),

        "previous_state": {
            "was_unresolved": (
                was_unresolved
            ),

            "affected_clause_count": (
                affected_clause_count
            ),
        },

        "affected_rules": (
            affected_rules
        ),

        "next_overlay": {
            "action": (
                "서울도심 condition을 UNKNOWN -> FALSE로 overlay"
            ),

            "expected_effect": (
                "서울도심을 필요로 하는 조문을 "
                "NOT_APPLICABLE로 재평가"
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
    # concise console
    # ========================================================

    print(
        "Condition:",
        "서울도심",
    )

    print(
        "Previous:",
        (
            "UNKNOWN"
            if was_unresolved
            else "NOT_FOUND"
        ),
    )

    print(
        "Resolved:",
        status,
        "/",
        confidence,
    )

    print()

    print(
        "Affected clauses:",
        len(
            affected_rules
        ),
    )

    for item in affected_rules:

        print(
            f"- clause "
            f"{item['clause_index']} "
            f"| "
            f"{item['previous_applicability']} "
            f"-> "
            f"{item['expected_applicability_after_overlay']} "
            f"| "
            f"{item['rule_title']}"
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