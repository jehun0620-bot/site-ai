# -*- coding: utf-8 -*-
"""Contract test for parcel-only canonical-PNU land enrichment."""
from unittest.mock import patch
from site_data import site_analysis_orchestrator as orchestrator

PNU = "1159010600200290003"


def _land_record():
    return {
        "pnu": PNU,
        "lndpclAr": "321.5",
        "lndcgrCodeNm": "임야",
        "prposArea1Nm": "제1종일반주거지역",
        "lastUpdtDt": "2026-09-01",
    }


def main():
    with patch.object(orchestrator, "get_latest_land_characteristics", return_value=("2026", [_land_record()])) as land_api:
        site = orchestrator._parcel_only_site(
            sigungu_cd="11590", bjdong_cd="10600", plat_gb_cd="1", bun="0029", ji="0003"
        )
        land_api.assert_called_once_with(PNU)
        assert orchestrator._actual_site_pnu(site) == PNU
        assert site.land is not None
        assert site.land.zoning == "제1종일반주거지역"
        assert site.land.land_category == "임야"
        assert site.land.land_area == 321.5
        assert site.land.source_reference_year == "2026"
        assert site.land.source_last_updated_at == "2026-09-01"

    with patch.object(orchestrator, "get_latest_land_characteristics", return_value=("2026", [])):
        site = orchestrator._parcel_only_site(
            sigungu_cd="11590", bjdong_cd="10600", plat_gb_cd="1", bun="0029", ji="0003"
        )
        assert site.land is None

    with patch.object(orchestrator, "get_latest_land_characteristics", side_effect=RuntimeError("unavailable")):
        site = orchestrator._parcel_only_site(
            sigungu_cd="11590", bjdong_cd="10600", plat_gb_cd="1", bun="0029", ji="0003"
        )
        assert site.land is None

    print("PARCEL_ONLY_LAND_ENRICHMENT_CONTRACT_PASS")


if __name__ == "__main__":
    main()
