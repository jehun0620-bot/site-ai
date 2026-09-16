"""Isolated executor for an authorized historical SITE-truth promotion candidate.

Easy model: the authorization is the permit; this executor prepares the exact
SITE-registry condition that a future wiring step may consume. It does not
write a global registry, call the Rule Engine, modify the builder, register
runtime state, or expose anything through the API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_site_truth_promotion_authorization import (
    AUTHORIZED as PROMOTION_AUTHORIZED,
    BOUNDARY_NAME as PROMOTION_AUTHORIZATION_BOUNDARY_NAME,
    HistoricalSiteEventSiteTruthPromotionAuthorization,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_EXECUTOR"
EXECUTED = "EXECUTED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"
HISTORICAL_CONDITION_TYPE = "SITE"
HISTORICAL_REGISTRY_SOURCE = "RUNTIME_HISTORICAL_SITE_EVENT"


@dataclass(frozen=True)
class HistoricalSiteEventSiteTruthPromotionExecution:
    boundary: str
    status: str
    authorization_present: bool
    authorization_boundary_matched: bool
    promotion_authorized: bool
    bound_pnu: str
    bound_condition: str
    bound_state: str
    promoted_condition_present: bool
    promoted_condition: Mapping[str, Any]
    missing_gates: tuple[str, ...]
    execution_succeeded: bool
    site_registry_mutated: bool = False
    rule_engine_called: bool = False
    builder_modified: bool = False
    runtime_registered: bool = False
    public_api_exposed: bool = False

    @property
    def executed(self) -> bool:
        return bool(
            self.status == EXECUTED
            and self.execution_succeeded
            and self.promotion_authorized
            and self.bound_pnu
            and self.bound_condition
            and self.bound_state
            and self.promoted_condition_present
            and self.promoted_condition
            and not self.missing_gates
            and not self.site_registry_mutated
            and not self.rule_engine_called
            and not self.builder_modified
            and not self.runtime_registered
            and not self.public_api_exposed
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.__dict__,
            "promoted_condition": dict(self.promoted_condition),
            "missing_gates": list(self.missing_gates),
            "executed": self.executed,
        }


def execute_historical_site_event_site_truth_promotion(
    authorization: HistoricalSiteEventSiteTruthPromotionAuthorization | None,
) -> HistoricalSiteEventSiteTruthPromotionExecution:
    authorization_present = isinstance(
        authorization,
        HistoricalSiteEventSiteTruthPromotionAuthorization,
    )
    authorization_boundary_matched = bool(
        authorization_present and authorization.boundary == PROMOTION_AUTHORIZATION_BOUNDARY_NAME
    )
    promotion_authorized = bool(
        authorization_present
        and authorization.status == PROMOTION_AUTHORIZED
        and authorization.authorized
    )
    bound_pnu = str(authorization.bound_pnu or "").strip() if authorization_present else ""
    bound_condition = str(authorization.bound_condition or "").strip() if authorization_present else ""
    bound_state = str(authorization.bound_state or "").strip().upper() if authorization_present else ""
    pnu_valid = len(bound_pnu) == 19 and bound_pnu.isdigit()
    state_valid = bound_state in {"TRUE", "FALSE"}

    gates = (
        ("authorization_present", authorization_present),
        ("authorization_boundary_matched", authorization_boundary_matched),
        ("promotion_authorized", promotion_authorized),
        ("bound_pnu_valid", pnu_valid),
        ("bound_condition_present", bool(bound_condition)),
        ("bound_state_valid", state_valid),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    upstream_unknown = bool(authorization_present and authorization.status == UNKNOWN)
    status = UNKNOWN if upstream_unknown else (REJECTED if missing_gates else EXECUTED)
    succeeded = status == EXECUTED

    promoted_condition: Mapping[str, Any] = {}
    if succeeded:
        promoted_condition = {
            "type": HISTORICAL_CONDITION_TYPE,
            "state": bound_state,
            "confidence": "HIGH",
            "source": HISTORICAL_REGISTRY_SOURCE,
            "runtime": True,
            "pnu": bound_pnu,
            "historical": True,
            "promotion_authorization_boundary": authorization.boundary,
            "promotion_executor_boundary": BOUNDARY_NAME,
        }

    return HistoricalSiteEventSiteTruthPromotionExecution(
        boundary=BOUNDARY_NAME,
        status=status,
        authorization_present=authorization_present,
        authorization_boundary_matched=authorization_boundary_matched,
        promotion_authorized=promotion_authorized,
        bound_pnu=bound_pnu,
        bound_condition=bound_condition,
        bound_state=bound_state,
        promoted_condition_present=bool(promoted_condition),
        promoted_condition=promoted_condition,
        missing_gates=missing_gates,
        execution_succeeded=succeeded,
    )
