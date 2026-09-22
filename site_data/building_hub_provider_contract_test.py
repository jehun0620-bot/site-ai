# -*- coding: utf-8 -*-
"""Contract tests for the Building HUB provider boundary."""
from unittest.mock import Mock, patch

import requests

from site_data.building_hub_provider import BuildingAPIError, fetch_building_items


def main():
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "response": {
            "header": {"resultCode": "00", "resultMsg": "NORMAL SERVICE"},
            "body": {
                "items": {"item": {"mgmBldrgstPk": "TEST"}},
                "totalCount": "1",
            },
        }
    }

    with patch("site_data.building_hub_provider.requests.get", return_value=response) as request:
        result = fetch_building_items(
            sigungu_cd="11680",
            bjdong_cd="10300",
            plat_gb_cd="0",
            bun="0012",
            ji="0000",
            service_key="TEST_KEY",
        )
    assert len(result["items"]) == 1
    assert result["total_count"] == 1
    assert result["result_code"] == "00"
    request.assert_called_once()

    def call_provider():
        return fetch_building_items(
            sigungu_cd="11680",
            bjdong_cd="10300",
            plat_gb_cd="0",
            bun="0012",
            ji="0000",
            service_key="TEST_KEY",
        )

    with patch(
        "site_data.building_hub_provider.requests.get",
        side_effect=requests.Timeout("timeout"),
    ):
        try:
            call_provider()
        except BuildingAPIError as exc:
            assert exc.retryable is True
        else:
            raise AssertionError("transport timeout was admitted")

    for status_code, expected_retryable in ((503, True), (429, True), (404, False)):
        response.status_code = status_code
        with patch("site_data.building_hub_provider.requests.get", return_value=response):
            try:
                call_provider()
            except BuildingAPIError as exc:
                assert exc.retryable is expected_retryable
            else:
                raise AssertionError(f"HTTP {status_code} was admitted")
    response.status_code = 200

    response.json.side_effect = ValueError("bad json")
    with patch("site_data.building_hub_provider.requests.get", return_value=response):
        try:
            call_provider()
        except BuildingAPIError as exc:
            assert exc.retryable is False
        else:
            raise AssertionError("invalid JSON was admitted")
    response.json.side_effect = None

    response.json.return_value["response"]["header"]["resultCode"] = "99"
    with patch("site_data.building_hub_provider.requests.get", return_value=response):
        try:
            call_provider()
        except BuildingAPIError as exc:
            assert exc.retryable is False
        else:
            raise AssertionError("provider application error was admitted")
    response.json.return_value["response"]["header"]["resultCode"] = "00"

    try:
        fetch_building_items(
            sigungu_cd="11680",
            bjdong_cd="10300",
            plat_gb_cd="0",
            bun="0012",
            ji="0000",
            service_key="",
        )
    except BuildingAPIError as exc:
        assert exc.retryable is False
    else:
        raise AssertionError("missing API key was admitted")

    response.json.return_value["response"]["body"]["totalCount"] = "invalid"
    with patch("site_data.building_hub_provider.requests.get", return_value=response):
        try:
            fetch_building_items(
                sigungu_cd="11680",
                bjdong_cd="10300",
                plat_gb_cd="0",
                bun="0012",
                ji="0000",
                service_key="TEST_KEY",
            )
        except BuildingAPIError:
            pass
        else:
            raise AssertionError("invalid totalCount was admitted")

    print("BUILDING_HUB_PROVIDER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
