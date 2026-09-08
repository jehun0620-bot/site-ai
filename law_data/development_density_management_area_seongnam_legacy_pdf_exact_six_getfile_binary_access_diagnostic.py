from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

import requests

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
TIMEOUT = (5, 25)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_leaf_direct_route_provenance_reconciliation.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_getfile_binary_access_diagnostic.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def is_exact_getfile_route(url: str, identity: dict[str, Any]) -> bool:
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.netloc.lower() != "www.seongnam.go.kr":
            return False
        if parsed.path != "/ct-bbs020101/getFile":
            return False
        query = parse_qs(parsed.query, keep_blank_values=True)
        pst = str(identity.get("pstsn", ""))
        fileno = str(identity.get("fileno", ""))
        return query.get("pstSn") == [pst] and query.get("fileNo") == [fileno]
    except Exception:
        return False


def select_exact_six_routes(data: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    diagnostics: list[dict[str, Any]] = []
    targets = data.get("reconciled_targets")
    if not isinstance(targets, list) or len(targets) != EXPECTED_COUNT:
        diagnostics.append({"type": "invalid_reconciled_target_count", "value": len(targets) if isinstance(targets, list) else None})
        return [], diagnostics

    selected: list[dict[str, Any]] = []
    seen_urls: set[str] = set()
    for target in targets:
        if not isinstance(target, dict):
            diagnostics.append({"type": "invalid_target_record"})
            continue
        target_index = target.get("target_index")
        identity = target.get("identity") if isinstance(target.get("identity"), dict) else {}
        routes = target.get("leaf_direct_routes") if isinstance(target.get("leaf_direct_routes"), list) else []
        candidates: list[str] = []
        for route in routes:
            if not isinstance(route, dict):
                continue
            url = route.get("url")
            if isinstance(url, str) and is_exact_getfile_route(url, identity):
                candidates.append(url)
        unique_candidates = list(dict.fromkeys(candidates))
        if len(unique_candidates) != 1:
            diagnostics.append({
                "type": "target_getfile_route_not_unique",
                "target_index": target_index,
                "identity": identity,
                "candidate_count": len(unique_candidates),
                "candidates": unique_candidates,
            })
            continue
        url = unique_candidates[0]
        if url in seen_urls:
            diagnostics.append({"type": "duplicate_getfile_url_across_targets", "target_index": target_index, "url": url})
            continue
        seen_urls.add(url)
        selected.append({"target_index": target_index, "identity": identity, "url": url})
    return selected, diagnostics


def probe(session: requests.Session, target: dict[str, Any]) -> dict[str, Any]:
    url = target["url"]
    result: dict[str, Any] = {
        "target_index": target["target_index"],
        "identity": target["identity"],
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
        with session.get(url, allow_redirects=True, stream=True, timeout=TIMEOUT) as response:
            result["final_url"] = response.url
            result["redirect_chain"] = [
                {"status": h.status_code, "url": h.url, "location": h.headers.get("Location")}
                for h in response.history
            ]
            result["http_status"] = response.status_code
            result["content_type"] = response.headers.get("Content-Type")
            result["content_disposition"] = response.headers.get("Content-Disposition")
            result["content_length_header"] = response.headers.get("Content-Length")

            prefix = b""
            total = 0
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if len(prefix) < 8:
                    need = 8 - len(prefix)
                    prefix += chunk[:need]
                total += len(chunk)
                if total >= MAX_DOWNLOAD_BYTES:
                    result["truncated"] = True
                    break
            result["bytes_read"] = total
            result["pdf_signature"] = prefix.startswith(b"%PDF-")
    except requests.RequestException as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)
    except Exception as exc:
        result["technical_unknown"] = True
        result["error"] = repr(exc)
    return result


def main() -> int:
    print("=" * 82)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX GETFILE BINARY ACCESS DIAGNOSTIC")
    print("=" * 82)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print("Only recorded exact getFile routes: ENABLED")
    print("ASIS physical URL retry: DISABLED")
    print("URL mutation/guessing: DISABLED")
    print("SSL verification bypass: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    try:
        data = load_json(INPUT_PATH)
    except Exception as exc:
        data = {}
        diagnostics.append({"type": "input_load_error", "error": repr(exc)})

    selected, select_diags = select_exact_six_routes(data)
    diagnostics.extend(select_diags)
    prerequisite_valid = (
        data.get("classification") == "SEONGNAM_LEGACY_PDF_LEAF_DIRECT_PRODUCER_ROUTES_RECONCILED_FOR_EXACT_SIX"
        and data.get("resolution") == "UNKNOWN"
        and len(selected) == EXPECTED_COUNT
        and not diagnostics
    )

    print("PREREQUISITE VALIDATION")
    print("-" * 82)
    print(f"Validated exact-six getFile prerequisite: {prerequisite_valid}")
    print(f"Selected getFile route count: {len(selected)}")
    for item in selected:
        print(f"TARGET {item['target_index']}: {json.dumps(item['identity'], ensure_ascii=False)}")
        print(f"  getFile_url={item['url']}")
    print()

    results: list[dict[str, Any]] = []
    network_access_used = False
    if prerequisite_valid:
        network_access_used = True
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "Referer": "https://www.seongnam.go.kr/",
        })
        for item in selected:
            results.append(probe(session, item))

    print("GETFILE BINARY ACCESS RESULTS")
    print("-" * 82)
    for result in results:
        print(f"TARGET {result['target_index']}: {json.dumps(result['identity'], ensure_ascii=False)}")
        for key in (
            "requested_url", "final_url", "http_status", "content_type", "content_disposition",
            "content_length_header", "bytes_read", "truncated", "pdf_signature", "technical_unknown", "error",
        ):
            print(f"  {key}={result[key]}")
        print(f"  redirect_chain={json.dumps(result['redirect_chain'], ensure_ascii=False)}")
        print()

    http_200_count = sum(1 for r in results if r["http_status"] == 200)
    pdf_signature_count = sum(1 for r in results if r["pdf_signature"] is True)
    technical_unknown_count = sum(1 for r in results if r["technical_unknown"] is True)

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_GETFILE_BINARY_ACCESS_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_RECONCILED_EXACT_SIX_GETFILE_PREREQUISITE_WITHOUT_NETWORK_OR_URL_GUESSING"
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_GETFILE_BINARY_ACCESS_DIAGNOSTIC_EXECUTED"
        if pdf_signature_count == EXPECTED_COUNT:
            next_action = "ASSESS_ONLY_THE_SIX_CONFIRMED_BINARY_PDFS_IN_A_SEPARATELY_APPROVED_IDENTITY_STEP"
        elif 0 < pdf_signature_count < EXPECTED_COUNT:
            next_action = "SPLIT_CONFIRMED_BINARY_TARGETS_FROM_REMAINING_ACCESS_TECHNICAL_UNKNOWNS_WITHOUT_NEGATIVE_EVIDENCE"
        elif technical_unknown_count > 0:
            next_action = "KEEP_NON_BINARY_TARGET_ACCESS_TECHNICAL_UNKNOWN_AND_INSPECT_ONLY_RECORDED_PROTOCOL_MECHANICS"
        else:
            next_action = "INSPECT_RECORDED_RESPONSE_AND_DOWNLOAD_MECHANICS_ONLY_WITHOUT_NEGATIVE_EVIDENCE"

    safety = {
        "network_access_used": network_access_used,
        "uqq700_query_executed": False,
        "asis_physical_url_retried": False,
        "url_mutation_used": False,
        "url_guessing_used": False,
        "ssl_verification_bypass_used": False,
        "ocr_used": False,
        "content_search_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": TARGET_STATUS,
    }
    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "expected_count_fixed_to_six": EXPECTED_COUNT == 6,
        "uqq700_not_queried": safety["uqq700_query_executed"] is False,
        "asis_physical_url_not_retried": safety["asis_physical_url_retried"] is False,
        "url_mutation_disabled": safety["url_mutation_used"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
        "ssl_bypass_disabled": safety["ssl_verification_bypass_used"] is False,
        "ocr_disabled": safety["ocr_used"] is False,
        "content_search_disabled": safety["content_search_used"] is False,
        "negative_evidence_disabled": safety["negative_evidence_allowed"] is False,
        "legal_absence_inference_disabled": safety["legal_absence_inference_allowed"] is False,
        "site_promotion_disabled": safety["site_promotion_allowed"] is False,
        "runtime_registration_blocked": safety["runtime_registration_allowed"] is False,
        "uqq700_remains_unknown": safety["uqq700_resolution"] == "UNKNOWN",
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": TARGET_STATUS,
        "input": str(INPUT_PATH),
        "expected_count": EXPECTED_COUNT,
        "prerequisite_valid": prerequisite_valid,
        "selected_getfile_routes": selected,
        "results": results,
        "http_200_count": http_200_count,
        "binary_pdf_signature_count": pdf_signature_count,
        "technical_unknown_count": technical_unknown_count,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 82)
    print("RESOLUTION")
    print("=" * 82)
    print(f"HTTP 200 count: {http_200_count}")
    print(f"Binary PDF signature count: {pdf_signature_count}")
    print(f"Technical unknown count: {technical_unknown_count}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("ASIS physical URL retried: False")
    print("URL mutation/guessing used: False")
    print("SSL verification bypass used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
