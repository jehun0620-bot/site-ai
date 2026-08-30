# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S52
Reconcile Gazette 1606 / pstSn 183149 RELATED_CANDIDATE after context review.

Context showed generic urban-renewal planning language about appropriate development density,
not a designation/change/notice for 개발밀도관리구역 (UQQ700).

Safety:
- no network;
- exact target only;
- candidate -> CONTEXTUAL_NON_UQQ700 only;
- no legal negative evidence;
- no SITE/runtime promotion.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
PROBE = OUT_DIR / "development_density_management_area_municipal_gazette_1606_related_candidate_context_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1606_candidate_reconciliation.json"
TARGET = "183149"


def norm(v):
    return str(v or "").strip()


def main() -> None:
    print("=" * 60)
    print("GAZETTE 1606 CANDIDATE RECONCILIATION")
    print("=" * 60)
    print("Target pstSn:", TARGET)
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not PROBE.exists():
        raise FileNotFoundError(PROBE)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    probe = json.loads(PROBE.read_text(encoding="utf-8"))
    contexts = probe.get("contexts") or []
    if probe.get("target", {}).get("pstSn") != TARGET:
        raise AssertionError("probe target mismatch")
    if probe.get("term_count") != 1 or not contexts:
        raise AssertionError("expected exactly one recovered context")

    rows = [r for r in state.get("results", []) if norm(r.get("pstSn")) == TARGET]
    if len(rows) != 1:
        raise AssertionError(f"expected one state row for target, got {len(rows)}")
    row = rows[0]
    if row.get("status") != "RELATED_CANDIDATE":
        raise AssertionError(f"unexpected prior status: {row.get('status')}")
    if any((row.get("direct_matches") or {}).values()):
        raise AssertionError("direct UQQ700 term unexpectedly present")

    row["status"] = "CONTEXTUAL_NON_UQQ700"
    row["candidate_reconciliation_reason"] = (
        "RELATED_TERM_IS_GENERIC_REDEVELOPMENT_PLAN_LANGUAGE_ABOUT_APPROPRIATE_DEVELOPMENT_DENSITY; "
        "NO_UQQ700_DESIGNATION_CHANGE_NOTICE_CONTEXT"
    )
    row["legal_negative_evidence"] = False

    results = state.get("results") or []
    processed = [norm(r.get("pstSn")) for r in results if norm(r.get("pstSn")) and r.get("status") not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}]
    quarantined = [r for r in results if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED"]
    candidates = [r for r in results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in results if r.get("status") in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}]
    state["processed_pstSn"] = list(dict.fromkeys(processed))
    state["processed_count"] = len(state["processed_pstSn"])
    state["quarantined_pstSn"] = [norm(r.get("pstSn")) for r in quarantined]
    state["quarantined_count"] = len(quarantined)
    state["candidate_count"] = len(candidates)
    state["unresolved_count"] = len(unresolved)
    state["remaining_count"] = int(state.get("era_row_count") or 0) - state["processed_count"] - state["quarantined_count"]
    state["negative_evidence_allowed"] = False
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S52",
        "target_pstSn": TARGET,
        "prior_status": "RELATED_CANDIDATE",
        "new_status": row["status"],
        "reason": row["candidate_reconciliation_reason"],
        "candidate_count_after": state["candidate_count"],
        "unresolved_count_after": state["unresolved_count"],
        "network_request_count": 0,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any(output[k] for k in ["verified_positive", "runtime_registration_allowed", "site_positive_allowed", "site_negative_allowed", "final_positive_promotion_allowed"])
    vals = {
        "target reconciled": row["status"] == "CONTEXTUAL_NON_UQQ700",
        "candidate removed": TARGET not in {norm(r.get("pstSn")) for r in candidates},
        "candidate count zero": state["candidate_count"] == 0,
        "target remains processed": TARGET in set(state["processed_pstSn"]),
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state arithmetic valid": state["processed_count"] + state["quarantined_count"] + state["remaining_count"] == state["era_row_count"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("Prior status: RELATED_CANDIDATE")
    print("New status:", row["status"])
    print("Candidates after:", state["candidate_count"])
    print("Unresolved after:", state["unresolved_count"])
    print("Processed:", state["processed_count"])
    print("Quarantined:", state["quarantined_count"], state["quarantined_pstSn"])
    print("Remaining:", state["remaining_count"])
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1606 candidate reconciliation failed")


if __name__ == "__main__":
    main()
