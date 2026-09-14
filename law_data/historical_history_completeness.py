"""Fail-closed historical history-completeness verification boundary.

This module answers one narrow question: whether an explicitly defined historical
coverage scope has been positively and completely verified for a fixed target.

It does not search sources, discover documents, infer legal absence, verify
provenance or authority, resolve SITE applicability, read/write output artifacts,
register production/runtime logic, mutate Rule Engine input, or expose a public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


BOUNDARY_NAME = "HISTORICAL_HISTORY_COMPLETENESS"


def _normalize_names(values: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    """Return unique non-empty names while preserving declaration order."""

    if not isinstance(values, (tuple, list)):
        return ()

    normalized: list[str] = []
    seen: set[str] = set()
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        normalized.append(value)
        seen.add(value)
    return tuple(normalized)


def _normalize_verified_facts(
    facts: Mapping[str, Any] | None,
) -> dict[str, bool]:
    """Accept only explicit boolean True as positive coverage verification."""

    if not isinstance(facts, Mapping):
        return {}

    normalized: dict[str, bool] = {}
    for raw_name, raw_verified in facts.items():
        name = str(raw_name or "").strip()
        if not name:
            continue
        normalized[name] = raw_verified is True
    return normalized


@dataclass(frozen=True)
class HistoricalHistoryCompletenessEvidence:
    """Explicit evidence supplied by an independent historical coverage process.

    ``required_coverage_items`` should encode the complete required scope at the
    granularity chosen by the caller (for example source-family, time interval,
    region, event class, or a composite key). This boundary never manufactures or
    discovers those requirements itself.
    """

    target_identity_verified: Any = False
    coverage_scope_defined: Any = False
    required_coverage_items: tuple[str, ...] = ()
    verified_coverage_facts: Mapping[str, Any] | None = None
    unresolved_gaps: tuple[str, ...] = ()


@dataclass(frozen=True)
class HistoricalHistoryCompletenessAssessment:
    """Read-only fail-closed assessment of historical coverage completeness."""

    target_identity_verified: bool
    coverage_scope_defined: bool
    coverage_requirements_declared: bool
    required_coverage_items: tuple[str, ...]
    verified_coverage_items: tuple[str, ...]
    missing_coverage_items: tuple[str, ...]
    unexpected_verified_items: tuple[str, ...]
    unresolved_gaps: tuple[str, ...]
    unresolved_gap_present: bool
    history_completeness_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_name": BOUNDARY_NAME,
            "target_identity_verified": self.target_identity_verified,
            "coverage_scope_defined": self.coverage_scope_defined,
            "coverage_requirements_declared": self.coverage_requirements_declared,
            "required_coverage_items": list(self.required_coverage_items),
            "verified_coverage_items": list(self.verified_coverage_items),
            "missing_coverage_items": list(self.missing_coverage_items),
            "unexpected_verified_items": list(self.unexpected_verified_items),
            "unresolved_gaps": list(self.unresolved_gaps),
            "unresolved_gap_present": self.unresolved_gap_present,
            "history_completeness_verified": self.history_completeness_verified,
        }


def evaluate_historical_history_completeness(
    evidence: HistoricalHistoryCompletenessEvidence | None,
) -> HistoricalHistoryCompletenessAssessment:
    """Verify historical completeness only from explicit positive coverage facts.

    Positive verification requires all of the following:

    - a fixed target identity explicitly verified with boolean ``True``;
    - an explicitly defined coverage scope with boolean ``True``;
    - at least one declared required coverage item;
    - explicit boolean ``True`` verification for every required coverage item; and
    - no unresolved coverage gaps.

    Search completion/exhaustion, no-hit results, discovered-record processing,
    provenance verification, contract readiness, current geometry, truthy values,
    and unrelated facts are intentionally outside this boundary and cannot satisfy
    any requirement unless represented as an exact required item with explicit
    independent boolean ``True`` verification.
    """

    if not isinstance(evidence, HistoricalHistoryCompletenessEvidence):
        evidence = HistoricalHistoryCompletenessEvidence()

    target_identity_verified = evidence.target_identity_verified is True
    coverage_scope_defined = evidence.coverage_scope_defined is True
    required_coverage_items = _normalize_names(evidence.required_coverage_items)
    coverage_requirements_declared = bool(required_coverage_items)
    verified_facts = _normalize_verified_facts(evidence.verified_coverage_facts)
    unresolved_gaps = _normalize_names(evidence.unresolved_gaps)
    required_set = set(required_coverage_items)

    verified_coverage_items = tuple(
        item for item in required_coverage_items if verified_facts.get(item) is True
    )
    missing_coverage_items = tuple(
        item for item in required_coverage_items if verified_facts.get(item) is not True
    )
    unexpected_verified_items = tuple(
        name
        for name, verified in verified_facts.items()
        if verified is True and name not in required_set
    )
    unresolved_gap_present = bool(unresolved_gaps)

    history_completeness_verified = bool(
        target_identity_verified
        and coverage_scope_defined
        and coverage_requirements_declared
        and not missing_coverage_items
        and not unresolved_gap_present
    )

    return HistoricalHistoryCompletenessAssessment(
        target_identity_verified=target_identity_verified,
        coverage_scope_defined=coverage_scope_defined,
        coverage_requirements_declared=coverage_requirements_declared,
        required_coverage_items=required_coverage_items,
        verified_coverage_items=verified_coverage_items,
        missing_coverage_items=missing_coverage_items,
        unexpected_verified_items=unexpected_verified_items,
        unresolved_gaps=unresolved_gaps,
        unresolved_gap_present=unresolved_gap_present,
        history_completeness_verified=history_completeness_verified,
    )
