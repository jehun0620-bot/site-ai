"""Contract test for single-lane promotion bridge wiring in the orchestrator."""
from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME,
    READY,
    HistoricalSiteEventSiteTruthPromotionRuleInputBridge,
)
from law_data.historical_verified_rule_input_envelope import (
    HistoricalVerifiedRuleInputEnvelope,
)
from site_data.site_analysis_orchestrator import SiteAnalysisError, analyze_site_by_parcel

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"
RULE_INPUT = {
    "channel": CHANNEL,
    "provenance": PROVENANCE,
    "repairs": [{
        "condition": CONDITION,
        "after": "FALSE",
        "new_confidence": "HIGH",
        "new_source": PROVENANCE,
        "pnu": PNU,
    }],
}


def ready_bridge():
    return HistoricalSiteEventSiteTruthPromotionRuleInputBridge(
        boundary=BOUNDARY_NAME,
        status=READY,
        execution_present=True,
        execution_boundary_matched=True,
        execution_succeeded=True,
        pnu_valid=True,
        condition_present=True,
        state_valid=True,
        promoted_condition_aligned=True,
        provenance_preserved=True,
        missing_gates=(),
        bridge_ready=True,
        historical_rule_input=RULE_INPUT,
    )


def run(bridge, *, legacy=False):
    captured = {}
    fake_site = object()

    def fake_analyze_site_object(**kwargs):
        captured["historical_rule_input"] = kwargs.get("historical_rule_input")
        return {"ok": True}

    with patch("site_data.site_analysis_orchestrator.fetch_building_items", return_value={
        "items": [{"x": 1}], "total_count": 1, "result_code": "00"
    }), patch("site_data.site_analysis_orchestrator.create_site", return_value=fake_site), patch(
        "site_data.site_analysis_orchestrator._actual_site_pnu", return_value=PNU
    ), patch(
        "site_data.site_analysis_orchestrator.analyze_site_object", side_effect=fake_analyze_site_object
    ), patch(
        "site_data.site_analysis_orchestrator.build_site_analysis_response", return_value={"ok": True}
    ):
        kwargs = {}
        if legacy:
            kwargs["historical_handoff_authorization"] = object()
        result = analyze_site_by_parcel(
            sigungu_cd="11680", bjdong_cd="10300", bun="0012", ji="0000",
            historical_promotion_rule_input_bridge=bridge,
            **kwargs,
        )
    return result, captured


def main():
    bridge = ready_bridge()
    assert bridge.ready

    result, captured = run(bridge)
    assert result["ok"] is True
    envelope = captured["historical_rule_input"]
    assert isinstance(envelope, HistoricalVerifiedRuleInputEnvelope)
    assert envelope.ready
    assert envelope.canonical_pnu == PNU
    assert envelope.historical_rule_input == RULE_INPUT
    assert envelope.historical_rule_input is not RULE_INPUT

    try:
        run(replace(bridge, bridge_ready=False))
        raise AssertionError("not-ready bridge must fail closed")
    except SiteAnalysisError as exc:
        assert "bridge is not ready" in str(exc)

    wrong_pnu_input = {
        **RULE_INPUT,
        "repairs": [{**RULE_INPUT["repairs"][0], "pnu": "1168010300100130000"}],
    }
    try:
        run(replace(bridge, historical_rule_input=wrong_pnu_input))
        raise AssertionError("cross-PNU promotion input must fail closed")
    except SiteAnalysisError as exc:
        assert "PNU rebinding failed" in str(exc)

    try:
        run(bridge, legacy=True)
        raise AssertionError("legacy and promotion paths together must fail closed")
    except SiteAnalysisError as exc:
        assert "ambiguous" in str(exc)

    print("SITE_ANALYSIS_ORCHESTRATOR_PROMOTION_RULE_INPUT_WIRING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
