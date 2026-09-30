# -*- coding: utf-8 -*-
"""Verified, branch-local Annex 1 cross-classification candidates.

This module does not perform general building-use inference and is not wired
into the production final classifier. It exposes only explicitly source-bound
cross-classification branches that have been verified from Annex 1.

Current verified scope:
- 체육관 -> 관람장 (5/다) when spectator seating exists and its floor area is
  at least 1,000 square meters.
- 운동장 -> 관람장 (5/다) under the same verified boundary.

A TRUE result means only that this cross-classification candidate branch
matched. It does not by itself create a RESOLVED BuildingUseFact.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.building_use_annex1_semantic_model import SourcePath
from law_data.rule_evaluation_pipeline import evaluate_condition_expression


VALID_STATES = {"TRUE", "FALSE", "UNKNOWN", "UNSET"}


@dataclass(frozen=True)
class BuildingUseCrossClassification:
    input_canonical_name: str
    resolved_canonical_name: str
    target_source_path: SourcePath
    expression: dict[str, Any]
    source_text: str
    status: str = "VERIFIED"

    def __post_init__(self) -> None:
        if not self.input_canonical_name.strip():
            raise ValueError("input_canonical_name is required")
        if not self.resolved_canonical_name.strip():
            raise ValueError("resolved_canonical_name is required")
        if not self.source_text.strip():
            raise ValueError("source_text is required")
        if self.status != "VERIFIED":
            raise ValueError("cross-classification admits VERIFIED relations only")


@dataclass(frozen=True)
class BuildingUseCrossClassificationResult:
    relation: BuildingUseCrossClassification
    state: str

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"invalid cross-classification state: {self.state}")


_SPECTATOR_VENUE_EXPRESSION = {
    "op": "AND",
    "children": [
        {"op": "STATE", "target": "has_spectator_seating"},
        {
            "op": "NUMERIC",
            "target": "spectator_seating_area",
            "operator": "GTE",
            "value": 1000,
            "unit": "square_meter",
        },
    ],
}


VERIFIED_CROSS_CLASSIFICATIONS: tuple[BuildingUseCrossClassification, ...] = (
    BuildingUseCrossClassification(
        input_canonical_name="체육관",
        resolved_canonical_name="관람장",
        target_source_path=SourcePath("5", "다"),
        expression=_SPECTATOR_VENUE_EXPRESSION,
        source_text=(
            "관람장 중 체육관으로서 관람석의 바닥면적의 합계가 "
            "1천제곱미터 이상인 것"
        ),
    ),
    BuildingUseCrossClassification(
        input_canonical_name="운동장",
        resolved_canonical_name="관람장",
        target_source_path=SourcePath("5", "다"),
        expression=_SPECTATOR_VENUE_EXPRESSION,
        source_text=(
            "관람장 중 운동장으로서 관람석의 바닥면적의 합계가 "
            "1천제곱미터 이상인 것"
        ),
    ),
)


def cross_classifications_for_input(
    canonical_name: str,
) -> tuple[BuildingUseCrossClassification, ...]:
    name = canonical_name.strip()
    if not name:
        raise ValueError("canonical_name is required")
    return tuple(
        relation
        for relation in VERIFIED_CROSS_CLASSIFICATIONS
        if relation.input_canonical_name == name
    )


def evaluate_cross_classifications(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> tuple[BuildingUseCrossClassificationResult, ...]:
    """Evaluate only explicitly registered cross-classification branches."""

    results: list[BuildingUseCrossClassificationResult] = []
    for relation in cross_classifications_for_input(canonical_name):
        evaluated = evaluate_condition_expression(
            {},
            relation.expression,
            fact_context,
        )
        state = evaluated.get("state", "UNKNOWN")
        if state not in VALID_STATES:
            state = "UNKNOWN"
        results.append(
            BuildingUseCrossClassificationResult(
                relation=relation,
                state=state,
            )
        )
    return tuple(results)
