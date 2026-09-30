# -*- coding: utf-8 -*-

"""Regression test for the fail-closed BUILDING_USE fact boundary."""

from __future__ import annotations

from dataclasses import replace

from law_data.building_use_annex1_final_classifier import (
    REVIEW_REQUIRED,
    UNRESOLVED,
    classify_building_use,
)
from law_data.building_use_fact import building_use_fact_from_final


def numeric_fact(value: float, unit: str = "square_meter") -> dict:
    return {
        "state": "TRUE",
        "value": value,
        "unit": unit,
    }


def main() -> int:
    resolved = classify_building_use(
        "공연장",
        {
            "use_floor_area": numeric_fact(500),
        },
    )

    fact = building_use_fact_from_final(resolved)

    validations = {
        "resolved fact exists": fact is not None,
        "canonical name preserved": fact is not None and fact.canonical_name == "공연장",
        "major use preserved": fact is not None and fact.major_use == "문화 및 집회시설",
        "source path preserved": fact is not None and fact.source_path == "5/가",
        "classification status preserved": (
            fact is not None and fact.classification_status == "RESOLVED"
        ),
    }

    unresolved = replace(
        resolved,
        status=UNRESOLVED,
        selected_candidate=None,
    )
    review_required = replace(
        resolved,
        status=REVIEW_REQUIRED,
        selected_candidate=None,
    )

    validations["UNRESOLVED does not create confirmed fact"] = (
        building_use_fact_from_final(unresolved) is None
    )
    validations["REVIEW_REQUIRED does not create confirmed fact"] = (
        building_use_fact_from_final(review_required) is None
    )

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
