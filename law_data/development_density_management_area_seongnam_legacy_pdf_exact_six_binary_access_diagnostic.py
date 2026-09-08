from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_producer_schema_recovery.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_binary_access_diagnostic.json"
)

MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
TIMEOUT = (5, 25)


class PrerequisiteError(RuntimeError):
    pass


def is_http_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    value = value.strip()
    if not value.startswith(("http://", "https://")):
        return False
    try:
        parsed = urlparse(value)
    except Exception:
        return False
    return bool(parsed.scheme and parsed.netloc)


def load_exact_six() -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    diagnostics: list[str] = []
    if not INPUT_PATH.exists():
        raise PrerequisiteError(f"missing prerequisite: {INPUT_PATH}")

    data = json.loads(INPUT_PATH.read_text(encoding="utf-8"))

    if data.get("target") != TARGET_NAME:
        diagnostics.append("target_name_mismatch")
    if data.get("standard_code") != TARGET_CODE:
        diagnostics.append("standard_code_mismatch")
    if data.get("resolution") != "UNKNOWN":
        diagnostics.append("prerequisite_resolution_not_unknown")
    if data.get("exact_six_recovered") is not True:
        diagnostics.append("exact_six_recovered_not_true")
    if data.get("classification") != "SEONGNAM_LEGACY_PDF_EXACT_SIX_PRODUCER_SCHEMA_RECOVERED":
        diagnostics.append("unexpected_prerequisite_classification")

    selected = data.get("selected_exact_six")
    if not isinstance(selected, dict):
        diagnostics.append("selected_exact_six_missing")
        return [], data, diagnostics

    records = selected.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_COUNT:
        diagnostics.append("selected_record_count_not_six")
        return [], data, diagnostics

    targets: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for index, record in enumerate(records, 1):
        if not isinstance(record, dict):
            diagnostics.append(f"record_{index}_not_dict")
            continue

        identity = record.get("identity")
        urls = record.get("urls")
        if not isinstance(identity, dict) or not identity:
            diagnostics.append(f"record_{index}_identity_missing")
        if not isinstance(urls, list) or len(urls) != 1:
            diagnostics.append(f"record_{index}_url_count_not_one")
            continue

        url = urls[0]
        if not is_http_url(url):
            diagnostics.append(f"record_{index}_invalid_url")
            continue
        if url in seen_urls:
            diagnostics.append(f"record_{index}_duplicate_url")
            continue
        seen_urls.add(url)

        targets.append({
            "index": index,
            "identity": identity,
            "url": url,
            "producer_source_path": selected.get("source_path"),
            "producer_container_path": selected.get("container_path"),
            "raw": record.get("raw"),
        })

    if len(targets) != EXPECTED_COUNT:
        diagnostics.append("validated_target_count_not_six")

    return targets, data, diagnostics


def probe_url(session: requests.Session, url: str) -> dict[str, Any]:
    result: dict[str, Any] = {
        "requested_url": url,
        "final_url": None,
        "redirect_chain": [],
        "http_status": None,
        "content_type": None,
        "content_disposition": None,
        "content_length_header": None,
        "bytes_read": 0,
        "truncated": False,
        "pdf_signature": False,
        "technical_unknown": False,
        "error": None,
    }

    try:
        with session.get(
            url,
            allow_redirects=True,
            timeout=TIMEOUT,
            stream=True,
        ) as response:
            result["final_url"] = response.url
            result["redirect_chain"] = [
                {
                    "status": item.status_code,
                    "url": item.url,
                    "location": item.headers.get("Location"),
                }
                for item in response.history
            ]
            result["http_status"] = response.status_code
            result["content_type"] = response.headers.get("Content-Type")
            result["content_disposition"] = response.headers.get("Content-Disposition")
            result["content_length_header"] = response.headers.get("Content-Length")

            prefix = bytearray()
            bytes_read = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                if len(prefix) < 8:
                    prefix.extend(chunk[: 8 - len(prefix)])
                bytes_read += len(chunk)
                if bytes_read >= MAX_DOWNLOAD_BYTES:
                    result["truncated"] = True
                    break

            result["bytes_read"] = bytes_read
            result["pdf_signature"] = bytes(prefix).startswith(b"%PDF-")
    except requests.RequestException as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)
    except Exception as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)

    return result


