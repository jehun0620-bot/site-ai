# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S55
Reconcile Gazette 1597 / 1598 isolated attachment orphans into technical quarantine.

Evidence chain:
- S51: official attachment metadata endpoint returned HTTP 200 + JSON, but 0 attachments for both exact targets;
- S53: detail pages contain only dynamic attachment plumbing and no concrete fileNo / filename;
- S54: six neighboring gazettes all return attachment_count=1 while both exact targets alone return 0.

Safety:
- no network;
- exact targets only;
- classify as TECHNICAL_UNRESOLVED_QUARANTINED, never legal FALSE;
- preserve all existing quarantine rows;
- no negative evidence or SITE/runtime promotion.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
TOPOLOGY = OUT_DIR / "development_density_management_area_municipal_gazette_1597_1598_attachment_topology_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1597_1598_orphan_quarantine_reconciliation.json"
TARGETS = {"181109", "181376"}
REASON = "OFFICIAL_DETAIL_PRESENT_BUT_ATTACHMENT_METADATA_EMPTY_WHILE_ALL_CHECKED_NEIGHBORING_GAZETTES_HAVE_ATTACHMENTS"


def norm(v):
    return str(v or "").strip()


def main() -> None:
    print("=" * 60)
    print("GAZETTE 1597 / 1598 ORPHAN QUARANTINE RECONCILIATION")
    print("=" * 60)
    print("Targets:", sorted(TARGETS))
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not TOPOLOGY.exists():
        raise FileNotFoundError(TOPOLOGY)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    topo = json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    summary = topo.get("summary") or {}
    if set(topo.get("targets") or []) != TARGETS:
        raise AssertionError("topology target mismatch")
    if not summary.get("target_all_empty"):
        raise AssertionError("targets are not both empty in topology evidence")
    if not summary.get("neighbors_all_transport_ok"):
        raise AssertionError("neighbor transport evidence incomplete")
    if int(summary.get("neighbor_nonempty_count") or 0) <= 0:
        raise AssertionError("no neighboring attachment evidence")
    if int(summary.get("neighbor_empty_count") or 0) != 0:
        raise AssertionError("neighbor empty metadata found; do not quarantine as isolated orphan")
    if not summary.get("local_orphan_pattern"):
        raise AssertionError("local orphan pattern not established")

    results = state.get("results") or []
    before_rows = {pst: [r for r in results if norm(r.get("pstSn")) == pst] for pst in TARGETS}
    for pst, rows in before_rows.items():
        if len(rows) != 1:
            raise AssertionError(f"expected one row for {pst}, got {len(rows)}")
        if rows[0].get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
            raise AssertionError(f"unexpected prior status for {pst}: {rows[0].get('status')}")
        if "HWP attachment not found" not in norm(rows[0].get("error")):
            raise AssertionError(f"unexpected prior error for {pst}: {rows[0].get('error')}")

    prior_existing_quarantine = {
        norm(r.get("pstSn")) for r in results
        if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED" and norm(r.get("pstSn"))
    }

    for pst in TARGETS:
        row = before_rows[pst][0]
        row["status"] = "TECHNICAL_UNRESOLVED_QUARANTINED"
        row["quarantine_reason"] = REASON
        row["legal_negative_evidence"] = False

    processed_status_exclusions = {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}
    processed = [
        norm(r.get("pstSn")) for r in results
        if norm(r.get("pstSn")) and r.get("status") not in processed_status_exclusions
    ]
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

    post_target_rows = {pst: [r for r in results if norm(r.get("pstSn")) == pst] for pst in TARGETS}
    post_quarantine = {
        norm(r.get("pstSn")) for r in results
        if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED" and norm(r.get("pstSn"))
    }

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S55",
        "targets": sorted(TARGETS),
        "prior_status": "EXTRACTION_OR_REQUEST_UNKNOWN",
        "new_status": "TECHNICAL_UNRESOLVED_QUARANTINED",
        "quarantine_reason": REASON,
        "prior_existing_quarantine": sorted(prior_existing_quarantine),
        "post_quarantine": sorted(post_quarantine),
        "processed_count_after": state["processed_count"],
        "quarantined_count_after": state["quarantined_count"],
        "remaining_count_after": state["remaining_count"],
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

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "targets uniquely retained": all(len(post_target_rows[p]) == 1 for p in TARGETS),
        "targets quarantined": all(post_target_rows[p][0].get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED" for p in TARGETS),
        "quarantine reason retained": all(post_target_rows[p][0].get("quarantine_reason") == REASON for p in TARGETS),
        "existing quarantine preserved": prior_existing_quarantine.issubset(post_quarantine),
        "targets not processed": TARGETS.isdisjoint(set(state["processed_pstSn"])),
        "candidate count zero": state["candidate_count"] == 0,
        "no retryable unknown remains for targets": all(post_target_rows[p][0].get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN" for p in TARGETS),
        "state arithmetic valid": state["processed_count"] + state["quarantined_count"] + state["remaining_count"] == state["era_row_count"],
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Processed:", state["processed_count"])
    print("Quarantined:", state["quarantined_count"], state["quarantined_pstSn"])
    print("Remaining:", state["remaining_count"])
    print("Candidates:", state["candidate_count"])
    print("Unresolved:", state["unresolved_count"])
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1597/1598 orphan quarantine reconciliation failed")


if __name__ == "__main__":
    main()
