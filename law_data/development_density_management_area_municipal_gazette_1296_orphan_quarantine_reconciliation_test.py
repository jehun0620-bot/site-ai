# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S47
Reconcile Gazette 1296 / pstSn 29471 isolated empty-attachment metadata into cumulative state.

Safety:
- exact target only;
- requires S46 isolated_empty_pattern == True;
- preserves Gazette 938 quarantine;
- classifies Gazette 1296 as technical unresolved quarantine, not legal FALSE;
- no network requests;
- no legal negative evidence or SITE/runtime promotion.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
S46 = OUT_DIR / "development_density_management_area_municipal_gazette_1296_attachment_topology_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1296_orphan_quarantine_reconciliation.json"

TARGET_PST = "29471"
EXISTING_QUARANTINE_PST = "29098"


def norm(v: Any) -> str:
    return str(v or "").strip()


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1296 ORPHAN QUARANTINE RECONCILIATION")
    print("=" * 60)
    print("Target pstSn:", TARGET_PST)
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not S46.exists():
        raise FileNotFoundError(S46)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    s46 = json.loads(S46.read_text(encoding="utf-8"))

    if norm(s46.get("target_pstSn")) != TARGET_PST:
        raise AssertionError("S46 target mismatch")
    summary = s46.get("summary") or {}
    if not summary.get("target_empty_metadata"):
        raise AssertionError("S46 target metadata is not empty")
    if not summary.get("neighbor_all_transport_ok"):
        raise AssertionError("S46 neighbor transport validation failed")
    if int(summary.get("neighbor_nonempty_count") or 0) < 2:
        raise AssertionError("S46 insufficient nonempty neighbors")
    if not summary.get("isolated_empty_pattern"):
        raise AssertionError("S46 did not establish isolated empty pattern")
    if s46.get("attachment_body_download_executed"):
        raise AssertionError("S46 unexpectedly downloaded attachment body")
    if s46.get("state_mutation_allowed"):
        raise AssertionError("S46 unexpectedly allowed state mutation")
    if s46.get("negative_evidence_allowed"):
        raise AssertionError("S46 unexpectedly allowed negative evidence")

    results = state.get("results") or []
    matches = [r for r in results if norm(r.get("pstSn")) == TARGET_PST]
    if len(matches) != 1:
        raise AssertionError(f"state target cardinality mismatch: {len(matches)}")
    prior = matches[0]
    if prior.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
        raise AssertionError(f"state prior status mismatch: {prior.get('status')}")

    reconciled: Dict[str, Any] = dict(prior)
    reconciled.update({
        "status": "TECHNICAL_UNRESOLVED_QUARANTINED",
        "signature_class": prior.get("signature_class") or "UNKNOWN",
        "parser_used": prior.get("parser_used") or "LEGACY_UNKNOWN",
        "extract_ok": False,
        "extract_error": prior.get("extract_error") or "",
        "error": "ISOLATED_EMPTY_ATTACHMENT_METADATA",
        "quarantine_reason": "OFFICIAL_DETAIL_PRESENT_BUT_ATTACHMENT_METADATA_EMPTY_WHILE_NEIGHBORING_GAZETTES_HAVE_ATTACHMENTS",
        "quarantined_by": "S46_ATTACHMENT_TOPOLOGY_PROBE",
        "technical_orphan": True,
        "legal_negative_evidence": False,
    })

    new_results = [reconciled if norm(r.get("pstSn")) == TARGET_PST else r for r in results]

    processed = []
    seen = set()
    candidates = []
    unresolved = []
    quarantined = []
    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}

    for r in new_results:
        pst = norm(r.get("pstSn"))
        status = r.get("status")
        if pst and status not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"} and pst not in seen:
            seen.add(pst)
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
    new_state = dict(state)
    new_state.update({
        "processed_count": len(processed),
        "remaining_count": era_count - len(processed) - len(quarantined),
        "quarantined_count": len(quarantined),
        "processed_pstSn": processed,
        "quarantined_pstSn": [norm(r.get("pstSn")) for r in quarantined],
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "results": new_results,
        "negative_evidence_allowed": False,
    })
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S47",
        "target_pstSn": TARGET_PST,
        "prior_status": prior.get("status"),
        "new_status": reconciled.get("status"),
        "quarantine_reason": reconciled.get("quarantine_reason"),
        "network_request_count": 0,
        "state_mutation_scope": [TARGET_PST],
        "summary": {
            "processed_count": new_state["processed_count"],
            "remaining_count": new_state["remaining_count"],
            "quarantined_count": new_state["quarantined_count"],
            "quarantined_pstSn": new_state["quarantined_pstSn"],
            "candidate_count": new_state["candidate_count"],
            "unresolved_count": new_state["unresolved_count"],
            "signature_counts": new_state["signature_counts"],
            "parser_counts": new_state["parser_counts"],
        },
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    qset = set(new_state["quarantined_pstSn"])
    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "state exists": STATE.exists(),
        "S46 exists": S46.exists(),
        "exact target only": output["state_mutation_scope"] == [TARGET_PST],
        "prior target was unresolved": prior.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN",
        "isolated empty pattern established": bool(summary.get("isolated_empty_pattern")),
        "target now quarantined": TARGET_PST in qset,
        "Gazette 938 quarantine retained": EXISTING_QUARANTINE_PST in qset,
        "both quarantines present": {EXISTING_QUARANTINE_PST, TARGET_PST}.issubset(qset),
        "target not processed": TARGET_PST not in processed,
        "Gazette 938 not processed": EXISTING_QUARANTINE_PST not in processed,
        "candidate count zero": len(candidates) == 0,
        "unresolved equals quarantines": len(unresolved) == len(quarantined) == 2,
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Prior status:", prior.get("status"))
    print("New status:", reconciled.get("status"))
    print("Quarantine reason:", reconciled.get("quarantine_reason"))
    print("\nSUMMARY")
    print("Cumulative processed:", new_state["processed_count"])
    print("Quarantined:", new_state["quarantined_count"], new_state["quarantined_pstSn"])
    print("Remaining searchable:", new_state["remaining_count"])
    print("Candidates:", new_state["candidate_count"])
    print("Unresolved total:", new_state["unresolved_count"])
    print("Signature counts:", signature_counts)
    print("Parser counts:", parser_counts)
    print("State:", STATE)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1296 orphan quarantine reconciliation failed")


if __name__ == "__main__":
    main()
