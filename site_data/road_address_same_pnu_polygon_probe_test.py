from __future__ import annotations

"""Live probe for road-search result coordinates against parcel PNU geometry.

This observes whether each VWorld category=road result coordinate can be
resolved to a parcel polygon carrying the same PNU returned by the road search.
It does not change production behavior and does not promote any discovery
result to VERIFIED state.
"""

from typing import Any, Dict, List

from law_data.parcel_geometry_provider import (
    PARCEL_DATASET,
    find_feature_pnu,
    is_polygon_geometry,
    load_vworld_key,
    query_dataset_by_point,
    request_json,
)
from site_data.address_parcel_candidate_search import VWORLD_SEARCH_URL


ROAD_ADDRESS_QUERY = "서울특별시 강남구 개포로109길 21"


def _road_items(api_key: str) -> List[Dict[str, Any]]:
    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": ROAD_ADDRESS_QUERY,
        "type": "address",
        "category": "road",
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }
    response, data, transport_error = request_json(VWORLD_SEARCH_URL, params)
    if transport_error or response is None or response.status_code != 200:
        return []
    response_data = data.get("response", {}) if isinstance(data, dict) else {}
    if not isinstance(response_data, dict) or str(response_data.get("status") or "").strip().upper() != "OK":
        return []
    result = response_data.get("result", {})
    items = result.get("items", []) if isinstance(result, dict) else []
    return [item for item in items if isinstance(item, dict)] if isinstance(items, list) else []


def _polygon_pnus(api_key: str, x: float, y: float) -> List[str]:
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


def main() -> None:
    api_key = str(load_vworld_key() or "").strip()
    if not api_key:
        raise RuntimeError("VWorld API key is not configured.")

    items = _road_items(api_key)
    print("=" * 60)
    print("ROAD SEARCH COORDINATE SAME-PNU POLYGON PROBE")
    print("=" * 60)
    print(f"query: {ROAD_ADDRESS_QUERY}")
    print(f"road_item_count: {len(items)}")

    checked = 0
    same_pnu_matches = 0

    for index, item in enumerate(items, start=1):
        expected_pnu = str(item.get("id") or "").strip()
        point = item.get("point", {})
        address = item.get("address", {})
        if not isinstance(point, dict):
            point = {}
        if not isinstance(address, dict):
            address = {}

        try:
            x = float(point.get("x"))
            y = float(point.get("y"))
        except (TypeError, ValueError):
            print("-" * 60)
            print(f"item[{index}].expected_pnu: {expected_pnu}")
            print(f"item[{index}].point_valid: False")
            continue

        polygon_pnus = _polygon_pnus(api_key, x, y)
        same_pnu = expected_pnu in polygon_pnus
        checked += 1
        if same_pnu:
            same_pnu_matches += 1

        print("-" * 60)
        print(f"item[{index}].expected_pnu: {expected_pnu}")
        print(f"item[{index}].road: {str(address.get('road') or '').strip()}")
        print(f"item[{index}].building_name: {str(address.get('bldnm') or '').strip()}")
        print(f"item[{index}].x: {x}")
        print(f"item[{index}].y: {y}")
        print(f"item[{index}].polygon_pnus: {polygon_pnus}")
        print(f"item[{index}].same_pnu_polygon_match: {same_pnu}")

    print("-" * 60)
    print(f"checked_coordinate_count: {checked}")
    print(f"same_pnu_match_count: {same_pnu_matches}")
    print(f"all_checked_coordinates_same_pnu: {checked > 0 and checked == same_pnu_matches}")
    print("PROBE_COMPLETE")


if __name__ == "__main__":
    main()
