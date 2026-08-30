# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S57
Gazette 1626 / pstSn 188147 bounded HWP5 retry with a raised record ceiling.

Purpose:
- retry the exact known distribution HWP5 whose single ViewText section hit the
  1,000,000-record parser ceiling in S56;
- raise only the record ceiling for this exact target to 2,000,000 records;
- keep the existing 64 MiB file ceiling;
- report whether the section is fully consumed and any UQQ700 terms;
- do not mutate cumulative state;
- no OCR, legal negative evidence, or SITE/runtime promotion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1626_hwp5_raised_record_ceiling_retry.json"
PSTSN = "188147"
GAZETTE_NUMBER = 1626
DATE = "2019-10-01"
FILE_LIMIT = 64 * 1024 * 1024
RECORD_LIMIT = 2_000_000


def raised_limit_parse_records_text(data: bytes) -> Dict[str, Any]:
    offset = 0
    records = 0
    paragraphs: List[str] = []
    para_count = 0
    error = ""
    while offset < len(data):
        try:
            rec, next_offset = hwp5.parse_record_header(data, offset)
        except Exception as exc:
            error = repr(exc)
            break
        if rec["tag_id"] == hwp5.PARA_TEXT_TAG:
            para_count += 1
            text = hwp5.sanitize_para_text(data[rec["payload_offset"]:rec["end"]])
            if text:
                paragraphs.append(text)
        records += 1
        offset = next_offset
        if records > RECORD_LIMIT:
            error = f"record safety limit exceeded ({RECORD_LIMIT})"
            break
    return {
        "record_count": records,
        "para_text_record_count": para_count,
        "fully_consumed": offset == len(data),
        "parse_error": error,
        "text": "\n".join(paragraphs),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1626 HWP5 RAISED RECORD CEILING RETRY")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("File ceiling:", FILE_LIMIT)
    print("Record ceiling:", RECORD_LIMIT)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print("Negative evidence: DISABLED")

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    hs, mu, obj = hwp5.get_json(session, PSTSN)
    att = hwp5.hwp_attachment(obj)
    if not att:
        raise AssertionError("HWP attachment not found")
    ds, du, raw = hwp5.get_file(session, PSTSN, att["file_no"])
    signature = base.classify_signature(raw)
    if signature != "HWP5":
        raise AssertionError(f"unexpected signature: {signature}")

    original_limit = hwp5.MAX_FILE_BYTES
    original_parser = hwp5.parse_records_text
    hwp5.MAX_FILE_BYTES = FILE_LIMIT
    hwp5.parse_records_text = raised_limit_parse_records_text
    try:
        ext = hwp5.extract_hwp5(raw)
    finally:
        hwp5.MAX_FILE_BYTES = original_limit
        hwp5.parse_records_text = original_parser

    text = ext.get("text", "") or ""
    sections = ext.get("sections") or []
    direct = {t: text.count(t) for t in hwp5.DIRECT}
    related = {t: text.count(t) for t in hwp5.RELATED}
    high_signal = {t: related.get(t, 0) for t in base.HIGH_SIGNAL_RELATED}
    low_signal = {t: related.get(t, 0) for t in base.LOW_SIGNAL_RELATED}
    all_consumed = bool(sections) and all(s.get("fully_consumed") and not s.get("parse_error") for s in sections)

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S57",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "metadata_http": hs,
        "metadata_url": mu,
        "attachment": att,
        "download_http": ds,
        "download_url": du,
        "download_bytes": len(raw),
        "signature_class": signature,
        "record_limit": RECORD_LIMIT,
        "extract_ok": ext.get("ok"),
        "extract_error": ext.get("error"),
        "hwp_flags": ext.get("flags") or {},
        "section_count": len(sections),
        "sections": sections,
        "all_sections_fully_consumed": all_consumed,
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
    print("Extract OK:", ext.get("ok"))
    print("Extract error:", ext.get("error"))
    print("HWP flags:", output["hwp_flags"])
    print("Section count:", len(sections))
    for i, sec in enumerate(sections, 1):
        print(f"SECTION {i}:", {k: sec.get(k) for k in ["stream", "stored_bytes", "plain_bytes", "records", "para_text_records", "fully_consumed", "parse_error", "text_chars"]})
    print("All sections fully consumed:", all_consumed)
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
        "section diagnostics available": len(sections) > 0,
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
        raise AssertionError("Gazette 1626 raised record ceiling retry validation failed")


if __name__ == "__main__":
    main()
