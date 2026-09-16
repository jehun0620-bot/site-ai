"""Fail-closed pre-promotion binding for HISTORICAL_SITE_EVENT.

This boundary does not promote SITE truth. It only proves that the current
PNU-bound admitted candidate, its trusted condition binding, and an already
committed historical SITE-registry condition describe the same candidate state
and condition identity.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_candidate_condition_binding_authorization import (
    BOUNDARY_NAME as CONDITION_BINDING_BOUNDARY_NAME,
    HistoricalSiteEventCandidateConditionBindingAuthorization,
)
from law_data.historical_site_event_candidate_repair_consistency_authorization import (
    BOUNDARY_NAME as CONSISTENCY_BOUNDARY_NAME,
    HistoricalSiteEventCandidateRepairConsistencyAuthorization,
)
from law_data.historical_site_event_site_applicability_admission import (
    ADMITTED,
    HistoricalSiteEventSiteApplicabilityAdmissionResult,
)
from law_data.historical_site_event_site_registry_mutation_executor import (
    BOUNDARY_NAME as MUTATION_EXECUTION_BOUNDARY_NAME,
    HistoricalSiteEventSiteRegistryMutationExecution,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    HISTORICAL_CONDITION_TYPE,
    HISTORICAL_REGISTRY_SOURCE,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_BINDING_AUTHORIZATION"
AUTHORIZED = "AUTHORIZED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"


def _candidate_state(value: bool | None) -> str:
    if value is True:
        return "TRUE"
    if value is False:
        return "FALSE"
    return ""


@dataclass(frozen=True)
class HistoricalSiteEventSiteTruthPromotionBindingAuthorization:
    boundary: str
    status: str
    applicability_admitted: bool
    canonical_pnu: str
    candidate_present: bool
    candidate_state: str
    consistency_present: bool
    consistency_boundary_matched: bool
    consistency_authorized: bool
    condition_binding_present: bool
    condition_binding_boundary_matched: bool
    condition_binding_authorized: bool
    bound_condition: str
    mutation_execution_present: bool
    mutation_execution_boundary_matched: bool
    mutation_executed: bool
    committed_condition_name: str
    condition_identity_matched: bool
    committed_condition_present: bool
    committed_state: str
    state_matched: bool
    historical_type_preserved: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    missing_gates: tuple[str, ...]
    promotion_binding_authorized: bool
    site_truth_decision_allowed: bool = False
    site_truth_mutation_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return bool(
            self.status == AUTHORIZED
            and self.promotion_binding_authorized
            and self.applicability_admitted
            and self.canonical_pnu
            and self.candidate_present
            and self.candidate_state
            and self.consistency_authorized
            and self.condition_binding_authorized
            and self.bound_condition
            and self.mutation_executed
            and self.condition_identity_matched
            and self.state_matched
            and self.historical_type_preserved
            and self.registry_source_matched
            and self.original_historical_source_preserved
            and not self.missing_gates
            and not self.site_truth_decision_allowed
            and not self.site_truth_mutation_allowed
            and not self.site_promotion_allowed
            and not self.production_registration_allowed
            and not self.runtime_registration_allowed
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "missing_gates": list(self.missing_gates), "authorized": self.authorized}


def authorize_historical_site_event_site_truth_promotion_binding(
    applicability: HistoricalSiteEventSiteApplicabilityAdmissionResult | None,
    consistency: HistoricalSiteEventCandidateRepairConsistencyAuthorization | None,
    condition_binding: HistoricalSiteEventCandidateConditionBindingAuthorization | None,
    mutation_execution: HistoricalSiteEventSiteRegistryMutationExecution | None,
) -> HistoricalSiteEventSiteTruthPromotionBindingAuthorization:
    applicability_present = isinstance(applicability, HistoricalSiteEventSiteApplicabilityAdmissionResult)
    applicability_admitted = bool(applicability_present and applicability.admitted)
    canonical_pnu = ""
    if applicability_present and applicability.site_admission is not None:
        canonical_pnu = str(applicability.site_admission.canonical_pnu or "").strip()
    candidate = applicability.candidate_site_decision if applicability_present else None
    candidate_present = isinstance(candidate, bool)
    candidate_state = _candidate_state(candidate)

    consistency_present = isinstance(consistency, HistoricalSiteEventCandidateRepairConsistencyAuthorization)
    consistency_boundary_matched = bool(consistency_present and consistency.boundary == CONSISTENCY_BOUNDARY_NAME)
    consistency_authorized = bool(consistency_present and consistency.authorized)

    condition_binding_present = isinstance(condition_binding, HistoricalSiteEventCandidateConditionBindingAuthorization)
    condition_binding_boundary_matched = bool(
        condition_binding_present and condition_binding.boundary == CONDITION_BINDING_BOUNDARY_NAME
    )
    condition_binding_authorized = bool(condition_binding_present and condition_binding.authorized)
    bound_condition = str(condition_binding.bound_condition or "").strip() if condition_binding_present else ""

    mutation_execution_present = isinstance(mutation_execution, HistoricalSiteEventSiteRegistryMutationExecution)
    mutation_execution_boundary_matched = bool(
        mutation_execution_present and mutation_execution.boundary == MUTATION_EXECUTION_BOUNDARY_NAME
    )
    mutation_executed = bool(mutation_execution_present and mutation_execution.mutation_executed is True)
    committed_condition_name = (
        str(mutation_execution.committed_historical_condition_name or "").strip()
        if mutation_execution_present else ""
    )
    condition_identity_matched = bool(bound_condition and committed_condition_name == bound_condition)
    committed_condition: Mapping[str, Any] = (
        mutation_execution.committed_historical_condition
        if mutation_execution_present and isinstance(mutation_execution.committed_historical_condition, Mapping)
        else {}
    )
    committed_condition_present = bool(committed_condition)
    committed_state = str(committed_condition.get("state") or "").strip().upper()
    state_matched = bool(candidate_state and committed_state == candidate_state)
    historical_type_preserved = str(committed_condition.get("type") or "").strip() == HISTORICAL_CONDITION_TYPE
    registry_source_matched = str(committed_condition.get("source") or "").strip() == HISTORICAL_REGISTRY_SOURCE
    historical_source = committed_condition.get("historical_source")
    runtime_source = committed_condition.get("runtime_source")
    original_historical_source_preserved = bool(
        str(historical_source or "").strip() and historical_source == runtime_source
    )

    gates = (
        ("applicability_admitted", applicability_admitted),
        ("canonical_pnu_present", bool(canonical_pnu)),
        ("candidate_present", candidate_present),
        ("consistency_present", consistency_present),
        ("consistency_boundary_matched", consistency_boundary_matched),
        ("consistency_authorized", consistency_authorized),
        ("condition_binding_present", condition_binding_present),
        ("condition_binding_boundary_matched", condition_binding_boundary_matched),
        ("condition_binding_authorized", condition_binding_authorized),
        ("bound_condition_present", bool(bound_condition)),
        ("mutation_execution_present", mutation_execution_present),
        ("mutation_execution_boundary_matched", mutation_execution_boundary_matched),
        ("mutation_executed", mutation_executed),
        ("committed_condition_present", committed_condition_present),
        ("condition_identity_matched", condition_identity_matched),
        ("state_matched", state_matched),
        ("historical_type_preserved", historical_type_preserved),
        ("registry_source_matched", registry_source_matched),
        ("original_historical_source_preserved", original_historical_source_preserved),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    unknown_input = bool(applicability_present and applicability.status == UNKNOWN)
    status = UNKNOWN if unknown_input else (REJECTED if missing_gates else AUTHORIZED)
    authorized = status == AUTHORIZED

    return HistoricalSiteEventSiteTruthPromotionBindingAuthorization(
        boundary=BOUNDARY_NAME,
        status=status,
        applicability_admitted=applicability_admitted,
        canonical_pnu=canonical_pnu,
        candidate_present=candidate_present,
        candidate_state=candidate_state,
        consistency_present=consistency_present,
        consistency_boundary_matched=consistency_boundary_matched,
        consistency_authorized=consistency_authorized,
        condition_binding_present=condition_binding_present,
        condition_binding_boundary_matched=condition_binding_boundary_matched,
        condition_binding_authorized=condition_binding_authorized,
        bound_condition=bound_condition,
        mutation_execution_present=mutation_execution_present,
        mutation_execution_boundary_matched=mutation_execution_boundary_matched,
        mutation_executed=mutation_executed,
        committed_condition_name=committed_condition_name,
        condition_identity_matched=condition_identity_matched,
        committed_condition_present=committed_condition_present,
        committed_state=committed_state,
        state_matched=state_matched,
        historical_type_preserved=historical_type_preserved,
        registry_source_matched=registry_source_matched,
        original_historical_source_preserved=original_historical_source_preserved,
        missing_gates=missing_gates,
        promotion_binding_authorized=authorized,
    )
