"""Terminal audit for STEP29 historical negative-resolution candidate boundary."""

from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofEvidence,
    evaluate_historical_site_event_exhaustive_disproof,
)
from law_data.historical_site_event_negative_evidence_eligibility import (
    evaluate_historical_site_event_negative_evidence_eligibility,
)
from law_data.historical_site_event_negative_resolution_candidate import (
    FALSE_CANDIDATE,
    UNKNOWN,
    evaluate_historical_site_event_negative_resolution_candidate,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_resolution_profile_registry import (
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)

TERMINAL_CLASSIFICATION = (
    "STEP29_HISTORICAL_SITE_EVENT_NEGATIVE_RESOLUTION_CANDIDATE_"
    "BOUNDARY_TERMINALLY_RECONCILED"
)


def _profile(name: str, allowed: object) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=name,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=allowed,  # type: ignore[arg-type]
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
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
    profile = _profile("STEP29_SYNTHETIC_HISTORICAL_PROFILE", True)
    disproof = _verified_disproof()
    eligibility = evaluate_historical_site_event_negative_evidence_eligibility(profile, disproof)
    assert disproof.exhaustive_disproof_verified is True
    assert eligibility.negative_evidence_eligible is True

    candidate = evaluate_historical_site_event_negative_resolution_candidate(
        profile, disproof, eligibility
    )
    assert candidate.negative_candidate_gate_satisfied is True
    assert candidate.resolution_candidate == FALSE_CANDIDATE

    payload = candidate.to_dict()
    assert payload["final_false_generated"] is False
    assert payload["legal_absence_inference_performed"] is False
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False

    assert evaluate_historical_site_event_negative_resolution_candidate(
        profile, disproof, None
    ).resolution_candidate == UNKNOWN

    assert evaluate_historical_site_event_negative_resolution_candidate(
        profile,
        disproof,
        replace(eligibility, negative_evidence_eligible=False),
    ).resolution_candidate == UNKNOWN

    assert evaluate_historical_site_event_negative_resolution_candidate(
        profile,
        replace(disproof, exhaustive_disproof_verified=False),
        eligibility,
    ).resolution_candidate == UNKNOWN

    assert evaluate_historical_site_event_negative_resolution_candidate(
        profile,
        disproof,
        replace(eligibility, negative_evidence_eligible=1),  # type: ignore[arg-type]
    ).resolution_candidate == UNKNOWN

    assert evaluate_historical_site_event_negative_resolution_candidate(
        profile,
        replace(disproof, exhaustive_disproof_verified=1),  # type: ignore[arg-type]
        eligibility,
    ).resolution_candidate == UNKNOWN

    other = _profile("STEP29_OTHER_PROFILE", True)
    mismatched = evaluate_historical_site_event_negative_resolution_candidate(
        other, disproof, eligibility
    )
    assert mismatched.resolution_candidate == UNKNOWN
    assert "eligibility_profile_aligned" in mismatched.missing_gates

    wrong_resolution = RegulationResolutionProfile(
        name="STEP29_WRONG_RESOLUTION",
        condition_type="SITE_HISTORY",
        resolution_type="SNAPSHOT",
        negative_evidence_allowed=True,
    )
    assert evaluate_historical_site_event_negative_resolution_candidate(
        wrong_resolution, disproof, eligibility
    ).resolution_candidate == UNKNOWN

    wrong_condition = RegulationResolutionProfile(
        name="STEP29_WRONG_CONDITION",
        condition_type="SITE",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=True,
    )
    assert evaluate_historical_site_event_negative_resolution_candidate(
        wrong_condition, disproof, eligibility
    ).resolution_candidate == UNKNOWN

    actual_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    assert actual_profile is not None
    assert actual_profile.negative_evidence_allowed is False

    actual_eligibility = evaluate_historical_site_event_negative_evidence_eligibility(
        actual_profile, disproof
    )
    assert actual_eligibility.negative_evidence_eligible is False

    actual_candidate = evaluate_historical_site_event_negative_resolution_candidate(
        actual_profile, disproof, actual_eligibility
    )
    assert actual_candidate.resolution_candidate == UNKNOWN

    print("=" * 60)
    print("STEP29 HISTORICAL SITE EVENT NEGATIVE RESOLUTION CANDIDATE")
    print("=" * 60)
    print("Synthetic FALSE_CANDIDATE composition: PASS")
    print("Actual historical profile remains UNKNOWN-safe: PASS")
    print("Final FALSE / SITE / runtime promotion blocked: PASS")
    print(f"Classification: {TERMINAL_CLASSIFICATION}")


if __name__ == "__main__":
    main()
