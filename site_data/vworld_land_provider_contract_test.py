# -*- coding: utf-8 -*-
"""Contract test for VWorld land-characteristics provider semantics."""
from unittest.mock import Mock, patch
import requests

from site_data import vworld_api


def _response(status_code=200, data=None, json_error=None):
    response = Mock()
    response.status_code = status_code
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = data
    return response


def main():
    with patch.object(vworld_api, "VWORLD_API_KEY", None):
        try:
            vworld_api.get_land_characteristics("1168010300100120000", "2026")
        except vworld_api.VWorldLandProviderError as exc:
            assert exc.retryable is False
        else:
            raise AssertionError("missing key must be a non-retryable provider failure")

    with patch.object(vworld_api, "VWORLD_API_KEY", "test-key"), patch.object(
        vworld_api.requests, "get", side_effect=requests.Timeout("timeout")
    ):
        try:
            vworld_api.get_land_characteristics("1168010300100120000", "2026")
        except vworld_api.VWorldLandProviderError as exc:
            assert exc.retryable is True
        else:
            raise AssertionError("transport failure must be retryable")

    for status_code, expected_retryable in ((408, True), (429, True), (503, True), (404, False)):
        with patch.object(vworld_api, "VWORLD_API_KEY", "test-key"), patch.object(
            vworld_api.requests, "get", return_value=_response(status_code=status_code)
        ):
            try:
                vworld_api.get_land_characteristics("1168010300100120000", "2026")
            except vworld_api.VWorldLandProviderError as exc:
                assert exc.retryable is expected_retryable
            else:
                raise AssertionError(f"HTTP {status_code} failure was admitted")

    malformed_cases = (
        _response(data=None, json_error=ValueError("bad json")),
        _response(data={"unexpected": {}}),
        _response(data={"landCharacteristicss": {"field": {}}}),
    )
    for response in malformed_cases:
        with patch.object(vworld_api, "VWORLD_API_KEY", "test-key"), patch.object(
            vworld_api.requests, "get", return_value=response
        ):
            try:
                vworld_api.get_land_characteristics("1168010300100120000", "2026")
            except vworld_api.VWorldLandProviderError as exc:
                assert exc.retryable is False
            else:
                raise AssertionError("malformed provider response was admitted")

    with patch.object(vworld_api, "get_land_characteristics", side_effect=[[], [], []]) as lookup:
        try:
            vworld_api.get_latest_land_characteristics(
                "1168010300100120000", start_year=2026, lookback_years=3
            )
        except vworld_api.VWorldLandNoDataError:
            pass
        else:
            raise AssertionError("successful no-data year window must have distinct no-data semantics")
        assert lookup.call_count == 3

    with patch.object(
        vworld_api, "get_land_characteristics", side_effect=[[], [{"pnu": "1168010300100120000"}]]
    ) as lookup:
        year, records = vworld_api.get_latest_land_characteristics(
            "1168010300100120000", start_year=2026, lookback_years=3
        )
        assert year == "2025"
        assert len(records) == 1
        assert lookup.call_count == 2

    print("VWORLD_LAND_PROVIDER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
