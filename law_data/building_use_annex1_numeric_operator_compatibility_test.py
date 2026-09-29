# -*- coding: utf-8 -*-
"""Regression for Annex 1 numeric comparisons using the existing E-5 evaluator."""

from law_data.rule_evaluation_pipeline import (
    evaluate_condition_expression,
    validation_e5_numeric_predicate_foundation,
)


def numeric(target: str, operator: str, value: float, unit: str) -> dict:
    return {
        "op": "NUMERIC",
        "target": target,
        "operator": operator,
        "value": value,
        "unit": unit,
    }


def fact(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def state(expression: dict, facts: dict) -> str:
    return evaluate_condition_expression({}, expression, facts).get("state")


def main() -> None:
    if not validation_e5_numeric_predicate_foundation():
        raise AssertionError("Existing LTE numeric regression failed.")

    apartment = numeric("residential_floor_count", "GTE", 5, "floor")
    if state(apartment, {"residential_floor_count": fact(5, "floor")}) != "TRUE":
        raise AssertionError("Apartment boundary 5 floors must be TRUE.")
    if state(apartment, {"residential_floor_count": fact(4, "floor")}) != "FALSE":
        raise AssertionError("Apartment 4 floors must be FALSE.")

    row_house = {
        "op": "AND",
        "children": [
            numeric("residential_floor_area", "GT", 660, "square_meter"),
            numeric("residential_floor_count", "LTE", 4, "floor"),
        ],
    }
    row_cases = [
        (661, 4, "TRUE"),
        (660, 4, "FALSE"),
        (661, 5, "FALSE"),
    ]
    for area, floors, expected in row_cases:
        actual = state(
            row_house,
            {
                "residential_floor_area": fact(area, "square_meter"),
                "residential_floor_count": fact(floors, "floor"),
            },
        )
        if actual != expected:
            raise AssertionError(
                f"Row-house boundary mismatch: area={area}, floors={floors}, "
                f"expected={expected}, actual={actual}"
            )

    multiplex_house = {
        "op": "AND",
        "children": [
            numeric("residential_floor_area", "LTE", 660, "square_meter"),
            numeric("residential_floor_count", "LTE", 4, "floor"),
        ],
    }
    multiplex_cases = [
        (660, 4, "TRUE"),
        (661, 4, "FALSE"),
    ]
    for area, floors, expected in multiplex_cases:
        actual = state(
            multiplex_house,
            {
                "residential_floor_area": fact(area, "square_meter"),
                "residential_floor_count": fact(floors, "floor"),
            },
        )
        if actual != expected:
            raise AssertionError(
                f"Multiplex-house boundary mismatch: area={area}, floors={floors}, "
                f"expected={expected}, actual={actual}"
            )

    table_tennis = numeric("use_floor_area", "LT", 500, "square_meter")
    if state(table_tennis, {"use_floor_area": fact(499, "square_meter")}) != "TRUE":
        raise AssertionError("Table-tennis 499 square meters must be TRUE.")
    if state(table_tennis, {"use_floor_area": fact(500, "square_meter")}) != "FALSE":
        raise AssertionError("Table-tennis 500 square meters must be FALSE.")

    unsupported = numeric("use_floor_area", "EQ", 500, "square_meter")
    if state(unsupported, {"use_floor_area": fact(500, "square_meter")}) != "UNKNOWN":
        raise AssertionError("Unsupported numeric operator must fail closed.")

    print("RESULT: PASS")
    print("Supported numeric operators: LT, LTE, GT, GTE")
    print("Existing LTE regression: PASS")
    print("Apartment GTE boundary: PASS")
    print("Row-house GT + LTE boundaries: PASS")
    print("Multiplex-house LTE boundaries: PASS")
    print("Table-tennis LT boundary: PASS")
    print("Unsupported operator fail-closed: PASS")
    print(
        "Not proven: full Annex 1 qualification coverage, non-numeric qualification "
        "evaluation, canonical-use resolution, frontend integration, PROJECT mapping, "
        "or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
