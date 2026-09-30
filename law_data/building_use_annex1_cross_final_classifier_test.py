# -*- coding: utf-8 -*-
"""Final-classifier contract for verified Annex 1 cross-classification."""

from __future__ import annotations

from law_data.building_use_annex1_final_classifier import (
    RESOLVED,
    UNRESOLVED,
    classify_building_use,
)


def state_fact(state: str) -> dict:
    return {"state": state}


def numeric_fact(value: float, unit: str = "square_meter") -> dict:
    return {"state": "TRUE", "value": value, "unit": unit}


def facts(*, seats: bool | None, area: float | None = None) -> dict:
    result: dict = {}
    if seats is not None:
        result["has_spectator_seating"] = state_fact("TRUE" if seats else "FALSE")
    if area is not None:
        result["spectator_seating_area"] = numeric_fact(area)
    return result


def selected_path(result) -> str | None:
    if result.selected_candidate is None:
        return None
    return result.selected_candidate.entry.source_path.key


def selected_major_use(result) -> str | None:
    if result.selected_candidate is None:
        return None
    return result.selected_candidate.entry.major_use


def main() -> int:
    validations: dict[str, bool] = {}

    for canonical_name in ("체육관", "운동장"):
        below = classify_building_use(
            canonical_name,
            facts(seats=True, area=999),
        )
        boundary = classify_building_use(
            canonical_name,
            facts(seats=True, area=1000),
        )
        above = classify_building_use(
            canonical_name,
            facts(seats=True, area=1001),
        )
        no_seats = classify_building_use(
            canonical_name,
            facts(seats=False),
        )
        missing = classify_building_use(canonical_name)

        validations[f"{canonical_name} 999 stays outside cross final"] = (
            below.status == UNRESOLVED
            and below.canonical_name == canonical_name
            and selected_path(below) is None
        )
        validations[f"{canonical_name} no seating stays outside cross final"] = (
            no_seats.status == UNRESOLVED
            and no_seats.canonical_name == canonical_name
            and selected_path(no_seats) is None
        )

        for label, result in (("1000", boundary), ("1001", above)):
            validations[f"{canonical_name} {label} -> RESOLVED"] = (
                result.status == RESOLVED
            )
            validations[f"{canonical_name} {label} -> 관람장"] = (
                result.canonical_name == "관람장"
            )
            validations[f"{canonical_name} {label} -> 5/다"] = (
                selected_path(result) == "5/다"
            )
            validations[f"{canonical_name} {label} -> 문화 및 집회시설"] = (
                selected_major_use(result) == "문화 및 집회시설"
            )

        validations[f"{canonical_name} missing facts -> UNRESOLVED"] = (
            missing.status == UNRESOLVED
            and missing.canonical_name == canonical_name
            and selected_path(missing) is None
        )

    assembly = classify_building_use(
        "집회장",
        facts(seats=True, area=1000),
    )
    validations["집회장 not promoted by cross classifier"] = (
        assembly.status == UNRESOLVED
        and assembly.canonical_name == "집회장"
        and selected_path(assembly) is None
    )

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: verified 체육관/운동장 -> 관람장(5/다) final promotion only; "
        "existing same-name whitelist remains unchanged."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
