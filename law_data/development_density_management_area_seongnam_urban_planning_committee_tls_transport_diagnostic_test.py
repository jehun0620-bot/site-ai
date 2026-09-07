# -*- coding: utf-8 -*-
from __future__ import annotations

import importlib.util
import json
import platform
import shutil
import ssl
import subprocess
import sys
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_seongnam_urban_planning_committee_tls_transport_diagnostic.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_URBAN_PLANNING_COMMITTEE_RECORD"

ROOT_URL = "https://www.seongnam.go.kr/"
DETAIL_URL = "https://www.seongnam.go.kr/city/1000557/30229/bbsView.do?idx=374215"


def classify_text(s: str) -> str:
    low = (s or "").lower()
    if "handshake failure" in low or "ssl" in low or "tls" in low:
        return "TLS_OR_SSL_ERROR"
    if "timeout" in low or "timed out" in low:
        return "TIMEOUT"
    if "could not resolve" in low or "name or service not known" in low or "getaddrinfo" in low:
        return "DNS_ERROR"
    if "connection reset" in low or "connection aborted" in low:
        return "CONNECTION_RESET"
    return "OTHER"


def run_requests(url: str) -> dict:
    try:
        r = requests.get(
            url,
            timeout=30,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
                "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
            },
        )
        return {
            "available": True,
            "ok": True,
            "http": r.status_code,
            "final_url": r.url,
            "error_class": None,
            "error": None,
        }
    except requests.RequestException as ex:
        msg = f"{type(ex).__name__}: {ex}"
        return {
            "available": True,
            "ok": False,
            "http": None,
            "final_url": None,
            "error_class": classify_text(msg),
            "error": msg,
        }


def run_curl(url: str, tls_flag: str | None = None) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"available": False, "ok": False, "returncode": None, "http": None, "stderr": "curl not found"}

    cmd = [exe, "-L", "-sS", "-o", "NUL" if sys.platform.startswith("win") else "/dev/null", "-w", "%{http_code}|%{url_effective}|%{ssl_version}", "--connect-timeout", "15", "--max-time", "30"]
    if tls_flag:
        cmd.append(tls_flag)
    cmd.append(url)

    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    stdout = (p.stdout or "").strip()
    stderr = (p.stderr or "").strip()
    parts = stdout.split("|", 2) if stdout else []
    http = parts[0] if len(parts) >= 1 else None
    final_url = parts[1] if len(parts) >= 2 else None
    ssl_version = parts[2] if len(parts) >= 3 else None
    return {
        "available": True,
        "ok": p.returncode == 0 and bool(http and http != "000"),
        "returncode": p.returncode,
        "http": http,
        "final_url": final_url,
        "ssl_version": ssl_version,
        "stderr_class": classify_text(stderr),
        "stderr": stderr,
        "command_mode": tls_flag or "default",
    }


def run_httpx(url: str) -> dict:
    if importlib.util.find_spec("httpx") is None:
        return {"available": False, "ok": False, "http": None, "final_url": None, "error": "httpx not installed"}
    try:
        import httpx
        with httpx.Client(follow_redirects=True, timeout=30.0, headers={"User-Agent": "Mozilla/5.0"}) as c:
            r = c.get(url)
        return {"available": True, "ok": True, "http": r.status_code, "final_url": str(r.url), "error_class": None, "error": None}
    except Exception as ex:
        msg = f"{type(ex).__name__}: {ex}"
        return {"available": True, "ok": False, "http": None, "final_url": None, "error_class": classify_text(msg), "error": msg}


