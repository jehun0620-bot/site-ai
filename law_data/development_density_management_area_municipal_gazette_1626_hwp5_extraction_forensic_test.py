# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S56
Gazette 1626 / pstSn 188147 HWP5 extraction forensic.

Purpose:
- reproduce the exact HWP5 extraction failure with the hardened 1M-record parser;
- expose FileHeader flags and per-section parser diagnostics;
- inspect any text retained despite extract_ok=False for UQQ700 terms;
- do not mutate cumulative state and do not create legal negative evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_quarantine_resume_test as h2
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1626_hwp5_extraction_forensic.json"
PSTSN = "188147"
GAZETTE_NUMBER = 1626
DATE = "2019-10-01"
LARGE_FILE_LIMIT = 64 * 1024 * 1024


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1626 HWP5 EXTRACTION FORENSIC")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print("Negative evidence: DISABLED")

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    hs, mu, obj = hwp5.get_json(session, PSTSN)
    att = hwp5.hwp_attachment(obj)
    if not att:
        raise AssertionError("HWP attachment not found in forensic probe")
    ds, du, raw = hwp5.get_file(session, PSTSN, att["file_no"])
    signature = base.classify_signature(raw)

    original_limit = hwp5.MAX_FILE_BYTES
    original_parser = hwp5.parse_records_text
    hwp5.MAX_FILE_BYTES = LARGE_FILE_LIMIT
    hwp5.parse_records_text = h2.high_limit_parse_records_text
    try:
        ext: Dict[str, Any] = hwp5.extract_hwp5(raw)
    finally:
        hwp5.MAX_FILE_BYTES = original_limit
        hwp5.parse_records_text = original_parser

    text = ext.get("text", "") or ""
    sections = ext.get("sections") or []
    direct = {t: text.count(t) for t in hwp5.DIRECT}
    related = {t: text.count(t) for t in hwp5.RELATED}
    high_signal = {t: related.get(t, 0) for t in base.HIGH_SIGNAL_RELATED}
    low_signal = {t: related.get(t, 0) for t in base.LOW_SIGNAL_RELATED}
    error_sections = [s for s in sections if s.get("parse_error") or not s.get("fully_consumed")]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S56",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "metadata_http": hs,
        "metadata_url": mu,
        "attachment": att,
        "download_http": ds,
        "download_url": du,
        "download_bytes": len(raw),
        "signature_class": signature,
        "extract_ok": ext.get("ok"),
        "extract_error": ext.get("error"),
        "hwp_flags": ext.get("flags") or {},
        "section_count": len(sections),
        "sections": sections,
        "error_section_count": len(error_sections),
        "error_sections": error_sections,
        "text_chars": len(text),
        "direct_matches": direct,
        "related_matches": related,
        "high_signal_related_matches": high_signal,
        "low_signal_related_matches": low_signal,
        "state_mutation_executed": False,
        "ocr_executed": False,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Metadata HTTP:", hs)
    print("Attachment:", att)
    print("Download HTTP:", ds)
    print("Download bytes:", len(raw))
    print("Signature:", signature)
    print("Extract OK:", ext.get("ok"))
    print("Extract error:", ext.get("error"))
    print("HWP flags:", output["hwp_flags"])
    print("Section count:", len(sections))
    print("Error section count:", len(error_sections))
    for i, sec in enumerate(sections, 1):
        print(f"SECTION {i}:", {k: sec.get(k) for k in ["stream", "stored_bytes", "plain_bytes", "records", "para_text_records", "fully_consumed", "parse_error", "text_chars"]})
    print("Text chars:", len(text))
    print("Direct matches:", direct)
    print("High-signal related matches:", high_signal)
    print("Low-signal related matches:", low_signal)
    print("Output:", OUT)

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "metadata HTTP 200": hs == 200,
        "attachment recovered": bool(att),
        "download HTTP 200": ds == 200,
        "HWP5 signature": signature == "HWP5",
        "text retained": len(text) > 0,
        "forensic section diagnostics available": len(sections) > 0,
        "state mutation disabled": not output["state_mutation_executed"],
        "OCR disabled": not output["ocr_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "parser restored": hwp5.parse_records_text is original_parser,
        "file limit restored": hwp5.MAX_FILE_BYTES == original_limit,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1626 HWP5 extraction forensic validation failed")


if __name__ == "__main__":
    main()
