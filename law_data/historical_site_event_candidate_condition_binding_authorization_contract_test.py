from __future__ import annotations

from dataclasses import replace

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_candidate_condition_binding_authorization import (
    AUTHORIZED,
    REJECTED,
    authorize_historical_site_event_candidate_condition_binding,
)
from law_data.historical_site_event_parcel_applicability_evidence import (
    HistoricalSiteEventParcelEvidenceInput,
)
from law_data.historical_site_event_site_applicability_admission import (
    admit_historical_site_event_site_applicability,
)
from law_data.historical_trusted_internal_source_handoff_authorization import (
    BOUNDARY_NAME as HANDOFF_BOUNDARY_NAME,
    HistoricalTrustedInternalSourceHandoffAuthorization,
)
from law_data.regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
)
from law_data.regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"


def _applicability():
    eligibility = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    assert eligibility.eligible

    evidence = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-HISTORICAL-CONDITION-BINDING",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    result = admit_historical_site_event_site_applicability(
        eligibility,
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )
    assert result.admitted
    return result


def _handoff(*conditions):
    repairs = tuple(
        {
            "condition": condition,
            "after": "FALSE",
            "new_confidence": "HIGH",
            "new_source": PROVENANCE,
        }
        for condition in conditions
    )
    return HistoricalTrustedInternalSourceHandoffAuthorization(
        boundary=HANDOFF_BOUNDARY_NAME,
        source_authorization_present=True,
        source_authorization_boundary_matched=True,
        trusted_source_authorized=True,
        channel_matched=True,
        provenance_matched=True,
        rules_present=True,
        repairs_present=True,
        repair_provenance_preserved=True,
        missing_gates=(),
        handoff_authorized=True,
        channel=CHANNEL,
        provenance=PROVENANCE,
        handoff_rules=(),
        handoff_repairs=repairs,
    )


def main() -> None:
    applicability = _applicability()

    single = authorize_historical_site_event_candidate_condition_binding(
        applicability,
        _handoff("HISTORICAL_CONDITION_A"),
    )
    assert single.status == AUTHORIZED
    assert single.authorized
    assert single.bound_condition == "HISTORICAL_CONDITION_A"
    assert single.unique_condition_count == 1

    repeated = authorize_historical_site_event_candidate_condition_binding(
        applicability,
        _handoff("HISTORICAL_CONDITION_A", "HISTORICAL_CONDITION_A"),
    )
    assert repeated.authorized
    assert repeated.bound_condition == "HISTORICAL_CONDITION_A"
    assert repeated.unique_condition_count == 1

    mixed = authorize_historical_site_event_candidate_condition_binding(
        applicability,
        _handoff("HISTORICAL_CONDITION_A", "HISTORICAL_CONDITION_B"),
    )
    assert mixed.status == REJECTED
    assert not mixed.authorized
    assert mixed.unique_condition_count == 2
    assert "condition_identity_unambiguous" in mixed.missing_gates

    blank = authorize_historical_site_event_candidate_condition_binding(
        applicability,
        _handoff(""),
    )
    assert blank.status == REJECTED
    assert not blank.authorized
    assert "repair_conditions_valid" in blank.missing_gates

    unauthorized = authorize_historical_site_event_candidate_condition_binding(
        applicability,
        replace(_handoff("HISTORICAL_CONDITION_A"), handoff_authorized=False),
    )
    assert unauthorized.status == REJECTED
    assert not unauthorized.authorized
    assert "handoff_authorized" in unauthorized.missing_gates

    assert single.site_truth_decision_allowed is False
    assert single.site_promotion_allowed is False
    assert single.production_readiness_allowed is False
    assert single.production_registration_allowed is False
    assert single.runtime_registration_allowed is False

    print("HISTORICAL_SITE_EVENT_CANDIDATE_CONDITION_BINDING_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
