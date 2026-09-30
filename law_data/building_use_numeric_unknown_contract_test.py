# -*- coding: utf-8 -*-
"""Contract test for user-declared UNKNOWN numeric Building Use facts.

UNKNOWN means the user has answered but the project value is not yet decided.
It must remain fail-closed and must not be treated as an unanswered UNSET fact.
"""

from __future__ import annotations

from law_data.building_use_annex1_cross_classification import (
    evaluate_cross_classifications,
)
from law_data.building_use_annex1_final_classifier import (
    REVIEW_REQUIRED,
    classify_building_use,
)
from law_data.building_use_classification_requirements import (
    building_use_classification_requirements,
)


def main() -> int:
    validations: dict[str, bool] = {}

    for canonical_name in ("체육관", "운동장"):
        context = {
            "has_spectator_seating": {"state": "TRUE"},
            "spectator_seating_area": {"state": "UNKNOWN"},
        }

        cross_results = evaluate_cross_classifications(canonical_name, context)
        final = classify_building_use(canonical_name, context)
        requirements = building_use_classification_requirements(
            canonical_name,
            context,
        )

        validations[f"{canonical_name} unknown area -> cross UNKNOWN"] = (
            len(cross_results) == 1
            and cross_results[0].state == "UNKNOWN"
        )
        validations[f"{canonical_name} unknown area -> final REVIEW_REQUIRED"] = (
            final.status == REVIEW_REQUIRED
            and final.selected_candidate is None
        )
        validations[
            f"{canonical_name} unknown area is answered, not repeated requirement"
        ] = requirements == ()

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Meaning: numeric UNSET remains unanswered; numeric UNKNOWN means the "
        "user answered but the project value is not yet decided. UNKNOWN stays "
        "fail-closed and is not re-requested as a missing input."
    )
    print(
        "Scope: contract only; no public API, Frontend, Rule125, or production "
        "classification logic change."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
