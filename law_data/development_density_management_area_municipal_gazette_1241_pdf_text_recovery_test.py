# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S42
Gazette 1241 / pstSn 29416 PDF-only attachment text recovery probe.

Exact official attachment:
- fileNo 28894
- 제1241호.4.14(월)발행분.pdf

Policy:
- exact one attachment body download only;
- PDF text-layer extraction only (OCR disabled);
- no cumulative state mutation;
- no negative-evidence inference;
- no runtime/SITE/legal promotion.
"""
from __future__ import annotations

import io
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
S41 = OUT_DIR / "development_density_management_area_municipal_gazette_1241_attachment_forensic.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1241_pdf_text_recovery.json"

PSTSN = "29416"
GAZETTE_NUMBER = 1241
DATE = "2014-04-14"
FILE_NO = "28894"
EXPECTED_NAME = "제1241호.4.14(월)발행분.pdf"
MAX_PDF_BYTES = 16 * 1024 * 1024
MAX_PAGES = 500
CONTEXT_CHARS = 700


def contexts(text: str) -> List[Dict[str, Any]]:
    terms = list(dict.fromkeys(list(hwp5.DIRECT) + list(base.HIGH_SIGNAL_RELATED)))
    out: List[Dict[str, Any]] = []
    for term in terms:
        for m in re.finditer(re.escape(term), text):
            a = max(0, m.start() - CONTEXT_CHARS)
            b = min(len(text), m.end() + CONTEXT_CHARS)
            out.append({
                "term": term,
                "offset": m.start(),
                "context": re.sub(r"\s+", " ", text[a:b]).strip(),
            })
            if len(out) >= 12:
                return out
    return out


def load_pdf_reader(raw: bytes):
    errors = []
    try:
        from pypdf import PdfReader  # type: ignore
        return PdfReader(io.BytesIO(raw)), "pypdf", errors
    except Exception as exc:
        errors.append("pypdf=" + repr(exc))
    try:
        from PyPDF2 import PdfReader  # type: ignore
        return PdfReader(io.BytesIO(raw)), "PyPDF2", errors
    except Exception as exc:
        errors.append("PyPDF2=" + repr(exc))
    return None, "", errors


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1241 PDF TEXT RECOVERY")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("Exact fileNo:", FILE_NO)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not S41.exists():
        raise FileNotFoundError(S41)

    s41 = json.loads(S41.read_text(encoding="utf-8"))
    attachments = s41.get("attachments") or []
    exact = [x for x in attachments if str(x.get("file_no") or "") == FILE_NO]
    if len(exact) != 1:
        raise AssertionError(f"S41 exact attachment mismatch: {len(exact)}")
    if str(exact[0].get("file_name") or "") != EXPECTED_NAME:
        raise AssertionError("S41 filename mismatch")
    if str(exact[0].get("file_ext") or "").lower() != "pdf":
        raise AssertionError("S41 attachment is not PDF")

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    original_limit = hwp5.MAX_FILE_BYTES
    hwp5.MAX_FILE_BYTES = MAX_PDF_BYTES
    try:
        ds, du, raw = hwp5.get_file(session, PSTSN, FILE_NO)
    finally:
        hwp5.MAX_FILE_BYTES = original_limit

    pdf_signature = raw.startswith(b"%PDF-")
    reader = None
    parser = ""
    parser_errors: List[str] = []
    page_count = 0
    extracted_pages = 0
    page_errors: List[str] = []
    text = ""

    if pdf_signature:
        reader, parser, parser_errors = load_pdf_reader(raw)
        if reader is not None:
            page_count = len(reader.pages)
            if page_count > MAX_PAGES:
                raise ValueError(f"PDF page safety limit exceeded: {page_count}")
            parts = []
            for i, page in enumerate(reader.pages):
                try:
                    t = page.extract_text() or ""
                    if t:
                        parts.append(t)
                    extracted_pages += 1
                except Exception as exc:
                    page_errors.append(f"page {i + 1}: {repr(exc)}")
            text = "\n".join(parts)

    direct = {t: text.count(t) for t in hwp5.DIRECT}
    high = {t: text.count(t) for t in base.HIGH_SIGNAL_RELATED}
    term_contexts = contexts(text)

    if not pdf_signature:
        status = "EXTRACTION_OR_REQUEST_UNKNOWN"
        error = "downloaded attachment does not have PDF signature"
    elif reader is None:
        status = "PDF_TEXT_PARSER_UNAVAILABLE"
        error = "; ".join(parser_errors)
    elif page_errors and not text:
        status = "EXTRACTION_OR_REQUEST_UNKNOWN"
        error = "; ".join(page_errors[:10])
    elif not text.strip():
        status = "PDF_TEXT_LAYER_EMPTY"
        error = "PDF downloaded but no text layer recovered; OCR remains disabled"
    elif any(direct.values()):
        status = "DIRECT_CANDIDATE"
        error = ""
    elif any(high.values()):
        status = "RELATED_CANDIDATE"
        error = ""
    else:
        status = "NO_TERM_IN_EXTRACTED_PDF_TEXT"
        error = ""

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S42",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "attachment": exact[0],
        "download_http": ds,
        "download_url": du,
        "download_bytes": len(raw),
        "pdf_signature": pdf_signature,
        "pdf_parser": parser,
        "parser_errors": parser_errors,
        "page_count": page_count,
        "extracted_pages": extracted_pages,
        "page_errors": page_errors,
        "text_chars": len(text),
        "direct_matches": direct,
        "high_signal_related_matches": high,
        "contexts": term_contexts,
        "status": status,
        "error": error,
        "ocr_allowed": False,
        "state_mutation_allowed": False,
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
        "S41 input exists": S41.exists(),
        "exact PDF metadata matched": len(exact) == 1 and exact[0].get("file_ext") == "pdf",
        "download HTTP 200": ds == 200,
        "download size bounded": 0 < len(raw) <= MAX_PDF_BYTES,
        "PDF signature valid": pdf_signature,
        "file limit restored": hwp5.MAX_FILE_BYTES == original_limit,
        "OCR disabled": not output["ocr_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Download HTTP:", ds)
    print("Download bytes:", len(raw))
    print("PDF signature:", pdf_signature)
    print("PDF parser:", parser or "UNAVAILABLE")
    print("Page count:", page_count)
    print("Extracted pages:", extracted_pages)
    print("Text chars:", len(text))
    print("Direct matches:", direct)
    print("High-signal related matches:", high)
    print("Status:", status)
    print("Error:", error)
    for i, c in enumerate(term_contexts, 1):
        print(f"CONTEXT {i} [{c['term']}]: {c['context']}")
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1241 PDF recovery validation failed")


if __name__ == "__main__":
    main()
