# -*- coding: utf-8 -*-

"""SITE Identity Resolver.

Identity values from persisted/fallback sources may only be reused when that
source is bound to the same canonical PNU as the current SITE. Caller-provided
values remain authoritative.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
QUERY_CONTEXT_PATH = OUTPUT_DIR / "site_spatial_query_context.json"
PARCEL_PROBE_PATH = OUTPUT_DIR / "vworld_parcel_polygon_identifier_probe.json"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def usable(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def first_value(*values: Any) -> Any:
    for value in values:
        if usable(value):
            return value
    return None


def normalize_site_input(site: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return copy.deepcopy(site) if site else {}


def _pnu(value: Any) -> str:
    return str(value or "").strip()


def _same_pnu(resolved_pnu: str, source: Dict[str, Any]) -> bool:
    source_pnu = _pnu(source.get("pnu"))
    return bool(resolved_pnu and source_pnu and resolved_pnu == source_pnu)


def _guarded(source: Dict[str, Any], key: str, allowed: bool) -> Any:
    return source.get(key) if allowed else None


def resolve_site_identity(
    base_site: Optional[Dict[str, Any]] = None,
    site_input: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    base_site = normalize_site_input(base_site)
    site_input = normalize_site_input(site_input)
    query_data = load_json(QUERY_CONTEXT_PATH)
    parcel_data = load_json(PARCEL_PROBE_PATH)
    query = query_data.get("query_context", {})
    parcel_site = parcel_data.get("site", {})
    point = parcel_site.get("point", {})

    # Resolve PNU first. It is the boundary used to decide whether persisted
    # identity evidence belongs to this SITE.
    pnu = first_value(
        site_input.get("pnu"),
        base_site.get("pnu"),
        query.get("pnu"),
        parcel_site.get("pnu"),
    )
    resolved_pnu = _pnu(pnu)
    same_base = _same_pnu(resolved_pnu, base_site)
    same_query = _same_pnu(resolved_pnu, query)
    same_parcel = _same_pnu(resolved_pnu, parcel_site)

    site_id = first_value(
        site_input.get("site_id"),
        _guarded(base_site, "site_id", same_base),
        _guarded(query, "site_id", same_query),
        _guarded(parcel_site, "site_id", same_parcel),
    )
    address = first_value(
        site_input.get("address"),
        _guarded(base_site, "address", same_base),
        _guarded(query, "address", same_query),
        _guarded(parcel_site, "address", same_parcel),
    )
    road_address = first_value(
        site_input.get("road_address"),
        site_input.get("road_name_address"),
        _guarded(base_site, "road_address", same_base),
        _guarded(query, "road_address", same_query),
    )
    zone = first_value(
        site_input.get("zone"),
        site_input.get("land_use_zone"),
        _guarded(base_site, "zone", same_base),
        _guarded(base_site, "land_use_zone", same_base),
        _guarded(query, "zone", same_query),
        _guarded(parcel_site, "zone", same_parcel),
    )
    sigungu_code = first_value(
        site_input.get("sigungu_code"), site_input.get("sigungu_cd"),
        _guarded(base_site, "sigungu_code", same_base),
        _guarded(base_site, "sigungu_cd", same_base),
        _guarded(query, "sigungu_code", same_query),
    )
    bjdong_code = first_value(
        site_input.get("bjdong_code"), site_input.get("bjdong_cd"),
        _guarded(base_site, "bjdong_code", same_base),
        _guarded(base_site, "bjdong_cd", same_base),
        _guarded(query, "bjdong_code", same_query),
    )
    main_no = first_value(
        site_input.get("main_no"), site_input.get("bun"),
        _guarded(base_site, "main_no", same_base),
        _guarded(base_site, "bun", same_base),
        _guarded(query, "main_no", same_query),
    )
    sub_no = first_value(
        site_input.get("sub_no"), site_input.get("ji"),
        _guarded(base_site, "sub_no", same_base),
        _guarded(base_site, "ji", same_base),
        _guarded(query, "sub_no", same_query),
    )

    base_coordinate = base_site.get("coordinate", {}) if isinstance(base_site.get("coordinate"), dict) else {}
    base_x = first_value(base_site.get("x"), base_coordinate.get("x")) if same_base else None
    base_y = first_value(base_site.get("y"), base_coordinate.get("y")) if same_base else None
    parcel_x = point.get("x") if same_parcel else None
    parcel_y = point.get("y") if same_parcel else None
    x = first_value(site_input.get("x"), site_input.get("longitude"), base_x, parcel_x)
    y = first_value(site_input.get("y"), site_input.get("latitude"), base_y, parcel_y)
    coordinate_crs = first_value(
        site_input.get("coordinate_crs"),
        base_coordinate.get("crs") if same_base else None,
        point.get("crs") if same_parcel else None,
    )

    identity = {
        "site_id": site_id,
        "address": address,
        "road_address": road_address,
        "pnu": pnu,
        "sigungu_code": sigungu_code,
        "bjdong_code": bjdong_code,
        "main_no": main_no,
        "sub_no": sub_no,
        "zone": zone,
        "land_use_zone": zone,
        "coordinate": {"x": x, "y": y, "crs": coordinate_crs},
        "x": x,
        "y": y,
    }
    required_identity = [
        "site_id", "address", "pnu", "sigungu_code", "bjdong_code",
        "main_no", "sub_no", "zone",
    ]
    missing_identity = [key for key in required_identity if not usable(identity.get(key))]
    identity["identity_status"] = "COMPLETE" if not missing_identity else "PARTIAL"
    identity["coordinate_status"] = "CONFIRMED" if usable(x) and usable(y) else "MISSING"
    identity["missing_identity_fields"] = missing_identity

    selected_parcel = parcel_data.get("selected", {})
    identity["parcel_reference"] = {
        "dataset": selected_parcel.get("dataset"),
        "status": selected_parcel.get("status"),
        "strict_pnu_verified": selected_parcel.get("strict_pnu_verified"),
        "geometry_loaded": False,
        "note": "Parcel dataset은 검증되었으나 geometry 자체는 이번 identity object에 아직 포함하지 않음",
    }
    return identity
