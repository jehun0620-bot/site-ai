# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-31
Development Density Management Area
Municipal Gazette HWP Internal Format Transition Bisection

Purpose
-------
Narrow the internal .hwp format transition from HWP3 single-stream binary to
HWP5 OLE/CFB before format-specific UQQ700 archive batches.

Known anchors from validated samples:
- 2003-04-14 Gazette 476: HWP3
- 2014-12-17 Gazette 1281: HWP5 OLE

Method
------
- use T-23 canonical registry
- bisect only between the two known anchor rows
- for each midpoint: one attachment-metadata request, then one bounded HWP download
- classify by file signature only:
    HWP3: b'HWP Document File V3.00'
    HWP5: OLE CFB signature D0 CF 11 E0 A1 B1 1A E1
- max 20 total network requests (<=10 probes)
- no text extraction, no body keyword search, no semantic/legal promotion
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_internal_format_transition_bisection.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"
DOWNLOAD_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/getFile"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
BBS_CRT_SN = "16002"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
TIMEOUT = 30
MAX_META_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 12 * 1024 * 1024
MAX_REQUESTS = 20
HWP3_SIG = b"HWP Document File V3.00"
HWP5_SIG = bytes.fromhex("D0CF11E0A1B11AE1")

LEFT_ANCHOR = {"date": "2003-04-14", "gazette_number": 476, "pstSn": "28627", "format": "HWP3"}
RIGHT_ANCHOR = {"date": "2014-12-17", "gazette_number": 1281, "pstSn": "29456", "format": "HWP5"}


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_date(v: Any) -> Optional[date]:
    try:
        y, m, d = [int(x) for x in norm(v).split("-")]
        return date(y, m, d)
    except Exception:
        return None


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def dated_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out = [r for r in rows if parse_date(r.get("date")) and norm(r.get("pstSn"))]
    out.sort(key=lambda r: (parse_date(r.get("date")), int(r.get("gazette_number") or 0), norm(r.get("pstSn"))))
    return out


def locate(rows: List[Dict[str, Any]], pst: str) -> int:
    for i, r in enumerate(rows):
        if norm(r.get("pstSn")) == pst:
            return i
    raise ValueError(f"anchor pstSn not found: {pst}")


def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x}
            if any(k in keys for k in ["fileno", "file_no", "atchfileno", "orginlfilenm", "orignlfilenm", "strefilenm"]):
                found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(obj)
    return found


def hwp_attachment(obj: Any) -> Optional[Dict[str, str]]:
    for item in flatten_items(obj):
        lower = {str(k).lower(): v for k, v in item.items()}
        file_no = lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
        name = lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm")
        explicit = norm(lower.get("fileextsn") or lower.get("fileext") or "").lower().lstrip(".")
        n = norm(name)
        ext = explicit or (re.search(r"\.([A-Za-z0-9]{1,10})$", n).group(1).lower() if re.search(r"\.([A-Za-z0-9]{1,10})$", n) else "")
        if ext == "hwp" and norm(file_no):
            return {"file_no": norm(file_no), "file_name": n}
    return None


