# -*- coding: utf-8 -*-
"""Public Building Use input catalog for the currently verified classifier scope.

This is intentionally narrower than the full Annex 1 canonical catalog.
Only canonical names already admitted by the limited Final Classifier or by
an explicitly VERIFIED cross-classification input relation are exposed.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_data.building_use_annex1_cross_classification import (
    VERIFIED_CROSS_CLASSIFICATIONS,
)
from law_data.building_use_annex1_final_classifier import (
    FINAL_CLASSIFICATION_WHITELIST,
)


@dataclass(frozen=True)
class PublicBuildingUseOption:
    canonical_name: str
    input_scope: str


def public_building_use_options() -> tuple[PublicBuildingUseOption, ...]:
    scopes: dict[str, set[str]] = {}

    for canonical_name in FINAL_CLASSIFICATION_WHITELIST:
        scopes.setdefault(canonical_name, set()).add("FINAL_CLASSIFIER")

    for relation in VERIFIED_CROSS_CLASSIFICATIONS:
        scopes.setdefault(relation.input_canonical_name, set()).add(
            "VERIFIED_CROSS_CLASSIFICATION"
        )

    return tuple(
        PublicBuildingUseOption(
            canonical_name=canonical_name,
            input_scope="+".join(sorted(scopes[canonical_name])),
        )
        for canonical_name in sorted(scopes)
    )


def public_building_use_names() -> tuple[str, ...]:
    return tuple(option.canonical_name for option in public_building_use_options())
