# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-30
Development Density Management Area
Municipal Gazette Attachment Format Transition Bisection

Bounded metadata-only bisection over the two transition intervals recovered by T-29:
1) hwp -> hwp+pdf
2) hwp+pdf -> hwpx+pdf

No attachment downloads and no body keyword search. This stage only narrows routing
boundaries for later format-specific UQQ700 search batches.
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
T29 = OUT_DIR / "development_density_management_area_municipal_gazette_attachment_format_stratified_sampling.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_attachment_format_transition_bisection.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 20


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_iso_date(value: Any) -> Optional[date]:
    try:
        y, m, d = [int(x) for x in norm(value).split("-")]
        return date(y, m, d)
    except Exception:
        return None


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x}
            if any(k in keys for k in ["fileno", "file_no", "atchfileno", "orginlfilenm", "orignlfilenm", "strefilenm"]):
                out.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return out


def ext_from(name: str, explicit: str) -> str:
    e = norm(explicit).lower().lstrip(".")
    if e:
        return e
    m = re.search(r"\.([A-Za-z0-9]{1,10})$", norm(name))
    return m.group(1).lower() if m else ""


def extensions(obj: Any) -> List[str]:
    found = set()
    for item in flatten_items(obj):
        lower = {str(k).lower(): v for k, v in item.items()}
        name = lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm")
        explicit = lower.get("fileextsn") or lower.get("fileext") or ""
        e = ext_from(norm(name), norm(explicit))
        if e:
            found.add(e)
    return sorted(found)


def signature(exts: List[str]) -> str:
    return "+".join(sorted(exts)) if exts else "NO_ATTACHMENT"


