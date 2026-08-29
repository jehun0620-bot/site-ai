# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S7
Targeted forensics for the first dynamic-HWP candidate and three HWP5
extraction failures observed in the 50-row batch ending at Gazette 768.

Targets
-------
Candidate:
- Gazette 730 / pstSn 28879: high-signal term `개발밀도` occurred once.

Extraction failures:
- Gazette 723 / pstSn 28872
- Gazette 745 / pstSn 28894
- Gazette 758 / pstSn 28907

This stage is diagnostic only. It re-downloads exactly four HWP files, runs the
validated HWP5 extractor, prints extractor diagnostics, and for the candidate
prints bounded text context around direct/high-signal terms.

Safety
------
- max 8 requests (metadata + file for four rows)
- no OCR/PDF fallback
- no state mutation
- no legal promotion
- candidate != designation
- no-match/error != FALSE
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_candidate_and_hwp5_failure_forensics.json"

TARGETS = [
    {"gazette_number": 730, "pstSn": "28879", "role": "RELATED_CANDIDATE"},
    {"gazette_number": 723, "pstSn": "28872", "role": "EXTRACTION_FAILURE"},
    {"gazette_number": 745, "pstSn": "28894", "role": "EXTRACTION_FAILURE"},
    {"gazette_number": 758, "pstSn": "28907", "role": "EXTRACTION_FAILURE"},
]
TERMS = ("개발밀도관리구역", "개발밀도 관리구역", "개발밀도", "밀도관리")
CONTEXT_RADIUS = 220
MAX_REQUESTS = 8


def contexts(text: str, term: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    start = 0
    while len(out) < 10:
        idx = text.find(term, start)
        if idx < 0:
            break
        lo = max(0, idx - CONTEXT_RADIUS)
        hi = min(len(text), idx + len(term) + CONTEXT_RADIUS)
        out.append({
            "term": term,
            "index": idx,
            "context": text[lo:hi].replace("\x00", " "),
        })
        start = idx + len(term)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CANDIDATE + HWP5 FAILURE TARGETED FORENSICS")
    print("=" * 60)
    print("Targets:", len(TARGETS))
    print("Max requests:", MAX_REQUESTS)
    print("State mutation: DISABLED")
    print("OCR/PDF fallback: DISABLED")
    print()

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0
    results: List[Dict[str, Any]] = []

    for target in TARGETS:
        pst = target["pstSn"]
        rec: Dict[str, Any] = dict(target)
        rec.update({"error": "", "contexts": []})
        try:
            hs, mu, obj = hwp5.get_json(session, pst)
            req += 1
            att = hwp5.hwp_attachment(obj)
            rec["metadata_http"] = hs
            rec["metadata_url"] = mu
            rec["attachment"] = att
            if not att:
                raise ValueError("HWP attachment not found")

            ds, du, raw = hwp5.get_file(session, pst, att["file_no"])
            req += 1
            rec["download_http"] = ds
            rec["download_url"] = du
            rec["download_bytes"] = len(raw)

            ext = hwp5.extract_hwp5(raw)
            text = ext.get("text", "") or ""
            rec["extract_ok"] = ext.get("ok")
            rec["extract_error"] = ext.get("error")
            rec["flags"] = ext.get("flags") or {}
            rec["section_count"] = len(ext.get("sections") or [])
            rec["sections"] = ext.get("sections") or []
            rec["text_chars"] = len(text)
            rec["term_counts"] = {term: text.count(term) for term in TERMS}

            if target["role"] == "RELATED_CANDIDATE":
                c: List[Dict[str, Any]] = []
                for term in TERMS:
                    c.extend(contexts(text, term))
                rec["contexts"] = c
        except Exception as exc:
            rec["error"] = repr(exc)

        results.append(rec)
        print("TARGET:", {k: rec.get(k) for k in [
            "gazette_number", "pstSn", "role", "download_bytes", "extract_ok",
            "extract_error", "section_count", "text_chars", "term_counts", "error"
        ]})
        if rec.get("contexts"):
            for ctx in rec["contexts"]:
                print("CONTEXT:", ctx)
        if rec.get("sections"):
            print("SECTIONS:", rec["sections"])
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S7 candidate and HWP5 failure forensics",
        "network_request_count": req,
        "results": results,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    candidate = next(r for r in results if r["role"] == "RELATED_CANDIDATE")
    failures = [r for r in results if r["role"] == "EXTRACTION_FAILURE"]
    unsafe = any([
        output["verified_positive"], output["runtime_registration_allowed"],
        output["site_positive_allowed"], output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "request budget respected": req <= MAX_REQUESTS,
        "all metadata hosts official": all(hwp5.host(r.get("metadata_url", "")) == "www.seongnam.go.kr" for r in results if r.get("metadata_url")),
        "all download hosts official": all(hwp5.host(r.get("download_url", "")) == "www.seongnam.go.kr" for r in results if r.get("download_url")),
        "candidate context captured": bool(candidate.get("contexts")),
        "all three failures inspected": len(failures) == 3 and all(r.get("download_bytes") for r in failures),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("candidate/HWP5 failure forensics failed")


if __name__ == "__main__":
    main()
