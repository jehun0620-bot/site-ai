# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S39
Targeted recovery for three oversized HWP rows discovered after S38.

Targets:
- Gazette 1157 / pstSn 29332
- Gazette 1158 / pstSn 29333
- Gazette 1161 / pstSn 29336

Safety:
- exact three pstSn only
- temporarily raise download ceiling to 64 MiB
- temporarily raise HWP5 record safety ceiling to 1,000,000
- no cumulative state mutation
- no legal/SITE promotion
- no negative-evidence inference
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search_test as hwp3
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_candidate_unresolved_diagnostic_test as diag

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_large_hwp_targeted_recovery.json"

TARGETS = {
    "29332": {"gazette_number": 1157, "date": "2013-02-12"},
    "29333": {"gazette_number": 1158, "date": "2013-02-18"},
    "29336": {"gazette_number": 1161, "date": "2013-03-08"},
}
LARGE_FILE_LIMIT = 64 * 1024 * 1024
MAX_RECORDS = 1_000_000
MAX_REQUESTS = len(TARGETS) * 2


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("OVERSIZED HWP TARGETED RECOVERY")
    print("=" * 60)
    print("Targets:", sorted(TARGETS))
    print("Download ceiling:", LARGE_FILE_LIMIT)
    print("HWP5 record ceiling:", MAX_RECORDS)
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    prior = {hwp5.norm(r.get("pstSn")): r for r in (state.get("results") or []) if hwp5.norm(r.get("pstSn"))}

    for pst, meta in TARGETS.items():
        if pst not in prior:
            raise AssertionError(f"target missing from state: {pst}")
        r = prior[pst]
        if r.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
            raise AssertionError(f"target is not retryable unresolved: {pst} / {r.get('status')}")
        if "file too large" not in str(r.get("error") or ""):
            raise AssertionError(f"target unresolved reason changed: {pst} / {r.get('error')}")
        if int(r.get("gazette_number") or 0) != meta["gazette_number"]:
            raise AssertionError(f"gazette identity mismatch: {pst}")

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0
    results: List[Dict[str, Any]] = []

    original_file_limit = hwp5.MAX_FILE_BYTES
    original_parser = hwp5.parse_records_text
    hwp5.MAX_FILE_BYTES = LARGE_FILE_LIMIT
    hwp5.parse_records_text = diag.high_limit_parse_records_text
    try:
        for pst, meta in TARGETS.items():
            rec: Dict[str, Any] = {
                "pstSn": pst,
                "gazette_number": meta["gazette_number"],
                "date": meta["date"],
                "prior_status": prior[pst].get("status"),
                "status": "UNKNOWN",
                "signature_class": "UNKNOWN",
                "parser_used": "",
                "direct_matches": {},
                "high_signal_related_matches": {},
                "contexts": [],
                "error": "",
            }
            try:
                hs, mu, obj = hwp5.get_json(session, pst); req += 1
                att = hwp5.hwp_attachment(obj)
                rec.update({"metadata_http": hs, "metadata_url": mu, "attachment": att})
                if not att:
                    raise ValueError("HWP attachment not found")

                ds, du, raw = hwp5.get_file(session, pst, att["file_no"]); req += 1
                rec.update({"download_http": ds, "download_url": du, "download_bytes": len(raw)})
                sig = base.classify_signature(raw)
                rec["signature_class"] = sig

                if sig == "HWP3":
                    ext = hwp3.extract_hwp3(raw)
                    rec["parser_used"] = "HWP3"
                elif sig == "HWP5":
                    ext = hwp5.extract_hwp5(raw)
                    rec["parser_used"] = f"HWP5_LARGE_FILE_HIGH_LIMIT_{MAX_RECORDS}"
                else:
                    raise ValueError("unknown HWP binary signature")

                rec["extract_ok"] = ext.get("ok")
                rec["extract_error"] = ext.get("error")
                text = ext.get("text", "") or ""
                rec["text_chars"] = len(text)
                rec["sections"] = ext.get("sections")
                if not ext.get("ok"):
                    raise ValueError(ext.get("error") or "targeted extraction failed")

                rec["direct_matches"] = {t: text.count(t) for t in hwp5.DIRECT}
                rec["high_signal_related_matches"] = {t: text.count(t) for t in base.HIGH_SIGNAL_RELATED}
                rec["contexts"] = diag.term_contexts(text)
                if any(rec["direct_matches"].values()):
                    rec["status"] = "DIRECT_CANDIDATE"
                elif any(rec["high_signal_related_matches"].values()):
                    rec["status"] = "RELATED_CANDIDATE"
                else:
                    rec["status"] = "NO_TERM_IN_EXTRACTED_SAMPLE"
            except Exception as exc:
                rec["status"] = "EXTRACTION_OR_REQUEST_UNKNOWN"
                rec["error"] = repr(exc)

            results.append(rec)
            print("\nTARGET RESULT:", {k: rec.get(k) for k in [
                "gazette_number", "date", "pstSn", "status", "signature_class",
                "parser_used", "download_http", "download_bytes", "text_chars",
                "direct_matches", "high_signal_related_matches", "extract_error", "error"
            ]})
            for i, c in enumerate(rec.get("contexts") or [], 1):
                print(f"CONTEXT {i} [{c['term']}]: {c['context']}")
    finally:
        hwp5.MAX_FILE_BYTES = original_file_limit
        hwp5.parse_records_text = original_parser

    recovered = [r for r in results if r.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN"]
    unresolved = [r for r in results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    candidates = [r for r in results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S39",
        "download_ceiling": LARGE_FILE_LIMIT,
        "hwp5_record_ceiling": MAX_RECORDS,
        "network_request_count": req,
        "results": results,
        "recovered_count": len(recovered),
        "unresolved_count": len(unresolved),
        "candidate_count": len(candidates),
        "state_mutation_allowed": False,
        "negative_evidence_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "state exists": STATE.exists(),
        "exact target set": {r.get("pstSn") for r in results} == set(TARGETS),
        "request budget respected": req <= MAX_REQUESTS,
        "download ceiling restored": hwp5.MAX_FILE_BYTES == original_file_limit,
        "parser restored": hwp5.parse_records_text is original_parser,
        "state mutation disabled": not output["state_mutation_allowed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Targets:", len(results))
    print("Recovered:", len(recovered))
    print("Still unresolved:", len(unresolved))
    print("Candidates:", len(candidates))
    print("Network requests:", req)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("oversized HWP targeted recovery validation failed")


if __name__ == "__main__":
    main()
