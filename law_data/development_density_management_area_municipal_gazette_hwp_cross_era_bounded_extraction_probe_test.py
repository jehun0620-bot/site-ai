# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-7
Development Density Management Area
Municipal Gazette Cross-Era Bounded HWP Extraction Probe

Downloads exactly TWO HWP attachments selected by T-28-S1-6 (EARLIEST and MIDPOINT)
and performs bounded format/extraction diagnostics only.

Safety:
- exactly 2 file downloads maximum
- no archive-wide traversal
- no OCR
- no external converter invocation
- no legal/SITE promotion
- extraction failure or term absence => UNKNOWN, never FALSE
"""
from __future__ import annotations

import json
import re
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlencode, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

T28S16 = OUT_DIR / "development_density_management_area_municipal_gazette_cross_era_attachment_format_sample.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_cross_era_bounded_extraction_probe.json"
SAMPLE_DIR = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
DOWNLOAD_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/getFile"
BBS_CRT_SN = "16002"
TIMEOUT = 30
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_DOWNLOADS = 2
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
DIRECT = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED = ["개발밀도", "밀도관리", "관리구역"]


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def gov(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def select_hwp_samples(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for role in ("EARLIEST", "MIDPOINT"):
        sample = next((x for x in doc.get("samples", []) if x.get("role") == role), None)
        if not sample:
            raise AssertionError(f"missing sample role {role}")
        hwp = next((a for a in sample.get("attachments", []) if norm(a.get("file_ext")).lower() == "hwp"), None)
        if not hwp:
            raise AssertionError(f"no HWP attachment for {role}")
        out.append({
            "role": role,
            "gazette_number": sample.get("gazette_number"),
            "date": norm(sample.get("date")),
            "pstSn": norm(sample.get("pstSn")),
            "file_no": norm(hwp.get("file_no")),
            "file_name": norm(hwp.get("file_name")),
            "metadata_file_size": hwp.get("file_size"),
        })
    if len({(x["pstSn"], x["file_no"]) for x in out}) != 2:
        raise AssertionError("HWP samples are not unique")
    return out


def download(session: requests.Session, sample: Dict[str, Any]) -> Dict[str, Any]:
    params = {"bbsCrtSn": BBS_CRT_SN, "pstSn": sample["pstSn"], "fileNo": sample["file_no"]}
    result: Dict[str, Any] = {"http_status": None, "final_url": "", "bytes": 0, "content_type": "", "error": "", "data": b""}
    detail = f"https://www.seongnam.go.kr/bbs010308/{sample['pstSn']}"
    try:
        with session.get(DOWNLOAD_ENDPOINT, params=params, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code
            result["final_url"] = str(r.url)
            result["content_type"] = norm(r.headers.get("Content-Type"))
            chunks: List[bytes] = []
            total = 0
            for c in r.iter_content(128 * 1024):
                if not c:
                    continue
                total += len(c)
                if total > MAX_FILE_BYTES:
                    raise ValueError("file exceeds bounded size")
                chunks.append(c)
            data = b"".join(chunks)
            result["bytes"] = len(data)
            result["data"] = data
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def ole_signature(data: bytes) -> bool:
    return data[:8] == bytes.fromhex("D0CF11E0A1B11AE1")


def ascii_strings(data: bytes, min_len: int = 4) -> str:
    return "\n".join(m.group(0).decode("latin1", errors="ignore") for m in re.finditer(rb"[ -~]{%d,}" % min_len, data))


def utf16le_strings(data: bytes, min_chars: int = 4) -> str:
    # Conservative scan for printable Hangul/ASCII UTF-16LE runs; diagnostic only.
    pieces: List[str] = []
    buf: List[str] = []
    for i in range(0, len(data) - 1, 2):
        code = data[i] | (data[i + 1] << 8)
        ok = (0x20 <= code <= 0x7E) or (0xAC00 <= code <= 0xD7A3) or code in (0x0009, 0x000A, 0x000D)
        if ok:
            buf.append(chr(code))
        else:
            if len(buf) >= min_chars:
                pieces.append("".join(buf))
            buf = []
    if len(buf) >= min_chars:
        pieces.append("".join(buf))
    return "\n".join(pieces)


def optional_olefile_probe(path: Path) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"available": False, "opened": False, "streams": [], "error": ""}
    try:
        import olefile  # type: ignore
        rec["available"] = True
        ole = olefile.OleFileIO(str(path))
        rec["opened"] = True
        rec["streams"] = ["/".join(x) for x in ole.listdir()][:200]
        ole.close()
    except Exception as exc:
        rec["error"] = repr(exc)
    return rec


def count_terms(text: str) -> Dict[str, Dict[str, int]]:
    return {
        "direct": {t: text.count(t) for t in DIRECT},
        "related": {t: text.count(t) for t in RELATED},
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE CROSS-ERA BOUNDED HWP EXTRACTION PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Maximum file downloads:", MAX_DOWNLOADS)
    print("OCR: DISABLED")
    print("External converter: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T28S16.exists():
        raise FileNotFoundError(T28S16)
    src = json.loads(T28S16.read_text(encoding="utf-8"))
    samples = select_hwp_samples(src)

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results: List[Dict[str, Any]] = []
    request_count = 0

    for s in samples:
        r = download(session, s)
        request_count += 1
        data = r.pop("data")
        safe_name = f"{s['role'].lower()}_{s['gazette_number']}_{s['pstSn']}_{s['file_no']}.hwp"
        path = SAMPLE_DIR / safe_name
        if r.get("http_status") == 200 and data:
            path.write_bytes(data)

        ascii_text = ascii_strings(data) if data else ""
        utf16_text = utf16le_strings(data) if data else ""
        combined = ascii_text + "\n" + utf16_text
        ole_probe = optional_olefile_probe(path) if path.exists() else {"available": False, "opened": False, "streams": [], "error": "sample not persisted"}

        rec = {
            **s,
            "request": r,
            "persisted_path": str(path) if path.exists() else "",
            "ole_signature": ole_signature(data),
            "prefix_hex": " ".join(f"{b:02x}" for b in data[:32]),
            "ascii_string_chars": len(ascii_text),
            "utf16le_string_chars": len(utf16_text),
            "hangul_chars_in_diagnostic_strings": len(re.findall(r"[가-힣]", combined)),
            "diagnostic_term_matches": count_terms(combined),
            "diagnostic_preview": combined[:1200],
            "olefile_probe": ole_probe,
        }
        results.append(rec)

    all_http = all(x["request"]["http_status"] == 200 for x in results)
    all_official = all(gov(host(x["request"]["final_url"])) and host(x["request"]["final_url"]) == host(DOWNLOAD_ENDPOINT) for x in results)
    all_ole = all(x["ole_signature"] for x in results)
    any_olefile_open = any(x["olefile_probe"].get("opened") for x in results)

    if all_ole and any_olefile_open:
        classification = "CROSS_ERA_HWP_OLE_CONTAINER_CONFIRMED_STREAM_ENUMERATION_AVAILABLE"
    elif all_ole:
        classification = "CROSS_ERA_HWP_OLE_CONTAINER_CONFIRMED_NEEDS_STREAM_PARSER"
    else:
        classification = "CROSS_ERA_HWP_CONTAINER_NOT_UNIFORMLY_CONFIRMED"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-7 Municipal Gazette Cross-Era Bounded HWP Extraction Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "input": str(T28S16),
        "method": {
            "sample_roles": ["EARLIEST", "MIDPOINT"],
            "max_downloads": MAX_DOWNLOADS,
            "ocr_enabled": False,
            "external_converter_enabled": False,
            "bulk_archive_traversal_enabled": False,
            "diagnostic_string_scan_only": True,
        },
        "summary": {
            "request_count": request_count,
            "sample_count": len(results),
            "http_200_count": sum(1 for x in results if x["request"]["http_status"] == 200),
            "ole_signature_count": sum(1 for x in results if x["ole_signature"]),
            "olefile_available_count": sum(1 for x in results if x["olefile_probe"].get("available")),
            "olefile_opened_count": sum(1 for x in results if x["olefile_probe"].get("opened")),
        },
        "samples": results,
        "classification": classification,
        "semantic_note": "This is format/extraction feasibility evidence only. Diagnostic string term absence is not document-level negative evidence and cannot produce UQQ700 FALSE.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_CROSS_ERA_BOUNDED_HWP_EXTRACTION_PROBE_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any([
        output["method"]["ocr_enabled"], output["method"]["external_converter_enabled"], output["method"]["bulk_archive_traversal_enabled"],
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ])
    vals = {
        "T-28-S1-6 input exists": T28S16.exists(),
        "exactly two unique HWP samples": len(results) == 2 and len({(x["pstSn"], x["file_no"]) for x in results}) == 2,
        "download budget respected": request_count == 2 and request_count <= MAX_DOWNLOADS,
        "all downloads HTTP 200": all_http,
        "all download hosts official and same host": all_official,
        "all samples persisted": all(bool(x["persisted_path"]) and Path(x["persisted_path"]).exists() for x in results),
        "OCR disabled": not output["method"]["ocr_enabled"],
        "external converter disabled": not output["method"]["external_converter_enabled"],
        "bulk archive traversal disabled": not output["method"]["bulk_archive_traversal_enabled"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    for x in results:
        print("-" * 60)
        print("Role:", x["role"])
        print("Gazette/Date:", x["gazette_number"], x["date"])
        print("pstSn/fileNo:", x["pstSn"], x["file_no"])
        print("File:", x["file_name"])
        print("HTTP:", x["request"]["http_status"])
        print("Bytes:", x["request"]["bytes"])
        print("Content-Type:", x["request"]["content_type"])
        print("OLE signature:", x["ole_signature"])
        print("Prefix hex:", x["prefix_hex"])
        print("olefile available/opened:", x["olefile_probe"].get("available"), x["olefile_probe"].get("opened"))
        print("OLE streams:", x["olefile_probe"].get("streams", [])[:30])
        print("Diagnostic string chars ASCII/UTF16:", x["ascii_string_chars"], x["utf16le_string_chars"])
        print("Hangul diagnostic chars:", x["hangul_chars_in_diagnostic_strings"])
        print("Direct/related matches:", x["diagnostic_term_matches"])
        print("Preview:", repr(x["diagnostic_preview"][:500]))

    print()
    print("SUMMARY")
    print("Request count:", request_count)
    print("OLE signature count:", output["summary"]["ole_signature_count"])
    print("olefile available count:", output["summary"]["olefile_available_count"])
    print("olefile opened count:", output["summary"]["olefile_opened_count"])
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("bounded cross-era HWP extraction probe failed")


if __name__ == "__main__":
    main()
