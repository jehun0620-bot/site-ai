# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_attachment_uqq700_content_scan.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_technical_unknown_attachment_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
ZIP_MAGIC = b"PK\x03\x04"
PDF_MAGIC = b"%PDF-"


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}|%{num_redirects}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 3)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
        redirects = parts[3] if len(parts) > 3 else None
    else:
        body, http, final_url, content_type, redirects = raw, None, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "redirects": redirects,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def classify_signature(body: bytes) -> str:
    if body.startswith(PDF_MAGIC):
        return "PDF"
    if body.startswith(OLE_MAGIC):
        return "OLE_HWP"
    if body.startswith(ZIP_MAGIC):
        return "ZIP_HWPX_OR_ZIP"
    prefix = body[:128].lstrip().lower()
    if prefix.startswith(b"<html") or b"<!doctype html" in prefix:
        return "HTML"
    return "OTHER"


def scan_terms(text: str) -> dict:
    exact = [t for t in EXACT_TERMS if t in text]
    variant = [t for t in VARIANT_TERMS if t in text]
    weak = [t for t in WEAK_TERMS if t in text]
    if exact:
        status = "EXACT_CONTENT_HIT"
    elif variant:
        status = "VARIANT_CONTENT_HIT"
    elif weak:
        status = "WEAK_CONTENT_HIT"
    else:
        status = "CONTENT_NO_HIT"
    return {"status": status, "exact_terms": exact, "variant_terms": variant, "weak_terms": weak}


def extract_pdf_text(body: bytes) -> tuple[str | None, str | None]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(body))
        chunks = []
        for i, page in enumerate(reader.pages, 1):
            try:
                chunks.append(page.extract_text() or "")
            except Exception as e:
                return None, f"PAGE_{i}_ERROR: {type(e).__name__}: {e}"
        return "\n".join(chunks), None
    except Exception as e:
        return None, f"PDF_PARSE_ERROR: {type(e).__name__}: {e}"