def main() -> None:
    print("=" * 78)
    print("SEONGNAM URBAN PLANNING COMMITTEE TLS TRANSPORT DIAGNOSTIC - S226T")
    print("=" * 78)
    print("Purpose: diagnose TLS/client compatibility only; no UQQ700 search")
    print("Search request: NOT EXECUTED")
    print("UQQ700 target query: NOT EXECUTED")
    print("Negative evidence: DISABLED")
    print("SITE promotion: BLOCKED")
    print("Runtime registration: BLOCKED")
    print("UQQ700 resolution: UNKNOWN")

    env = {
        "python_version": sys.version,
        "platform": platform.platform(),
        "openssl_version": ssl.OPENSSL_VERSION,
        "has_tls_1_2": hasattr(ssl.TLSVersion, "TLSv1_2"),
        "has_tls_1_3": hasattr(ssl.TLSVersion, "TLSv1_3"),
        "requests_version": requests.__version__,
        "curl_path": shutil.which("curl.exe") or shutil.which("curl"),
        "httpx_installed": importlib.util.find_spec("httpx") is not None,
    }

    results = {
        "requests_root": run_requests(ROOT_URL),
        "requests_detail": run_requests(DETAIL_URL),
        "curl_default_root": run_curl(ROOT_URL),
        "curl_tls12_root": run_curl(ROOT_URL, "--tlsv1.2"),
        "curl_tls13_root": run_curl(ROOT_URL, "--tlsv1.3"),
        "curl_default_detail": run_curl(DETAIL_URL),
        "httpx_root": run_httpx(ROOT_URL),
        "httpx_detail": run_httpx(DETAIL_URL),
    }

    curl_success = any(results[k].get("ok") for k in ("curl_default_root", "curl_tls12_root", "curl_tls13_root", "curl_default_detail"))
    httpx_success = any(results[k].get("ok") for k in ("httpx_root", "httpx_detail"))
    requests_success = any(results[k].get("ok") for k in ("requests_root", "requests_detail"))

    if curl_success:
        classification = "SEONGNAM_OFFICIAL_TLS_TRANSPORT_RECOVERED_VIA_CURL"
        next_action = "USE_CURL_TRANSPORT_TO_REQUALIFY_COMMITTEE_ENTRY_CONTRACT_WITHOUT_UQQ700_QUERY"
    elif httpx_success:
        classification = "SEONGNAM_OFFICIAL_TLS_TRANSPORT_RECOVERED_VIA_ALTERNATE_CLIENT"
        next_action = "USE_HTTPX_TRANSPORT_TO_REQUALIFY_COMMITTEE_ENTRY_CONTRACT_WITHOUT_UQQ700_QUERY"
    elif not requests_success and (env["curl_path"] or env["httpx_installed"]):
        classification = "SEONGNAM_OFFICIAL_TLS_TRANSPORT_ENVIRONMENT_MISMATCH"
        next_action = "HARDEN_TLS_STACK_OR_SELECT_BROWSER_BACKED_OFFICIAL_TRANSPORT_WITHOUT_NEGATIVE_INFERENCE"
    else:
        classification = "SEONGNAM_OFFICIAL_TLS_TRANSPORT_TECHNICAL_UNKNOWN"
        next_action = "CONTINUE_TRANSPORT_FORENSICS_WITHOUT_UQQ700_QUERY_OR_LEGAL_ABSENCE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-141-S226T",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "environment": env,
        "transport_results": results,
        "classification": classification,
        "summary": {
            "next_action": next_action,
            "search_request_executed": False,
            "target_query_executed": False,
            "transport_failure_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"PYTHON: {env['python_version'].split()[0]}")
    print(f"OPENSSL: {env['openssl_version']}")
    print(f"REQUESTS: {env['requests_version']}")
    print(f"CURL PATH: {env['curl_path']}")
    print(f"HTTPX INSTALLED: {env['httpx_installed']}")
    print("-" * 78)
    for name, row in results.items():
        print(f"{name}: ok={row.get('ok')} http={row.get('http')} final={row.get('final_url')} ssl={row.get('ssl_version')} error_class={row.get('error_class') or row.get('stderr_class')}")
        if row.get("error"):
            print(f"  error={row['error']}")
        if row.get("stderr"):
            print(f"  stderr={row['stderr']}")

    print("-" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print("Search request executed: False")
    print("Target query executed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "classification emitted": classification in {
            "SEONGNAM_OFFICIAL_TLS_TRANSPORT_RECOVERED_VIA_CURL",
            "SEONGNAM_OFFICIAL_TLS_TRANSPORT_RECOVERED_VIA_ALTERNATE_CLIENT",
            "SEONGNAM_OFFICIAL_TLS_TRANSPORT_ENVIRONMENT_MISMATCH",
            "SEONGNAM_OFFICIAL_TLS_TRANSPORT_TECHNICAL_UNKNOWN",
        },
        "search request not executed": out["summary"]["search_request_executed"] is False,
        "target query not executed": out["summary"]["target_query_executed"] is False,
        "transport failure not legal absence": out["summary"]["transport_failure_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "SITE promotion blocked": out["summary"]["site_positive_allowed"] is False and out["summary"]["site_negative_allowed"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for key, value in validation.items():
        print(f"{key}: {value}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")

    if not all(validation.values()):
        raise AssertionError("S226T validation failed")


if __name__ == "__main__":
    main()
