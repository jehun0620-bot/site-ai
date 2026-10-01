# -*- coding: utf-8 -*-

"""Regression for expression-derived BUILDING_USE and NUMERIC requirements."""

from law_data.rule_evaluation_pipeline import refresh_condition_groups


def atom(name: str) -> dict:
    return {
        "op": "ATOM",
        "condition": {
            "type": "SITE",
            "name": name,
        },
    }


def building_use(value: str = "공연장") -> dict:
    return {
        "op": "BUILDING_USE",
        "identity": "canonical",
        "value": value,
    }


def numeric() -> dict:
    return {
        "op": "NUMERIC",
        "target": "applicable_use_floor_area",
        "operator": "GT",
        "value": 1000,
        "unit": "square_meter",
    }


def rule(site_state: str, expression: dict) -> dict:
    return {
        "conditions": [
            {
                "type": "SITE",
                "name": "자연경관지구",
                "state": site_state,
                "source": "EXPRESSION_REQUIREMENT_TEST",
                "derived": False,
            }
        ],
        "condition_expression": expression,
        "condition_expression_status": "VERIFIED",
    }


def groups(site_state: str, expression: dict, facts: dict) -> dict:
    item = rule(site_state, expression)
    refresh_condition_groups(item, facts)
    return {
        "required_inputs": item["required_inputs"],
        "blocked_by": item["blocked_by"],
        "unknown_by": item["unknown_by"],
    }


def required_types(result: dict) -> list[str]:
    return [item.get("type") for item in result["required_inputs"]]


def main() -> int:
    numeric_unset = {
        "op": "AND",
        "children": [
            atom("자연경관지구"),
            numeric(),
        ],
    }

    building_use_unset_or = {
        "op": "OR",
        "children": [
            atom("자연경관지구"),
            building_use(),
        ],
    }

    building_use_set_or = {
        "op": "OR",
        "children": [
            building_use("공연장"),
            building_use("집회장"),
            building_use("관람장"),
        ],
    }

    building_use_set_missing = groups("TRUE", building_use_set_or, {})
    building_use_set_performance = groups(
        "TRUE",
        building_use_set_or,
        {
            "building_use": {
                "canonical_name": "공연장",
                "major_use": "문화 및 집회시설",
                "source_path": "5/가",
                "classification_status": "RESOLVED",
            }
        },
    )
    building_use_set_spectator = groups(
        "TRUE",
        building_use_set_or,
        {
            "building_use": {
                "canonical_name": "관람장",
                "major_use": "문화 및 집회시설",
                "source_path": "5/다",
                "classification_status": "RESOLVED",
            }
        },
    )
    building_use_set_office = groups(
        "TRUE",
        building_use_set_or,
        {
            "building_use": {
                "canonical_name": "사무소",
                "major_use": "업무시설",
                "source_path": "TEST",
                "classification_status": "RESOLVED",
            }
        },
    )

    validations = {
        "TRUE AND numeric UNSET requires NUMERIC_FACT": (
            required_types(groups("TRUE", numeric_unset, {}))
            == ["NUMERIC_FACT"]
        ),
        "FALSE AND numeric UNSET does not require numeric input": (
            required_types(groups("FALSE", numeric_unset, {}))
            == []
        ),
        "FALSE OR building use UNSET requires BUILDING_USE": (
            required_types(groups("FALSE", building_use_unset_or, {}))
            == ["BUILDING_USE"]
        ),
        "TRUE OR building use UNSET does not require building use": (
            required_types(groups("TRUE", building_use_unset_or, {}))
            == []
        ),
        "numeric requirement preserves target and unit": (
            groups("TRUE", numeric_unset, {})["required_inputs"]
            == [
                {
                    "type": "NUMERIC_FACT",
                    "name": "applicable_use_floor_area",
                    "state": "UNSET",
                    "unit": "square_meter",
                }
            ]
        ),
        "building use requirement preserves canonical identity": (
            groups("FALSE", building_use_unset_or, {})["required_inputs"]
            == [
                {
                    "type": "BUILDING_USE",
                    "name": "공연장",
                    "identity": "canonical",
                    "state": "UNSET",
                }
            ]
        ),
        "available numeric fact removes numeric requirement": (
            required_types(
                groups(
                    "TRUE",
                    numeric_unset,
                    {
                        "applicable_use_floor_area": {
                            "value": 1001,
                            "unit": "square_meter",
                        }
                    },
                )
            )
            == []
        ),
        "OR building-use set becomes one canonical requirement": (
            building_use_set_missing["required_inputs"]
            == [
                {
                    "type": "BUILDING_USE",
                    "name": "building_use",
                    "identity": "canonical",
                    "state": "UNSET",
                    "allowed_values": ["공연장", "집회장", "관람장"],
                }
            ]
        ),
        "OR building-use set performance fact removes requirement": (
            building_use_set_performance["required_inputs"] == []
        ),
        "OR building-use set spectator fact removes requirement": (
            building_use_set_spectator["required_inputs"] == []
        ),
        "OR building-use set confirmed mismatch does not request another use": (
            building_use_set_office["required_inputs"] == []
        ),
        "available building use fact removes building use requirement": (
            required_types(
                groups(
                    "FALSE",
                    building_use_unset_or,
                    {
                        "building_use": {
                            "canonical_name": "공연장",
                            "major_use": "문화 및 집회시설",
                            "source_path": "5/가",
                            "classification_status": "RESOLVED",
                        }
                    },
                )
            )
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
