from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from law_data.parcel_geometry_provider import (
    PARCEL_DATASET,
    find_feature_pnu,
    is_polygon_geometry,
    load_vworld_key,
    query_dataset_by_point,
)
from site_data.address_parcel_identity_resolver import parcel_identity_from_pnu


@dataclass(frozen=True)
class SelectedParcelCandidateVerification:
    status: str
    resolution: str
    pnu: str = ""
    sigungu_cd: str = ""
    bjdong_cd: str = ""
    plat_gb_cd: str = ""
    bun: str = ""
    ji: str = ""
    x: Optional[float] = None
    y: Optional[float] = None
    crs: str = ""

    @property
    def verified(self) -> bool:
        return self.status == "VERIFIED" and self.resolution == "SELECTED_PARCEL_CANDIDATE_VERIFIED"


def _valid_pnu(value: str) -> str:
    pnu = str(value or "").strip()
    return pnu if len(pnu) == 19 and pnu.isdigit() else ""


def verify_selected_parcel_candidate(
    candidate_pnu: str,
    x: float,
    y: float,
    api_key: Optional[str] = None,
) -> SelectedParcelCandidateVerification:
    pnu = _valid_pnu(candidate_pnu)
    if not pnu:
        return SelectedParcelCandidateVerification("REJECTED", "CANDIDATE_PNU_INVALID")

    try:
        point_x = float(x)
        point_y = float(y)
    except (TypeError, ValueError):
        return SelectedParcelCandidateVerification("REJECTED", "CANDIDATE_POINT_INVALID", pnu=pnu)

    if not (-180.0 <= point_x <= 180.0 and -90.0 <= point_y <= 90.0):
        return SelectedParcelCandidateVerification("REJECTED", "CANDIDATE_POINT_INVALID", pnu=pnu)

    key = str(api_key or load_vworld_key() or "").strip()
    if not key:
        return SelectedParcelCandidateVerification(
            "REJECTED", "VWORLD_KEY_MISSING", pnu=pnu, x=point_x, y=point_y, crs="EPSG:4326"
        )

    result = query_dataset_by_point(key, PARCEL_DATASET, point_x, point_y)
    if not isinstance(result, dict):
        return SelectedParcelCandidateVerification(
            "REJECTED", "PARCEL_GEOMETRY_QUERY_FAILED", pnu=pnu, x=point_x, y=point_y, crs="EPSG:4326"
        )

    features = result.get("features", [])
    if not isinstance(features, list):
        features = []

    polygon_pnus = []
    for feature in features:
        if not isinstance(feature, dict) or not is_polygon_geometry(feature):
            continue
        _, feature_pnu = find_feature_pnu(feature)
        if feature_pnu and feature_pnu not in polygon_pnus:
            polygon_pnus.append(feature_pnu)

    if not polygon_pnus:
        return SelectedParcelCandidateVerification(
            "REJECTED", "PARCEL_POLYGON_UNRESOLVED", pnu=pnu, x=point_x, y=point_y, crs="EPSG:4326"
        )

    if pnu not in polygon_pnus:
        return SelectedParcelCandidateVerification(
            "REJECTED", "SELECTED_PNU_POLYGON_MISMATCH", pnu=pnu, x=point_x, y=point_y, crs="EPSG:4326"
        )

    try:
        identity = parcel_identity_from_pnu(pnu)
    except ValueError:
        return SelectedParcelCandidateVerification(
            "REJECTED", "CANDIDATE_PNU_INVALID", pnu=pnu, x=point_x, y=point_y, crs="EPSG:4326"
        )

    return SelectedParcelCandidateVerification(
        status="VERIFIED",
        resolution="SELECTED_PARCEL_CANDIDATE_VERIFIED",
        pnu=pnu,
        x=point_x,
        y=point_y,
        crs="EPSG:4326",
        **identity,
    )
