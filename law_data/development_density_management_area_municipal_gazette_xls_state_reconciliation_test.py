# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S6
Reconcile the validated targeted XLS recovery for pstSn 28847 into the shared
municipal-gazette cumulative traversal state.

Why this exists
---------------
T-34 is intentionally HWP-focused. pstSn 28847 has no HWP attachment; T-34-S4
proved it has one XLS attachment and T-34-S5 successfully parsed that XLS with
xlrd and searched the extracted cells. Without reconciliation, future T-34 bulk
runs would retry the same row and fail again at HWP attachment selection.

Safety
------
- accepts only the exact known pstSn 28847
- requires the targeted XLS result to be parser=XLRD with no parser error
- requires status to be NO_TERM_IN_EXTRACTED_SAMPLE or a candidate status
- preserves candidate semantics; no-match remains UNKNOWN, never FALSE
- no network requests
- no legal promotion
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
XLS_RESULT = OUT_DIR / "development_density_management_area_municipal_gazette_xls_uqq700_targeted_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_xls_state_reconciliation.json"

TARGET_PST = "28847"
ALLOWED_STATUS = {"NO_TERM_IN_EXTRACTED_SAMPLE", "DIRECT_CANDIDATE", "RELATED_CANDIDATE"}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE XLS STATE RECONCILIATION")
    print("=" * 60)
    print("Target pstSn:", TARGET_PST)
    print("Network requests: 0")
    print("Negative evidence: DISABLED")
    print()

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not XLS_RESULT.exists():
        raise FileNotFoundError(XLS_RESULT)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    xls = json.loads(XLS_RESULT.read_text(encoding="utf-8"))

    checks = {
        "target pst matches": str(xls.get("pstSn") or "") == TARGET_PST,
        "parser is XLRD": xls.get("parser") == "XLRD",
        "parser error empty": not (xls.get("parser_error") or ""),
        "xls status accepted": xls.get("status") in ALLOWED_STATUS,
        "download http 200": xls.get("download_http") == 200,
        "xls bytes present": int(xls.get("download_bytes") or 0) > 0,
        "negative evidence disabled in source": xls.get("negative_evidence_allowed") is False,
    }
    for k, v in checks.items():
        print(f"PRECHECK {k}: {v}")
    if not all(checks.values()):
        raise AssertionError("targeted XLS result is not safe to reconcile")

    prior_results = state.get("results") or []
    prior_processed = [str(x) for x in (state.get("processed_pstSn") or [])]

    # Remove stale prior copies of this exact row only, then insert the validated
    # XLS-format result as a successfully processed source document.
    kept_results = [r for r in prior_results if str(r.get("pstSn") or "") != TARGET_PST]
    rec: Dict[str, Any] = {
        "date": "2006-06-19",
        "gazette_number": 699,
        "pstSn": TARGET_PST,
        "status": xls.get("status"),
        "signature_class": "XLS",
        "parser_used": "XLRD",
        "attachment": {
            "file_no": str(xls.get("fileNo") or "28302"),
            "name": xls.get("file_name") or "백현2천-편입용지조서.xls",
            "format": "xls",
        },
        "download_http": xls.get("download_http"),
        "download_url": xls.get("download_url"),
        "download_bytes": xls.get("download_bytes"),
        "sheet_count": xls.get("sheet_count"),
        "cell_count": xls.get("cell_count"),
        "text_chars": xls.get("text_chars"),
        "direct_matches": xls.get("direct_matches") or {},
        "related_matches": {
            **(xls.get("high_signal_related_matches") or {}),
            **(xls.get("low_signal_related_matches") or {}),
        },
        "high_signal_related_matches": xls.get("high_signal_related_matches") or {},
        "low_signal_related_matches": xls.get("low_signal_related_matches") or {},
        "error": "",
        "format_specific_recovery": "T-34-S5_XLS",
        "negative_evidence_allowed": False,
    }
    merged_results = kept_results + [rec]

    processed = [p for p in prior_processed if p != TARGET_PST]
    processed.append(TARGET_PST)
    processed = list(dict.fromkeys(processed))

    candidates = [r for r in merged_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in merged_results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]

    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in merged_results:
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    era_count = int(state.get("era_row_count") or 0)
    state["processed_pstSn"] = processed
    state["processed_count"] = len(processed)
    state["remaining_count"] = era_count - len(processed)
    state["candidate_count"] = len(candidates)
    state["unresolved_count"] = len(unresolved)
    state["signature_counts"] = signature_counts
    state["parser_counts"] = parser_counts
    state["results"] = merged_results
    state["negative_evidence_allowed"] = False
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S6 XLS state reconciliation",
        "target_pstSn": TARGET_PST,
        "reconciled_result": rec,
        "processed_count": state["processed_count"],
        "remaining_count": state["remaining_count"],
        "candidate_count": state["candidate_count"],
        "unresolved_count": state["unresolved_count"],
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("SUMMARY")
    print("Processed:", state["processed_count"])
    print("Remaining:", state["remaining_count"])
    print("Candidates:", state["candidate_count"])
    print("Unresolved:", state["unresolved_count"])
    print("Signature counts:", signature_counts)
    print("Parser counts:", parser_counts)
    print("State:", STATE)
    print("Output:", OUT)

    unsafe = any([
        output["verified_positive"], output["runtime_registration_allowed"],
        output["site_positive_allowed"], output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "target processed": TARGET_PST in processed,
        "target result unique": sum(1 for r in merged_results if str(r.get("pstSn") or "") == TARGET_PST) == 1,
        "target parser preserved": rec["parser_used"] == "XLRD",
        "target format preserved": rec["signature_class"] == "XLS",
        "no unresolved target": all(str(r.get("pstSn") or "") != TARGET_PST for r in unresolved),
        "remaining arithmetic valid": state["remaining_count"] == era_count - state["processed_count"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("XLS state reconciliation failed")


if __name__ == "__main__":
    main()
