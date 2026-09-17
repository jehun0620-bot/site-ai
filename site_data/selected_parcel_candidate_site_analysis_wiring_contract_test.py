from __future__ import annotations

from unittest.mock import patch

from site_data.selected_parcel_candidate_verifier import SelectedParcelCandidateVerification
from site_data.site_analysis_orchestrator import SiteBuildError, analyze_site_by_selected_candidate


VERIFIED = SelectedParcelCandidateVerification(
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
)

REJECTED = SelectedParcelCandidateVerification(
    status="REJECTED",
    resolution="SELECTED_PNU_POLYGON_MISMATCH",
    pnu="1168010300100120002",
    x=127.07662495509604,
    y=37.49629354642009,
    crs="EPSG:4326",
)


def main() -> None:
    expected_response = {"schema_version": "SITE_ANALYSIS_API_V1", "status": "READY"}

    with patch("site_data.site_analysis_orchestrator.verify_selected_parcel_candidate", return_value=VERIFIED) as verify_mock, patch(
        "site_data.site_analysis_orchestrator.analyze_site_by_parcel", return_value=expected_response
    ) as analyze_mock:
        result = analyze_site_by_selected_candidate(
            candidate_pnu="1168010300100120002",
            x=127.07662495509604,
            y=37.49629354642009,
            project_profile={"use": "test"},
            procedure_profile={"mode": "test"},
            include_debug=True,
        )

        assert result == expected_response
        verify_mock.assert_called_once_with(
            "1168010300100120002",
            127.07662495509604,
            37.49629354642009,
            api_key=None,
        )
        analyze_mock.assert_called_once_with(
            sigungu_cd="11680",
            bjdong_cd="10300",
            plat_gb_cd="0",
            bun="0012",
            ji="0002",
            project_profile={"use": "test"},
            procedure_profile={"mode": "test"},
            include_debug=True,
            service_key=None,
        )

    with patch("site_data.site_analysis_orchestrator.verify_selected_parcel_candidate", return_value=REJECTED), patch(
        "site_data.site_analysis_orchestrator.analyze_site_by_parcel"
    ) as analyze_mock:
        try:
            analyze_site_by_selected_candidate(
                candidate_pnu="1168010300100120002",
                x=127.07662495509604,
                y=37.49629354642009,
            )
        except SiteBuildError as exc:
            assert "SELECTED_PNU_POLYGON_MISMATCH" in str(exc)
        else:
            raise AssertionError("Rejected selected candidate must not enter parcel analysis")
        analyze_mock.assert_not_called()

    print("SELECTED_PARCEL_CANDIDATE_SITE_ANALYSIS_WIRING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
