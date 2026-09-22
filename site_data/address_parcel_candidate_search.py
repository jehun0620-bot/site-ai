from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import re
from typing import Any, Dict, List, Optional

from law_data.parcel_geometry_provider import (
    PARCEL_DATASET,
    find_feature_pnu,
    is_polygon_geometry,
    load_vworld_key,
    query_dataset_by_point,
    request_json,
)

VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"


class AddressParcelCandidateSearchProviderError(RuntimeError):
    """Raised when candidate discovery cannot distinguish results because the provider failed."""



@dataclass(frozen=True)
class AddressParcelCandidate:
    candidate_pnu: str
    parcel_address: str
    road_address: str
    building_name: str
    x: float
    y: float
    crs: str = "EPSG:4326"
    reference_geometry: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _normalize_search_query(query: str) -> str:
    value = " ".join(str(query or "").strip().split())
    return re.sub(r"(?<=\d)번지$", "", value).strip()


def _candidate_from_item(item: Dict[str, Any]) -> Optional[AddressParcelCandidate]:
    if not isinstance(item, dict):
        return None

    pnu = str(item.get("id") or "").strip()
    if len(pnu) != 19 or not pnu.isdigit():
        return None

    address = item.get("address", {})
    point = item.get("point", {})
    if not isinstance(address, dict) or not isinstance(point, dict):
        return None

    parcel_address = " ".join(str(address.get("parcel") or "").strip().split())
    if not parcel_address:
        return None

    try:
        x = float(point.get("x"))
        y = float(point.get("y"))
    except (TypeError, ValueError):
        return None

    return AddressParcelCandidate(
        candidate_pnu=pnu,
        parcel_address=parcel_address,
        road_address=" ".join(str(address.get("road") or "").strip().split()),
        building_name=" ".join(str(address.get("bldnm") or "").strip().split()),
        x=x,
        y=y,
    )


def _reference_geometry_for_candidate(
    candidate: AddressParcelCandidate,
    api_key: str,
) -> Optional[Dict[str, Any]]:
    """Return discovery-only parcel geometry when the feature PNU matches.

    This is not canonical parcel verification. The existing selected-candidate
    verification boundary must still be executed before VERIFIED state or SITE
    analysis admission.
    """
    result = query_dataset_by_point(
        api_key,
        PARCEL_DATASET,
        candidate.x,
        candidate.y,
    )
    if not isinstance(result, dict):
        return None

    features = result.get("features", [])
    if not isinstance(features, list):
        return None

    for feature in features:
        if not isinstance(feature, dict) or not is_polygon_geometry(feature):
            continue
        _, feature_pnu = find_feature_pnu(feature)
        if feature_pnu != candidate.candidate_pnu:
            continue
        geometry = feature.get("geometry")
        if isinstance(geometry, dict) and geometry.get("type") in {"Polygon", "MultiPolygon"}:
            return geometry
    return None


def _search_items(
    query: str,
    api_key: str,
    *,
    category: str,
    size: int,
) -> List[Dict[str, Any]]:
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": size,
        "page": 1,
        "query": query,
        "type": "address",
        "category": category,
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }
    response, data, transport_error = request_json(VWORLD_SEARCH_URL, params)
    if transport_error or response is None:
        raise AddressParcelCandidateSearchProviderError(
            f"VWorld address search transport failure: {transport_error or 'missing response'}"
        )
    if response.status_code != 200:
        raise AddressParcelCandidateSearchProviderError(
            f"VWorld address search HTTP failure: {response.status_code}"
        )

    response_data = data.get("response", {}) if isinstance(data, dict) else {}
    status = str(response_data.get("status") or "").strip().upper()
    if status == "NOT_FOUND":
        return []
    if status != "OK":
        raise AddressParcelCandidateSearchProviderError(
            f"VWorld address search provider failure: {status or 'missing status'}"
        )

    result = response_data.get("result", {})
    items = result.get("items", []) if isinstance(result, dict) else []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def search_address_parcel_candidates(
    query: str,
    *,
    api_key: Optional[str] = None,
    size: int = 10,
) -> List[AddressParcelCandidate]:
    """Return provider parcel candidates for discovery only.

    Parcel-address discovery remains the primary provider query. When that
    returns no usable provider items, road-address discovery is attempted as a
    fallback. Results from either mode are deduplicated by PNU and remain
    discovery-only until the separate backend parcel verification boundary is
    executed.
    """
    normalized = _normalize_search_query(query)
    if not normalized:
        return []

    key = str(api_key or load_vworld_key() or "").strip()
    if not key:
        return []

    safe_size = max(1, min(int(size), 100))
    items = _search_items(normalized, key, category="parcel", size=safe_size)
    if not items:
        items = _search_items(normalized, key, category="road", size=safe_size)

    candidates: List[AddressParcelCandidate] = []
    seen_pnus = set()
    for item in items:
        candidate = _candidate_from_item(item)
        if candidate is None or candidate.candidate_pnu in seen_pnus:
            continue
        seen_pnus.add(candidate.candidate_pnu)
        reference_geometry = _reference_geometry_for_candidate(candidate, key)
        candidates.append(replace(candidate, reference_geometry=reference_geometry))
    return candidates
