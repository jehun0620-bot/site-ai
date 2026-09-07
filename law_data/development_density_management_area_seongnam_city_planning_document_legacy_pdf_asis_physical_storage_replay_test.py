# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urljoin, urlparse

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_storage_reverse_discovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_legacy_pdf_asis_physical_storage_replay.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"
HOST = "https://www.seongnam.go.kr"

EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]


def curl(url: str) -> dict:
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


def extract_pdf_text(body: bytes) -> tuple[str | None, str | None]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(body))
        chunks = []
        for i, page in enumerate(reader.pages, 1):
            try:
                chunks.append(page.extract_text() or "")
            except Exception as e:
                return None, f"PAGE_{i}_ERROR:{type(e).__name__}:{e}"
        return "\n".join(chunks), None
    except Exception as e:
        return None, f"PDF_PARSE_ERROR:{type(e).__name__}:{e}"


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


def recover_flpth(row: dict) -> str | None:
    metadata = row.get("metadata") or {}
    flpth = metadata.get("flpth")
    if isinstance(flpth, str) and flpth.strip():
        return flpth.strip()

    # S227I may have observed the directory as a metadata-derived probe even if
    # its broad storage-field filter did not retain the key in STORAGE_FIELDS.
    for probe in row.get("probes", []) or []:
        if probe.get("source") == "metadata:flpth":
            url = probe.get("url")
            if isinstance(url, str) and url.startswith(HOST):
                path = urlparse(url).path
                if path:
                    return path if path.endswith("/") else path + "/"
    return None


