"""Terminal audit for STEP28 historical negative-evidence eligibility."""

from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofEvidence,
    evaluate_historical_site_event_exhaustive_disproof,
)
from law_data.historical_site_event_negative_evidence_eligibility import (
    BOUNDARY_NAME,
    evaluate_historical_site_event_negative_evidence_eligibility,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile
from law_data.regulation_resolution_profile_registry import (
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)


TERMINAL_CLASSIFICATION = (
    "STEP28_HISTORICAL_SITE_EVENT_NEGATIVE_EVIDENCE_ELIGIBILITY_"
    "BOUNDARY_TERMINALLY_RECONCILED"
)


def _historical_profile(*, negative_evidence_allowed: object) -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name="STEP28_SYNTHETIC_HISTORICAL_PROFILE",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=negative_evidence_allowed,  # type: ignore[arg-type]
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
    verified_disproof = _verified_disproof()
    assert verified_disproof.exhaustive_disproof_verified is True

    # STEP27 verification alone is not enough without explicit profile permission.
    blocked_profile = _historical_profile(negative_evidence_allowed=False)
    blocked = evaluate_historical_site_event_negative_evidence_eligibility(
        blocked_profile,
        verified_disproof,
    )
    assert blocked.negative_evidence_eligible is False
    assert "negative_evidence_allowed" in blocked.missing_gates

    # Profile permission alone is not enough without a verified STEP27 assessment.
    allowed_profile = _historical_profile(negative_evidence_allowed=True)
    no_disproof = evaluate_historical_site_event_negative_evidence_eligibility(
        allowed_profile,
        None,
    )
    assert no_disproof.negative_evidence_eligible is False
    assert "exhaustive_disproof_assessment_present" in no_disproof.missing_gates
    assert "exhaustive_disproof_verified" in no_disproof.missing_gates

    incomplete_disproof = replace(
        verified_disproof,
        exhaustive_disproof_verified=False,
    )
    incomplete = evaluate_historical_site_event_negative_evidence_eligibility(
        allowed_profile,
        incomplete_disproof,
    )
    assert incomplete.negative_evidence_eligible is False

    # Wrong resolution/condition semantics fail closed even with permission/evidence.
    wrong_resolution = RegulationResolutionProfile(
        name="STEP28_WRONG_RESOLUTION",
        condition_type="SITE_HISTORY",
        resolution_type="SNAPSHOT",
        negative_evidence_allowed=True,
    )
    assert (
        evaluate_historical_site_event_negative_evidence_eligibility(
            wrong_resolution,
            verified_disproof,
        ).negative_evidence_eligible
        is False
    )

    wrong_condition = RegulationResolutionProfile(
        name="STEP28_WRONG_CONDITION",
        condition_type="SITE",
        resolution_type="HISTORICAL_SITE_EVENT",
        negative_evidence_allowed=True,
    )
    assert (
        evaluate_historical_site_event_negative_evidence_eligibility(
            wrong_condition,
            verified_disproof,
        ).negative_evidence_eligible
        is False
    )

    # Truthy non-booleans do not become explicit permission or verified evidence.
    truthy_profile = _historical_profile(negative_evidence_allowed=1)
    assert (
        evaluate_historical_site_event_negative_evidence_eligibility(
            truthy_profile,
            verified_disproof,
        ).negative_evidence_eligible
        is False
    )

    truthy_disproof = replace(
        verified_disproof,
        exhaustive_disproof_verified=1,  # type: ignore[arg-type]
    )
    assert (
        evaluate_historical_site_event_negative_evidence_eligibility(
            allowed_profile,
            truthy_disproof,
        ).negative_evidence_eligible
        is False
    )

    # Only all explicit gates produce eligibility; this still is not FALSE.
    eligible = evaluate_historical_site_event_negative_evidence_eligibility(
        allowed_profile,
        verified_disproof,
    )
    assert eligible.boundary == BOUNDARY_NAME
    assert eligible.negative_evidence_eligible is True
    assert eligible.missing_gates == ()
    assert eligible.legal_absence_inference_allowed is False

    payload = eligible.to_dict()
    assert payload["negative_evidence_eligible"] is True
    assert payload["false_candidate_generated"] is False
    assert payload["negative_resolution_generated"] is False
    assert payload["legal_absence_inference_performed"] is False
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False

    # The actual built-in historical profile remains blocked and therefore UNKNOWN-safe.
    actual_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    assert actual_profile is not None
    assert actual_profile.negative_evidence_allowed is False
    assert actual_profile.legal_absence_inference_allowed is False
    assert actual_profile.site_promotion_allowed is False
    assert actual_profile.production_registration_allowed is False
    assert actual_profile.runtime_registration_allowed is False

    actual = evaluate_historical_site_event_negative_evidence_eligibility(
        actual_profile,
        verified_disproof,
    )
    assert actual.negative_evidence_eligible is False
    assert "negative_evidence_allowed" in actual.missing_gates

    print("=" * 60)
    print("STEP28 HISTORICAL SITE EVENT NEGATIVE EVIDENCE ELIGIBILITY")
    print("=" * 60)
    print("Synthetic all-gates eligibility: PASS")
    print("Actual historical profile remains blocked: PASS")
    print("FALSE / legal-absence / SITE / runtime promotion blocked: PASS")
    print(f"Classification: {TERMINAL_CLASSIFICATION}")


if __name__ == "__main__":
    main()
