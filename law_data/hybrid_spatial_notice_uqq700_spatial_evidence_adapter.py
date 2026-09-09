from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_site_spatial_inclusion_verifier import (
    SiteSpatialEvidence,
    verify_site_spatial_inclusion,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"


@dataclass(frozen=True)
class Uqq700SpatialProvenance:
    official_designation_identity_verified: bool
    current_validity_verified: bool

    spatial_source_id: str
    official_spatial_source_verified: bool

    designation_geometry_id: str
    designation_geometry_bound_to_verified_designation: bool

    site_geometry_id: str
    site_geometry_bound_to_target_site: bool

    positive_spatial_intersection_verified: bool


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def adapt_uqq700_spatial_evidence(
    evidence: Uqq700SpatialProvenance,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Create Gate-3 evidence only from explicit positive spatial provenance.

    This adapter does not perform geometry operations. It accepts only already
    verified provenance for the official designation geometry, target-site geometry,
    and their positive spatial intersection. Address/name display, search hits,
    candidate-layer hits, EUM presence, HTTP success, bbox/centroid proximity, and
    negative evidence remain diagnostic and non-dispositive.
    """

    spatial_source_id = _text(evidence.spatial_source_id)
    designation_geometry_id = _text(evidence.designation_geometry_id)
    site_geometry_id = _text(evidence.site_geometry_id)

    official_spatial_source_verified = bool(
        spatial_source_id and evidence.official_spatial_source_verified is True
    )
    designation_geometry_bound = bool(
        designation_geometry_id
        and evidence.designation_geometry_bound_to_verified_designation is True
    )
    site_geometry_bound = bool(
        site_geometry_id and evidence.site_geometry_bound_to_target_site is True
    )

    verifier_result = verify_site_spatial_inclusion(
        SiteSpatialEvidence(
            official_designation_identity_verified=(
                evidence.official_designation_identity_verified is True
            ),
            current_validity_verified=evidence.current_validity_verified is True,
            official_spatial_source_verified=official_spatial_source_verified,
            designation_geometry_bound=designation_geometry_bound,
            site_geometry_bound=site_geometry_bound,
            positive_spatial_intersection_verified=(
                evidence.positive_spatial_intersection_verified is True
            ),
        ),
        diagnostics=dict(diagnostics or {}),
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        **verifier_result,
        "spatial_provenance": {
            "spatial_source_id": spatial_source_id if official_spatial_source_verified else "",
            "designation_geometry_id": (
                designation_geometry_id if designation_geometry_bound else ""
            ),
            "site_geometry_id": site_geometry_id if site_geometry_bound else "",
            "official_spatial_source_verified": official_spatial_source_verified,
            "designation_geometry_bound": designation_geometry_bound,
            "site_geometry_bound": site_geometry_bound,
            "positive_spatial_intersection_verified": (
                evidence.positive_spatial_intersection_verified is True
            ),
        },
        "address_name_display_dispositive": False,
        "search_hit_dispositive": False,
        "candidate_layer_hit_dispositive": False,
        "eum_page_presence_dispositive": False,
        "http_success_dispositive": False,
        "bbox_proximity_dispositive": False,
        "centroid_proximity_dispositive": False,
        "same_district_name_dispositive": False,
        "negative_evidence_dispositive": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