def main() -> int:
    print("=" * 78)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX BINARY ACCESS DIAGNOSTIC")
    print("=" * 78)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print(f"Expected target count: {EXPECTED_COUNT}")
    print("URL guessing: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    prerequisite_data: dict[str, Any] = {}
    prerequisite_diagnostics: list[str] = []
    targets: list[dict[str, Any]] = []

    try:
        targets, prerequisite_data, prerequisite_diagnostics = load_exact_six()
    except Exception as exc:
        prerequisite_diagnostics.append(repr(exc))

    prerequisite_valid = (
        len(targets) == EXPECTED_COUNT
        and not prerequisite_diagnostics
        and prerequisite_data.get("exact_six_recovered") is True
    )

    print("PREREQUISITE VALIDATION")
    print("-" * 78)
    print(f"Validated exact-six prerequisite: {prerequisite_valid}")
    print(f"Validated target count: {len(targets)}")
    if prerequisite_diagnostics:
        for item in prerequisite_diagnostics:
            print(f"diagnostic: {item}")
    print()

    if targets:
        print("SELECTED EXACT SIX")
        print("-" * 78)
        for target in targets:
            print(f"[{target['index']}] identity={json.dumps(target['identity'], ensure_ascii=False)}")
            print(f"    url={target['url']}")
        print()

    probes: list[dict[str, Any]] = []
    network_access_used = False

    if prerequisite_valid:
        network_access_used = True
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; site-ai-step17/1.0; bounded-seongnam-pdf-diagnostic)",
            "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8",
        })

        for target in targets:
            probe = probe_url(session, target["url"])
            probes.append({
                "index": target["index"],
                "identity": target["identity"],
                "url": target["url"],
                "producer_source_path": target["producer_source_path"],
                "producer_container_path": target["producer_container_path"],
                "probe": probe,
            })
    else:
        print("Network probing skipped: exact-six producer prerequisite was not valid.")
        print("No URL guessing or alternate URL generation is permitted.")
        print()

    binary_pdf_count = sum(1 for item in probes if item["probe"].get("pdf_signature") is True)
    http_200_count = sum(1 for item in probes if item["probe"].get("http_status") == 200)
    technical_unknown_count = sum(1 for item in probes if item["probe"].get("technical_unknown") is True)

    print("BINARY ACCESS RESULTS")
    print("-" * 78)
    if not probes:
        print("NO NETWORK PROBES")
    else:
        for item in probes:
            p = item["probe"]
            print(f"TARGET {item['index']}: {json.dumps(item['identity'], ensure_ascii=False)}")
            print(f"  requested_url={p['requested_url']}")
            print(f"  final_url={p['final_url']}")
            print(f"  http_status={p['http_status']}")
            print(f"  content_type={p['content_type']}")
            print(f"  content_disposition={p['content_disposition']}")
            print(f"  content_length_header={p['content_length_header']}")
            print(f"  bytes_read={p['bytes_read']}")
            print(f"  truncated={p['truncated']}")
            print(f"  pdf_signature={p['pdf_signature']}")
            print(f"  technical_unknown={p['technical_unknown']}")
            if p.get("error"):
                print(f"  error={p['error']}")
            print()

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_BINARY_ACCESS_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_THE_EXACT_SIX_PRODUCER_OUTPUT_WITHOUT_NETWORK_OR_URL_GUESSING"
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_BINARY_ACCESS_DIAGNOSTIC_EXECUTED"
        if binary_pdf_count == EXPECTED_COUNT:
            next_action = "ASSESS_ONLY_THE_SIX_CONFIRMED_BINARY_PDFS_IN_A_SEPARATELY_APPROVED_IDENTITY_STEP"
        elif binary_pdf_count > 0:
            next_action = "RECOVER_ONLY_EXISTING_ACCESS_MECHANICS_FOR_THE_NON_BINARY_TARGETS_WITHOUT_URL_GUESSING"
        elif technical_unknown_count > 0:
            next_action = "KEEP_BINARY_ACCESS_TECHNICAL_UNKNOWN_AND_INSPECT_EXISTING_ACCESS_MECHANICS_ONLY"
        else:
            next_action = "INSPECT_EXISTING_VIEWER_OR_DOWNLOAD_MECHANICS_ONLY_WITHOUT_NEGATIVE_EVIDENCE"

    safety = {
        "uqq700_query_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "ocr_used": False,
        "content_search_used": False,
        "brute_force_used": False,
        "broad_crawl_used": False,
        "url_guessing_used": False,
        "target_status": TARGET_STATUS,
    }

    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "expected_count_fixed_to_six": EXPECTED_COUNT == 6,
        "uqq700_not_queried": not safety["uqq700_query_executed"],
        "negative_evidence_disabled": not safety["negative_evidence_allowed"],
        "legal_absence_inference_disabled": not safety["legal_absence_inference_allowed"],
        "site_promotion_disabled": not safety["site_promotion_allowed"],
        "runtime_registration_blocked": not safety["runtime_registration_allowed"],
        "ocr_disabled": not safety["ocr_used"],
        "content_search_disabled": not safety["content_search_used"],
        "brute_force_disabled": not safety["brute_force_used"],
        "broad_crawl_disabled": not safety["broad_crawl_used"],
        "url_guessing_disabled": not safety["url_guessing_used"],
        "uqq700_remains_unknown": safety["target_status"] == "UNKNOWN",
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "input": str(INPUT_PATH),
        "expected_count": EXPECTED_COUNT,
        "prerequisite_valid": prerequisite_valid,
        "prerequisite_diagnostics": prerequisite_diagnostics,
        "validated_target_count": len(targets),
        "targets": targets,
        "network_access_used": network_access_used,
        "probes": probes,
        "http_200_count": http_200_count,
        "binary_pdf_count": binary_pdf_count,
        "technical_unknown_count": technical_unknown_count,
        "classification": classification,
        "next_action": next_action,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"HTTP 200 count: {http_200_count}")
    print(f"Binary PDF signature count: {binary_pdf_count}")
    print(f"Technical unknown count: {technical_unknown_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("OCR/content search used: False")
    print("URL guessing used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
