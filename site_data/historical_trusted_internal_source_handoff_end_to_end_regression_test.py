"""STEP74 trusted historical handoff end-to-end regression.

Reconciled with provenance-bound SITE applicability admission and the current
FALSE-only historical SITE decision eligibility contract.
"""
from __future__ import annotations

import copy
from dataclasses import replace
from unittest.mock import patch

import site_data.site_analysis_orchestrator as orchestrator
import law_data.rule_evaluation_pipeline as rule_pipeline

from law_data.historical_site_event_builder_injection_payload import BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME, CHANNEL, PROVENANCE, HistoricalSiteEventBuilderInjectionPayload
from law_data.historical_site_event_parcel_applicability_evidence import HistoricalSiteEventParcelEvidenceInput
from law_data.historical_site_event_site_applicability_admission import admit_historical_site_event_site_applicability
from law_data.historical_trusted_internal_source_authorization import authorize_historical_trusted_internal_source
from law_data.historical_trusted_internal_source_handoff_authorization import authorize_historical_trusted_internal_source_handoff
from law_data.regulation_resolution_profile_resolver_family_input_admission import HISTORICAL_SITE_EVENT
from law_data.regulation_resolution_profile_site_decision_eligibility import ELIGIBLE, RegulationResolutionProfileSiteDecisionEligibility

CONDITION = "STEP74_HISTORICAL_TEST"
PNU = "1168010300100120000"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


class FakeSite:
    site_id = "11680-10300-0012-0000"
    address = "STEP74 TEST"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "0012"
    ji = "0000"
    land = None


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
        historical_rules=({"condition": CONDITION, "state": "UNKNOWN"},),
        historical_repairs=({
            "condition": CONDITION,
            "before": "UNKNOWN",
            "after": "FALSE",
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
        event_identity="STEP74-HISTORICAL-EVENT",
        official_source_verified=True,
        parcel_binding_verified=parcel_binding_verified,
        event_binding_verified=True,
    )
    return admit_historical_site_event_site_applicability(
        eligibility,
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )


def fake_fetch(**kwargs):
    return {"items": [{"test": True}], "total_count": 1, "result_code": "00", "result_message": "OK"}


def fake_spatial_payload(*, site):
    return {"parcel": {"area": {"value": None}, "source": {"live": {}}}}


def run(*, handoff=None, applicability=None):
    captured = {}
    original_response_builder = orchestrator.build_site_analysis_response
    original_apply_site_registry = rule_pipeline.apply_site_registry

    def capture_apply_site_registry(*, rules, site_registry):
        captured.setdefault("consumed_registries", []).append(copy.deepcopy(site_registry))
        return original_apply_site_registry(rules=rules, site_registry=site_registry)

    def capture_response(analysis, include_debug=False):
        captured["analysis"] = copy.deepcopy(analysis)
        return original_response_builder(analysis, include_debug=include_debug)

    with (
        patch.object(orchestrator, "fetch_building_items", fake_fetch),
        patch.object(orchestrator, "create_site", lambda items: FakeSite()),
        patch("law_data.site_analysis_builder.resolve_site_spatial_payload", fake_spatial_payload),
        patch("law_data.site_analysis_builder.get_supported_spatial_conditions", lambda: []),
        patch.object(orchestrator, "build_site_analysis_response", capture_response),
        patch.object(rule_pipeline, "apply_site_registry", capture_apply_site_registry),
    ):
        response = orchestrator.analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            historical_handoff_authorization=handoff,
            historical_site_applicability_admission=applicability,
        )

    return response, captured.get("analysis", {}), captured.get("consumed_registries", [])


def expect_rejected(*, handoff=None, applicability=None):
    try:
        run(handoff=handoff, applicability=applicability)
    except orchestrator.SiteAnalysisError:
        return True
    return False


def main():
    print("=" * 72)
    print("STEP 74 HISTORICAL TRUSTED INTERNAL SOURCE HANDOFF END-TO-END REGRESSION")
    print("=" * 72)

    legacy, legacy_raw, legacy_consumed = run()
    check("Legacy no-historical path completes", isinstance(legacy, dict))
    check("Legacy path has no historical input", "historical" not in legacy_raw.get("input", {}))

    handoff = valid_handoff()
    applicability = valid_applicability()
    original_handoff = copy.deepcopy(handoff)
    original_applicability = copy.deepcopy(applicability)
    _, raw_analysis, consumed = run(handoff=handoff, applicability=applicability)

    historical_input = raw_analysis.get("input", {}).get("historical")
    check("PNU-admitted trusted handoff reaches builder", isinstance(historical_input, dict))
    check("Historical channel reaches builder intact", historical_input.get("channel") == CHANNEL)
    check("Historical provenance reaches builder intact", historical_input.get("provenance") == PROVENANCE)
    repairs = historical_input.get("repairs")
    check(
        "Historical repairs reach builder intact",
        isinstance(repairs, list) and len(repairs) == 1
        and repairs[0].get("condition") == CONDITION
        and repairs[0].get("after") == "FALSE"
        and repairs[0].get("new_source") == PROVENANCE,
    )

    registry = raw_analysis.get("rule_engine", {}).get("site_registry", {})
    check("Legacy Rule Engine consumption remains spatial-only", len(legacy_consumed) == 1 and CONDITION not in legacy_consumed[0])
    check("Historical path performs two Rule Engine consumptions", len(consumed) == 2)
    historical_registry = consumed[-1].get(CONDITION) if consumed else None
    check("Historical condition consumed by Rule Engine", isinstance(historical_registry, dict))
    check("Historical condition state applied", historical_registry.get("state") == "FALSE")
    check("Historical provenance preserved", historical_registry.get("source") == PROVENANCE)
    check("Historical condition excluded from returned spatial registry", CONDITION not in registry)
    runtime_conditions = raw_analysis.get("site", {}).get("runtime_conditions", {})
    check("Historical condition excluded from spatial runtime", CONDITION not in runtime_conditions)
    check("Caller handoff remains immutable", handoff == original_handoff)
    check("Caller applicability remains immutable", applicability == original_applicability)

    check("Handoff without SITE applicability rejected", expect_rejected(handoff=handoff))
    check("SITE applicability without handoff rejected", expect_rejected(applicability=applicability))
    check(
        "UNKNOWN parcel applicability rejected",
        expect_rejected(handoff=handoff, applicability=valid_applicability(parcel_binding_verified=False)),
    )
    check(
        "Unauthorized trusted handoff rejected",
        expect_rejected(handoff=replace(handoff, handoff_authorized=False), applicability=applicability),
    )

    print("Trusted historical E2E path: PNU ADMISSION -> ORCHESTRATOR -> SERVICE -> BUILDER -> RULE ENGINE")
    print("Historical spatial runtime registration: NONE")
    print("Public API historical exposure: NONE")
    print("Real-condition activation: NONE")
    print(
        "CLASSIFICATION: "
        "STEP74_HISTORICAL_TRUSTED_INTERNAL_SOURCE_"
        "HANDOFF_END_TO_END_REGRESSION_BOUNDARY_RECONCILED"
    )


if __name__ == "__main__":
    main()
