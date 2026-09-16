from __future__ import annotations

from unittest.mock import patch

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
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
from site_data.site_analysis_orchestrator import SiteAnalysisError, analyze_site_by_parcel

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


class _Site:
    site_id = "11680-10300-0012-0000"
    address = "test"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "0012"
    ji = "0000"
    land = None


class _OtherSite:
    site_id = "11680-10300-0013-0000"
    address = "other"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "0013"
    ji = "0000"
    land = None


class _IncompleteSite:
    site_id = "incomplete"
    address = "incomplete"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "12"
    ji = "0"
    land = None


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
        event_identity="TEST-HISTORICAL-EVENT-PNU-REBINDING",
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
    return result


def _handoff():
    repair = {
        "condition": "TEST_CONDITION",
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": PROVENANCE,
    }
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
        handoff_repairs=(repair,),
    )


def _run(site):
    captured = {}

    def fake_analyze_site_object(**kwargs):
        captured.update(kwargs)
        return {"analysis": "ok"}

    with (
        patch(
            "site_data.site_analysis_orchestrator.fetch_building_items",
            return_value={
                "items": [{"x": 1}],
                "total_count": 1,
                "result_code": "00",
            },
        ),
        patch(
            "site_data.site_analysis_orchestrator.create_site",
            return_value=site,
        ),
        patch(
            "site_data.site_analysis_orchestrator.analyze_site_object",
            side_effect=fake_analyze_site_object,
        ),
        patch(
            "site_data.site_analysis_orchestrator.build_site_analysis_response",
            side_effect=lambda analysis, include_debug=False: dict(analysis),
        ),
    ):
        response = analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            historical_handoff_authorization=_handoff(),
            historical_site_applicability_admission=_applicability(),
            service_key="test",
        )
    return response, captured


def _must_fail(site):
    try:
        _run(site)
    except SiteAnalysisError:
        return
    raise AssertionError("historical path should reject an actual Site PNU mismatch")


def main() -> None:
    response, captured = _run(_Site())
    assert response["analysis"] == "ok"
    assert captured["historical_rule_input"] is not None
    assert captured["historical_rule_input"]["channel"] == CHANNEL
    assert captured["historical_rule_input"]["provenance"] == PROVENANCE

    # Admission says parcel 12, but the actual Site object says parcel 13.
    _must_fail(_OtherSite())

    # If the actual Site cannot produce a complete 19-digit PNU, fail closed.
    _must_fail(_IncompleteSite())

    print("SITE_ANALYSIS_ORCHESTRATOR_CANONICAL_PNU_REBINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
