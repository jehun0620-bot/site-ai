# -*- coding: utf-8 -*-
"""STEP 17-21-C-16-8-T-15-S1 family-budget validation hardening."""
from __future__ import annotations
import json
from collections import Counter
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_competent_authority_historical_period_boundary_recovery.json"
TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
MAX_REQUESTS_PER_CONTRACT = 18


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("T-15 FAMILY / CONTRACT BUDGET VALIDATION HARDENING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print()

    if not OUTPUT_PATH.exists():
        raise FileNotFoundError(f"T-15 output not found: {OUTPUT_PATH}")
    data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    probes = data.get("probe_records") or []
    boundaries = data.get("historical_boundaries") or []

    contract_counts = Counter()
    family_counts = Counter()
    for row in probes:
        family = str(row.get("source_family") or "")
        base_url = str(row.get("base_url") or "")
        pagination_key = str(row.get("pagination_key") or "").lower()
        contract_counts[(family, base_url, pagination_key)] += 1
        family_counts[family] += 1

    target_query_leakage = sum(1 for row in probes + boundaries if row.get("target_query_executed") is True)
    document_candidate_leakage = sum(1 for row in probes + boundaries if row.get("document_candidate") is True)
    site_true_leakage = sum(1 for row in probes + boundaries if row.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for row in probes + boundaries if row.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "T-15 output exists": OUTPUT_PATH.exists(),
        "probe records loaded": len(probes) > 0,
        "historical boundaries loaded": len(boundaries) > 0,
        "per-contract request budget respected": all(count <= MAX_REQUESTS_PER_CONTRACT for count in contract_counts.values()),
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_candidate_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": data.get("runtime_registration_allowed") is False,
        "final positive promotion remains blocked": data.get("final_positive_promotion_allowed") is False,
    }

    print("Contract request counts:")
    for key, count in sorted(contract_counts.items()):
        print("-", key, "=>", count)
    print("Family aggregate request counts:", dict(family_counts))
    print()
    print("NOTE: T-15 execution budget is contract-scoped. Multiple independently recovered")
    print("pagination contracts may share one source_family, so family aggregate > 18 is valid.")
    print()
    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        failed = [name for name, passed in validations.items() if not passed]
        print("FAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 T-15 budget validation hardening failed")


if __name__ == "__main__":
    main()
