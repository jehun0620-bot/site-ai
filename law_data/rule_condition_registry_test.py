# -*- coding: utf-8 -*-

from rule_condition_registry import (
    build_branch_condition,
    find_missing_branch_predicates,
)


def main() -> int:

    rule = {
        "clause_index": 205,

        "rule_title": (
            "용적률의 완화"
        ),

        "text": (
            "다목에도 불구하고 제48조제7호부터 "
            "제10호까지의 지역(서울도심 지역을 포함한다)에서 "
            "다목에 따른 관광숙박시설을 건축하는 경우 "
            "용적률을 완화할 수 있다."
        ),

        "inherited_context": (
            "지구단위계획으로 고시하거나 "
            "도시계획위원회의 심의를 거쳐 완화 가능"
        ),

        "conditions": [
            {
                "name": "지구단위계획",
                "type": "SITE",
                "state": "TRUE",
            },

            {
                "name": "도시계획위원회심의",
                "type": "PROCEDURE",
                "state": "TRUE",
            },
        ],
    }

    missing = (
        find_missing_branch_predicates(
            rule
        )
    )

    names = {
        item[
            "name"
        ]
        for item
        in missing
    }

    site_registry = {
        "서울도심": {
            "state": "FALSE",
            "confidence": "HIGH",
            "source": "TEST_SITE_REGISTRY",
        },
    }

    conditions = [
        build_branch_condition(
            predicate=item,
            site_zone=(
                "제3종일반주거지역"
            ),
            site_registry=(
                site_registry
            ),
        )

        for item in missing

        if (
            item[
                "branch_priority"
            ]
            == "HIGH"
            and item[
                "direct_in_clause_text"
            ]
        )
    ]

    condition_states = {
        item[
            "name"
        ]: item[
            "state"
        ]
        for item
        in conditions
    }

    validations = {

        "서울도심 detected": (
            "서울도심"
            in names
        ),

        "article48 branch detected": (
            "서울조례제48조7호부터10호지역"
            in names
        ),

        "tourism detected": (
            "관광숙박시설"
            in names
        ),

        "서울도심 FALSE": (
            condition_states.get(
                "서울도심"
            )
            == "FALSE"
        ),

        "article48 branch FALSE": (
            condition_states.get(
                "서울조례제48조7호부터10호지역"
            )
            == "FALSE"
        ),

        "tourism UNSET": (
            condition_states.get(
                "관광숙박시설"
            )
            == "UNSET"
        ),
    }

    all_pass = all(
        validations.values()
    )

    print(
        "Missing:",
        sorted(
            names
        ),
    )

    print(
        "Resolved:",
        condition_states,
    )

    print(
        "all_pass:",
        all_pass,
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