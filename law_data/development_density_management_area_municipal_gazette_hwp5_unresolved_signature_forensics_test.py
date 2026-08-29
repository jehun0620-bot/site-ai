# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-33-S1
Development Density Management Area
Municipal Gazette HWP5 Unresolved Signature Forensics

Purpose
-------
T-33 found seven .hwp attachments after the first HWP5 rows that were not OLE HWP5.
This stage re-downloads ONLY those cumulative unresolved files using the already-saved
attachment file numbers and classifies their binary signatures.

No text extraction, keyword search, OCR, archive traversal, or legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_unresolved_signature_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
DOWNLOAD_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/getFile"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
BBS_CRT_SN = "16002"
TIMEOUT = 30
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_REQUESTS = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"

HWP3_SIG = b"HWP Document File V3.00"
HWP5_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_SIG = b"PK\x03\x04"
PDF_SIG = b"%PDF-"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def classify(raw: bytes) -> str:
    if raw.startswith(HWP3_SIG):
        return "HWP3"
    if raw.startswith(HWP5_SIG):
        return "HWP5_OLE"
    if raw.startswith(ZIP_SIG):
        return "ZIP_BASED"
    if raw.startswith(PDF_SIG):
        return "PDF"
    return "UNKNOWN_BINARY"


def ascii_preview(raw: bytes, limit: int = 96) -> str:
    head = raw[:limit]
    return "".join(chr(b) if 32 <= b <= 126 else "." for b in head)


def download(session: requests.Session, pst: str, file_no: str) -> Dict[str, Any]:
    detail = urljoin(BASE_DETAIL, pst)
    params = {"bbsCrtSn": BBS_CRT_SN, "pstSn": pst, "fileNo": file_no}
    result: Dict[str, Any] = {"http_status": None, "final_url": "", "bytes": 0, "prefix_hex": "", "ascii_preview": "", "classification": "UNKNOWN", "error": ""}
    try:
        with session.get(DOWNLOAD_ENDPOINT, params=params, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code
            result["final_url"] = str(r.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in r.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_FILE_BYTES:
                    raise ValueError("file exceeds bounded size cap")
                chunks.append(chunk)
            raw = b"".join(chunks)
            result["bytes"] = len(raw)
            result["prefix_hex"] = raw[:96].hex(" ")
            result["ascii_preview"] = ascii_preview(raw)
            result["classification"] = classify(raw)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP5 UNRESOLVED SIGNATURE FORENSICS")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Text extraction: DISABLED")
    print("Keyword search: DISABLED")
    print("OCR: DISABLED")
    print()

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    unresolved = [r for r in (state.get("results") or []) if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    if not unresolved:
        raise AssertionError("no cumulative unresolved rows available")
    if len(unresolved) > MAX_REQUESTS:
        raise AssertionError(f"unresolved count {len(unresolved)} exceeds bounded request cap {MAX_REQUESTS}")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    rows = []
    request_count = 0
    for prior in unresolved:
        att = prior.get("attachment") or {}
        pst = norm(prior.get("pstSn"))
        file_no = norm(att.get("file_no"))
        if not pst or not file_no:
            rows.append({"gazette_number": prior.get("gazette_number"), "date": norm(prior.get("date")), "pstSn": pst, "file_no": file_no, "file_name": norm(att.get("file_name")), "classification": "MISSING_SAVED_ATTACHMENT_ID", "error": "saved attachment id unavailable"})
            continue
        dl = download(session, pst, file_no)
        request_count += 1
        rec = {
            "gazette_number": prior.get("gazette_number"),
            "date": norm(prior.get("date")),
            "pstSn": pst,
            "file_no": file_no,
            "file_name": norm(att.get("file_name")),
            **dl,
        }
        rows.append(rec)
        print("ROW:", {k: rec.get(k) for k in ["gazette_number", "date", "pstSn", "file_name", "bytes", "classification", "ascii_preview", "error"]})

    counts: Dict[str, int] = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1

    if counts.get("HWP3") == len(rows):
        classification = "UNRESOLVED_ROWS_ALL_HWP3_AFTER_HWP5_APPEARANCE"
    elif counts.get("HWP3", 0) > 0 and counts.get("HWP5_OLE", 0) > 0:
        classification = "HWP3_HWP5_INTERLEAVING_CONFIRMED"
    elif counts.get("UNKNOWN_BINARY", 0) > 0:
        classification = "NON_OLE_HWP_VARIANTS_REQUIRE_FURTHER_FORENSICS"
    else:
        classification = "UNRESOLVED_SIGNATURES_CLASSIFIED"

    output = {
        "step": "STEP 17-21-C-16-8-T-33-S1 Municipal Gazette HWP5 Unresolved Signature Forensics",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "input": str(STATE),
        "network_request_count": request_count,
        "max_request_count": MAX_REQUESTS,
        "unresolved_input_count": len(unresolved),
        "signature_counts": counts,
        "rows": rows,
        "classification": classification,
        "text_extraction_executed": False,
        "body_keyword_search_executed": False,
        "ocr_executed": False,
        "bulk_archive_traversal_executed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "semantic_note": "Binary signature routing only. Format interleaving or HWP3 recurrence does not imply any UQQ700 legal fact.",
        "resolution": "MUNICIPAL_GAZETTE_HWP5_UNRESOLVED_SIGNATURE_FORENSICS_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("SUMMARY")
    print("Unresolved input count:", len(unresolved))
    print("Network request count:", request_count)
    print("Signature counts:", counts)
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([output["text_extraction_executed"], output["body_keyword_search_executed"], output["ocr_executed"], output["bulk_archive_traversal_executed"], output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"], output["final_positive_promotion_allowed"]])
    vals = {
        "cumulative HWP5 state exists": STATE.exists(),
        "unresolved rows bounded": 0 < len(unresolved) <= MAX_REQUESTS,
        "request budget respected": request_count <= MAX_REQUESTS,
        "all downloads HTTP 200": all(r.get("http_status") == 200 for r in rows if r.get("file_no")),
        "all response hosts official": all(host(r.get("final_url", "")) == "www.seongnam.go.kr" for r in rows if r.get("file_no")),
        "all downloaded rows classified": all(r.get("classification") not in {"UNKNOWN", ""} for r in rows),
        "text extraction disabled": not output["text_extraction_executed"],
        "keyword search disabled": not output["body_keyword_search_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("unresolved HWP signature forensics failed")


if __name__ == "__main__":
    main()
