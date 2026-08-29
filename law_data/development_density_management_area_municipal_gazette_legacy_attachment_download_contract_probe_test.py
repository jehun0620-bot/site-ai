# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S12
Bounded legacy attachment download-contract probe for Gazette 938 / pstSn 29098.

The metadata endpoint returns the attachment, but the modern canonical getFile
serialization returns HTTP 404. This probe tests a small fixed family of
plausible official Seongnam serializations only. It never extracts document
text, mutates cumulative state, or promotes legal status.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_attachment_download_contract_probe.json"

HOST = "www.seongnam.go.kr"
BASE = "https://www.seongnam.go.kr"
PST_SN = "29098"
FILE_NO = "28559"
BBS_CRT_SN = "16002"
MAX_REQUESTS = 10
MAX_BODY_BYTES = 2 * 1024 * 1024
TIMEOUT = 20


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
    if raw.startswith(b"<!DOCTYPE") or raw.lstrip().startswith(b"<html"):
        return "HTML"
    return "UNKNOWN"


def bounded_body(resp: requests.Response) -> bytes:
    raw = resp.content
    return raw[:MAX_BODY_BYTES]


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY GAZETTE ATTACHMENT DOWNLOAD CONTRACT PROBE")
    print("=" * 60)
    print("Target pstSn:", PST_SN)
    print("Target fileNo:", FILE_NO)
    print("Text extraction: DISABLED")
    print("State mutation: DISABLED")
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Referer": f"{BASE}/bbs010308/{PST_SN}",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    probes = [
        ("GET_CANONICAL", "GET", f"{BASE}/bbs010308/getFile", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
        ("POST_CANONICAL", "POST", f"{BASE}/bbs010308/getFile", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
        ("GET_NO_BBS", "GET", f"{BASE}/bbs010308/getFile", {"pstSn": PST_SN, "fileNo": FILE_NO}),
        ("POST_NO_BBS", "POST", f"{BASE}/bbs010308/getFile", {"pstSn": PST_SN, "fileNo": FILE_NO}),
        ("GET_ATCH_FILE_NO", "GET", f"{BASE}/bbs010308/getFile", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "atchFileNo": FILE_NO}),
        ("GET_FILE_SN", "GET", f"{BASE}/bbs010308/getFile", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileSn": FILE_NO}),
        ("GET_TRAILING_SLASH", "GET", f"{BASE}/bbs010308/getFile/", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
        ("GET_BOARD_ROOT", "GET", f"{BASE}/getFile", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
        ("GET_FILE_DOWNLOAD", "GET", f"{BASE}/bbs010308/fileDownload", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
        ("GET_DOWNLOAD", "GET", f"{BASE}/bbs010308/download", {"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}),
    ]

    results = []
    for name, method, url, params in probes[:MAX_REQUESTS]:
        try:
            if method == "GET":
                resp = session.get(url, params=params, timeout=TIMEOUT, allow_redirects=True)
            else:
                resp = session.post(url, data=params, timeout=TIMEOUT, allow_redirects=True)
            raw = bounded_body(resp)
            rec = {
                "name": name,
                "method": method,
                "status": resp.status_code,
                "url": resp.url,
                "host": host(resp.url),
                "content_type": resp.headers.get("Content-Type", ""),
                "content_disposition": resp.headers.get("Content-Disposition", ""),
                "content_length_header": resp.headers.get("Content-Length", ""),
                "body_bytes_observed": len(raw),
                "signature_class": classify(raw),
                "head_hex": raw[:32].hex(),
            }
        except Exception as exc:
            rec = {"name": name, "method": method, "url": url, "error": repr(exc)}
        results.append(rec)
        print("PROBE:", rec)

    successful_binary = [r for r in results if r.get("status") == 200 and r.get("signature_class") in {"HWP3", "OLE_CFB", "ZIP_CONTAINER", "PDF"}]
    output = {
        "step": "STEP 17-21-C-16-8-T-34-S12",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO},
        "results": results,
        "successful_binary_contracts": successful_binary,
        "network_request_count": len(results),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(results) <= MAX_REQUESTS,
        "all resolved hosts official": all((not r.get("host")) or r.get("host") == HOST for r in results),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("SUMMARY")
    print("Successful binary contracts:", len(successful_binary))
    for r in successful_binary:
        print("SUCCESS:", r)
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy attachment download contract probe validation failed")


if __name__ == "__main__":
    main()
