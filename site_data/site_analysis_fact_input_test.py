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

    spectator_true = build_public_fact_context(
        has_spectator_seating=True,
    )
    spectator_false = build_public_fact_context(
        has_spectator_seating=False,
    )
    undecided_numeric = build_public_fact_context(
        numeric_facts={
            "spectator_seating_area": {
                "value": None,
                "unit": "square_meter",
                "undecided": True,
            }
        }
    )
    contradictory_numeric = build_public_fact_context(
        numeric_facts={
            "spectator_seating_area": {
                "value": 1000,
                "unit": "square_meter",
                "undecided": True,
            }
        }
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
        "spectator true maps to internal TRUE": (
            spectator_true.get("has_spectator_seating") == {"state": "TRUE"}
        ),
        "spectator false maps to internal FALSE": (
            spectator_false.get("has_spectator_seating") == {"state": "FALSE"}
        ),
        "undecided numeric maps to internal UNKNOWN": (
            undecided_numeric.get("spectator_seating_area") == {"state": "UNKNOWN"}
        ),
        "contradictory numeric is ignored fail closed": (
            "spectator_seating_area" not in contradictory_numeric
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
