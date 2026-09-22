from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

import api_app
from site_data.address_parcel_candidate_search import AddressParcelCandidateSearchProviderError
from site_data.selected_parcel_candidate_verifier import SelectedParcelCandidateVerification


EXPECTED_KEYS = {
    "schema_version",
    "code",
    "category",
    "message",
    "retryable",
}


def assert_product_error(response, status_code: int, code: str, category: str) -> None:
    assert response.status_code == status_code, response.text
    detail = response.json()["detail"]
    assert set(detail) == EXPECTED_KEYS, detail
    assert detail["schema_version"] == "SITE_API_ERROR_V1"
    assert detail["code"] == code
    assert detail["category"] == category
    assert isinstance(detail["message"], str) and detail["message"]
    assert detail["retryable"] is False


def main() -> None:
    client = TestClient(api_app.app)
    payload = {
        "candidate_pnu": "1168010300100120002",
        "x": 127.0,
        "y": 37.0,
    }

    with patch.object(
        api_app,
        "analyze_site_by_selected_candidate",
        side_effect=api_app.BuildingAPIError("provider transport detail"),
    ):
        response = client.post("/v1/site-analysis/selected-candidate", json=payload)
        assert_product_error(response, 502, "BUILDING_PROVIDER_FAILED", "PROVIDER")
        assert "provider transport detail" not in response.text

    with patch.object(
        api_app,
        "analyze_site_by_selected_candidate",
        side_effect=api_app.SiteBuildError("internal parcel build detail"),
    ):
        response = client.post("/v1/site-analysis/selected-candidate", json=payload)
        assert_product_error(response, 404, "PARCEL_BUILD_FAILED", "PARCEL")
        assert "internal parcel build detail" not in response.text

    with patch.object(
        api_app,
        "analyze_site_by_selected_candidate",
        side_effect=api_app.SiteAnalysisError("internal analysis detail"),
    ):
        response = client.post("/v1/site-analysis/selected-candidate", json=payload)
        assert_product_error(response, 500, "SITE_ANALYSIS_FAILED", "ANALYSIS")
        assert "internal analysis detail" not in response.text

    with patch.object(
        api_app,
        "analyze_site_by_selected_candidate",
        side_effect=RuntimeError("unexpected internal detail"),
    ):
        response = client.post("/v1/site-analysis/selected-candidate", json=payload)
        assert_product_error(response, 500, "UNEXPECTED_ERROR", "INTERNAL")
        assert "unexpected internal detail" not in response.text

    with patch.object(
        api_app,
        "analyze_site_by_address",
        side_effect=RuntimeError("unexpected internal detail"),
    ):
        response = client.post(
            "/v1/site-analysis/address",
            json={"address": "서울특별시 강남구 개포동 12번지"},
        )
        assert_product_error(response, 500, "UNEXPECTED_ERROR", "INTERNAL")
        assert "unexpected internal detail" not in response.text

    rejected = SelectedParcelCandidateVerification(
        status="REJECTED",
        resolution="SELECTED_PNU_POLYGON_MISMATCH",
        pnu="1168010300100120002",
        x=127.0,
        y=37.0,
        crs="EPSG:4326",
    )
    with patch.object(api_app, "verify_selected_parcel_candidate", return_value=rejected):
        response = client.post("/v1/parcel-candidates/confirm", json=payload)
        assert_product_error(response, 404, "PARCEL_VERIFICATION_FAILED", "PARCEL")

    missing_geometry = SelectedParcelCandidateVerification(
        status="VERIFIED",
        resolution="SELECTED_PARCEL_CANDIDATE_VERIFIED",
        pnu="1168010300100120002",
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0002",
        x=127.0,
        y=37.0,
        crs="EPSG:4326",
        geometry=None,
    )
    with patch.object(api_app, "verify_selected_parcel_candidate", return_value=missing_geometry):
        response = client.post("/v1/parcel-candidates/confirm", json=payload)
        assert_product_error(response, 404, "PARCEL_GEOMETRY_UNRESOLVED", "PARCEL")

    with patch.object(
        api_app,
        "search_address_parcel_candidates",
        side_effect=AddressParcelCandidateSearchProviderError("candidate provider detail"),
    ):
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "서울특별시 강남구 개포동 12"},
        )
        assert_product_error(response, 500, "CANDIDATE_SEARCH_FAILED", "PROVIDER")
        assert "candidate provider detail" not in response.text

    print("PUBLIC_API_PRODUCT_ERROR_CONTRACT_PASS")


if __name__ == "__main__":
    main()
