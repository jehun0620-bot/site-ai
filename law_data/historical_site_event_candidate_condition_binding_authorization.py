"""Fail-closed binding between an admitted historical SITE candidate and one condition identity.

This boundary only proves that the trusted handoff repairs point to one unique
condition and binds that identity to the already PNU-admitted candidate. It
does not wire production, mutate SITE truth, or register runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .historical_site_event_site_applicability_admission import (
    HistoricalSiteEventSiteApplicabilityAdmissionResult,
)
from .historical_trusted_internal_source_handoff_authorization import (
    BOUNDARY_NAME as HANDOFF_BOUNDARY_NAME,
    HistoricalTrustedInternalSourceHandoffAuthorization,
)

AUTHORIZED = "AUTHORIZED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"
BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_CANDIDATE_CONDITION_BINDING_AUTHORIZATION"


@dataclass(frozen=True)
class HistoricalSiteEventCandidateConditionBindingAuthorization:
    boundary: str
    status: str
    applicability_admitted: bool
    candidate_present: bool
    handoff_present: bool
    handoff_boundary_matched: bool
    handoff_authorized: bool
    repairs_present: bool
    repair_conditions_valid: bool
    unique_condition_count: int
    condition_identity_unambiguous: bool
    bound_condition: str
    missing_gates: tuple[str, ...]
    binding_authorized: bool
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return (
            self.status == AUTHORIZED
            and self.binding_authorized
            and self.applicability_admitted
            and self.candidate_present
            and self.condition_identity_unambiguous
            and bool(self.bound_condition)
            and not self.missing_gates
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "missing_gates": list(self.missing_gates)}


def authorize_historical_site_event_candidate_condition_binding(
    applicability: HistoricalSiteEventSiteApplicabilityAdmissionResult | None,
    handoff: HistoricalTrustedInternalSourceHandoffAuthorization | None,
) -> HistoricalSiteEventCandidateConditionBindingAuthorization:
    applicability_present = isinstance(
        applicability,
        HistoricalSiteEventSiteApplicabilityAdmissionResult,
    )
    applicability_admitted = bool(applicability_present and applicability.admitted)
    candidate_present = bool(
        applicability_admitted
        and isinstance(applicability.candidate_site_decision, bool)
    )

    handoff_present = isinstance(
        handoff,
        HistoricalTrustedInternalSourceHandoffAuthorization,
    )
    handoff_boundary_matched = bool(
        handoff_present and handoff.boundary == HANDOFF_BOUNDARY_NAME
    )
    handoff_authorized = bool(handoff_present and handoff.handoff_authorized is True)
    repairs = tuple(handoff.handoff_repairs) if handoff_present else ()
    repairs_present = bool(repairs)

    repair_conditions_valid = bool(
        repairs_present
        and all(
            isinstance(repair, Mapping)
            and isinstance(repair.get("condition"), str)
            and bool(repair.get("condition").strip())
            for repair in repairs
        )
    )
    unique_conditions = (
        {repair["condition"].strip() for repair in repairs}
        if repair_conditions_valid
        else set()
    )
    unique_condition_count = len(unique_conditions)
    condition_identity_unambiguous = unique_condition_count == 1
    bound_condition = (
        next(iter(unique_conditions)) if condition_identity_unambiguous else ""
    )

    gates = (
        ("applicability_admitted", applicability_admitted),
        ("candidate_present", candidate_present),
        ("handoff_present", handoff_present),
        ("handoff_boundary_matched", handoff_boundary_matched),
        ("handoff_authorized", handoff_authorized),
        ("repairs_present", repairs_present),
        ("repair_conditions_valid", repair_conditions_valid),
        ("condition_identity_unambiguous", condition_identity_unambiguous),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    if applicability_present and applicability.status == UNKNOWN:
        status = UNKNOWN
    elif missing_gates:
        status = REJECTED
    else:
        status = AUTHORIZED

    return HistoricalSiteEventCandidateConditionBindingAuthorization(
        boundary=BOUNDARY_NAME,
        status=status,
        applicability_admitted=applicability_admitted,
        candidate_present=candidate_present,
        handoff_present=handoff_present,
        handoff_boundary_matched=handoff_boundary_matched,
        handoff_authorized=handoff_authorized,
        repairs_present=repairs_present,
        repair_conditions_valid=repair_conditions_valid,
        unique_condition_count=unique_condition_count,
        condition_identity_unambiguous=condition_identity_unambiguous,
        bound_condition=bound_condition,
        missing_gates=missing_gates,
        binding_authorized=status == AUTHORIZED,
    )
