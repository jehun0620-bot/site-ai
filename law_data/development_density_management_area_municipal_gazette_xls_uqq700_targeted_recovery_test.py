# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S5
Targeted XLS recovery for pstSn 28847 / Gazette 699.

The prior attachment forensics established that this row has exactly one XLS
attachment (`백현2천-편입용지조서.xls`, fileNo 28302) and no HWP attachment.

This stage:
- downloads only that one XLS file from the official Seongnam file endpoint
- parses legacy XLS with xlrd if available
- searches extracted cell text for UQQ700 direct/high-signal related terms
- writes a forensic result only
- does not promote TRUE/FALSE and does not treat no-match as negative evidence

No OCR, no PDF fallback, no bulk traversal.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any, Dict, List

import requests

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_xls_uqq700_targeted_recovery.json"

PST = "28847"
FILE_NO = "28302"
BBS_CRT_SN = "16002"
MAX_FILE_BYTES = 8 * 1024 * 1024

DIRECT = ("개발밀도관리구역", "개발밀도 관리구역")
HIGH_SIGNAL_RELATED = ("개발밀도", "밀도관리")
LOW_SIGNAL_RELATED = ("관리구역",)


def download_xls(session: requests.Session) -> tuple[int, str, bytes]:
    url = "https://www.seongnam.go.kr/bbs010308/getFile"
    params = {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST, "fileNo": FILE_NO}
    with session.get(url, params=params, timeout=30, stream=True) as resp:
        final_url = resp.url
        status = resp.status_code
        resp.raise_for_status()
        chunks: List[bytes] = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise ValueError("xls file too large")
            chunks.append(chunk)
        return status, final_url, b"".join(chunks)


def extract_xls_text(raw: bytes) -> Dict[str, Any]:
    try:
        import xlrd  # type: ignore
    except Exception as exc:
        return {
            "parser": "UNAVAILABLE",
            "error": f"xlrd unavailable: {exc!r}",
            "sheet_count": None,
            "cell_count": None,
            "text": "",
            "sheets": [],
        }

    try:
        book = xlrd.open_workbook(file_contents=raw, on_demand=True)
    except Exception as exc:
        return {
            "parser": "XLRD",
            "error": repr(exc),
            "sheet_count": None,
            "cell_count": None,
            "text": "",
            "sheets": [],
        }

    texts: List[str] = []
    sheets: List[Dict[str, Any]] = []
    cell_count = 0
    for sheet in book.sheets():
        sheet_values: List[str] = []
        for r in range(sheet.nrows):
            for c in range(sheet.ncols):
                v = sheet.cell_value(r, c)
                if v is None:
                    continue
                s = str(v).strip()
                if not s:
                    continue
                cell_count += 1
                sheet_values.append(s)
                texts.append(s)
        sheets.append({
            "name": sheet.name,
            "nrows": sheet.nrows,
            "ncols": sheet.ncols,
            "nonempty_cells": len(sheet_values),
            "sample": sheet_values[:30],
        })

    return {
        "parser": "XLRD",
        "error": "",
        "sheet_count": len(sheets),
        "cell_count": cell_count,
        "text": "\n".join(texts),
        "sheets": sheets,
    }


def counts(text: str, terms: tuple[str, ...]) -> Dict[str, int]:
    return {term: text.count(term) for term in terms}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE XLS UQQ700 TARGETED RECOVERY")
    print("=" * 60)
    print("Target pstSn:", PST)
    print("FileNo:", FILE_NO)
    print("Max file bytes:", MAX_FILE_BYTES)
    print("OCR: DISABLED")
    print("PDF fallback: DISABLED")
    print()

    session = requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    status, url, raw = download_xls(session)
    extracted = extract_xls_text(raw)
    text = extracted.get("text") or ""

    direct_matches = counts(text, DIRECT)
    high_matches = counts(text, HIGH_SIGNAL_RELATED)
    low_matches = counts(text, LOW_SIGNAL_RELATED)

    if any(direct_matches.values()):
        result_status = "DIRECT_CANDIDATE"
    elif any(high_matches.values()):
        result_status = "RELATED_CANDIDATE"
    elif extracted.get("error"):
        result_status = "EXTRACTION_UNKNOWN"
    else:
        result_status = "NO_TERM_IN_EXTRACTED_SAMPLE"

    result = {
        "pstSn": PST,
        "fileNo": FILE_NO,
        "file_name": "백현2천-편입용지조서.xls",
        "download_http": status,
        "download_url": url,
        "download_bytes": len(raw),
        "parser": extracted.get("parser"),
        "parser_error": extracted.get("error"),
        "sheet_count": extracted.get("sheet_count"),
        "cell_count": extracted.get("cell_count"),
        "sheets": extracted.get("sheets"),
        "text_chars": len(text),
        "direct_matches": direct_matches,
        "high_signal_related_matches": high_matches,
        "low_signal_related_matches": low_matches,
        "status": result_status,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Download HTTP:", status)
    print("Download URL:", url)
    print("Download bytes:", len(raw))
    print("Parser:", result["parser"])
    print("Parser error:", result["parser_error"])
    print("Sheet count:", result["sheet_count"])
    print("Cell count:", result["cell_count"])
    print("Text chars:", result["text_chars"])
    print("Direct matches:", direct_matches)
    print("High-signal related matches:", high_matches)
    print("Low-signal related matches:", low_matches)
    print("Status:", result_status)
    for s in result.get("sheets") or []:
        print("SHEET:", s)
    print("Output:", OUT)

    unsafe = any([
        result["verified_positive"],
        result["runtime_registration_allowed"],
        result["site_positive_allowed"],
        result["site_negative_allowed"],
        result["final_positive_promotion_allowed"],
    ])
    vals = {
        "official download host": hwp5.host(url) == "www.seongnam.go.kr",
        "download http 200": status == 200,
        "download bounded": len(raw) <= MAX_FILE_BYTES,
        "xls bytes present": len(raw) > 0,
        "generic related term cannot trigger alone": not (
            result_status == "RELATED_CANDIDATE" and not any(high_matches.values())
        ),
        "negative evidence disabled": not result["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("targeted XLS recovery validation failed")


if __name__ == "__main__":
    main()
