"""End-to-end regression for the promotion lane through builder and Rule Engine.

This test keeps external building/spatial I/O deterministic, but does not mock
the orchestrator -> service -> builder -> historical registry adapter ->
collision policy -> Rule Engine handoff. The promoted FALSE fact must appear in
the final Rule Engine SITE registry with historical provenance.
"""
from __future__ import annotations

from unittest.mock import patch

from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME,
    READY,
    HistoricalSiteEventSiteTruthPromotionRuleInputBridge,
)
from site_data.site_analysis_orchestrator import analyze_site_by_parcel
from site_data.site_data_model import Site

PNU = "1168010300100120000"
CONDITION = "TEST_HISTORICAL_CONDITION"
RULE_INPUT = {
    "channel": CHANNEL,
    "provenance": PROVENANCE,
    "repairs": [
        {
            "condition": CONDITION,
            "after": "FALSE",
            "new_confidence": "HIGH",
            "new_source": PROVENANCE,
            "pnu": PNU,
        }
    ],
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


def fake_site():
    return Site(
        site_id="11680-10300-0012-0000",
        address="서울특별시 강남구 개포동 12번지",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
    )


def main():
    bridge = ready_bridge()
    assert bridge.ready

    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        return_value={"items": [{"x": 1}], "total_count": 1, "result_code": "00"},
    ), patch(
        "site_data.site_analysis_orchestrator.create_site", return_value=fake_site()
    ), patch(
        "law_data.site_analysis_builder.resolve_site_spatial_payload",
        return_value={"parcel": {}},
    ), patch(
        "law_data.site_analysis_builder.get_supported_spatial_conditions",
        return_value=[],
    ):
        response = analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            historical_promotion_rule_input_bridge=bridge,
            include_debug=True,
            service_key="TEST_KEY",
        )

    assert response["service"]["building_api_status"] == "00"

    # Debug response must retain the one historical input that entered builder.
    historical_input = response.get("input", {}).get("historical")
    assert historical_input == RULE_INPUT

    # Most importantly, the existing Rule Engine SITE registry must consume it.
    registry = response.get("rule_engine", {}).get("site_registry", {})
    assert CONDITION in registry
    assert registry[CONDITION]["state"] == "FALSE"
    assert registry[CONDITION]["confidence"] == "HIGH"
    assert registry[CONDITION]["source"] == PROVENANCE

    print("HISTORICAL_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS")


if __name__ == "__main__":
    main()
