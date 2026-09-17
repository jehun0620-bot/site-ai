"""Contract test for district-unit-plan/spatial registry collision policy."""

from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_spatial_registry_collision_policy import (
    evaluate_district_unit_plan_spatial_registry_collision_policy,
)

PNU = "1168010600100010000"


def _district_registry():
    return {
        "지구단위계획": {
            "state": "TRUE",
            "confidence": "HIGH",
            "source": REGISTRY_SOURCE,
            "pnu": PNU,
            "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
        }
    }


def _spatial(state=None):
    registry = {
        "서울도심": {
            "state": "FALSE",
            "confidence": "HIGH",
            "source": "RUNTIME_SPATIAL_CONDITION",
        }
    }
    if state is not None:
        registry["지구단위계획"] = {
            "state": state,
            "confidence": "HIGH",
            "source": "RUNTIME_SPATIAL_CONDITION",
            "pnu": PNU,
        }
    return registry


def _assert_isolated(result):
    assert result.implicit_precedence_used is False
    assert result.site_registry_mutated is False
    assert result.rule_engine_called is False
    assert result.builder_modified is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False


def main():
    no_collision = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial(), _district_registry()
    )
    assert no_collision.ready
    assert not no_collision.collision_present
    assert no_collision.canonical_pnu == PNU
    assert no_collision.merged_registry_candidate["지구단위계획"]["state"] == "TRUE"
    assert no_collision.merged_registry_candidate["지구단위계획"]["source"] == REGISTRY_SOURCE
    _assert_isolated(no_collision)

    compatible = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial("TRUE"), _district_registry()
    )
    assert compatible.ready
    assert compatible.collision_present
    assert compatible.compatible_collision
    assert compatible.canonical_pnu == PNU
    assert compatible.merged_registry_candidate["지구단위계획"]["source"] == "RUNTIME_SPATIAL_CONDITION"
    _assert_isolated(compatible)

    conflict = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial("FALSE"), _district_registry()
    )
    assert not conflict.ready
    assert conflict.conflicting_collision
    assert conflict.merged_registry_candidate == {}
    _assert_isolated(conflict)

    unknown = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial("UNKNOWN"), _district_registry()
    )
    assert not unknown.ready
    assert unknown.unresolved_collision
    assert unknown.merged_registry_candidate == {}
    _assert_isolated(unknown)

    unset = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial("UNSET"), _district_registry()
    )
    assert not unset.ready
    assert unset.unresolved_collision
    _assert_isolated(unset)

    bad_pnu = _district_registry()
    next(iter(bad_pnu.values()))["pnu"] = "FORGED"
    bad_pnu_result = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial(), bad_pnu
    )
    assert not bad_pnu_result.ready
    assert bad_pnu_result.canonical_pnu == ""
    _assert_isolated(bad_pnu_result)

    bad_district = _district_registry()
    bad_district["지구단위계획"]["source"] = "FORGED"
    forged = evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial(), bad_district
    )
    assert not forged.ready
    _assert_isolated(forged)

    assert not evaluate_district_unit_plan_spatial_registry_collision_policy(
        None, _district_registry()
    ).ready
    assert not evaluate_district_unit_plan_spatial_registry_collision_policy(
        _spatial(), None
    ).ready

    print("DISTRICT_UNIT_PLAN_SPATIAL_REGISTRY_COLLISION_POLICY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
