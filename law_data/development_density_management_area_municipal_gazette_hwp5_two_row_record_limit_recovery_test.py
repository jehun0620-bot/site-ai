# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S11
Targeted recovery for the two current HWP5 unresolved municipal-gazette rows
using the already validated 600,000-record bounded parser from T-34-S8.

Safety:
- exact two-row target set only
- max 4 network requests
- no OCR/PDF fallback
- no legal promotion / no negative evidence
"""
from __future__ import annotations

import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_hwp5_record_limit_recovery_and_candidate_reclassification_test as s8

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_two_row_record_limit_recovery.json"
TARGETS = {"29032", "29038"}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HWP5 TWO-ROW RECORD-LIMIT RECOVERY")
    print("=" * 60)
    print("Targets:", sorted(TARGETS))
    print("Temporary record limit:", s8.RECORD_LIMIT)
    print("OCR/PDF fallback: DISABLED")
    print()

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    before = json.loads(STATE.read_text(encoding="utf-8"))
    unresolved = [r for r in (before.get("results") or []) if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    unresolved_ids = {str(r.get("pstSn")) for r in unresolved}
    if unresolved_ids != TARGETS:
        raise AssertionError(f"expected unresolved targets {sorted(TARGETS)}, got {sorted(unresolved_ids)}")

    original_parser = hwp5.parse_records_text
    original_batch = t34.BATCH_SIZE
    original_requests = t34.MAX_REQUESTS
    try:
        hwp5.parse_records_text = s8.parse_records_text_with_higher_bound
        t34.BATCH_SIZE = 2
        t34.MAX_REQUESTS = 4
        t34.main()
    finally:
        hwp5.parse_records_text = original_parser
        t34.BATCH_SIZE = original_batch
        t34.MAX_REQUESTS = original_requests

    after = json.loads(STATE.read_text(encoding="utf-8"))
    results = after.get("results") or []
    by_pst = {str(r.get("pstSn")): r for r in results}
    recovered = [by_pst.get(pst) for pst in sorted(TARGETS)]
    unresolved_after = [r for r in results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    candidates = [r for r in results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]

    summary = {
        "targets": sorted(TARGETS),
        "recovered_rows": recovered,
        "processed_count": len(after.get("processed_pstSn") or []),
        "remaining_count": 1338 - len(after.get("processed_pstSn") or []),
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved_after),
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("RECOVERY RESULTS")
    for row in recovered:
        print(row)
    print()
    print("SUMMARY")
    print("Processed:", summary["processed_count"])
    print("Remaining:", summary["remaining_count"])
    print("Candidates:", summary["candidate_count"])
    print("Unresolved:", summary["unresolved_count"])
    print("State:", STATE)
    print("Output:", OUT)

    unsafe = any([
        summary["verified_positive"], summary["runtime_registration_allowed"],
        summary["site_positive_allowed"], summary["site_negative_allowed"],
        summary["final_positive_promotion_allowed"],
    ])
    vals = {
        "exact targets recovered": all(row is not None for row in recovered),
        "all targets HWP5": all((row or {}).get("signature_class") == "HWP5" for row in recovered),
        "all targets parsed HWP5": all((row or {}).get("parser_used") == "HWP5" for row in recovered),
        "no target unresolved": all((row or {}).get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN" for row in recovered),
        "global unresolved zero": len(unresolved_after) == 0,
        "candidate count zero": len(candidates) == 0,
        "processed arithmetic": summary["processed_count"] == 388,
        "remaining arithmetic": summary["remaining_count"] == 950,
        "negative evidence disabled": not summary["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("two-row record-limit recovery failed")


if __name__ == "__main__":
    main()
