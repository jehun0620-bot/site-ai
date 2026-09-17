"""Contract test for the common verified SITE registry consumption boundary."""
from dataclasses import replace

from .common_verified_site_registry_live_consumption import (
    HISTORICAL, DISTRICT_UNIT_PLAN,
    normalize_verified_site_registry_live_consumption,
)
from .historical_merged_registry_live_consumption_authorization import HistoricalMergedRegistryLiveConsumptionAuthorization
from .district_unit_plan_merged_registry_live_consumption_authorization import DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization

PNU = "1168010600100010000"

def _historical():
    registry = {"역사조건": {"state": "FALSE", "confidence": "HIGH", "source": "RUNTIME_HISTORICAL_SITE_EVENT", "pnu": PNU}}
    return HistoricalMergedRegistryLiveConsumptionAuthorization(
        boundary="HISTORICAL_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION",
        policy_present=True, policy_boundary_matched=True, merge_candidate_ready=True,
        no_conflicting_collisions=True, candidate_registry_valid=True,
        historical_provenance_preserved=True, missing_gates=(),
        live_consumption_authorized=True, authorized_merged_registry=registry,
    )

def _district():
    registry = {"지구단위계획": {"state": "TRUE", "confidence": "HIGH", "source": "RUNTIME_DISTRICT_UNIT_PLAN_HYBRID", "pnu": PNU, "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED"}}
    return DistrictUnitPlanMergedRegistryLiveConsumptionAuthorization(
        boundary="DISTRICT_UNIT_PLAN_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION",
        policy_present=True, policy_boundary_matched=True, merge_candidate_ready=True,
        no_conflicting_collision=True, no_unresolved_collision=True,
        candidate_registry_valid=True, district_provenance_preserved=True,
        missing_gates=(), live_consumption_authorized=True,
        authorized_merged_registry=registry,
    )

def _assert_isolated(result):
    assert result.rule_engine_called is False
    assert result.builder_modified is False
    assert result.production_wiring_applied is False
    assert result.runtime_registered is False
    assert result.public_api_exposed is False

def main():
    historical = normalize_verified_site_registry_live_consumption(_historical())
    assert historical.ready
    assert historical.source_family == HISTORICAL
    assert historical.verified_site_registry["역사조건"]["state"] == "FALSE"
    _assert_isolated(historical)

    district = normalize_verified_site_registry_live_consumption(_district())
    assert district.ready
    assert district.source_family == DISTRICT_UNIT_PLAN
    assert district.verified_site_registry["지구단위계획"]["state"] == "TRUE"
    assert district.verified_site_registry["지구단위계획"]["provenance"] == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    _assert_isolated(district)

    rejected_historical = replace(_historical(), live_consumption_authorized=False)
    assert not normalize_verified_site_registry_live_consumption(rejected_historical).ready

    rejected_district = replace(_district(), live_consumption_authorized=False)
    assert not normalize_verified_site_registry_live_consumption(rejected_district).ready

    empty_district = replace(_district(), authorized_merged_registry={})
    assert not normalize_verified_site_registry_live_consumption(empty_district).ready

    assert not normalize_verified_site_registry_live_consumption(None).ready
    assert not normalize_verified_site_registry_live_consumption({"forged": True}).ready

    print("COMMON_VERIFIED_SITE_REGISTRY_LIVE_CONSUMPTION_CONTRACT_PASS")

if __name__ == "__main__":
    main()
