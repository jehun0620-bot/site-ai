"""Contract test for district-unit verified registry candidate transport."""

from dataclasses import replace

from .district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from .district_unit_plan_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME as BRIDGE_BOUNDARY_NAME,
    CONDITION_NAME,
    READY,
    DistrictUnitPlanSiteTruthPromotionRuleInputBridge,
)
from .district_unit_plan_verified_registry_candidate_envelope import (
    BOUNDARY_NAME,
    seal_verified_district_unit_plan_registry_candidate,
)

PNU = "1168010600100010000"
OTHER_PNU = "1168010600100020000"


def _candidate(pnu=PNU):
    return {
        CONDITION_NAME: {
            "state": "TRUE",
            "confidence": "HIGH",
            "source": REGISTRY_SOURCE,
            "pnu": pnu,
            "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
        }
    }


def _bridge():
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
        registry_candidate=_candidate(),
    )


def _assert_isolated(result):
    assert result.site_truth_decided is False
    assert result.registry_merged is False
    assert result.collision_policy_called is False
    assert result.rule_engine_called is False
    assert result.builder_modified is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False


def main():
    bridge = _bridge()
    result = seal_verified_district_unit_plan_registry_candidate(bridge)

    assert result.ready
    assert result.verified
    assert result.boundary == BOUNDARY_NAME
    assert result.canonical_pnu == PNU
    assert result.registry_candidate[CONDITION_NAME]["pnu"] == PNU
    assert result.registry_candidate[CONDITION_NAME]["source"] == REGISTRY_SOURCE
    _assert_isolated(result)

    # Sealed transport must be a snapshot, not an alias.
    assert result.registry_candidate is not bridge.registry_candidate

    malformed_pnu = replace(
        _bridge(),
        canonical_pnu="FORGED",
        registry_candidate=_candidate("FORGED"),
    )
    malformed_result = seal_verified_district_unit_plan_registry_candidate(
        malformed_pnu
    )
    assert not malformed_result.ready
    assert not malformed_result.verified
    assert malformed_result.canonical_pnu == ""
    assert malformed_result.registry_candidate == {}
    _assert_isolated(malformed_result)

    cross_pnu = replace(
        _bridge(),
        registry_candidate=_candidate(OTHER_PNU),
    )
    cross_result = seal_verified_district_unit_plan_registry_candidate(cross_pnu)
    assert not cross_result.ready
    assert not cross_result.verified
    assert cross_result.registry_candidate == {}
    _assert_isolated(cross_result)

    forged_source_candidate = _candidate()
    forged_source_candidate[CONDITION_NAME]["source"] = "FORGED"
    forged_source = replace(
        _bridge(),
        registry_candidate=forged_source_candidate,
    )
    assert not seal_verified_district_unit_plan_registry_candidate(
        forged_source
    ).ready

    forged_boundary = replace(_bridge(), boundary="FORGED")
    assert not seal_verified_district_unit_plan_registry_candidate(
        forged_boundary
    ).ready

    rejected_bridge = replace(
        _bridge(),
        status="REJECTED",
        bridge_ready=False,
    )
    assert not seal_verified_district_unit_plan_registry_candidate(
        rejected_bridge
    ).ready

    assert not seal_verified_district_unit_plan_registry_candidate(None).ready

    # Raw mappings are not accepted as production transport.
    assert not seal_verified_district_unit_plan_registry_candidate(
        {"canonical_pnu": PNU, "registry_candidate": _candidate()}
    ).ready

    print(
        "DISTRICT_UNIT_PLAN_VERIFIED_REGISTRY_CANDIDATE_ENVELOPE_CONTRACT_PASS"
    )


if __name__ == "__main__":
    main()
