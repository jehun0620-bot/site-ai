# -*- coding: utf-8 -*-
"""Resolve candidate Annex 1 source paths for one canonical building use.

This module is deliberately fail-closed. It does not infer missing legal
qualifications. Candidates with no VERIFIED qualification rule remain UNSET. Registered numeric and major-use exclusion qualifications are combined fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from law_data.building_use_annex1_canonical_catalog import (
    BuildingUseCatalogEntry,
    catalog_entries_for_name,
)
from law_data.building_use_annex1_qualification_registry import (
    qualification_rules_for_candidate,
)
from law_data.rule_evaluation_pipeline import evaluate_condition_expression


VALID_STATES = {"TRUE", "FALSE", "UNKNOWN", "UNSET"}


@dataclass(frozen=True)
class BuildingUseCandidateResult:
    entry: BuildingUseCatalogEntry
    state: str
    qualification_status: str

    def __post_init__(self) -> None:
        if self.state not in VALID_STATES:
            raise ValueError(f"invalid candidate state: {self.state}")
        if self.qualification_status not in {"VERIFIED", "UNREGISTERED"}:
            raise ValueError(
                f"invalid qualification_status: {self.qualification_status}"
            )


def candidate_results_for_major_use(
    results: Iterable[BuildingUseCandidateResult],
    major_use: str,
) -> tuple[BuildingUseCandidateResult, ...]:
    """Return already-evaluated candidates belonging to one legal major use."""

    name = major_use.strip()
    if not name:
        raise ValueError("major_use is required")

    return tuple(
        result
        for result in results
        if result.entry.major_use == name
    )



def aggregate_candidate_state(
    results: Iterable[BuildingUseCandidateResult],
) -> str:
    """Aggregate candidate states with the existing four-state OR semantics.

    No candidates means UNSET rather than FALSE because absence of a catalog
    candidate is not proof that the legal classification is false.
    """

    states = tuple(result.state for result in results)
    if not states:
        return "UNSET"
    if "TRUE" in states:
        return "TRUE"
    if "UNKNOWN" in states:
        return "UNKNOWN"
    if "UNSET" in states:
        return "UNSET"
    if all(state == "FALSE" for state in states):
        return "FALSE"
    return "UNKNOWN"


def negate_candidate_state(state: str) -> str:
    """Negate a verified four-state result without turning uncertainty true."""

    if state not in VALID_STATES:
        raise ValueError(f"invalid candidate state: {state}")
    if state == "TRUE":
        return "FALSE"
    if state == "FALSE":
        return "TRUE"
    return state


def major_use_classification_state(
    results: Iterable[BuildingUseCandidateResult],
    major_use: str,
) -> str:
    """Return the aggregated state for one legal major-use classification."""

    return aggregate_candidate_state(
        candidate_results_for_major_use(results, major_use)
    )


def excluded_major_use_state(
    results: Iterable[BuildingUseCandidateResult],
    major_use: str,
) -> str:
    """Return the four-state meaning of 'not classified as this major use'."""

    return negate_candidate_state(
        major_use_classification_state(results, major_use)
    )

def _and_states(states: Iterable[str]) -> str:
    values = tuple(states)
    if not values:
        return "UNSET"
    if "FALSE" in values:
        return "FALSE"
    if "UNKNOWN" in values:
        return "UNKNOWN"
    if "UNSET" in values:
        return "UNSET"
    if all(state == "TRUE" for state in values):
        return "TRUE"
    return "UNKNOWN"


def _evaluate_qualification_rule(
    qualification: Any,
    fact_context: dict[str, Any] | None,
) -> str:
    if qualification.expression is None:
        return "UNSET"

    evaluated = evaluate_condition_expression(
        {},
        qualification.expression,
        fact_context,
    )
    state = evaluated.get("state", "UNKNOWN")
    if state not in VALID_STATES:
        return "UNKNOWN"
    return state


def resolve_candidate_source_paths(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> tuple[BuildingUseCandidateResult, ...]:
    """Evaluate every catalog candidate without inferring missing qualifications."""

    entries = catalog_entries_for_name(canonical_name)
    base_results: list[BuildingUseCandidateResult] = []
    candidate_rules: dict[str, tuple[Any, ...]] = {}

    for entry in entries:
        qualifications = qualification_rules_for_candidate(
            entry.source_path,
            entry.canonical_name,
        )
        candidate_rules[entry.source_path.key] = qualifications

        if not qualifications:
            base_results.append(
                BuildingUseCandidateResult(
                    entry=entry,
                    state="UNSET",
                    qualification_status="UNREGISTERED",
                )
            )
            continue

        expression_states = tuple(
            _evaluate_qualification_rule(qualification, fact_context)
            for qualification in qualifications
            if qualification.expression is not None
        )
        state = _and_states(expression_states) if expression_states else "UNSET"

        base_results.append(
            BuildingUseCandidateResult(
                entry=entry,
                state=state,
                qualification_status="VERIFIED",
            )
        )

    final_results: list[BuildingUseCandidateResult] = []
    for result in base_results:
        qualifications = candidate_rules[result.entry.source_path.key]
        excluded_major_uses = tuple(
            major_use
            for qualification in qualifications
            for major_use in qualification.excluded_major_uses
        )
        if not excluded_major_uses:
            final_results.append(result)
            continue

        exclusion_states = tuple(
            excluded_major_use_state(base_results, major_use)
            for major_use in excluded_major_uses
        )
        expression_states = tuple(
            _evaluate_qualification_rule(qualification, fact_context)
            for qualification in qualifications
            if qualification.expression is not None
        )
        states = (*expression_states, *exclusion_states)

        final_results.append(
            BuildingUseCandidateResult(
                entry=result.entry,
                state=_and_states(states),
                qualification_status=result.qualification_status,
            )
        )

    return tuple(final_results)