def fetch_sig(session: requests.Session, row: Dict[str, Any]) -> Dict[str, Any]:
    pst = norm(row.get("pstSn"))
    detail = urljoin(BASE_DETAIL, pst)
    result = {"pstSn": pst, "date": norm(row.get("date")), "gazette_number": row.get("gazette_number"), "http_status": None, "final_url": "", "json_detected": False, "extensions": [], "signature": "NO_ATTACHMENT", "error": ""}
    try:
        with session.get(ATTACHMENT_ENDPOINT, params={"pstSn": pst}, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            result["http_status"] = r.status_code
            result["final_url"] = str(r.url)
            chunks = []
            total = 0
            for chunk in r.iter_content(128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            try:
                obj = r.json()
            except Exception:
                obj = json.loads(raw.decode(r.encoding or "utf-8", errors="replace"))
            result["json_detected"] = True
            result["extensions"] = extensions(obj)
            result["signature"] = signature(result["extensions"])
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def dated_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    valid = [r for r in rows if parse_iso_date(r.get("date")) and norm(r.get("pstSn"))]
    valid.sort(key=lambda r: (parse_iso_date(r.get("date")), int(r.get("gazette_number") or 0), norm(r.get("pstSn"))))
    return valid


def locate_index(rows: List[Dict[str, Any]], pst: str) -> int:
    for i, r in enumerate(rows):
        if norm(r.get("pstSn")) == pst:
            return i
    raise ValueError(f"pstSn not in registry: {pst}")


def bisect_transition(session: requests.Session, rows: List[Dict[str, Any]], left: Dict[str, Any], right: Dict[str, Any], budget: List[int]) -> Dict[str, Any]:
    li = locate_index(rows, norm(left.get("pstSn")))
    ri = locate_index(rows, norm(right.get("pstSn")))
    if li >= ri:
        raise AssertionError("invalid transition interval ordering")
    left_sig = norm(left.get("format_signature"))
    right_sig = norm(right.get("format_signature"))
    probes = []
    while ri - li > 1 and budget[0] < MAX_REQUESTS:
        mi = (li + ri) // 2
        probe = fetch_sig(session, rows[mi])
        budget[0] += 1
        probe["registry_index"] = mi
        probes.append(probe)
        sig = probe["signature"]
        if sig == left_sig:
            li = mi
        elif sig == right_sig:
            ri = mi
        else:
            # Intermediate signature means transition is multi-step; stop exact bisection and report it.
            return {
                "status": "INTERMEDIATE_SIGNATURE_FOUND",
                "left_index": li,
                "right_index": ri,
                "left_signature": left_sig,
                "right_signature": right_sig,
                "intermediate_probe": probe,
                "probes": probes,
            }
    return {
        "status": "ADJACENT_BOUNDARY_RECOVERED" if ri - li == 1 else "REQUEST_BUDGET_EXHAUSTED",
        "left_index": li,
        "right_index": ri,
        "left_row": {"date": norm(rows[li].get("date")), "gazette_number": rows[li].get("gazette_number"), "pstSn": norm(rows[li].get("pstSn"))},
        "right_row": {"date": norm(rows[ri].get("date")), "gazette_number": rows[ri].get("gazette_number"), "pstSn": norm(rows[ri].get("pstSn"))},
        "left_signature": left_sig,
        "right_signature": right_sig,
        "probes": probes,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE ATTACHMENT FORMAT TRANSITION BISECTION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Maximum metadata requests:", MAX_REQUESTS)
    print("File download: DISABLED")
    print("Body keyword search: DISABLED")
    print()

    if not T23.exists() or not T29.exists():
        raise FileNotFoundError("T-23 or T-29 output missing")
    reg = json.loads(T23.read_text(encoding="utf-8"))
    t29 = json.loads(T29.read_text(encoding="utf-8"))
    rows = dated_rows(reg.get("canonical_gazette_rows") or reg.get("next_stage_row_pool") or [])
    samples = t29.get("samples") or []
    transitions = t29.get("transition_intervals") or []
    by_ordinal = {int(s.get("sample_ordinal")): s for s in samples}

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    budget = [0]
    results = []
    for t in transitions:
        left = by_ordinal[int(t["left_sample"])]
        right = by_ordinal[int(t["right_sample"])]
        results.append(bisect_transition(session, rows, left, right, budget))

    classification = "ATTACHMENT_FORMAT_TRANSITIONS_BOUNDED_BISECTION_COMPLETED"
    output = {
        "step": "STEP 17-21-C-16-8-T-30 Municipal Gazette Attachment Format Transition Bisection",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": budget[0],
        "max_request_count": MAX_REQUESTS,
        "results": results,
        "classification": classification,
        "file_download_executed": False,
        "body_keyword_search_executed": False,
        "bulk_archive_traversal_executed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "semantic_note": "Format boundary recovery only. No UQQ700 semantic inference.",
        "resolution": "MUNICIPAL_GAZETTE_ATTACHMENT_FORMAT_TRANSITION_BISECTION_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    for i, r in enumerate(results, 1):
        print("-" * 60)
        print("Transition:", i)
        print("Status:", r["status"])
        print("Left signature:", r["left_signature"])
        print("Right signature:", r["right_signature"])
        if r.get("left_row"):
            print("Left boundary row:", r["left_row"])
            print("Right boundary row:", r["right_row"])
        if r.get("intermediate_probe"):
            print("Intermediate probe:", r["intermediate_probe"])
        print("Probe count:", len(r["probes"]))
        for p in r["probes"]:
            print("  PROBE:", {"index": p.get("registry_index"), "date": p.get("date"), "gazette": p.get("gazette_number"), "signature": p.get("signature"), "http": p.get("http_status")})

    print()
    print("SUMMARY")
    print("Network request count:", budget[0])
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["file_download_executed"], output["body_keyword_search_executed"], output["bulk_archive_traversal_executed"],
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ])
    vals = {
        "T-23 registry exists": T23.exists(),
        "T-29 stratified sampling exists": T29.exists(),
        "transition interval count preserved": len(results) == len(transitions) and len(results) > 0,
        "request budget respected": budget[0] <= MAX_REQUESTS,
        "all probes HTTP 200": all(p.get("http_status") == 200 for r in results for p in r.get("probes", [])),
        "all probes JSON detected": all(p.get("json_detected") for r in results for p in r.get("probes", [])),
        "all probe hosts official": all(host(p.get("final_url", "")) == "www.seongnam.go.kr" for r in results for p in r.get("probes", [])),
        "file download disabled": not output["file_download_executed"],
        "body keyword search disabled": not output["body_keyword_search_executed"],
        "bulk archive traversal disabled": not output["bulk_archive_traversal_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("attachment format transition bisection failed")


if __name__ == "__main__":
    main()
