# -*- coding: utf-8 -*-
"""Resolve candidate Annex 1 source paths for one canonical building use.

This module is deliberately fail-closed. It does not infer missing legal
qualifications. Candidates with no VERIFIED qualification rule remain UNSET.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from law_data.building_use_annex1_canonical_catalog import (
    BuildingUseCatalogEntry,
    catalog_entries_for_name,
)
from law_data.building_use_annex1_qualification_registry import (
    qualification_rule_for_path,
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

def resolve_candidate_source_paths(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> tuple[BuildingUseCandidateResult, ...]:
    """Evaluate every catalog candidate independently.

    A registered VERIFIED qualification is evaluated by the existing E-5
    expression evaluator. A candidate whose qualification is not registered
    is not inferred from neighboring candidates; it remains UNSET.
    """

    entries = catalog_entries_for_name(canonical_name)
    results: list[BuildingUseCandidateResult] = []

    for entry in entries:
        qualification = qualification_rule_for_path(entry.source_path)

        if qualification is None:
            results.append(
                BuildingUseCandidateResult(
                    entry=entry,
                    state="UNSET",
                    qualification_status="UNREGISTERED",
                )
            )
            continue

        evaluated = evaluate_condition_expression(
            {},
            qualification.expression,
            fact_context,
        )
        state = evaluated.get("state", "UNKNOWN")
        if state not in VALID_STATES:
            state = "UNKNOWN"

        results.append(
            BuildingUseCandidateResult(
                entry=entry,
                state=state,
                qualification_status=qualification.expression_status,
            )
        )

    return tuple(results)
