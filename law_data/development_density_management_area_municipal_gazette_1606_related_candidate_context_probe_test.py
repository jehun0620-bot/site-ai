# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S50
Context probe for Gazette 1606 / pstSn 183149 RELATED_CANDIDATE.

Safety:
- exact target only;
- no cumulative state mutation;
- no OCR;
- no legal negative evidence;
- no SITE/runtime promotion.
"""
from __future__ import annotations

import json
from pathlib import Path

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_quarantine_resume_test as h2

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1606_related_candidate_context_probe.json"

PSTSN = "183149"
GAZETTE_NUMBER = 1606
DATE = "2019-05-27"
TERM = "개발밀도"
CONTEXT_RADIUS = 700
LARGE_FILE_LIMIT = 64 * 1024 * 1024


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1606 RELATED CANDIDATE CONTEXT PROBE")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("Term:", TERM)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print("Negative evidence: DISABLED")

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    hs, mu, obj = hwp5.get_json(session, PSTSN)
    att = hwp5.hwp_attachment(obj)
    if not att:
        raise AssertionError("expected HWP attachment for Gazette 1606")

    original_file_limit = hwp5.MAX_FILE_BYTES
    original_parser = hwp5.parse_records_text
    try:
        hwp5.MAX_FILE_BYTES = LARGE_FILE_LIMIT
        hwp5.parse_records_text = h2.high_limit_parse_records_text
        ds, du, raw = hwp5.get_file(session, PSTSN, att["file_no"])
        ext = hwp5.extract_hwp5(raw)
    finally:
        hwp5.MAX_FILE_BYTES = original_file_limit
        hwp5.parse_records_text = original_parser

    text = ext.get("text", "") or ""
    hits = []
    pos = 0
    while True:
        idx = text.find(TERM, pos)
        if idx < 0:
            break
        lo = max(0, idx - CONTEXT_RADIUS)
        hi = min(len(text), idx + len(TERM) + CONTEXT_RADIUS)
        hits.append({
            "index": idx,
            "context_start": lo,
            "context_end": hi,
            "context": text[lo:hi],
        })
        pos = idx + len(TERM)

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S50",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "metadata_http": hs,
        "metadata_url": mu,
        "attachment": att,
        "download_http": ds,
        "download_url": du,
        "download_bytes": len(raw),
        "extract_ok": ext.get("ok"),
        "extract_error": ext.get("error"),
        "text_chars": len(text),
        "term": TERM,
        "term_count": len(hits),
        "contexts": hits,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "metadata HTTP 200": hs == 200,
        "attachment recovered": bool(att),
        "download HTTP 200": ds == 200,
        "extract ok": bool(ext.get("ok")),
        "term found exactly once": len(hits) == 1,
        "state mutation disabled": not output["state_mutation_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "HWP5 parser restored": hwp5.parse_records_text is original_parser,
        "file limit restored": hwp5.MAX_FILE_BYTES == original_file_limit,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Metadata HTTP:", hs)
    print("Attachment:", att)
    print("Download HTTP:", ds)
    print("Extract OK:", ext.get("ok"))
    print("Text chars:", len(text))
    print("Term count:", len(hits))
    for i, hit in enumerate(hits, 1):
        print("\n" + "=" * 80)
        print(f"CONTEXT {i} | INDEX {hit['index']}")
        print(hit["context"])
    print("\nOutput:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1606 related-candidate context probe failed")


if __name__ == "__main__":
    main()
