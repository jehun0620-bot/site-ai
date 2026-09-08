from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
VERIFIED = "VERIFIED_SITE_SPATIAL_INCLUSION"
REJECTED_DESIGNATION_IDENTITY_UNVERIFIED = "REJECTED_DESIGNATION_IDENTITY_UNVERIFIED"
REJECTED_CURRENT_VALIDITY_UNVERIFIED = "REJECTED_CURRENT_VALIDITY_UNVERIFIED"
REJECTED_SPATIAL_SOURCE_UNOFFICIAL = "REJECTED_SPATIAL_SOURCE_UNOFFICIAL"
REJECTED_DESIGNATION_GEOMETRY_UNBOUND = "REJECTED_DESIGNATION_GEOMETRY_UNBOUND"
REJECTED_SITE_GEOMETRY_UNBOUND = "REJECTED_SITE_GEOMETRY_UNBOUND"
REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION = "REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION"


@dataclass(frozen=True)
class SiteSpatialEvidence:
    official_designation_identity_verified: bool
    current_validity_verified: bool
    official_spatial_source_verified: bool
    designation_geometry_bound: bool
    site_geometry_bound: bool
    positive_spatial_intersection_verified: bool


def verify_site_spatial_inclusion(
    evidence: SiteSpatialEvidence,
    *,
    address_name_hit: bool | None = None,
    search_hit: bool | None = None,
    candidate_layer_hit: bool | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify parcel inclusion from positive official spatial evidence only.

    Address/name display, search hits, or candidate-layer hits are diagnostic only.
    They cannot establish parcel inclusion. Positive inclusion requires an already
    identity-verified and currently valid designation, an official spatial source,
    both designation/site geometries, and an explicit positive spatial intersection.
    """

    if not evidence.official_designation_identity_verified:
        status = REJECTED_DESIGNATION_IDENTITY_UNVERIFIED
        spatial_verified = False
    elif not evidence.current_validity_verified:
        status = REJECTED_CURRENT_VALIDITY_UNVERIFIED
        spatial_verified = False
    elif not evidence.official_spatial_source_verified:
        status = REJECTED_SPATIAL_SOURCE_UNOFFICIAL
        spatial_verified = False
    elif not evidence.designation_geometry_bound:
        status = REJECTED_DESIGNATION_GEOMETRY_UNBOUND
        spatial_verified = False
    elif not evidence.site_geometry_bound:
        status = REJECTED_SITE_GEOMETRY_UNBOUND
        spatial_verified = False
    elif not evidence.positive_spatial_intersection_verified:
        status = REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION
        spatial_verified = False
    else:
        status = VERIFIED
        spatial_verified = True

    return {
        "resolution_type": RESOLUTION_TYPE,
        "status": status,
        "official_designation_identity_verified": (
            evidence.official_designation_identity_verified
        ),
        "current_validity_verified": evidence.current_validity_verified,
        "site_spatial_inclusion_verified": spatial_verified,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "legal_absence_inference_allowed": False,
        "negative_evidence_allowed": False,
        "evidence": {
            "official_spatial_source_verified": evidence.official_spatial_source_verified,
            "designation_geometry_bound": evidence.designation_geometry_bound,
            "site_geometry_bound": evidence.site_geometry_bound,
            "positive_spatial_intersection_verified": (
                evidence.positive_spatial_intersection_verified
            ),
        },
        "diagnostic_discovery": {
            "address_name_hit": address_name_hit,
            "search_hit": search_hit,
            "candidate_layer_hit": candidate_layer_hit,
            "dispositive": False,
        },
        "diagnostics": dict(diagnostics or {}),
    }


def verify_many(items: list[SiteSpatialEvidence]) -> list[dict[str, Any]]:
    return [verify_site_spatial_inclusion(item) for item in items]
