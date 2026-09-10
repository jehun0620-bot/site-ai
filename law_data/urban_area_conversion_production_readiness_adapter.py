from __future__ import annotations

from law_data.historical_site_event_production_readiness_gate import (
    HistoricalSiteEventProductionReadinessEvidence,
    evaluate_historical_site_event_production_readiness,
)
from law_data.regulation_resolution_profile_registry import (
    get_regulation_resolution_profile,
)


CONDITION_NAME = "도시지역편입해제구역"
ADAPTER_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


def adapt_urban_area_conversion_production_readiness() -> dict[str, object]:
    """Map current condition-level readiness into the common production gate.

    Contract readiness means the safety/verifier path exists and is semantically
    aligned. It does not mean the condition's current historical evidence satisfies
    the TRUE or FALSE legal-resolution gates.

    Condition identity and standard-code verification are read from the immutable
    regulation-resolution profile registry. Missing profile metadata fails closed;
    this adapter never derives or guesses a standard code from the condition name.

    Current condition status:
    - condition identity has an exact-name built-in profile;
    - exact standard code is still unverified and must not be guessed;
    - positive-evidence and history-completeness contracts are implemented;
    - condition-specific provenance policy is not yet positively verified;
    - runtime registration policy is not yet positively verified.

    The adapter is pure/read-only and performs no production mutation.
    """

    profile = get_regulation_resolution_profile(CONDITION_NAME)
    condition_identity_verified = (
        profile is not None and profile.name == CONDITION_NAME
    )
    standard_code_verified = (
        profile.standard_code_verified is True if profile is not None else False
    )

    evidence = HistoricalSiteEventProductionReadinessEvidence(
        condition_identity_verified=condition_identity_verified,
        standard_code_verified=standard_code_verified,
        positive_evidence_contract_ready=True,
        history_completeness_contract_ready=True,
        provenance_policy_verified=False,
        runtime_registration_policy_verified=False,
    )

    readiness = evaluate_historical_site_event_production_readiness(evidence)

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "resolution_profile": (
            profile.to_dict() if profile is not None else None
        ),
        "semantic_contract": {
            "contract_ready_means_implementation_ready_not_evidence_satisfied": True,
            "profile_lookup_is_identity_metadata_not_evidence_verification": True,
            "profile_missing_fails_closed": True,
            "positive_evidence_contract_ready": True,
            "actual_verified_qualifying_event_present": False,
            "history_completeness_contract_ready": True,
            "actual_history_scope_complete_verified": False,
        },
        "readiness": readiness,
        "condition_specific_blockers": {
            "profile_missing": profile is None,
            "standard_code_unverified": not standard_code_verified,
            "provenance_policy_unverified": True,
            "runtime_registration_policy_unverified": True,
        },
        "promotion_guards": {
            "condition_name_promoted_to_standard_code": False,
            "profile_presence_promoted_to_evidence_satisfaction": False,
            "contract_readiness_promoted_to_evidence_satisfaction": False,
            "current_unknown_resolution_promoted_to_runtime_registration": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
