from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


class AuthorityQualification(str, Enum):
    QUALIFIED_OFFICIAL_AUTHORITY_SOURCE = "QUALIFIED_OFFICIAL_AUTHORITY_SOURCE"
    REJECTED_NON_OFFICIAL_HOST = "REJECTED_NON_OFFICIAL_HOST"
    REJECTED_REGION_UNBOUND = "REJECTED_REGION_UNBOUND"
    REJECTED_ROLE_WEAK = "REJECTED_ROLE_WEAK"
    REJECTED_DETAIL_DOCUMENT = "REJECTED_DETAIL_DOCUMENT"
    REJECTED_INVALID_URL = "REJECTED_INVALID_URL"


@dataclass(frozen=True)
class AuthoritySourceCandidate:
    url: str
    authority_name: str | None = None
    region: str | None = None
    title: str | None = None
    heading: str | None = None
    breadcrumb: str | None = None
    endpoint_role: str | None = None
    official_host_verified: bool = False
    region_binding_verified: bool = False
    entry_endpoint_verified: bool = False
    role_verified: bool = False


def qualify_authority_source(
    candidate: AuthoritySourceCandidate,
    *,
    diagnostic_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Qualify a competent official source without proving designation identity.

    This resolver intentionally stops at authority/source qualification.
    A qualified official source MUST NOT be interpreted as:
    - an identity-verified designation notice,
    - proof of current legal validity,
    - proof of SITE spatial inclusion,
    - permission for SITE promotion or runtime registration.
    """

    parsed = urlparse(candidate.url)
    url_valid = parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    if not url_valid:
        qualification = AuthorityQualification.REJECTED_INVALID_URL
    elif not candidate.official_host_verified:
        qualification = AuthorityQualification.REJECTED_NON_OFFICIAL_HOST
    elif not candidate.region_binding_verified:
        qualification = AuthorityQualification.REJECTED_REGION_UNBOUND
    elif not candidate.entry_endpoint_verified:
        qualification = AuthorityQualification.REJECTED_DETAIL_DOCUMENT
    elif not candidate.role_verified:
        qualification = AuthorityQualification.REJECTED_ROLE_WEAK
    else:
        qualification = AuthorityQualification.QUALIFIED_OFFICIAL_AUTHORITY_SOURCE

    authority_source_qualified = (
        qualification == AuthorityQualification.QUALIFIED_OFFICIAL_AUTHORITY_SOURCE
    )

    return {
        "resolution_type": RESOLUTION_TYPE,
        "qualification": qualification.value,
        "authority_source_qualified": authority_source_qualified,
        "candidate": {
            "url": candidate.url,
            "authority_name": candidate.authority_name,
            "region": candidate.region,
            "title": candidate.title,
            "heading": candidate.heading,
            "breadcrumb": candidate.breadcrumb,
            "endpoint_role": candidate.endpoint_role,
        },
        "verification": {
            "official_host_verified": candidate.official_host_verified,
            "region_binding_verified": candidate.region_binding_verified,
            "entry_endpoint_verified": candidate.entry_endpoint_verified,
            "role_verified": candidate.role_verified,
        },
        "designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_promotion_allowed": False,
        "site_false_inference_allowed": False,
        "legal_absence_inference_allowed": False,
        "negative_evidence_allowed": False,
        "diagnostic_evidence": {
            "items": dict(diagnostic_evidence or {}),
            "dispositive_for_designation_identity": False,
            "dispositive_for_legal_absence": False,
        },
    }


def qualify_authority_sources(
    candidates: Sequence[AuthoritySourceCandidate],
) -> list[dict[str, Any]]:
    """Pure batch wrapper. Input order is preserved and no external I/O occurs."""
    return [qualify_authority_source(candidate) for candidate in candidates]
