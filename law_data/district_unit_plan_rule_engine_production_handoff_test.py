"""Production handoff contract for verified district-unit registry input."""

from dataclasses import replace

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
from law_data.historical_verified_rule_input_envelope import (
    seal_verified_historical_rule_input,
)
from law_data.rule_evaluation_pipeline import evaluate_site_rules
from law_data.site_analysis_builder import build_site_analysis

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"

SITE_INPUT = {
    "sigungu_code": "11680",
    "bjdong_code": "10300",
    "main_no": "0012",
    "sub_no": "0000",
    "pnu": PNU,
}


def check(name, passed):
    print(f"{name}: {'PASS' if passed else 'FAIL'}")
    if not passed:
        raise AssertionError(name)


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
    legacy = build_site_analysis(site_input=SITE_INPUT)
    check(
        "Legacy builder path preserved",
        "district_unit_plan" not in legacy.get("input", {}),
    )

    raw_blocked = False
    try:
        build_site_analysis(
            site_input=SITE_INPUT,
            district_unit_plan_registry_candidate=candidate(),
        )
    except ValueError:
        raw_blocked = True
    check("Raw district-unit builder injection blocked", raw_blocked)

    verified = envelope()
    before = verified.to_dict()

    spatial = evaluate_site_rules().get("site_registry", {})
    existing = spatial.get(CONDITION_NAME)

    if existing and existing.get("state") in ("FALSE", "UNKNOWN", "UNSET"):
        collision_blocked = False
        try:
            build_site_analysis(
                site_input=SITE_INPUT,
                district_unit_plan_registry_candidate=verified,
            )
        except ValueError:
            collision_blocked = True
        check(
            "Existing conclusive/unresolved spatial collision fail-closed",
            collision_blocked,
        )
    else:
        integrated = build_site_analysis(
            site_input=SITE_INPUT,
            district_unit_plan_registry_candidate=verified,
        )
        registry = integrated.get("rule_engine", {}).get("site_registry", {})
        check(
            "Verified district-unit builder-to-Rule-Engine consumption",
            CONDITION_NAME in registry
            and registry[CONDITION_NAME].get("state") == "TRUE",
        )
        check(
            "District-unit input preserved",
            integrated.get("input", {}).get("district_unit_plan")
            == candidate(),
        )

    check("Caller envelope immutable", verified.to_dict() == before)

    wrong_pnu = replace(
        verified,
        canonical_pnu=OTHER_PNU,
    )
    cross_pnu_blocked = False
    try:
        build_site_analysis(
            site_input=SITE_INPUT,
            district_unit_plan_registry_candidate=wrong_pnu,
        )
    except ValueError:
        cross_pnu_blocked = True
    check("Cross-PNU district-unit envelope blocked", cross_pnu_blocked)

    historical = seal_verified_historical_rule_input(
        canonical_pnu=PNU,
        historical_rule_input={
            "channel": "HISTORICAL_SITE_EVENT",
            "provenance": "TEST",
            "repairs": [],
        },
    )

    ambiguous_blocked = False
    try:
        build_site_analysis(
            site_input=SITE_INPUT,
            historical_rule_input=historical,
            district_unit_plan_registry_candidate=verified,
        )
    except ValueError:
        ambiguous_blocked = True
    check(
        "Historical plus district-unit simultaneous injection blocked",
        ambiguous_blocked,
    )

    print("DISTRICT_UNIT_PLAN_RULE_ENGINE_PRODUCTION_HANDOFF_PASS")


if __name__ == "__main__":
    main()
