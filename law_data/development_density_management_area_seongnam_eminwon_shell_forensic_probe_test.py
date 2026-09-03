# -*- coding: utf-8 -*-
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE = Path(__file__).resolve().parent.parent
OUT = BASE / "law_data" / "output" / "development_density_management_area_seongnam_eminwon_shell_forensic_probe.json"
ENTRY_URL = "http://eminwon.seongnam.go.kr/emwp/emwpIndex.html"
HOST = "eminwon.seongnam.go.kr"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
MAX_BYTES = 6 * 1024 * 1024

SCRIPT_SRC_RE = re.compile(r'<script\b[^>]*src\s*=\s*["\']([^"\']+)["\']', re.I)
FRAME_SRC_RE = re.compile(r'<(?:iframe|frame)\b[^>]*src\s*=\s*["\']([^"\']+)["\']', re.I)
META_REFRESH_RE = re.compile(r'<meta\b[^>]*http-equiv\s*=\s*["\']?refresh["\']?[^>]*content\s*=\s*["\']([^"\']+)["\']', re.I)
URL_LITERAL_RE = re.compile(r'["\']((?:https?://|/|\.\.?/)[^"\']{3,240})["\']', re.I)
FUNC_RE = re.compile(r'\b(?:window\.open|location\.href|location\.replace|document\.location)\s*(?:=|\()\s*["\']([^"\']+)["\']', re.I)


def host(url):
    return (urlparse(url).hostname or "").lower()


def bounded_get(session, url):
    try:
        r = session.get(url, timeout=25, stream=True, allow_redirects=True)
        buf = bytearray()
        overflow = False
        try:
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if len(buf) + len(chunk) > MAX_BYTES:
                    overflow = True
                    break
                buf.extend(chunk)
        finally:
            r.close()
        return {
            "state": "HTTP_RESPONSE_CAPTURED" if not overflow else "TECHNICAL_REQUEST_UNKNOWN",
            "http": r.status_code,
            "final_url": str(r.url),
            "body": bytes(buf),
            "overflow": overflow,
            "error": "RESPONSE_SIZE_LIMIT_EXCEEDED" if overflow else None,
        }
    except requests.RequestException as exc:
        return {
            "state": "TECHNICAL_REQUEST_UNKNOWN",
            "http": None,
            "final_url": url,
            "body": b"",
            "overflow": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def same_host_urls(base_url, raw_values):
    out = []
    seen = set()
    for raw in raw_values:
        value = html.unescape(str(raw or "").strip())
        if not value or value.lower().startswith(("javascript:", "mailto:", "#")):
            continue
        url = urljoin(base_url, value)
        if host(url) != HOST:
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
    return out


def main():
    print("=" * 60)
    print("SEONGNAM EMINWON SHELL FORENSIC PROBE - S146")
    print("=" * 60)
    print("Child URL requests: DISABLED")
    print("Target-term search: DISABLED")
    print("Negative evidence: DISABLED")
    print("SITE/runtime promotion: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    res = bounded_get(session, ENTRY_URL)
    ok_host = host(res["final_url"]) == HOST
    print("ENTRY STATE:", res["state"], "| HTTP:", res["http"], "| HOST_OK:", ok_host)
    if res["error"]:
        print("ERROR:", res["error"])

    script_urls = []
    frame_urls = []
    meta_refresh = []
    inline_urls = []
    function_urls = []
    if res["state"] == "HTTP_RESPONSE_CAPTURED" and res["http"] == 200 and ok_host:
        text = res["body"].decode("utf-8", errors="ignore")
        script_urls = same_host_urls(res["final_url"], SCRIPT_SRC_RE.findall(text))
        frame_urls = same_host_urls(res["final_url"], FRAME_SRC_RE.findall(text))
        meta_refresh = same_host_urls(res["final_url"], META_REFRESH_RE.findall(text))
        inline_urls = same_host_urls(res["final_url"], URL_LITERAL_RE.findall(text))
        function_urls = same_host_urls(res["final_url"], FUNC_RE.findall(text))

    all_children = []
    seen = set()
    for source, values in [
        ("SCRIPT_SRC", script_urls),
        ("FRAME_SRC", frame_urls),
        ("META_REFRESH", meta_refresh),
        ("INLINE_URL_LITERAL", inline_urls),
        ("INLINE_NAVIGATION", function_urls),
    ]:
        for url in values:
            if url in seen:
                continue
            seen.add(url)
            all_children.append({"source": source, "url": url})

    out = {
        "step": "STEP 17-21-C-16-8-T-42-S146",
        "target_name": "개발밀도관리구역",
        "standard_code": "UQQ700",
        "source_family": "SEONGNAM_EMINWON_HISTORICAL_NOTICE",
        "entry_url": ENTRY_URL,
        "request": {k: v for k, v in res.items() if k != "body"},
        "summary": {
            "script_src_count": len(script_urls),
            "frame_src_count": len(frame_urls),
            "meta_refresh_count": len(meta_refresh),
            "inline_url_count": len(inline_urls),
            "inline_navigation_count": len(function_urls),
            "unique_child_url_count": len(all_children),
            "transport_unknown_count": 1 if res["state"] == "TECHNICAL_REQUEST_UNKNOWN" else 0,
            "semantic_state": "SEONGNAM_EMINWON_SHELL_FORENSIC_CAPTURED",
            "negative_evidence_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
        "script_urls": script_urls,
        "frame_urls": frame_urls,
        "meta_refresh_urls": meta_refresh,
        "inline_urls": inline_urls,
        "inline_navigation_urls": function_urls,
        "child_urls": all_children,
        "child_url_requests_executed": False,
        "target_term_search_executed": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nCHILD URLS")
    for rec in all_children[:100]:
        print(rec["source"], "|", rec["url"])

    print("\nSUMMARY")
    for k, v in out["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    checks = {
        "entry host official": ok_host,
        "child requests disabled": not out["child_url_requests_executed"],
        "target search disabled": not out["target_term_search_executed"],
        "negative evidence disabled": not out["negative_evidence_allowed"],
        "legal absence inference disabled": not out["legal_absence_inference_allowed"],
        "unsafe promotion leakage zero": not any(out[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed"]),
        "final resolution unknown": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\nVALIDATION")
    for k, v in checks.items():
        print(f"{k}: {v}")
    print("all_pass:", all(checks.values()))
    if not all(checks.values()):
        raise AssertionError("S146 shell forensic probe failed")


if __name__ == "__main__":
    main()
