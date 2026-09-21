# -*- coding: utf-8 -*-
"""Regression test for automatic latest-available VWorld year selection."""

from __future__ import annotations

from site_data.land_converter import select_latest_land_record
from site_data.vworld_api import get_latest_land_characteristics


PNU = "1168010300100120000"
EXPECTED_YEAR = "2026"


def main() -> int:
    year, records = get_latest_land_characteristics(
        PNU,
        start_year=2026,
        lookback_years=3,
    )
    latest = select_latest_land_record(records)

    validations = {
        "latest available year": year == EXPECTED_YEAR,
        "records exist": bool(records),
        "latest record exists": latest is not None,
        "land category": (latest or {}).get("lndcgrCodeNm") == "대",
        "land area": float((latest or {}).get("lndpclAr") or 0) == 121040.4,
        "zoning": (latest or {}).get("prposArea1Nm") == "제3종일반주거지역",
    }

    print("VWORLD_LATEST_LAND_YEAR_SELECTION")
    print("Selected year:", year)
    print("Record count:", len(records))
    print("Latest lastUpdtDt:", (latest or {}).get("lastUpdtDt"))
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        print("FAILED:")
        for name, passed in validations.items():
            if not passed:
                print("-", name)

    return 0 if all(validations.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
