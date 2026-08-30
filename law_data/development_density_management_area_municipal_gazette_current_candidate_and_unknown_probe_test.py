# -*- coding: utf-8 -*-
"""S64: report current candidate rows and non-quarantine unknown rows from cumulative state."""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATE = BASE / "law_data" / "output" / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_municipal_gazette_current_candidate_and_unknown_probe.json"


def norm(v):
    return str(v or "").strip()


def slim(r):
    keys = [
        "gazette_number", "date", "pstSn", "status", "signature_class", "parser_used",
        "metadata_http", "attachment", "download_http", "download_bytes",
        "extract_ok", "extract_error", "text_chars", "direct_matches",
        "related_matches", "high_signal_related_matches", "low_signal_related_matches", "error",
    ]
    return {k: r.get(k) for k in keys}


def main():
    print("=" * 60)
    print("CURRENT CANDIDATE + NON-QUARANTINE UNKNOWN PROBE - S64")
    print("=" * 60)
    print("Network: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")
    if not STATE.exists():
        raise FileNotFoundError(STATE)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    rows = state.get("results") or []
    quarantine = {
        norm(r.get("pstSn")) for r in rows
        if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED" and norm(r.get("pstSn"))
    }
    candidates = [r for r in rows if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unknowns = [
        r for r in rows
        if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"
        and norm(r.get("pstSn")) not in quarantine
    ]
    candidate_rows = [slim(r) for r in candidates]
    unknown_rows = [slim(r) for r in unknowns]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S64",
        "candidate_count": len(candidate_rows),
        "nonquarantine_unknown_count": len(unknown_rows),
        "quarantine_pstSn": sorted(quarantine),
        "candidate_rows": candidate_rows,
        "unknown_rows": unknown_rows,
        "network_request_count": 0,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Quarantine:", sorted(quarantine))
    print("Candidate count:", len(candidate_rows))
    for i, rec in enumerate(candidate_rows, 1):
        print(f"CANDIDATE {i}:", rec)
    print("Non-quarantine unknown count:", len(unknown_rows))
    for i, rec in enumerate(unknown_rows, 1):
        print(f"UNKNOWN {i}:", rec)
    print("Output:", OUT)

    unsafe = any(output[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"])
    vals = {
        "state exists": STATE.exists(),
        "candidate count matches state": len(candidate_rows) == int(state.get("candidate_count") or 0),
        "unresolved arithmetic matches": len(unknown_rows) + len(quarantine) == int(state.get("unresolved_count") or 0),
        "network disabled": output["network_request_count"] == 0,
        "state mutation disabled": not output["state_mutation_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("current candidate and unknown probe failed")


if __name__ == "__main__":
    main()
