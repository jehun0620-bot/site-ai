# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S38
Reconcile the validated S37 targeted diagnostics into the cumulative dynamic-HWP state.

This is a narrow state mutation step. It only accepts the exact three rows diagnosed
by S37:
- pstSn 29253 / Gazette 1082: high-signal word occurs only in general redevelopment
  planning context, with zero direct UQQ700 term -> CONTEXTUAL_NON_UQQ700.
- pstSn 29257 / Gazette 1086: high-limit HWP5 extraction recovered successfully,
  no direct/high-signal UQQ700 term -> NO_TERM_IN_EXTRACTED_SAMPLE.
- pstSn 29263 / Gazette 1091: same recovery semantics.

Gazette 938 (pstSn 29098) remains TECHNICAL_UNRESOLVED_QUARANTINED and unprocessed.
No negative legal inference or legal/SITE promotion is permitted.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
DIAG = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_candidate_unresolved_diagnostic.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_s37_state_reconciliation.json"

TARGET_CONTEXTUAL = "29253"
TARGET_RECOVERED = {"29257", "29263"}
QUARANTINE = {"29098"}
EXPECTED_TARGETS = {TARGET_CONTEXTUAL} | TARGET_RECOVERED
CONTEXT_MARKERS = ("정비계획 수립시 개발밀도 증가에 따른 환경계획 수립", "개발밀도 증가에 따른 환경계획")


