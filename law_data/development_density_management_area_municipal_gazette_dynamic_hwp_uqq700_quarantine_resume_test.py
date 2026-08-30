# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S36-H2
Resume the dynamic-HWP UQQ700 search while quarantining Gazette 938.

Hardened after S39/S36-H1:
- HWP downloads are bounded at 64 MiB.
- HWP5 parsing is bounded at 1,000,000 records.
- The high-limit parser preserves the exact dict return contract required by
  extract_hwp5 (S36-H1 incorrectly returned a tuple; H2 fixes that bug).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search_test as hwp3
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5
from law_data import development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search_test as base

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_quarantine_resume.json"

QUARANTINE = {
    "29098": {
        "gazette_number": 938,
        "reason": "LEGACY_PREVIEW_ERA_COMMON_INFO_XML_404_AND_CANONICAL_DOWNLOAD_404",
        "status": "TECHNICAL_UNRESOLVED_QUARANTINED",
        "legal_negative_evidence": False,
    }
}
BATCH_SIZE = 50
MAX_REQUESTS = BATCH_SIZE * 2
LARGE_FILE_LIMIT = 64 * 1024 * 1024
HWP5_MAX_RECORDS = 1_000_000


def high_limit_parse_records_text(data: bytes) -> Dict[str, Any]:
    """S37-validated HWP5 record parser contract with a 1M-record ceiling."""
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
        if records > HWP5_MAX_RECORDS:
            error = f"record safety limit exceeded ({HWP5_MAX_RECORDS})"
            break
    return {
        "record_count": records,
        "para_text_record_count": para_count,
        "fully_consumed": offset == len(data),
        "parse_error": error,
        "text": "\n".join(paragraphs),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("DYNAMIC HWP UQQ700 QUARANTINE RESUME - HARDENED H2")
    print("=" * 60)
    print("Quarantine pstSn:", sorted(QUARANTINE))
    print("Batch size:", BATCH_SIZE)
    print("Download ceiling:", LARGE_FILE_LIMIT)
    print("HWP5 record ceiling:", HWP5_MAX_RECORDS)
    print("OCR: DISABLED")
    print("PDF fallback: DISABLED")
    print("Negative evidence: DISABLED")

    if not T23.exists():
        raise FileNotFoundError(T23)
    if not STATE.exists():
        raise FileNotFoundError(STATE)

    reg = json.loads(T23.read_text(encoding="utf-8"))
    rows = [
        r for r in (reg.get("canonical_gazette_rows") or [])
        if hwp5.parse_date(r.get("date")) and hwp5.norm(r.get("pstSn"))
    ]
    rows.sort(key=lambda r: (
        hwp5.parse_date(r.get("date")),
        int(r.get("gazette_number") or 0),
        hwp5.norm(r.get("pstSn")),
    ))
    start = next(i for i, r in enumerate(rows) if hwp5.norm(r.get("pstSn")) == hwp5.HWP5_FIRST_PST)
    end = next(i for i, r in enumerate(rows) if hwp5.norm(r.get("pstSn")) == hwp5.HWP5_LAST_PST)
    era = rows[start:end + 1]
    era_pst = {hwp5.norm(r.get("pstSn")) for r in era}

    prior = json.loads(STATE.read_text(encoding="utf-8"))
    prior_results = prior.get("results") or []
    kept_results: List[Dict[str, Any]] = []
    retryable_unknown = []
    existing_quarantine = {}

    for r in prior_results:
        pst = hwp5.norm(r.get("pstSn"))
        if pst in QUARANTINE:
            q = dict(r)
            q.update(QUARANTINE[pst])
            q["pstSn"] = pst
            q["error"] = q.get("error") or "Technical source recovery unresolved; quarantined after S35 neighborhood evidence"
            existing_quarantine[pst] = q
        elif r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN":
            retryable_unknown.append(r)
        elif r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED":
            kept_results.append(r)
        else:
            kept_results.append(r)

    for pst, policy in QUARANTINE.items():
        if pst not in era_pst:
            raise AssertionError(f"quarantine pstSn outside era: {pst}")
        if pst not in existing_quarantine:
            row = next(r for r in era if hwp5.norm(r.get("pstSn")) == pst)
            existing_quarantine[pst] = {
                "date": hwp5.norm(row.get("date")),
                "gazette_number": row.get("gazette_number"),
                "pstSn": pst,
                "signature_class": "UNKNOWN",
                "parser_used": "",
                "direct_matches": {},
                "related_matches": {},
                "high_signal_related_matches": {},
                "low_signal_related_matches": {},
                "error": "Technical source recovery unresolved; quarantined after S35 neighborhood evidence",
                **policy,
            }

    successful_pst = {
        hwp5.norm(r.get("pstSn"))
        for r in kept_results
        if hwp5.norm(r.get("pstSn"))
        and r.get("status") not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}
    }
    selected = [
        r for r in era
        if hwp5.norm(r.get("pstSn")) not in successful_pst
        and hwp5.norm(r.get("pstSn")) not in QUARANTINE
    ][:BATCH_SIZE]

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0
    batch: List[Dict[str, Any]] = []
    original_file_limit = hwp5.MAX_FILE_BYTES
    original_parser = hwp5.parse_records_text
    hwp5.MAX_FILE_BYTES = LARGE_FILE_LIMIT
    hwp5.parse_records_text = high_limit_parse_records_text

    try:
        for row in selected:
            pst = hwp5.norm(row.get("pstSn"))
            rec: Dict[str, Any] = {
                "date": hwp5.norm(row.get("date")),
                "gazette_number": row.get("gazette_number"),
                "pstSn": pst,
                "status": "UNKNOWN",
                "signature_class": "UNKNOWN",
                "parser_used": "",
                "direct_matches": {},
                "related_matches": {},
                "high_signal_related_matches": {},
                "low_signal_related_matches": {},
                "error": "",
            }
            try:
                hs, mu, obj = hwp5.get_json(session, pst)
                req += 1
                att = hwp5.hwp_attachment(obj)
                rec.update({"metadata_http": hs, "metadata_url": mu, "attachment": att})
                if not att:
                    raise ValueError("HWP attachment not found")

                ds, du, raw = hwp5.get_file(session, pst, att["file_no"])
                req += 1
                rec.update({
                    "download_http": ds,
                    "download_url": du,
                    "download_bytes": len(raw),
                    "signature_class": base.classify_signature(raw),
                })

                if rec["signature_class"] == "HWP3":
                    ext = hwp3.extract_hwp3(raw)
                    rec.update({
                        "parser_used": "HWP3",
                        "section_count": None,
                        "hwp_flags": {},
                        "paragraphs": ext.get("paragraphs", 0),
                    })
                elif rec["signature_class"] == "HWP5":
                    ext = hwp5.extract_hwp5(raw)
                    rec.update({
                        "parser_used": "HWP5_HIGH_LIMIT_1000000",
                        "section_count": len(ext.get("sections") or []),
                        "hwp_flags": ext.get("flags") or {},
                        "paragraphs": None,
                    })
                else:
                    raise ValueError("unknown HWP binary signature")

                rec.update({
                    "extract_ok": ext.get("ok"),
                    "extract_error": ext.get("error"),
                    "text_chars": len(ext.get("text", "") or ""),
                })
                if not ext.get("ok"):
                    raise ValueError(ext.get("error") or "signature-routed extraction failed")

                text = ext["text"]
                rec["direct_matches"] = {t: text.count(t) for t in hwp5.DIRECT}
                rec["related_matches"] = {t: text.count(t) for t in hwp5.RELATED}
                rec["high_signal_related_matches"] = {
                    t: rec["related_matches"].get(t, 0) for t in base.HIGH_SIGNAL_RELATED
                }
                rec["low_signal_related_matches"] = {
                    t: rec["related_matches"].get(t, 0) for t in base.LOW_SIGNAL_RELATED
                }
                if any(rec["direct_matches"].values()):
                    rec["status"] = "DIRECT_CANDIDATE"
                elif any(rec["high_signal_related_matches"].values()):
                    rec["status"] = "RELATED_CANDIDATE"
                else:
                    rec["status"] = "NO_TERM_IN_EXTRACTED_SAMPLE"
            except Exception as exc:
                rec["error"] = repr(exc)
                rec["status"] = "EXTRACTION_OR_REQUEST_UNKNOWN"

            batch.append(rec)
            print("ROW:", {k: rec.get(k) for k in [
                "gazette_number", "date", "pstSn", "signature_class", "parser_used", "status",
                "download_bytes", "text_chars", "direct_matches", "high_signal_related_matches", "error",
            ]})
    finally:
        hwp5.MAX_FILE_BYTES = original_file_limit
        hwp5.parse_records_text = original_parser

    merged_results = kept_results + list(existing_quarantine.values()) + batch
    processed = list(dict.fromkeys(
        hwp5.norm(r.get("pstSn")) for r in merged_results
        if hwp5.norm(r.get("pstSn"))
        and r.get("status") not in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}
    ))
    candidates = [r for r in merged_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in merged_results if r.get("status") in {"EXTRACTION_OR_REQUEST_UNKNOWN", "TECHNICAL_UNRESOLVED_QUARANTINED"}]
    quarantined = [r for r in merged_results if r.get("status") == "TECHNICAL_UNRESOLVED_QUARANTINED"]

    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in merged_results:
        sig = r.get("signature_class") or "LEGACY_UNKNOWN"
        parser = r.get("parser_used") or "LEGACY_UNKNOWN"
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    new_state = {
        "era": "DYNAMIC_HWP_PRE_HWPX",
        "era_row_count": len(era),
        "processed_count": len(processed),
        "remaining_count": len(era) - len(processed) - len(quarantined),
        "quarantined_count": len(quarantined),
        "processed_pstSn": processed,
        "quarantined_pstSn": [r["pstSn"] for r in quarantined],
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "retryable_unknown_removed_before_batch": len(retryable_unknown),
        "results": merged_results,
        "negative_evidence_allowed": False,
        "hardened_download_ceiling": LARGE_FILE_LIMIT,
        "hardened_hwp5_record_ceiling": HWP5_MAX_RECORDS,
        "hardened_parser_contract": "DICT_V1_S37_VALIDATED",
    }
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S36-H2",
        "network_request_count": req,
        "batch_size": len(batch),
        "quarantine_policy": QUARANTINE,
        "cumulative_summary": {k: new_state[k] for k in [
            "era_row_count", "processed_count", "remaining_count", "quarantined_count",
            "candidate_count", "unresolved_count", "signature_counts", "parser_counts",
        ]},
        "batch": batch,
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
        "T-23 registry exists": T23.exists(),
        "state exists": STATE.exists(),
        "quarantine retained": set(QUARANTINE).issubset(set(new_state["quarantined_pstSn"])),
        "quarantine not processed": not (set(QUARANTINE) & set(processed)),
        "batch excludes quarantine": all(r.get("pstSn") not in QUARANTINE for r in batch),
        "batch bounded": len(batch) <= BATCH_SIZE,
        "request budget respected": req <= MAX_REQUESTS,
        "unresolved not processed": all(hwp5.norm(r.get("pstSn")) not in processed for r in unresolved),
        "generic related term cannot trigger alone": all(
            not (r.get("status") == "RELATED_CANDIDATE" and not any((r.get("high_signal_related_matches") or {}).values()))
            for r in batch
        ),
        "large-file ceiling restored": hwp5.MAX_FILE_BYTES == original_file_limit,
        "HWP5 parser restored": hwp5.parse_records_text is original_parser,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "state written": STATE.exists() and STATE.stat().st_size > 0,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Dynamic HWP era rows:", len(era))
    print("Retryable prior unknown removed:", len(retryable_unknown))
    print("Batch processed:", len(batch))
    print("Cumulative processed:", new_state["processed_count"])
    print("Quarantined:", new_state["quarantined_count"], new_state["quarantined_pstSn"])
    print("Remaining searchable:", new_state["remaining_count"])
    print("Candidates:", new_state["candidate_count"])
    print("Unresolved total:", new_state["unresolved_count"])
    print("Signature counts:", signature_counts)
    print("Parser counts:", parser_counts)
    print("Network requests:", req)
    print("State:", STATE)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("dynamic HWP hardened H2 quarantine resume validation failed")


if __name__ == "__main__":
    main()
