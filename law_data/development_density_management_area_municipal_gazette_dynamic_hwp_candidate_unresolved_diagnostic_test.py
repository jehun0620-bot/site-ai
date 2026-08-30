# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S37
Targeted diagnostic for the current dynamic-HWP state.

Goals:
- identify all current DIRECT/RELATED candidates and print bounded term contexts;
- identify retryable unresolved rows excluding the explicit Gazette 938 quarantine;
- retry those unresolved rows with a higher HWP5 record safety ceiling;
- do NOT mutate cumulative state;
- do NOT promote any candidate to legal/SITE truth;
- do NOT treat any failure/no-match as negative evidence.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

from law_data import development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search_test as hwp3
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_candidate_unresolved_diagnostic.json"
QUARANTINE = {"29098"}
MAX_RECORDS = 1_000_000
MAX_TARGET_ROWS = 8
MAX_REQUESTS = MAX_TARGET_ROWS * 2
CONTEXT_CHARS = 700


def high_limit_parse_records_text(data: bytes) -> Dict[str, Any]:
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
        if records > MAX_RECORDS:
            error = f"record safety limit exceeded ({MAX_RECORDS})"
            break
    return {
        "record_count": records,
        "para_text_record_count": para_count,
        "fully_consumed": offset == len(data),
        "parse_error": error,
        "text": "\n".join(paragraphs),
    }


def term_contexts(text: str) -> List[Dict[str, Any]]:
    terms = list(dict.fromkeys(list(hwp5.DIRECT) + list(base.HIGH_SIGNAL_RELATED)))
    rows: List[Dict[str, Any]] = []
    for term in terms:
        for m in re.finditer(re.escape(term), text):
            a = max(0, m.start() - CONTEXT_CHARS)
            b = min(len(text), m.end() + CONTEXT_CHARS)
            ctx = re.sub(r"\s+", " ", text[a:b]).strip()
            rows.append({"term": term, "offset": m.start(), "context": ctx})
            if len(rows) >= 12:
                return rows
    return rows


