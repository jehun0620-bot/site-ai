from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
EXPECTED_COUNT = 6
MAX_DOWNLOAD_BYTES = 25 * 1024 * 1024
CONNECT_TIMEOUT_SECONDS = 5
MAX_TIME_SECONDS = 30

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_getfile_binary_access_diagnostic.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "seongnam_legacy_pdf_exact_six_system_curl_tls_transport_diagnostic.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def select_routes(data: dict[str, Any]) -> list[dict[str, Any]]:
    routes = data.get("selected_getfile_routes")
    if not isinstance(routes, list) or len(routes) != EXPECTED_COUNT:
        return []
    selected: list[dict[str, Any]] = []
    for item in routes:
        if not isinstance(item, dict):
            return []
        url = item.get("url")
        identity = item.get("identity")
        target_index = item.get("target_index")
        if not isinstance(url, str) or not url.startswith("https://www.seongnam.go.kr/ct-bbs020101/getFile?"):
            return []
        if not isinstance(identity, dict):
            return []
        selected.append({"target_index": target_index, "identity": identity, "url": url})
    return selected


def curl_version(curl_path: str) -> dict[str, Any]:
    try:
        cp = subprocess.run(
            [curl_path, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        return {
            "returncode": cp.returncode,
            "stdout": cp.stdout.strip(),
            "stderr": cp.stderr.strip(),
        }
    except Exception as exc:
        return {"returncode": None, "stdout": "", "stderr": repr(exc)}


def parse_write_out(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def run_curl(curl_path: str, target: dict[str, Any]) -> dict[str, Any]:
    url = target["url"]
    result: dict[str, Any] = {
        "target_index": target["target_index"],
        "identity": target["identity"],
        "requested_url": url,
        "curl_returncode": None,
        "http_code": None,
        "final_url": None,
        "content_type": None,
        "download_size": 0,
        "pdf_signature": False,
        "technical_unknown": False,
        "stderr": None,
        "write_out_raw": None,
        "response_header_path": None,
    }

    with tempfile.TemporaryDirectory(prefix="seongnam_curl_") as td:
        td_path = Path(td)
        body_path = td_path / "body.bin"
        header_path = td_path / "headers.txt"
        write_out = (
            "HTTP_CODE=%{http_code}\n"
            "FINAL_URL=%{url_effective}\n"
            "CONTENT_TYPE=%{content_type}\n"
            "SIZE_DOWNLOAD=%{size_download}\n"
            "SSL_VERIFY_RESULT=%{ssl_verify_result}\n"
        )
        cmd = [
            curl_path,
            "--location",
            "--fail-with-body",
            "--connect-timeout", str(CONNECT_TIMEOUT_SECONDS),
            "--max-time", str(MAX_TIME_SECONDS),
            "--max-filesize", str(MAX_DOWNLOAD_BYTES),
            "--output", str(body_path),
            "--dump-header", str(header_path),
            "--write-out", write_out,
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            "--header", "Accept: application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
            "--referer", "https://www.seongnam.go.kr/",
            url,
        ]
        try:
            cp = subprocess.run(cmd, capture_output=True, text=True, timeout=MAX_TIME_SECONDS + 10, check=False)
            result["curl_returncode"] = cp.returncode
            result["stderr"] = cp.stderr.strip()
            result["write_out_raw"] = cp.stdout.strip()
            parsed = parse_write_out(cp.stdout)
            result["http_code"] = parsed.get("HTTP_CODE")
            result["final_url"] = parsed.get("FINAL_URL")
            result["content_type"] = parsed.get("CONTENT_TYPE")
            result["ssl_verify_result"] = parsed.get("SSL_VERIFY_RESULT")
            try:
                result["download_size"] = int(float(parsed.get("SIZE_DOWNLOAD", "0") or 0))
            except Exception:
                result["download_size"] = 0

            if body_path.exists():
                with body_path.open("rb") as fh:
                    prefix = fh.read(8)
                result["pdf_signature"] = prefix.startswith(b"%PDF-")
            if header_path.exists():
                result["response_headers"] = header_path.read_text(encoding="utf-8", errors="replace")[:20000]
            else:
                result["response_headers"] = ""

            if cp.returncode != 0 and not result["http_code"]:
                result["technical_unknown"] = True
        except Exception as exc:
            result["technical_unknown"] = True
            result["stderr"] = repr(exc)
    return result


def main() -> int:
    print("=" * 82)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("SEONGNAM LEGACY PDF EXACT-SIX SYSTEM CURL TLS TRANSPORT DIAGNOSTIC")
    print("=" * 82)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print("Recorded exact getFile URLs only: ENABLED")
    print("URL mutation/guessing: DISABLED")
    print("curl --insecure/-k: DISABLED")
    print("Python SSL context mutation: DISABLED")
    print("ASIS physical URL retry: DISABLED")
    print("OCR/content search: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    try:
        data = load_json(INPUT_PATH)
    except Exception as exc:
        data = {}
        diagnostics.append({"type": "input_load_error", "error": repr(exc)})

    routes = select_routes(data)
    curl_path = shutil.which("curl.exe") or shutil.which("curl")
    curl_info = curl_version(curl_path) if curl_path else {"returncode": None, "stdout": "", "stderr": "curl not found"}

    prerequisite_valid = (
        data.get("classification") == "SEONGNAM_LEGACY_PDF_EXACT_SIX_GETFILE_BINARY_ACCESS_DIAGNOSTIC_EXECUTED"
        and data.get("resolution") == "UNKNOWN"
        and len(routes) == EXPECTED_COUNT
        and curl_path is not None
    )

    print("PREREQUISITE VALIDATION")
    print("-" * 82)
    print(f"Validated exact-six curl prerequisite: {prerequisite_valid}")
    print(f"Selected route count: {len(routes)}")
    print(f"curl path: {curl_path}")
    print("curl version:")
    print(curl_info.get("stdout", ""))
    print()

    results: list[dict[str, Any]] = []
    network_access_used = False
    if prerequisite_valid and curl_path:
        network_access_used = True
        for route in routes:
            results.append(run_curl(curl_path, route))

    print("SYSTEM CURL RESULTS")
    print("-" * 82)
    for result in results:
        print(f"TARGET {result['target_index']}: {json.dumps(result['identity'], ensure_ascii=False)}")
        for key in (
            "requested_url", "curl_returncode", "http_code", "final_url", "content_type",
            "ssl_verify_result", "download_size", "pdf_signature", "technical_unknown", "stderr",
        ):
            print(f"  {key}={result.get(key)}")
        print()

    curl_success_count = sum(1 for r in results if r.get("curl_returncode") == 0)
    http_200_count = sum(1 for r in results if str(r.get("http_code")) == "200")
    pdf_signature_count = sum(1 for r in results if r.get("pdf_signature") is True)
    technical_unknown_count = sum(1 for r in results if r.get("technical_unknown") is True)

    if not prerequisite_valid:
        classification = "SEONGNAM_LEGACY_PDF_SYSTEM_CURL_TLS_TRANSPORT_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_EXACT_SIX_GETFILE_AND_SYSTEM_CURL_PREREQUISITES_WITHOUT_URL_GUESSING_OR_SSL_BYPASS"
    else:
        classification = "SEONGNAM_LEGACY_PDF_EXACT_SIX_SYSTEM_CURL_TLS_TRANSPORT_DIAGNOSTIC_EXECUTED"
        if pdf_signature_count == EXPECTED_COUNT:
            next_action = "TREAT_PYTHON_REQUESTS_FAILURE_AS_CLIENT_TLS_STACK_SPECIFIC_AND_ASSESS_ONLY_THE_SIX_CURL_CONFIRMED_BINARY_PDFS_IN_A_SEPARATELY_APPROVED_IDENTITY_STEP"
        elif curl_success_count > 0 or http_200_count > 0:
            next_action = "COMPARE_CURL_RESPONSE_MECHANICS_WITH_PYTHON_REQUESTS_WITHOUT_SSL_BYPASS_OR_NEGATIVE_EVIDENCE"
        else:
            next_action = "KEEP_TRANSPORT_TECHNICAL_UNKNOWN_AND_INSPECT_SYSTEM_TLS_OR_NETWORK_PATH_WITHOUT_URL_MUTATION_SSL_BYPASS_OR_NEGATIVE_EVIDENCE"

    safety = {
        "network_access_used": network_access_used,
        "uqq700_query_executed": False,
        "url_mutation_used": False,
        "url_guessing_used": False,
        "curl_insecure_used": False,
        "python_ssl_context_mutation_used": False,
        "asis_physical_url_retried": False,
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
        "url_mutation_disabled": safety["url_mutation_used"] is False,
        "url_guessing_disabled": safety["url_guessing_used"] is False,
        "curl_insecure_disabled": safety["curl_insecure_used"] is False,
        "python_ssl_context_unchanged": safety["python_ssl_context_mutation_used"] is False,
        "asis_physical_url_not_retried": safety["asis_physical_url_retried"] is False,
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
        "curl_path": curl_path,
        "curl_version": curl_info,
        "selected_routes": routes,
        "results": results,
        "curl_success_count": curl_success_count,
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
    print(f"curl success count: {curl_success_count}")
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
    print("URL mutation/guessing used: False")
    print("curl --insecure/-k used: False")
    print("Python SSL context mutation used: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
