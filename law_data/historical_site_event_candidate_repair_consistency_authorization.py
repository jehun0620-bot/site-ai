"""Fail-closed consistency authorization between an admitted SITE candidate and handoff repairs.

This boundary does not wire the orchestrator, builder, Rule Engine, SITE truth,
or runtime registration. It only proves that a PNU-admitted historical SITE
candidate is not contradicted by the trusted handoff repair set.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .historical_site_event_builder_injection_payload import PROVENANCE
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
BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_CANDIDATE_REPAIR_CONSISTENCY_AUTHORIZATION"


@dataclass(frozen=True)
class HistoricalSiteEventCandidateRepairConsistencyAuthorization:
    boundary: str
    status: str
    applicability_admitted: bool
    candidate_present: bool
    expected_state: str
    handoff_present: bool
    handoff_boundary_matched: bool
    handoff_authorized: bool
    repairs_present: bool
    repairs_valid: bool
    matching_repair_count: int
    contradictory_repair_count: int
    missing_gates: tuple[str, ...]
    consistency_authorized: bool
    authorized_repairs: tuple[Mapping[str, Any], ...]
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return (
            self.status == AUTHORIZED
            and self.consistency_authorized
            and not self.missing_gates
            and self.matching_repair_count >= 1
            and self.contradictory_repair_count == 0
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "missing_gates": list(self.missing_gates),
            "authorized_repairs": copy.deepcopy(list(self.authorized_repairs)),
        }


def _candidate_to_state(candidate: bool | None) -> str:
    if candidate is True:
        return "TRUE"
    if candidate is False:
        return "FALSE"
    return ""


def authorize_historical_site_event_candidate_repair_consistency(
    applicability: HistoricalSiteEventSiteApplicabilityAdmissionResult | None,
    handoff: HistoricalTrustedInternalSourceHandoffAuthorization | None,
) -> HistoricalSiteEventCandidateRepairConsistencyAuthorization:
    """Authorize only when the trusted repair set contains no candidate contradiction."""

    applicability_present = isinstance(
        applicability,
        HistoricalSiteEventSiteApplicabilityAdmissionResult,
    )
    applicability_admitted = bool(
        applicability_present and applicability.admitted
    )
    candidate = (
        applicability.candidate_site_decision
        if applicability_present and applicability_admitted
        else None
    )
    expected_state = _candidate_to_state(candidate)
    candidate_present = bool(expected_state)

    handoff_present = isinstance(
        handoff,
        HistoricalTrustedInternalSourceHandoffAuthorization,
    )
    handoff_boundary_matched = bool(
        handoff_present and handoff.boundary == HANDOFF_BOUNDARY_NAME
    )
    handoff_authorized = bool(
        handoff_present and handoff.handoff_authorized is True
    )
    repairs = copy.deepcopy(tuple(handoff.handoff_repairs)) if handoff_present else ()
    repairs_present = bool(
        handoff_present
        and isinstance(handoff.handoff_repairs, tuple)
        and len(repairs) >= 1
    )
    repairs_valid = bool(
        repairs_present
        and all(
            isinstance(repair, Mapping)
            and isinstance(repair.get("condition"), str)
            and bool(repair.get("condition").strip())
            and repair.get("after") in {"TRUE", "FALSE", "UNKNOWN", "UNSET"}
            and isinstance(repair.get("new_confidence"), str)
            and bool(repair.get("new_confidence").strip())
            and repair.get("new_source") == PROVENANCE
            for repair in repairs
        )
    )

    matching = 0
    contradictory = 0
    if candidate_present and repairs_valid:
        for repair in repairs:
            state = repair.get("after")
            if state == expected_state:
                matching += 1
            else:
                contradictory += 1

    gates = (
        ("applicability_admitted", applicability_admitted),
        ("candidate_present", candidate_present),
        ("handoff_present", handoff_present),
        ("handoff_boundary_matched", handoff_boundary_matched),
        ("handoff_authorized", handoff_authorized),
        ("repairs_present", repairs_present),
        ("repairs_valid", repairs_valid),
        ("candidate_matching_repair_present", matching >= 1),
        ("no_candidate_contradictory_repairs", contradictory == 0),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    if applicability_present and applicability.status == UNKNOWN:
        status = UNKNOWN
    elif missing_gates:
        status = REJECTED
    else:
        status = AUTHORIZED

    consistency_authorized = status == AUTHORIZED
    return HistoricalSiteEventCandidateRepairConsistencyAuthorization(
        boundary=BOUNDARY_NAME,
        status=status,
        applicability_admitted=applicability_admitted,
        candidate_present=candidate_present,
        expected_state=expected_state,
        handoff_present=handoff_present,
        handoff_boundary_matched=handoff_boundary_matched,
        handoff_authorized=handoff_authorized,
        repairs_present=repairs_present,
        repairs_valid=repairs_valid,
        matching_repair_count=matching,
        contradictory_repair_count=contradictory,
        missing_gates=missing_gates,
        consistency_authorized=consistency_authorized,
        authorized_repairs=repairs if consistency_authorized else (),
    )