def detect_hwp_parser() -> dict:
    return {
        "hwp5txt": shutil.which("hwp5txt") or shutil.which("hwp5txt.exe"),
        "python_module_hwp5": _module_available("hwp5"),
        "python_module_olefile": _module_available("olefile"),
    }


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def extract_hwp_text(body: bytes, suffix: str, parser_info: dict) -> tuple[str | None, str | None, str]:
    cli = parser_info.get("hwp5txt")
    if not cli:
        return None, "HWP5TXT_NOT_AVAILABLE", "NONE"
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(body)
            path = tf.name
        p = subprocess.run([cli, path], capture_output=True, timeout=120)
        if p.returncode != 0:
            return None, (p.stderr or b"").decode("utf-8", errors="replace")[:2000], "hwp5txt"
        raw = p.stdout or b""
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                return raw.decode(enc), None, "hwp5txt"
            except UnicodeDecodeError:
                pass
        return raw.decode("utf-8", errors="replace"), None, "hwp5txt"
    except Exception as e:
        return None, f"HWP_PARSE_ERROR: {type(e).__name__}: {e}", "hwp5txt"
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT UQQ700 TECHNICAL UNKNOWN ATTACHMENT RECOVERY - S227F")
    print("=" * 78)
    print("Purpose: recover only S227D TECHNICAL_UNKNOWN attachments")
    print("Package auto-install: NOT EXECUTED")
    print("OCR: NOT EXECUTED")
    print("Recovery no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227D output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    unknowns = [r for r in (prior.get("results") or []) if r.get("status") == "TECHNICAL_UNKNOWN"]
    parser_info = detect_hwp_parser()

    results = []
    recovered_pdf = 0
    recovered_hwp = 0
    remaining = 0
    exact_hits = variant_hits = weak_hits = no_hits = 0

    for idx, row in enumerate(unknowns, 1):
        url = row.get("download_url")
        ext = str(row.get("extension") or "").lower()
        dl = curl_bytes(url) if url else {"http": None, "final_url": None, "content_type": None, "redirects": None, "body": b"", "stderr": "missing url"}
        body = dl.get("body") or b""
        sig = classify_signature(body) if body else "EMPTY"
        rec = {
            "pstSn": row.get("pstSn"), "fileNo": row.get("fileNo"), "name": row.get("name"), "extension": ext,
            "download_url": url, "http": dl.get("http"), "final_url": dl.get("final_url"),
            "content_type": dl.get("content_type"), "redirect_count": dl.get("redirects"),
            "body_size": len(body), "body_prefix_hex": body[:24].hex(), "signature": sig,
            "parser": None, "status": "TECHNICAL_UNKNOWN", "error": None,
            "exact_terms": [], "variant_terms": [], "weak_terms": [],
        }

        if dl.get("http") == "200" and body:
            if ext == "pdf" and sig == "PDF":
                text, err = extract_pdf_text(body)
                rec["parser"] = "pypdf"
                rec["error"] = err
                if text is not None:
                    rec.update(scan_terms(text))
                    recovered_pdf += 1
            elif ext in {"hwp", "hwpx"} and sig in {"OLE_HWP", "ZIP_HWPX_OR_ZIP"}:
                text, err, parser = extract_hwp_text(body, "." + ext, parser_info)
                rec["parser"] = parser
                rec["error"] = err
                if text is not None:
                    rec.update(scan_terms(text))
                    recovered_hwp += 1
            else:
                rec["error"] = f"UNEXPECTED_RESPONSE_SIGNATURE:{sig}"
        else:
            rec["error"] = f"DOWNLOAD_FAILED:{dl.get('http')}:{dl.get('stderr')}"

        if rec["status"] == "EXACT_CONTENT_HIT": exact_hits += 1
        elif rec["status"] == "VARIANT_CONTENT_HIT": variant_hits += 1
        elif rec["status"] == "WEAK_CONTENT_HIT": weak_hits += 1
        elif rec["status"] == "CONTENT_NO_HIT": no_hits += 1
        else: remaining += 1

        results.append(rec)
        print(f"RECOVERY PROGRESS: {idx}/{len(unknowns)} | PSTSN={row.get('pstSn')} | FILENO={row.get('fileNo')} | HTTP={rec['http']} | SIG={sig} | STATUS={rec['status']}")

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_RECOVERY_UQQ700_CANDIDATE_HIT"
        semantic = "RECOVERED_ATTACHMENT_CONTENT_CONTAINS_EXACT_OR_VARIANT_UQQ700_TERM_REQUIRING_CONTEXT_AND_OFFICIAL_NOTICE_TRACE"
        next_action = "REVIEW_ONLY_RECOVERED_EXACT_OR_VARIANT_HITS_AND_TRACE_ANY_LITERAL_NOTICE_IDENTITY_NON_PROMOTIONALLY"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_RECOVERY_WEAK_HIT"
        semantic = "RECOVERED_ATTACHMENT_CONTENT_CONTAINS_WEAK_DENSITY_TERM_WITHOUT_DESIGNATION_PROMOTION"
        next_action = "REVIEW_RECOVERED_WEAK_CONTEXT_NON_PROMOTIONALLY_THEN_RECONCILE_REMAINING_TECHNICAL_UNKNOWN"
    elif remaining == 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_ATTACHMENTS_FULLY_RECOVERED_NO_UQQ700_HIT"
        semantic = "ALL_PRIOR_TECHNICAL_UNKNOWN_TEXT_ATTACHMENTS_RECOVERED_AND_SCANNED_WITH_NO_UQQ700_TERM"
        next_action = "RECONCILE_PLANNING_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_ATTACHMENTS_PARTIALLY_UNRESOLVED"
        semantic = "ONE_OR_MORE_PRIOR_TECHNICAL_UNKNOWN_ATTACHMENTS_REMAIN_UNRESOLVED_AFTER_BOUNDED_RECOVERY"
        next_action = "HARDEN_ONLY_REMAINING_UNRESOLVED_ATTACHMENT_TRANSPORT_OR_HWP_PARSER_COVERAGE_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-152-S227F",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_technical_unknown_count": len(unknowns),
        "hwp_parser_availability": parser_info,
        "recovered_pdf_count": recovered_pdf,
        "recovered_hwp_count": recovered_hwp,
        "remaining_technical_unknown_count": remaining,
        "exact_content_hit_count": exact_hits,
        "variant_content_hit_count": variant_hits,
        "weak_content_hit_count": weak_hits,
        "content_no_hit_count": no_hits,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "recovery_hit_equals_designation_notice": False,
            "recovery_hit_equals_current_validity": False,
            "recovery_hit_equals_site_inclusion": False,
            "recovery_no_hit_equals_legal_absence": False,
            "remaining_technical_unknown_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nTECHNICAL UNKNOWN RECOVERY SUMMARY")
    print("-" * 78)
    print(f"PRIOR TECHNICAL UNKNOWN COUNT: {len(unknowns)}")
    print(f"HWP PARSER AVAILABILITY: {parser_info}")
    print(f"RECOVERED PDF COUNT: {recovered_pdf}")
    print(f"RECOVERED HWP COUNT: {recovered_hwp}")
    print(f"REMAINING TECHNICAL UNKNOWN COUNT: {remaining}")
    print(f"EXACT CONTENT HIT COUNT: {exact_hits}")
    print(f"VARIANT CONTENT HIT COUNT: {variant_hits}")
    print(f"WEAK CONTENT HIT COUNT: {weak_hits}")
    print(f"CONTENT NO HIT COUNT: {no_hits}")

    print("\nDETAILS")
    print("-" * 78)
    for r in results:
        print(f"PSTSN={r['pstSn']} FILENO={r['fileNo']} EXT={r['extension']} HTTP={r['http']} SIG={r['signature']} STATUS={r['status']}")
        print(f"  FINAL={r['final_url']} REDIRECTS={r['redirect_count']} CT={r['content_type']} SIZE={r['body_size']}")
        print(f"  PREFIX={r['body_prefix_hex']} PARSER={r['parser']} ERROR={r['error']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Recovery hit == designation/current validity/site inclusion: False")
    print("Recovery no-hit == legal absence: False")
    print("Remaining technical unknown == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227D input exists": PRIOR_OUT.exists(),
        "technical unknowns present": len(unknowns) > 0,
        "recovery hit not designation": out["summary"]["recovery_hit_equals_designation_notice"] is False,
        "recovery hit not validity": out["summary"]["recovery_hit_equals_current_validity"] is False,
        "recovery hit not site inclusion": out["summary"]["recovery_hit_equals_site_inclusion"] is False,
        "recovery no-hit not legal absence": out["summary"]["recovery_no_hit_equals_legal_absence"] is False,
        "remaining unknown not legal absence": out["summary"]["remaining_technical_unknown_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_RECOVERY_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_RECOVERY_WEAK_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_ATTACHMENTS_FULLY_RECOVERED_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_TECHNICAL_UNKNOWN_ATTACHMENTS_PARTIALLY_UNRESOLVED",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S227F validation failed")


if __name__ == "__main__":
    main()
