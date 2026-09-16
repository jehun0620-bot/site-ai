"""Adapt a PNU-admitted historical SITE event to the existing rule-input shape.

This boundary does not wire the builder or Rule Engine. It only emits the
already-supported historical input shape when both parcel applicability and
the existing trusted handoff are independently authorized.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from .historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
from .historical_site_event_site_applicability_admission import (
    HistoricalSiteEventSiteApplicabilityAdmissionResult,
)
from .historical_trusted_internal_source_handoff_authorization import (
    BOUNDARY_NAME as HANDOFF_BOUNDARY_NAME,
    HistoricalTrustedInternalSourceHandoffAuthorization,
)

READY = "READY"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventAdmittedRuleInputAdapterResult:
    status: str
    applicability_admitted: bool
    handoff_present: bool
    handoff_boundary_matched: bool
    handoff_authorized: bool
    channel_matched: bool
    provenance_matched: bool
    repairs_valid: bool
    missing_gates: tuple[str, ...]
    historical_rule_input: Mapping[str, Any] | None
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def ready(self) -> bool:
        return (
            self.status == READY
            and not self.missing_gates
            and self.applicability_admitted
            and self.handoff_authorized
            and self.channel_matched
            and self.provenance_matched
            and self.repairs_valid
            and self.historical_rule_input is not None
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def adapt_admitted_historical_site_event_rule_input(
    applicability: HistoricalSiteEventSiteApplicabilityAdmissionResult | None,
    handoff: HistoricalTrustedInternalSourceHandoffAuthorization | None,
) -> HistoricalSiteEventAdmittedRuleInputAdapterResult:
    """Emit existing channel/provenance/repairs input only after both gates pass."""

    applicability_present = isinstance(
        applicability,
        HistoricalSiteEventSiteApplicabilityAdmissionResult,
    )
    applicability_admitted = bool(
        applicability_present and applicability.admitted
    )

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
    channel_matched = bool(
        handoff_present and handoff.channel == CHANNEL
    )
    provenance_matched = bool(
        handoff_present and handoff.provenance == PROVENANCE
    )

    repairs = copy.deepcopy(tuple(handoff.handoff_repairs)) if handoff_present else ()
    repairs_valid = bool(
        handoff_present
        and isinstance(handoff.handoff_repairs, tuple)
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

    gates = (
        ("applicability_admitted", applicability_admitted),
        ("handoff_present", handoff_present),
        ("handoff_boundary_matched", handoff_boundary_matched),
        ("handoff_authorized", handoff_authorized),
        ("channel_matched", channel_matched),
        ("provenance_matched", provenance_matched),
        ("repairs_valid", repairs_valid),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    if applicability_present and applicability.status == UNKNOWN:
        status = UNKNOWN
    elif missing_gates:
        status = REJECTED
    else:
        status = READY

    historical_rule_input = None
    if status == READY:
        historical_rule_input = {
            "channel": CHANNEL,
            "provenance": PROVENANCE,
            "repairs": copy.deepcopy(list(repairs)),
        }

    return HistoricalSiteEventAdmittedRuleInputAdapterResult(
        status=status,
        applicability_admitted=applicability_admitted,
        handoff_present=handoff_present,
        handoff_boundary_matched=handoff_boundary_matched,
        handoff_authorized=handoff_authorized,
        channel_matched=channel_matched,
        provenance_matched=provenance_matched,
        repairs_valid=repairs_valid,
        missing_gates=missing_gates,
        historical_rule_input=historical_rule_input,
    )
