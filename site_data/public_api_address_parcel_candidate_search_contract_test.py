from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

import api_app
from site_data.address_parcel_candidate_search import AddressParcelCandidate


def _candidate() -> AddressParcelCandidate:
    return AddressParcelCandidate(
        candidate_pnu="1168010300100120000",
        parcel_address="서울특별시 강남구 개포동 12",
        road_address="개포로109길 21",
        building_name="대청아파트302동",
        x=127.07539280356858,
        y=37.494197498186885,
    )


def main() -> None:
    client = TestClient(api_app.app)

    with patch.object(api_app, "search_address_parcel_candidates", return_value=[_candidate()]) as search:
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "서울특별시 강남구 개포동 12", "size": 10},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["schema_version"] == "PARCEL_CANDIDATE_SEARCH_V1"
        assert body["status"] == "READY"
        assert body["query"] == "서울특별시 강남구 개포동 12"
        assert body["count"] == 1
        assert body["candidates"][0]["candidate_pnu"] == "1168010300100120000"
        assert body["candidates"][0]["parcel_address"] == "서울특별시 강남구 개포동 12"
        assert "verified" not in body["candidates"][0]
        search.assert_called_once_with("서울특별시 강남구 개포동 12", size=10)

    with patch.object(api_app, "search_address_parcel_candidates") as search:
        response = client.post("/v1/parcel-candidates/address", json={"query": ""})
        assert response.status_code == 422
        search.assert_not_called()

    with patch.object(api_app, "search_address_parcel_candidates") as search:
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "서울특별시 강남구 개포동 12", "size": 101},
        )
        assert response.status_code == 422
        search.assert_not_called()

    with patch.object(api_app, "search_address_parcel_candidates", return_value=[]) as search:
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "없는 주소", "size": 5},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "READY"
        assert body["count"] == 0
        assert body["candidates"] == []
        search.assert_called_once_with("없는 주소", size=5)

    with patch.object(api_app, "analyze_site_by_address") as analyze_address, patch.object(
        api_app, "search_address_parcel_candidates", return_value=[_candidate()]
    ):
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "서울특별시 강남구 개포동 12"},
        )
        assert response.status_code == 200
        analyze_address.assert_not_called()

    print("PUBLIC_API_ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS")


if __name__ == "__main__":
    main()
