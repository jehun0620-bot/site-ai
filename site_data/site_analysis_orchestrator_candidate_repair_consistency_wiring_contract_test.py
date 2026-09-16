from __future__ import annotations

from dataclasses import replace
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


class _Site:
    site_id = "11680-10300-0012-0000"
    address = "test"
    road_address = ""
    sigungu_cd = "11680"
    bjdong_cd = "10300"
    bun = "0012"
    ji = "0000"
    land = None


def _eligibility(candidate=False):
    resolution = "TRUE" if candidate else "FALSE"
    value = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution=resolution,
        candidate_site_decision=candidate,
        conclusive_for_site_decision=True,
    )
    assert value.eligible
    return value


def _applicability(candidate=False):
    evidence = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-HISTORICAL-EVENT-CONSISTENCY",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    result = admit_historical_site_event_site_applicability(
        _eligibility(candidate),
        {"pnu": PNU, "identity_status": "COMPLETE"},
        evidence,
    )
    assert result.admitted
    return result


def _handoff(*states):
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


def _run(*, handoff, applicability):
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
            return_value=_Site(),
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
            historical_handoff_authorization=handoff,
            historical_site_applicability_admission=applicability,
            service_key="test",
        )
    return response, captured


def _must_fail(*, handoff, applicability):
    try:
        _run(handoff=handoff, applicability=applicability)
    except SiteAnalysisError as exc:
        assert "candidate/repair consistency failed" in str(exc)
        return
    raise AssertionError("candidate/repair inconsistency should fail closed")


def main() -> None:
    response, captured = _run(
        handoff=_handoff("FALSE"),
        applicability=_applicability(False),
    )
    assert response["analysis"] == "ok"
    assert captured["historical_rule_input"]["repairs"][0]["after"] == "FALSE"

    response_true, captured_true = _run(
        handoff=_handoff("TRUE"),
        applicability=_applicability(True),
    )
    assert response_true["analysis"] == "ok"
    assert captured_true["historical_rule_input"]["repairs"][0]["after"] == "TRUE"

    _must_fail(
        handoff=_handoff("TRUE"),
        applicability=_applicability(False),
    )
    _must_fail(
        handoff=_handoff("FALSE"),
        applicability=_applicability(True),
    )
    _must_fail(
        handoff=_handoff("FALSE", "TRUE"),
        applicability=_applicability(False),
    )
    _must_fail(
        handoff=replace(_handoff("FALSE"), handoff_authorized=False),
        applicability=_applicability(False),
    )

    print(
        "SITE_ANALYSIS_ORCHESTRATOR_"
        "CANDIDATE_REPAIR_CONSISTENCY_WIRING_CONTRACT_PASS"
    )


if __name__ == "__main__":
    main()
