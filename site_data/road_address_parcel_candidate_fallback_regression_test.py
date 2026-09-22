from __future__ import annotations

"""Live regression for production road-address candidate fallback."""

from site_data.address_parcel_candidate_search import search_address_parcel_candidates
from site_data.selected_parcel_candidate_verifier import verify_selected_parcel_candidate


ROAD_ADDRESS_QUERY = "서울특별시 강남구 개포로109길 21"
EXPECTED_PNU = "1168010300100120000"


def main() -> None:
    candidates = search_address_parcel_candidates(ROAD_ADDRESS_QUERY)
    matching = [candidate for candidate in candidates if candidate.candidate_pnu == EXPECTED_PNU]

    assert len(candidates) == 1, f"expected one PNU-deduplicated candidate, got {len(candidates)}"
    assert len(matching) == 1, f"expected PNU {EXPECTED_PNU} was not resolved"

    candidate = matching[0]
    assert isinstance(candidate.reference_geometry, dict)
    assert candidate.reference_geometry.get("type") in {"Polygon", "MultiPolygon"}

    verification = verify_selected_parcel_candidate(
        candidate.candidate_pnu,
        candidate.x,
        candidate.y,
    )
    assert verification.verified
    assert verification.pnu == EXPECTED_PNU
    assert isinstance(verification.geometry, dict)
    assert verification.geometry.get("type") in {"Polygon", "MultiPolygon"}

    print("=" * 60)
    print("ROAD ADDRESS PARCEL CANDIDATE FALLBACK REGRESSION")
    print("=" * 60)
    print(f"query: {ROAD_ADDRESS_QUERY}")
    print(f"candidate_count: {len(candidates)}")
    print(f"candidate_pnu: {candidate.candidate_pnu}")
    print(f"parcel_address: {candidate.parcel_address}")
    print(f"road_address: {candidate.road_address}")
    print(f"building_name: {candidate.building_name}")
    print(f"reference_geometry: {candidate.reference_geometry.get('type')}")
    print(f"verification_status: {verification.status}")
    print(f"verification_resolution: {verification.resolution}")
    print(f"verified_pnu: {verification.pnu}")
    print(f"verified_geometry: {verification.geometry.get('type')}")
    print("ROAD_ADDRESS_PARCEL_CANDIDATE_FALLBACK_REGRESSION_PASS")


if __name__ == "__main__":
    main()
