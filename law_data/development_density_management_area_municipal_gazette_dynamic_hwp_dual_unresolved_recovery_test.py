# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S3
Targeted bounded recovery for the two unresolved rows observed in the first
50-row accelerated dynamic HWP batch.

Targets
-------
1) pstSn 28821 / Gazette 674: prior failure = file too large under 16 MiB cap.
   Retry only this row with a 32 MiB per-file cap.
2) pstSn 28847 / Gazette 699: prior failure = HWP attachment not found.
   Run metadata-only attachment forensics for this exact row. Do not infer absence
   of legal content and do not perform OCR/PDF fallback here.

Safety
------
- no legal promotion
- no negative evidence
- no bulk traversal
- bounded to the two known unresolved rows
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_dual_unresolved_recovery.json"

LARGE_PST = "28821"
MISSING_HWP_PST = "28847"


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("DYNAMIC HWP DUAL UNRESOLVED RECOVERY")
    print("=" * 60)
    print("Large-file target pstSn:", LARGE_PST)
    print("Missing-HWP target pstSn:", MISSING_HWP_PST)
    print("Large-file cap: 32 MiB")
    print("OCR: DISABLED")
    print("PDF fallback: DISABLED")
    print()

    # Part A: reuse T-34 state-repair machinery, but select exactly one row and
    # raise only the per-file cap. Because unresolved rows are not processed,
    # pstSn 28821 is the first retryable row.
    original_batch = t34.BATCH_SIZE
    original_requests = t34.MAX_REQUESTS
    original_cap = hwp5.MAX_FILE_BYTES
    try:
        t34.BATCH_SIZE = 1
        t34.MAX_REQUESTS = 2
        hwp5.MAX_FILE_BYTES = 32 * 1024 * 1024
        print("PART A - LARGE FILE RETRY")
        t34.main()
    finally:
        t34.BATCH_SIZE = original_batch
        t34.MAX_REQUESTS = original_requests
        hwp5.MAX_FILE_BYTES = original_cap

    # Part B: metadata-only forensics for the exact row where the normal HWP
    # selector found no HWP attachment. Preserve the raw attachment metadata so
    # the next stage can decide whether PDF/other attachment handling is needed.
    print()
    print("PART B - MISSING HWP ATTACHMENT METADATA FORENSICS")
    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    hs, mu, obj = hwp5.get_json(session, MISSING_HWP_PST)
    selected_hwp = hwp5.hwp_attachment(obj)

    forensic: Dict[str, Any] = {
        "pstSn": MISSING_HWP_PST,
        "metadata_http": hs,
        "metadata_url": mu,
        "selected_hwp_attachment": selected_hwp,
        "metadata_type": type(obj).__name__,
        "metadata": obj,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(forensic, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Metadata HTTP:", hs)
    print("Metadata URL:", mu)
    print("Selected HWP attachment:", selected_hwp)
    print("Metadata type:", type(obj).__name__)
    if isinstance(obj, dict):
        print("Metadata keys:", list(obj.keys()))
    elif isinstance(obj, list):
        print("Metadata item count:", len(obj))
        for idx, item in enumerate(obj[:20], start=1):
            print(f"ATTACHMENT {idx}:", item)
    else:
        print("Metadata repr:", repr(obj)[:2000])

    vals = {
        "official metadata host": hwp5.host(mu) == "www.seongnam.go.kr",
        "target remains without normal HWP selection": selected_hwp is None,
        "negative evidence disabled": not forensic["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any([
            forensic["verified_positive"],
            forensic["runtime_registration_allowed"],
            forensic["site_positive_allowed"],
            forensic["site_negative_allowed"],
            forensic["final_positive_promotion_allowed"],
        ]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("FORENSICS VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("forensics_all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("dual unresolved recovery forensics failed")


if __name__ == "__main__":
    main()
