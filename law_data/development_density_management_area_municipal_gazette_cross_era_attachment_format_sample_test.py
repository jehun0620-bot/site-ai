# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-6
Development Density Management Area
Municipal Gazette Cross-Era Attachment Format Sample

Purpose
-------
Before generalizing the successfully validated 2026 HWPX decryption pipeline to the
entire 2003-2026 municipal gazette archive, sample exactly three canonical gazette
rows (earliest, temporal midpoint, latest) and enumerate attachment metadata only.

Safety
------
- exactly 3 attachment-metadata requests maximum
- no attachment/file download
- no preview request
- no document/body keyword search
- no bulk archive traversal
- no TRUE/FALSE or SITE promotion
- attachment absence / format mismatch => UNKNOWN, never FALSE
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
OUT_DIR.mkdir(parents=True, exist_ok=True)

T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_cross_era_attachment_format_sample.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
SOURCE_FAMILY = "CURRENT_MUNICIPAL_GAZETTE_ARCHIVE"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"

TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def gov(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def parse_iso_date(value: Any) -> Optional[date]:
    s = norm(value)
    try:
        y, m, d = [int(x) for x in s.split("-")]
        return date(y, m, d)
    except Exception:
        return None


def select_cross_era_rows(rows: List[Dict[str, Any]]) -> List[Tuple[str, Dict[str, Any]]]:
    dated = [(parse_iso_date(r.get("date")), r) for r in rows]
    dated = [(d, r) for d, r in dated if d is not None and norm(r.get("pstSn"))]
    dated.sort(key=lambda x: (x[0], int(x[1].get("gazette_number") or 0), norm(x[1].get("pstSn"))))
    if len(dated) < 3:
        raise AssertionError("need at least three dated canonical gazette rows")

    first_d, first = dated[0]
    last_d, last = dated[-1]
    target_ord = first_d.toordinal() + (last_d.toordinal() - first_d.toordinal()) / 2.0
    middle_d, middle = min(dated, key=lambda x: abs(x[0].toordinal() - target_ord))

    selected = [("EARLIEST", first), ("MIDPOINT", middle), ("LATEST", last)]
    if len({norm(r.get("pstSn")) for _, r in selected}) != 3:
        raise AssertionError("cross-era sample rows are not unique")
    return selected


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
    headers = {"Referer": detail_url}
    try:
        with session.get(
            ATTACHMENT_ENDPOINT,
            params={"pstSn": pst_sn},
            headers=headers,
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
            text = raw.decode(response.encoding or "utf-8", errors="replace")
            try:
                result["json"] = response.json()
            except Exception:
                try:
                    result["json"] = json.loads(text)
                except Exception:
                    result["json"] = None
    except Exception as exc:
        result["error"] = repr(exc)
    return result


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


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE CROSS-ERA ATTACHMENT FORMAT SAMPLE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Sample roles: EARLIEST / MIDPOINT / LATEST")
    print("Maximum metadata requests:", MAX_REQUESTS)
    print("File download: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T23.exists():
        raise FileNotFoundError(T23)
    t23 = json.loads(T23.read_text(encoding="utf-8"))
    rows = t23.get("canonical_gazette_rows") or t23.get("next_stage_row_pool") or []
    if not isinstance(rows, list) or len(rows) < 3:
        raise AssertionError("T-23 canonical row registry unavailable")

    selected = select_cross_era_rows(rows)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})

    samples: List[Dict[str, Any]] = []
    request_count = 0
    for role, row in selected:
        pst_sn = norm(row.get("pstSn"))
        response = fetch_json(session, pst_sn)
        request_count += 1
        attachments = normalize_attachments(response.get("json")) if response.get("json") is not None else []
        extensions = sorted({a["file_ext"] for a in attachments if a.get("file_ext")})
        samples.append({
            "role": role,
            "gazette_number": row.get("gazette_number"),
            "date": norm(row.get("date")),
            "pstSn": pst_sn,
            "page_number": row.get("page_number"),
            "request": {
                "method": "GET",
                "endpoint": ATTACHMENT_ENDPOINT,
                "params": {"pstSn": pst_sn},
                "http_status": response.get("http_status"),
                "final_url": response.get("final_url"),
                "response_bytes": response.get("response_bytes"),
                "error": response.get("error"),
                "json_detected": response.get("json") is not None,
            },
            "attachment_count": len(attachments),
            "extensions": extensions,
            "has_hwpx": "hwpx" in extensions,
            "has_hwp": "hwp" in extensions,
            "has_pdf": "pdf" in extensions,
            "attachments": attachments,
        })

    all_http_200 = all(s["request"]["http_status"] == 200 for s in samples)
    all_official = all(
        gov(host(s["request"]["final_url"])) and host(s["request"]["final_url"]) == host(ATTACHMENT_ENDPOINT)
        for s in samples
    )
    format_signatures = [tuple(s["extensions"]) for s in samples]
    same_format_signature = len(set(format_signatures)) == 1

    if all(s["has_hwpx"] for s in samples):
        classification = "CROSS_ERA_SAMPLES_ALL_HAVE_HWPX"
    elif any(s["has_hwpx"] for s in samples):
        classification = "CROSS_ERA_ATTACHMENT_FORMAT_MIXED_HWPX_PRESENT"
    elif all(s["attachment_count"] > 0 for s in samples):
        classification = "CROSS_ERA_SAMPLES_NO_HWPX_OTHER_ATTACHMENTS_PRESENT"
    else:
        classification = "CROSS_ERA_ATTACHMENT_METADATA_INCOMPLETE"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-6 Municipal Gazette Cross-Era Attachment Format Sample",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "source_family": SOURCE_FAMILY,
        "input": str(T23),
        "method": {
            "sample_roles": ["EARLIEST", "MIDPOINT", "LATEST"],
            "selection_by_archive_date_span": True,
            "metadata_only": True,
            "max_request_count": MAX_REQUESTS,
            "file_download_enabled": False,
            "preview_request_enabled": False,
            "body_keyword_search_enabled": False,
            "bulk_archive_traversal_enabled": False,
        },
        "summary": {
            "request_count": request_count,
            "sample_count": len(samples),
            "http_200_count": sum(1 for s in samples if s["request"]["http_status"] == 200),
            "attachment_bearing_sample_count": sum(1 for s in samples if s["attachment_count"] > 0),
            "hwpx_sample_count": sum(1 for s in samples if s["has_hwpx"]),
            "hwp_sample_count": sum(1 for s in samples if s["has_hwp"]),
            "pdf_sample_count": sum(1 for s in samples if s["has_pdf"]),
            "same_format_signature": same_format_signature,
        },
        "samples": samples,
        "classification": classification,
        "semantic_note": "Three cross-era metadata samples characterize attachment-format continuity only. Absence of HWPX or attachments is not UQQ700 negative evidence.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_CROSS_ERA_ATTACHMENT_FORMAT_SAMPLE_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any([
        output["verified_positive"],
        output["runtime_registration_allowed"],
        output["site_positive_allowed"],
        output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
        output["method"]["file_download_enabled"],
        output["method"]["preview_request_enabled"],
        output["method"]["body_keyword_search_enabled"],
        output["method"]["bulk_archive_traversal_enabled"],
    ])

    validations = {
        "T-23 registry exists": T23.exists(),
        "exactly three unique samples": len(samples) == 3 and len({s["pstSn"] for s in samples}) == 3,
        "request budget respected": request_count == 3 and request_count <= MAX_REQUESTS,
        "all metadata requests HTTP 200": all_http_200,
        "all response hosts official and same host": all_official,
        "JSON metadata responses detected": all(s["request"]["json_detected"] for s in samples),
        "file download disabled": not output["method"]["file_download_enabled"],
        "preview request disabled": not output["method"]["preview_request_enabled"],
        "bulk archive traversal disabled": not output["method"]["bulk_archive_traversal_enabled"],
        "unsafe promotion leakage zero": not unsafe,
        "classification produced": bool(classification),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    for s in samples:
        print("-" * 60)
        print("Role:", s["role"])
        print("Gazette:", s["gazette_number"])
        print("Date:", s["date"])
        print("pstSn:", s["pstSn"])
        print("HTTP:", s["request"]["http_status"])
        print("Attachment count:", s["attachment_count"])
        print("Extensions:", s["extensions"])
        print("HWPX/HWP/PDF:", s["has_hwpx"], s["has_hwp"], s["has_pdf"])
        for a in s["attachments"]:
            print("  ATTACHMENT:", {"file_no": a["file_no"], "file_name": a["file_name"], "file_ext": a["file_ext"], "file_size": a["file_size"]})

    print()
    print("SUMMARY")
    print("Request count:", request_count)
    print("HWPX sample count:", output["summary"]["hwpx_sample_count"])
    print("HWP sample count:", output["summary"]["hwp_sample_count"])
    print("PDF sample count:", output["summary"]["pdf_sample_count"])
    print("Same format signature:", same_format_signature)
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in validations.items():
        print(f"{k}: {v}")
    print("all_pass:", all(validations.values()))

    if not all(validations.values()):
        raise AssertionError("municipal gazette cross-era attachment format sample failed")


if __name__ == "__main__":
    main()
