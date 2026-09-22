from __future__ import annotations

"""Live observation probe for VWorld road-address search parameter modes.

This file does not change production search behavior. It calls the same VWorld
search endpoint through the existing request_json transport and prints only
non-secret request mode/result facts needed to determine whether a road-address
discovery path exists.

No result from this probe is VERIFIED parcel truth. Any future discovery path
must still pass the existing selected-candidate same-PNU polygon verification.
"""

from typing import Any, Dict

from law_data.parcel_geometry_provider import load_vworld_key, request_json
from site_data.address_parcel_candidate_search import VWORLD_SEARCH_URL


ROAD_ADDRESS_QUERY = "서울특별시 강남구 개포로109길 21"
CATEGORIES = ("parcel", "road")


def _params(api_key: str, category: str) -> Dict[str, Any]:
    return {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": ROAD_ADDRESS_QUERY,
        "type": "address",
        "category": category,
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }


def _print_item(index: int, item: Dict[str, Any]) -> None:
    address = item.get("address", {})
    point = item.get("point", {})
    if not isinstance(address, dict):
        address = {}
    if not isinstance(point, dict):
        point = {}

    print(f"item[{index}].id: {str(item.get('id') or '').strip()}")
    print(f"item[{index}].parcel: {str(address.get('parcel') or '').strip()}")
    print(f"item[{index}].road: {str(address.get('road') or '').strip()}")
    print(f"item[{index}].building_name: {str(address.get('bldnm') or '').strip()}")
    print(f"item[{index}].x: {point.get('x')}")
    print(f"item[{index}].y: {point.get('y')}")


def main() -> None:
    api_key = str(load_vworld_key() or "").strip()
    if not api_key:
        raise RuntimeError("VWorld API key is not configured.")

    print("=" * 60)
    print("VWORLD ROAD ADDRESS SEARCH MODE PROBE")
    print("=" * 60)
    print(f"query: {ROAD_ADDRESS_QUERY}")

    for category in CATEGORIES:
        response, data, transport_error = request_json(
            VWORLD_SEARCH_URL,
            _params(api_key, category),
        )

        print("-" * 60)
        print(f"category: {category}")
        print(f"http_status: {getattr(response, 'status_code', None)}")
        print(f"transport_error: {bool(transport_error)}")

        response_data = data.get("response", {}) if isinstance(data, dict) else {}
        if not isinstance(response_data, dict):
            response_data = {}
        print(f"provider_status: {str(response_data.get('status') or '').strip()}")

        error = response_data.get("error")
        if isinstance(error, dict):
            print(f"provider_error_code: {str(error.get('code') or '').strip()}")
            print(f"provider_error_text: {str(error.get('text') or '').strip()}")

        result = response_data.get("result", {})
        items = result.get("items", []) if isinstance(result, dict) else []
        if not isinstance(items, list):
            items = []

        print(f"item_count: {len(items)}")
        for index, item in enumerate(items, start=1):
            if isinstance(item, dict):
                _print_item(index, item)

    print("-" * 60)
    print("PROBE_COMPLETE")


if __name__ == "__main__":
    main()
