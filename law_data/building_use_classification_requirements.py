# -*- coding: utf-8 -*-
"""Missing public inputs for verified Building Use cross-classification.

This module does not define new legal classification rules. It reads only the
expressions already registered in VERIFIED_CROSS_CLASSIFICATIONS and reports
which user-supplied facts are still needed to evaluate those expressions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.building_use_annex1_cross_classification import (
    cross_classifications_for_input,
)
from law_data.rule_evaluation_pipeline import evaluate_condition_expression


STATE_FACT = "STATE_FACT"
NUMERIC_FACT = "NUMERIC_FACT"


@dataclass(frozen=True)
class BuildingUseClassificationRequirement:
    kind: str
    name: str
    unit: str | None = None


def _missing_for_expression(
    expression: dict[str, Any],
    fact_context: dict[str, Any] | None,
) -> tuple[BuildingUseClassificationRequirement, ...]:
    op = str(expression.get("op") or "").strip()

    if op == "STATE":
        target = str(expression.get("target") or "").strip()
        if not target:
            return ()
        result = evaluate_condition_expression({}, expression, fact_context)
        if result.get("state") == "UNSET":
            return (
                BuildingUseClassificationRequirement(
                    kind=STATE_FACT,
                    name=target,
                ),
            )
        return ()

    if op == "NUMERIC":
        target = str(expression.get("target") or "").strip()
        unit = str(expression.get("unit") or "").strip()
        if not target:
            return ()
        result = evaluate_condition_expression({}, expression, fact_context)
        if result.get("state") == "UNSET":
            return (
                BuildingUseClassificationRequirement(
                    kind=NUMERIC_FACT,
                    name=target,
                    unit=unit or None,
                ),
            )
        return ()

    if op == "AND":
        children = expression.get("children")
        if not isinstance(children, list):
            return ()

        requirements: list[BuildingUseClassificationRequirement] = []
        for child in children:
            if not isinstance(child, dict):
                continue

            child_result = evaluate_condition_expression({}, child, fact_context)
            child_state = child_result.get("state")

            if child_state == "FALSE":
                return ()

            if child_state == "UNSET":
                requirements.extend(_missing_for_expression(child, fact_context))
                # Ask sequentially. A missing earlier AND condition may make
                # later questions unnecessary once the user answers FALSE.
                break

            if child_state == "UNKNOWN":
                return ()

        return tuple(requirements)

    return ()


def building_use_classification_requirements(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> tuple[BuildingUseClassificationRequirement, ...]:
    """Return missing facts for verified cross-classification branches only."""

    name = str(canonical_name or "").strip()
    if not name:
        return ()

    requirements: list[BuildingUseClassificationRequirement] = []
    seen: set[tuple[str, str, str | None]] = set()

    for relation in cross_classifications_for_input(name):
        result = evaluate_condition_expression({}, relation.expression, fact_context)
        if result.get("state") != "UNSET":
            continue

        for requirement in _missing_for_expression(relation.expression, fact_context):
            key = (requirement.kind, requirement.name, requirement.unit)
            if key in seen:
                continue
            seen.add(key)
            requirements.append(requirement)

    return tuple(requirements)
