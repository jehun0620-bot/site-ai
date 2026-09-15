"""Read-only STEP33 application adapter for HISTORICAL_SITE_EVENT.

This boundary converts aligned STEP31 semantic resolution and STEP32 production-
consumption eligibility assessments into the existing ProductionSiteCondition
shadow contract. It does not mutate SITE or Rule Engine state, execute a
historical producer, apply production wiring, register runtime behavior, or
expose a public API.
"""

from __future__ import annotations

from typing import Any

from law_data.historical_site_event_final_resolution import (
    FALSE,
    TRUE,
    UNKNOWN,
    HistoricalSiteEventFinalResolutionAssessment,
)
from law_data.historical_site_event_production_consumption_eligibility import (
    HistoricalSiteEventProductionConsumptionEligibilityAssessment,
)
from law_data.production_site_condition import (
    ProductionSiteCondition,
    normalize_production_site_condition,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


ADAPTER_NAME = "HISTORICAL_SITE_EVENT_PRODUCTION_APPLICATION_ADAPTER"
HISTORICAL_RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
HISTORICAL_CONDITION_TYPE = "SITE_HISTORY"


def adapt_historical_site_event_production_application_shadow(
    profile: RegulationResolutionProfile | None,
    final_resolution: HistoricalSiteEventFinalResolutionAssessment | None,
    eligibility: HistoricalSiteEventProductionConsumptionEligibilityAssessment | None,
    *,
    confidence: Any = "NONE",
    source: Any = "",
) -> ProductionSiteCondition:
    """Create an application-ready shadow without applying it anywhere.

    TRUE/FALSE is preserved only when STEP31 and STEP32 are concrete, aligned,
    and STEP32 explicitly marks production consumption eligible. Every missing,
    malformed, UNKNOWN, or misaligned input fails closed to UNKNOWN.

    `runtime_registered` remains False even when the profile says runtime
    registration is allowed: permission is not registration/application.
    """

    profile_present = isinstance(profile, RegulationResolutionProfile)
    final_present = isinstance(
        final_resolution, HistoricalSiteEventFinalResolutionAssessment
    )
    eligibility_present = isinstance(
        eligibility, HistoricalSiteEventProductionConsumptionEligibilityAssessment
    )

    profile_name = profile.name if profile_present else "HISTORICAL_SITE_EVENT"
    profile_shape_matched = bool(
        profile_present
        and profile.condition_type == HISTORICAL_CONDITION_TYPE
        and profile.resolution_type == HISTORICAL_RESOLUTION_TYPE
    )
    final_aligned = bool(
        profile_present
        and final_present
        and final_resolution.profile_name == profile.name
    )
    eligibility_aligned = bool(
        profile_present
        and eligibility_present
        and eligibility.profile_name == profile.name
    )
    assessments_aligned = bool(
        final_present
        and eligibility_present
        and eligibility.semantic_resolution == final_resolution.resolution
    )
    semantic_resolution = final_resolution.resolution if final_present else UNKNOWN
    semantic_consumable = semantic_resolution in {TRUE, FALSE}
    production_consumption_eligible = bool(
        eligibility_present and eligibility.production_consumption_eligible is True
    )

    application_ready = all(
        (
            profile_shape_matched,
            final_aligned,
            eligibility_aligned,
            assessments_aligned,
            semantic_consumable,
            production_consumption_eligible,
        )
    )
    production_state = semantic_resolution if application_ready else UNKNOWN

    diagnostics = {
        "adapter": ADAPTER_NAME,
        "profile_present": profile_present,
        "profile_shape_matched": profile_shape_matched,
        "final_resolution_assessment_present": final_present,
        "final_resolution_profile_aligned": final_aligned,
        "eligibility_assessment_present": eligibility_present,
        "eligibility_profile_aligned": eligibility_aligned,
        "assessments_semantically_aligned": assessments_aligned,
        "semantic_resolution": semantic_resolution,
        "production_consumption_eligible": production_consumption_eligible,
        "application_ready": application_ready,
        "site_state_mutated": False,
        "rule_engine_state_mutated": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "historical_producer_auto_run": False,
        "public_api_exposed": False,
    }

    return normalize_production_site_condition(
        name=profile_name,
        condition_type=HISTORICAL_CONDITION_TYPE,
        resolution_type=HISTORICAL_RESOLUTION_TYPE,
        state=production_state,
        confidence=confidence,
        source=source,
        provenance={
            "adapter": ADAPTER_NAME,
            "step31_boundary": (
                final_resolution.boundary if final_present else None
            ),
            "step32_boundary": eligibility.boundary if eligibility_present else None,
        },
        production_eligible=application_ready,
        runtime_registered=False,
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        diagnostics=diagnostics,
    )
