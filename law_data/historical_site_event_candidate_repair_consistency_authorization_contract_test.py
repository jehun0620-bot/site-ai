from __future__ import annotations

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_candidate_repair_consistency_authorization import (
    AUTHORIZED,
    REJECTED,
    authorize_historical_site_event_candidate_repair_consistency,
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


def _eligibility():
    value = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    assert value.eligible
    return value


def _applicability():
    evidence = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-HISTORICAL-CANDIDATE-REPAIR-CONSISTENCY",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    result = admit_historical_site_event_site_applicability(
        _eligibility(),
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )
    assert result.admitted
    assert result.candidate_site_decision is False
    return result


def _handoff(*states: str, authorized: bool = True):
    repairs = tuple(
        {
            "condition": f"TEST_CONDITION_{index}",
            "after": state,
            "new_confidence": "HIGH",
            "new_source": PROVENANCE,
        }
        for index, state in enumerate(states, start=1)
    )
    return HistoricalTrustedInternalSourceHandoffAuthorization(
        boundary=HANDOFF_BOUNDARY_NAME,
        source_authorization_present=True,
        source_authorization_boundary_matched=True,
        trusted_source_authorized=authorized,
        channel_matched=True,
        provenance_matched=True,
        rules_present=True,
        repairs_present=True,
        repair_provenance_preserved=True,
        missing_gates=() if authorized else ("trusted_source_authorized",),
        handoff_authorized=authorized,
        channel=CHANNEL if authorized else "",
        provenance=PROVENANCE if authorized else "",
        handoff_rules=(),
        handoff_repairs=repairs if authorized else (),
    )


def main() -> None:
    applicability = _applicability()

    matching = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff("FALSE"),
    )
    assert matching.status == AUTHORIZED
    assert matching.authorized
    assert matching.expected_state == "FALSE"
    assert matching.matching_repair_count == 1
    assert matching.contradictory_repair_count == 0
    assert len(matching.authorized_repairs) == 1
    assert matching.site_truth_decision_allowed is False
    assert matching.site_promotion_allowed is False
    assert matching.production_registration_allowed is False
    assert matching.runtime_registration_allowed is False

    contradictory = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff("TRUE"),
    )
    assert contradictory.status == REJECTED
    assert not contradictory.authorized
    assert contradictory.matching_repair_count == 0
    assert contradictory.contradictory_repair_count == 1
    assert "candidate_matching_repair_present" in contradictory.missing_gates
    assert "no_candidate_contradictory_repairs" in contradictory.missing_gates
    assert contradictory.authorized_repairs == ()

    mixed = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff("FALSE", "TRUE"),
    )
    assert mixed.status == REJECTED
    assert not mixed.authorized
    assert mixed.matching_repair_count == 1
    assert mixed.contradictory_repair_count == 1
    assert "no_candidate_contradictory_repairs" in mixed.missing_gates

    unknown_repair = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff("UNKNOWN"),
    )
    assert unknown_repair.status == REJECTED
    assert not unknown_repair.authorized

    empty = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff(),
    )
    assert empty.status == REJECTED
    assert not empty.authorized
    assert "repairs_present" in empty.missing_gates

    unauthorized = authorize_historical_site_event_candidate_repair_consistency(
        applicability,
        _handoff("FALSE", authorized=False),
    )
    assert unauthorized.status == REJECTED
    assert not unauthorized.authorized
    assert "handoff_authorized" in unauthorized.missing_gates

    print("HISTORICAL_SITE_EVENT_CANDIDATE_REPAIR_CONSISTENCY_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
