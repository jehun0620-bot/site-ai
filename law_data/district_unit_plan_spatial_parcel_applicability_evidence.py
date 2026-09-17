"""Fail-closed spatial parcel applicability evidence for district-unit-plan HYBRID.

This module proves only that already-verified district-unit-plan spatial evidence is
bound to one canonical parcel and one verified positive candidate. It does not satisfy
STEP114, decide SITE truth, or authorize promotion/production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    SPATIAL_PARCEL_INCLUSION,
    RegulationResolutionProfileSiteApplicabilityEvidence,
)

CONDITION_NAME = "지구단위계획"
EXPECTED_DATASET = "LT_C_UPISUQ161"
VERIFIED = "VERIFIED"
UNKNOWN = "UNKNOWN"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult:
    status: str
    canonical_pnu: str
    evidence_pnu: str
    positive_candidate_verified: bool
    spatial_inclusion_verified: bool
    pnu_matched: bool
    applicability_verified: bool
    applicability_state: str
    missing_gates: tuple[str, ...]
    applicability_evidence: RegulationResolutionProfileSiteApplicabilityEvidence | None
    site_decision_eligible: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.positive_candidate_verified
            and self.spatial_inclusion_verified
            and self.pnu_matched
            and self.applicability_verified
            and self.applicability_state == "APPLIES"
            and self.applicability_evidence is not None
            and not self.missing_gates
            and self.site_decision_eligible is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _text(value: Any) -> str:
    return str(value or "").strip()


def _valid_pnu(value: str) -> bool:
    return len(value) == 19 and value.isdigit()


def build_district_unit_plan_spatial_parcel_applicability_evidence(
    canonical_site: Mapping[str, Any] | None,
    positive_candidate: Mapping[str, Any] | None,
    spatial_inclusion: Mapping[str, Any] | None,
) -> DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult:
    """Build generic HYBRID SPATIAL_PARCEL_INCLUSION evidence without authority."""

    site = dict(canonical_site or {})
    candidate = dict(positive_candidate or {})
    spatial = dict(spatial_inclusion or {})

    canonical_pnu = _text(site.get("pnu"))
    candidate_pnu = _text(candidate.get("canonical_pnu"))
    spatial_pnu = _text(spatial.get("canonical_pnu"))
    source_pnu = _text(spatial.get("source_pnu"))

    canonical_identity_complete = bool(
        site.get("identity_status") == "COMPLETE" and _valid_pnu(canonical_pnu)
    )
    positive_candidate_verified = bool(
        candidate.get("positive_candidate_verified") is True
        and candidate.get("candidate_state") == "POSITIVE_CANDIDATE"
        and candidate.get("condition_name") == CONDITION_NAME
        and candidate.get("resolution_type") == HYBRID_SPATIAL_NOTICE
        and candidate.get("source_resolution") == "UNKNOWN"
        and candidate.get("parcel_applicability_verified") is False
        and candidate.get("site_decision_eligible") is False
    )
    spatial_inclusion_verified = bool(
        spatial.get("site_spatial_inclusion_verified") is True
        and spatial.get("condition_name") == CONDITION_NAME
        and spatial.get("dataset") == EXPECTED_DATASET
    )
    pnu_matched = bool(
        canonical_identity_complete
        and candidate_pnu == canonical_pnu
        and spatial_pnu == canonical_pnu
        and source_pnu == canonical_pnu
    )

    gates = (
        ("canonical_site_identity", canonical_identity_complete),
        ("positive_candidate_verified", positive_candidate_verified),
        ("spatial_inclusion_verified", spatial_inclusion_verified),
        ("parcel_pnu_binding", pnu_matched),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)
    applicability_verified = not missing_gates

    if applicability_verified:
        status = VERIFIED
        applicability_state = "APPLIES"
        applicability_evidence = RegulationResolutionProfileSiteApplicabilityEvidence(
            resolver_family=HYBRID_SPATIAL_NOTICE,
            evidence_kind=SPATIAL_PARCEL_INCLUSION,
            target_pnu=canonical_pnu,
            evidence_pnu=source_pnu,
            applicability_verified=True,
            applicability_state="APPLIES",
        )
    else:
        hard_rejection = bool(
            not canonical_identity_complete
            or not _valid_pnu(candidate_pnu)
            or not _valid_pnu(spatial_pnu)
            or not _valid_pnu(source_pnu)
            or (
                canonical_identity_complete
                and all(_valid_pnu(value) for value in (candidate_pnu, spatial_pnu, source_pnu))
                and not pnu_matched
            )
        )
        status = REJECTED if hard_rejection else UNKNOWN
        applicability_state = UNKNOWN
        applicability_evidence = None

    return DistrictUnitPlanSpatialParcelApplicabilityEvidenceResult(
        status=status,
        canonical_pnu=canonical_pnu,
        evidence_pnu=source_pnu,
        positive_candidate_verified=positive_candidate_verified,
        spatial_inclusion_verified=spatial_inclusion_verified,
        pnu_matched=pnu_matched,
        applicability_verified=applicability_verified,
        applicability_state=applicability_state,
        missing_gates=missing_gates,
        applicability_evidence=applicability_evidence,
    )
