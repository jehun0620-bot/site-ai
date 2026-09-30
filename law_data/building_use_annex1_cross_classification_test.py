# -*- coding: utf-8 -*-
"""Behavioral contract for verified Annex 1 cross-classification branches."""

from __future__ import annotations

from law_data.building_use_annex1_cross_classification import (
    VERIFIED_CROSS_CLASSIFICATIONS,
    evaluate_cross_classifications,
)


def numeric_fact(value: float, unit: str = "square_meter") -> dict:
    return {
        "state": "TRUE",
        "value": value,
        "unit": unit,
    }


def one(canonical_name: str, facts: dict | None = None):
    results = evaluate_cross_classifications(canonical_name, facts)
    assert len(results) == 1
    return results[0]


def main() -> int:
    validations: dict[str, bool] = {}

    validations["verified relation count"] = len(VERIFIED_CROSS_CLASSIFICATIONS) == 2

    for canonical_name in ("체육관", "운동장"):
        no_seats = one(
            canonical_name,
            {"has_spectator_seating": {"state": "FALSE"}},
        )
        below = one(
            canonical_name,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": numeric_fact(999),
            },
        )
        boundary = one(
            canonical_name,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": numeric_fact(1000),
            },
        )
        above = one(
            canonical_name,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": numeric_fact(1001),
            },
        )
        missing_all = one(canonical_name)
        missing_area = one(
            canonical_name,
            {"has_spectator_seating": {"state": "TRUE"}},
        )
        wrong_unit = one(
            canonical_name,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": numeric_fact(1000, "meter"),
            },
        )

        prefix = canonical_name
        validations[f"{prefix} no seating -> FALSE"] = no_seats.state == "FALSE"
        validations[f"{prefix} 999 -> FALSE"] = below.state == "FALSE"
        validations[f"{prefix} 1000 -> TRUE"] = boundary.state == "TRUE"
        validations[f"{prefix} 1001 -> TRUE"] = above.state == "TRUE"
        validations[f"{prefix} missing facts -> UNSET"] = missing_all.state == "UNSET"
        validations[f"{prefix} missing area -> UNSET"] = missing_area.state == "UNSET"
        validations[f"{prefix} wrong unit fail-closed"] = wrong_unit.state in {
            "UNKNOWN",
            "UNSET",
        }

        validations[f"{prefix} target canonical"] = (
            boundary.relation.resolved_canonical_name == "관람장"
        )
        validations[f"{prefix} target path"] = (
            boundary.relation.target_source_path.key == "5/다"
        )
        validations[f"{prefix} candidate only, not final fact"] = not hasattr(
            boundary,
            "classification_status",
        )

    validations["unrelated use has no cross candidate"] = (
        evaluate_cross_classifications("사무소") == ()
    )
    validations["집회장 remains outside this registry"] = (
        evaluate_cross_classifications("집회장") == ()
    )

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: verified 체육관/운동장 -> 관람장(5/다) candidate branches only; "
        "no Final Classifier, BuildingUseFact, Rule125, API, or Frontend authority."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
