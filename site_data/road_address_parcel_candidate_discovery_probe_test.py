from __future__ import annotations

"""Live probe for road-address parcel-candidate discovery.

This probe does not change or relax the VERIFIED parcel boundary. It only
observes whether the current VWorld-backed discovery provider can resolve a
road-address query into parcel candidates. A successful candidate still needs
the existing selected-candidate same-PNU polygon verification before analysis.
"""

from site_data.address_parcel_candidate_search import search_address_parcel_candidates


ROAD_ADDRESS_QUERY = "서울특별시 강남구 개포로109길 21"
EXPECTED_PNU = "1168010300100120000"


def main() -> None:
    candidates = search_address_parcel_candidates(ROAD_ADDRESS_QUERY)

    print("=" * 60)
    print("ROAD ADDRESS PARCEL CANDIDATE DISCOVERY PROBE")
    print("=" * 60)
    print(f"query: {ROAD_ADDRESS_QUERY}")
    print(f"candidate_count: {len(candidates)}")

    for index, candidate in enumerate(candidates, start=1):
        print("-" * 60)
        print(f"candidate[{index}].pnu: {candidate.candidate_pnu}")
        print(f"candidate[{index}].parcel_address: {candidate.parcel_address}")
        print(f"candidate[{index}].road_address: {candidate.road_address}")
        print(f"candidate[{index}].building_name: {candidate.building_name}")
        print(
            f"candidate[{index}].reference_geometry: "
            f"{candidate.reference_geometry.get('type') if isinstance(candidate.reference_geometry, dict) else None}"
        )

    matching = [candidate for candidate in candidates if candidate.candidate_pnu == EXPECTED_PNU]
    print("-" * 60)
    print(f"expected_pnu: {EXPECTED_PNU}")
    print(f"expected_pnu_found: {bool(matching)}")

    if matching:
        candidate = matching[0]
        print(f"matched_parcel_address: {candidate.parcel_address}")
        print(f"matched_road_address: {candidate.road_address}")
        print(
            "matched_reference_geometry: "
            f"{candidate.reference_geometry.get('type') if isinstance(candidate.reference_geometry, dict) else None}"
        )

    print("-" * 60)
    print(
        "PROBE_RESULT: "
        + ("ROAD_ADDRESS_DISCOVERY_OBSERVED" if matching else "ROAD_ADDRESS_DISCOVERY_NOT_OBSERVED")
    )


if __name__ == "__main__":
    main()
