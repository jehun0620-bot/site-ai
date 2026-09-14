"""Fail-closed production-consumption eligibility for HISTORICAL_SITE_EVENT.

STEP32 determines only whether a concrete STEP31 semantic resolution is
eligible for later production consumption under explicit profile permissions.
It does not mutate SITE or Rule Engine state, register production/runtime
behavior, write outputs, or expose public API behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_final_resolution import (
    FALSE,
    TRUE,
    UNKNOWN,
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_PRODUCTION_CONSUMPTION_ELIGIBILITY"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


@dataclass(frozen=True)
class HistoricalSiteEventProductionConsumptionEligibilityAssessment:
    boundary: str
    profile_present: bool
    profile_name: str | None
    historical_resolution_type_matched: bool
    historical_condition_type_matched: bool
    final_resolution_assessment_present: bool
    final_resolution_profile_aligned: bool
    semantic_resolution: str
    semantic_resolution_consumable: bool
    site_promotion_allowed: bool
    production_registration_allowed: bool
    runtime_registration_allowed: bool
    missing_gates: tuple[str, ...]
    production_consumption_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "profile_present": self.profile_present,
            "profile_name": self.profile_name,
            "historical_resolution_type_matched": self.historical_resolution_type_matched,
            "historical_condition_type_matched": self.historical_condition_type_matched,
            "final_resolution_assessment_present": self.final_resolution_assessment_present,
            "final_resolution_profile_aligned": self.final_resolution_profile_aligned,
            "semantic_resolution": self.semantic_resolution,
            "semantic_resolution_consumable": self.semantic_resolution_consumable,
            "site_promotion_allowed": self.site_promotion_allowed,
            "production_registration_allowed": self.production_registration_allowed,
            "runtime_registration_allowed": self.runtime_registration_allowed,
            "missing_gates": list(self.missing_gates),
            "production_consumption_eligible": self.production_consumption_eligible,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
            "public_api_exposed": False,
        }


def evaluate_historical_site_event_production_consumption_eligibility(
    profile: RegulationResolutionProfile | None,
    final_resolution: HistoricalSiteEventFinalResolutionAssessment | None,
) -> HistoricalSiteEventProductionConsumptionEligibilityAssessment:
    profile_present = isinstance(profile, RegulationResolutionProfile)
    profile_name = profile.name if profile_present else None
    historical_resolution_type_matched = bool(
        profile_present and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    historical_condition_type_matched = bool(
        profile_present and profile.condition_type == HISTORICAL_CONDITION_TYPE
    )

    final_resolution_assessment_present = isinstance(
        final_resolution, HistoricalSiteEventFinalResolutionAssessment
    )
    final_resolution_profile_aligned = bool(
        profile_present
        and final_resolution_assessment_present
        and final_resolution.profile_name == profile_name
    )
    semantic_resolution = (
        final_resolution.resolution if final_resolution_assessment_present else UNKNOWN
    )
    semantic_resolution_consumable = semantic_resolution in {TRUE, FALSE}

    site_promotion_allowed = bool(
        profile_present and profile.site_promotion_allowed is True
    )
    production_registration_allowed = bool(
        profile_present and profile.production_registration_allowed is True
    )
    runtime_registration_allowed = bool(
        profile_present and profile.runtime_registration_allowed is True
    )

    gates = {
        "profile_present": profile_present,
        "historical_resolution_type_matched": historical_resolution_type_matched,
        "historical_condition_type_matched": historical_condition_type_matched,
        "final_resolution_assessment_present": final_resolution_assessment_present,
        "final_resolution_profile_aligned": final_resolution_profile_aligned,
        "semantic_resolution_consumable": semantic_resolution_consumable,
        "site_promotion_allowed": site_promotion_allowed,
        "production_registration_allowed": production_registration_allowed,
        "runtime_registration_allowed": runtime_registration_allowed,
    }
    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    production_consumption_eligible = not missing_gates

    return HistoricalSiteEventProductionConsumptionEligibilityAssessment(
        boundary=BOUNDARY_NAME,
        profile_present=profile_present,
        profile_name=profile_name,
        historical_resolution_type_matched=historical_resolution_type_matched,
        historical_condition_type_matched=historical_condition_type_matched,
        final_resolution_assessment_present=final_resolution_assessment_present,
        final_resolution_profile_aligned=final_resolution_profile_aligned,
        semantic_resolution=semantic_resolution,
        semantic_resolution_consumable=semantic_resolution_consumable,
        site_promotion_allowed=site_promotion_allowed,
        production_registration_allowed=production_registration_allowed,
        runtime_registration_allowed=runtime_registration_allowed,
        missing_gates=missing_gates,
        production_consumption_eligible=production_consumption_eligible,
    )
