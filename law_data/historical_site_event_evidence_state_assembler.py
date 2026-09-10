from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_resolver import HistoricalSiteEventEvidenceState


@dataclass(frozen=True)
class HistoricalSiteEventDisproofEvidence:
    all_candidates_classified_non_target_verified: bool = False
    unresolved_historical_source_absence_verified: bool = False


def _as_bool(mapping: Mapping[str, Any], key: str) -> bool:
    return bool(mapping.get(key, False))


def assemble_historical_site_event_evidence_state(
    *,
    positive_verification: Mapping[str, Any],
    completeness_verification: Mapping[str, Any],
    disproof_evidence: HistoricalSiteEventDisproofEvidence | None = None,
) -> dict[str, Any]:
    """Assemble canonical generalized evidence state from verified outputs only.

    This assembler intentionally refuses weak or legacy promotions. Positive event
    state must come only from the positive verifier. Historical completeness fields
    must come only from the completeness verifier. Final non-target classification
    and absence of unresolved historical sources require separate explicit positive
    proof.

    Contradictory completeness payloads fail closed: if the aggregate completeness
    flag is true but one of its required component gates is false, completeness is
    treated as unverified rather than repaired or inferred.
    """

    disproof = disproof_evidence or HistoricalSiteEventDisproofEvidence()

    verified_qualifying_event_present = _as_bool(
        positive_verification,
        "verified_qualifying_event_present",
    )

    source_set_verified = _as_bool(
        completeness_verification,
        "official_historical_source_set_verified",
    )
    authority_time_verified = _as_bool(
        completeness_verification,
        "authority_time_scope_completeness_verified",
    )
    originals_resolved = _as_bool(
        completeness_verification,
        "required_original_documents_resolved",
    )
    universe_enumerated = _as_bool(
        completeness_verification,
        "candidate_universe_exhaustively_enumerated",
    )
    reported_history_complete = _as_bool(
        completeness_verification,
        "history_scope_complete_verified",
    )

    component_complete = (
        source_set_verified
        and authority_time_verified
        and originals_resolved
        and universe_enumerated
    )
    history_scope_complete_verified = (
        reported_history_complete and component_complete
    )

    unresolved_historical_source_present = not (
        disproof.unresolved_historical_source_absence_verified
    )

    evidence_state = HistoricalSiteEventEvidenceState(
        verified_qualifying_event_present=verified_qualifying_event_present,
        official_history_source_verified=source_set_verified,
        history_scope_complete_verified=history_scope_complete_verified,
        required_originals_resolved=originals_resolved,
        candidate_universe_exhaustively_enumerated=universe_enumerated,
        all_candidates_classified_non_target=(
            disproof.all_candidates_classified_non_target_verified
        ),
        unresolved_historical_source_present=(
            unresolved_historical_source_present
        ),
    )

    return {
        "evidence_state": evidence_state,
        "canonical_mapping": {
            "verified_qualifying_event_present": (
                verified_qualifying_event_present
            ),
            "official_history_source_verified": source_set_verified,
            "history_scope_complete_verified": (
                history_scope_complete_verified
            ),
            "required_originals_resolved": originals_resolved,
            "candidate_universe_exhaustively_enumerated": (
                universe_enumerated
            ),
            "all_candidates_classified_non_target": (
                disproof.all_candidates_classified_non_target_verified
            ),
            "unresolved_historical_source_present": (
                unresolved_historical_source_present
            ),
        },
        "consistency": {
            "reported_history_scope_complete_verified": (
                reported_history_complete
            ),
            "component_history_scope_complete_verified": component_complete,
            "history_scope_completeness_consistent": (
                reported_history_complete == component_complete
            ),
            "contradictory_completeness_failed_closed": (
                reported_history_complete and not component_complete
            ),
        },
        "promotion_guards": {
            "legacy_positive_candidate_promoted": False,
            "announcement_success_promoted_to_complete_source_set": False,
            "database_negative_promoted_to_candidate_universe": False,
            "candidate_enumeration_promoted_to_non_target_classification": False,
            "absence_of_unresolved_flag_promoted_to_verified_absence": False,
        },
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
