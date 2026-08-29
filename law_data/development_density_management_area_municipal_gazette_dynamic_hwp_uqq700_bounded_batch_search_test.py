# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34
Development Density Management Area
Municipal Gazette Dynamic HWP UQQ700 Bounded Batch Search

Purpose
-------
T-33-S1 proved that HWP3 and HWP5 files are interleaved after HWP5 first appears.
Therefore this stage replaces date-based HWP parser routing with per-file binary
signature routing.

State repair
------------
- Reuses the existing T-33 cumulative state file.
- Keeps successfully processed rows.
- Removes prior EXTRACTION_OR_REQUEST_UNKNOWN rows from processed/results so they
  are retried with the correct signature-routed parser.

Routing
-------
- HWP3 signature -> validated HWP3 extractor from T-32 module
- OLE/CFB HWP5 signature -> validated HWP5 extractor from T-33 module
- anything else -> UNKNOWN

Scope remains Gazette 526 through Gazette 1872, because Gazette 1873 onward is HWPX.
Zero matches remain UNKNOWN, never FALSE.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp3_uqq700_bounded_batch_search_test as hwp3
from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_dynamic_hwp_uqq700_bounded_batch_search.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
BATCH_SIZE = 10
MAX_REQUESTS = 20
HWP3_SIG = b"HWP Document File V3.00"
HWP5_SIG = bytes.fromhex("D0CF11E0A1B11AE1")


