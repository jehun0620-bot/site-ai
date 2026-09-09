from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
TARGET_SITE_ID = "11680-10300-0012-0000"
TARGET_SITE_PNU = "1168010300100120000"


@dataclass(frozen=True)
class Uqq700SiteGeometryProvenance:
    site_id: str
    site_pnu: str
    geometry_id: str
    geometry_type: str
    geometry_present: bool
    geometry_pnu: str
    source_id: str
    source_snapshot_verified: bool
    crs_id: str = ""
    crs_verified: bool = False


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def adapt_uqq700_site_geometry_provenance(
    evidence: Uqq700SiteGeometryProvenance,
    *,
    diagnostics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind an already recovered parcel geometry to the canonical target SITE.

    This is a SITE-side provenance adapter only. It does not identify UQQ700
    designation geometry, verify an official UQQ700 spatial source, perform an
    intersection, verify Gate 3, promote SITE, or mutate runtime state.

    The SITE binding is fail-closed: both the canonical SITE ID and canonical
    PNU must match exactly, and the recovered geometry PNU must match that PNU.
    CRS provenance is exposed separately and never makes this adapter
    intersection-ready by itself.
    """

    site_id = _text(evidence.site_id)
    site_pnu = _text(evidence.site_pnu)
    geometry_id = _text(evidence.geometry_id)
    geometry_type = _text(evidence.geometry_type)
    geometry_pnu = _text(evidence.geometry_pnu)
    source_id = _text(evidence.source_id)
    crs_id = _text(evidence.crs_id)

    canonical_site_identity_matches = bool(
        site_id == TARGET_SITE_ID
        and site_pnu == TARGET_SITE_PNU
    )
    geometry_identity_present = bool(geometry_id and source_id)
    parcel_identity_matches = bool(
        site_pnu == TARGET_SITE_PNU
        and geometry_pnu == TARGET_SITE_PNU
    )
    polygon_geometry_present = bool(
        evidence.geometry_present is True
        and geometry_type in {"Polygon", "MultiPolygon"}
    )
    source_snapshot_verified = bool(
        source_id and evidence.source_snapshot_verified is True
    )
    explicit_crs_verified = bool(
        crs_id and evidence.crs_verified is True
    )

    site_geometry_bound = bool(
        canonical_site_identity_matches
        and geometry_identity_present
        and parcel_identity_matches
        and polygon_geometry_present
        and source_snapshot_verified
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "site_geometry_id": geometry_id if site_geometry_bound else "",
        "site_geometry_bound_to_target_site": site_geometry_bound,
        "site_geometry_provenance": {
            "site_id": site_id,
            "site_pnu": site_pnu,
            "canonical_site_id": TARGET_SITE_ID,
            "canonical_site_pnu": TARGET_SITE_PNU,
            "canonical_site_identity_matches": canonical_site_identity_matches,
            "geometry_pnu": geometry_pnu,
            "geometry_type": geometry_type,
            "source_id": source_id if source_snapshot_verified else "",
            "source_snapshot_verified": source_snapshot_verified,
            "parcel_identity_matches": parcel_identity_matches,
            "polygon_geometry_present": polygon_geometry_present,
            "crs_id": crs_id if explicit_crs_verified else "",
            "crs_verified": explicit_crs_verified,
        },
        "crs_verified": explicit_crs_verified,
        "intersection_ready": False,
        "official_spatial_source_verified": False,
        "designation_geometry_bound": False,
        "positive_spatial_intersection_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
        "runtime_registration_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "legal_absence_inference_allowed": False,
        "negative_evidence_allowed": False,
        "diagnostics": dict(diagnostics or {}),
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
    }
