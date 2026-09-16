"""Compose historical parcel evidence with SITE applicability admission.

This is a fail-closed composition boundary. It does not mutate SITE truth and
does not authorize production or runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .historical_site_event_parcel_applicability_evidence import (
    HistoricalSiteEventParcelApplicabilityEvidenceResult,
    HistoricalSiteEventParcelEvidenceInput,
    build_historical_site_event_parcel_applicability_evidence,
)
from .regulation_resolution_profile_site_applicability_admission import (
    RegulationResolutionProfileSiteApplicabilityAdmission,
    admit_site_applicability,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    RegulationResolutionProfileSiteDecisionEligibility,
)

ADMITTED = "ADMITTED"
REJECTED = "REJECTED"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HistoricalSiteEventSiteApplicabilityAdmissionResult:
    status: str
    parcel_evidence_result: HistoricalSiteEventParcelApplicabilityEvidenceResult
    site_admission: RegulationResolutionProfileSiteApplicabilityAdmission | None
    candidate_site_decision: bool | None
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
            and self.parcel_evidence_result.verified
            and self.site_admission is not None
            and self.site_admission.admitted
            and self.candidate_site_decision is not None
            and not self.missing_gates
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def admit_historical_site_event_site_applicability(
    eligibility: RegulationResolutionProfileSiteDecisionEligibility | None,
    canonical_site: Mapping[str, Any] | None,
    evidence_input: HistoricalSiteEventParcelEvidenceInput | None,
) -> HistoricalSiteEventSiteApplicabilityAdmissionResult:
    """Run historical parcel proof first, then the generic SITE admission gate."""

    parcel_result = build_historical_site_event_parcel_applicability_evidence(
        canonical_site,
        evidence_input,
    )

    site_admission = None
    if parcel_result.applicability_evidence is not None:
        site_admission = admit_site_applicability(
            eligibility,
            canonical_site,
            parcel_result.applicability_evidence,
        )

    missing = []
    if not parcel_result.verified:
        missing.append("historical_parcel_applicability_evidence")
    if site_admission is None:
        missing.append("site_applicability_admission")
    elif not site_admission.admitted:
        missing.append("site_applicability_admitted")

    candidate = (
        site_admission.candidate_site_decision
        if site_admission is not None and site_admission.admitted
        else None
    )

    if parcel_result.status == "UNKNOWN":
        status = UNKNOWN
    elif parcel_result.status == "REJECTED":
        status = REJECTED
    elif site_admission is None:
        status = REJECTED
    elif site_admission.status == "UNKNOWN":
        status = UNKNOWN
    elif not site_admission.admitted:
        status = REJECTED
    else:
        status = ADMITTED

    return HistoricalSiteEventSiteApplicabilityAdmissionResult(
        status=status,
        parcel_evidence_result=parcel_result,
        site_admission=site_admission,
        candidate_site_decision=candidate,
        missing_gates=tuple(missing),
    )