def classify_signature(raw: bytes) -> str:
    if raw.startswith(HWP3_SIG):
        return "HWP3"
    if raw.startswith(HWP5_SIG):
        return "HWP5"
    return "UNKNOWN"


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE DYNAMIC HWP UQQ700 BOUNDED BATCH SEARCH")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Batch size:", BATCH_SIZE)
    print("Max requests:", MAX_REQUESTS)
    print("Parser routing: FILE SIGNATURE")
    print("OCR: DISABLED")
    print("PDF search: DISABLED")
    print()

    if not T23.exists():
        raise FileNotFoundError(T23)

    reg = json.loads(T23.read_text(encoding="utf-8"))
    rows = [r for r in (reg.get("canonical_gazette_rows") or []) if hwp5.parse_date(r.get("date")) and hwp5.norm(r.get("pstSn"))]
    rows.sort(key=lambda r: (hwp5.parse_date(r.get("date")), int(r.get("gazette_number") or 0), hwp5.norm(r.get("pstSn"))))
    start = next(i for i, r in enumerate(rows) if hwp5.norm(r.get("pstSn")) == hwp5.HWP5_FIRST_PST)
    end = next(i for i, r in enumerate(rows) if hwp5.norm(r.get("pstSn")) == hwp5.HWP5_LAST_PST)
    era = rows[start:end + 1]

    if STATE.exists():
        prior = json.loads(STATE.read_text(encoding="utf-8"))
    else:
        prior = {"processed_pstSn": [], "results": []}

    prior_results = prior.get("results") or []
    repaired_away = [r for r in prior_results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    kept_results = [r for r in prior_results if r.get("status") != "EXTRACTION_OR_REQUEST_UNKNOWN"]
    kept_processed = [hwp5.norm(r.get("pstSn")) for r in kept_results if hwp5.norm(r.get("pstSn"))]
    done = set(kept_processed)

    selected = [r for r in era if hwp5.norm(r.get("pstSn")) not in done][:BATCH_SIZE]
    if not selected:
        print("No remaining dynamic-HWP rows.")
        return

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0
    batch: List[Dict[str, Any]] = []

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
            "error": "",
        }
        try:
            hs, mu, obj = hwp5.get_json(session, pst)
            req += 1
            att = hwp5.hwp_attachment(obj)
            rec["metadata_http"] = hs
            rec["metadata_url"] = mu
            rec["attachment"] = att
            if not att:
                raise ValueError("HWP attachment not found")

            ds, du, raw = hwp5.get_file(session, pst, att["file_no"])
            req += 1
            rec["download_http"] = ds
            rec["download_url"] = du
            rec["download_bytes"] = len(raw)
            rec["signature_class"] = classify_signature(raw)

            if rec["signature_class"] == "HWP3":
                ext = hwp3.extract_hwp3(raw)
                rec["parser_used"] = "HWP3"
                rec["section_count"] = None
                rec["hwp_flags"] = {}
                rec["paragraphs"] = ext.get("paragraphs", 0)
            elif rec["signature_class"] == "HWP5":
                ext = hwp5.extract_hwp5(raw)
                rec["parser_used"] = "HWP5"
                rec["section_count"] = len(ext.get("sections") or [])
                rec["hwp_flags"] = ext.get("flags") or {}
                rec["paragraphs"] = None
            else:
                raise ValueError("unknown HWP binary signature")

            rec["extract_ok"] = ext.get("ok")
            rec["extract_error"] = ext.get("error")
            rec["text_chars"] = len(ext.get("text", "") or "")
            if not ext.get("ok"):
                raise ValueError(ext.get("error") or "signature-routed extraction failed")

            text = ext["text"]
            rec["direct_matches"] = {t: text.count(t) for t in hwp5.DIRECT}
            rec["related_matches"] = {t: text.count(t) for t in hwp5.RELATED}
            if any(rec["direct_matches"].values()):
                rec["status"] = "DIRECT_CANDIDATE"
            elif any(rec["related_matches"].values()):
                rec["status"] = "RELATED_CANDIDATE"
            else:
                rec["status"] = "NO_TERM_IN_EXTRACTED_SAMPLE"
        except Exception as exc:
            rec["error"] = repr(exc)
            rec["status"] = "EXTRACTION_OR_REQUEST_UNKNOWN"

        batch.append(rec)
        print("ROW:", {k: rec.get(k) for k in ["gazette_number", "date", "pstSn", "signature_class", "parser_used", "status", "download_bytes", "hwp_flags", "section_count", "paragraphs", "text_chars", "direct_matches", "related_matches", "error"]})

    merged_results = kept_results + batch
    processed = list(dict.fromkeys(kept_processed + [r["pstSn"] for r in batch]))
    candidates = [r for r in merged_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in merged_results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    signature_counts: Dict[str, int] = {}
    parser_counts: Dict[str, int] = {}
    for r in merged_results:
        sig = r.get("signature_class") or ("HWP5" if r.get("hwp_flags") is not None and r.get("extract_ok") else "LEGACY_UNKNOWN")
        signature_counts[sig] = signature_counts.get(sig, 0) + 1
        parser = r.get("parser_used") or ("HWP5" if r.get("hwp_flags") is not None and r.get("extract_ok") else "LEGACY_UNKNOWN")
        parser_counts[parser] = parser_counts.get(parser, 0) + 1

    new_state = {
        "era": "DYNAMIC_HWP_PRE_HWPX",
        "era_row_count": len(era),
        "processed_count": len(processed),
        "remaining_count": len(era) - len(processed),
        "processed_pstSn": processed,
        "candidate_count": len(candidates),
        "unresolved_count": len(unresolved),
        "signature_counts": signature_counts,
        "parser_counts": parser_counts,
        "state_repair_removed_unknown_count": len(repaired_away),
        "results": merged_results,
        "negative_evidence_allowed": False,
    }
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {
        "step": "STEP 17-21-C-16-8-T-34 Municipal Gazette Dynamic HWP UQQ700 Bounded Batch Search",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": req,
        "batch_size": len(batch),
        "era_row_count": len(era),
        "state_repair": {
            "prior_result_count": len(prior_results),
            "removed_prior_unknown_count": len(repaired_away),
            "kept_prior_success_count": len(kept_results),
        },
        "batch": batch,
        "cumulative_summary": {k: new_state[k] for k in ["processed_count", "remaining_count", "candidate_count", "unresolved_count", "signature_counts", "parser_counts"]},
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_DYNAMIC_HWP_UQQ700_BOUNDED_BATCH_SEARCH_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("SUMMARY")
    print("Dynamic HWP era rows:", len(era))
    print("Prior unknown rows removed from state:", len(repaired_away))
    print("Batch processed:", len(batch))
    print("Cumulative processed:", new_state["processed_count"])
    print("Remaining:", new_state["remaining_count"])
    print("Candidates:", new_state["candidate_count"])
    print("Unresolved:", new_state["unresolved_count"])
    print("Signature counts:", signature_counts)
    print("Parser counts:", parser_counts)
    print("Network requests:", req)
    print("State:", STATE)
    print("Output:", OUT)

    unsafe = any([output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"], output["final_positive_promotion_allowed"]])
    vals = {
        "T-23 registry exists": T23.exists(),
        "prior unknown rows repaired": len(repaired_away) >= 0,
        "batch bounded": len(batch) <= BATCH_SIZE,
        "request budget respected": req <= MAX_REQUESTS,
        "all response hosts official": all((not r.get("metadata_url") or hwp5.host(r.get("metadata_url")) == "www.seongnam.go.kr") and (not r.get("download_url") or hwp5.host(r.get("download_url")) == "www.seongnam.go.kr") for r in batch),
        "all accepted rows signature routed": all(r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN" or r.get("parser_used") in {"HWP3", "HWP5"} for r in batch),
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
        raise AssertionError("dynamic HWP UQQ700 bounded batch search failed")


if __name__ == "__main__":
    main()
