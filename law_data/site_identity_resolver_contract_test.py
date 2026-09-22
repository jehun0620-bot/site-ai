# -*- coding: utf-8 -*-

"""Contract regression for SITE identity resolution and PNU isolation."""

from __future__ import annotations

from copy import deepcopy
from unittest.mock import patch

from law_data.site_identity_resolver import resolve_site_identity


PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _resolve(base_site=None, site_input=None, query=None, parcel_site=None, selected=None):
    payloads = [
        {"query_context": query or {}},
        {"site": parcel_site or {}, "selected": selected or {}},
    ]
    with patch(
        "law_data.site_identity_resolver.load_json",
        side_effect=payloads,
    ):
        return resolve_site_identity(
            base_site=base_site,
            site_input=site_input,
        )


def main() -> int:
    validations = {}

    base = {
        "pnu": PNU,
        "site_id": "BASE-ID",
        "address": "BASE-ADDRESS",
        "road_address": "BASE-ROAD",
        "zone": "BASE-ZONE",
        "sigungu_code": "11680",
        "bjdong_code": "10300",
        "main_no": "0012",
        "sub_no": "0000",
        "coordinate": {"x": 127.1, "y": 37.5, "crs": "EPSG:4326"},
    }
    base_before = deepcopy(base)
    result = _resolve(base_site=base, site_input={"pnu": PNU})

    validations["same PNU base identity reused"] = (
        result["site_id"] == "BASE-ID"
        and result["address"] == "BASE-ADDRESS"
        and result["sigungu_code"] == "11680"
        and result["bjdong_code"] == "10300"
    )
    validations["same PNU coordinate reused"] = (
        result["x"] == 127.1 and result["y"] == 37.5
    )
    validations["same PNU complete"] = result["identity_status"] == "COMPLETE"
    validations["base input immutable"] = base == base_before

    result = _resolve(
        base_site={**base, "pnu": OTHER_PNU},
        site_input={"pnu": PNU, "site_id": "INPUT-ID", "address": "INPUT-ADDRESS"},
        query={
            "pnu": OTHER_PNU,
            "site_id": "QUERY-ID",
            "sigungu_code": "99999",
            "bjdong_code": "99999",
        },
        parcel_site={
            "pnu": OTHER_PNU,
            "site_id": "PARCEL-ID",
            "zone": "WRONG-ZONE",
            "point": {"x": 1.0, "y": 2.0, "crs": "EPSG:4326"},
        },
    )
    validations["mismatched PNU identity blocked"] = (
        result["site_id"] == "INPUT-ID"
        and result["address"] == "INPUT-ADDRESS"
        and result["sigungu_code"] is None
        and result["bjdong_code"] is None
        and result["zone"] is None
    )
    validations["mismatched PNU coordinate blocked"] = (
        result["x"] is None and result["y"] is None
    )
    validations["mismatched PNU partial"] = (
        result["identity_status"] == "PARTIAL"
        and "sigungu_code" in result["missing_identity_fields"]
        and "zone" in result["missing_identity_fields"]
    )

    site_input = {
        "pnu": PNU,
        "site_id": "INPUT-ID",
        "address": "INPUT-ADDRESS",
        "road_address": "INPUT-ROAD",
        "zone": "INPUT-ZONE",
        "sigungu_cd": "11680",
        "bjdong_cd": "10300",
        "bun": "0012",
        "ji": "0000",
        "longitude": 127.2,
        "latitude": 37.6,
    }
    site_input_before = deepcopy(site_input)
    result = _resolve(
        base_site=base,
        site_input=site_input,
        query={"pnu": PNU, "site_id": "QUERY-ID", "address": "QUERY-ADDRESS"},
    )
    validations["caller identity authoritative"] = (
        result["site_id"] == "INPUT-ID"
        and result["address"] == "INPUT-ADDRESS"
        and result["road_address"] == "INPUT-ROAD"
        and result["zone"] == "INPUT-ZONE"
    )
    validations["caller aliases normalized"] = (
        result["sigungu_code"] == "11680"
        and result["bjdong_code"] == "10300"
        and result["main_no"] == "0012"
        and result["sub_no"] == "0000"
    )
    validations["caller coordinate authoritative"] = (
        result["x"] == 127.2 and result["y"] == 37.6
    )
    validations["caller complete"] = (
        result["identity_status"] == "COMPLETE"
        and result["coordinate_status"] == "CONFIRMED"
        and result["missing_identity_fields"] == []
    )
    validations["caller input immutable"] = site_input == site_input_before

    all_pass = all(validations.values())
    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")
    print("all_pass:", all_pass)
    print(
        "CLASSIFICATION:",
        "SITE_IDENTITY_RESOLVER_CONTRACT_PASS"
        if all_pass
        else "SITE_IDENTITY_RESOLVER_CONTRACT_FAIL",
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
