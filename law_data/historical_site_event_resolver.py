from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
TRUE_CANDIDATE = "TRUE_CANDIDATE"
FALSE = "FALSE"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventEvidenceState:
    """Fail-closed evidence state for SITE_HISTORY-style historical conditions.

    A False value means only "not positively verified". It must not be interpreted
    as legal absence or as permission to resolve the condition FALSE.
    """

    verified_qualifying_event_present: bool = False
    official_history_source_verified: bool = False
    history_scope_complete_verified: bool = False
    required_originals_resolved: bool = False
    candidate_universe_exhaustively_enumerated: bool = False
    all_candidates_classified_non_target: bool = False
    unresolved_historical_source_present: bool = False

    @property
    def exhaustive_disproof_verified(self) -> bool:
        return (
            not self.verified_qualifying_event_present
            and self.official_history_source_verified
            and self.history_scope_complete_verified
            and self.required_originals_resolved
            and self.candidate_universe_exhaustively_enumerated
            and self.all_candidates_classified_non_target
            and not self.unresolved_historical_source_present
        )


def resolve_historical_site_event(
    evidence_state: HistoricalSiteEventEvidenceState,
    *,
    search_hit: bool | None = None,
    http_200: bool | None = None,
    candidate_count: int | None = None,
    negative_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve a reusable historical SITE event contract without production wiring.

    Discovery signals are diagnostic only. TRUE requires a positively verified
    qualifying historical event. FALSE is allowed only when the historical universe
    itself is positively verified as complete and exhaustively non-qualifying.
    Otherwise the resolver fails closed to UNKNOWN.
    """

    if evidence_state.verified_qualifying_event_present:
        resolution = TRUE_CANDIDATE
        resolution_basis = "VERIFIED_QUALIFYING_EVENT"
    elif evidence_state.exhaustive_disproof_verified:
        resolution = FALSE
        resolution_basis = "VERIFIED_EXHAUSTIVE_DISPROOF"
    else:
        resolution = UNKNOWN
        resolution_basis = "INSUFFICIENT_VERIFIED_HISTORICAL_EVIDENCE"

    return {
        "resolution_type": RESOLUTION_TYPE,
        "resolution": resolution,
        "resolution_basis": resolution_basis,
        "evidence_state": {
            "verified_qualifying_event_present": (
                evidence_state.verified_qualifying_event_present
            ),
            "official_history_source_verified": (
                evidence_state.official_history_source_verified
            ),
            "history_scope_complete_verified": (
                evidence_state.history_scope_complete_verified
            ),
            "required_originals_resolved": evidence_state.required_originals_resolved,
            "candidate_universe_exhaustively_enumerated": (
                evidence_state.candidate_universe_exhaustively_enumerated
            ),
            "all_candidates_classified_non_target": (
                evidence_state.all_candidates_classified_non_target
            ),
            "unresolved_historical_source_present": (
                evidence_state.unresolved_historical_source_present
            ),
        },
        "exhaustive_disproof_verified": evidence_state.exhaustive_disproof_verified,
        "generic_negative_inference_allowed": False,
        "legal_absence_inference_from_discovery_allowed": False,
        "automatic_true_promotion_allowed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "diagnostic_discovery": {
            "search_hit": search_hit,
            "http_200": http_200,
            "candidate_count": candidate_count,
            "negative_evidence": dict(negative_evidence or {}),
            "dispositive": False,
        },
    }
