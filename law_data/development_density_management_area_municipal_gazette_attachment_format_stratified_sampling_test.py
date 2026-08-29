# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-29
Development Density Management Area
Municipal Gazette Attachment Format Stratified Sampling

Purpose
-------
The HWP3, HWP5-distribution, and HWPX extraction paths are now technically validated
on representative municipal gazette samples. Before archive-scale UQQ700 candidate
search, characterize attachment-format eras using a bounded metadata-only sample.

Method
------
- input: T-23 canonical gazette registry (1608 rows in current archive snapshot)
- sort by date ascending
- select exactly 15 unique stratified positions across the full archive span
- issue exactly one attachment-metadata request per selected pstSn
- do not download attachments
- summarize HWP/HWPX/PDF extension signatures and adjacent signature transitions

This is format-routing evidence only. No attachment/body search and no legal status
promotion. Missing attachments or no UQQ700 evidence remains UNKNOWN, never FALSE.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_attachment_format_stratified_sampling.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
SOURCE_FAMILY = "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"

SAMPLE_COUNT = 15
MAX_REQUESTS = 15
TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_iso_date(value: Any) -> Optional[date]:
    s = norm(value)
    try:
        y, m, d = [int(x) for x in s.split("-")]
        return date(y, m, d)
    except Exception:
        return None


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def gov(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []

    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x.keys()}
            if any(k in keys for k in ["fileno", "file_no", "atchfileno", "orginlfilenm", "orignlfilenm", "strefilenm"]):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(obj)
    return found


def file_ext_from(name: str, explicit: str) -> str:
    e = norm(explicit).lower().lstrip(".")
    if e:
        return e
    m = re.search(r"\.([A-Za-z0-9]{1,10})$", norm(name))
    return m.group(1).lower() if m else ""


