from __future__ import annotations

from typing import Any, Mapping

from law_data.production_historical_site_event_adapter import (
    adapt_historical_site_event_to_production_contract,
)
from law_data.urban_area_conversion_historical_site_event_shadow_adapter import (
    CONDITION_NAME,
    adapt_urban_area_conversion_history_shadow,
)
from law_data.urban_area_conversion_production_readiness_adapter import (
    adapt_urban_area_conversion_production_readiness,
)
from law_data.urban_area_conversion_provenance_policy_adapter import (
    adapt_urban_area_conversion_provenance_policy,
)
from law_data.urban_area_conversion_runtime_registration_policy_adapter import (
    adapt_urban_area_conversion_runtime_registration_policy,
)


ADAPTER_MODE = "READ_ONLY_PRODUCTION_CONDITION_SHADOW"


def adapt_urban_area_conversion_production_condition_shadow(
    previous_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a production-facing SITE_HISTORY shadow without production wiring.

    Existing condition-specific adapters remain authoritative for historical
    resolution, readiness, provenance, and runtime-registration policy. This
    wrapper only composes their read-only results into the common production
    condition contract.
    """

    historical_shadow = adapt_urban_area_conversion_history_shadow(previous_payload)
    readiness = adapt_urban_area_conversion_production_readiness()
    provenance = adapt_urban_area_conversion_provenance_policy(previous_payload)
    runtime_registration = adapt_urban_area_conversion_runtime_registration_policy()

    generalized_resolution = historical_shadow.get("generalized_resolution")
    if not isinstance(generalized_resolution, Mapping):
        generalized_resolution = {}

    production_condition = adapt_historical_site_event_to_production_contract(
        name=CONDITION_NAME,
        resolver_result=generalized_resolution,
        confidence="MEDIUM",
        source="URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_SHADOW",
        provenance={
            "historical_shadow_mode": historical_shadow.get("shadow_mode"),
            "readiness_adapter_mode": readiness.get("adapter_mode"),
            "provenance_adapter_mode": provenance.get("adapter_mode"),
            "runtime_registration_adapter_mode": runtime_registration.get(
                "adapter_mode"
            ),
            "standard_code_verified": not bool(
                readiness.get("condition_specific_blockers", {}).get(
                    "standard_code_unverified", True
                )
            ),
            "provenance_policy_verified": not bool(
                readiness.get("condition_specific_blockers", {}).get(
                    "provenance_policy_unverified", True
                )
            ),
            "runtime_registration_policy_verified": not bool(
                readiness.get("condition_specific_blockers", {}).get(
                    "runtime_registration_policy_unverified", True
                )
            ),
        },
        production_eligible=False,
        runtime_registered=False,
    )

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "production_condition": production_condition.to_dict(),
        "historical_shadow": historical_shadow,
        "production_readiness": readiness,
        "provenance_policy": provenance,
        "runtime_registration_policy": runtime_registration,
        "promotion_guards": {
            "true_candidate_promoted_to_true": False,
            "unknown_promoted_to_false": False,
            "unknown_promoted_to_true": False,
            "readiness_promoted_to_production_eligibility": False,
            "runtime_policy_promoted_to_actual_registration": False,
            "condition_name_promoted_to_standard_code": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
