from __future__ import annotations

from dataclasses import dataclass


READINESS_CONTRACT = "HISTORICAL_SITE_EVENT_PRODUCTION_READINESS"


@dataclass(frozen=True)
class HistoricalSiteEventProductionReadinessEvidence:
    """Positive-proof-only readiness inputs for HISTORICAL_SITE_EVENT wiring.

    False means only "not positively verified". Missing or false evidence must never
    be interpreted as permission to wire production, mutate SITE overlays, or register
    runtime behavior.
    """

    condition_identity_verified: bool = False
    standard_code_verified: bool = False
    positive_evidence_contract_ready: bool = False
    history_completeness_contract_ready: bool = False
    provenance_policy_verified: bool = False
    runtime_registration_policy_verified: bool = False

    @property
    def production_wiring_ready(self) -> bool:
        return (
            self.condition_identity_verified
            and self.standard_code_verified
            and self.positive_evidence_contract_ready
            and self.history_completeness_contract_ready
            and self.provenance_policy_verified
            and self.runtime_registration_policy_verified
        )


def evaluate_historical_site_event_production_readiness(
    evidence: HistoricalSiteEventProductionReadinessEvidence,
) -> dict[str, object]:
    """Evaluate readiness without performing any production mutation.

    This is a pure gate. It does not write files, register a resolver, mutate SITE
    state, alter overlays, or infer missing identity/standard-code/policy evidence.
    """

    gates = {
        "condition_identity_verified": evidence.condition_identity_verified,
        "standard_code_verified": evidence.standard_code_verified,
        "positive_evidence_contract_ready": evidence.positive_evidence_contract_ready,
        "history_completeness_contract_ready": (
            evidence.history_completeness_contract_ready
        ),
        "provenance_policy_verified": evidence.provenance_policy_verified,
        "runtime_registration_policy_verified": (
            evidence.runtime_registration_policy_verified
        ),
    }
    missing_gates = [name for name, verified in gates.items() if not verified]
    ready = evidence.production_wiring_ready

    return {
        "readiness_contract": READINESS_CONTRACT,
        "gates": gates,
        "verified_gate_count": sum(1 for verified in gates.values() if verified),
        "required_gate_count": len(gates),
        "missing_gates": missing_gates,
        "production_wiring_ready": ready,
        "readiness_state": "READY" if ready else "BLOCKED",
        "promotion_guards": {
            "condition_name_promoted_to_verified_identity": False,
            "unverified_standard_code_promoted": False,
            "candidate_evidence_promoted_to_positive_contract_ready": False,
            "search_or_database_coverage_promoted_to_completeness_ready": False,
            "missing_provenance_promoted_to_verified": False,
            "missing_runtime_policy_promoted_to_verified": False,
        },
        "negative_evidence_inference_allowed": False,
        "legal_absence_inference_allowed": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
