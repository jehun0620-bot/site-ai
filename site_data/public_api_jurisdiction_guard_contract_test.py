from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

import api_app
from site_data.address_parcel_identity_resolver import AddressParcelIdentityResolution
from site_data.selected_parcel_candidate_verifier import SelectedParcelCandidateVerification

BUSAN_PNU = "2635010500105240002"
BUSAN_ADDRESS = "부산광역시 해운대구 우동 524-2"
EXPECTED_ERROR = {
    "schema_version": "SITE_API_ERROR_V1",
    "code": "LEGAL_JURISDICTION_UNSUPPORTED",
    "category": "ANALYSIS",
    "message": "현재 이 지역의 법규 분석을 지원하지 않습니다. 해당 관할의 조례 검증이 필요합니다.",
    "retryable": False,
}


def assert_unsupported(response) -> None:
    assert response.status_code == 422, response.text
    assert response.json() == {"detail": EXPECTED_ERROR}, response.text


def main() -> None:
    client = TestClient(api_app.app)

    # Direct parcel API: reject before BuildingHUB/network access.
    with patch("site_data.site_analysis_orchestrator.fetch_building_items") as fetch:
        response = client.post("/v1/site-analysis", json={
            "sigungu_cd": "26350", "bjdong_cd": "10500",
            "plat_gb_cd": "0", "bun": "0524", "ji": "0002",
        })
        assert_unsupported(response)
        fetch.assert_not_called()

    # Address API: keep the real orchestrator, mock only verified identity.
    verified_address = AddressParcelIdentityResolution(
        status="VERIFIED", resolution="ADDRESS_PARCEL_IDENTITY_VERIFIED",
        address=BUSAN_ADDRESS, pnu=BUSAN_PNU,
        sigungu_cd="26350", bjdong_cd="10500", plat_gb_cd="0",
        bun="0524", ji="0002",
        x=0.0, y=0.0, crs="EPSG:4326",
    )
    with (
        patch(
            "site_data.site_analysis_orchestrator.resolve_address_parcel_identity",
            return_value=verified_address,
        ) as resolver,
        patch("site_data.site_analysis_orchestrator.fetch_building_items") as fetch,
    ):
        response = client.post("/v1/site-analysis/address", json={"address": BUSAN_ADDRESS})
        assert_unsupported(response)
        resolver.assert_called_once()
        fetch.assert_not_called()

    # Selected candidate API: mock successful same-PNU verification only.
    # Synthetic (0,0) coordinates are test doubles, not real Busan geometry.
    selected = SelectedParcelCandidateVerification(
        status="VERIFIED", resolution="SELECTED_PARCEL_CANDIDATE_VERIFIED",
        pnu=BUSAN_PNU, sigungu_cd="26350", bjdong_cd="10500",
        plat_gb_cd="0", bun="0524", ji="0002",
        x=0.0, y=0.0, crs="EPSG:4326",
    )
    with (
        patch(
            "site_data.site_analysis_orchestrator.verify_selected_parcel_candidate",
            return_value=selected,
        ) as verifier,
        patch("site_data.site_analysis_orchestrator.fetch_building_items") as fetch,
    ):
        response = client.post("/v1/site-analysis/selected-candidate", json={
            "candidate_pnu": BUSAN_PNU, "x": 0.0, "y": 0.0,
        })
        assert_unsupported(response)
        verifier.assert_called_once()
        fetch.assert_not_called()

    print("PUBLIC_API_JURISDICTION_GUARD_CONTRACT_PASS")


if __name__ == "__main__":
    main()
