"""STEP42 non-executing builder context injection payload for HISTORICAL_SITE_EVENT.

A valid STEP41 authorization is converted into the explicit payload shape for a
future site_analysis_builder site_condition_context injection. Payload readiness
is not injection: this module never modifies/calls the builder, never calls
Rule Engine evaluation, and never overlays or mutates SITE/runtime state.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_builder_context_injection_authorization import (
    BOUNDARY_NAME as AUTHORIZATION_BOUNDARY_NAME,
    TARGET_INJECTION_POINT,
    HistoricalSiteEventBuilderContextInjectionAuthorization,
)


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_BUILDER_CONTEXT_INJECTION_PAYLOAD"


@dataclass(frozen=True)
class HistoricalSiteEventBuilderContextInjectionPayload:
    boundary: str
    target_injection_point: str
    authorization_present: bool
    authorization_boundary_matched: bool
    target_injection_point_matched: bool
    builder_injection_authorized: bool
    authorized_context_present: bool
    authorization_contract_aligned: bool
    missing_gates: tuple[str, ...]
    injection_ready: bool
    site_condition_context_payload: Mapping[str, Mapping[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "target_injection_point": self.target_injection_point,
            "authorization_present": self.authorization_present,
            "authorization_boundary_matched": self.authorization_boundary_matched,
            "target_injection_point_matched": self.target_injection_point_matched,
            "builder_injection_authorized": self.builder_injection_authorized,
            "authorized_context_present": self.authorized_context_present,
            "authorization_contract_aligned": self.authorization_contract_aligned,
            "missing_gates": list(self.missing_gates),
            "injection_ready": self.injection_ready,
            "site_condition_context_payload": {
                name: copy.deepcopy(dict(condition))
                for name, condition in self.site_condition_context_payload.items()
            },
            "builder_argument_supplied": False,
            "site_analysis_builder_modified": False,
            "site_condition_context_injected": False,
            "rule_engine_input_consumed": False,
            "site_registry_overlaid": False,
            "site_state_mutated": False,
            "rule_engine_state_mutated": False,
            "rule_evaluation_executed": False,
            "rule_applicability_changed": False,
            "builder_wiring_applied": False,
            "production_wiring_applied": False,
            "runtime_registered": False,
            "runtime_registry_mutated": False,
            "historical_producer_auto_run": False,
            "public_api_exposed": False,
        }


def prepare_historical_site_event_builder_context_injection_payload(
    authorization: HistoricalSiteEventBuilderContextInjectionAuthorization | None,
) -> HistoricalSiteEventBuilderContextInjectionPayload:
    """Prepare an authorized builder payload without supplying it to the builder."""

    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventBuilderContextInjectionAuthorization,
    )
    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == AUTHORIZATION_BOUNDARY_NAME
    )
    target_injection_point_matched = bool(
        authorization_present
        and authorization.target_injection_point == TARGET_INJECTION_POINT
    )
    builder_injection_authorized = bool(
        authorization_present and authorization.builder_injection_authorized is True
    )
    authorized_context = (
        copy.deepcopy(dict(authorization.authorized_merged_context))
        if authorization_present
        else {}
    )
    authorized_context_present = bool(authorized_context)
    authorization_contract_aligned = bool(
        authorization_present
        and authorization.merge_present is True
        and authorization.merge_boundary_matched is True
        and authorization.merge_ready is True
        and authorization.merged_context_present is True
        and authorization.historical_condition_name_present is True
        and authorization.historical_condition_preserved is True
        and authorization.no_condition_name_collision is True
        and authorization.merge_contract_aligned is True
    )

    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("target_injection_point_matched", target_injection_point_matched),
        ("builder_injection_authorized", builder_injection_authorized),
        ("authorized_context_present", authorized_context_present),
        ("authorization_contract_aligned", authorization_contract_aligned),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    injection_ready = not missing_gates

    return HistoricalSiteEventBuilderContextInjectionPayload(
        boundary=BOUNDARY_NAME,
        target_injection_point=TARGET_INJECTION_POINT,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        target_injection_point_matched=target_injection_point_matched,
        builder_injection_authorized=builder_injection_authorized,
        authorized_context_present=authorized_context_present,
        authorization_contract_aligned=authorization_contract_aligned,
        missing_gates=missing_gates,
        injection_ready=injection_ready,
        site_condition_context_payload=(authorized_context if injection_ready else {}),
    )
