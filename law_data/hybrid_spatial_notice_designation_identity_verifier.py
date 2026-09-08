from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
VERIFIED = "VERIFIED_OFFICIAL_DESIGNATION_IDENTITY"
REJECTED_CANDIDATE_UNQUALIFIED = "REJECTED_CANDIDATE_UNQUALIFIED"
REJECTED_AUTHORITY_UNQUALIFIED = "REJECTED_AUTHORITY_UNQUALIFIED"
REJECTED_TARGET_UNBOUND = "REJECTED_TARGET_UNBOUND"
REJECTED_DESIGNATION_ACT_UNBOUND = "REJECTED_DESIGNATION_ACT_UNBOUND"
REJECTED_NOTICE_IDENTITY_INSUFFICIENT = "REJECTED_NOTICE_IDENTITY_INSUFFICIENT"


@dataclass(frozen=True)
class DesignationIdentityEvidence:
    candidate_qualified: bool
    authority_source_qualified: bool
    target_name_bound: bool
    designation_act_bound: bool
    notice_number_bound: bool
    issuing_authority_bound: bool
    effective_or_notice_date_bound: bool

    @property
    def notice_identity_sufficient(self) -> bool:
        return (
            self.notice_number_bound
            and self.issuing_authority_bound
            and self.effective_or_notice_date_bound
        )


def verify_designation_identity(
    evidence: DesignationIdentityEvidence,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify official designation-document identity without inferring later gates.

    This verifier answers only whether a previously qualified historical notice
    candidate is sufficiently bound to the target designation act and official
    notice identity. A successful identity verification does not establish current
    validity, parcel inclusion, SITE TRUE, or runtime registration eligibility.
    """

    if not evidence.candidate_qualified:
        status = REJECTED_CANDIDATE_UNQUALIFIED
        identity_verified = False
    elif not evidence.authority_source_qualified:
        status = REJECTED_AUTHORITY_UNQUALIFIED
        identity_verified = False
    elif not evidence.target_name_bound:
        status = REJECTED_TARGET_UNBOUND
        identity_verified = False
    elif not evidence.designation_act_bound:
        status = REJECTED_DESIGNATION_ACT_UNBOUND
        identity_verified = False
    elif not evidence.notice_identity_sufficient:
        status = REJECTED_NOTICE_IDENTITY_INSUFFICIENT
        identity_verified = False
    else:
        status = VERIFIED
        identity_verified = True

    return {
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "official_designation_identity_verified": identity_verified,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "legal_absence_inference_allowed": False,
        "negative_evidence_allowed": False,
        "evidence": {
            "candidate_qualified": evidence.candidate_qualified,
            "authority_source_qualified": evidence.authority_source_qualified,
            "target_name_bound": evidence.target_name_bound,
            "designation_act_bound": evidence.designation_act_bound,
            "notice_number_bound": evidence.notice_number_bound,
            "issuing_authority_bound": evidence.issuing_authority_bound,
            "effective_or_notice_date_bound": evidence.effective_or_notice_date_bound,
            "notice_identity_sufficient": evidence.notice_identity_sufficient,
        },
        "diagnostics": dict(diagnostics or {}),
    }


def verify_many(
    items: list[DesignationIdentityEvidence],
) -> list[dict[str, Any]]:
    return [verify_designation_identity(item) for item in items]