def extract_for_row(session, pst: str) -> Tuple[Dict[str, Any], int]:
    req = 0
    rec: Dict[str, Any] = {"pstSn": pst, "status": "UNKNOWN", "error": ""}
    try:
        hs, mu, obj = hwp5.get_json(session, pst); req += 1
        att = hwp5.hwp_attachment(obj)
        rec.update({"metadata_http": hs, "metadata_url": mu, "attachment": att})
        if not att:
            raise ValueError("HWP attachment not found")
        ds, du, raw = hwp5.get_file(session, pst, att["file_no"]); req += 1
        rec.update({"download_http": ds, "download_url": du, "download_bytes": len(raw)})
        sig = base.classify_signature(raw)
        rec["signature_class"] = sig
        if sig == "HWP3":
            ext = hwp3.extract_hwp3(raw)
            rec["parser_used"] = "HWP3"
        elif sig == "HWP5":
            original = hwp5.parse_records_text
            hwp5.parse_records_text = high_limit_parse_records_text
            try:
                ext = hwp5.extract_hwp5(raw)
            finally:
                hwp5.parse_records_text = original
            rec["parser_used"] = f"HWP5_HIGH_LIMIT_{MAX_RECORDS}"
        else:
            raise ValueError("unknown HWP binary signature")

        rec["extract_ok"] = ext.get("ok")
        rec["extract_error"] = ext.get("error")
        rec["text_chars"] = len(ext.get("text", "") or "")
        rec["sections"] = ext.get("sections")
        if not ext.get("ok"):
            raise ValueError(ext.get("error") or "targeted extraction failed")
        text = ext.get("text") or ""
        rec["direct_matches"] = {t: text.count(t) for t in hwp5.DIRECT}
        rec["high_signal_related_matches"] = {t: text.count(t) for t in base.HIGH_SIGNAL_RELATED}
        rec["contexts"] = term_contexts(text)
        if any(rec["direct_matches"].values()):
            rec["status"] = "DIRECT_CANDIDATE"
        elif any(rec["high_signal_related_matches"].values()):
            rec["status"] = "RELATED_CANDIDATE"
        else:
            rec["status"] = "NO_TERM_IN_EXTRACTED_SAMPLE"
    except Exception as exc:
        rec["status"] = "EXTRACTION_OR_REQUEST_UNKNOWN"
        rec["error"] = repr(exc)
    return rec, req


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("DYNAMIC HWP CANDIDATE / UNRESOLVED DIAGNOSTIC")
    print("=" * 60)
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")
    print("High HWP5 record limit:", MAX_RECORDS)

    if not STATE.exists():
        raise FileNotFoundError(STATE)
    state = json.loads(STATE.read_text(encoding="utf-8"))
    results = state.get("results") or []

    candidates = [r for r in results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    retryable = [r for r in results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN" and hwp5.norm(r.get("pstSn")) not in QUARANTINE]
    quarantined = [r for r in results if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED"]

    print("\nSTATE SNAPSHOT")
    print("Candidates:", len(candidates))
    for r in candidates:
        print("CANDIDATE STATE:", {k: r.get(k) for k in ["gazette_number", "date", "pstSn", "status", "signature_class", "parser_used", "direct_matches", "high_signal_related_matches", "text_chars", "error"]})
    print("Retryable unresolved:", len(retryable))
    for r in retryable:
        print("UNRESOLVED STATE:", {k: r.get(k) for k in ["gazette_number", "date", "pstSn", "status", "signature_class", "parser_used", "download_http", "download_bytes", "extract_error", "error"]})
    print("Quarantined:", [(r.get("gazette_number"), r.get("pstSn")) for r in quarantined])

    target_pst = []
    for r in candidates + retryable:
        pst = hwp5.norm(r.get("pstSn"))
        if pst and pst not in target_pst and pst not in QUARANTINE:
            target_pst.append(pst)
    target_pst = target_pst[:MAX_TARGET_ROWS]

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    reqs = 0
    diagnostics = []
    for pst in target_pst:
        prior = next((r for r in results if hwp5.norm(r.get("pstSn")) == pst), {})
        print("\n-- TARGET", prior.get("gazette_number"), prior.get("date"), "pstSn", pst, "--")
        rec, used = extract_for_row(session, pst)
        reqs += used
        rec["gazette_number"] = prior.get("gazette_number")
        rec["date"] = prior.get("date")
        rec["prior_status"] = prior.get("status")
        diagnostics.append(rec)
        print("RESULT:", {k: rec.get(k) for k in ["gazette_number", "date", "pstSn", "prior_status", "status", "signature_class", "parser_used", "download_bytes", "text_chars", "direct_matches", "high_signal_related_matches", "extract_error", "error"]})
        for i, c in enumerate(rec.get("contexts") or [], 1):
            print(f"CONTEXT {i} [{c['term']}]: {c['context']}")

    recovered_unknown = [r for r in diagnostics if r.get("prior_status") == "EXTRACTION_OR_REQUEST_UNKNOWN" and r.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN"]
    still_unknown = [r for r in diagnostics if r.get("prior_status") == "EXTRACTION_OR_REQUEST_UNKNOWN" and r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    candidate_diag = [r for r in diagnostics if r.get("prior_status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S37",
        "state_candidate_count": len(candidates),
        "state_retryable_unresolved_count": len(retryable),
        "quarantined_count": len(quarantined),
        "network_request_count": reqs,
        "diagnostics": diagnostics,
        "recovered_retryable_unknown_count": len(recovered_unknown),
        "still_unknown_count": len(still_unknown),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "state exists": STATE.exists(),
        "target rows bounded": len(target_pst) <= MAX_TARGET_ROWS,
        "request budget respected": reqs <= MAX_REQUESTS,
        "quarantine excluded from retry": all(r.get("pstSn") not in QUARANTINE for r in diagnostics),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("State candidates:", len(candidates))
    print("State retryable unresolved:", len(retryable))
    print("Targets diagnosed:", len(diagnostics))
    print("Recovered retryable unresolved:", len(recovered_unknown))
    print("Still unresolved after high-limit retry:", len(still_unknown))
    print("Candidate diagnostics:", len(candidate_diag))
    print("Network requests:", reqs)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("candidate/unresolved diagnostic validation failed")


if __name__ == "__main__":
    main()
