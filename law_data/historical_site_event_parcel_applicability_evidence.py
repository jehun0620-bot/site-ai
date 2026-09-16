"""Fail-closed parcel applicability evidence for HISTORICAL_SITE_EVENT.

This module proves only that historical-event evidence is explicitly bound to
one target parcel. It does not infer parcel ownership from source provenance,
apply a SITE decision, or authorize production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
)
from .regulation_resolution_profile_site_applicability_admission import (
    HISTORICAL_PARCEL_EVENT_BINDING,
    RegulationResolutionProfileSiteApplicabilityEvidence,
)

VERIFIED = "VERIFIED"
UNKNOWN = "UNKNOWN"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class HistoricalSiteEventParcelEvidenceInput:
    target_pnu: str
    evidence_pnu: str
    event_identity: str
    official_source_verified: bool
    parcel_binding_verified: bool
    event_binding_verified: bool


@dataclass(frozen=True)
class HistoricalSiteEventParcelApplicabilityEvidenceResult:
    status: str
    target_pnu: str
    evidence_pnu: str
    event_identity: str
    pnu_matched: bool
    official_source_verified: bool
    parcel_binding_verified: bool
    event_binding_verified: bool
    applicability_verified: bool
    applicability_state: str
    missing_gates: tuple[str, ...]
    applicability_evidence: RegulationResolutionProfileSiteApplicabilityEvidence | None
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.applicability_verified
            and self.applicability_state == "APPLIES"
            and self.applicability_evidence is not None
            and not self.missing_gates
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _valid_pnu(value: str) -> bool:
    return len(value) == 19 and value.isdigit()


def build_historical_site_event_parcel_applicability_evidence(
    canonical_site: Mapping[str, Any] | None,
    evidence_input: HistoricalSiteEventParcelEvidenceInput | None,
) -> HistoricalSiteEventParcelApplicabilityEvidenceResult:
    """Create family-specific applicability evidence only from explicit PNU binding."""

    canonical_pnu = _text(
        canonical_site.get("pnu") if isinstance(canonical_site, Mapping) else None
    )
    canonical_identity_complete = bool(
        isinstance(canonical_site, Mapping)
        and canonical_site.get("identity_status") == "COMPLETE"
        and _valid_pnu(canonical_pnu)
    )

    input_valid = isinstance(evidence_input, HistoricalSiteEventParcelEvidenceInput)
    target_pnu = _text(evidence_input.target_pnu if input_valid else None)
    evidence_pnu = _text(evidence_input.evidence_pnu if input_valid else None)
    event_identity = _text(evidence_input.event_identity if input_valid else None)

    target_pnu_valid = _valid_pnu(target_pnu)
    evidence_pnu_valid = _valid_pnu(evidence_pnu)
    pnu_matched = bool(
        canonical_identity_complete
        and target_pnu_valid
        and evidence_pnu_valid
        and canonical_pnu == target_pnu == evidence_pnu
    )

    official_source_verified = bool(
        input_valid and evidence_input.official_source_verified is True
    )
    parcel_binding_verified = bool(
        input_valid and evidence_input.parcel_binding_verified is True
    )
    event_binding_verified = bool(
        input_valid and evidence_input.event_binding_verified is True
    )

    gates = (
        ("canonical_site_identity", canonical_identity_complete),
        ("evidence_input", input_valid),
        ("target_pnu_valid", target_pnu_valid),
        ("evidence_pnu_valid", evidence_pnu_valid),
        ("pnu_matched", pnu_matched),
        ("event_identity", bool(event_identity)),
        ("official_source_verified", official_source_verified),
        ("parcel_binding_verified", parcel_binding_verified),
        ("event_binding_verified", event_binding_verified),
    )
    missing_gates = tuple(name for name, passed in gates if not passed)

    applicability_verified = not missing_gates
    if applicability_verified:
        status = VERIFIED
        applicability_state = "APPLIES"
        applicability_evidence = RegulationResolutionProfileSiteApplicabilityEvidence(
            resolver_family=HISTORICAL_SITE_EVENT,
            evidence_kind=HISTORICAL_PARCEL_EVENT_BINDING,
            target_pnu=target_pnu,
            evidence_pnu=evidence_pnu,
            applicability_verified=True,
            applicability_state="APPLIES",
        )
    else:
        hard_rejection = bool(
            not canonical_identity_complete
            or not input_valid
            or not target_pnu_valid
            or not evidence_pnu_valid
            or (
                target_pnu_valid
                and evidence_pnu_valid
                and canonical_identity_complete
                and not pnu_matched
            )
        )
        status = REJECTED if hard_rejection else UNKNOWN
        applicability_state = "UNKNOWN"
        applicability_evidence = None

    return HistoricalSiteEventParcelApplicabilityEvidenceResult(
        status=status,
        target_pnu=target_pnu,
        evidence_pnu=evidence_pnu,
        event_identity=event_identity,
        pnu_matched=pnu_matched,
        official_source_verified=official_source_verified,
        parcel_binding_verified=parcel_binding_verified,
        event_binding_verified=event_binding_verified,
        applicability_verified=applicability_verified,
        applicability_state=applicability_state,
        missing_gates=missing_gates,
        applicability_evidence=applicability_evidence,
    )
