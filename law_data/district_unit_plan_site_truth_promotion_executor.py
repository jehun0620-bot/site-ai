"""Isolated executor for authorized district-unit-plan SITE-truth promotion.

The authorization is the permit; this executor prepares one exact SITE condition for
a later bridge. It does not mutate a registry, call the Rule Engine, modify builders,
register runtime state, or expose anything through the public API.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_site_truth_promotion_authorization import (
    AUTHORIZED as PROMOTION_AUTHORIZED,
    BOUNDARY_NAME as PROMOTION_AUTHORIZATION_BOUNDARY_NAME,
    CONDITION_NAME,
    DistrictUnitPlanSiteTruthPromotionAuthorization,
)

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_EXECUTOR"
EXECUTED = "EXECUTED"
REJECTED = "REJECTED"
CONDITION_TYPE = "SITE"
REGISTRY_SOURCE = "RUNTIME_DISTRICT_UNIT_PLAN_HYBRID"
EXPECTED_PROVENANCE = "HYBRID_SPATIAL_NOTICE_VERIFIED"


@dataclass(frozen=True)
class DistrictUnitPlanSiteTruthPromotionExecution:
    boundary: str
    status: str
    authorization_present: bool
    authorization_boundary_matched: bool
    promotion_authorized: bool
    bound_pnu: str
    bound_condition: str
    bound_state: str
    provenance_verified: bool
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
        return (
            self.status == EXECUTED
            and self.boundary == BOUNDARY_NAME
            and self.execution_succeeded
            and self.authorization_present
            and self.authorization_boundary_matched
            and self.promotion_authorized
            and self.bound_pnu
            and self.bound_condition == CONDITION_NAME
            and self.bound_state == "TRUE"
            and self.provenance_verified
            and self.promoted_condition_present
            and bool(self.promoted_condition)
            and not self.missing_gates
            and self.site_registry_mutated is False
            and self.rule_engine_called is False
            and self.builder_modified is False
            and self.runtime_registered is False
            and self.public_api_exposed is False
        )


def execute_district_unit_plan_site_truth_promotion(
    authorization: DistrictUnitPlanSiteTruthPromotionAuthorization | None,
) -> DistrictUnitPlanSiteTruthPromotionExecution:
    """Prepare a provenance-preserving SITE TRUE condition without registering it."""

    present = isinstance(authorization, DistrictUnitPlanSiteTruthPromotionAuthorization)
    boundary_matched = bool(
        present and authorization.boundary == PROMOTION_AUTHORIZATION_BOUNDARY_NAME
    )
    promotion_authorized = bool(
        present
        and authorization.status == PROMOTION_AUTHORIZED
        and authorization.authorized
    )
    pnu = str(authorization.canonical_pnu or "").strip() if present else ""
    condition = str(authorization.condition_name or "").strip() if present else ""
    state = str(authorization.bound_state or "").strip().upper() if present else ""
    provenance_verified = bool(
        present and authorization.provenance_kind == EXPECTED_PROVENANCE
    )
    pnu_valid = len(pnu) == 19 and pnu.isdigit()
    condition_valid = condition == CONDITION_NAME
    state_valid = state == "TRUE"
    upstream_authority_closed = bool(
        present
        and authorization.site_truth_decision_allowed is False
        and authorization.site_truth_mutation_allowed is False
        and authorization.promotion_execution_allowed is False
        and authorization.production_readiness_allowed is False
        and authorization.production_registration_allowed is False
        and authorization.runtime_registration_allowed is False
        and authorization.public_api_exposure_allowed is False
    )

    gates = (
        ("authorization_present", present),
        ("authorization_boundary_matched", boundary_matched),
        ("promotion_authorized", promotion_authorized),
        ("bound_pnu_valid", pnu_valid),
        ("condition_is_district_unit_plan", condition_valid),
        ("bound_state_true", state_valid),
        ("provenance_verified", provenance_verified),
        ("upstream_authority_closed", upstream_authority_closed),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    succeeded = not missing_gates

    promoted_condition: Mapping[str, Any] = {}
    if succeeded:
        promoted_condition = {
            "type": CONDITION_TYPE,
            "state": "TRUE",
            "confidence": "HIGH",
            "source": REGISTRY_SOURCE,
            "runtime": True,
            "pnu": pnu,
            "historical": False,
            "hybrid": True,
            "provenance": EXPECTED_PROVENANCE,
            "promotion_authorization_boundary": authorization.boundary,
            "promotion_executor_boundary": BOUNDARY_NAME,
        }

    return DistrictUnitPlanSiteTruthPromotionExecution(
        boundary=BOUNDARY_NAME,
        status=EXECUTED if succeeded else REJECTED,
        authorization_present=present,
        authorization_boundary_matched=boundary_matched,
        promotion_authorized=promotion_authorized,
        bound_pnu=pnu,
        bound_condition=condition,
        bound_state=state,
        provenance_verified=provenance_verified,
        promoted_condition_present=bool(promoted_condition),
        promoted_condition=promoted_condition,
        missing_gates=missing_gates,
        execution_succeeded=succeeded,
    )
