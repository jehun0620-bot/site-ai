# -*- coding: utf-8 -*-
"""S59: report current non-quarantine EXTRACTION_OR_REQUEST_UNKNOWN rows from cumulative state."""
from __future__ import annotations
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
STATE = BASE / "law_data" / "output" / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = BASE / "law_data" / "output" / "development_density_management_area_municipal_gazette_current_nonquarantine_unknown_probe.json"


def norm(v):
    return str(v or "").strip()


def main():
    print("=" * 60)
    print("CURRENT NON-QUARANTINE UNKNOWN PROBE - S59")
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
    unknowns = [
        r for r in rows
        if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"
        and norm(r.get("pstSn")) not in quarantine
    ]
    slim = []
    for r in unknowns:
        slim.append({k: r.get(k) for k in [
            "gazette_number", "date", "pstSn", "signature_class", "parser_used",
            "metadata_http", "attachment", "download_http", "download_bytes",
            "extract_ok", "extract_error", "text_chars", "error"
        ]})
    output = {
        "step": "STEP 17-21-C-16-8-T-34-S59",
        "unknown_count": len(unknowns),
        "quarantine_pstSn": sorted(quarantine),
        "unknown_rows": slim,
        "network_request_count": 0,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Quarantine:", sorted(quarantine))
    print("Non-quarantine unknown count:", len(unknowns))
    for i, rec in enumerate(slim, 1):
        print(f"UNKNOWN {i}:", rec)
    print("Output:", OUT)
    unsafe = any(output[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"])
    vals = {
        "state exists": STATE.exists(),
        "exactly one non-quarantine unknown": len(unknowns) == 1,
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
        raise AssertionError("current non-quarantine unknown probe failed")


if __name__ == "__main__":
    main()
