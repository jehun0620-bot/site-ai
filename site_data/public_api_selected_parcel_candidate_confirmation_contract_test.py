from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

import api_app
from site_data.selected_parcel_candidate_verifier import SelectedParcelCandidateVerification


def main() -> None:
    client = TestClient(api_app.app)
    geometry = {
        "type": "Polygon",
        "coordinates": [
            [
                [127.0765, 37.4962],
                [127.0767, 37.4962],
                [127.0767, 37.4964],
                [127.0765, 37.4962],
            ]
        ],
    }
    verified = SelectedParcelCandidateVerification(
        status="VERIFIED",
        resolution="SELECTED_PARCEL_CANDIDATE_VERIFIED",
        pnu="1168010300100120002",
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0002",
        x=127.07662495509604,
        y=37.49629354642009,
        crs="EPSG:4326",
        geometry=geometry,
    )

    with patch.object(api_app, "verify_selected_parcel_candidate", return_value=verified) as verify, patch.object(
        api_app, "analyze_site_by_selected_candidate"
    ) as analyze:
        response = client.post(
            "/v1/parcel-candidates/confirm",
            json={
                "candidate_pnu": "1168010300100120002",
                "x": 127.07662495509604,
                "y": 37.49629354642009,
            },
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["schema_version"] == "PARCEL_CONFIRMATION_V1"
        assert body["status"] == "READY"
        assert body["parcel"] == {
            "pnu": "1168010300100120002",
            "sigungu_cd": "11680",
            "bjdong_cd": "10300",
            "plat_gb_cd": "0",
            "bun": "0012",
            "ji": "0002",
            "x": 127.07662495509604,
            "y": 37.49629354642009,
            "crs": "EPSG:4326",
        }
        assert body["verification"] == {
            "status": "VERIFIED",
            "resolution": "SELECTED_PARCEL_CANDIDATE_VERIFIED",
        }
        assert body["geometry"] == geometry
        verify.assert_called_once_with(
            candidate_pnu="1168010300100120002",
            x=127.07662495509604,
            y=37.49629354642009,
        )
        analyze.assert_not_called()

    invalid_requests = [
        {"candidate_pnu": "116801030010012000", "x": 127.0, "y": 37.0},
        {"candidate_pnu": "116801030010012000X", "x": 127.0, "y": 37.0},
        {"candidate_pnu": "1168010300100120002", "x": 181.0, "y": 37.0},
        {"candidate_pnu": "1168010300100120002", "x": 127.0, "y": 91.0},
    ]
    for payload in invalid_requests:
        with patch.object(api_app, "verify_selected_parcel_candidate") as verify:
            response = client.post("/v1/parcel-candidates/confirm", json=payload)
            assert response.status_code == 422, response.text
            verify.assert_not_called()

    rejected = SelectedParcelCandidateVerification(
        status="REJECTED",
        resolution="SELECTED_PNU_POLYGON_MISMATCH",
        pnu="1168010300100120002",
        x=127.0,
        y=37.0,
        crs="EPSG:4326",
    )
    with patch.object(api_app, "verify_selected_parcel_candidate", return_value=rejected), patch.object(
        api_app, "analyze_site_by_selected_candidate"
    ) as analyze:
        response = client.post(
            "/v1/parcel-candidates/confirm",
            json={"candidate_pnu": "1168010300100120002", "x": 127.0, "y": 37.0},
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == {
            "schema_version": "SITE_API_ERROR_V1",
            "code": "PARCEL_VERIFICATION_FAILED",
            "category": "PARCEL",
            "message": "선택한 필지를 검증할 수 없습니다.",
            "retryable": False,
        }
        analyze.assert_not_called()

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
    with patch.object(api_app, "verify_selected_parcel_candidate", return_value=missing_geometry), patch.object(
        api_app, "analyze_site_by_selected_candidate"
    ) as analyze:
        response = client.post(
            "/v1/parcel-candidates/confirm",
            json={"candidate_pnu": "1168010300100120002", "x": 127.0, "y": 37.0},
        )
        assert response.status_code == 404, response.text
        assert response.json()["detail"] == {
            "schema_version": "SITE_API_ERROR_V1",
            "code": "PARCEL_GEOMETRY_UNRESOLVED",
            "category": "PARCEL",
            "message": "선택한 필지의 검증된 경계를 확인할 수 없습니다.",
            "retryable": False,
        }
        analyze.assert_not_called()

    print("PUBLIC_API_SELECTED_PARCEL_CANDIDATE_CONFIRMATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
