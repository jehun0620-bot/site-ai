"""End-to-end regression for district-unit verified SITE truth transport.

External building/spatial I/O is deterministic. The production path from
orchestrator -> service -> builder -> collision policy -> common verified
registry -> existing Rule Engine remains real.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from law_data.district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from law_data.district_unit_plan_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME as BRIDGE_BOUNDARY_NAME,
    CONDITION_NAME,
    READY,
    DistrictUnitPlanSiteTruthPromotionRuleInputBridge,
)
from law_data.district_unit_plan_verified_registry_candidate_envelope import (
    seal_verified_district_unit_plan_registry_candidate,
)
from site_data.site_analysis_orchestrator import (
    SiteAnalysisError,
    analyze_site_by_parcel,
)
from site_data.site_data_model import Site


PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def fake_site():
    return Site(
        site_id="11680-10300-0012-0000",
        address="????? ??? ??? 12??",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
    )


def candidate(pnu=PNU):
    return {
        CONDITION_NAME: {
            "state": "TRUE",
            "confidence": "HIGH",
            "source": REGISTRY_SOURCE,
            "pnu": pnu,
            "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
        }
    }


def ready_bridge():
    return DistrictUnitPlanSiteTruthPromotionRuleInputBridge(
        boundary=BRIDGE_BOUNDARY_NAME,
        status=READY,
        execution_present=True,
        execution_boundary_matched=True,
        execution_succeeded=True,
        pnu_valid=True,
        condition_matched=True,
        state_true=True,
        promoted_condition_aligned=True,
        provenance_preserved=True,
        missing_gates=(),
        bridge_ready=True,
        canonical_pnu=PNU,
        registry_candidate=candidate(),
    )


def envelope():
    return seal_verified_district_unit_plan_registry_candidate(ready_bridge())


def run_verified(verified):
    # Empty supported-spatial set gives the district candidate a clean
    # no-collision production path. Collision behavior itself is independently
    # covered by the dedicated Builder/collision contracts.
    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        return_value={
            "items": [{"x": 1}],
            "total_count": 1,
            "result_code": "00",
        },
    ), patch(
        "site_data.site_analysis_orchestrator.create_site",
        return_value=fake_site(),
    ), patch(
        "law_data.site_analysis_builder.resolve_site_spatial_payload",
        return_value={"parcel": {}},
    ), patch(
        "law_data.site_analysis_builder.get_supported_spatial_conditions",
        return_value=[],
    ):
        return analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            bun="0012",
            ji="0000",
            district_unit_plan_registry_candidate=verified,
            include_debug=True,
            service_key="TEST_KEY",
        )


def main():
    verified = envelope()
    check("Verified district-unit envelope ready", verified.ready)

    before = verified.to_dict()
    response = run_verified(verified)

    check(
        "Orchestrator building service preserved",
        response.get("service", {}).get("building_api_status") == "00",
    )

    debug = response.get("debug", {})

    district_input = debug.get("input", {}).get("district_unit_plan")
    check(
        "District-unit input reaches Builder through production path",
        district_input == candidate(),
    )

    registry = debug.get("rule_engine", {}).get("site_registry", {})
    check(
        "District-unit TRUE reaches existing Rule Engine",
        CONDITION_NAME in registry
        and registry[CONDITION_NAME].get("state") == "TRUE",
    )

    check(
        "District-unit provenance preserved",
        registry.get(CONDITION_NAME, {}).get("source") == REGISTRY_SOURCE
        and registry.get(CONDITION_NAME, {}).get("provenance")
        == "HYBRID_SPATIAL_NOTICE_VERIFIED",
    )

    check(
        "Caller district-unit envelope immutable end-to-end",
        verified.to_dict() == before,
    )

    wrong_pnu = replace(
        verified,
        canonical_pnu=OTHER_PNU,
    )

    cross_pnu_blocked = False
    try:
        run_verified(wrong_pnu)
    except SiteAnalysisError:
        cross_pnu_blocked = True

    check(
        "Cross-PNU district-unit envelope blocked by Orchestrator",
        cross_pnu_blocked,
    )

    raw_blocked = False
    try:
        run_verified(candidate())
    except SiteAnalysisError:
        raw_blocked = True

    check(
        "Raw district-unit Orchestrator injection blocked",
        raw_blocked,
    )

    # The Orchestrator must reject mixed historical/district production input
    # before either family can enter Service/Builder.
    simultaneous_blocked = False

    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        return_value={
            "items": [{"x": 1}],
            "total_count": 1,
            "result_code": "00",
        },
    ), patch(
        "site_data.site_analysis_orchestrator.create_site",
        return_value=fake_site(),
    ):
        try:
            analyze_site_by_parcel(
                sigungu_cd="11680",
                bjdong_cd="10300",
                bun="0012",
                ji="0000",
                historical_promotion_rule_input_bridge=object(),
                district_unit_plan_registry_candidate=verified,
                include_debug=True,
                service_key="TEST_KEY",
            )
        except SiteAnalysisError:
            simultaneous_blocked = True

    check(
        "Historical plus district-unit simultaneous Orchestrator input blocked",
        simultaneous_blocked,
    )

    print(
        "DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_END_TO_END_REGRESSION_PASS"
    )


if __name__ == "__main__":
    main()
