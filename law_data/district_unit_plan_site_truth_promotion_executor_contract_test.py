"""Contract test for the district-unit-plan isolated promotion executor."""

from dataclasses import replace

from .district_unit_plan_site_truth_promotion_authorization import (
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY,
    DistrictUnitPlanSiteTruthPromotionAuthorization,
)
from .district_unit_plan_site_truth_promotion_executor import (
    BOUNDARY_NAME,
    REGISTRY_SOURCE,
    execute_district_unit_plan_site_truth_promotion,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)

PNU = "1168010600100010000"


def _authorization() -> DistrictUnitPlanSiteTruthPromotionAuthorization:
    return DistrictUnitPlanSiteTruthPromotionAuthorization(
        boundary=AUTHORIZATION_BOUNDARY,
        status="AUTHORIZED",
        canonical_pnu=PNU,
        resolver_family=HYBRID_SPATIAL_NOTICE,
        condition_name="지구단위계획",
        bound_state="TRUE",
        common_applicability_admitted=True,
        pnu_valid=True,
        family_matched=True,
        candidate_true=True,
        applicability_applies=True,
        provenance_kind="HYBRID_SPATIAL_NOTICE_VERIFIED",
        missing_gates=(),
        promotion_authorized=True,
    )


def _assert_isolated(result) -> None:
    assert result.site_registry_mutated is False
    assert result.rule_engine_called is False
    assert result.builder_modified is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False


def main() -> None:
    result = execute_district_unit_plan_site_truth_promotion(_authorization())
    assert result.executed
    assert result.boundary == BOUNDARY_NAME
    assert result.bound_pnu == PNU
    assert result.bound_condition == "지구단위계획"
    assert result.bound_state == "TRUE"
    assert result.promoted_condition_present
    assert result.promoted_condition["type"] == "SITE"
    assert result.promoted_condition["state"] == "TRUE"
    assert result.promoted_condition["confidence"] == "HIGH"
    assert result.promoted_condition["source"] == REGISTRY_SOURCE
    assert result.promoted_condition["runtime"] is True
    assert result.promoted_condition["pnu"] == PNU
    assert result.promoted_condition["historical"] is False
    assert result.promoted_condition["hybrid"] is True
    assert result.promoted_condition["provenance"] == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    _assert_isolated(result)

    forged_boundary = replace(_authorization(), boundary="FORGED")
    assert not execute_district_unit_plan_site_truth_promotion(forged_boundary).executed

    forged_status = replace(_authorization(), status="REJECTED")
    assert not execute_district_unit_plan_site_truth_promotion(forged_status).executed

    wrong_condition = replace(_authorization(), condition_name="개발밀도관리구역")
    assert not execute_district_unit_plan_site_truth_promotion(wrong_condition).executed

    false_state = replace(_authorization(), bound_state="FALSE")
    assert not execute_district_unit_plan_site_truth_promotion(false_state).executed

    wrong_provenance = replace(_authorization(), provenance_kind="FORGED")
    assert not execute_district_unit_plan_site_truth_promotion(wrong_provenance).executed

    forged_runtime_authority = replace(_authorization(), runtime_registration_allowed=True)
    forged_result = execute_district_unit_plan_site_truth_promotion(forged_runtime_authority)
    assert not forged_result.executed
    _assert_isolated(forged_result)

    assert not execute_district_unit_plan_site_truth_promotion(None).executed

    print("DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_EXECUTOR_CONTRACT_PASS")


if __name__ == "__main__":
    main()
