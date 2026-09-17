"""Common, non-authoritative input contract for later SITE applicability admission.

This boundary normalizes already-verified SITE-decision candidates without mutating
generic STEP114 or generic SITE applicability admission. It accepts either the
existing historical STEP114 candidate or the district-unit-plan common candidate,
and grants no SITE truth, promotion, production, or runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .district_unit_plan_common_site_decision_candidate_adapter import (
    DistrictUnitPlanCommonSiteDecisionCandidate,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    RegulationResolutionProfileSiteDecisionEligibility,
)

ADMITTED = "ADMITTED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class CommonSiteApplicabilityAdmissionCandidate:
    status: str
    resolver_family: str | None
    canonical_pnu: str
    candidate_site_decision: bool | None
    conclusive_for_site_decision: bool
    source_candidate_verified: bool
    source_kind: str | None
    generic_site_applicability_admission_allowed: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def admitted(self) -> bool:
        return (
            self.status == ADMITTED
            and self.resolver_family in {HISTORICAL_SITE_EVENT, HYBRID_SPATIAL_NOTICE}
            and bool(self.canonical_pnu)
            and self.candidate_site_decision is not None
            and self.conclusive_for_site_decision
            and self.source_candidate_verified
            and self.source_kind in {"GENERIC_STEP114", "DISTRICT_UNIT_PLAN_COMMON"}
            and self.generic_site_applicability_admission_allowed is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def admit_common_site_applicability_candidate(
    source_candidate: Any,
    *,
    canonical_pnu: str,
) -> CommonSiteApplicabilityAdmissionCandidate:
    """Normalize a verified candidate while keeping the existing generic admission closed."""

    expected_pnu = str(canonical_pnu or "").strip()
    if not expected_pnu:
        return _rejected(expected_pnu)

    if isinstance(source_candidate, RegulationResolutionProfileSiteDecisionEligibility):
        valid = bool(
            source_candidate.eligible
            and source_candidate.resolver_family == HISTORICAL_SITE_EVENT
            and source_candidate.candidate_site_decision is False
            and source_candidate.conclusive_for_site_decision
            and source_candidate.site_truth_decision_allowed is False
            and source_candidate.site_promotion_allowed is False
            and source_candidate.production_readiness_allowed is False
            and source_candidate.production_registration_allowed is False
            and source_candidate.runtime_registration_allowed is False
        )
        if valid:
            return CommonSiteApplicabilityAdmissionCandidate(
                status=ADMITTED,
                resolver_family=HISTORICAL_SITE_EVENT,
                canonical_pnu=expected_pnu,
                candidate_site_decision=False,
                conclusive_for_site_decision=True,
                source_candidate_verified=True,
                source_kind="GENERIC_STEP114",
            )
        return _rejected(expected_pnu)

    if isinstance(source_candidate, DistrictUnitPlanCommonSiteDecisionCandidate):
        valid = bool(
            source_candidate.adapted
            and source_candidate.resolver_family == HYBRID_SPATIAL_NOTICE
            and source_candidate.canonical_pnu == expected_pnu
            and source_candidate.candidate_site_decision is True
            and source_candidate.conclusive_for_site_decision
            and source_candidate.source_eligibility_verified
            and source_candidate.generic_step114_satisfied is False
            and source_candidate.generic_site_applicability_admission_allowed is False
            and source_candidate.site_truth_decision_allowed is False
            and source_candidate.site_promotion_allowed is False
            and source_candidate.production_readiness_allowed is False
            and source_candidate.production_registration_allowed is False
            and source_candidate.runtime_registration_allowed is False
        )
        if valid:
            return CommonSiteApplicabilityAdmissionCandidate(
                status=ADMITTED,
                resolver_family=HYBRID_SPATIAL_NOTICE,
                canonical_pnu=expected_pnu,
                candidate_site_decision=True,
                conclusive_for_site_decision=True,
                source_candidate_verified=True,
                source_kind="DISTRICT_UNIT_PLAN_COMMON",
            )

    return _rejected(expected_pnu)


def _rejected(canonical_pnu: str) -> CommonSiteApplicabilityAdmissionCandidate:
    return CommonSiteApplicabilityAdmissionCandidate(
        status=REJECTED,
        resolver_family=None,
        canonical_pnu=canonical_pnu,
        candidate_site_decision=None,
        conclusive_for_site_decision=False,
        source_candidate_verified=False,
        source_kind=None,
    )
