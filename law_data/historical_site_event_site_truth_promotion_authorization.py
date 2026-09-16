"""Final non-executing authority gate for historical SITE-truth promotion.

Think of this as the final permit check before a future promotion executor.
It does not change SITE truth, mutate a registry, register runtime state, or
expose anything through the public API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_production_integration_authorization import (
    BOUNDARY_NAME as PRODUCTION_AUTHORIZATION_BOUNDARY_NAME,
    HistoricalSiteEventProductionIntegrationAuthorization,
)
from law_data.historical_site_event_site_truth_promotion_pnu_binding_authorization import (
    AUTHORIZED as PNU_BINDING_AUTHORIZED,
    BOUNDARY_NAME as PNU_BINDING_BOUNDARY_NAME,
    HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_AUTHORIZATION"
AUTHORIZED = "AUTHORIZED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"
HISTORICAL_SOURCE = "RUNTIME_HISTORICAL_SITE_EVENT"


@dataclass(frozen=True)
class HistoricalSiteEventSiteTruthPromotionAuthorization:
    boundary: str
    status: str
    pnu_binding_present: bool
    pnu_binding_boundary_matched: bool
    pnu_binding_authorized: bool
    bound_pnu: str
    bound_condition: str
    bound_state: str
    production_authorization_present: bool
    production_authorization_boundary_matched: bool
    production_integration_authorized: bool
    production_repairs_present: bool
    production_condition_matched: bool
    production_state_matched: bool
    production_provenance_preserved: bool
    missing_gates: tuple[str, ...]
    promotion_authorized: bool
    site_truth_decision_allowed: bool = False
    site_truth_mutation_allowed: bool = False
    promotion_execution_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False
    public_api_exposure_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return bool(
            self.status == AUTHORIZED
            and self.promotion_authorized
            and self.pnu_binding_authorized
            and self.bound_pnu
            and self.bound_condition
            and self.bound_state
            and self.production_integration_authorized
            and self.production_repairs_present
            and self.production_condition_matched
            and self.production_state_matched
            and self.production_provenance_preserved
            and not self.missing_gates
            and not self.site_truth_decision_allowed
            and not self.site_truth_mutation_allowed
            and not self.promotion_execution_allowed
            and not self.production_registration_allowed
            and not self.runtime_registration_allowed
            and not self.public_api_exposure_allowed
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "missing_gates": list(self.missing_gates), "authorized": self.authorized}


def authorize_historical_site_event_site_truth_promotion(
    pnu_binding: HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization | None,
    production_authorization: HistoricalSiteEventProductionIntegrationAuthorization | None,
) -> HistoricalSiteEventSiteTruthPromotionAuthorization:
    pnu_binding_present = isinstance(pnu_binding, HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization)
    pnu_binding_boundary_matched = bool(pnu_binding_present and pnu_binding.boundary == PNU_BINDING_BOUNDARY_NAME)
    pnu_binding_authorized = bool(
        pnu_binding_present and pnu_binding.status == PNU_BINDING_AUTHORIZED and pnu_binding.authorized
    )
    bound_pnu = str(pnu_binding.bound_pnu or "").strip() if pnu_binding_present else ""
    bound_condition = str(pnu_binding.bound_condition or "").strip() if pnu_binding_present else ""
    bound_state = str(pnu_binding.bound_state or "").strip().upper() if pnu_binding_present else ""

    production_authorization_present = isinstance(
        production_authorization,
        HistoricalSiteEventProductionIntegrationAuthorization,
    )
    production_authorization_boundary_matched = bool(
        production_authorization_present
        and production_authorization.boundary == PRODUCTION_AUTHORIZATION_BOUNDARY_NAME
    )
    production_integration_authorized = bool(
        production_authorization_present and production_authorization.production_integration_authorized is True
    )
    repairs = production_authorization.authorized_repairs if production_authorization_present else ()
    production_repairs_present = bool(repairs)

    valid_repairs = [repair for repair in repairs if isinstance(repair, Mapping)]
    production_condition_matched = bool(
        production_repairs_present
        and len(valid_repairs) == len(repairs)
        and bound_condition
        and all(str(repair.get("condition") or "").strip() == bound_condition for repair in valid_repairs)
    )
    production_state_matched = bool(
        production_repairs_present
        and len(valid_repairs) == len(repairs)
        and bound_state
        and all(str(repair.get("after") or "").strip().upper() == bound_state for repair in valid_repairs)
    )
    production_provenance_preserved = bool(
        production_repairs_present
        and len(valid_repairs) == len(repairs)
        and all(str(repair.get("new_source") or "").strip() == HISTORICAL_SOURCE for repair in valid_repairs)
    )

    gates = (
        ("pnu_binding_present", pnu_binding_present),
        ("pnu_binding_boundary_matched", pnu_binding_boundary_matched),
        ("pnu_binding_authorized", pnu_binding_authorized),
        ("bound_pnu_present", bool(bound_pnu)),
        ("bound_condition_present", bool(bound_condition)),
        ("bound_state_present", bool(bound_state)),
        ("production_authorization_present", production_authorization_present),
        ("production_authorization_boundary_matched", production_authorization_boundary_matched),
        ("production_integration_authorized", production_integration_authorized),
        ("production_repairs_present", production_repairs_present),
        ("production_condition_matched", production_condition_matched),
        ("production_state_matched", production_state_matched),
        ("production_provenance_preserved", production_provenance_preserved),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    upstream_unknown = bool(pnu_binding_present and pnu_binding.status == UNKNOWN)
    status = UNKNOWN if upstream_unknown else (REJECTED if missing_gates else AUTHORIZED)
    authorized = status == AUTHORIZED

    return HistoricalSiteEventSiteTruthPromotionAuthorization(
        boundary=BOUNDARY_NAME,
        status=status,
        pnu_binding_present=pnu_binding_present,
        pnu_binding_boundary_matched=pnu_binding_boundary_matched,
        pnu_binding_authorized=pnu_binding_authorized,
        bound_pnu=bound_pnu,
        bound_condition=bound_condition,
        bound_state=bound_state,
        production_authorization_present=production_authorization_present,
        production_authorization_boundary_matched=production_authorization_boundary_matched,
        production_integration_authorized=production_integration_authorized,
        production_repairs_present=production_repairs_present,
        production_condition_matched=production_condition_matched,
        production_state_matched=production_state_matched,
        production_provenance_preserved=production_provenance_preserved,
        missing_gates=missing_gates,
        promotion_authorized=authorized,
    )
