# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S43
Reconcile Gazette 1241 / pstSn 29416 PDF-text recovery into cumulative state.

Safety:
- exact target only;
- requires S42 NO_TERM_IN_EXTRACTED_PDF_TEXT with valid PDF/text extraction;
- preserves Gazette 938 quarantine;
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
S42 = OUT_DIR / "development_density_management_area_municipal_gazette_1241_pdf_text_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1241_pdf_state_reconciliation.json"

TARGET_PST = "29416"
QUARANTINE_PST = "29098"
EXPECTED_STATUS = "NO_TERM_IN_EXTRACTED_PDF_TEXT"


def norm(v: Any) -> str:
    return str(v or "").strip()


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1241 PDF STATE RECONCILIATION")
    print("=" * 60)
    print("Target pstSn:", TARGET_PST)
    print("Network: DISABLED")
    print("Negative evidence: DISABLED")

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    if not S42.exists():
        raise FileNotFoundError(S42)

    state = json.loads(STATE.read_text(encoding="utf-8"))
    s42 = json.loads(S42.read_text(encoding="utf-8"))

    if norm((s42.get("target") or {}).get("pstSn")) != TARGET_PST:
        raise AssertionError("S42 target mismatch")
    if s42.get("status") != EXPECTED_STATUS:
        raise AssertionError(f"S42 status mismatch: {s42.get('status')}")
    if s42.get("download_http") != 200:
        raise AssertionError("S42 download HTTP not 200")
    if not s42.get("pdf_signature"):
        raise AssertionError("S42 PDF signature not verified")
    if not s42.get("pdf_parser"):
        raise AssertionError("S42 PDF parser missing")
    if int(s42.get("page_count") or 0) <= 0:
        raise AssertionError("S42 page count invalid")
    if int(s42.get("text_chars") or 0) <= 0:
        raise AssertionError("S42 text extraction empty")
    if any((s42.get("direct_matches") or {}).values()):
        raise AssertionError("S42 direct candidate cannot be reconciled as no-term")
    if any((s42.get("high_signal_related_matches") or {}).values()):
        raise AssertionError("S42 related candidate cannot be reconciled as no-term")
    if s42.get("state_mutation_allowed"):
        raise AssertionError("S42 unexpectedly allowed state mutation")
    if s42.get("negative_evidence_allowed"):
        raise AssertionError("S42 unexpectedly allowed negative evidence")

    results = state.get("results") or []
    matches = [r for r in results if norm(r.get("pstSn")) == TARGET_PST]
    if len(matches) != 1:
        raise AssertionError(f"state target cardinality mismatch: {len(matches)}")
    prior = matches[0]
    if prior.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN":
        raise AssertionError(f"state prior status mismatch: {prior.get('status')}")

    reconciled: Dict[str, Any] = dict(prior)
    reconciled.update({
        "status": "NO_TERM_IN_EXTRACTED_SAMPLE",
        "signature_class": "PDF",
        "parser_used": f"PDF_TEXT_{s42.get('pdf_parser')}",
        "download_http": s42.get("download_http"),
        "download_url": s42.get("download_url"),
        "download_bytes": s42.get("download_bytes"),
        "extract_ok": True,
        "extract_error": "",
        "text_chars": s42.get("text_chars"),
        "direct_matches": s42.get("direct_matches") or {},
        "related_matches": {},
        "high_signal_related_matches": s42.get("high_signal_related_matches") or {},
        "low_signal_related_matches": {},
        "error": "",
        "pdf_page_count": s42.get("page_count"),
        "pdf_extracted_pages": s42.get("extracted_pages"),
        "recovered_by": "S42_PDF_TEXT_LAYER_RECOVERY",
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
        "step": "STEP 17-21-C-16-8-T-34-S43",
        "target_pstSn": TARGET_PST,
        "prior_status": prior.get("status"),
        "new_status": reconciled.get("status"),
        "recovered_by": reconciled.get("recovered_by"),
        "network_request_count": 0,
        "state_mutation_scope": [TARGET_PST],
        "summary": {
            "processed_count": new_state["processed_count"],
            "remaining_count": new_state["remaining_count"],
            "quarantined_count": new_state["quarantined_count"],
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

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "state exists": STATE.exists(),
        "S42 exists": S42.exists(),
        "exact target only": output["state_mutation_scope"] == [TARGET_PST],
        "prior target was unresolved": prior.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN",
        "S42 PDF text recovered": s42.get("status") == EXPECTED_STATUS and int(s42.get("text_chars") or 0) > 0,
        "target now processed": TARGET_PST in processed,
        "target no longer unresolved": all(norm(r.get("pstSn")) != TARGET_PST for r in unresolved),
        "Gazette 938 quarantine retained": QUARANTINE_PST in new_state["quarantined_pstSn"],
        "Gazette 938 not processed": QUARANTINE_PST not in processed,
        "candidate count zero": len(candidates) == 0,
        "unresolved is quarantine only": len(unresolved) == 1 and norm(unresolved[0].get("pstSn")) == QUARANTINE_PST,
        "network disabled": output["network_request_count"] == 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Prior status:", prior.get("status"))
    print("New status:", reconciled.get("status"))
    print("Recovered by:", reconciled.get("recovered_by"))
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
        raise AssertionError("Gazette 1241 PDF state reconciliation failed")


if __name__ == "__main__":
    main()
