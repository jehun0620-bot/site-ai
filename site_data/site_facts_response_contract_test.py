# -*- coding: utf-8 -*-
"""Contract test for the public SITE facts response projection."""
from site_data.site_data_model import Building, Land, Site
from site_data.site_facts_response import build_site_facts_response


def main():
    land = Land(
        land_category="대",
        land_area=123.4,
        zoning="제3종일반주거지역",
    )
    land.source_reference_year = "2026"
    land.source_last_updated_at = "2026-05-12"

    building = Building(
        management_id="TEST",
        dong_name="101동",
        building_name="테스트",
        main_use="공동주택",
        land_area=123.4,
        building_area=50.0,
        total_floor_area=200.0,
        building_coverage_ratio=40.0,
        floor_area_ratio=160.0,
        ground_floor_count=5,
        underground_floor_count=1,
        household_count=10,
        approval_date="20200101",
    )
    site = Site(
        site_id="TEST",
        land=land,
        land_provider_status="AVAILABLE",
        buildings=[building],
    )

    facts = build_site_facts_response(
        site,
        runtime_conditions={
            "지구단위계획": {
                "state": "TRUE",
                "evidence": {"must_not_be_public": True},
            },
            "개발진흥지구": {"state": "FALSE"},
            "취락지구": {"state": "UNKNOWN"},
            "방재지구": {"state": "INVALID"},
        },
    )

    assert facts["land"] == {
        "land_category": "대",
        "land_area": 123.4,
        "zoning": "제3종일반주거지역",
    }
    assert facts["spatial_conditions"] == {
        "district_unit_plan": {"state": "TRUE"},
        "development_promotion_district": {"state": "FALSE"},
        "settlement_district": {"state": "UNKNOWN"},
        "disaster_prevention_district": {"state": "UNKNOWN"},
    }
    assert "evidence" not in facts["spatial_conditions"]["district_unit_plan"]
    assert facts["buildings"]["count"] == 1
    assert facts["buildings"]["items"][0]["management_id"] == "TEST"
    assert facts["buildings"]["items"][0]["ground_floor_count"] == 5
    assert facts["sources"] == {
        "land": "VWORLD_LAND_CHARACTERISTICS",
        "land_status": "AVAILABLE",
        "land_retryable": False,
        "land_reference_year": "2026",
        "land_last_updated_at": "2026-05-12",
        "buildings": "BUILDING_HUB_TITLE",
    }

    failed_site = Site(
        site_id="FAILED",
        land_provider_status="PROVIDER_FAILED",
        land_provider_retryable=True,
    )
    failed = build_site_facts_response(failed_site)
    assert failed["sources"]["land"] is None
    assert failed["sources"]["land_status"] == "PROVIDER_FAILED"
    assert failed["sources"]["land_retryable"] is True

    empty = build_site_facts_response(None)
    assert empty["land"] == {
        "land_category": "",
        "land_area": None,
        "zoning": "",
    }
    assert empty["buildings"] == {"count": 0, "items": []}
    assert empty["spatial_conditions"] == {
        "district_unit_plan": {"state": "UNKNOWN"},
        "development_promotion_district": {"state": "UNKNOWN"},
        "settlement_district": {"state": "UNKNOWN"},
        "disaster_prevention_district": {"state": "UNKNOWN"},
    }
    assert empty["sources"] == {
        "land": None,
        "land_status": None,
        "land_retryable": False,
        "land_reference_year": None,
        "land_last_updated_at": None,
        "buildings": None,
    }

    print("SITE_FACTS_RESPONSE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
