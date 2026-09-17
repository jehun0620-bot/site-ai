"""Non-authoritative common SITE-decision candidate adapter for district-unit-plan.

This adapter translates the family-specific conclusive district-unit-plan result into
an explicit common candidate representation. It deliberately does not impersonate the
generic STEP114 eligibility object and does not authorize SITE truth, applicability
admission, promotion, production, or runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .district_unit_plan_conclusive_site_decision_eligibility import (
    DistrictUnitPlanConclusiveSiteDecisionEligibility,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)

CONDITION_NAME = "지구단위계획"
ADAPTED = "ADAPTED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class DistrictUnitPlanCommonSiteDecisionCandidate:
    status: str
    resolver_family: str | None
    condition_name: str | None
    canonical_pnu: str
    candidate_site_decision: bool | None
    conclusive_for_site_decision: bool
    source_eligibility_verified: bool
    generic_step114_satisfied: bool = False
    generic_site_applicability_admission_allowed: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def adapted(self) -> bool:
        return (
            self.status == ADAPTED
            and self.resolver_family == HYBRID_SPATIAL_NOTICE
            and self.condition_name == CONDITION_NAME
            and bool(self.canonical_pnu)
            and self.candidate_site_decision is True
            and self.conclusive_for_site_decision
            and self.source_eligibility_verified
            and self.generic_step114_satisfied is False
            and self.generic_site_applicability_admission_allowed is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def adapt_district_unit_plan_common_site_decision_candidate(
    eligibility: DistrictUnitPlanConclusiveSiteDecisionEligibility | None,
    *,
    canonical_pnu: str,
) -> DistrictUnitPlanCommonSiteDecisionCandidate:
    """Adapt only an exact, PNU-bound conclusive TRUE candidate without authority."""

    expected_pnu = str(canonical_pnu or "").strip()
    source_valid = bool(
        isinstance(eligibility, DistrictUnitPlanConclusiveSiteDecisionEligibility)
        and eligibility.eligible
        and eligibility.status == "ELIGIBLE"
        and eligibility.canonical_pnu == expected_pnu
        and eligibility.positive_candidate_verified
        and eligibility.parcel_applicability_verified
        and eligibility.parcel_applicability_state == "APPLIES"
        and eligibility.pnu_bound
        and eligibility.candidate_site_decision is True
        and eligibility.conclusive_for_site_decision
        and eligibility.generic_step114_satisfied is False
        and eligibility.site_truth_decision_allowed is False
        and eligibility.site_promotion_allowed is False
        and eligibility.production_readiness_allowed is False
        and eligibility.production_registration_allowed is False
        and eligibility.runtime_registration_allowed is False
    )

    if not source_valid or not expected_pnu:
        return DistrictUnitPlanCommonSiteDecisionCandidate(
            status=REJECTED,
            resolver_family=None,
            condition_name=None,
            canonical_pnu=expected_pnu,
            candidate_site_decision=None,
            conclusive_for_site_decision=False,
            source_eligibility_verified=False,
        )

    return DistrictUnitPlanCommonSiteDecisionCandidate(
        status=ADAPTED,
        resolver_family=HYBRID_SPATIAL_NOTICE,
        condition_name=CONDITION_NAME,
        canonical_pnu=expected_pnu,
        candidate_site_decision=True,
        conclusive_for_site_decision=True,
        source_eligibility_verified=True,
    )
