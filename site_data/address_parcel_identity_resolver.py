from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from law_data.parcel_geometry_provider import (
    PARCEL_DATASET,
    find_feature_pnu,
    is_polygon_geometry,
    load_vworld_key,
    query_dataset_by_point,
    request_json,
)
from site_data.vworld_api import create_pnu

VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"


@dataclass(frozen=True)
class AddressParcelIdentityResolution:
    status: str
    resolution: str
    address: str
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
        return self.status == "VERIFIED" and self.resolution == "ADDRESS_PARCEL_IDENTITY_VERIFIED"


def parcel_identity_from_pnu(pnu: str) -> Dict[str, str]:
    value = str(pnu or "").strip()
    if len(value) != 19 or not value.isdigit():
        raise ValueError("PNU는 19자리 숫자여야 합니다.")

    land_gbn = value[10]
    plat_by_land_gbn = {"1": "0", "2": "1"}
    if land_gbn not in plat_by_land_gbn:
        raise ValueError("PNU 필지구분은 1(일반) 또는 2(산)이어야 합니다.")

    identity = {
        "sigungu_cd": value[:5],
        "bjdong_cd": value[5:10],
        "plat_gb_cd": plat_by_land_gbn[land_gbn],
        "bun": value[11:15],
        "ji": value[15:19],
    }
    rebuilt = create_pnu(**identity)
    if rebuilt != value:
        raise ValueError("PNU 구성요소 재생성 결과가 원본 PNU와 일치하지 않습니다.")
    return identity


def _search_address_items(address: str, api_key: str) -> List[Dict[str, Any]]:
    normalized = str(address or "").strip()
    if not normalized:
        return []

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": normalized,
        "type": "address",
        "category": "parcel",
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }
    response, data, transport_error = request_json(VWORLD_SEARCH_URL, params)
    if transport_error or response is None or response.status_code != 200:
        return []
    response_data = data.get("response", {}) if isinstance(data, dict) else {}
    if str(response_data.get("status") or "").strip().upper() != "OK":
        return []
    result = response_data.get("result", {})
    items = result.get("items", []) if isinstance(result, dict) else []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _point(item: Dict[str, Any]) -> Optional[tuple[float, float]]:
    point = item.get("point", {}) if isinstance(item, dict) else {}
    try:
        return float(point.get("x")), float(point.get("y"))
    except (TypeError, ValueError):
        return None


def _address_item_pnu(item: Dict[str, Any]) -> str:
    value = str(item.get("id") or "").strip() if isinstance(item, dict) else ""
    return value if len(value) == 19 and value.isdigit() else ""


def _parcel_pnus_at_point(api_key: str, x: float, y: float) -> List[str]:
    result = query_dataset_by_point(api_key, PARCEL_DATASET, x, y)
    features = result.get("features", []) if isinstance(result, dict) else []
    pnus: List[str] = []
    if not isinstance(features, list):
        return pnus
    for feature in features:
        if not isinstance(feature, dict) or not is_polygon_geometry(feature):
            continue
        _, pnu = find_feature_pnu(feature)
        if pnu and pnu not in pnus:
            pnus.append(pnu)
    return pnus


def resolve_address_parcel_identity(address: str, api_key: Optional[str] = None) -> AddressParcelIdentityResolution:
    normalized = str(address or "").strip()
    if not normalized:
        return AddressParcelIdentityResolution("REJECTED", "ADDRESS_MISSING", normalized)

    key = str(api_key or load_vworld_key() or "").strip()
    if not key:
        return AddressParcelIdentityResolution("REJECTED", "VWORLD_KEY_MISSING", normalized)

    items = _search_address_items(normalized, key)
    if not items:
        return AddressParcelIdentityResolution("REJECTED", "ADDRESS_RESULT_EMPTY", normalized)

    candidates: Dict[str, tuple[float, float]] = {}
    mismatch_seen = False
    for item in items:
        address_pnu = _address_item_pnu(item)
        point = _point(item)
        if not address_pnu or point is None:
            continue
        x, y = point
        polygon_pnus = _parcel_pnus_at_point(key, x, y)
        if address_pnu not in polygon_pnus:
            mismatch_seen = True
            continue
        candidates.setdefault(address_pnu, (x, y))

    if not candidates:
        resolution = "ADDRESS_POLYGON_PNU_MISMATCH" if mismatch_seen else "PARCEL_PNU_UNRESOLVED"
        return AddressParcelIdentityResolution("REJECTED", resolution, normalized)
    if len(candidates) != 1:
        return AddressParcelIdentityResolution("REJECTED", "ADDRESS_PARCEL_AMBIGUOUS", normalized)

    pnu, (x, y) = next(iter(candidates.items()))
    try:
        identity = parcel_identity_from_pnu(pnu)
    except ValueError:
        return AddressParcelIdentityResolution("REJECTED", "PARCEL_PNU_INVALID", normalized)

    return AddressParcelIdentityResolution(
        status="VERIFIED",
        resolution="ADDRESS_PARCEL_IDENTITY_VERIFIED",
        address=normalized,
        pnu=pnu,
        x=x,
        y=y,
        crs="EPSG:4326",
        **identity,
    )
