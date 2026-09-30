# -*- coding: utf-8 -*-
"""Integration contract for progressive Building Use requirements in SITE analysis."""

from __future__ import annotations

from law_data.site_analysis_builder import build_input_requirements
from site_data.site_analysis_fact_input import build_public_fact_context


EMPTY_ENGINE = {"remaining_inputs": {}}


def requirements(building_use_name: str, *, seating=None, area=None):
    numeric_facts = {}
    if area == "UNDECIDED":
        numeric_facts["spectator_seating_area"] = {
            "value": None,
            "unit": "square_meter",
            "undecided": True,
        }
    elif area is not None:
        numeric_facts["spectator_seating_area"] = {
            "value": area,
            "unit": "square_meter",
        }

    context = build_public_fact_context(
        building_use_name=building_use_name,
        numeric_facts=numeric_facts,
        has_spectator_seating=seating,
    )
    return (
        context,
        build_input_requirements(
            EMPTY_ENGINE,
            building_use_name,
            context,
        ),
    )


def main() -> int:
    initial_context, initial = requirements("체육관")
    yes_context, yes = requirements("체육관", seating=True)
    no_context, no = requirements("체육관", seating=False)
    below_context, below = requirements("체육관", seating=True, area=999)
    boundary_context, boundary = requirements("체육관", seating=True, area=1000)
    unknown_context, unknown = requirements(
        "체육관",
        seating=True,
        area="UNDECIDED",
    )

    validations = {
        "initial asks spectator state": (
            initial["state_fact_count"] == 1
            and initial["state_facts"][0]["name"] == "has_spectator_seating"
            and initial["state_facts"][0]["source"] == "BUILDING_USE_CLASSIFICATION"
            and initial["numeric_fact_count"] == 0
        ),
        "seating yes asks spectator area": (
            yes["state_fact_count"] == 0
            and yes["numeric_fact_count"] == 1
            and yes["numeric_facts"][0]["name"] == "spectator_seating_area"
            and yes["numeric_facts"][0]["unit"] == "square_meter"
            and yes["numeric_facts"][0]["source"] == "BUILDING_USE_CLASSIFICATION"
        ),
        "seating no asks nothing": (
            no["state_fact_count"] == 0
            and no["numeric_fact_count"] == 0
            and not no["requires_additional_input"]
        ),
        "999 asks nothing": (
            below["state_fact_count"] == 0
            and below["numeric_fact_count"] == 0
        ),
        "1000 resolves spectator facility": (
            boundary_context.get("building_use", {}).get("canonical_name") == "관람장"
            and boundary_context.get("building_use", {}).get("source_path") == "5/다"
            and boundary["state_fact_count"] == 0
            and boundary["numeric_fact_count"] == 0
        ),
        "undecided stays UNKNOWN": (
            unknown_context.get("spectator_seating_area") == {"state": "UNKNOWN"}
        ),
        "undecided is not re-requested": (
            unknown["state_fact_count"] == 0
            and unknown["numeric_fact_count"] == 0
            and not unknown["requires_additional_input"]
        ),
        "existing known numeric contract retained": (
            below_context.get("spectator_seating_area")
            == {"value": 999, "unit": "square_meter"}
        ),
    }

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: Backend public-fact + SITE requirement integration only; "
        "no Frontend or Rule125 production change."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
