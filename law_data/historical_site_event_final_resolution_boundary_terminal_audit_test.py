"""Terminal audit for STEP31 HISTORICAL_SITE_EVENT semantic resolution."""

from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_final_resolution import (
    FALSE,
    TRUE,
    UNKNOWN,
    evaluate_historical_site_event_final_resolution,
)
from law_data.historical_site_event_final_resolution_candidate import (
    FALSE_CANDIDATE,
    TRUE_CANDIDATE,
    evaluate_historical_site_event_final_resolution_candidate,
)
from law_data.historical_site_event_negative_evidence_eligibility import (
    evaluate_historical_site_event_negative_evidence_eligibility,
)
from law_data.historical_site_event_negative_resolution_candidate import (
    evaluate_historical_site_event_negative_resolution_candidate,
)
from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofEvidence,
    evaluate_historical_site_event_exhaustive_disproof,
)
from law_data.historical_site_event_resolution_composition import (
    HistoricalSiteEventResolutionCompositionAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_resolution_profile_registry import (
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)


TERMINAL_CLASSIFICATION = (
    "STEP31_HISTORICAL_SITE_EVENT_FINAL_RESOLUTION_"
    "BOUNDARY_TERMINALLY_RECONCILED"
)


def _profile(name: str, allowed: bool = True) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=name,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=allowed,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )


def _positive(profile: RegulationResolutionProfile, candidate: str):
    return HistoricalSiteEventResolutionCompositionAssessment(
        boundary="STEP31_SYNTHETIC_POSITIVE",
        profile_present=True,
        profile_name=profile.name,
        historical_resolution_type_matched=True,
        historical_condition_type_matched=True,
        authority_profile_aligned=True,
        source_policy_profile_aligned=True,
        qualifying_historical_event_verified=candidate == TRUE_CANDIDATE,
        history_completeness_verified=candidate == TRUE_CANDIDATE,
        authority_requirement_satisfied=candidate == TRUE_CANDIDATE,
        source_policy_requirement_satisfied=candidate == TRUE_CANDIDATE,
        missing_gates=(),
        positive_gate_satisfied=candidate == TRUE_CANDIDATE,
        resolution_candidate=candidate,
    )


def _verified_disproof():
    return evaluate_historical_site_event_exhaustive_disproof(
        HistoricalSiteEventExhaustiveDisproofEvidence(
            official_history_source_verified=True,
            history_scope_completeness_verified=True,
            required_original_documents_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
            all_candidates_verified_non_target=True,
            no_unresolved_historical_source=True,
        )
    )


def main() -> None:
    profile = _profile("STEP31_SYNTHETIC_PROFILE")
    disproof = _verified_disproof()
    eligibility = evaluate_historical_site_event_negative_evidence_eligibility(
        profile, disproof
    )
    negative_false = evaluate_historical_site_event_negative_resolution_candidate(
        profile, disproof, eligibility
    )
    negative_unknown = replace(
        negative_false,
        negative_candidate_gate_satisfied=False,
        resolution_candidate=UNKNOWN,
    )
    positive_true = _positive(profile, TRUE_CANDIDATE)
    positive_unknown = _positive(profile, UNKNOWN)

    true_candidate = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_true, negative_unknown
    )
    true_resolution = evaluate_historical_site_event_final_resolution(
        profile, true_candidate
    )
    assert true_resolution.resolution == TRUE

    false_candidate = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_unknown, negative_false
    )
    false_resolution = evaluate_historical_site_event_final_resolution(
        profile, false_candidate
    )
    assert false_resolution.resolution == FALSE

    unknown_candidate = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_unknown, negative_unknown
    )
    unknown_resolution = evaluate_historical_site_event_final_resolution(
        profile, unknown_candidate
    )
    assert unknown_resolution.resolution == UNKNOWN

    conflict_candidate = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_true, negative_false
    )
    conflict_resolution = evaluate_historical_site_event_final_resolution(
        profile, conflict_candidate
    )
    assert conflict_candidate.conflict_detected is True
    assert conflict_resolution.resolution == UNKNOWN
    assert "candidate_conflict_free" in conflict_resolution.missing_gates

    missing_candidate = evaluate_historical_site_event_final_resolution(profile, None)
    assert missing_candidate.resolution == UNKNOWN

    other_profile = _profile("STEP31_OTHER_PROFILE")
    mismatched = evaluate_historical_site_event_final_resolution(
        other_profile, true_candidate
    )
    assert mismatched.resolution == UNKNOWN
    assert "candidate_profile_aligned" in mismatched.missing_gates

    invalid_candidate = replace(
        unknown_candidate,
        final_resolution_candidate="TRUE",
    )
    invalid = evaluate_historical_site_event_final_resolution(profile, invalid_candidate)
    assert invalid.resolution == UNKNOWN

    payload = true_resolution.to_dict()
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False

    actual_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    assert actual_profile is not None
    actual_positive = _positive(actual_profile, UNKNOWN)
    actual_eligibility = evaluate_historical_site_event_negative_evidence_eligibility(
        actual_profile, disproof
    )
    actual_negative = evaluate_historical_site_event_negative_resolution_candidate(
        actual_profile, disproof, actual_eligibility
    )
    actual_candidate = evaluate_historical_site_event_final_resolution_candidate(
        actual_profile, actual_positive, actual_negative
    )
    actual_resolution = evaluate_historical_site_event_final_resolution(
        actual_profile, actual_candidate
    )
    assert actual_profile.negative_evidence_allowed is False
    assert actual_candidate.final_resolution_candidate == UNKNOWN
    assert actual_resolution.resolution == UNKNOWN

    print("=" * 60)
    print("STEP31 HISTORICAL SITE EVENT FINAL RESOLUTION")
    print("=" * 60)
    print("TRUE_CANDIDATE -> semantic TRUE: PASS")
    print("FALSE_CANDIDATE -> semantic FALSE: PASS")
    print("UNKNOWN candidate -> semantic UNKNOWN: PASS")
    print("Candidate conflict -> semantic UNKNOWN: PASS")
    print("Actual historical profile remains UNKNOWN-safe: PASS")
    print("SITE / Rule Engine / production / runtime / API mutation blocked: PASS")
    print(f"Classification: {TERMINAL_CLASSIFICATION}")


if __name__ == "__main__":
    main()
