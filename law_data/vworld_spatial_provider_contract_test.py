from __future__ import annotations

from unittest.mock import Mock, patch

import requests

from law_data.vworld_spatial_provider import query_spatial_dataset


DATASET = "LT_C_UQ129"


def _response(status_code: int, payload=None, json_error: Exception | None = None):
    response = Mock()
    response.status_code = status_code
    if json_error is not None:
        response.json.side_effect = json_error
    else:
        response.json.return_value = payload
    return response


def _query():
    return query_spatial_dataset(
        dataset=DATASET,
        api_key="TEST_KEY",
        x=127.0,
        y=37.0,
    )


def main() -> None:
    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        side_effect=requests.RequestException("offline"),
    ):
        result = _query()
        assert result["classification"] == "TRANSPORT_ERROR"
        assert result["http_status"] is None
        assert result["features"] == []

    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        return_value=_response(200, json_error=ValueError("bad json")),
    ):
        result = _query()
        assert result["classification"] == "JSON_PARSE_ERROR"
        assert result["http_status"] == 200
        assert result["features"] == []

    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        return_value=_response(
            503,
            {"response": {"status": "ERROR", "error": {"text": "down"}}},
        ),
    ):
        result = _query()
        assert result["classification"] == "HTTP_ERROR"
        assert result["http_status"] == 503
        assert result["error"] == {"text": "down"}

    feature = {
        "id": "LT_C_UQ129.1",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[127.0, 37.0], [127.1, 37.0], [127.1, 37.1], [127.0, 37.0]]],
        },
        "properties": {"uname": "test"},
    }
    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        return_value=_response(
            200,
            {"response": {"status": "OK", "result": {"featureCollection": {"features": [feature]}}}},
        ),
    ):
        result = _query()
        assert result["classification"] == "QUERY_SUCCESS"
        assert result["feature_count"] == 1
        assert result["features"] == [feature]

    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        return_value=_response(200, {"response": {"status": "NOT_FOUND"}}),
    ):
        result = _query()
        assert result["classification"] == "QUERY_EMPTY"
        assert result["feature_count"] == 0

    with patch(
        "law_data.vworld_spatial_provider.requests.get",
        return_value=_response(200, {"response": {"status": "ERROR"}}),
    ):
        result = _query()
        assert result["classification"] == "QUERY_FAILED"

    result_request = result["request"]
    assert result_request == {
        "dataset": DATASET,
        "x": 127.0,
        "y": 37.0,
        "crs": "EPSG:4326",
    }

    print("VWORLD_SPATIAL_PROVIDER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
