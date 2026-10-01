# -*- coding: utf-8 -*-
"""Contract test for the narrow public Building Use input catalog."""

from __future__ import annotations

from law_data.building_use_annex1_cross_classification import (
    VERIFIED_CROSS_CLASSIFICATIONS,
)
from law_data.building_use_annex1_final_classifier import (
    FINAL_CLASSIFICATION_WHITELIST,
)
from site_data.building_use_public_catalog import (
    public_building_use_names,
    public_building_use_options,
)


def main() -> int:
    names = public_building_use_names()
    options = public_building_use_options()
    cross_inputs = {
        relation.input_canonical_name
        for relation in VERIFIED_CROSS_CLASSIFICATIONS
    }
    expected = FINAL_CLASSIFICATION_WHITELIST | cross_inputs

    validations = {
        "catalog equals verified input union": set(names) == expected,
        "catalog has no duplicates": len(names) == len(set(names)),
        "catalog is deterministic": names == tuple(sorted(names)),
        "체육관 is exposed": "체육관" in names,
        "운동장 is exposed": "운동장" in names,
        "verified whitelist remains exposed": FINAL_CLASSIFICATION_WHITELIST <= set(names),
        "unverified arbitrary use is excluded": "골프연습장" not in names,
        "option count matches name count": len(options) == len(names),
        "cross input scope is explicit": all(
            "VERIFIED_CROSS_CLASSIFICATION" in option.input_scope
            for option in options
            if option.canonical_name in cross_inputs
        ),
    }

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print("Public Building Use option count:", len(names))
    print("Names:", ", ".join(names))
    print(
        "Scope: public input discovery only; full Annex 1 catalog, legal "
        "classification completeness, Frontend, and Rule125 are not proven."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
