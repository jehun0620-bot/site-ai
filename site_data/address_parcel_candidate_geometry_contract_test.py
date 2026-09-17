from __future__ import annotations

from unittest.mock import patch

from site_data.address_parcel_candidate_search import (
    AddressParcelCandidate,
    _reference_geometry_for_candidate,
)


PNU = "1168010300100120002"
OTHER_PNU = "1168010300100120003"
POLYGON = {
    "type": "Polygon",
    "coordinates": [[[127.07, 37.49], [127.08, 37.49], [127.08, 37.50], [127.07, 37.49]]],
}
MULTIPOLYGON = {
    "type": "MultiPolygon",
    "coordinates": [[[[127.07, 37.49], [127.08, 37.49], [127.08, 37.50], [127.07, 37.49]]]],
}


def _candidate() -> AddressParcelCandidate:
    return AddressParcelCandidate(
        candidate_pnu=PNU,
        parcel_address="서울특별시 강남구 개포동 12-2",
        road_address="개포로109길 69",
        building_name="개포자이",
        x=127.07662495509604,
        y=37.49629354642009,
    )


def _feature(pnu: str, geometry: dict) -> dict:
    return {"type": "Feature", "properties": {"pnu": pnu}, "geometry": geometry}


def main() -> None:
    candidate = _candidate()

    with patch(
        "site_data.address_parcel_candidate_search.query_dataset_by_point",
        return_value={"features": [_feature(PNU, POLYGON)]},
    ) as query:
        geometry = _reference_geometry_for_candidate(candidate, "test-key")
        assert geometry == POLYGON
        query.assert_called_once()

    with patch(
        "site_data.address_parcel_candidate_search.query_dataset_by_point",
        return_value={"features": [_feature(PNU, MULTIPOLYGON)]},
    ):
        geometry = _reference_geometry_for_candidate(candidate, "test-key")
        assert geometry == MULTIPOLYGON

    with patch(
        "site_data.address_parcel_candidate_search.query_dataset_by_point",
        return_value={"features": [_feature(OTHER_PNU, POLYGON)]},
    ):
        geometry = _reference_geometry_for_candidate(candidate, "test-key")
        assert geometry is None

    with patch(
        "site_data.address_parcel_candidate_search.query_dataset_by_point",
        return_value={"features": [{"type": "Feature", "properties": {"pnu": PNU}, "geometry": {"type": "Point", "coordinates": [127.07, 37.49]}}]},
    ):
        geometry = _reference_geometry_for_candidate(candidate, "test-key")
        assert geometry is None

    with patch(
        "site_data.address_parcel_candidate_search.query_dataset_by_point",
        return_value={"features": []},
    ):
        geometry = _reference_geometry_for_candidate(candidate, "test-key")
        assert geometry is None

    payload = AddressParcelCandidate(
        candidate_pnu=PNU,
        parcel_address=candidate.parcel_address,
        road_address=candidate.road_address,
        building_name=candidate.building_name,
        x=candidate.x,
        y=candidate.y,
        reference_geometry=POLYGON,
    ).to_dict()
    assert payload["reference_geometry"] == POLYGON
    assert "verified" not in payload
    assert "verification" not in payload

    print("ADDRESS_PARCEL_CANDIDATE_GEOMETRY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
