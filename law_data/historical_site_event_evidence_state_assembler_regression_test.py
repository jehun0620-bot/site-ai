from __future__ import annotations

from law_data.historical_site_event_evidence_state_assembler import (
    HistoricalSiteEventDisproofEvidence,
    assemble_historical_site_event_evidence_state,
)
from law_data.historical_site_event_resolver import resolve_historical_site_event


def _positive(verified: bool = False) -> dict:
    return {"verified_qualifying_event_present": verified}


def _completeness(
    source_set: bool = False,
    authority_time: bool = False,
    originals: bool = False,
    universe: bool = False,
    reported_complete: bool = False,
) -> dict:
    return {
        "official_historical_source_set_verified": source_set,
        "authority_time_scope_completeness_verified": authority_time,
        "required_original_documents_resolved": originals,
        "candidate_universe_exhaustively_enumerated": universe,
        "history_scope_complete_verified": reported_complete,
    }


def main() -> None:
    empty = assemble_historical_site_event_evidence_state(
        positive_verification={},
        completeness_verification={},
    )
    empty_resolution = resolve_historical_site_event(empty["evidence_state"])

    true_case = assemble_historical_site_event_evidence_state(
        positive_verification=_positive(True),
        completeness_verification=_completeness(),
    )
    true_resolution = resolve_historical_site_event(true_case["evidence_state"])

    complete_without_disproof = assemble_historical_site_event_evidence_state(
        positive_verification=_positive(False),
        completeness_verification=_completeness(
            True, True, True, True, True
        ),
    )
    complete_without_disproof_resolution = resolve_historical_site_event(
        complete_without_disproof["evidence_state"]
    )

    false_case = assemble_historical_site_event_evidence_state(
        positive_verification=_positive(False),
        completeness_verification=_completeness(
            True, True, True, True, True
        ),
        disproof_evidence=HistoricalSiteEventDisproofEvidence(
            all_candidates_classified_non_target_verified=True,
            unresolved_historical_source_absence_verified=True,
        ),
    )
    false_resolution = resolve_historical_site_event(false_case["evidence_state"])

    contradictory = assemble_historical_site_event_evidence_state(
        positive_verification=_positive(False),
        completeness_verification=_completeness(
            source_set=True,
            authority_time=False,
            originals=True,
            universe=True,
            reported_complete=True,
        ),
        disproof_evidence=HistoricalSiteEventDisproofEvidence(
            all_candidates_classified_non_target_verified=True,
            unresolved_historical_source_absence_verified=True,
        ),
    )
    contradictory_resolution = resolve_historical_site_event(
        contradictory["evidence_state"]
    )

    enumerated_only = assemble_historical_site_event_evidence_state(
        positive_verification=_positive(False),
        completeness_verification=_completeness(
            universe=True,
        ),
    )

    checks = {
        "missing inputs fail closed UNKNOWN": (
            empty_resolution["resolution"] == "UNKNOWN"
            and empty["evidence_state"].verified_qualifying_event_present is False
        ),
        "missing unresolved-source proof stays unresolved": (
            empty["evidence_state"].unresolved_historical_source_present is True
        ),
        "verified positive event maps to TRUE_CANDIDATE": (
            true_resolution["resolution"] == "TRUE_CANDIDATE"
        ),
        "complete history alone cannot manufacture FALSE": (
            complete_without_disproof_resolution["resolution"] == "UNKNOWN"
        ),
        "complete history does not imply non-target classification": (
            complete_without_disproof[
                "evidence_state"
            ].all_candidates_classified_non_target
            is False
        ),
        "complete history does not imply unresolved-source absence": (
            complete_without_disproof[
                "evidence_state"
            ].unresolved_historical_source_present
            is True
        ),
        "explicit exhaustive disproof can open FALSE": (
            false_resolution["resolution"] == "FALSE"
            and false_case["evidence_state"].exhaustive_disproof_verified is True
        ),
        "contradictory completeness fails closed": (
            contradictory[
                "evidence_state"
            ].history_scope_complete_verified
            is False
            and contradictory_resolution["resolution"] == "UNKNOWN"
            and contradictory["consistency"][
                "contradictory_completeness_failed_closed"
            ]
            is True
        ),
        "candidate enumeration cannot imply non-target classification": (
            enumerated_only[
                "evidence_state"
            ].candidate_universe_exhaustively_enumerated
            is True
            and enumerated_only[
                "evidence_state"
            ].all_candidates_classified_non_target
            is False
        ),
        "source-set mapping uses strong completeness source gate": (
            false_case["evidence_state"].official_history_source_verified is True
        ),
        "absence of unresolved flag cannot verify absence": (
            empty["promotion_guards"][
                "absence_of_unresolved_flag_promoted_to_verified_absence"
            ]
            is False
        ),
        "assembler remains production-unwired": (
            false_case["production_wiring_applied"] is False
            and false_case["overlay_mutated"] is False
            and false_case["runtime_registry_mutated"] is False
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("HISTORICAL SITE EVENT EVIDENCE STATE ASSEMBLER")
    print("=" * 72)
    for label, passed in checks.items():
        print(f"{label}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "HISTORICAL_SITE_EVENT_EVIDENCE_STATE_ASSEMBLER_PASS"
            if all_pass
            else "HISTORICAL_SITE_EVENT_EVIDENCE_STATE_ASSEMBLER_FAIL"
        )
    )

    if not all_pass:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
