"""Contract test for district-unit-plan live-consumption authorization."""

from dataclasses import replace

from .district_unit_plan_merged_registry_live_consumption_authorization import (
    BOUNDARY_NAME,
    authorize_district_unit_plan_merged_registry_live_consumption,
)
from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_spatial_registry_collision_policy import (
    BOUNDARY_NAME as POLICY_BOUNDARY,
    DistrictUnitPlanSpatialRegistryCollisionPolicy,
)

PNU = "1168010600100010000"


def _district_entry():
    return {
        "state": "TRUE",
        "confidence": "HIGH",
        "source": REGISTRY_SOURCE,
        "pnu": PNU,
        "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
    }


def _policy(entry=None):
    registry = {
        "서울도심": {
            "state": "FALSE",
            "confidence": "HIGH",
            "source": "RUNTIME_SPATIAL_CONDITION",
        },
        "지구단위계획": entry or _district_entry(),
    }
    return DistrictUnitPlanSpatialRegistryCollisionPolicy(
        boundary=POLICY_BOUNDARY,
        spatial_registry_valid=True,
        district_registry_valid=True,
        district_condition_present=True,
        collision_present=False,
        spatial_collision_state=None,
        district_collision_state="TRUE",
        compatible_collision=False,
        conflicting_collision=False,
        unresolved_collision=False,
        merge_candidate_ready=True,
        canonical_pnu=PNU,
        merged_registry_candidate=registry,
    )


def _assert_non_executing(result):
    assert result.apply_site_registry_called is False
    assert result.rule_engine_called is False
    assert result.rule_engine_modified is False
    assert result.builder_modified is False
    assert result.production_wiring_applied is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False


def main():
    result = authorize_district_unit_plan_merged_registry_live_consumption(_policy())
    assert result.authorized
    assert result.boundary == BOUNDARY_NAME
    assert result.canonical_pnu_valid
    assert result.canonical_pnu == PNU
    assert result.authorized_merged_registry["지구단위계획"]["state"] == "TRUE"
    assert result.authorized_merged_registry["지구단위계획"]["source"] == REGISTRY_SOURCE
    _assert_non_executing(result)

    spatial_compatible = {
        "state": "TRUE",
        "confidence": "HIGH",
        "source": "RUNTIME_SPATIAL_CONDITION",
        "pnu": PNU,
    }
    compatible = replace(
        _policy(spatial_compatible),
        collision_present=True,
        spatial_collision_state="TRUE",
        compatible_collision=True,
    )
    compatible_result = authorize_district_unit_plan_merged_registry_live_consumption(
        compatible
    )
    assert compatible_result.authorized
    assert compatible_result.canonical_pnu_valid
    assert compatible_result.canonical_pnu == PNU
    assert compatible_result.authorized_merged_registry["지구단위계획"]["source"] == "RUNTIME_SPATIAL_CONDITION"
    _assert_non_executing(compatible_result)

    missing_pnu = replace(_policy(), canonical_pnu="")
    missing_pnu_result = authorize_district_unit_plan_merged_registry_live_consumption(
        missing_pnu
    )
    assert not missing_pnu_result.authorized
    assert not missing_pnu_result.canonical_pnu_valid
    assert missing_pnu_result.canonical_pnu == ""

    forged_pnu = replace(_policy(), canonical_pnu="FORGED")
    forged_pnu_result = authorize_district_unit_plan_merged_registry_live_consumption(
        forged_pnu
    )
    assert not forged_pnu_result.authorized
    assert not forged_pnu_result.canonical_pnu_valid

    wrong_boundary = replace(_policy(), boundary="FORGED")
    assert not authorize_district_unit_plan_merged_registry_live_consumption(
        wrong_boundary
    ).authorized

    conflict = replace(
        _policy(),
        merge_candidate_ready=False,
        conflicting_collision=True,
        merged_registry_candidate={},
    )
    assert not authorize_district_unit_plan_merged_registry_live_consumption(
        conflict
    ).authorized

    unresolved = replace(
        _policy(),
        merge_candidate_ready=False,
        unresolved_collision=True,
        merged_registry_candidate={},
    )
    assert not authorize_district_unit_plan_merged_registry_live_consumption(
        unresolved
    ).authorized

    forged_entry = _district_entry()
    forged_entry["source"] = "FORGED"
    forged = _policy(forged_entry)
    assert not authorize_district_unit_plan_merged_registry_live_consumption(
        forged
    ).authorized

    forged_provenance = _district_entry()
    forged_provenance["provenance"] = "FORGED"
    forged_provenance_result = authorize_district_unit_plan_merged_registry_live_consumption(
        _policy(forged_provenance)
    )
    assert not forged_provenance_result.authorized

    assert not authorize_district_unit_plan_merged_registry_live_consumption(None).authorized

    print("DISTRICT_UNIT_PLAN_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