def norm_pst(v: Any) -> str:
    return hwp5.norm(v)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("S37 DIAGNOSTIC STATE RECONCILIATION")
    print("=" * 60)
    print("Allowed state mutation: S37 exact rows only")
    print("Legal negative evidence: DISABLED")
    print("Legal/SITE promotion: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not DIAG.exists():
        raise FileNotFoundError(DIAG)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    diag = json.loads(DIAG.read_text(encoding="utf-8"))
    diagnostics = diag.get("diagnostics") or []
    by_pst = {norm_pst(r.get("pstSn")): r for r in diagnostics if norm_pst(r.get("pstSn"))}

    if set(by_pst) != EXPECTED_TARGETS:
        raise AssertionError(f"unexpected S37 target set: {sorted(by_pst)}")
    if diag.get("state_mutation_allowed") is not False:
        raise AssertionError("S37 diagnostic must have state mutation disabled")
    if diag.get("negative_evidence_allowed") is not False:
        raise AssertionError("S37 diagnostic must have negative evidence disabled")
    if diag.get("legal_promotion_allowed") is not False:
        raise AssertionError("S37 diagnostic must have legal promotion disabled")

    contextual = by_pst[TARGET_CONTEXTUAL]
    direct = contextual.get("direct_matches") or {}
    high = contextual.get("high_signal_related_matches") or {}
    contexts = contextual.get("contexts") or []
    joined_context = " ".join(str(c.get("context") or "") for c in contexts)
    contextual_ok = (
        contextual.get("status") == "RELATED_CANDIDATE"
        and not any(int(v or 0) for v in direct.values())
        and int(high.get("개발밀도") or 0) > 0
        and any(marker in joined_context for marker in CONTEXT_MARKERS)
    )
    if not contextual_ok:
        raise AssertionError("Gazette 1082 contextual non-UQQ700 evidence not sufficient")

    for pst in TARGET_RECOVERED:
        r = by_pst[pst]
        if r.get("prior_status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
            raise AssertionError(f"{pst}: prior status was not unresolved")
        if r.get("status") != "NO_TERM_IN_EXTRACTED_SAMPLE":
            raise AssertionError(f"{pst}: high-limit recovery did not finish as no-term")
        if not r.get("extract_ok"):
            raise AssertionError(f"{pst}: extraction not successful")
        if any(int(v or 0) for v in (r.get("direct_matches") or {}).values()):
            raise AssertionError(f"{pst}: unexpected direct UQQ700 term")
        if any(int(v or 0) for v in (r.get("high_signal_related_matches") or {}).values()):
            raise AssertionError(f"{pst}: unexpected high-signal term")

    prior_results = state.get("results") or []
    prior_by_pst = {norm_pst(r.get("pstSn")): r for r in prior_results if norm_pst(r.get("pstSn"))}
    for pst in EXPECTED_TARGETS | QUARANTINE:
        if pst not in prior_by_pst:
            raise AssertionError(f"required state row missing: {pst}")

    replacements: Dict[str, Dict[str, Any]] = {}

    c = dict(prior_by_pst[TARGET_CONTEXTUAL])
    c.update({
        "status": "CONTEXTUAL_NON_UQQ700",
        "candidate_disposition": "GENERAL_REDEVELOPMENT_PLANNING_CONTEXT",
        "candidate_disposition_basis": "S37_CONTEXT_REVIEW",
        "legal_negative_evidence": False,
        "verified_positive": False,
    })
    replacements[TARGET_CONTEXTUAL] = c

    for pst in TARGET_RECOVERED:
        old = prior_by_pst[pst]
        d = by_pst[pst]
        merged = dict(old)
        for key in [
            "metadata_http", "metadata_url", "attachment", "download_http", "download_url",
            "download_bytes", "signature_class", "parser_used", "extract_ok", "extract_error",
            "text_chars", "sections", "direct_matches", "high_signal_related_matches", "contexts",
        ]:
            if key in d:
                merged[key] = d[key]
        merged.update({
            "status": "NO_TERM_IN_EXTRACTED_SAMPLE",
            "error": "",
            "recovered_by": "S37_HWP5_HIGH_RECORD_LIMIT_RETRY",
            "legal_negative_evidence": False,
            "verified_positive": False,
        })
        replacements[pst] = merged

    new_results: List[Dict[str, Any]] = []
    replaced = set()
    for r in prior_results:
        pst = norm_pst(r.get("pstSn"))
        if pst in replacements:
            if pst not in replaced:
                new_results.append(replacements[pst])
                replaced.add(pst)
        else:
            new_results.append(r)

    processed = list(dict.fromkeys(
        norm_pst(r.get("pstSn")) for r in new_results
        if norm_pst(r.get("pstSn"))
        and r.get("status") not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}
    ))
    quarantined = [r for r in new_results if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED"]
    unresolved = [r for r in new_results if r.get("status") in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}]
    candidates = [r for r in new_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]

    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in new_results:
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    era_count = int(state.get("era_row_count") or 0)
    remaining = era_count - len(processed) - len(quarantined)
    new_state = dict(state)
    new_state.update({
        "processed_count": len(processed),
        "remaining_count": remaining,
        "quarantined_count": len(quarantined),
        "processed_pstSn": processed,
        "quarantined_pstSn": [norm_pst(r.get("pstSn")) for r in quarantined],
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "results": new_results,
        "negative_evidence_allowed": False,
        "last_reconciliation": "S38_FROM_S37_DIAGNOSTIC",
    })
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S38",
        "reconciled_pstSn": sorted(EXPECTED_TARGETS),
        "contextual_non_uqq700_pstSn": TARGET_CONTEXTUAL,
        "recovered_no_term_pstSn": sorted(TARGET_RECOVERED),
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
        "S37 exact targets reconciled": replaced == EXPECTED_TARGETS,
        "Gazette1082 contextual disposition": replacements[TARGET_CONTEXTUAL]["status"] == "CONTEXTUAL_NON_UQQ700",
        "Gazette1086 recovered": replacements["29257"]["status"] == "NO_TERM_IN_EXTRACTED_SAMPLE",
        "Gazette1091 recovered": replacements["29263"]["status"] == "NO_TERM_IN_EXTRACTED_SAMPLE",
        "candidate count cleared": len(candidates) == 0,
        "quarantine retained": QUARANTINE.issubset(set(new_state["quarantined_pstSn"])),
        "quarantine not processed": not (QUARANTINE & set(processed)),
        "only quarantine unresolved": len(unresolved) == len(QUARANTINE) and all(norm_pst(r.get("pstSn")) in QUARANTINE for r in unresolved),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Reconciled:", sorted(EXPECTED_TARGETS))
    print("Contextual non-UQQ700:", TARGET_CONTEXTUAL)
    print("Recovered no-term:", sorted(TARGET_RECOVERED))
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
        raise AssertionError("S37 state reconciliation validation failed")


if __name__ == "__main__":
    main()
