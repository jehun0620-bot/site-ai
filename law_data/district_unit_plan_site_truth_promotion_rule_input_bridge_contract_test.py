"""Contract test for district-unit-plan promotion rule-input bridge."""

from dataclasses import replace

from .district_unit_plan_site_truth_promotion_executor import (
    BOUNDARY_NAME as EXECUTOR_BOUNDARY,
    REGISTRY_SOURCE,
    DistrictUnitPlanSiteTruthPromotionExecution,
)
from .district_unit_plan_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME,
    bridge_district_unit_plan_site_truth_promotion_rule_input,
)

PNU = "1168010600100010000"


def _execution() -> DistrictUnitPlanSiteTruthPromotionExecution:
    promoted = {
        "type": "SITE",
        "state": "TRUE",
        "confidence": "HIGH",
        "source": REGISTRY_SOURCE,
        "runtime": True,
        "pnu": PNU,
        "historical": False,
        "hybrid": True,
        "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
        "promotion_authorization_boundary": "DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_AUTHORIZATION",
        "promotion_executor_boundary": EXECUTOR_BOUNDARY,
    }
    return DistrictUnitPlanSiteTruthPromotionExecution(
        boundary=EXECUTOR_BOUNDARY,
        status="EXECUTED",
        authorization_present=True,
        authorization_boundary_matched=True,
        promotion_authorized=True,
        bound_pnu=PNU,
        bound_condition="지구단위계획",
        bound_state="TRUE",
        provenance_verified=True,
        promoted_condition_present=True,
        promoted_condition=promoted,
        missing_gates=(),
        execution_succeeded=True,
    )


def _assert_isolated(result) -> None:
    assert result.site_registry_mutated is False
    assert result.registry_merged is False
    assert result.collision_policy_called is False
    assert result.rule_engine_called is False
    assert result.builder_modified is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False


def main() -> None:
    result = bridge_district_unit_plan_site_truth_promotion_rule_input(_execution())
    assert result.ready
    assert result.boundary == BOUNDARY_NAME
    assert result.canonical_pnu == PNU
    assert set(result.registry_candidate) == {"지구단위계획"}
    condition = result.registry_candidate["지구단위계획"]
    assert condition["state"] == "TRUE"
    assert condition["confidence"] == "HIGH"
    assert condition["source"] == REGISTRY_SOURCE
    assert condition["pnu"] == PNU
    assert condition["provenance"] == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    _assert_isolated(result)

    forged_boundary = replace(_execution(), boundary="FORGED")
    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(
        forged_boundary
    ).ready

    wrong_condition = replace(_execution(), bound_condition="개발밀도관리구역")
    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(
        wrong_condition
    ).ready

    false_state = replace(_execution(), bound_state="FALSE")
    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(
        false_state
    ).ready

    forged_promoted = dict(_execution().promoted_condition)
    forged_promoted["source"] = "FORGED"
    forged_source = replace(_execution(), promoted_condition=forged_promoted)
    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(
        forged_source
    ).ready

    cross_pnu_promoted = dict(_execution().promoted_condition)
    cross_pnu_promoted["pnu"] = "1168010600100020000"
    cross_pnu = replace(_execution(), promoted_condition=cross_pnu_promoted)
    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(
        cross_pnu
    ).ready

    assert not bridge_district_unit_plan_site_truth_promotion_rule_input(None).ready

    print("DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_RULE_INPUT_BRIDGE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
