# -*- coding: utf-8 -*-
"""Regression tests for Building HUB numeric value preservation."""

from __future__ import annotations

from site_data.building_converter import convert_building


def main() -> int:
    missing = convert_building({
        "mgmBldrgstPk": "MISSING",
        "platArea": None,
        "archArea": "",
        "totArea": "   ",
        "bcRat": None,
        "vlRat": "",
        "grndFlrCnt": None,
        "ugrndFlrCnt": "",
        "hhldCnt": " ",
    })

    zero = convert_building({
        "mgmBldrgstPk": "ZERO",
        "platArea": 0,
        "archArea": "0",
        "totArea": 0.0,
        "bcRat": "0",
        "vlRat": 0,
        "grndFlrCnt": "0",
        "ugrndFlrCnt": 0,
        "hhldCnt": "0",
    })

    validations = {
        "missing land area": missing.land_area is None,
        "missing building area": missing.building_area is None,
        "missing total floor area": missing.total_floor_area is None,
        "missing BCR": missing.building_coverage_ratio is None,
        "missing FAR": missing.floor_area_ratio is None,
        "missing ground floors": missing.ground_floor_count is None,
        "missing underground floors": missing.underground_floor_count is None,
        "missing households": missing.household_count is None,
        "zero land area": zero.land_area == 0.0,
        "zero building area": zero.building_area == 0.0,
        "zero total floor area": zero.total_floor_area == 0.0,
        "zero BCR": zero.building_coverage_ratio == 0.0,
        "zero FAR": zero.floor_area_ratio == 0.0,
        "zero ground floors": zero.ground_floor_count == 0,
        "zero underground floors": zero.underground_floor_count == 0,
        "zero households": zero.household_count == 0,
    }

    print("BUILDING_HUB_NUMERIC_PRESERVATION")
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)

    return 0 if all(validations.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
