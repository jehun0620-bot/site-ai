# -*- coding: utf-8 -*-

"""Regression for BUILDING_USE / NUMERIC_FACT remaining-input aggregation."""

from law_data.rule_evaluation_pipeline import aggregate_remaining_inputs


def requirement(
    condition_type: str,
    name: str,
    *,
    identity: str | None = None,
    unit: str | None = None,
) -> dict:
    item = {
        "type": condition_type,
        "name": name,
        "state": "UNSET",
    }

    if identity is not None:
        item["identity"] = identity

    if unit is not None:
        item["unit"] = unit

    return item


def rule(*items: dict) -> dict:
    return {
        "required_inputs": list(items),
    }


def main() -> int:
    rules = [
        rule(
            requirement("PROJECT", "공공주택"),
            requirement("PROCEDURE", "도시계획위원회심의"),
            requirement(
                "BUILDING_USE",
                "공연장",
                identity="canonical",
            ),
            requirement(
                "NUMERIC_FACT",
                "applicable_use_floor_area",
                unit="square_meter",
            ),
        ),
        rule(
            requirement("PROJECT", "공공주택"),
            requirement(
                "BUILDING_USE",
                "공연장",
                identity="canonical",
            ),
            requirement(
                "NUMERIC_FACT",
                "applicable_use_floor_area",
                unit="square_meter",
            ),
        ),
        rule(
            requirement(
                "BUILDING_USE",
                "공연장",
                identity="major",
            ),
            requirement(
                "NUMERIC_FACT",
                "applicable_use_floor_area",
                unit="percent",
            ),
        ),
        rule(),
    ]

    result = aggregate_remaining_inputs(rules)

    validations = {
        "existing PROJECT aggregation preserved": (
            result["project"]
            == [
                {
                    "name": "공공주택",
                    "affected_clause_count": 2,
                    "state": "UNSET",
                }
            ]
        ),
        "existing PROCEDURE aggregation preserved": (
            result["procedure"]
            == [
                {
                    "name": "도시계획위원회심의",
                    "affected_clause_count": 1,
                    "state": "UNSET",
                }
            ]
        ),
        "BUILDING_USE duplicate aggregation": (
            {
                (
                    item["identity"],
                    item["name"],
                ): item["affected_clause_count"]
                for item in result["building_use"]
            }
            == {
                ("canonical", "공연장"): 2,
                ("major", "공연장"): 1,
            }
        ),
        "BUILDING_USE identity stays separate": (
            len(result["building_use"]) == 2
        ),
        "NUMERIC_FACT duplicate aggregation": (
            {
                (
                    item["name"],
                    item["unit"],
                ): item["affected_clause_count"]
                for item in result["numeric_facts"]
            }
            == {
                (
                    "applicable_use_floor_area",
                    "square_meter",
                ): 2,
                (
                    "applicable_use_floor_area",
                    "percent",
                ): 1,
            }
        ),
        "NUMERIC_FACT unit stays separate": (
            len(result["numeric_facts"]) == 2
        ),
        "missing required input is not invented": (
            aggregate_remaining_inputs([rule()])
            == {
                "project": [],
                "procedure": [],
                "building_use": [],
                "numeric_facts": [],
            }
        ),
        "invalid BUILDING_USE identity is ignored": (
            aggregate_remaining_inputs(
                [
                    rule(
                        requirement(
                            "BUILDING_USE",
                            "공연장",
                            identity="invalid",
                        )
                    )
                ]
            )["building_use"]
            == []
        ),
        "missing NUMERIC_FACT unit is ignored": (
            aggregate_remaining_inputs(
                [
                    rule(
                        requirement(
                            "NUMERIC_FACT",
                            "applicable_use_floor_area",
                        )
                    )
                ]
            )["numeric_facts"]
            == []
        ),
    }

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
