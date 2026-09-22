from __future__ import annotations

from unittest.mock import patch

from site_data.address_parcel_candidate_search import (
    AddressParcelCandidateSearchProviderError,
    _normalize_search_query,
    search_address_parcel_candidates,
)


class _Response:
    def __init__(self, status_code=200):
        self.status_code = status_code


def _ok(items):
    return _Response(), {"response": {"status": "OK", "result": {"items": items}}}, None


def _not_found():
    return _Response(), {"response": {"status": "NOT_FOUND"}}, None


def _http_error(status_code):
    return _Response(status_code), {"response": {"status": "ERROR"}}, None


def _provider_error(status="ERROR"):
    return _Response(), {"response": {"status": status}}, None


def _item(pnu, parcel, *, road="", building="", x="127.075", y="37.494"):
    return {
        "id": pnu,
        "address": {"parcel": parcel, "road": road, "bldnm": building},
        "point": {"x": x, "y": y},
    }


def main() -> None:
    assert _normalize_search_query(" 서울특별시  강남구 개포동 12번지 ") == "서울특별시 강남구 개포동 12"
    assert _normalize_search_query("서울특별시 동작구 동작동 산 29-3") == "서울특별시 동작구 동작동 산 29-3"

    parcel_items = [
        _item(
            "1168010300100120000",
            "서울특별시 강남구 개포동 12",
            road="개포로109길 21",
            building="대청아파트302동",
            x="127.07539280356858",
            y="37.494197498186885",
        ),
        _item("1168010300100120001", "서울특별시 강남구 개포동 12-1"),
        _item("1168010300100120010", "서울특별시 강남구 개포동 12-10"),
        {"id": "bad-pnu", "address": {"parcel": "무효"}, "point": {"x": "1", "y": "2"}},
        {"id": "1168010300100120000", "address": {"parcel": "중복"}, "point": {"x": "1", "y": "2"}},
        {"id": "1168010300100990000", "address": {"parcel": "좌표없음"}, "point": {}},
    ]

    with patch("site_data.address_parcel_candidate_search.request_json", return_value=_ok(parcel_items)) as request:
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
        assert request.call_count == 1
        params = request.call_args.args[1]
        assert params["query"] == "서울특별시 강남구 개포동 12"
        assert params["category"] == "parcel"
        assert params["key"] == "test-key"

    road_items = [
        _item(
            "1168010300100120000",
            "개포동 12",
            road="서울특별시 강남구 개포로109길 21 (개포동,대청아파트301동)",
            building="대청아파트301동",
            x="127.07634613396932",
            y="37.495383237713945",
        ),
        _item(
            "1168010300100120000",
            "개포동 12",
            road="서울특별시 강남구 개포로109길 21 (개포동,대청아파트302동)",
            building="대청아파트302동",
            x="127.07709615813468",
            y="37.495607572541424",
        ),
    ]

    with patch(
        "site_data.address_parcel_candidate_search.request_json",
        side_effect=[_not_found(), _ok(road_items)],
    ) as request:
        candidates = search_address_parcel_candidates(
            "서울특별시 강남구 개포로109길 21",
            api_key="test-key",
        )
        assert len(candidates) == 1
        assert candidates[0].candidate_pnu == "1168010300100120000"
        assert candidates[0].parcel_address == "개포동 12"
        assert candidates[0].building_name == "대청아파트301동"
        assert request.call_count == 2
        assert request.call_args_list[0].args[1]["category"] == "parcel"
        assert request.call_args_list[1].args[1]["category"] == "road"

    with patch(
        "site_data.address_parcel_candidate_search.request_json",
        return_value=(None, {}, "network"),
    ) as request:
        try:
            search_address_parcel_candidates("개포동 12", api_key="test-key")
        except AddressParcelCandidateSearchProviderError as exc:
            assert exc.retryable is True
        else:
            raise AssertionError("transport failure must not be returned as an empty candidate result")
        assert request.call_count == 1

    for status_code, expected_retryable in ((503, True), (429, True), (404, False)):
        with patch(
            "site_data.address_parcel_candidate_search.request_json",
            return_value=_http_error(status_code),
        ):
            try:
                search_address_parcel_candidates("개포동 12", api_key="test-key")
            except AddressParcelCandidateSearchProviderError as exc:
                assert exc.retryable is expected_retryable
            else:
                raise AssertionError(f"HTTP {status_code} failure was admitted")

    with patch(
        "site_data.address_parcel_candidate_search.request_json",
        return_value=_provider_error(),
    ):
        try:
            search_address_parcel_candidates("개포동 12", api_key="test-key")
        except AddressParcelCandidateSearchProviderError as exc:
            assert exc.retryable is False
        else:
            raise AssertionError("provider status failure was admitted")

    with patch(
        "site_data.address_parcel_candidate_search.request_json",
        side_effect=[_not_found(), (None, {}, "network")],
    ) as request:
        try:
            search_address_parcel_candidates("개포로109길 21", api_key="test-key")
        except AddressParcelCandidateSearchProviderError as exc:
            assert exc.retryable is True
        else:
            raise AssertionError("road fallback transport failure must not be returned as an empty candidate result")
        assert request.call_count == 2

    with patch("site_data.address_parcel_candidate_search.load_vworld_key", return_value=""):
        assert search_address_parcel_candidates("개포동 12") == []

    with patch("site_data.address_parcel_candidate_search.request_json") as request:
        assert search_address_parcel_candidates("   ", api_key="test-key") == []
        request.assert_not_called()

    print("ADDRESS_PARCEL_CANDIDATE_SEARCH_CONTRACT_PASS")


if __name__ == "__main__":
    main()
