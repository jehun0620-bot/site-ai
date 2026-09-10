from __future__ import annotations

from law_data.historical_site_event_resolver import RESOLUTION_TYPE, UNKNOWN
from law_data.historical_site_event_runtime_registration_policy import (
    HistoricalSiteEventRuntimeRegistrationEvidence,
    evaluate_historical_site_event_runtime_registration_policy,
)


CONDITION_NAME = "도시지역편입해제구역"
ADAPTER_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


def adapt_urban_area_conversion_runtime_registration_policy() -> dict[str, object]:
    """Bind the current condition state to the common runtime registration policy.

    This adapter is deliberately conservative. The condition currently remains
    UNKNOWN, its exact standard code is unverified, provenance policy is unverified,
    and production wiring is not ready. Therefore registration eligibility must
    remain blocked.

    The adapter performs no SITE promotion, overlay mutation, production wiring, or
    runtime registry mutation.
    """

    evidence = HistoricalSiteEventRuntimeRegistrationEvidence(
        production_wiring_ready=False,
        standard_code_verified=False,
        provenance_policy_verified=False,
        resolver_type=RESOLUTION_TYPE,
        resolution=UNKNOWN,
    )

    policy = evaluate_historical_site_event_runtime_registration_policy(evidence)

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "resolver_type": RESOLUTION_TYPE,
        "current_resolution": UNKNOWN,
        "runtime_registration_policy": policy,
        "condition_specific_blockers": {
            "standard_code_unverified": True,
            "provenance_policy_unverified": True,
            "production_wiring_not_ready": True,
        },
        "promotion_guards": {
            "condition_name_promoted_to_standard_code": False,
            "unknown_promoted_to_site_false": False,
            "unknown_promoted_to_site_true": False,
            "policy_eligibility_promoted_to_actual_registration": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
