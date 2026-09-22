# -*- coding: utf-8 -*-

"""Contract regression for the live parcel geometry provider."""

from __future__ import annotations

from unittest.mock import patch

from law_data.parcel_geometry_provider import (
    PARCEL_DATASET,
    resolve_live_parcel_geometry,
)


TARGET_PNU = "1168010300100130000"
OTHER_PNU = "1168010300100140000"
POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [127.0, 37.0],
            [127.1, 37.0],
            [127.1, 37.1],
            [127.0, 37.1],
            [127.0, 37.0],
        ]
    ],
}


def _query(features):
    return {
        "http_status": 200,
        "vworld_status": "OK",
        "classification": "QUERY_SUCCESS",
        "feature_count": len(features),
        "polygon_feature_count": len(features),
        "error": None,
        "features": features,
    }


def _feature(pnu: str, geometry=None):
    return {
        "id": "parcel.1",
        "properties": {"pnu": pnu},
        "geometry": geometry or POLYGON,
    }


def main() -> int:
    validations = {}

    with patch(
        "law_data.parcel_geometry_provider.load_vworld_key",
        return_value="test-key",
    ), patch(
        "law_data.parcel_geometry_provider.query_dataset_by_point",
        return_value=_query([_feature(TARGET_PNU)]),
    ):
        result = resolve_live_parcel_geometry(
            pnu=TARGET_PNU,
            x=127.05,
            y=37.05,
        )

    validations["same PNU geometry loaded"] = result.get("geometry_loaded") is True
    validations["same PNU strict verified"] = result.get("strict_pnu_verified") is True
    validations["same PNU resolution"] = result.get("resolution") == "PNU_POLYGON_VERIFIED"
    validations["same PNU preserved"] = result.get("feature_pnu") == TARGET_PNU
    validations["same PNU dataset"] = result.get("dataset") == PARCEL_DATASET
    validations["same PNU polygon"] = result.get("geometry") == POLYGON

    with patch(
        "law_data.parcel_geometry_provider.load_vworld_key",
        return_value="test-key",
    ), patch(
        "law_data.parcel_geometry_provider.query_dataset_by_point",
        return_value=_query([_feature(OTHER_PNU)]),
    ):
        result = resolve_live_parcel_geometry(
            pnu=TARGET_PNU,
            x=127.05,
            y=37.05,
        )

    validations["mismatched PNU rejected"] = result.get("geometry_loaded") is False
    validations["mismatched PNU resolution"] = result.get("resolution") == "PNU_POLYGON_NOT_FOUND"
    validations["mismatched PNU no strict verification"] = result.get("strict_pnu_verified") is not True
    validations["mismatched PNU match count zero"] = (
        result.get("analysis", {}).get("pnu_polygon_match_count") == 0
    )

    with patch(
        "law_data.parcel_geometry_provider.load_vworld_key",
        return_value="",
    ):
        result = resolve_live_parcel_geometry(
            pnu=TARGET_PNU,
            x=127.05,
            y=37.05,
        )

    validations["missing key fail closed"] = result.get("geometry_loaded") is False
    validations["missing key resolution"] = result.get("resolution") == "VWORLD_KEY_MISSING"

    result = resolve_live_parcel_geometry(
        pnu="",
        x=127.05,
        y=37.05,
    )
    validations["invalid PNU fail closed"] = result.get("geometry_loaded") is False
    validations["invalid PNU resolution"] = result.get("resolution") == "INVALID_PNU"

    all_pass = all(validations.values())

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("all_pass:", all_pass)
    print(
        "CLASSIFICATION:",
        "PARCEL_GEOMETRY_PROVIDER_CONTRACT_PASS"
        if all_pass
        else "PARCEL_GEOMETRY_PROVIDER_CONTRACT_FAIL",
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
