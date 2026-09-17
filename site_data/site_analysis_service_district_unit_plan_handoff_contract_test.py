"""Service handoff contract for verified district-unit registry input."""

from dataclasses import replace
from types import SimpleNamespace

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
from site_data.site_analysis_service import analyze_site_object

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


def site():
    return SimpleNamespace(
        site_id="11680-10300-0012-0000",
        address="????? ???",
        road_address="",
        sigungu_cd="11680",
        bjdong_cd="10300",
        bun="0012",
        ji="0000",
        land=None,
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


def bridge():
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
    return seal_verified_district_unit_plan_registry_candidate(bridge())


def main():
    legacy = analyze_site_object(site())
    check(
        "Legacy service path preserved",
        "district_unit_plan" not in legacy.get("input", {}),
    )

    raw_blocked = False
    try:
        analyze_site_object(
            site(),
            district_unit_plan_registry_candidate=candidate(),
        )
    except ValueError:
        raw_blocked = True
    check("Raw district-unit service injection blocked", raw_blocked)

    verified = envelope()
    before = verified.to_dict()

    # Service contract ends at the Builder handoff. Builder-side spatial
    # collision and Rule Engine consumption are covered by the dedicated
    # production handoff contract.
    import site_data.site_analysis_service as service_module

    original_builder = service_module.build_site_analysis
    captured = {}

    def builder_spy(**kwargs):
        captured.update(kwargs)
        return {
            "analysis": {"status": "TEST_SERVICE_HANDOFF"},
            "input": {
                "site": kwargs.get("site_input"),
            },
        }

    try:
        service_module.build_site_analysis = builder_spy
        integrated = analyze_site_object(
            site(),
            district_unit_plan_registry_candidate=verified,
        )
    finally:
        service_module.build_site_analysis = original_builder

    forwarded = captured.get("district_unit_plan_registry_candidate")

    check(
        "Verified district-unit Service-to-Builder handoff",
        forwarded is verified
        and forwarded.ready
        and forwarded.canonical_pnu == PNU,
    )

    check(
        "Service forwards current Site PNU",
        captured.get("site_input", {}).get("pnu") == PNU,
    )

    check(
        "Service does not reinterpret district-unit registry candidate",
        forwarded.registry_candidate == candidate(),
    )

    check(
        "Caller envelope immutable through Service",
        verified.to_dict() == before,
    )

    wrong_pnu = replace(
        verified,
        canonical_pnu=OTHER_PNU,
    )

    cross_pnu_blocked = False
    try:
        analyze_site_object(
            site(),
            district_unit_plan_registry_candidate=wrong_pnu,
        )
    except ValueError:
        cross_pnu_blocked = True

    check(
        "Cross-PNU district-unit envelope blocked by Service",
        cross_pnu_blocked,
    )

    simultaneous_blocked = False
    try:
        analyze_site_object(
            site(),
            historical_rule_input=object(),
            district_unit_plan_registry_candidate=verified,
        )
    except ValueError:
        simultaneous_blocked = True

    check(
        "Historical plus district-unit simultaneous Service input blocked",
        simultaneous_blocked,
    )

    print(
        "SITE_ANALYSIS_SERVICE_DISTRICT_UNIT_PLAN_HANDOFF_CONTRACT_PASS"
    )


if __name__ == "__main__":
    main()
