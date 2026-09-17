"""Conclusive, non-authoritative SITE-decision eligibility for district-unit-plan HYBRID.

This boundary combines an already verified district-unit-plan positive candidate with
verified PNU-bound spatial parcel applicability. It does not mutate generic STEP114,
decide SITE truth, or authorize promotion/production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .district_unit_plan_spatial_parcel_applicability_evidence import (
    DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    SPATIAL_PARCEL_INCLUSION,
)

CONDITION_NAME = "지구단위계획"
ELIGIBLE = "ELIGIBLE"
INELIGIBLE = "INELIGIBLE"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class DistrictUnitPlanConclusiveSiteDecisionEligibility:
    status: str
    canonical_pnu: str
    positive_candidate_verified: bool
    parcel_applicability_verified: bool
    parcel_applicability_state: str
    pnu_bound: bool
    candidate_site_decision: bool | None
    conclusive_for_site_decision: bool
    missing_gates: tuple[str, ...]
    generic_step114_satisfied: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def eligible(self) -> bool:
        return (
            self.status == ELIGIBLE
            and self.positive_candidate_verified
            and self.parcel_applicability_verified
            and self.parcel_applicability_state == "APPLIES"
            and self.pnu_bound
            and self.candidate_site_decision is True
            and self.conclusive_for_site_decision
            and not self.missing_gates
            and self.generic_step114_satisfied is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _text(value: Any) -> str:
    return str(value or "").strip()


def evaluate_district_unit_plan_conclusive_site_decision_eligibility(
    positive_candidate: Mapping[str, Any] | None,
    parcel_applicability: DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult | None,
    *,
    canonical_pnu: str,
) -> DistrictUnitPlanConclusiveSiteDecisionEligibility:
    """Recognize a conclusive TRUE candidate without claiming generic STEP114 authority."""

    candidate = dict(positive_candidate or {})
    expected_pnu = _text(canonical_pnu)

    positive_candidate_verified = bool(
        expected_pnu
        and candidate.get("positive_candidate_verified") is True
        and candidate.get("candidate_state") == "POSITIVE_CANDIDATE"
        and candidate.get("condition_name") == CONDITION_NAME
        and candidate.get("resolution_type") == HYBRID_SPATIAL_NOTICE
        and candidate.get("source_resolution") == "UNKNOWN"
        and _text(candidate.get("canonical_pnu")) == expected_pnu
        and candidate.get("parcel_applicability_verified") is False
        and candidate.get("site_decision_eligible") is False
    )

    evidence = (
        parcel_applicability.applicability_evidence
        if isinstance(
            parcel_applicability,
            DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult,
        )
        else None
    )
    parcel_applicability_verified = bool(
        isinstance(
            parcel_applicability,
            DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult,
        )
        and parcel_applicability.verified
        and parcel_applicability.applicability_verified
        and parcel_applicability.applicability_state == "APPLIES"
        and evidence is not None
        and evidence.resolver_family == HYBRID_SPATIAL_NOTICE
        and evidence.evidence_kind == SPATIAL_PARCEL_INCLUSION
        and evidence.applicability_verified
        and evidence.applicability_state == "APPLIES"
    )
    pnu_bound = bool(
        expected_pnu
        and parcel_applicability_verified
        and parcel_applicability is not None
        and parcel_applicability.canonical_pnu == expected_pnu
        and parcel_applicability.evidence_pnu == expected_pnu
        and evidence is not None
        and evidence.target_pnu == expected_pnu
        and evidence.evidence_pnu == expected_pnu
    )

    gates = (
        ("canonical_pnu_present", bool(expected_pnu)),
        ("positive_candidate_verified", positive_candidate_verified),
        ("spatial_parcel_applicability_verified", parcel_applicability_verified),
        ("candidate_and_evidence_pnu_bound", pnu_bound),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    conclusive = not missing_gates

    if conclusive:
        status = ELIGIBLE
        candidate_site_decision: bool | None = True
    elif not expected_pnu or (
        parcel_applicability is not None
        and parcel_applicability.status == REJECTED
    ):
        status = REJECTED
        candidate_site_decision = None
    else:
        status = INELIGIBLE
        candidate_site_decision = None

    return DistrictUnitPlanConclusiveSiteDecisionEligibility(
        status=status,
        canonical_pnu=expected_pnu,
        positive_candidate_verified=positive_candidate_verified,
        parcel_applicability_verified=parcel_applicability_verified,
        parcel_applicability_state=(
            parcel_applicability.applicability_state
            if parcel_applicability is not None
            else "UNKNOWN"
        ),
        pnu_bound=pnu_bound,
        candidate_site_decision=candidate_site_decision,
        conclusive_for_site_decision=conclusive,
        missing_gates=missing_gates,
    )
