# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S8
Recover the three HWP5 rows that exceeded the 200k record safety limit and
reclassify the Gazette 730 `개발밀도` hit as contextual/non-UQQ700 terminology.

Evidence from T-34-S7
---------------------
- pstSn 28879 / Gazette 730: the only `개발밀도` occurrence appears in the phrase
  `주변지역의 향후 개발밀도 등을 고려하여 ... 도로폭원을 설정`, i.e. generic
  future development density used for road-capacity planning, not the statutory
  name `개발밀도관리구역` and not a designation act.
- pstSn 28872, 28894, 28907: HWP5 parsing stopped only because the existing
  200,000-record safety ceiling was reached. Binary signature, decompression and
  paragraph extraction were otherwise valid.

Actions
-------
1) Temporarily replace only the HWP5 record parser with the same parser logic but
   a bounded 600,000-record ceiling.
2) Reuse T-34 with BATCH_SIZE=3 / MAX_REQUESTS=6. Because unresolved rows are not
   processed, these are the next three retryable rows.
3) After successful recovery, change only pstSn 28879 from RELATED_CANDIDATE to
   CONTEXTUAL_TERM_NOT_UQQ700_CANDIDATE, preserving the original term telemetry
   and adding the reviewed context classification.
4) Recompute state counts.

Safety
------
- no OCR/PDF fallback
- no negative evidence
- contextual reclassification is not legal FALSE
- no TRUE/SITE/runtime promotion
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as t34
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_record_limit_recovery_and_candidate_reclassification.json"

RECORD_LIMIT = 600_000
RECOVERY_TARGETS = {"28872", "28894", "28907"}
CANDIDATE_PST = "28879"
CONTEXT_NOTE = (
    "The sole 개발밀도 occurrence is generic planning language: "
    "주변지역의 향후 개발밀도 등을 고려하여 정비사업 시행 후 교통량을 감안해 도로폭원을 설정. "
    "It does not name 개발밀도관리구역 and does not express a designation/release act."
)


def parse_records_text_with_higher_bound(data: bytes) -> Dict[str, Any]:
    offset = 0
    records = 0
    paragraphs: List[str] = []
    para_count = 0
    error = ""
    while offset < len(data):
        try:
            rec, next_offset = hwp5.parse_record_header(data, offset)
        except Exception as exc:
            error = repr(exc)
            break
        if rec["tag_id"] == hwp5.PARA_TEXT_TAG:
            para_count += 1
            text = hwp5.sanitize_para_text(data[rec["payload_offset"]:rec["end"]])
            if text:
                paragraphs.append(text)
        records += 1
        offset = next_offset
        if records > RECORD_LIMIT:
            error = f"record safety limit exceeded ({RECORD_LIMIT})"
            break
    merged = "\n".join(paragraphs)
    return {
        "record_count": records,
        "para_text_record_count": para_count,
        "fully_consumed": offset == len(data),
        "parse_error": error,
        "text": merged,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("HWP5 RECORD-LIMIT RECOVERY + CANDIDATE RECLASSIFICATION")
    print("=" * 60)
    print("Recovery targets:", sorted(RECOVERY_TARGETS))
    print("Temporary record limit:", RECORD_LIMIT)
    print("Candidate reclassification target:", CANDIDATE_PST)
    print("OCR/PDF fallback: DISABLED")
    print()

    original_parser = hwp5.parse_records_text
    original_batch = t34.BATCH_SIZE
    original_requests = t34.MAX_REQUESTS
    try:
        hwp5.parse_records_text = parse_records_text_with_higher_bound
        t34.BATCH_SIZE = 3
        t34.MAX_REQUESTS = 6
        t34.main()
    finally:
        hwp5.parse_records_text = original_parser
        t34.BATCH_SIZE = original_batch
        t34.MAX_REQUESTS = original_requests

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    results = state.get("results") or []

    recovered = [r for r in results if str(r.get("pstSn") or "") in RECOVERY_TARGETS]
    recovery_ok = (
        len(recovered) == 3
        and all(r.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN" for r in recovered)
        and all(r.get("parser_used") == "HWP5" for r in recovered)
    )

    candidate_hits = [r for r in results if str(r.get("pstSn") or "") == CANDIDATE_PST]
    if len(candidate_hits) != 1:
        raise AssertionError(f"expected exactly one candidate state row, got {len(candidate_hits)}")
    cand = candidate_hits[0]
    if cand.get("status") != "RELATED_CANDIDATE":
        raise AssertionError(f"unexpected candidate status before reclassification: {cand.get('status')}")
    if int((cand.get("high_signal_related_matches") or {}).get("개발밀도") or 0) != 1:
        raise AssertionError("expected exactly one 개발밀도 telemetry hit")
    if any((cand.get("direct_matches") or {}).values()):
        raise AssertionError("direct UQQ700 term unexpectedly present")

    cand["status"] = "CONTEXTUAL_TERM_NOT_UQQ700_CANDIDATE"
    cand["candidate_reclassification"] = {
        "reviewed": True,
        "basis": "T-34-S7 bounded context review",
        "classification": "GENERIC_DEVELOPMENT_DENSITY_PLANNING_LANGUAGE",
        "context_note": CONTEXT_NOTE,
        "legal_false": False,
        "negative_evidence_allowed": False,
    }

    candidates = [r for r in results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    processed = [str(x) for x in (state.get("processed_pstSn") or [])]
    era_count = int(state.get("era_row_count") or 0)

    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in results:
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    state["results"] = results
    state["processed_count"] = len(processed)
    state["remaining_count"] = era_count - len(processed)
    state["candidate_count"] = len(candidates)
    state["unresolved_count"] = len(unresolved)
    state["signature_counts"] = signature_counts
    state["parser_counts"] = parser_counts
    state["negative_evidence_allowed"] = False
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S8",
        "record_limit": RECORD_LIMIT,
        "recovery_targets": sorted(RECOVERY_TARGETS),
        "recovered": recovered,
        "candidate_reclassified": cand,
        "processed_count": state["processed_count"],
        "remaining_count": state["remaining_count"],
        "candidate_count": state["candidate_count"],
        "unresolved_count": state["unresolved_count"],
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("RECLASSIFIED CANDIDATE")
    print("pstSn:", CANDIDATE_PST)
    print("New status:", cand["status"])
    print("Classification:", cand["candidate_reclassification"]["classification"])
    print("Legal FALSE:", cand["candidate_reclassification"]["legal_false"])
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
        "all three record-limit rows recovered": recovery_ok,
        "all recovery targets processed": RECOVERY_TARGETS.issubset(set(processed)),
        "candidate reclassified": cand.get("status") == "CONTEXTUAL_TERM_NOT_UQQ700_CANDIDATE",
        "candidate telemetry preserved": int((cand.get("high_signal_related_matches") or {}).get("개발밀도") or 0) == 1,
        "candidate is not legal false": cand["candidate_reclassification"]["legal_false"] is False,
        "candidate count recomputed": state["candidate_count"] == 0,
        "unresolved count zero": state["unresolved_count"] == 0,
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
        raise AssertionError("record-limit recovery/candidate reclassification failed")


if __name__ == "__main__":
    main()
