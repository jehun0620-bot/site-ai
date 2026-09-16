"""Fail-closed SITE/PNU applicability admission after SITE-decision eligibility.

This boundary binds a STEP114 decision candidate to the canonical SITE PNU and
family-specific parcel applicability evidence. It does not mutate SITE truth or
authorize production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    RegulationResolutionProfileSiteDecisionEligibility,
)

ADMITTED = "ADMITTED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"

HISTORICAL_PARCEL_EVENT_BINDING = "HISTORICAL_PARCEL_EVENT_BINDING"
SPATIAL_PARCEL_INCLUSION = "SPATIAL_PARCEL_INCLUSION"

_FAMILY_EVIDENCE_KIND = {
    HISTORICAL_SITE_EVENT: HISTORICAL_PARCEL_EVENT_BINDING,
    HYBRID_SPATIAL_NOTICE: SPATIAL_PARCEL_INCLUSION,
}


@dataclass(frozen=True)
class RegulationResolutionProfileSiteApplicabilityEvidence:
    resolver_family: str
    evidence_kind: str
    target_pnu: str
    evidence_pnu: str
    applicability_verified: bool
    applicability_state: str


@dataclass(frozen=True)
class RegulationResolutionProfileSiteApplicabilityAdmission:
    status: str
    resolver_family: str | None
    canonical_pnu: str
    evidence_pnu: str
    candidate_site_decision: bool | None
    identity_bound: bool
    family_evidence_matched: bool
    parcel_applicability_verified: bool
    parcel_applicability_state: str
    missing_gates: tuple[str, ...]
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def admitted(self) -> bool:
        return (
            self.status == ADMITTED
            and not self.missing_gates
            and self.identity_bound
            and self.family_evidence_matched
            and self.parcel_applicability_verified
            and self.parcel_applicability_state == "APPLIES"
            and self.candidate_site_decision is not None
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _safe_text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def admit_site_applicability(
    eligibility: RegulationResolutionProfileSiteDecisionEligibility | None,
    canonical_site: Mapping[str, Any] | None,
    applicability_evidence: RegulationResolutionProfileSiteApplicabilityEvidence | None,
) -> RegulationResolutionProfileSiteApplicabilityAdmission:
    """Bind a STEP114 candidate to one canonical parcel without authority escalation."""

    eligibility_valid = bool(
        isinstance(eligibility, RegulationResolutionProfileSiteDecisionEligibility)
        and eligibility.eligible
    )
    family = eligibility.resolver_family if eligibility_valid else None
    candidate = eligibility.candidate_site_decision if eligibility_valid else None

    canonical_pnu = _safe_text(
        canonical_site.get("pnu")
        if isinstance(canonical_site, Mapping)
        else None
    )
    identity_complete = bool(
        isinstance(canonical_site, Mapping)
        and canonical_site.get("identity_status") == "COMPLETE"
        and canonical_pnu
    )

    evidence_valid = isinstance(
        applicability_evidence,
        RegulationResolutionProfileSiteApplicabilityEvidence,
    )
    evidence_pnu = _safe_text(
        applicability_evidence.evidence_pnu if evidence_valid else None
    )
    target_pnu = _safe_text(
        applicability_evidence.target_pnu if evidence_valid else None
    )

    identity_bound = bool(
        identity_complete
        and evidence_valid
        and target_pnu == canonical_pnu
        and evidence_pnu == canonical_pnu
    )

    expected_kind = _FAMILY_EVIDENCE_KIND.get(family)
    family_evidence_matched = bool(
        eligibility_valid
        and evidence_valid
        and applicability_evidence.resolver_family == family
        and expected_kind
        and applicability_evidence.evidence_kind == expected_kind
    )

    parcel_applicability_verified = bool(
        evidence_valid
        and applicability_evidence.applicability_verified is True
    )
    parcel_applicability_state = (
        _safe_text(applicability_evidence.applicability_state)
        if evidence_valid
        else ""
    )

    gates = (
        ("step114_eligibility", eligibility_valid),
        ("canonical_site_identity", identity_complete),
        ("parcel_identity_binding", identity_bound),
        ("resolver_family_evidence", family_evidence_matched),
        ("parcel_applicability_verified", parcel_applicability_verified),
        ("parcel_applicability_applies", parcel_applicability_state == "APPLIES"),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    if not eligibility_valid or not identity_complete or not evidence_valid:
        status = REJECTED
    elif parcel_applicability_state == "UNKNOWN" or not parcel_applicability_verified:
        status = UNKNOWN
    elif missing_gates:
        status = REJECTED
    else:
        status = ADMITTED

    return RegulationResolutionProfileSiteApplicabilityAdmission(
        status=status,
        resolver_family=family,
        canonical_pnu=canonical_pnu,
        evidence_pnu=evidence_pnu,
        candidate_site_decision=candidate,
        identity_bound=identity_bound,
        family_evidence_matched=family_evidence_matched,
        parcel_applicability_verified=parcel_applicability_verified,
        parcel_applicability_state=parcel_applicability_state,
        missing_gates=missing_gates,
    )