def build_physical_url(flpth: str | None, stre_file_nm: str | None) -> str | None:
    if not flpth or not stre_file_nm:
        return None
    base = flpth if flpth.endswith("/") else flpth + "/"
    return urljoin(HOST, base + stre_file_nm.lstrip("/"))


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT LEGACY PDF ASIS PHYSICAL STORAGE REPLAY - S227J")
    print("=" * 78)
    print("Purpose: replay only metadata-derived flpth + streFileNm physical URLs")
    print("Arbitrary route guessing: DISABLED")
    print("Physical 404 != legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227I output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    targets = prior.get("results") or []

    results = []
    recovered = remaining = exact_hits = variant_hits = weak_hits = no_hits = 0
    physical_identity_count = 0
    expected_size_match_count = 0

    for idx, row in enumerate(targets, 1):
        metadata = row.get("metadata") or {}
        pst_sn = str(row.get("pstSn"))
        file_no = str(row.get("fileNo"))
        stre_file_nm = metadata.get("streFileNm") or (row.get("identifier_snapshot") or {}).get("streFileNm")
        expected_size = metadata.get("fileSize") or (row.get("identifier_snapshot") or {}).get("fileSize")
        try:
            expected_size = int(expected_size) if expected_size is not None else None
        except Exception:
            expected_size = None
        flpth = recover_flpth(row)
        physical_url = build_physical_url(flpth, stre_file_nm)
        if physical_url:
            physical_identity_count += 1

        rec = {
            "pstSn": pst_sn,
            "fileNo": file_no,
            "name": row.get("name"),
            "flpth": flpth,
            "streFileNm": stre_file_nm,
            "expected_file_size": expected_size,
            "physical_url": physical_url,
            "http": None,
            "final_url": None,
            "redirects": None,
            "content_type": None,
            "body_size": 0,
            "body_prefix_hex": "",
            "pdf_magic": False,
            "expected_size_match": False,
            "status": "ASIS_PHYSICAL_BINARY_ACCESS_TECHNICAL_UNKNOWN",
            "error": None,
            "exact_terms": [],
            "variant_terms": [],
            "weak_terms": [],
        }

        if not physical_url:
            rec["error"] = "FLPTH_OR_STREFILENM_NOT_AVAILABLE"
            remaining += 1
            results.append(rec)
            continue

        rr = curl(physical_url)
        body = rr.get("body") or b""
        rec.update({
            "http": rr.get("http"),
            "final_url": rr.get("final_url"),
            "redirects": rr.get("redirects"),
            "content_type": rr.get("content_type"),
            "body_size": len(body),
            "body_prefix_hex": body[:24].hex(),
            "pdf_magic": body.startswith(b"%PDF-"),
        })
        rec["expected_size_match"] = expected_size is not None and len(body) == expected_size
        if rec["expected_size_match"]:
            expected_size_match_count += 1

        if rr.get("http") == "200" and rec["pdf_magic"]:
            text, err = extract_pdf_text(body)
            if text is None:
                rec["error"] = err
                remaining += 1
            else:
                rec.update(scan_terms(text))
                recovered += 1
                if rec["status"] == "EXACT_CONTENT_HIT": exact_hits += 1
                elif rec["status"] == "VARIANT_CONTENT_HIT": variant_hits += 1
                elif rec["status"] == "WEAK_CONTENT_HIT": weak_hits += 1
                elif rec["status"] == "CONTENT_NO_HIT": no_hits += 1
        else:
            rec["error"] = f"PHYSICAL_BINARY_NOT_RECOVERED_HTTP_{rr.get('http')}_PDF_{rec['pdf_magic']}"
            remaining += 1

        results.append(rec)
        print(
            f"ASIS REPLAY: {idx}/{len(targets)} | PSTSN={pst_sn} | FILENO={file_no} | "
            f"HTTP={rec['http']} | PDF={rec['pdf_magic']} | SIZE_MATCH={rec['expected_size_match']} | STATUS={rec['status']}"
        )

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_UQQ700_CANDIDATE_HIT"
        semantic = "METADATA_DERIVED_ASIS_PHYSICAL_BINARY_RECOVERY_RETURNED_EXACT_OR_VARIANT_UQQ700_TERM"
        next_action = "REVIEW_ONLY_RECOVERED_CANDIDATE_CONTEXT_AND_TRACE_LITERAL_OFFICIAL_NOTICE_IDENTITY_NON_PROMOTIONALLY"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_WEAK_HIT"
        semantic = "METADATA_DERIVED_ASIS_PHYSICAL_BINARY_RECOVERY_RETURNED_WEAK_DENSITY_TERM_ONLY"
        next_action = "REVIEW_RECOVERED_WEAK_CONTEXT_NON_PROMOTIONALLY_BEFORE_SOURCE_FAMILY_RECONCILIATION"
    elif remaining == 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_RECOVERY_COMPLETE_NO_UQQ700_HIT"
        semantic = "ALL_SIX_METADATA_DERIVED_ASIS_PHYSICAL_PDFS_RECOVERED_AND_SCANNED_WITH_NO_UQQ700_TERM"
        next_action = "RECONCILE_PLANNING_DOCUMENT_SOURCE_FAMILY_OPERATIONALLY_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_BINARY_ACCESS_TECHNICAL_UNKNOWN"
        semantic = "ASIS_PHYSICAL_STORAGE_IDENTITY_WAS_CONSTRUCTED_FROM_SERVER_METADATA_BUT_ONE_OR_MORE_BINARIES_REMAIN_HTTP_INACCESSIBLE"
        next_action = "DECIDE_NON_NEGATIVE_OPERATIONAL_RECONCILIATION_OR_ARCHIVAL_STORAGE_FAMILY_ESCALATION_WITHOUT_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-156-S227J",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": PRIOR_OUT.exists(),
        "target_count": len(targets),
        "physical_storage_identity_count": physical_identity_count,
        "recovered_pdf_count": recovered,
        "remaining_technical_unknown_count": remaining,
        "expected_size_match_count": expected_size_match_count,
        "exact_content_hit_count": exact_hits,
        "variant_content_hit_count": variant_hits,
        "weak_content_hit_count": weak_hits,
        "content_no_hit_count": no_hits,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "physical_storage_identity_equals_binary_presence": False,
            "physical_404_equals_legal_absence": False,
            "physical_recovery_hit_equals_designation_notice": False,
            "physical_recovery_hit_equals_current_validity": False,
            "physical_recovery_hit_equals_site_inclusion": False,
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

    print("\nASIS PHYSICAL STORAGE REPLAY SUMMARY")
    print("-" * 78)
    print(f"TARGET COUNT: {len(targets)}")
    print(f"PHYSICAL STORAGE IDENTITY COUNT: {physical_identity_count}")
    print(f"RECOVERED PDF COUNT: {recovered}")
    print(f"REMAINING TECHNICAL UNKNOWN COUNT: {remaining}")
    print(f"EXPECTED SIZE MATCH COUNT: {expected_size_match_count}")
    print(f"EXACT CONTENT HIT COUNT: {exact_hits}")
    print(f"VARIANT CONTENT HIT COUNT: {variant_hits}")
    print(f"WEAK CONTENT HIT COUNT: {weak_hits}")
    print(f"CONTENT NO HIT COUNT: {no_hits}")

    print("\nDETAILS")
    print("-" * 78)
    for r in results:
        print(f"PSTSN={r['pstSn']} FILENO={r['fileNo']} NAME={r['name']} STATUS={r['status']}")
        print(f"  FLPTH={r['flpth']} STREFILENM={r['streFileNm']} EXPECTED_SIZE={r['expected_file_size']}")
        print(f"  PHYSICAL_URL={r['physical_url']}")
        print(f"  HTTP={r['http']} FINAL={r['final_url']} REDIRECTS={r['redirects']} CT={r['content_type']}")
        print(f"  BODY_SIZE={r['body_size']} PDF_MAGIC={r['pdf_magic']} SIZE_MATCH={r['expected_size_match']} PREFIX={r['body_prefix_hex']}")
        print(f"  EXACT={r['exact_terms']} VARIANT={r['variant_terms']} WEAK={r['weak_terms']} ERROR={r['error']}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("Physical storage identity == binary presence: False")
    print("Physical 404 == legal absence: False")
    print("Physical recovery hit == designation/current validity/site inclusion: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227I input exists": PRIOR_OUT.exists(),
        "ASIS targets present": len(targets) > 0,
        "physical identity derived": physical_identity_count == len(targets),
        "physical identity not binary presence": out["summary"]["physical_storage_identity_equals_binary_presence"] is False,
        "physical 404 not legal absence": out["summary"]["physical_404_equals_legal_absence"] is False,
        "physical hit not designation": out["summary"]["physical_recovery_hit_equals_designation_notice"] is False,
        "physical hit not validity": out["summary"]["physical_recovery_hit_equals_current_validity"] is False,
        "physical hit not site inclusion": out["summary"]["physical_recovery_hit_equals_site_inclusion"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_WEAK_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_STORAGE_RECOVERY_COMPLETE_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_ASIS_PHYSICAL_BINARY_ACCESS_TECHNICAL_UNKNOWN",
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
        raise AssertionError("S227J validation failed")


if __name__ == "__main__":
    main()
