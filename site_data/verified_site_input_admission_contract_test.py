# -*- coding: utf-8 -*-
"""Fail-closed contracts for verified SITE input admission in the orchestrator."""
from __future__ import annotations

from unittest.mock import patch

from law_data.district_unit_plan_site_truth_promotion_rule_input_bridge import CONDITION_NAME
from law_data.district_unit_plan_site_truth_promotion_executor import REGISTRY_SOURCE
from law_data.district_unit_plan_verified_registry_candidate_envelope import (
    BOUNDARY_NAME as DISTRICT_BOUNDARY,
    DistrictUnitPlanVerifiedRegistryCandidateEnvelope,
)
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import (
    BOUNDARY_NAME as HISTORICAL_BOUNDARY,
    READY,
    HistoricalSiteEventSiteTruthPromotionRuleInputBridge,
)
from site_data.site_analysis_orchestrator import SiteAnalysisError, analyze_site_by_parcel
from site_data.site_data_model import Site

SITE_PNU = "1168010300100120000"
OTHER_PNU = "1168010300100120001"


def fake_site() -> Site:
    return Site(
        site_id="11680-10300-0012-0000",
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0000",
    )


def district_envelope(pnu: str) -> DistrictUnitPlanVerifiedRegistryCandidateEnvelope:
    return DistrictUnitPlanVerifiedRegistryCandidateEnvelope(
        boundary=DISTRICT_BOUNDARY,
        canonical_pnu=pnu,
        registry_candidate={
            CONDITION_NAME: {
                "state": "TRUE",
                "confidence": "HIGH",
                "source": REGISTRY_SOURCE,
                "pnu": pnu,
                "provenance": "HYBRID_SPATIAL_NOTICE_VERIFIED",
            }
        },
        verified=True,
    )


def promotion_bridge(pnu: str) -> HistoricalSiteEventSiteTruthPromotionRuleInputBridge:
    return HistoricalSiteEventSiteTruthPromotionRuleInputBridge(
        boundary=HISTORICAL_BOUNDARY,
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
        historical_rule_input={
            "channel": CHANNEL,
            "provenance": PROVENANCE,
            "repairs": [
                {
                    "condition": "TEST_CONDITION",
                    "after": "TRUE",
                    "new_confidence": "HIGH",
                    "new_source": PROVENANCE,
                    "pnu": pnu,
                }
            ],
        },
    )


def expect_site_analysis_error(**kwargs) -> None:
    try:
        analyze_site_by_parcel(
            sigungu_cd="11680",
            bjdong_cd="10300",
            plat_gb_cd="0",
            bun="0012",
            ji="0000",
            service_key="TEST_KEY",
            **kwargs,
        )
    except SiteAnalysisError:
        return
    raise AssertionError("unsafe verified SITE input was admitted")


def main() -> None:
    with patch(
        "site_data.site_analysis_orchestrator.fetch_building_items",
        return_value={"items": [{"x": 1}], "total_count": 1, "result_code": "00"},
    ), patch(
        "site_data.site_analysis_orchestrator.create_site",
        return_value=fake_site(),
    ):
        # A district envelope for another parcel must never bind to this Site.
        expect_site_analysis_error(
            district_unit_plan_registry_candidate=district_envelope(OTHER_PNU)
        )

        # A historical promotion for another parcel must never bind to this Site.
        expect_site_analysis_error(
            historical_promotion_rule_input_bridge=promotion_bridge(OTHER_PNU)
        )

        # Historical and district verified inputs cannot be combined.
        expect_site_analysis_error(
            historical_promotion_rule_input_bridge=promotion_bridge(SITE_PNU),
            district_unit_plan_registry_candidate=district_envelope(SITE_PNU),
        )

        # A malformed/not-ready district envelope must fail closed.
        bad_district = district_envelope(SITE_PNU)
        bad_district = DistrictUnitPlanVerifiedRegistryCandidateEnvelope(
            boundary=bad_district.boundary,
            canonical_pnu=bad_district.canonical_pnu,
            registry_candidate=bad_district.registry_candidate,
            verified=False,
        )
        expect_site_analysis_error(
            district_unit_plan_registry_candidate=bad_district
        )

    print("VERIFIED_SITE_INPUT_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
