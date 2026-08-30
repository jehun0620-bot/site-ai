# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S48
Repair duplicate cumulative-state rows created when a dynamically quarantined
pstSn was re-selected by S36-H2.

Safety:
- no network;
- no legal negative evidence;
- quarantine wins over duplicate retryable UNKNOWN for the same pstSn;
- does not promote SITE/runtime truth.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_duplicate_quarantine_state_repair.json"
TARGET_PST = "29471"
EXPECTED_OTHER_QUARANTINE = "29098"


def norm(v: Any) -> str:
    return str(v or "").strip()


def priority(r: Dict[str, Any]) -> int:
    status = r.get("status")
    if status == "TECHNICAL_UNRESOLVED_QUARANTINED":
        return 100
    if status in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}:
        return 90
    if status in {"NO_TERM_IN_EXTRACTED_SAMPLE", "CONTEXTUAL_TERM_NOT_UQQ700_CANDIDATE", "CONTEXTUAL_NON_UQQ700"}:
        return 80
    if status == "EXTRACTION_OR_REQUEST_UNKNOWN":
        return 10
    return 0


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("DUPLICATE QUARANTINE STATE REPAIR")
    print("=" * 60)
    print("Target pstSn:", TARGET_PST)
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    results: List[Dict[str, Any]] = list(state.get("results") or [])

    target_before = [r for r in results if norm(r.get("pstSn")) == TARGET_PST]
    if len(target_before) < 2:
        raise AssertionError(f"expected duplicate target rows, got {len(target_before)}")
    if not any(r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED" for r in target_before):
        raise AssertionError("target quarantine row missing")
    if not any(r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN" for r in target_before):
        raise AssertionError("target duplicate UNKNOWN row missing")

    chosen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []
    duplicates_removed = 0
    for r in results:
        pst = norm(r.get("pstSn"))
        if not pst:
            continue
        if pst not in chosen:
            chosen[pst] = r
            order.append(pst)
        else:
            duplicates_removed += 1
            if priority(r) > priority(chosen[pst]):
                chosen[pst] = r

    repaired_results = [chosen[p] for p in order]
    target_after = [r for r in repaired_results if norm(r.get("pstSn")) == TARGET_PST]
    if len(target_after) != 1 or target_after[0].get("status") != "TECHNICAL_UNRESOLVED_QUARANTINED":
        raise AssertionError("target did not resolve to single quarantine row")

    processed = []
    candidates = []
    unresolved = []
    quarantined = []
    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}

    for r in repaired_results:
        pst = norm(r.get("pstSn"))
        status = r.get("status")
        if pst and status not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}:
            processed.append(pst)
        if status in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}:
            candidates.append(r)
        if status in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}:
            unresolved.append(r)
        if status == "TECHNICAL_UNRESOLVED_QUARANTINED":
            quarantined.append(r)
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    era_count = int(state.get("era_row_count") or 0)
    q_pst = [norm(r.get("pstSn")) for r in quarantined]
    repaired = dict(state)
    repaired.update({
        "processed_count": len(processed),
        "remaining_count": era_count - len(processed) - len(quarantined),
        "quarantined_count": len(quarantined),
        "processed_pstSn": processed,
        "quarantined_pstSn": q_pst,
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "results": repaired_results,
        "negative_evidence_allowed": False,
    })
    STATE.write_text(json.dumps(repaired, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S48",
        "target_pstSn": TARGET_PST,
        "rows_before": len(results),
        "rows_after": len(repaired_results),
        "duplicates_removed": duplicates_removed,
        "target_status_after": target_after[0].get("status"),
        "summary": {
            "processed_count": repaired["processed_count"],
            "quarantined_count": repaired["quarantined_count"],
            "quarantined_pstSn": repaired["quarantined_pstSn"],
            "remaining_count": repaired["remaining_count"],
            "candidate_count": repaired["candidate_count"],
            "unresolved_count": repaired["unresolved_count"],
        },
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "duplicate removed": duplicates_removed >= 1,
        "target unique": len(target_after) == 1,
        "target quarantine retained": TARGET_PST in q_pst,
        "Gazette 938 quarantine retained": EXPECTED_OTHER_QUARANTINE in q_pst,
        "target not processed": TARGET_PST not in processed,
        "quarantine count two": len(quarantined) == 2,
        "unresolved count two": len(unresolved) == 2,
        "candidate count zero": len(candidates) == 0,
        "state arithmetic valid": len(processed) + len(quarantined) + repaired["remaining_count"] == era_count,
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Rows before:", len(results))
    print("Rows after:", len(repaired_results))
    print("Duplicates removed:", duplicates_removed)
    print("Target status after:", target_after[0].get("status"))
    print("\nSUMMARY")
    print("Cumulative processed:", repaired["processed_count"])
    print("Quarantined:", repaired["quarantined_count"], repaired["quarantined_pstSn"])
    print("Remaining searchable:", repaired["remaining_count"])
    print("Candidates:", repaired["candidate_count"])
    print("Unresolved total:", repaired["unresolved_count"])
    print("State:", STATE)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("duplicate quarantine state repair failed")


if __name__ == "__main__":
    main()
