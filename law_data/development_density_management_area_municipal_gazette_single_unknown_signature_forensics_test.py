# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S9
Inspect the single unresolved UNKNOWN-signature row left by the latest 50-row
municipal-gazette dynamic-HWP batch.

This stage reads the shared cumulative state, requires exactly one unresolved
row, then re-fetches only that row's attachment metadata and at most one file.
It prints attachment metadata plus a bounded binary signature preview so the
actual format can be routed safely in the next stage.

Safety:
- no text extraction
- no OCR/PDF/XLS parsing
- no state mutation
- max 2 network requests
- no legal promotion and no negative evidence
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_single_unknown_signature_forensics.json"
MAX_FILE_BYTES = 32 * 1024 * 1024


def flatten_attachments(obj: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x.keys()}
            if any(k in keys for k in {"fileno", "file_no", "atchfileno", "orginlfilenm", "strefilenm", "fileextsn"}):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return found


def summarize_attachment(item: Dict[str, Any]) -> Dict[str, Any]:
    def first(*names: str):
        for n in names:
            if item.get(n) not in (None, ""):
                return item.get(n)
        return None
    return {
        "fileNo": first("fileNo", "file_no", "atchFileNo", "atchFileSn"),
        "orginlFileNm": first("orginlFileNm", "orignlFileNm", "originalFileName"),
        "streFileNm": first("streFileNm"),
        "fileExtsn": first("fileExtsn", "fileExt", "extension"),
        "fileSize": first("fileSize", "fileMg", "size"),
    }


def classify(raw: bytes) -> str:
    if raw.startswith(b"HWP Document File V3.00"):
        return "HWP3"
    if raw.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "OLE_CFB"
    if raw.startswith(b"PK\x03\x04"):
        return "ZIP_CONTAINER"
    if raw.startswith(b"%PDF-"):
        return "PDF"
    if raw.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1"):
        return "OLE_CFB"
    if raw.startswith(b"\x89PNG\r\n\x1a\n"):
        return "PNG"
    if raw.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    return "UNKNOWN"


def get_file_bounded(session, pst: str, file_no: str):
    url = hwp5.DOWNLOAD_ENDPOINT
    params = {"bbsCrtSn": hwp5.BBS_CRT_SN, "pstSn": pst, "fileNo": file_no}
    with session.get(url, params=params, timeout=hwp5.TIMEOUT, stream=True) as resp:
        final_url = resp.url
        status = resp.status_code
        resp.raise_for_status()
        chunks = []
        total = 0
        for chunk in resp.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > MAX_FILE_BYTES:
                raise ValueError("file too large")
            chunks.append(chunk)
        return status, final_url, b"".join(chunks)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SINGLE UNKNOWN ATTACHMENT SIGNATURE FORENSICS")
    print("=" * 60)
    print("State mutation: DISABLED")
    print("Text extraction: DISABLED")
    print("Max file bytes:", MAX_FILE_BYTES)
    print()

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    unresolved = [r for r in (state.get("results") or []) if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    if len(unresolved) != 1:
        raise AssertionError(f"expected exactly one unresolved row, got {len(unresolved)}")

    src = unresolved[0]
    pst = hwp5.norm(src.get("pstSn"))
    print("State unresolved row:", {k: src.get(k) for k in ["gazette_number", "date", "pstSn", "signature_class", "parser_used", "error"]})

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0

    hs, mu, obj = hwp5.get_json(session, pst)
    req += 1
    attachments = [summarize_attachment(x) for x in flatten_attachments(obj)]
    print("Metadata HTTP:", hs)
    print("Metadata URL:", mu)
    print("Attachment count:", len(attachments))
    for i, a in enumerate(attachments, 1):
        print(f"ATTACHMENT {i}:", a)

    selected = None
    prior_att = src.get("attachment") or {}
    prior_file_no = str(prior_att.get("file_no") or prior_att.get("fileNo") or "")
    if prior_file_no:
        selected = next((a for a in attachments if str(a.get("fileNo") or "") == prior_file_no), None)
    if selected is None and len(attachments) == 1:
        selected = attachments[0]

    file_result: Dict[str, Any] = {}
    if selected and selected.get("fileNo") is not None:
        ds, du, raw = get_file_bounded(session, pst, str(selected["fileNo"]))
        req += 1
        file_result = {
            "download_http": ds,
            "download_url": du,
            "download_bytes": len(raw),
            "signature_class": classify(raw),
            "head_hex": raw[:64].hex(),
            "head_ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in raw[:64]),
        }
        print("Selected attachment:", selected)
        print("Download HTTP:", ds)
        print("Download URL:", du)
        print("Download bytes:", len(raw))
        print("Signature class:", file_result["signature_class"])
        print("Head hex:", file_result["head_hex"])
        print("Head ASCII:", file_result["head_ascii"])
    else:
        print("Selected attachment: NONE")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S9",
        "state_unresolved": src,
        "metadata_http": hs,
        "metadata_url": mu,
        "attachments": attachments,
        "selected_attachment": selected,
        "file_result": file_result,
        "network_request_count": req,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any([
        output["verified_positive"], output["runtime_registration_allowed"],
        output["site_positive_allowed"], output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "exactly one unresolved": len(unresolved) == 1,
        "metadata http 200": hs == 200,
        "metadata host official": hwp5.host(mu) == "www.seongnam.go.kr",
        "request budget respected": req <= 2,
        "download host official": not file_result or hwp5.host(file_result.get("download_url", "")) == "www.seongnam.go.kr",
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("single unknown signature forensics failed")


if __name__ == "__main__":
    main()
