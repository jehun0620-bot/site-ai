from unittest.mock import patch

from site_data.address_parcel_identity_resolver import AddressParcelIdentityResolution
from site_data.site_analysis_orchestrator import SiteBuildError, analyze_site_by_address


def _verified_identity():
    return AddressParcelIdentityResolution(
        status="VERIFIED",
        resolution="ADDRESS_PARCEL_IDENTITY_VERIFIED",
        address="서울특별시 강남구 개포동 12번지",
        pnu="1168010300100120000",
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0000",
        x=127.07539280356858,
        y=37.494197498186885,
        crs="EPSG:4326",
    )


def _rejected_identity():
    return AddressParcelIdentityResolution(
        status="REJECTED",
        resolution="ADDRESS_RESULT_EMPTY",
        address="not found",
    )


def run_contract() -> None:
    expected={"site":{"pnu":"1168010300100120000"},"service":{"building_count":34}}
    with patch(
        "site_data.site_analysis_orchestrator.resolve_address_parcel_identity",
        return_value=_verified_identity(),
    ) as resolver, patch(
        "site_data.site_analysis_orchestrator.analyze_site_by_parcel",
        return_value=expected,
    ) as parcel_analysis:
        result=analyze_site_by_address(
            address="서울특별시 강남구 개포동 12번지",
            project_profile={"use":"office"},
            procedure_profile={"review":"required"},
            include_debug=True,
            service_key="building-test",
            vworld_api_key="vworld-test",
        )

    assert result is expected
    resolver.assert_called_once_with("서울특별시 강남구 개포동 12번지",api_key="vworld-test")
    parcel_analysis.assert_called_once_with(
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0000",
        project_profile={"use":"office"},
        procedure_profile={"review":"required"},
        include_debug=True,
        service_key="building-test",
    )

    with patch(
        "site_data.site_analysis_orchestrator.resolve_address_parcel_identity",
        return_value=_rejected_identity(),
    ), patch("site_data.site_analysis_orchestrator.analyze_site_by_parcel") as parcel_analysis:
        try:
            analyze_site_by_address(address="not found",vworld_api_key="vworld-test")
        except SiteBuildError as exc:
            assert "ADDRESS_RESULT_EMPTY" in str(exc)
        else:
            raise AssertionError("unverified address identity must fail closed")
        parcel_analysis.assert_not_called()

    print("ADDRESS_SITE_ANALYSIS_ORCHESTRATOR_WIRING_CONTRACT_PASS")


if __name__ == "__main__":
    run_contract()
