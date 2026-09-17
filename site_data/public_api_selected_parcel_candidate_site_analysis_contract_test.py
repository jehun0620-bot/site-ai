from __future__ import annotations

from unittest.mock import patch

from fastapi.testclient import TestClient

import api_app


def main() -> None:
    client = TestClient(api_app.app)
    expected = {
        "schema_version": "SITE_ANALYSIS_API_V1",
        "status": "READY",
        "site": {"site_id": "11680-10300-0012-0002", "pnu": "1168010300100120002"},
    }

    with patch.object(api_app, "analyze_site_by_selected_candidate", return_value=expected) as analyze:
        response = client.post(
            "/v1/site-analysis/selected-candidate",
            json={
                "candidate_pnu": "1168010300100120002",
                "x": 127.07662495509604,
                "y": 37.49629354642009,
                "project_profile": {"use": "residential"},
                "procedure_profile": {"stage": "review"},
                "include_debug": True,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json() == expected
        analyze.assert_called_once_with(
            candidate_pnu="1168010300100120002",
            x=127.07662495509604,
            y=37.49629354642009,
            project_profile={"use": "residential"},
            procedure_profile={"stage": "review"},
            include_debug=True,
        )

    invalid_requests = [
        {"candidate_pnu": "116801030010012000", "x": 127.0, "y": 37.0},
        {"candidate_pnu": "116801030010012000X", "x": 127.0, "y": 37.0},
        {"candidate_pnu": "1168010300100120002", "x": 181.0, "y": 37.0},
        {"candidate_pnu": "1168010300100120002", "x": 127.0, "y": 91.0},
    ]
    for payload in invalid_requests:
        with patch.object(api_app, "analyze_site_by_selected_candidate") as analyze:
            response = client.post("/v1/site-analysis/selected-candidate", json=payload)
            assert response.status_code == 422, response.text
            analyze.assert_not_called()

    with patch.object(
        api_app,
        "analyze_site_by_selected_candidate",
        side_effect=api_app.SiteBuildError("선택한 필지를 검증할 수 없습니다: SELECTED_PNU_POLYGON_MISMATCH"),
    ):
        response = client.post(
            "/v1/site-analysis/selected-candidate",
            json={"candidate_pnu": "1168010300100120002", "x": 127.0, "y": 37.0},
        )
        assert response.status_code == 404, response.text
        assert "SELECTED_PNU_POLYGON_MISMATCH" in response.json()["detail"]

    with patch.object(api_app, "analyze_site_by_selected_candidate") as selected_analyze, patch.object(
        api_app, "search_address_parcel_candidates", return_value=[]
    ) as search:
        response = client.post(
            "/v1/parcel-candidates/address",
            json={"query": "서울특별시 강남구 개포동 12"},
        )
        assert response.status_code == 200, response.text
        search.assert_called_once()
        selected_analyze.assert_not_called()

    print("PUBLIC_API_SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_CONTRACT_PASS")


if __name__ == "__main__":
    main()
