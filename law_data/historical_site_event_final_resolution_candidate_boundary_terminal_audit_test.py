"""Terminal audit for STEP30 historical final-resolution candidate boundary."""

from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_final_resolution_candidate import (
    FALSE_CANDIDATE,
    TRUE_CANDIDATE,
    UNKNOWN,
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
    "STEP30_HISTORICAL_SITE_EVENT_FINAL_RESOLUTION_CANDIDATE_"
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
        boundary="STEP30_SYNTHETIC_POSITIVE",
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
    profile = _profile("STEP30_SYNTHETIC_PROFILE")
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

    positive_only = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_true, negative_unknown
    )
    assert positive_only.final_resolution_candidate == TRUE_CANDIDATE
    assert positive_only.conflict_detected is False

    negative_only = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_unknown, negative_false
    )
    assert negative_only.final_resolution_candidate == FALSE_CANDIDATE
    assert negative_only.conflict_detected is False

    neither = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_unknown, negative_unknown
    )
    assert neither.final_resolution_candidate == UNKNOWN
    assert neither.conflict_detected is False

    conflict = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_true, negative_false
    )
    assert conflict.final_resolution_candidate == UNKNOWN
    assert conflict.conflict_detected is True

    missing_positive = evaluate_historical_site_event_final_resolution_candidate(
        profile, None, negative_false
    )
    assert missing_positive.final_resolution_candidate == UNKNOWN

    missing_negative = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_true, None
    )
    assert missing_negative.final_resolution_candidate == UNKNOWN

    other_profile = _profile("STEP30_OTHER_PROFILE")
    mismatched = evaluate_historical_site_event_final_resolution_candidate(
        other_profile, positive_true, negative_false
    )
    assert mismatched.final_resolution_candidate == UNKNOWN
    assert "positive_profile_aligned" in mismatched.missing_gates
    assert "negative_profile_aligned" in mismatched.missing_gates

    invalid_positive = replace(positive_true, resolution_candidate="TRUE")
    invalid_positive_result = evaluate_historical_site_event_final_resolution_candidate(
        profile, invalid_positive, negative_unknown
    )
    assert invalid_positive_result.final_resolution_candidate == UNKNOWN

    invalid_negative = replace(negative_false, resolution_candidate="FALSE")
    invalid_negative_result = evaluate_historical_site_event_final_resolution_candidate(
        profile, positive_unknown, invalid_negative
    )
    assert invalid_negative_result.final_resolution_candidate == UNKNOWN

    payload = conflict.to_dict()
    assert payload["production_true_generated"] is False
    assert payload["production_false_generated"] is False
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
    actual = evaluate_historical_site_event_final_resolution_candidate(
        actual_profile, actual_positive, actual_negative
    )
    assert actual.final_resolution_candidate == UNKNOWN
    assert actual_profile.negative_evidence_allowed is False

    print("=" * 60)
    print("STEP30 HISTORICAL SITE EVENT FINAL RESOLUTION CANDIDATE")
    print("=" * 60)
    print("Positive-only candidate normalization: PASS")
    print("Negative-only candidate normalization: PASS")
    print("Positive/negative conflict -> UNKNOWN: PASS")
    print("Actual historical profile remains UNKNOWN-safe: PASS")
    print("Production TRUE/FALSE / SITE / runtime promotion blocked: PASS")
    print(f"Classification: {TERMINAL_CLASSIFICATION}")


if __name__ == "__main__":
    main()
