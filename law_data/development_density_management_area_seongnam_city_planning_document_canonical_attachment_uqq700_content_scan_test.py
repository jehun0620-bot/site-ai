# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import shutil
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_archive_coverage_canonical_enumeration.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_canonical_attachment_uqq700_content_scan.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"

EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]
TEXT_EXTENSIONS = {"pdf", "hwp", "hwpx"}
NON_TEXT_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "bmp", "tif", "tiff"}


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "final_url": None, "content_type": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}|%{url_effective}|%{content_type}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        parts = meta.decode("utf-8", errors="replace").strip().split("|", 2)
        http = parts[0] if parts else None
        final_url = parts[1] if len(parts) > 1 else None
        content_type = parts[2] if len(parts) > 2 else None
    else:
        body, http, final_url, content_type = raw, None, None, None
    return {
        "http": http,
        "final_url": final_url,
        "content_type": content_type,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def scan_terms(text: str) -> dict:
    normalized = text or ""
    exact = [t for t in EXACT_TERMS if t in normalized]
    variant = [t for t in VARIANT_TERMS if t in normalized]
    weak = [t for t in WEAK_TERMS if t in normalized]
    if exact:
        status = "EXACT_CONTENT_HIT"
    elif variant:
        status = "VARIANT_CONTENT_HIT"
    elif weak:
        status = "WEAK_CONTENT_HIT"
    else:
        status = "CONTENT_NO_HIT"
    return {"status": status, "exact_terms": exact, "variant_terms": variant, "weak_terms": weak}


def extract_pdf_text(body: bytes) -> tuple[str | None, dict]:
    try:
        from pypdf import PdfReader
    except Exception as e:
        return None, {"parser": "pypdf", "error": f"IMPORT_ERROR: {type(e).__name__}: {e}"}
    try:
        reader = PdfReader(io.BytesIO(body))
        page_texts = []
        empty_pages = 0
        page_errors = []
        for idx, page in enumerate(reader.pages):
            try:
                txt = page.extract_text() or ""
                if not txt.strip():
                    empty_pages += 1
                page_texts.append(txt)
            except Exception as e:
                page_errors.append({"page": idx + 1, "error": f"{type(e).__name__}: {e}"})
        if page_errors:
            return None, {
                "parser": "pypdf",
                "page_count": len(reader.pages),
                "empty_page_count": empty_pages,
                "page_errors": page_errors,
                "error": "ONE_OR_MORE_PAGE_EXTRACTION_ERRORS",
            }
        return "\n".join(page_texts), {
            "parser": "pypdf",
            "page_count": len(reader.pages),
            "empty_page_count": empty_pages,
            "page_errors": [],
            "error": None,
        }
    except Exception as e:
        return None, {"parser": "pypdf", "error": f"PDF_PARSE_ERROR: {type(e).__name__}: {e}"}


def extract_hwp_text(body: bytes, suffix: str) -> tuple[str | None, dict]:
    cli = shutil.which("hwp5txt") or shutil.which("hwp5txt.exe")
    if not cli:
        return None, {"parser": "hwp5txt", "error": "HWP5TXT_NOT_AVAILABLE"}
    path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tf:
            tf.write(body)
            path = tf.name
        p = subprocess.run([cli, path], capture_output=True, timeout=120)
        if p.returncode != 0:
            return None, {
                "parser": "hwp5txt",
                "returncode": p.returncode,
                "error": (p.stderr or b"").decode("utf-8", errors="replace")[:2000],
            }
        raw = p.stdout or b""
        for enc in ("utf-8", "cp949", "euc-kr"):
            try:
                return raw.decode(enc), {"parser": "hwp5txt", "returncode": 0, "error": None}
            except UnicodeDecodeError:
                pass
        return raw.decode("utf-8", errors="replace"), {"parser": "hwp5txt", "returncode": 0, "error": None}
    except Exception as e:
        return None, {"parser": "hwp5txt", "error": f"HWP_PARSE_ERROR: {type(e).__name__}: {e}"}
    finally:
        if path:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT CANONICAL ATTACHMENT UQQ700 CONTENT SCAN - S227D")
    print("=" * 78)
    print("Purpose: bounded content scan over qualified canonical attachments")
    print("PDF parser: pypdf")
    print("HWP parser: hwp5txt only when locally available")
    print("Image OCR: NOT EXECUTED")
    print("Content hit != designation notice/current validity/site inclusion")
    print("Content no-hit != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227B output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    inventory_qualified = bool(prior.get("canonical_inventory_qualified"))
    attachments = prior.get("canonical_attachments") or []

    results = []
    status_counts = Counter()
    ext_counts = Counter()
    download_success = 0
    pdf_parse_success = 0
    hwp_parse_success = 0
    hwpx_parse_success = 0
    technical_unknown = 0
    non_text = 0

    for idx, a in enumerate(attachments, 1):
        pst_sn = str(a.get("pstSn") or "")
        file_no = str(a.get("fileNo") or "")
        name = a.get("orginlFileNm") or ""
        ext = str(a.get("fileExtsn") or "").lower().lstrip(".")
        url = a.get("download_url")
        ext_counts[ext] += 1

        row = {
            "pstSn": pst_sn,
            "fileNo": file_no,
            "name": name,
            "extension": ext,
            "download_url": url,
            "download_http": None,
            "content_type": None,
            "body_size": 0,
            "parser": None,
            "parser_detail": None,
            "status": None,
            "exact_terms": [],
            "variant_terms": [],
            "weak_terms": [],
        }

        if ext in NON_TEXT_EXTENSIONS:
            row["status"] = "NON_TEXT_ATTACHMENT"
            row["parser"] = "NONE"
            row["parser_detail"] = {"reason": "NON_TEXT_EXTENSION_OCR_NOT_EXECUTED"}
            non_text += 1
            status_counts[row["status"]] += 1
            results.append(row)
            continue

        if ext not in TEXT_EXTENSIONS:
            row["status"] = "TECHNICAL_UNKNOWN"
            row["parser"] = "NONE"
            row["parser_detail"] = {"reason": "UNSUPPORTED_EXTENSION"}
            technical_unknown += 1
            status_counts[row["status"]] += 1
            results.append(row)
            continue

        if not url:
            row["status"] = "TECHNICAL_UNKNOWN"
            row["parser"] = "NONE"
            row["parser_detail"] = {"reason": "MISSING_DOWNLOAD_URL"}
            technical_unknown += 1
            status_counts[row["status"]] += 1
            results.append(row)
            continue

        dl = curl_bytes(url)
        body = dl.get("body") or b""
        row["download_http"] = dl.get("http")
        row["content_type"] = dl.get("content_type")
        row["body_size"] = len(body)

        if dl.get("http") != "200" or not body:
            row["status"] = "TECHNICAL_UNKNOWN"
            row["parser"] = "NONE"
            row["parser_detail"] = {"reason": "DOWNLOAD_FAILED", "stderr": dl.get("stderr")}
            technical_unknown += 1
            status_counts[row["status"]] += 1
            results.append(row)
            continue

        download_success += 1

        if ext == "pdf":
            text, detail = extract_pdf_text(body)
            row["parser"] = "pypdf"
            row["parser_detail"] = detail
            if text is None:
                row["status"] = "TECHNICAL_UNKNOWN"
                technical_unknown += 1
            else:
                pdf_parse_success += 1
                scan = scan_terms(text)
                row.update(scan)
        elif ext in {"hwp", "hwpx"}:
            text, detail = extract_hwp_text(body, "." + ext)
            row["parser"] = "hwp5txt"
            row["parser_detail"] = detail
            if text is None:
                row["status"] = "TECHNICAL_UNKNOWN"
                technical_unknown += 1
            else:
                if ext == "hwp":
                    hwp_parse_success += 1
                else:
                    hwpx_parse_success += 1
                scan = scan_terms(text)
                row.update(scan)

        status_counts[row["status"]] += 1
        results.append(row)

        if idx % 10 == 0 or idx == len(attachments):
            print(f"CONTENT SCAN PROGRESS: {idx}/{len(attachments)}")

    exact_hits = [r for r in results if r["status"] == "EXACT_CONTENT_HIT"]
    variant_hits = [r for r in results if r["status"] == "VARIANT_CONTENT_HIT"]
    weak_hits = [r for r in results if r["status"] == "WEAK_CONTENT_HIT"]
    no_hits = [r for r in results if r["status"] == "CONTENT_NO_HIT"]
    technical_rows = [r for r in results if r["status"] == "TECHNICAL_UNKNOWN"]

    text_target_count = sum(1 for a in attachments if str(a.get("fileExtsn") or "").lower().lstrip(".") in TEXT_EXTENSIONS)
    fully_scanned_text_count = len(exact_hits) + len(variant_hits) + len(weak_hits) + len(no_hits)
    content_scan_complete = inventory_qualified and technical_unknown == 0 and fully_scanned_text_count == text_target_count

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_UQQ700_CANDIDATE_HIT"
        semantic = "EXACT_OR_VARIANT_UQQ700_TERM_OBSERVED_IN_QUALIFIED_PLANNING_DOCUMENT_CONTENT_REQUIRING_DOCUMENT_IDENTITY_REVIEW"
        next_action = "REVIEW_ONLY_THE_HIT_DOCUMENT_CONTEXT_AND_TRACE_ANY_LITERAL_DESIGNATION_NOTICE_IDENTITY_TO_OFFICIAL_NOTICE"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_WEAK_UQQ700_TERM_HIT"
        semantic = "WEAK_UQQ700_TERM_OBSERVED_IN_CONTENT_WITHOUT_DESIGNATION_IDENTITY_PROMOTION"
        next_action = "REVIEW_WEAK_HIT_CONTEXT_NON_PROMOTIONALLY_BEFORE_ANY_SOURCE_FAMILY_RECONCILIATION"
    elif content_scan_complete:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_SCAN_COMPLETE_NO_UQQ700_HIT"
        semantic = "ALL_SUPPORTED_TEXT_ATTACHMENTS_SCANNED_WITH_NO_EXACT_VARIANT_OR_WEAK_UQQ700_TERM_OBSERVED"
        next_action = "OPERATIONALLY_RECONCILE_PLANNING_DOCUMENT_SOURCE_FAMILY_NO_HIT_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_SCAN_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_SUPPORTED_TEXT_ATTACHMENTS_REMAIN_TECHNICALLY_UNSCANNED_SO_SOURCE_FAMILY_CONTENT_NO_HIT_CANNOT_CLOSE"
        next_action = "HARDEN_ONLY_TECHNICAL_UNKNOWN_ATTACHMENTS_OR_PARSER_COVERAGE_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-150-S227D",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_inventory_qualified": inventory_qualified,
        "target_query_executed": True,
        "binary_download_executed": True,
        "image_ocr_executed": False,
        "canonical_attachment_count": len(attachments),
        "extension_counts": dict(sorted(ext_counts.items())),
        "download_success_count": download_success,
        "pdf_parse_success_count": pdf_parse_success,
        "hwp_parse_success_count": hwp_parse_success,
        "hwpx_parse_success_count": hwpx_parse_success,
        "technical_unknown_count": technical_unknown,
        "non_text_attachment_count": non_text,
        "text_target_count": text_target_count,
        "fully_scanned_text_count": fully_scanned_text_count,
        "status_counts": dict(status_counts),
        "exact_content_hit_count": len(exact_hits),
        "variant_content_hit_count": len(variant_hits),
        "weak_content_hit_count": len(weak_hits),
        "content_no_hit_count": len(no_hits),
        "content_scan_complete": content_scan_complete,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "content_hit_equals_designation_notice": False,
            "content_hit_equals_current_validity": False,
            "content_hit_equals_site_inclusion": False,
            "content_no_hit_equals_legal_absence": False,
            "technical_unknown_equals_legal_absence": False,
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

    print("\nCONTENT SCAN SUMMARY")
    print("-" * 78)
    print(f"TOTAL CANONICAL ATTACHMENTS: {len(attachments)}")
    print(f"DOWNLOAD SUCCESS COUNT: {download_success}")
    print(f"PDF PARSE SUCCESS COUNT: {pdf_parse_success}")
    print(f"HWP PARSE SUCCESS COUNT: {hwp_parse_success}")
    print(f"HWPX PARSE SUCCESS COUNT: {hwpx_parse_success}")
    print(f"NON-TEXT ATTACHMENT COUNT: {non_text}")
    print(f"TECHNICAL UNKNOWN COUNT: {technical_unknown}")
    print(f"EXACT CONTENT HIT COUNT: {len(exact_hits)}")
    print(f"VARIANT CONTENT HIT COUNT: {len(variant_hits)}")
    print(f"WEAK CONTENT HIT COUNT: {len(weak_hits)}")
    print(f"CONTENT NO HIT COUNT: {len(no_hits)}")
    print(f"STATUS COUNTS: {dict(status_counts)}")

    print("\nHITS")
    print("-" * 78)
    for row in (exact_hits + variant_hits + weak_hits)[:50]:
        print(f"{row['status']} | PSTSN={row['pstSn']} | FILENO={row['fileNo']} | {row['name']}")
        print(f"  exact={row['exact_terms']} variant={row['variant_terms']} weak={row['weak_terms']}")

    if technical_rows:
        print("\nTECHNICAL UNKNOWN SAMPLE")
        print("-" * 78)
        for row in technical_rows[:30]:
            print(f"PSTSN={row['pstSn']} FILENO={row['fileNo']} EXT={row['extension']} NAME={row['name']}")
            print(f"  parser={row['parser']} detail={row['parser_detail']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"PRIOR CANONICAL INVENTORY QUALIFIED: {inventory_qualified}")
    print(f"CONTENT SCAN COMPLETE: {content_scan_complete}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Content hit == designation/current validity/site inclusion: False")
    print("Content no-hit == legal absence: False")
    print("Technical unknown == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227B inventory qualified": inventory_qualified,
        "attachment count preserved": len(attachments) == int(prior.get("canonical_attachment_count") or -1),
        "image OCR disabled": out["image_ocr_executed"] is False,
        "content hit not designation": out["summary"]["content_hit_equals_designation_notice"] is False,
        "content hit not validity": out["summary"]["content_hit_equals_current_validity"] is False,
        "content hit not site inclusion": out["summary"]["content_hit_equals_site_inclusion"] is False,
        "content no-hit not legal absence": out["summary"]["content_no_hit_equals_legal_absence"] is False,
        "technical unknown not legal absence": out["summary"]["technical_unknown_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_WEAK_UQQ700_TERM_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_SCAN_COMPLETE_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_CANONICAL_CONTENT_SCAN_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227D validation failed")


if __name__ == "__main__":
    main()
