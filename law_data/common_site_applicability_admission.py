"""Common fail-closed SITE applicability admission boundary.

This boundary combines an already-admitted common SITE-decision candidate with the
existing generic parcel-applicability evidence shape. It does not mutate the legacy
generic admission, decide SITE truth, or authorize promotion/production/runtime use.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common_site_applicability_admission_candidate import (
    CommonSiteApplicabilityAdmissionCandidate,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    HISTORICAL_PARCEL_EVENT_BINDING,
    SPATIAL_PARCEL_INCLUSION,
    RegulationResolutionProfileSiteApplicabilityEvidence,
)

ADMITTED = "ADMITTED"
REJECTED = "REJECTED"

_FAMILY_EVIDENCE_KIND = {
    HISTORICAL_SITE_EVENT: HISTORICAL_PARCEL_EVENT_BINDING,
    HYBRID_SPATIAL_NOTICE: SPATIAL_PARCEL_INCLUSION,
}


@dataclass(frozen=True)
class CommonSiteApplicabilityAdmission:
    status: str
    resolver_family: str | None
    canonical_pnu: str
    candidate_site_decision: bool | None
    applicability_state: str | None
    candidate_verified: bool
    evidence_verified: bool
    family_matched: bool
    evidence_kind_matched: bool
    pnu_bound: bool
    site_applicability_admitted: bool
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def admitted(self) -> bool:
        return (
            self.status == ADMITTED
            and self.resolver_family in _FAMILY_EVIDENCE_KIND
            and bool(self.canonical_pnu)
            and self.candidate_site_decision is not None
            and self.applicability_state == "APPLIES"
            and self.candidate_verified
            and self.evidence_verified
            and self.family_matched
            and self.evidence_kind_matched
            and self.pnu_bound
            and self.site_applicability_admitted
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def admit_common_site_applicability(
    candidate: CommonSiteApplicabilityAdmissionCandidate | None,
    evidence: RegulationResolutionProfileSiteApplicabilityEvidence | None,
    *,
    canonical_pnu: str,
) -> CommonSiteApplicabilityAdmission:
    """Admit only same-family, same-PNU, verified APPLIES evidence."""

    expected_pnu = str(canonical_pnu or "").strip()
    candidate_verified = bool(
        isinstance(candidate, CommonSiteApplicabilityAdmissionCandidate)
        and candidate.admitted
        and candidate.canonical_pnu == expected_pnu
        and candidate.conclusive_for_site_decision
        and candidate.source_candidate_verified
        and candidate.generic_site_applicability_admission_allowed is False
        and candidate.site_truth_decision_allowed is False
        and candidate.site_promotion_allowed is False
        and candidate.production_readiness_allowed is False
        and candidate.production_registration_allowed is False
        and candidate.runtime_registration_allowed is False
    )

    evidence_verified = bool(
        isinstance(evidence, RegulationResolutionProfileSiteApplicabilityEvidence)
        and evidence.applicability_verified is True
        and evidence.applicability_state == "APPLIES"
    )

    family_matched = bool(
        candidate_verified
        and evidence_verified
        and candidate is not None
        and evidence is not None
        and candidate.resolver_family == evidence.resolver_family
        and candidate.resolver_family in _FAMILY_EVIDENCE_KIND
    )
    evidence_kind_matched = bool(
        family_matched
        and evidence is not None
        and candidate is not None
        and evidence.evidence_kind == _FAMILY_EVIDENCE_KIND[candidate.resolver_family]
    )
    pnu_bound = bool(
        expected_pnu
        and candidate_verified
        and evidence_verified
        and candidate is not None
        and evidence is not None
        and candidate.canonical_pnu
        == evidence.target_pnu
        == evidence.evidence_pnu
        == expected_pnu
    )

    admitted = bool(
        candidate_verified
        and evidence_verified
        and family_matched
        and evidence_kind_matched
        and pnu_bound
    )

    if not admitted:
        return CommonSiteApplicabilityAdmission(
            status=REJECTED,
            resolver_family=None,
            canonical_pnu=expected_pnu,
            candidate_site_decision=None,
            applicability_state=None,
            candidate_verified=candidate_verified,
            evidence_verified=evidence_verified,
            family_matched=family_matched,
            evidence_kind_matched=evidence_kind_matched,
            pnu_bound=pnu_bound,
            site_applicability_admitted=False,
        )

    return CommonSiteApplicabilityAdmission(
        status=ADMITTED,
        resolver_family=candidate.resolver_family,
        canonical_pnu=expected_pnu,
        candidate_site_decision=candidate.candidate_site_decision,
        applicability_state="APPLIES",
        candidate_verified=True,
        evidence_verified=True,
        family_matched=True,
        evidence_kind_matched=True,
        pnu_bound=True,
        site_applicability_admitted=True,
    )
