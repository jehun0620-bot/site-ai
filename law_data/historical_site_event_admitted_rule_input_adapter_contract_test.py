from __future__ import annotations

from dataclasses import replace

from .historical_site_event_admitted_rule_input_adapter import (
    READY,
    REJECTED,
    UNKNOWN,
    adapt_admitted_historical_site_event_rule_input,
)
from .historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from .historical_site_event_parcel_applicability_evidence import (
    HistoricalSiteEventParcelEvidenceInput,
)
from .historical_site_event_site_applicability_admission import (
    admit_historical_site_event_site_applicability,
)
from .historical_trusted_internal_source_handoff_authorization import (
    BOUNDARY_NAME as HANDOFF_BOUNDARY_NAME,
    HistoricalTrustedInternalSourceHandoffAuthorization,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


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


def _site():
    return {"pnu": PNU, "identity_status": "COMPLETE"}


def _evidence(**changes):
    value = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-HISTORICAL-EVENT-1",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    return replace(value, **changes)


def _applicability(**evidence_changes):
    return admit_historical_site_event_site_applicability(
        _eligibility(),
        _site(),
        _evidence(**evidence_changes),
    )


def _handoff(**changes):
    repair = {
        "condition": "TEST_CONDITION",
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": PROVENANCE,
    }
    value = HistoricalTrustedInternalSourceHandoffAuthorization(
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
        handoff_repairs=(repair,),
    )
    return replace(value, **changes)


def main() -> None:
    ready = adapt_admitted_historical_site_event_rule_input(
        _applicability(),
        _handoff(),
    )
    assert ready.status == READY
    assert ready.ready is True
    assert ready.historical_rule_input == {
        "channel": CHANNEL,
        "provenance": PROVENANCE,
        "repairs": [
            {
                "condition": "TEST_CONDITION",
                "after": "FALSE",
                "new_confidence": "HIGH",
                "new_source": PROVENANCE,
            }
        ],
    }

    cross_pnu = adapt_admitted_historical_site_event_rule_input(
        _applicability(evidence_pnu=OTHER_PNU),
        _handoff(),
    )
    assert cross_pnu.status == REJECTED
    assert cross_pnu.ready is False
    assert cross_pnu.historical_rule_input is None

    unknown = adapt_admitted_historical_site_event_rule_input(
        _applicability(parcel_binding_verified=False),
        _handoff(),
    )
    assert unknown.status == UNKNOWN
    assert unknown.ready is False
    assert unknown.historical_rule_input is None

    unauthorized = adapt_admitted_historical_site_event_rule_input(
        _applicability(),
        _handoff(handoff_authorized=False),
    )
    assert unauthorized.status == REJECTED
    assert unauthorized.ready is False
    assert unauthorized.historical_rule_input is None

    wrong_channel = adapt_admitted_historical_site_event_rule_input(
        _applicability(),
        _handoff(channel="WRONG"),
    )
    assert wrong_channel.status == REJECTED
    assert wrong_channel.ready is False

    bad_repair = {
        "condition": "TEST_CONDITION",
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": "WRONG_SOURCE",
    }
    bad_repairs = adapt_admitted_historical_site_event_rule_input(
        _applicability(),
        _handoff(handoff_repairs=(bad_repair,)),
    )
    assert bad_repairs.status == REJECTED
    assert bad_repairs.ready is False
    assert bad_repairs.historical_rule_input is None

    missing_handoff = adapt_admitted_historical_site_event_rule_input(
        _applicability(),
        None,
    )
    assert missing_handoff.status == REJECTED
    assert missing_handoff.ready is False

    for result in (
        ready,
        cross_pnu,
        unknown,
        unauthorized,
        wrong_channel,
        bad_repairs,
        missing_handoff,
    ):
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("HISTORICAL_SITE_EVENT_ADMITTED_RULE_INPUT_ADAPTER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
