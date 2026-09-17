from unittest.mock import patch

from site_data.address_parcel_identity_resolver import (
    _normalize_parcel_address,
    _parcel_pnus_at_point,
    parcel_identity_from_pnu,
    resolve_address_parcel_identity,
)


def _item(pnu: str, parcel: str, x: float, y: float):
    return {
        "id": pnu,
        "address": {"parcel": parcel},
        "point": {"x": str(x), "y": str(y)},
    }


def _feature(pnu: str):
    return {
        "type": "Feature",
        "geometry": {"type": "MultiPolygon", "coordinates": []},
        "properties": {"pnu": pnu},
    }


def run_contract() -> None:
    ordinary = parcel_identity_from_pnu("1168010300100120000")
    assert ordinary == {
        "sigungu_cd": "11680",
        "bjdong_cd": "10300",
        "plat_gb_cd": "0",
        "bun": "0012",
        "ji": "0000",
    }

    mountain = parcel_identity_from_pnu("1159010600200290003")
    assert mountain == {
        "sigungu_cd": "11590",
        "bjdong_cd": "10600",
        "plat_gb_cd": "1",
        "bun": "0029",
        "ji": "0003",
    }

    assert _normalize_parcel_address("서울특별시 강남구 개포동 12번지") == "서울특별시 강남구 개포동 12"
    assert _normalize_parcel_address("서울특별시 동작구 동작동 산 29-3") == "서울특별시 동작구 동작동 산 29-3"

    with patch(
        "site_data.address_parcel_identity_resolver.query_dataset_by_point",
        return_value={"features": [_feature("1159010600200290003")]},
    ):
        assert _parcel_pnus_at_point("test", 1, 2) == ["1159010600200290003"]

    ordinary_items = [
        _item("1168010300100120000", "서울특별시 강남구 개포동 12", 1, 2),
        _item("1168010300100120001", "서울특별시 강남구 개포동 12-1", 3, 4),
        _item("1168010300100120010", "서울특별시 강남구 개포동 12-10", 5, 6),
    ]
    with patch(
        "site_data.address_parcel_identity_resolver._search_address_items",
        return_value=ordinary_items,
    ) as search, patch(
        "site_data.address_parcel_identity_resolver._parcel_pnus_at_point",
        return_value=["1168010300100120000"],
    ) as polygon:
        resolved_ordinary = resolve_address_parcel_identity("서울특별시 강남구 개포동 12번지", api_key="test")
    search.assert_called_once_with("서울특별시 강남구 개포동 12", "test")
    polygon.assert_called_once_with("test", 1.0, 2.0)
    assert resolved_ordinary.verified is True
    assert resolved_ordinary.pnu == "1168010300100120000"
    assert resolved_ordinary.plat_gb_cd == "0"

    with patch(
        "site_data.address_parcel_identity_resolver._search_address_items",
        return_value=[_item("1159010600200290003", "서울특별시 동작구 동작동 산 29-3", 1, 2)],
    ), patch(
        "site_data.address_parcel_identity_resolver._parcel_pnus_at_point",
        return_value=["1159010600200290003"],
    ):
        resolved = resolve_address_parcel_identity("서울특별시 동작구 동작동 산 29-3", api_key="test")
    assert resolved.verified is True
    assert resolved.pnu == "1159010600200290003"
    assert resolved.plat_gb_cd == "1"
    assert resolved.bun == "0029"
    assert resolved.ji == "0003"

    with patch(
        "site_data.address_parcel_identity_resolver._search_address_items",
        return_value=[_item("1159010600200290003", "mismatch", 1, 2)],
    ), patch(
        "site_data.address_parcel_identity_resolver._parcel_pnus_at_point",
        return_value=["1168010300100120000"],
    ):
        mismatch = resolve_address_parcel_identity("mismatch", api_key="test")
    assert mismatch.verified is False
    assert mismatch.resolution == "ADDRESS_POLYGON_PNU_MISMATCH"

    with patch(
        "site_data.address_parcel_identity_resolver._search_address_items",
        return_value=[
            _item("1168010300100120000", "ambiguous", 1, 2),
            _item("1159010600200290003", "ambiguous", 3, 4),
        ],
    ), patch(
        "site_data.address_parcel_identity_resolver._parcel_pnus_at_point",
        side_effect=[["1168010300100120000"], ["1159010600200290003"]],
    ):
        ambiguous = resolve_address_parcel_identity("ambiguous", api_key="test")
    assert ambiguous.verified is False
    assert ambiguous.resolution == "ADDRESS_PARCEL_AMBIGUOUS"

    with patch("site_data.address_parcel_identity_resolver._search_address_items", return_value=[]):
        empty = resolve_address_parcel_identity("not found", api_key="test")
    assert empty.verified is False
    assert empty.resolution == "ADDRESS_RESULT_EMPTY"

    print("ADDRESS_PARCEL_IDENTITY_RESOLVER_CONTRACT_PASS")


if __name__ == "__main__":
    run_contract()
