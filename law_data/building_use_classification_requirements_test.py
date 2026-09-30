# -*- coding: utf-8 -*-
"""Contract test for Building Use cross-classification requirements."""

from __future__ import annotations

from law_data.building_use_classification_requirements import (
    NUMERIC_FACT,
    STATE_FACT,
    building_use_classification_requirements,
)
from law_data.building_use_annex1_final_classifier import (
    RESOLVED,
    classify_building_use,
)


def state_fact(value: bool) -> dict:
    return {"state": "TRUE" if value else "FALSE"}


def numeric_fact(value: float) -> dict:
    return {"value": value, "unit": "square_meter"}


def requirement_keys(items) -> list[tuple[str, str, str | None]]:
    return [(item.kind, item.name, item.unit) for item in items]


def main() -> int:
    validations: dict[str, bool] = {}

    for canonical_name in ("체육관", "운동장"):
        initial = building_use_classification_requirements(canonical_name)
        validations[f"{canonical_name} initially asks seating state only"] = (
            requirement_keys(initial)
            == [(STATE_FACT, "has_spectator_seating", None)]
        )

        with_seating = {
            "has_spectator_seating": state_fact(True),
        }
        after_yes = building_use_classification_requirements(
            canonical_name,
            with_seating,
        )
        validations[f"{canonical_name} seating yes asks area"] = (
            requirement_keys(after_yes)
            == [(NUMERIC_FACT, "spectator_seating_area", "square_meter")]
        )

        no_seating = {
            "has_spectator_seating": state_fact(False),
        }
        after_no = building_use_classification_requirements(
            canonical_name,
            no_seating,
        )
        validations[f"{canonical_name} seating no asks nothing else"] = (
            after_no == ()
        )

        below_context = {
            "has_spectator_seating": state_fact(True),
            "spectator_seating_area": numeric_fact(999),
        }
        below = building_use_classification_requirements(
            canonical_name,
            below_context,
        )
        validations[f"{canonical_name} 999 has no missing cross input"] = (
            below == ()
        )

        boundary_context = {
            "has_spectator_seating": state_fact(True),
            "spectator_seating_area": numeric_fact(1000),
        }
        boundary = building_use_classification_requirements(
            canonical_name,
            boundary_context,
        )
        final = classify_building_use(canonical_name, boundary_context)
        validations[f"{canonical_name} 1000 has no missing cross input"] = (
            boundary == ()
        )
        validations[f"{canonical_name} 1000 still resolves 관람장"] = (
            final.status == RESOLVED
            and final.canonical_name == "관람장"
            and final.selected_candidate is not None
            and final.selected_candidate.entry.source_path.key == "5/다"
        )

    for unrelated in ("사무소", "공연장", "집회장"):
        validations[f"{unrelated} gets no cross requirement"] = (
            building_use_classification_requirements(unrelated) == ()
        )

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: missing-input bridge for verified 체육관/운동장 -> 관람장 "
        "cross-classification only; no API, Frontend, Rule125, or JSON change."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
