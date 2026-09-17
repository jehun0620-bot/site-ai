from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any, Dict, List, Optional

from law_data.parcel_geometry_provider import load_vworld_key, request_json

VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"


@dataclass(frozen=True)
class AddressParcelCandidate:
    candidate_pnu: str
    parcel_address: str
    road_address: str
    building_name: str
    x: float
    y: float
    crs: str = "EPSG:4326"

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


def search_address_parcel_candidates(
    query: str,
    *,
    api_key: Optional[str] = None,
    size: int = 10,
) -> List[AddressParcelCandidate]:
    """Return provider parcel candidates for discovery only.

    Results are intentionally NOT VERIFIED canonical parcel identities. Analysis
    admission requires a separate backend parcel verification boundary.
    """
    normalized = _normalize_search_query(query)
    if not normalized:
        return []

    key = str(api_key or load_vworld_key() or "").strip()
    if not key:
        return []

    safe_size = max(1, min(int(size), 100))
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": safe_size,
        "page": 1,
        "query": normalized,
        "type": "address",
        "category": "parcel",
        "format": "json",
        "errorformat": "json",
        "key": key,
    }
    response, data, transport_error = request_json(VWORLD_SEARCH_URL, params)
    if transport_error or response is None or response.status_code != 200:
        return []

    response_data = data.get("response", {}) if isinstance(data, dict) else {}
    if str(response_data.get("status") or "").strip().upper() != "OK":
        return []

    result = response_data.get("result", {})
    items = result.get("items", []) if isinstance(result, dict) else []
    if not isinstance(items, list):
        return []

    candidates: List[AddressParcelCandidate] = []
    seen_pnus = set()
    for item in items:
        candidate = _candidate_from_item(item)
        if candidate is None or candidate.candidate_pnu in seen_pnus:
            continue
        seen_pnus.add(candidate.candidate_pnu)
        candidates.append(candidate)
    return candidates
