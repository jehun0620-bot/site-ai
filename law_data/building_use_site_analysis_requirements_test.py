# -*- coding: utf-8 -*-

"""Integration regression for Site Analysis building-use requirements."""

from law_data.site_analysis_builder import (
    build_input_requirements,
    build_rule_details,
)


def main() -> int:
    engine = {
        "remaining_inputs": {
            "project": [
                {
                    "name": "공공주택",
                    "affected_clause_count": 2,
                    "state": "UNSET",
                }
            ],
            "procedure": [
                {
                    "name": "도시계획위원회심의",
                    "affected_clause_count": 1,
                    "state": "UNSET",
                }
            ],
            "building_use": [
                {
                    "name": "공연장",
                    "identity": "canonical",
                    "affected_clause_count": 1,
                    "state": "UNSET",
                }
            ],
            "numeric_facts": [
                {
                    "name": "applicable_use_floor_area",
                    "unit": "square_meter",
                    "affected_clause_count": 1,
                    "state": "UNSET",
                }
            ],
        },
        "rules": [
            {
                "clause_index": 125,
                "conditions": [
                    {
                        "type": "SITE",
                        "name": "자연경관지구",
                        "state": "TRUE",
                    }
                ],
                "required_inputs": [
                    {
                        "type": "BUILDING_USE",
                        "name": "공연장",
                        "identity": "canonical",
                        "state": "UNSET",
                    },
                    {
                        "type": "NUMERIC_FACT",
                        "name": "applicable_use_floor_area",
                        "unit": "square_meter",
                        "state": "UNSET",
                    },
                ],
            }
        ],
    }

    requirements = build_input_requirements(engine)
    details = build_rule_details(engine)
    detail = details["items"][0]

    validations = {
        "existing PROJECT requirements preserved": (
            requirements["project_count"] == 1
            and requirements["project"][0]["name"] == "공공주택"
        ),
        "existing PROCEDURE requirements preserved": (
            requirements["procedure_count"] == 1
            and requirements["procedure"][0]["name"] == "도시계획위원회심의"
        ),
        "BUILDING_USE requirements exposed": (
            requirements["building_use_count"] == 1
            and requirements["building_use"][0]["name"] == "공연장"
            and requirements["building_use"][0]["identity"] == "canonical"
        ),
        "NUMERIC_FACT requirements exposed": (
            requirements["numeric_fact_count"] == 1
            and requirements["numeric_facts"][0]["name"]
            == "applicable_use_floor_area"
            and requirements["numeric_facts"][0]["unit"] == "square_meter"
        ),
        "new requirements trigger additional input": (
            requirements["requires_additional_input"] is True
        ),
        "BUILDING_USE appears in rule detail names": (
            "공연장" in detail["required_inputs"]
        ),
        "NUMERIC_FACT appears in rule detail names": (
            "applicable_use_floor_area" in detail["required_inputs"]
        ),
        "rule detail required inputs stay string list": (
            all(isinstance(item, str) for item in detail["required_inputs"])
        ),
        "empty requirements do not trigger additional input": (
            build_input_requirements(
                {
                    "remaining_inputs": {
                        "project": [],
                        "procedure": [],
                        "building_use": [],
                        "numeric_facts": [],
                    }
                }
            )["requires_additional_input"]
            is False
        ),
        "building use alone triggers additional input": (
            build_input_requirements(
                {
                    "remaining_inputs": {
                        "building_use": [
                            {
                                "name": "공연장",
                                "identity": "canonical",
                                "affected_clause_count": 1,
                                "state": "UNSET",
                            }
                        ]
                    }
                }
            )["requires_additional_input"]
            is True
        ),
        "numeric fact alone triggers additional input": (
            build_input_requirements(
                {
                    "remaining_inputs": {
                        "numeric_facts": [
                            {
                                "name": "applicable_use_floor_area",
                                "unit": "square_meter",
                                "affected_clause_count": 1,
                                "state": "UNSET",
                            }
                        ]
                    }
                }
            )["requires_additional_input"]
            is True
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