def fetch_metadata(session: requests.Session, row: Dict[str, Any]) -> Dict[str, Any]:
    pst = norm(row.get("pstSn"))
    detail = urljoin(BASE_DETAIL, pst)
    result = {"http_status": None, "final_url": "", "json": None, "error": ""}
    try:
        with session.get(ATTACHMENT_ENDPOINT, params={"pstSn": pst}, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code
            result["final_url"] = str(r.url)
            chunks = []
            total = 0
            for chunk in r.iter_content(128 * 1024):
                if not chunk: continue
                total += len(chunk)
                if total > MAX_META_BYTES: raise ValueError("metadata response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            try:
                result["json"] = r.json()
            except Exception:
                result["json"] = json.loads(raw.decode(r.encoding or "utf-8", errors="replace"))
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def fetch_hwp(session: requests.Session, pst: str, file_no: str) -> Dict[str, Any]:
    params = {"bbsCrtSn": BBS_CRT_SN, "pstSn": pst, "fileNo": file_no}
    detail = urljoin(BASE_DETAIL, pst)
    result = {"http_status": None, "final_url": "", "bytes": 0, "prefix_hex": "", "format": "UNKNOWN", "error": ""}
    try:
        with session.get(DOWNLOAD_ENDPOINT, params=params, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code
            result["final_url"] = str(r.url)
            chunks = []
            total = 0
            for chunk in r.iter_content(128 * 1024):
                if not chunk: continue
                total += len(chunk)
                if total > MAX_FILE_BYTES: raise ValueError("HWP file exceeds bounded size cap")
                chunks.append(chunk)
            raw = b"".join(chunks)
            result["bytes"] = len(raw)
            result["prefix_hex"] = raw[:64].hex(" ")
            if raw.startswith(HWP3_SIG): result["format"] = "HWP3"
            elif raw.startswith(HWP5_SIG): result["format"] = "HWP5"
            else: result["format"] = "UNKNOWN"
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def probe(session: requests.Session, row: Dict[str, Any], request_count: List[int]) -> Dict[str, Any]:
    meta = fetch_metadata(session, row)
    request_count[0] += 1
    att = hwp_attachment(meta.get("json")) if meta.get("json") is not None else None
    rec: Dict[str, Any] = {
        "date": norm(row.get("date")), "gazette_number": row.get("gazette_number"), "pstSn": norm(row.get("pstSn")),
        "metadata_http": meta.get("http_status"), "metadata_url": meta.get("final_url"), "hwp_attachment": att,
        "download_http": None, "download_url": "", "download_bytes": 0, "prefix_hex": "", "format": "UNKNOWN", "error": meta.get("error") or "",
    }
    if not att or request_count[0] >= MAX_REQUESTS:
        return rec
    dl = fetch_hwp(session, rec["pstSn"], att["file_no"])
    request_count[0] += 1
    rec.update({
        "download_http": dl.get("http_status"), "download_url": dl.get("final_url"), "download_bytes": dl.get("bytes"),
        "prefix_hex": dl.get("prefix_hex"), "format": dl.get("format"), "error": dl.get("error") or rec["error"],
    })
    return rec


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP INTERNAL FORMAT TRANSITION BISECTION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Known left anchor:", LEFT_ANCHOR)
    print("Known right anchor:", RIGHT_ANCHOR)
    print("Maximum total requests:", MAX_REQUESTS)
    print("Text extraction: DISABLED")
    print("Body keyword search: DISABLED")
    print()

    if not T23.exists(): raise FileNotFoundError(T23)
    registry = json.loads(T23.read_text(encoding="utf-8"))
    rows = dated_rows(registry.get("canonical_gazette_rows") or registry.get("next_stage_row_pool") or [])
    li = locate(rows, LEFT_ANCHOR["pstSn"])
    ri = locate(rows, RIGHT_ANCHOR["pstSn"])
    if li >= ri: raise AssertionError("anchor ordering invalid")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    requests_used = [0]
    probes: List[Dict[str, Any]] = []
    status = "UNKNOWN"

    while ri - li > 1 and requests_used[0] + 2 <= MAX_REQUESTS:
        mi = (li + ri) // 2
        p = probe(session, rows[mi], requests_used)
        p["registry_index"] = mi
        probes.append(p)
        if p["format"] == "HWP3": li = mi
        elif p["format"] == "HWP5": ri = mi
        else:
            status = "UNCLASSIFIED_MIDPOINT_ENCOUNTERED"
            break
    else:
        status = "ADJACENT_BOUNDARY_RECOVERED" if ri - li == 1 else "REQUEST_BUDGET_EXHAUSTED"

    left_row = {"index": li, "date": norm(rows[li].get("date")), "gazette_number": rows[li].get("gazette_number"), "pstSn": norm(rows[li].get("pstSn")), "format": "HWP3"}
    right_row = {"index": ri, "date": norm(rows[ri].get("date")), "gazette_number": rows[ri].get("gazette_number"), "pstSn": norm(rows[ri].get("pstSn")), "format": "HWP5"}

    output = {
        "step": "STEP 17-21-C-16-8-T-31 Municipal Gazette HWP Internal Format Transition Bisection",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "known_anchors": {"left": LEFT_ANCHOR, "right": RIGHT_ANCHOR},
        "network_request_count": requests_used[0], "max_request_count": MAX_REQUESTS,
        "status": status, "left_boundary_row": left_row, "right_boundary_row": right_row, "probes": probes,
        "classification": "HWP3_TO_HWP5_INTERNAL_FORMAT_BOUNDARY_BISECTION_COMPLETED",
        "text_extraction_executed": False, "body_keyword_search_executed": False, "bulk_archive_traversal_executed": False,
        "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False,
        "site_negative_allowed": False, "final_positive_promotion_allowed": False,
        "semantic_note": "Binary format-routing evidence only. No UQQ700 semantic inference.",
        "resolution": "MUNICIPAL_GAZETTE_HWP_INTERNAL_FORMAT_TRANSITION_BISECTION_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    for p in probes:
        print("PROBE:", {"index": p["registry_index"], "date": p["date"], "gazette": p["gazette_number"], "pstSn": p["pstSn"], "file": (p.get("hwp_attachment") or {}).get("file_name"), "format": p["format"], "bytes": p["download_bytes"], "meta_http": p["metadata_http"], "download_http": p["download_http"]})
    print()
    print("Status:", status)
    print("Left boundary row:", left_row)
    print("Right boundary row:", right_row)
    print("Network request count:", requests_used[0])
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([output["text_extraction_executed"], output["body_keyword_search_executed"], output["bulk_archive_traversal_executed"], output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"], output["final_positive_promotion_allowed"]])
    vals = {
        "T-23 registry exists": T23.exists(),
        "known anchors found in registry": li >= 0 and ri >= 0,
        "request budget respected": requests_used[0] <= MAX_REQUESTS,
        "all metadata probes HTTP 200": all(p["metadata_http"] == 200 for p in probes),
        "all downloads HTTP 200": all(p["download_http"] == 200 for p in probes),
        "all probes binary-classified": all(p["format"] in {"HWP3", "HWP5"} for p in probes),
        "all response hosts official": all(host(p["metadata_url"]) == "www.seongnam.go.kr" and host(p["download_url"]) == "www.seongnam.go.kr" for p in probes),
        "text extraction disabled": not output["text_extraction_executed"],
        "body keyword search disabled": not output["body_keyword_search_executed"],
        "bulk archive traversal disabled": not output["bulk_archive_traversal_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()): raise AssertionError("HWP internal format transition bisection failed")


if __name__ == "__main__":
    main()
