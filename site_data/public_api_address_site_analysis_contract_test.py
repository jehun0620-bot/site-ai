# -*- coding: utf-8 -*-
"""Contract test for the public address-based SITE analysis HTTP boundary."""
from __future__ import annotations
from unittest.mock import patch
from fastapi.testclient import TestClient
import api_app


def main() -> None:
    client = TestClient(api_app.app)
    expected = {
        "site": {
            "site_id": "11680-10300-0012-0000",
            "pnu": "1168010300100120000",
            "identity_status": "COMPLETE",
        },
        "service": {"building_count": 34},
    }

    with patch("api_app.analyze_site_by_address", return_value=expected) as analyze:
        response = client.post(
            "/v1/site-analysis/address",
            json={
                "address": "서울특별시 강남구 개포동 12번지",
                "project_profile": {"use": "residential"},
                "procedure_profile": {"stage": "review"},
                "include_debug": True,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == expected
        analyze.assert_called_once_with(
            address="서울특별시 강남구 개포동 12번지",
            project_profile={"use": "residential"},
            procedure_profile={"stage": "review"},
            include_debug=True,
        )

    with patch("api_app.analyze_site_by_address", side_effect=api_app.SiteBuildError("주소에서 검증된 필지를 확정할 수 없습니다")):
        response = client.post(
            "/v1/site-analysis/address",
            json={"address": "검증되지 않은 주소"},
        )
        assert response.status_code == 404, response.text
        assert "검증된 필지" in response.json()["detail"]

    with patch("api_app.analyze_site_by_address") as analyze:
        response = client.post("/v1/site-analysis/address", json={"address": ""})
        assert response.status_code == 422, response.text
        analyze.assert_not_called()

    with patch("api_app.analyze_site_by_address", return_value=expected) as address_analyze, patch("api_app.analyze_site_by_parcel", return_value=expected) as parcel_analyze:
        response = client.post(
            "/v1/site-analysis",
            json={
                "sigungu_cd": "11680",
                "bjdong_cd": "10300",
                "plat_gb_cd": "0",
                "bun": "0012",
                "ji": "0000",
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == expected
        parcel_analyze.assert_called_once()
        address_analyze.assert_not_called()

    print("PUBLIC_API_ADDRESS_SITE_ANALYSIS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
