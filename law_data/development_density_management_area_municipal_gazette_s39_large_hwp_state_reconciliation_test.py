# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S40
Reconcile the exact three successful S39 oversized-HWP recoveries into the
shared cumulative dynamic-HWP state.

No network calls. No legal/SITE promotion. No negative-evidence inference.
Gazette 938 / pstSn 29098 remains quarantined.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
S39 = OUT_DIR / "development_density_management_area_municipal_gazette_large_hwp_targeted_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_s39_large_hwp_state_reconciliation.json"

TARGETS = {"29332", "29333", "29336"}
QUARANTINE = {"29098"}


def norm(v: Any) -> str:
    return hwp5.norm(v)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("S39 LARGE-HWP STATE RECONCILIATION")
    print("=" * 60)
    print("Exact reconciliation targets:", sorted(TARGETS))
    print("Negative evidence: DISABLED")
    print("Legal/SITE promotion: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not S39.exists():
        raise FileNotFoundError(S39)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    s39 = json.loads(S39.read_text(encoding="utf-8"))

    if s39.get("state_mutation_allowed") is not False:
        raise AssertionError("S39 state mutation flag must be disabled")
    if s39.get("negative_evidence_allowed") is not False:
        raise AssertionError("S39 negative evidence flag must be disabled")
    if s39.get("legal_promotion_allowed") is not False:
        raise AssertionError("S39 legal promotion flag must be disabled")

    recovered = {norm(r.get("pstSn")): r for r in (s39.get("results") or []) if norm(r.get("pstSn"))}
    if set(recovered) != TARGETS:
        raise AssertionError(f"unexpected S39 target set: {sorted(recovered)}")

    for pst, r in recovered.items():
        if r.get("prior_status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
            raise AssertionError(f"{pst}: prior status mismatch")
        if r.get("status") != "NO_TERM_IN_EXTRACTED_SAMPLE":
            raise AssertionError(f"{pst}: not recovered as no-term")
        if r.get("download_http") != 200:
            raise AssertionError(f"{pst}: download not HTTP 200")
        if r.get("signature_class") != "HWP5":
            raise AssertionError(f"{pst}: unexpected signature")
        if not r.get("extract_ok"):
            raise AssertionError(f"{pst}: extraction failed")
        if any(int(v or 0) for v in (r.get("direct_matches") or {}).values()):
            raise AssertionError(f"{pst}: direct candidate term present")
        if any(int(v or 0) for v in (r.get("high_signal_related_matches") or {}).values()):
            raise AssertionError(f"{pst}: high-signal candidate term present")

    prior_results = state.get("results") or []
    prior_map = {norm(r.get("pstSn")): r for r in prior_results if norm(r.get("pstSn"))}
    if not TARGETS.issubset(prior_map):
        raise AssertionError("one or more S39 targets missing from cumulative state")
    if not QUARANTINE.issubset(prior_map):
        raise AssertionError("Gazette 938 quarantine row missing from cumulative state")

    replacements: Dict[str, Dict[str, Any]] = {}
    for pst in TARGETS:
        old = dict(prior_map[pst])
        d = recovered[pst]
        for key in [
            "metadata_http", "metadata_url", "attachment", "download_http", "download_url",
            "download_bytes", "signature_class", "parser_used", "extract_ok", "extract_error",
            "text_chars", "sections", "direct_matches", "high_signal_related_matches", "contexts",
        ]:
            if key in d:
                old[key] = d[key]
        old.update({
            "status": "NO_TERM_IN_EXTRACTED_SAMPLE",
            "error": "",
            "recovered_by": "S39_LARGE_FILE_64M_HIGH_RECORD_LIMIT",
            "legal_negative_evidence": False,
            "verified_positive": False,
        })
        replacements[pst] = old

    new_results: List[Dict[str, Any]] = []
    replaced = set()
    for r in prior_results:
        pst = norm(r.get("pstSn"))
        if pst in replacements:
            if pst not in replaced:
                new_results.append(replacements[pst])
                replaced.add(pst)
        else:
            new_results.append(r)

    processed = list(dict.fromkeys(
        norm(r.get("pstSn")) for r in new_results
        if norm(r.get("pstSn"))
        and r.get("status") not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}
    ))
    candidates = [r for r in new_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in new_results if r.get("status") in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}]
    quarantined = [r for r in new_results if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED"]

    sig_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in new_results:
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        sig_counts[sig] = sig_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    era_count = int(state.get("era_row_count") or 0)
    remaining = era_count - len(processed) - len(quarantined)
    new_state = dict(state)
    new_state.update({
        "processed_count": len(processed),
        "remaining_count": remaining,
        "quarantined_count": len(quarantined),
        "processed_pstSn": processed,
        "quarantined_pstSn": [norm(r.get("pstSn")) for r in quarantined],
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": sig_counts,
        "parser_counts": parser_counts,
        "results": new_results,
        "negative_evidence_allowed": False,
        "last_reconciliation": "S40_FROM_S39_LARGE_HWP_RECOVERY",
    })
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S40",
        "reconciled_pstSn": sorted(TARGETS),
        "processed_count": len(processed),
        "remaining_count": remaining,
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "quarantined_pstSn": new_state["quarantined_pstSn"],
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
        "exact S39 targets reconciled": replaced == TARGETS,
        "all three recovered no-term": all(replacements[p]["status"] == "NO_TERM_IN_EXTRACTED_SAMPLE" for p in TARGETS),
        "candidate count zero": len(candidates) == 0,
        "Gazette938 quarantine retained": QUARANTINE.issubset(set(new_state["quarantined_pstSn"])),
        "Gazette938 not processed": not (QUARANTINE & set(processed)),
        "only quarantine unresolved": len(unresolved) == 1 and norm(unresolved[0].get("pstSn")) == "29098",
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Reconciled:", sorted(TARGETS))
    print("Cumulative processed:", len(processed))
    print("Quarantined:", len(quarantined), new_state["quarantined_pstSn"])
    print("Remaining searchable:", remaining)
    print("Candidates:", len(candidates))
    print("Unresolved total:", len(unresolved))
    print("State:", STATE)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("S39 state reconciliation validation failed")


if __name__ == "__main__":
    main()
