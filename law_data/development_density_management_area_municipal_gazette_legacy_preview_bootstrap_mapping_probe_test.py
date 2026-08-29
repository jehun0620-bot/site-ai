# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S26
Probe the official legacy preview bootstrap for filename-to-runtime mapping.

Goal:
- replay official detail -> metadata -> filePreview
- inspect preview shell HTML plus official viewer JS for exact bootstrap expressions
  that transform/use query params fn/rs before getInfoURL() is called
- print only tightly focused contexts around localSynap/module initialization,
  query parsing, load(), getInfoURL(), and any inline script references to fn/rs

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_bootstrap_mapping_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
BBS_CRT_SN = "16002"
FILE_NO = "28559"
DETAIL_URL = BASE + "/bbs010308/" + PST_SN
META_URL = BASE + "/bbs010308/atchFileDetail"
PREVIEW_URL = BASE + "/bbs010308/filePreview"
VIEWER_JS = BASE + "/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
TIMEOUT = 20
MAX_REQUESTS = 4

SHELL_PATTERNS = (
    r"\bfn\b",
    r"\brs\b",
    r"localSynap",
    r"newviewer",
    r"script",
    r"location\.search",
    r"URLSearchParams",
)

VIEWER_PATTERNS = (
    r"getParameter=function",
    r"this\.load=function",
    r"this\.getInfoURL=function",
    r"this\.isModuleType=function",
    r"this\.getContextPath=function",
    r"this\.id=this\.isModuleType\(e\)\?e\.fn:e\.key",
    r"e=a\.Util\.getParameter\(\)",
    r"loadDocument\(e\)",
)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def compact_contexts(text: str, patterns, before=900, after=1600, limit=20):
    rows = []
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            a = max(0, m.start() - before)
            b = min(len(text), m.end() + after)
            s = re.sub(r"\s+", " ", text[a:b]).strip()
            key = (pat, s)
            if key not in seen:
                seen.add(key)
                rows.append({"pattern": pat, "context": s[:5000]})
            if len(rows) >= limit:
                return rows
    return rows


def inline_scripts(html: str):
    out = []
    for m in re.finditer(r"<script\b[^>]*>(.*?)</script>", html, flags=re.I | re.S):
        body = m.group(1).strip()
        if body:
            out.append(re.sub(r"\s+", " ", body)[:12000])
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW BOOTSTRAP MAPPING PROBE")
    print("=" * 60)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    r1 = s.get(DETAIL_URL, timeout=TIMEOUT)
    r2 = s.get(META_URL, params={"pstSn": PST_SN}, headers={"X-Requested-With": "XMLHttpRequest", "Referer": r1.url}, timeout=TIMEOUT)
    r3 = s.get(PREVIEW_URL, params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}, headers={"Referer": r1.url}, timeout=TIMEOUT, allow_redirects=True)
    r4 = s.get(VIEWER_JS, headers={"Referer": r3.url}, timeout=TIMEOUT)

    shell = r3.text
    viewer = r4.text

    shell_ctx = compact_contexts(shell, SHELL_PATTERNS, before=700, after=1400, limit=24)
    viewer_ctx = compact_contexts(viewer, VIEWER_PATTERNS, before=1000, after=2200, limit=24)
    scripts = inline_scripts(shell)

    print("PREVIEW URL")
    print(r3.url)
    print()
    print("SHELL INLINE SCRIPTS")
    for i, x in enumerate(scripts, 1):
        print(f"[{i}] {x}")
    print()
    print("SHELL FOCUSED CONTEXTS")
    for i, row in enumerate(shell_ctx, 1):
        print(f"[{i}] pattern={row['pattern']}")
        print(row["context"])
    print()
    print("VIEWER FOCUSED CONTEXTS")
    for i, row in enumerate(viewer_ctx, 1):
        print(f"[{i}] pattern={row['pattern']}")
        print(row["context"])
    print()

    records = [
        {"kind": "DETAIL", "status": r1.status_code, "url": r1.url, "host": host(r1.url)},
        {"kind": "META", "status": r2.status_code, "url": r2.url, "host": host(r2.url)},
        {"kind": "PREVIEW", "status": r3.status_code, "url": r3.url, "host": host(r3.url)},
        {"kind": "VIEWER_JS", "status": r4.status_code, "url": r4.url, "host": host(r4.url)},
    ]
    output = {
        "step": "STEP 17-21-C-16-8-T-34-S26",
        "records": records,
        "preview_url": r3.url,
        "cookies": sorted(s.cookies.get_dict().keys()),
        "inline_scripts": scripts,
        "shell_contexts": shell_ctx,
        "viewer_contexts": viewer_ctx,
        "network_request_count": 4,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": output["network_request_count"] <= MAX_REQUESTS,
        "all hosts official": all(x["host"] == HOST for x in records),
        "detail succeeded": r1.status_code == 200,
        "metadata succeeded": r2.status_code == 200,
        "preview succeeded": r3.status_code == 200,
        "viewer js succeeded": r4.status_code == 200,
        "focused evidence present": bool(shell_ctx) and bool(viewer_ctx),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Inline scripts:", len(scripts))
    print("Shell contexts:", len(shell_ctx))
    print("Viewer contexts:", len(viewer_ctx))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview bootstrap mapping probe validation failed")


if __name__ == "__main__":
    main()
