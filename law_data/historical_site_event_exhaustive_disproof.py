"""Fail-closed exhaustive-disproof boundary for HISTORICAL_SITE_EVENT.

This module evaluates only explicit positive evidence that the legally relevant
historical universe has been exhaustively resolved and disproves the target event.
It does not search sources, infer legal absence from no-hit signals, generate a
FALSE regulation result, mutate SITE/Rule Engine/runtime state, register production
logic, write outputs, or expose a public API contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_EXHAUSTIVE_DISPROOF"


def _is_explicit_true(value: object) -> bool:
    """Accept only the literal boolean True as verified evidence."""

    return value is True


@dataclass(frozen=True)
class HistoricalSiteEventExhaustiveDisproofEvidence:
    """Independent positive facts required for exhaustive historical disproof."""

    official_history_source_verified: bool = False
    history_scope_completeness_verified: bool = False
    required_original_documents_resolved: bool = False
    candidate_universe_exhaustively_enumerated: bool = False
    all_candidates_verified_non_target: bool = False
    no_unresolved_historical_source: bool = False


@dataclass(frozen=True)
class HistoricalSiteEventExhaustiveDisproofAssessment:
    """Read-only assessment of the exhaustive-disproof evidence contract."""

    boundary: str
    official_history_source_verified: bool
    history_scope_completeness_verified: bool
    required_original_documents_resolved: bool
    candidate_universe_exhaustively_enumerated: bool
    all_candidates_verified_non_target: bool
    no_unresolved_historical_source: bool
    missing_gates: tuple[str, ...]
    exhaustive_disproof_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "official_history_source_verified": self.official_history_source_verified,
            "history_scope_completeness_verified": (
                self.history_scope_completeness_verified
            ),
            "required_original_documents_resolved": (
                self.required_original_documents_resolved
            ),
            "candidate_universe_exhaustively_enumerated": (
                self.candidate_universe_exhaustively_enumerated
            ),
            "all_candidates_verified_non_target": (
                self.all_candidates_verified_non_target
            ),
            "no_unresolved_historical_source": self.no_unresolved_historical_source,
            "missing_gates": list(self.missing_gates),
            "exhaustive_disproof_verified": self.exhaustive_disproof_verified,
            "negative_evidence_inference_allowed": False,
            "search_no_hit_promoted_to_disproof": False,
            "candidate_zero_promoted_to_disproof": False,
            "search_exhaustion_promoted_to_universe_completeness": False,
            "legal_absence_inference_allowed": False,
            "negative_resolution_generated": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_exhaustive_disproof(
    evidence: HistoricalSiteEventExhaustiveDisproofEvidence,
) -> HistoricalSiteEventExhaustiveDisproofAssessment:
    """Verify exhaustive disproof only from six explicit positive evidence gates.

    The evaluator deliberately accepts no search-result, candidate-count, current
    geometry, provenance, contract-readiness, or runtime shortcut parameters.
    Missing, partial, or truthy non-boolean values fail closed.
    """

    gates = {
        "official_history_source_verified": _is_explicit_true(
            evidence.official_history_source_verified
        ),
        "history_scope_completeness_verified": _is_explicit_true(
            evidence.history_scope_completeness_verified
        ),
        "required_original_documents_resolved": _is_explicit_true(
            evidence.required_original_documents_resolved
        ),
        "candidate_universe_exhaustively_enumerated": _is_explicit_true(
            evidence.candidate_universe_exhaustively_enumerated
        ),
        "all_candidates_verified_non_target": _is_explicit_true(
            evidence.all_candidates_verified_non_target
        ),
        "no_unresolved_historical_source": _is_explicit_true(
            evidence.no_unresolved_historical_source
        ),
    }

    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    exhaustive_disproof_verified = not missing_gates

    return HistoricalSiteEventExhaustiveDisproofAssessment(
        boundary=BOUNDARY_NAME,
        official_history_source_verified=gates["official_history_source_verified"],
        history_scope_completeness_verified=gates[
            "history_scope_completeness_verified"
        ],
        required_original_documents_resolved=gates[
            "required_original_documents_resolved"
        ],
        candidate_universe_exhaustively_enumerated=gates[
            "candidate_universe_exhaustively_enumerated"
        ],
        all_candidates_verified_non_target=gates[
            "all_candidates_verified_non_target"
        ],
        no_unresolved_historical_source=gates["no_unresolved_historical_source"],
        missing_gates=missing_gates,
        exhaustive_disproof_verified=exhaustive_disproof_verified,
    )
