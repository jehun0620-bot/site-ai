# -*- coding: utf-8 -*-
"""Contract test for Building-HUB-backed Site land-provider provenance."""
from unittest.mock import patch

from site_data import site_builder
from site_data.vworld_api import VWorldLandNoDataError, VWorldLandProviderError

PNU = "1168010300100120000"


def _building_item():
    return {
        "sigunguCd": "11680",
        "bjdongCd": "10300",
        "platGbCd": "0",
        "bun": "0012",
        "ji": "0000",
        "platPlc": "서울특별시 강남구 개포동 12",
        "newPlatPlc": "서울특별시 강남구 개포로109길 21",
    }


def _land_record():
    return {
        "pnu": PNU,
        "lndpclAr": "123.4",
        "lndcgrCodeNm": "대",
        "prposArea1Nm": "제3종일반주거지역",
        "lastUpdtDt": "2026-09-01",
    }


def main():
    with patch.object(site_builder, "convert_building", side_effect=lambda item: item), patch.object(
        site_builder, "get_latest_land_characteristics", return_value=("2026", [_land_record()])
    ) as land_api:
        site = site_builder.create_site([_building_item()])
        land_api.assert_called_once_with(PNU)
        assert site is not None
        assert site.land is not None
        assert site.land_provider_status == "AVAILABLE"
        assert site.land_provider_retryable is False

    with patch.object(site_builder, "convert_building", side_effect=lambda item: item), patch.object(
        site_builder, "get_latest_land_characteristics", return_value=("2026", [])
    ):
        site = site_builder.create_site([_building_item()])
        assert site is not None
        assert site.land is None
        assert site.land_provider_status == "NO_DATA"
        assert site.land_provider_retryable is False

    with patch.object(site_builder, "convert_building", side_effect=lambda item: item), patch.object(
        site_builder,
        "get_latest_land_characteristics",
        side_effect=VWorldLandNoDataError("no data"),
    ):
        site = site_builder.create_site([_building_item()])
        assert site is not None
        assert site.land is None
        assert site.land_provider_status == "NO_DATA"
        assert site.land_provider_retryable is False

    for retryable in (True, False):
        with patch.object(site_builder, "convert_building", side_effect=lambda item: item), patch.object(
            site_builder,
            "get_latest_land_characteristics",
            side_effect=VWorldLandProviderError("unavailable", retryable=retryable),
        ):
            site = site_builder.create_site([_building_item()])
            assert site is not None
            assert site.land is None
            assert site.land_provider_status == "PROVIDER_FAILED"
            assert site.land_provider_retryable is retryable

    with patch.object(site_builder, "convert_building", side_effect=lambda item: item), patch.object(
        site_builder, "get_latest_land_characteristics", side_effect=ValueError("bad land data")
    ):
        site = site_builder.create_site([_building_item()])
        assert site is not None
        assert site.land is None
        assert site.land_provider_status == "PROVIDER_FAILED"
        assert site.land_provider_retryable is False

    print("BUILDING_SITE_LAND_ENRICHMENT_CONTRACT_PASS")


if __name__ == "__main__":
    main()
