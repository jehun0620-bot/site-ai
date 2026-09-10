from __future__ import annotations

from dataclasses import dataclass

from law_data.historical_site_event_resolver import (
    FALSE,
    RESOLUTION_TYPE,
    TRUE_CANDIDATE,
    UNKNOWN,
)


POLICY_NAME = "HISTORICAL_SITE_EVENT_RUNTIME_REGISTRATION_POLICY"
ALLOWED_RESOLUTIONS = frozenset({TRUE_CANDIDATE, FALSE, UNKNOWN})


@dataclass(frozen=True)
class HistoricalSiteEventRuntimeRegistrationEvidence:
    """Positive-proof-only inputs for HISTORICAL_SITE_EVENT registration eligibility.

    This policy evaluates whether registration could be eligible. It never mutates a
    runtime registry, SITE state, overlay, or legal resolution.
    """

    production_wiring_ready: bool = False
    standard_code_verified: bool = False
    provenance_policy_verified: bool = False
    resolver_type: str = ""
    resolution: str = UNKNOWN

    @property
    def registration_eligible(self) -> bool:
        return (
            self.production_wiring_ready
            and self.standard_code_verified
            and self.provenance_policy_verified
            and self.resolver_type == RESOLUTION_TYPE
            and self.resolution in ALLOWED_RESOLUTIONS
        )


def evaluate_historical_site_event_runtime_registration_policy(
    evidence: HistoricalSiteEventRuntimeRegistrationEvidence,
) -> dict[str, object]:
    """Evaluate runtime registration eligibility without applying registration.

    UNKNOWN and TRUE_CANDIDATE are legitimate historical resolver states, but neither
    may be promoted to SITE TRUE/FALSE by this policy. FALSE is also accepted only as
    a resolver state; this policy does not infer or manufacture exhaustive disproof.
    """

    gates = {
        "production_wiring_ready": evidence.production_wiring_ready,
        "standard_code_verified": evidence.standard_code_verified,
        "provenance_policy_verified": evidence.provenance_policy_verified,
        "resolver_type_verified": evidence.resolver_type == RESOLUTION_TYPE,
        "resolution_supported": evidence.resolution in ALLOWED_RESOLUTIONS,
    }
    missing_gates = [name for name, passed in gates.items() if not passed]
    eligible = evidence.registration_eligible

    return {
        "policy": POLICY_NAME,
        "resolver_type": evidence.resolver_type,
        "resolution": evidence.resolution,
        "allowed_resolutions": sorted(ALLOWED_RESOLUTIONS),
        "gates": gates,
        "missing_gates": missing_gates,
        "registration_eligible": eligible,
        "registration_state": "ELIGIBLE" if eligible else "BLOCKED",
        "resolution_semantics": {
            "unknown_is_registered_as_site_false": False,
            "unknown_is_registered_as_site_true": False,
            "true_candidate_is_registered_as_site_true": False,
            "true_candidate_is_registered_as_site_false": False,
            "false_is_inferred_from_registration_policy": False,
        },
        "negative_evidence_inference_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
        "production_wiring_applied": False,
    }
