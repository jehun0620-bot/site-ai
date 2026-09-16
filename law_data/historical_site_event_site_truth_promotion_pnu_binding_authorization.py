"""Fail-closed canonical-PNU binding for a historical SITE-truth promotion candidate.

This boundary does not promote or mutate SITE truth. It accepts only an already
validated pre-promotion binding and binds that candidate to one explicit
canonical 19-digit PNU for any future promotion executor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.historical_site_event_site_truth_promotion_binding_authorization import (
    AUTHORIZED as PROMOTION_BINDING_AUTHORIZED,
    BOUNDARY_NAME as PROMOTION_BINDING_BOUNDARY_NAME,
    HistoricalSiteEventSiteTruthPromotionBindingAuthorization,
)

BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_SITE_TRUTH_PROMOTION_PNU_BINDING_AUTHORIZATION"
AUTHORIZED = "AUTHORIZED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"


def _valid_pnu(value: Any) -> bool:
    text = str(value or "").strip()
    return len(text) == 19 and text.isdigit()


@dataclass(frozen=True)
class HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization:
    boundary: str
    status: str
    promotion_binding_present: bool
    promotion_binding_boundary_matched: bool
    promotion_binding_authorized: bool
    canonical_pnu_present: bool
    canonical_pnu_valid: bool
    requested_pnu_present: bool
    requested_pnu_valid: bool
    pnu_matched: bool
    bound_pnu: str
    bound_condition: str
    bound_state: str
    missing_gates: tuple[str, ...]
    pnu_binding_authorized: bool
    site_truth_decision_allowed: bool = False
    site_truth_mutation_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return bool(
            self.status == AUTHORIZED
            and self.pnu_binding_authorized
            and self.promotion_binding_present
            and self.promotion_binding_boundary_matched
            and self.promotion_binding_authorized
            and self.canonical_pnu_present
            and self.canonical_pnu_valid
            and self.requested_pnu_present
            and self.requested_pnu_valid
            and self.pnu_matched
            and self.bound_pnu
            and self.bound_condition
            and self.bound_state
            and not self.missing_gates
            and not self.site_truth_decision_allowed
            and not self.site_truth_mutation_allowed
            and not self.site_promotion_allowed
            and not self.production_registration_allowed
            and not self.runtime_registration_allowed
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self.__dict__, "missing_gates": list(self.missing_gates), "authorized": self.authorized}


def authorize_historical_site_event_site_truth_promotion_pnu_binding(
    promotion_binding: HistoricalSiteEventSiteTruthPromotionBindingAuthorization | None,
    canonical_pnu: Any,
) -> HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization:
    promotion_binding_present = isinstance(
        promotion_binding,
        HistoricalSiteEventSiteTruthPromotionBindingAuthorization,
    )
    promotion_binding_boundary_matched = bool(
        promotion_binding_present and promotion_binding.boundary == PROMOTION_BINDING_BOUNDARY_NAME
    )
    promotion_binding_authorized = bool(
        promotion_binding_present
        and promotion_binding.status == PROMOTION_BINDING_AUTHORIZED
        and promotion_binding.authorized
    )

    admitted_pnu = str(promotion_binding.canonical_pnu or "").strip() if promotion_binding_present else ""
    canonical_pnu_present = bool(admitted_pnu)
    canonical_pnu_valid = _valid_pnu(admitted_pnu)

    requested_pnu = str(canonical_pnu or "").strip()
    requested_pnu_present = bool(requested_pnu)
    requested_pnu_valid = _valid_pnu(requested_pnu)
    pnu_matched = bool(canonical_pnu_valid and requested_pnu_valid and admitted_pnu == requested_pnu)

    bound_condition = str(promotion_binding.bound_condition or "").strip() if promotion_binding_present else ""
    bound_state = str(promotion_binding.candidate_state or "").strip().upper() if promotion_binding_present else ""

    gates = (
        ("promotion_binding_present", promotion_binding_present),
        ("promotion_binding_boundary_matched", promotion_binding_boundary_matched),
        ("promotion_binding_authorized", promotion_binding_authorized),
        ("canonical_pnu_present", canonical_pnu_present),
        ("canonical_pnu_valid", canonical_pnu_valid),
        ("requested_pnu_present", requested_pnu_present),
        ("requested_pnu_valid", requested_pnu_valid),
        ("pnu_matched", pnu_matched),
        ("bound_condition_present", bool(bound_condition)),
        ("bound_state_present", bool(bound_state)),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    upstream_unknown = bool(promotion_binding_present and promotion_binding.status == UNKNOWN)
    status = UNKNOWN if upstream_unknown else (REJECTED if missing_gates else AUTHORIZED)
    authorized = status == AUTHORIZED

    return HistoricalSiteEventSiteTruthPromotionPnuBindingAuthorization(
        boundary=BOUNDARY_NAME,
        status=status,
        promotion_binding_present=promotion_binding_present,
        promotion_binding_boundary_matched=promotion_binding_boundary_matched,
        promotion_binding_authorized=promotion_binding_authorized,
        canonical_pnu_present=canonical_pnu_present,
        canonical_pnu_valid=canonical_pnu_valid,
        requested_pnu_present=requested_pnu_present,
        requested_pnu_valid=requested_pnu_valid,
        pnu_matched=pnu_matched,
        bound_pnu=(requested_pnu if authorized else ""),
        bound_condition=(bound_condition if authorized else ""),
        bound_state=(bound_state if authorized else ""),
        missing_gates=missing_gates,
        pnu_binding_authorized=authorized,
    )
