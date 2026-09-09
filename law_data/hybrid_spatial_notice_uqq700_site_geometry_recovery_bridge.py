from __future__ import annotations

from typing import Any, Mapping

from law_data.hybrid_spatial_notice_uqq700_site_geometry_provenance_adapter import (
    Uqq700SiteGeometryProvenance,
    adapt_uqq700_site_geometry_provenance,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
TARGET_SITE_ID = "11680-10300-0012-0000"
TARGET_SITE_PNU = "1168010300100120000"
EXPECTED_DATASET = "MapPlan"

_REQUIRED_VALIDATIONS = (
    "feature recovered",
    "target PNU",
    "geometry dict",
    "geometry Polygon",
    "coordinates exist",
    "calculated bounds",
    "expected bounds match",
    "area evidence found",
    "bounds evidence found",
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def bridge_uqq700_site_geometry_recovery(
    recovery: Mapping[str, Any],
    *,
    site_id: str,
    source_snapshot_verified: bool,
) -> dict[str, Any]:
    """Convert existing MapPlan parcel recovery evidence into SITE provenance.

    This bridge is intentionally limited to the target SITE parcel geometry.
    It does not verify UQQ700 designation geometry, an official UQQ700 spatial
    source, a positive intersection, Gate 3, SITE truth, or runtime eligibility.
    """

    site = _mapping(recovery.get("site"))
    source = _mapping(recovery.get("source"))
    parcel = _mapping(recovery.get("parcel"))
    validations = _mapping(recovery.get("validations"))

    normalized_site_id = _text(site_id)
    recovered_pnu = _text(site.get("pnu"))
    dataset = _text(source.get("dataset"))
    snapshot = _text(source.get("snapshot"))
    recovery_source = _mapping(source.get("recovery"))
    recovery_mode = _text(recovery_source.get("mode"))
    geometry_type = _text(parcel.get("geometry_type"))
    geometry_snapshot = _text(parcel.get("geometry_snapshot"))
    crs_status = _text(parcel.get("crs_status"))
    stored_crs = parcel.get("crs")

    exact_site_identity_verified = bool(
        normalized_site_id == TARGET_SITE_ID
        and recovered_pnu == TARGET_SITE_PNU
    )
    recovery_validations_verified = bool(
        recovery.get("all_pass") is True
        and all(validations.get(name) is True for name in _REQUIRED_VALIDATIONS)
    )
    recovery_source_verified = bool(
        dataset == EXPECTED_DATASET
        and snapshot
        and recovery_mode in {"DIRECT_JSON", "EMBEDDED_JSON_STRING"}
        and geometry_snapshot
        and source_snapshot_verified is True
    )
    polygon_verified = bool(
        geometry_type in {"Polygon", "MultiPolygon"}
        and validations.get("geometry dict") is True
        and validations.get("coordinates exist") is True
    )

    site_geometry_provenance_verified = bool(
        exact_site_identity_verified
        and recovery_validations_verified
        and recovery_source_verified
        and polygon_verified
    )

    crs_verified = bool(
        stored_crs
        and crs_status == "RECOVERED"
    )

    adapter_input = Uqq700SiteGeometryProvenance(
        site_id=TARGET_SITE_ID if exact_site_identity_verified else "",
        site_pnu=TARGET_SITE_PNU if exact_site_identity_verified else "",
        geometry_id=(
            f"mapplan-parcel:{TARGET_SITE_PNU}"
            if site_geometry_provenance_verified
            else ""
        ),
        geometry_type=geometry_type if polygon_verified else "",
        geometry_present=site_geometry_provenance_verified,
        geometry_pnu=recovered_pnu if site_geometry_provenance_verified else "",
        source_id=snapshot if recovery_source_verified else "",
        source_snapshot_verified=recovery_source_verified,
    )

    adapted = adapt_uqq700_site_geometry_provenance(
        adapter_input,
        diagnostics={
            "bridge": "MAPPLAN_PARCEL_SPATIAL_RECOVERY",
            "recovery_mode": recovery_mode,
            "crs_status": crs_status,
            "crs_verified": crs_verified,
        },
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "exact_site_identity_verified": exact_site_identity_verified,
        "recovery_validations_verified": recovery_validations_verified,
        "recovery_source_verified": recovery_source_verified,
        "polygon_verified": polygon_verified,
        "site_geometry_provenance_verified": site_geometry_provenance_verified,
        "site_geometry_id": adapted["site_geometry_id"],
        "site_geometry_bound_to_target_site": adapted[
            "site_geometry_bound_to_target_site"
        ],
        "crs_verified": crs_verified,
        "crs_status": crs_status,
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
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "site_mutated": False,
        "adapter_result": adapted,
    }
