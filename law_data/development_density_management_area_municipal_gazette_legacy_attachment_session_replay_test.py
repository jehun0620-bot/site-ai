# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S14
Replay the exact browser order for Gazette 938 legacy attachment download:
1) open detail page
2) fetch attachment metadata
3) submit the documented GET /getFile form in the same session
4) bounded filePreview fallback only if download still fails

No cumulative state mutation and no legal promotion.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_attachment_session_replay.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
FILE_NO = "28559"
BBS_CRT_SN = "16002"
TIMEOUT = 20
MAX_REQUESTS = 4
MAX_BODY_BYTES = 4 * 1024 * 1024


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def classify(raw: bytes) -> str:
    if raw.startswith(b"HWP Document File V3.00"):
        return "HWP3"
    if raw.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "OLE_CFB"
    if raw.startswith(b"PK\x03\x04"):
        return "ZIP_CONTAINER"
    if raw.startswith(b"%PDF-"):
        return "PDF"
    if raw.startswith(b"\x89PNG"):
        return "PNG"
    if raw.startswith(b"\xff\xd8\xff"):
        return "JPEG"
    if raw.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        return "HTML"
    return "UNKNOWN"


def record_response(kind: str, resp: requests.Response) -> dict:
    raw = resp.content[:MAX_BODY_BYTES]
    return {
        "kind": kind,
        "status": resp.status_code,
        "url": resp.url,
        "host": host(resp.url),
        "content_type": resp.headers.get("Content-Type", ""),
        "content_disposition": resp.headers.get("Content-Disposition", ""),
        "content_length_header": resp.headers.get("Content-Length", ""),
        "body_bytes_observed": len(raw),
        "signature_class": classify(raw),
        "head_hex": raw[:32].hex(),
        "raw": raw,
    }


def printable(rec: dict) -> dict:
    return {k: v for k, v in rec.items() if k != "raw"}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY ATTACHMENT SESSION REPLAY")
    print("=" * 60)
    print("Target pstSn:", PST_SN)
    print("Target fileNo:", FILE_NO)
    print("State mutation: DISABLED")
    print("Text extraction: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    records = []

    # 1) Prime session exactly as browser detail view.
    detail = s.get(f"{BASE}/bbs010308/{PST_SN}", timeout=TIMEOUT)
    rec = record_response("detail_get", detail)
    records.append(rec)
    print("DETAIL:", printable(rec))
    print("Cookies after detail:", s.cookies.get_dict())

    # 2) Browser AJAX attachment metadata.
    meta = s.get(
        f"{BASE}/bbs010308/atchFileDetail",
        params={"pstSn": PST_SN},
        headers={"Referer": f"{BASE}/bbs010308/{PST_SN}", "X-Requested-With": "XMLHttpRequest"},
        timeout=TIMEOUT,
    )
    rec = record_response("metadata", meta)
    records.append(rec)
    print("METADATA:", printable(rec))
    print("Cookies after metadata:", s.cookies.get_dict())

    # 3) Exact documented form contract. No method attribute => GET.
    download = s.get(
        f"{BASE}/bbs010308/getFile",
        params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO},
        headers={"Referer": f"{BASE}/bbs010308/{PST_SN}"},
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    rec = record_response("session_primed_getFile", download)
    records.append(rec)
    print("GETFILE:", printable(rec))

    binary_classes = {"HWP3", "OLE_CFB", "ZIP_CONTAINER", "PDF", "PNG", "JPEG"}
    successful = rec.get("status") == 200 and rec.get("signature_class") in binary_classes and rec.get("body_bytes_observed", 0) > 0

    # 4) Only if the exact browser contract still fails, try documented preview form.
    if not successful and len(records) < MAX_REQUESTS:
        preview = s.get(
            f"{BASE}/bbs010308/filePreview",
            params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO},
            headers={"Referer": f"{BASE}/bbs010308/{PST_SN}"},
            timeout=TIMEOUT,
            allow_redirects=True,
        )
        rec2 = record_response("session_primed_filePreview", preview)
        records.append(rec2)
        print("PREVIEW:", printable(rec2))

    output_records = [printable(r) for r in records]
    successes = [r for r in output_records if r.get("status") == 200 and r.get("signature_class") in binary_classes and r.get("body_bytes_observed", 0) > 0]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S14",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO, "bbsCrtSn": BBS_CRT_SN},
        "records": output_records,
        "successful_binary_contracts": successes,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(r.get("host") == HOST for r in output_records),
        "detail available": output_records[0].get("status") == 200,
        "metadata available": output_records[1].get("status") == 200,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print()
    print("SUMMARY")
    print("Successful binary contracts:", len(successes))
    for x in successes:
        print("SUCCESS:", x)
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy attachment session replay validation failed")


if __name__ == "__main__":
    main()
