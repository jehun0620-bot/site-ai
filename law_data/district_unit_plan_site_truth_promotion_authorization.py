"""Non-executing promotion authorization for district-unit-plan SITE truth.

This is a permit boundary only. It consumes the common SITE applicability admission
and verifies that one canonical parcel has a conclusive district-unit-plan TRUE
candidate. It does not mutate SITE truth, build a runtime registry condition, call the
Rule Engine, or authorize production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .common_site_applicability_admission import CommonSiteApplicabilityAdmission
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)

BOUNDARY_NAME = "DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_AUTHORIZATION"
CONDITION_NAME = "지구단위계획"
AUTHORIZED = "AUTHORIZED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class DistrictUnitPlanSiteTruthPromotionAuthorization:
    boundary: str
    status: str
    canonical_pnu: str
    resolver_family: str | None
    condition_name: str | None
    bound_state: str | None
    common_applicability_admitted: bool
    pnu_valid: bool
    family_matched: bool
    candidate_true: bool
    applicability_applies: bool
    provenance_kind: str | None
    missing_gates: tuple[str, ...]
    promotion_authorized: bool
    site_truth_decision_allowed: bool = False
    site_truth_mutation_allowed: bool = False
    promotion_execution_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False
    public_api_exposure_allowed: bool = False

    @property
    def authorized(self) -> bool:
        return (
            self.status == AUTHORIZED
            and self.boundary == BOUNDARY_NAME
            and self.common_applicability_admitted
            and self.pnu_valid
            and self.family_matched
            and self.candidate_true
            and self.applicability_applies
            and self.canonical_pnu
            and self.condition_name == CONDITION_NAME
            and self.bound_state == "TRUE"
            and self.provenance_kind == "HYBRID_SPATIAL_NOTICE_VERIFIED"
            and not self.missing_gates
            and self.promotion_authorized
            and self.site_truth_decision_allowed is False
            and self.site_truth_mutation_allowed is False
            and self.promotion_execution_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
            and self.public_api_exposure_allowed is False
        )


def authorize_district_unit_plan_site_truth_promotion(
    admission: CommonSiteApplicabilityAdmission | None,
    *,
    canonical_pnu: str,
) -> DistrictUnitPlanSiteTruthPromotionAuthorization:
    """Authorize only the exact admitted HYBRID TRUE/APPLIES parcel decision."""

    expected_pnu = str(canonical_pnu or "").strip()
    present = isinstance(admission, CommonSiteApplicabilityAdmission)
    common_applicability_admitted = bool(present and admission.admitted)
    pnu_valid = bool(
        len(expected_pnu) == 19
        and expected_pnu.isdigit()
        and present
        and admission.canonical_pnu == expected_pnu
    )
    family_matched = bool(
        present and admission.resolver_family == HYBRID_SPATIAL_NOTICE
    )
    candidate_true = bool(present and admission.candidate_site_decision is True)
    applicability_applies = bool(
        present and admission.applicability_state == "APPLIES"
    )
    upstream_authority_closed = bool(
        present
        and admission.site_truth_decision_allowed is False
        and admission.site_promotion_allowed is False
        and admission.production_readiness_allowed is False
        and admission.production_registration_allowed is False
        and admission.runtime_registration_allowed is False
    )

    gates = (
        ("common_applicability_admitted", common_applicability_admitted),
        ("canonical_pnu_valid_and_bound", pnu_valid),
        ("hybrid_family_matched", family_matched),
        ("candidate_site_decision_true", candidate_true),
        ("applicability_applies", applicability_applies),
        ("upstream_authority_closed", upstream_authority_closed),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    authorized = not missing_gates

    return DistrictUnitPlanSiteTruthPromotionAuthorization(
        boundary=BOUNDARY_NAME,
        status=AUTHORIZED if authorized else REJECTED,
        canonical_pnu=expected_pnu,
        resolver_family=HYBRID_SPATIAL_NOTICE if authorized else None,
        condition_name=CONDITION_NAME if authorized else None,
        bound_state="TRUE" if authorized else None,
        common_applicability_admitted=common_applicability_admitted,
        pnu_valid=pnu_valid,
        family_matched=family_matched,
        candidate_true=candidate_true,
        applicability_applies=applicability_applies,
        provenance_kind="HYBRID_SPATIAL_NOTICE_VERIFIED" if authorized else None,
        missing_gates=missing_gates,
        promotion_authorized=authorized,
    )
