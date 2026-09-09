from __future__ import annotations

import sys
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR))

from historical_site_event_resolver import (  # noqa: E402
    FALSE,
    TRUE_CANDIDATE,
    UNKNOWN,
    HistoricalSiteEventEvidenceState,
    resolve_historical_site_event,
)


def resolve(**kwargs):
    return resolve_historical_site_event(HistoricalSiteEventEvidenceState(**kwargs))


def main() -> int:
    positive = resolve(verified_qualifying_event_present=True)

    no_hit_only = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(),
        search_hit=False,
        negative_evidence={"search_no_hit": True},
    )

    database_zero_only = resolve_historical_site_event(
        HistoricalSiteEventEvidenceState(),
        http_200=True,
        candidate_count=0,
        negative_evidence={"official_database_query_success": True},
    )

    complete_disproof = resolve(
        official_history_source_verified=True,
        history_scope_complete_verified=True,
        required_originals_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_classified_non_target=True,
    )

    incomplete_scope = resolve(
        official_history_source_verified=True,
        history_scope_complete_verified=False,
        required_originals_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_classified_non_target=True,
    )

    unresolved_original = resolve(
        official_history_source_verified=True,
        history_scope_complete_verified=True,
        required_originals_resolved=False,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_classified_non_target=True,
        unresolved_historical_source_present=True,
    )

    incomplete_enumeration = resolve(
        official_history_source_verified=True,
        history_scope_complete_verified=True,
        required_originals_resolved=True,
        candidate_universe_exhaustively_enumerated=False,
        all_candidates_classified_non_target=True,
    )

    unresolved_source_blocks_false = resolve(
        official_history_source_verified=True,
        history_scope_complete_verified=True,
        required_originals_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_classified_non_target=True,
        unresolved_historical_source_present=True,
    )

    positive_precedes_negative_universe = resolve(
        verified_qualifying_event_present=True,
        official_history_source_verified=True,
        history_scope_complete_verified=True,
        required_originals_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_classified_non_target=True,
    )

    cases = {
        "verified positive event becomes TRUE_CANDIDATE": (
            positive["resolution"] == TRUE_CANDIDATE
        ),
        "positive event does not auto-promote TRUE": (
            positive["automatic_true_promotion_allowed"] is False
        ),
        "search no-hit alone remains UNKNOWN": no_hit_only["resolution"] == UNKNOWN,
        "database success plus zero candidates remains UNKNOWN": (
            database_zero_only["resolution"] == UNKNOWN
        ),
        "discovery diagnostics are non-dispositive": (
            no_hit_only["diagnostic_discovery"]["dispositive"] is False
            and database_zero_only["diagnostic_discovery"]["dispositive"] is False
        ),
        "complete verified universe allows FALSE": (
            complete_disproof["resolution"] == FALSE
            and complete_disproof["exhaustive_disproof_verified"] is True
            and complete_disproof["resolution_basis"] == "VERIFIED_EXHAUSTIVE_DISPROOF"
        ),
        "incomplete history scope blocks FALSE": incomplete_scope["resolution"] == UNKNOWN,
        "unresolved original blocks FALSE": unresolved_original["resolution"] == UNKNOWN,
        "incomplete enumeration blocks FALSE": incomplete_enumeration["resolution"] == UNKNOWN,
        "unresolved historical source blocks FALSE": (
            unresolved_source_blocks_false["resolution"] == UNKNOWN
        ),
        "verified positive event takes precedence over disproof fields": (
            positive_precedes_negative_universe["resolution"] == TRUE_CANDIDATE
        ),
        "generic negative inference is always disabled": all(
            result["generic_negative_inference_allowed"] is False
            for result in (
                positive,
                no_hit_only,
                database_zero_only,
                complete_disproof,
                incomplete_scope,
                unresolved_original,
            )
        ),
        "discovery cannot infer legal absence": all(
            result["legal_absence_inference_from_discovery_allowed"] is False
            for result in (no_hit_only, database_zero_only, complete_disproof)
        ),
        "resolver remains pure and production-unwired": all(
            result["production_wiring_applied"] is False
            and result["runtime_registry_mutated"] is False
            for result in (
                positive,
                no_hit_only,
                database_zero_only,
                complete_disproof,
                incomplete_scope,
                unresolved_original,
                incomplete_enumeration,
                unresolved_source_blocks_false,
            )
        ),
    }

    all_pass = all(cases.values())

    print("=" * 72)
    print("HISTORICAL SITE EVENT RESOLVER REGRESSION")
    print("=" * 72)
    for name, passed in cases.items():
        print(f"{name}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        "HISTORICAL_SITE_EVENT_GENERALIZED_SAFETY_CONTRACT_PASS"
        if all_pass
        else "CLASSIFICATION: HISTORICAL_SITE_EVENT_GENERALIZED_SAFETY_CONTRACT_FAIL"
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
