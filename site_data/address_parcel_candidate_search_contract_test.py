from __future__ import annotations

from unittest.mock import patch

from site_data.address_parcel_candidate_search import (
    _normalize_search_query,
    search_address_parcel_candidates,
)


class _Response:
    status_code = 200


def _ok(items):
    return _Response(), {"response": {"status": "OK", "result": {"items": items}}}, None


def main() -> None:
    assert _normalize_search_query(" 서울특별시  강남구 개포동 12번지 ") == "서울특별시 강남구 개포동 12"
    assert _normalize_search_query("서울특별시 동작구 동작동 산 29-3") == "서울특별시 동작구 동작동 산 29-3"

    items = [
        {
            "id": "1168010300100120000",
            "address": {"parcel": "서울특별시 강남구 개포동 12", "road": "개포로109길 21", "bldnm": "대청아파트302동"},
            "point": {"x": "127.07539280356858", "y": "37.494197498186885"},
        },
        {
            "id": "1168010300100120001",
            "address": {"parcel": "서울특별시 강남구 개포동 12-1"},
            "point": {"x": "127.075", "y": "37.494"},
        },
        {
            "id": "1168010300100120010",
            "address": {"parcel": "서울특별시 강남구 개포동 12-10"},
            "point": {"x": "127.076", "y": "37.495"},
        },
        {"id": "bad-pnu", "address": {"parcel": "무효"}, "point": {"x": "1", "y": "2"}},
        {"id": "1168010300100120000", "address": {"parcel": "중복"}, "point": {"x": "1", "y": "2"}},
        {"id": "1168010300100990000", "address": {"parcel": "좌표없음"}, "point": {}},
    ]

    with patch("site_data.address_parcel_candidate_search.request_json", return_value=_ok(items)) as request:
        candidates = search_address_parcel_candidates("서울특별시 강남구 개포동 12번지", api_key="test-key")
        assert [candidate.candidate_pnu for candidate in candidates] == [
            "1168010300100120000",
            "1168010300100120001",
            "1168010300100120010",
        ]
        assert candidates[0].parcel_address == "서울특별시 강남구 개포동 12"
        assert candidates[0].road_address == "개포로109길 21"
        assert candidates[0].building_name == "대청아파트302동"
        assert candidates[0].crs == "EPSG:4326"
        assert candidates[0].to_dict()["candidate_pnu"] == "1168010300100120000"
        params = request.call_args.args[1]
        assert params["query"] == "서울특별시 강남구 개포동 12"
        assert params["category"] == "parcel"
        assert params["key"] == "test-key"

    with patch("site_data.address_parcel_candidate_search.request_json", return_value=(None, {}, "network")):
        assert search_address_parcel_candidates("개포동 12", api_key="test-key") == []

    with patch("site_data.address_parcel_candidate_search.load_vworld_key", return_value=""):
        assert search_address_parcel_candidates("개포동 12") == []

    with patch("site_data.address_parcel_candidate_search.request_json") as request:
        assert search_address_parcel_candidates("   ", api_key="test-key") == []
        request.assert_not_called()

    print("ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS")


if __name__ == "__main__":
    main()