def normalize_attachments(obj: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    seen = set()
    for item in flatten_items(obj):
        lower = {str(k).lower(): v for k, v in item.items()}
        file_no = lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
        name = lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm")
        stored = lower.get("strefilenm") or ""
        explicit_ext = lower.get("fileextsn") or lower.get("fileext") or ""
        rec = {
            "file_no": norm(file_no),
            "file_name": norm(name),
            "stored_file_name": norm(stored),
            "file_ext": file_ext_from(norm(name), norm(explicit_ext)),
            "file_size": lower.get("filesize"),
        }
        key = (rec["file_no"], rec["file_name"])
        if key in seen:
            continue
        seen.add(key)
        out.append(rec)
    return out


def fetch_json(session: requests.Session, pst_sn: str) -> Dict[str, Any]:
    detail_url = urljoin(BASE_DETAIL, pst_sn)
    result: Dict[str, Any] = {
        "http_status": None,
        "final_url": "",
        "response_bytes": 0,
        "json": None,
        "error": "",
        "detail_url": detail_url,
    }
    try:
        with session.get(
            ATTACHMENT_ENDPOINT,
            params={"pstSn": pst_sn},
            headers={"Referer": detail_url},
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:
            result["http_status"] = response.status_code
            result["final_url"] = str(response.url)
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            result["response_bytes"] = len(raw)
            try:
                result["json"] = response.json()
            except Exception:
                try:
                    result["json"] = json.loads(raw.decode(response.encoding or "utf-8", errors="replace"))
                except Exception:
                    result["json"] = None
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def select_stratified(rows: List[Dict[str, Any]], n: int) -> List[Tuple[int, Dict[str, Any]]]:
    dated: List[Tuple[date, Dict[str, Any]]] = []
    for row in rows:
        d = parse_iso_date(row.get("date"))
        if d is not None and norm(row.get("pstSn")):
            dated.append((d, row))
    dated.sort(key=lambda x: (x[0], int(x[1].get("gazette_number") or 0), norm(x[1].get("pstSn"))))
    if len(dated) < n:
        raise AssertionError(f"need at least {n} dated rows")

    indices: List[int] = []
    last = len(dated) - 1
    for i in range(n):
        idx = round(i * last / (n - 1))
        if idx not in indices:
            indices.append(idx)
    # Guard against rare round collisions.
    cursor = 0
    while len(indices) < n:
        if cursor not in indices:
            indices.append(cursor)
        cursor += 1
    indices = sorted(indices[:n])
    return [(idx, dated[idx][1]) for idx in indices]


def signature(exts: List[str]) -> str:
    s = sorted({e.lower() for e in exts if e})
    return "+".join(s) if s else "NO_ATTACHMENT"


def route_class(exts: List[str]) -> str:
    e = {x.lower() for x in exts}
    if "hwpx" in e:
        return "HWPX_CAPABLE"
    if "hwp" in e:
        return "HWP_LEGACY_REQUIRES_BINARY_CLASSIFICATION"
    if "pdf" in e:
        return "PDF_ONLY_OR_PDF_PRIMARY"
    if e:
        return "OTHER_ATTACHMENT_FORMAT"
    return "NO_ATTACHMENT_METADATA"


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE ATTACHMENT FORMAT STRATIFIED SAMPLING")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Stratified sample count:", SAMPLE_COUNT)
    print("Maximum metadata requests:", MAX_REQUESTS)
    print("File download: DISABLED")
    print("Body keyword search: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T23.exists():
        raise FileNotFoundError(T23)
    registry = json.loads(T23.read_text(encoding="utf-8"))
    rows = registry.get("canonical_gazette_rows") or registry.get("next_stage_row_pool") or []
    if not isinstance(rows, list) or len(rows) < SAMPLE_COUNT:
        raise AssertionError("T-23 canonical registry unavailable")

    selected = select_stratified(rows, SAMPLE_COUNT)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    samples: List[Dict[str, Any]] = []
    request_count = 0
    for ordinal, (registry_index, row) in enumerate(selected, 1):
        pst_sn = norm(row.get("pstSn"))
        response = fetch_json(session, pst_sn)
        request_count += 1
        attachments = normalize_attachments(response.get("json")) if response.get("json") is not None else []
        extensions = sorted({a["file_ext"] for a in attachments if a.get("file_ext")})
        samples.append({
            "sample_ordinal": ordinal,
            "registry_index": registry_index,
            "gazette_number": row.get("gazette_number"),
            "date": norm(row.get("date")),
            "pstSn": pst_sn,
            "page_number": row.get("page_number"),
            "request": {
                "http_status": response.get("http_status"),
                "final_url": response.get("final_url"),
                "response_bytes": response.get("response_bytes"),
                "error": response.get("error"),
                "json_detected": response.get("json") is not None,
            },
            "attachment_count": len(attachments),
            "extensions": extensions,
            "format_signature": signature(extensions),
            "route_class": route_class(extensions),
            "attachments": attachments,
        })

    transitions: List[Dict[str, Any]] = []
    for left, right in zip(samples, samples[1:]):
        if left["format_signature"] != right["format_signature"] or left["route_class"] != right["route_class"]:
            transitions.append({
                "left_sample": left["sample_ordinal"],
                "left_date": left["date"],
                "left_gazette": left["gazette_number"],
                "left_signature": left["format_signature"],
                "left_route": left["route_class"],
                "right_sample": right["sample_ordinal"],
                "right_date": right["date"],
                "right_gazette": right["gazette_number"],
                "right_signature": right["format_signature"],
                "right_route": right["route_class"],
                "candidate_transition_interval": [left["date"], right["date"]],
            })

    route_counts: Dict[str, int] = {}
    signature_counts: Dict[str, int] = {}
    for s in samples:
        route_counts[s["route_class"]] = route_counts.get(s["route_class"], 0) + 1
        signature_counts[s["format_signature"]] = signature_counts.get(s["format_signature"], 0) + 1

    all_http_200 = all(s["request"]["http_status"] == 200 for s in samples)
    all_json = all(s["request"]["json_detected"] for s in samples)
    all_official = all(
        gov(host(s["request"]["final_url"])) and host(s["request"]["final_url"]) == host(ATTACHMENT_ENDPOINT)
        for s in samples
    )

    if transitions:
        classification = "STRATIFIED_ATTACHMENT_FORMAT_TRANSITION_INTERVALS_RECOVERED"
    elif len(signature_counts) == 1:
        classification = "STRATIFIED_ATTACHMENT_FORMAT_SIGNATURE_STABLE_IN_SAMPLES"
    else:
        classification = "STRATIFIED_ATTACHMENT_FORMAT_MIXED_WITHOUT_ADJACENT_TRANSITION"

    output = {
        "step": "STEP 17-21-C-16-8-T-29 Municipal Gazette Attachment Format Stratified Sampling",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "source_family": SOURCE_FAMILY,
        "input": str(T23),
        "method": {
            "registry_row_count": len(rows),
            "sample_count": SAMPLE_COUNT,
            "selection": "equal-index stratified over date-sorted canonical registry",
            "metadata_only": True,
            "max_request_count": MAX_REQUESTS,
            "file_download_enabled": False,
            "body_keyword_search_enabled": False,
            "bulk_archive_traversal_enabled": False,
        },
        "summary": {
            "request_count": request_count,
            "sample_count": len(samples),
            "http_200_count": sum(1 for s in samples if s["request"]["http_status"] == 200),
            "attachment_bearing_count": sum(1 for s in samples if s["attachment_count"] > 0),
            "route_counts": route_counts,
            "signature_counts": signature_counts,
            "transition_interval_count": len(transitions),
        },
        "samples": samples,
        "transition_intervals": transitions,
        "classification": classification,
        "semantic_note": "Stratified metadata sampling determines extraction routing only. It is not UQQ700 positive or negative evidence.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_ATTACHMENT_FORMAT_STRATIFIED_SAMPLING_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any([
        output["method"]["file_download_enabled"],
        output["method"]["body_keyword_search_enabled"],
        output["method"]["bulk_archive_traversal_enabled"],
        output["verified_positive"],
        output["runtime_registration_allowed"],
        output["site_positive_allowed"],
        output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])

    for s in samples:
        print("-" * 60)
        print("Sample:", s["sample_ordinal"], "/", SAMPLE_COUNT)
        print("Registry index:", s["registry_index"])
        print("Gazette / Date:", s["gazette_number"], s["date"])
        print("pstSn:", s["pstSn"])
        print("HTTP / JSON:", s["request"]["http_status"], s["request"]["json_detected"])
        print("Attachments:", s["attachment_count"])
        print("Extensions:", s["extensions"])
        print("Format signature:", s["format_signature"])
        print("Route class:", s["route_class"])

    print()
    print("TRANSITION INTERVALS")
    for t in transitions:
        print(
            f"- {t['left_date']} {t['left_signature']} -> "
            f"{t['right_date']} {t['right_signature']} | {t['candidate_transition_interval']}"
        )
    print()
    print("SUMMARY")
    print("Request count:", request_count)
    print("Route counts:", route_counts)
    print("Signature counts:", signature_counts)
    print("Transition interval count:", len(transitions))
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    validations = {
        "T-23 registry exists": T23.exists(),
        "exactly 15 unique stratified samples": len(samples) == SAMPLE_COUNT and len({s["pstSn"] for s in samples}) == SAMPLE_COUNT,
        "request budget respected": request_count == SAMPLE_COUNT and request_count <= MAX_REQUESTS,
        "all metadata requests HTTP 200": all_http_200,
        "all JSON metadata responses detected": all_json,
        "all response hosts official and same host": all_official,
        "file download disabled": not output["method"]["file_download_enabled"],
        "body keyword search disabled": not output["method"]["body_keyword_search_enabled"],
        "bulk archive traversal disabled": not output["method"]["bulk_archive_traversal_enabled"],
        "unsafe promotion leakage zero": not unsafe,
        "classification produced": bool(classification),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in validations.items():
        print(f"{k}: {v}")
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        raise AssertionError("municipal gazette attachment format stratified sampling failed")


if __name__ == "__main__":
    main()
