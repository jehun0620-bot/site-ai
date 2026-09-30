# -*- coding: utf-8 -*-
"""Regression for validated public SITE fact input boundary."""

from site_data.site_analysis_fact_input import build_public_fact_context


def main() -> int:
    numeric_only = build_public_fact_context(
        numeric_facts={
            "use_floor_area": {
                "value": 500,
                "unit": "square_meter",
            }
        }
    )

    resolved = build_public_fact_context(
        building_use_name="공연장",
        numeric_facts={
            "use_floor_area": {
                "value": 500,
                "unit": "square_meter",
            }
        },
    )

    unresolved = build_public_fact_context(
        building_use_name="공연장",
    )

    validations = {
        "numeric fact preserved": (
            numeric_only["use_floor_area"]
            == {"value": 500, "unit": "square_meter"}
        ),
        "resolved building use admitted": (
            resolved.get("building_use", {}).get("canonical_name") == "공연장"
            and resolved.get("building_use", {}).get("classification_status")
            == "RESOLVED"
        ),
        "unresolved building use not invented": (
            "building_use" not in unresolved
        ),
        "invalid numeric fact ignored": (
            build_public_fact_context(
                numeric_facts={
                    "use_floor_area": {
                        "value": "500",
                        "unit": "square_meter",
                    }
                }
            )
            == {}
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
