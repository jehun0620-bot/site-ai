from unittest.mock import patch

from site_data.site_analysis_orchestrator import (
    SiteBuildError,
    _actual_site_pnu,
    _parcel_only_site,
    analyze_site_by_parcel,
)


def main():
    mountain = _parcel_only_site(
        sigungu_cd="11590",
        bjdong_cd="10600",
        plat_gb_cd="1",
        bun="0029",
        ji="0003",
    )
    assert mountain.buildings == []
    assert _actual_site_pnu(mountain) == "1159010600200290003"

    try:
        _parcel_only_site(
            sigungu_cd="11590",
            bjdong_cd="10600",
            plat_gb_cd="2",
            bun="0029",
            ji="0003",
        )
    except SiteBuildError:
        pass
    else:
        raise AssertionError("invalid parcel identity was admitted")

    captured = {}

    def fake_fetch(**kwargs):
        captured.update(kwargs)
        return {
            "items": [],
            "total_count": 0,
            "result_code": "00",
            "result_message": "NORMAL SERVICE",
        }

    def fake_analyze(site, **kwargs):
        captured["site"] = site
        return {"analysis_contract_version": "test"}

    def fake_response(analysis, include_debug=False):
        return {"analysis": analysis, "include_debug": include_debug}

    with patch("site_data.site_analysis_orchestrator.fetch_building_items", fake_fetch), patch(
        "site_data.site_analysis_orchestrator.analyze_site_object", fake_analyze
    ), patch(
        "site_data.site_analysis_orchestrator.build_site_analysis_response", fake_response
    ):
        response = analyze_site_by_parcel(
            sigungu_cd="11590",
            bjdong_cd="10600",
            plat_gb_cd="1",
            bun="0029",
            ji="0003",
        )

    assert captured["plat_gb_cd"] == "1"
    assert captured["site"].buildings == []
    assert _actual_site_pnu(captured["site"]) == "1159010600200290003"
    assert response["service"]["building_count"] == 0
    assert response["service"]["building_total_count"] == 0
    assert response["service"]["building_api_status"] == "00"

    print("PARCEL_ONLY_SITE_ORCHESTRATOR_CONTRACT_PASS")


if __name__ == "__main__":
    main()
