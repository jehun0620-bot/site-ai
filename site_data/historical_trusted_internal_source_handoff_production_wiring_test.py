"""STEP73 trusted historical source handoff production wiring tests.

Reconciled so the historical production seam requires both the trusted handoff
and provenance-bound SITE applicability admission.
"""
from __future__ import annotations

import copy
from dataclasses import replace

import site_data.site_analysis_orchestrator as orchestrator

from law_data.historical_site_event_builder_injection_payload import (
    BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME,
    CHANNEL,
    PROVENANCE,
    HistoricalSiteEventBuilderInjectionPayload,
)
from law_data.historical_site_event_parcel_applicability_evidence import HistoricalSiteEventParcelEvidenceInput
from law_data.historical_site_event_site_applicability_admission import admit_historical_site_event_site_applicability
from law_data.historical_trusted_internal_source_authorization import authorize_historical_trusted_internal_source
from law_data.historical_trusted_internal_source_handoff_authorization import authorize_historical_trusted_internal_source_handoff
from law_data.regulation_resolution_profile_resolver_family_input_admission import HISTORICAL_SITE_EVENT
from law_data.regulation_resolution_profile_site_decision_eligibility import ELIGIBLE, RegulationResolutionProfileSiteDecisionEligibility

PNU = "1168010300100120000"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def valid_handoff():
    payload = HistoricalSiteEventBuilderInjectionPayload(
        boundary=PAYLOAD_BOUNDARY_NAME,
        authorization_present=True,
        authorization_boundary_matched=True,
        production_integration_authorized=True,
        channel=CHANNEL,
        provenance=PROVENANCE,
        rules_present=True,
        repairs_aligned=True,
        provenance_preserved=True,
        missing_gates=(),
        builder_injection_payload_ready=True,
        historical_rules=({"condition": "HISTORICAL_TEST", "state": "UNKNOWN"},),
        historical_repairs=({
            "condition": "HISTORICAL_TEST",
            "before": "UNKNOWN",
            "after": "TRUE",
            "new_confidence": "HIGH",
            "new_source": PROVENANCE,
        },),
    )
    return authorize_historical_trusted_internal_source_handoff(
        authorize_historical_trusted_internal_source(payload)
    )


def valid_applicability(*, parcel_binding_verified=True):
    eligibility = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    evidence = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="STEP73-HISTORICAL-EVENT",
        official_source_verified=True,
        parcel_binding_verified=parcel_binding_verified,
        event_binding_verified=True,
    )
    return admit_historical_site_event_site_applicability(
        eligibility,
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )


def run_orchestrator(*, handoff=None, applicability=None):
    captured = {}
    original_fetch = orchestrator.fetch_building_items
    original_create = orchestrator.create_site
    original_analyze = orchestrator.analyze_site_object
    original_response = orchestrator.build_site_analysis_response
    try:
        orchestrator.fetch_building_items = lambda **kwargs: {
            "items": [{"test": True}], "total_count": 1, "result_code": "00", "result_message": "OK"
        }
        orchestrator.create_site = lambda items: object()
        orchestrator.analyze_site_object = lambda **kwargs: captured.update(kwargs) or {"analysis": True}
        orchestrator.build_site_analysis_response = lambda analysis, include_debug=False: {
            "analysis": analysis, "include_debug": include_debug
        }
        return orchestrator.analyze_site_by_parcel(
            sigungu_cd="11680", bjdong_cd="10300", bun="0012", ji="0000",
            historical_handoff_authorization=handoff,
            historical_site_applicability_admission=applicability,
        ), captured
    finally:
        orchestrator.fetch_building_items = original_fetch
        orchestrator.create_site = original_create
        orchestrator.analyze_site_object = original_analyze
        orchestrator.build_site_analysis_response = original_response


def expect_rejected(*, handoff=None, applicability=None):
    try:
        run_orchestrator(handoff=handoff, applicability=applicability)
    except orchestrator.SiteAnalysisError:
        return True
    return False


def main():
    print("=" * 72)
    print("STEP 73 HISTORICAL TRUSTED INTERNAL SOURCE HANDOFF PRODUCTION WIRING")
    print("=" * 72)

    _, legacy = run_orchestrator()
    check("Legacy no-historical path preserved", legacy.get("historical_rule_input") is None)

    handoff = valid_handoff()
    applicability = valid_applicability()
    original_handoff = copy.deepcopy(handoff)
    original_applicability = copy.deepcopy(applicability)
    _, captured = run_orchestrator(handoff=handoff, applicability=applicability)
    historical = captured.get("historical_rule_input")

    check("PNU-admitted trusted handoff reaches service seam", isinstance(historical, dict))
    check("Historical channel preserved", historical.get("channel") == CHANNEL)
    check("Historical provenance preserved", historical.get("provenance") == PROVENANCE)
    check("Historical repairs preserved", historical.get("repairs") == list(handoff.handoff_repairs))
    check("Caller handoff remains immutable", handoff == original_handoff)
    check("Caller applicability remains immutable", applicability == original_applicability)

    check("Handoff without applicability rejected", expect_rejected(handoff=handoff))
    check("Applicability without handoff rejected", expect_rejected(applicability=applicability))
    check(
        "UNKNOWN parcel applicability rejected",
        expect_rejected(handoff=handoff, applicability=valid_applicability(parcel_binding_verified=False)),
    )
    check(
        "Unauthorized handoff rejected",
        expect_rejected(handoff=replace(handoff, handoff_authorized=False), applicability=applicability),
    )

    print("Raw historical orchestrator injection: REMOVED")
    print("Typed trusted handoff + PNU applicability wiring: ACTIVE")
    print("Service / builder / Rule Engine wiring mutation: NONE")
    print("Public API exposure / spatial runtime registration: NONE")
    print(
        "CLASSIFICATION: "
        "STEP73_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "HANDOFF_PRODUCTION_WIRING_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
