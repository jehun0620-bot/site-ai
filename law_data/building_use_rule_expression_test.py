# -*- coding: utf-8 -*-

"""Regression for BUILDING_USE facts consumed by the E-5 expression evaluator."""

from law_data.rule_evaluation_pipeline import evaluate_condition_expression


def building_use(identity: str, value: str) -> dict:
    return {
        "op": "BUILDING_USE",
        "identity": identity,
        "value": value,
    }


def numeric(target: str, operator: str, value: float, unit: str) -> dict:
    return {
        "op": "NUMERIC",
        "target": target,
        "operator": operator,
        "value": value,
        "unit": unit,
    }


def state(expression: dict, facts=None) -> str:
    return evaluate_condition_expression({}, expression, facts).get("state")


def main() -> int:
    facts = {
        "building_use": {
            "canonical_name": "공연장",
            "major_use": "문화 및 집회시설",
            "source_path": "5/가",
            "classification_status": "RESOLVED",
        },
        "total_floor_area": {
            "value": 1200,
            "unit": "square_meter",
        },
    }

    validations = {
        "canonical match": (
            state(building_use("canonical", "공연장"), facts) == "TRUE"
        ),
        "canonical mismatch": (
            state(building_use("canonical", "사무소"), facts) == "FALSE"
        ),
        "source path match": (
            state(building_use("source_path", "5/가"), facts) == "TRUE"
        ),
        "source path mismatch": (
            state(building_use("source_path", "4/가"), facts) == "FALSE"
        ),
        "major match": (
            state(building_use("major", "문화 및 집회시설"), facts) == "TRUE"
        ),
        "major mismatch": (
            state(building_use("major", "공장"), facts) == "FALSE"
        ),
        "missing fact context": (
            state(building_use("canonical", "공연장")) == "UNSET"
        ),
        "missing building use fact": (
            state(building_use("canonical", "공연장"), {}) == "UNSET"
        ),
        "malformed building use fact": (
            state(
                building_use("canonical", "공연장"),
                {"building_use": "공연장"},
            )
            == "UNKNOWN"
        ),
        "missing selected identity value": (
            state(
                building_use("source_path", "5/가"),
                {
                    "building_use": {
                        "canonical_name": "공연장",
                        "major_use": "문화 및 집회시설",
                    }
                },
            )
            == "UNKNOWN"
        ),
        "unsupported identity": (
            state(building_use("detail", "가"), facts) == "UNKNOWN"
        ),
        "missing expected value": (
            state(building_use("canonical", ""), facts) == "UNKNOWN"
        ),
    }

    combined = {
        "op": "AND",
        "children": [
            building_use("canonical", "공연장"),
            numeric(
                "total_floor_area",
                "GT",
                1000,
                "square_meter",
            ),
        ],
    }
    validations["BUILDING_USE + NUMERIC AND"] = state(combined, facts) == "TRUE"

    negated = {
        "op": "NOT",
        "child": building_use("major", "공장"),
    }
    validations["BUILDING_USE + NOT"] = state(negated, facts) == "TRUE"

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
