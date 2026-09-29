# -*- coding: utf-8 -*-
"""Resolve candidate Annex 1 source paths for one canonical building use.

This module is deliberately fail-closed. It does not infer missing legal
qualifications. Candidates with no VERIFIED qualification rule remain UNSET.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
