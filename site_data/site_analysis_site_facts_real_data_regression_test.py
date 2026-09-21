# -*- coding: utf-8 -*-
"""Real-provider regression for public VERIFIED SITE FACTS."""

from __future__ import annotations

from site_data.site_analysis_orchestrator import analyze_site_by_parcel


EXPECTED_PNU = "1168010300100120000"


def main() -> int:
    response = analyze_site_by_parcel(
        sigungu_cd="11680",
        bjdong_cd="10300",
        plat_gb_cd="0",
        bun="0012",
        ji="0000",
    )

    site_facts = response.get("site_facts") or {}
    land = site_facts.get("land") or {}
    buildings = site_facts.get("buildings") or {}
    items = buildings.get("items") or []
    sources = site_facts.get("sources") or {}

    validations = {
        "schema": response.get("schema_version") == "SITE_ANALYSIS_API_V1",
        "ready": response.get("status") == "READY",
        "pnu": (response.get("site") or {}).get("pnu") == EXPECTED_PNU,
        "land category": land.get("land_category") == "대",
        "land area": land.get("land_area") == 121040.4,
        "zoning": land.get("zoning") == "제3종일반주거지역",
        "building count": buildings.get("count") == 34,
        "building item count": len(items) == 34,
        "building identity": all(item.get("management_id") is not None for item in items),
        "building use": any(str(item.get("main_use") or "").strip() for item in items),
        "land source": sources.get("land") == "VWORLD_LAND_CHARACTERISTICS",
        "building source": sources.get("buildings") == "BUILDING_HUB_TITLE",
        "service count agrees": (response.get("service") or {}).get("building_count") == buildings.get("count"),
    }

    print("Schema:", response.get("schema_version"))
    print("Status:", response.get("status"))
    print("PNU:", (response.get("site") or {}).get("pnu"))
    print("Land:", land)
    print("Building count:", buildings.get("count"))
    print("Building item count:", len(items))
    print("Sources:", sources)
    print("Service:", response.get("service"))
    print()
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)

    return 0 if all(validations.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
