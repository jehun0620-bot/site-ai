# -*- coding: utf-8 -*-

"""Integration regression for the Rule 125 performance-hall branch.

This proves only the performance-hall branch shape:
SITE natural landscape district
AND confirmed canonical building use = performance hall
AND rule-applicability use-specific floor area > 1000 square meters.

It does not prove full Rule 125 automation. Assembly halls and spectator
facilities are intentionally outside this test until their classification
contracts are separately verified.
"""

from copy import deepcopy

from law_data.rule_evaluation_pipeline import evaluate_condition_expression


RULE_125_PERFORMANCE_HALL = {
    "clause_index": 125,
    "conditions": [
        {
            "type": "SITE",
            "name": "자연경관지구",
            "state": "TRUE",
            "source": "RULE_125_INTEGRATION_TEST",
            "derived": False,
        }
    ],
}


EXPRESSION = {
    "op": "AND",
    "children": [
        {
            "op": "ATOM",
            "condition": {
                "type": "SITE",
                "name": "자연경관지구",
            },
        },
        {
            "op": "BUILDING_USE",
            "identity": "canonical",
            "value": "공연장",
        },
        {
            "op": "NUMERIC",
            "target": "applicable_use_floor_area",
            "operator": "GT",
            "value": 1000,
            "unit": "square_meter",
        },
    ],
}


def building_use_fact(canonical_name: str = "공연장") -> dict:
    return {
        "canonical_name": canonical_name,
        "major_use": "문화 및 집회시설",
        "source_path": "5/가",
        "classification_status": "RESOLVED",
    }


def area_fact(value: float) -> dict:
    return {
        "value": value,
        "unit": "square_meter",
    }


def expression_state(
    *,
    site_state: str = "TRUE",
    canonical_name: str = "공연장",
    applicable_use_floor_area: float | None = 1001,
    total_floor_area: float | None = None,
) -> str:
    rule = deepcopy(RULE_125_PERFORMANCE_HALL)
    rule["conditions"][0]["state"] = site_state

    facts = {
        "building_use": building_use_fact(canonical_name),
    }

    if applicable_use_floor_area is not None:
        facts["applicable_use_floor_area"] = area_fact(
            applicable_use_floor_area
        )

    if total_floor_area is not None:
        facts["total_floor_area"] = area_fact(total_floor_area)

    return evaluate_condition_expression(
        rule,
        EXPRESSION,
        facts,
    ).get("state")


def main() -> int:
    validations = {
        "natural landscape + performance hall + 1001 sqm": (
            expression_state(applicable_use_floor_area=1001) == "TRUE"
        ),
        "1000 sqm boundary is not over 1000": (
            expression_state(applicable_use_floor_area=1000) == "FALSE"
        ),
        "999 sqm is not over 1000": (
            expression_state(applicable_use_floor_area=999) == "FALSE"
        ),
        "outside natural landscape district": (
            expression_state(
                site_state="FALSE",
                applicable_use_floor_area=1001,
            )
            == "FALSE"
        ),
        "different canonical building use": (
            expression_state(
                canonical_name="사무소",
                applicable_use_floor_area=1001,
            )
            == "FALSE"
        ),
        "missing rule-applicability area is UNSET": (
            expression_state(applicable_use_floor_area=None) == "UNSET"
        ),
        "total floor area does not substitute for use-specific area": (
            expression_state(
                applicable_use_floor_area=800,
                total_floor_area=2000,
            )
            == "FALSE"
        ),
        "total floor area alone does not satisfy rule area": (
            expression_state(
                applicable_use_floor_area=None,
                total_floor_area=2000,
            )
            == "UNSET"
        ),
    }

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: performance-hall branch only; "
        "full Rule 125 automation is not proven."
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
