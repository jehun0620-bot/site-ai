# -*- coding: utf-8 -*-
"""Diagnostic check for VWorld land-characteristics year availability.

This test intentionally does not change production year-selection behavior.
It probes explicit years so we can choose a currentness policy from observed
provider data instead of guessing.
"""

from __future__ import annotations

from site_data.land_converter import select_latest_land_record
from site_data.vworld_api import get_land_characteristics


PNU = "1168010300100120000"
YEARS = ("2024", "2025", "2026")


def main() -> int:
    print("VWORLD_LAND_CHARACTERISTICS_YEAR_AVAILABILITY")
    print("PNU:", PNU)

    completed = True

    for year in YEARS:
        try:
            records = get_land_characteristics(PNU, stdr_year=year)
            latest = select_latest_land_record(records)
            print()
            print("Year:", year)
            print("Record count:", len(records))
            print("Latest lastUpdtDt:", (latest or {}).get("lastUpdtDt"))
            print("Land category:", (latest or {}).get("lndcgrCodeNm"))
            print("Land area:", (latest or {}).get("lndpclAr"))
            print("Zoning:", (latest or {}).get("prposArea1Nm"))
        except Exception as exc:
            completed = False
            print()
            print("Year:", year)
            print("ERROR:", type(exc).__name__, str(exc))

    print()
    print("probe_completed:", completed)
    return 0 if completed else 1


if __name__ == "__main__":
    raise SystemExit(main())
