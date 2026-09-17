# -*- coding: utf-8 -*-
"""Contract test for cross-PNU SITE identity fallback isolation."""
from __future__ import annotations

import law_data.site_identity_resolver as resolver


def _without_persisted_sources():
    original = resolver.load_json
    resolver.load_json = lambda path: {}
    return original


def main() -> None:
    original = _without_persisted_sources()
    try:
        base = {
            "site_id": "11680-10300-0012-0000",
            "address": "서울특별시 강남구 개포동 12번지",
            "road_address": "서울특별시 강남구 개포로109길 5",
            "pnu": "1168010300100120000",
            "sigungu_code": "11680",
            "bjdong_code": "10300",
            "main_no": "0012",
            "sub_no": "0000",
            "zone": "제3종일반주거지역",
            "coordinate": {"x": 127.0, "y": 37.0, "crs": "EPSG:4326"},
        }
        mountain = {
            "site_id": "11590-10600-0029-0003",
            "pnu": "1159010600200290003",
            "sigungu_code": "11590",
            "bjdong_code": "10600",
            "main_no": "0029",
            "sub_no": "0003",
        }
        isolated = resolver.resolve_site_identity(base_site=base, site_input=mountain)
        assert isolated["pnu"] == mountain["pnu"]
        assert isolated["address"] is None
        assert isolated["road_address"] is None
        assert isolated["zone"] is None
        assert isolated["coordinate"]["x"] is None
        assert isolated["coordinate"]["y"] is None
        assert isolated["identity_status"] == "PARTIAL"
        assert "address" in isolated["missing_identity_fields"]
        assert "zone" in isolated["missing_identity_fields"]

        same_pnu = {
            "site_id": base["site_id"],
            "pnu": base["pnu"],
            "sigungu_code": base["sigungu_code"],
            "bjdong_code": base["bjdong_code"],
            "main_no": base["main_no"],
            "sub_no": base["sub_no"],
        }
        compatible = resolver.resolve_site_identity(base_site=base, site_input=same_pnu)
        assert compatible["address"] == base["address"]
        assert compatible["road_address"] == base["road_address"]
        assert compatible["zone"] == base["zone"]
        assert compatible["coordinate"]["x"] == base["coordinate"]["x"]
        assert compatible["identity_status"] == "COMPLETE"
    finally:
        resolver.load_json = original

    print("SITE_IDENTITY_CROSS_PNU_FALLBACK_GUARD_CONTRACT_PASS")


if __name__ == "__main__":
    main()
