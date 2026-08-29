# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S29
Extract the exact preview-side API helpers and load/bootstrap call chain that
may prepare/transform document resources before page XML is read.

Targets official viewer JS functions/call-sites involving:
- ajaxCall
- getUrlWithExtraParam
- getXml / getJson
- initService
- loadDocument
- getInfoURL call path
- archiveFileList / xml / result / thumbnailxml API construction

No document requests beyond one official viewer JS fetch.
No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_preflight_api_contract_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
VIEWER_JS = BASE + "/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
TIMEOUT = 20
MAX_REQUESTS = 1

TARGET_PATTERNS = (
    r"ajaxCall=function",
    r"getUrlWithExtraParam=function",
    r"getXml=function",
    r"getJson=function",
    r"initService=function",
    r"loadDocument=function",
    r"getInfoURL=function",
    r"archiveFileList",
    r"/xml/",
    r"/result/",
    r"thumbnailxml",
)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def contexts(text: str, pattern: str, limit: int = 12) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(pattern, text, flags=re.I):
        a = max(0, m.start() - 1400)
        b = min(len(text), m.end() + 3200)
        s = re.sub(r"\s+", " ", text[a:b]).strip()
        if s not in seen:
            seen.add(s)
            out.append(s[:7200])
        if len(out) >= limit:
            break
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW PREFLIGHT API CONTRACT PROBE")
    print("=" * 60)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print()

    r = requests.get(
        VIEWER_JS,
        headers={"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"},
        timeout=TIMEOUT,
    )
    text = r.text

    evidence = {}
    for pat in TARGET_PATTERNS:
        rows = contexts(text, pat)
        evidence[pat] = rows
        print(f"-- {pat} ({len(rows)}) --")
        for i, row in enumerate(rows, 1):
            print(f"[{i}] {row}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S29",
        "viewer": {
            "status": r.status_code,
            "url": r.url,
            "host": host(r.url),
            "content_type": r.headers.get("Content-Type", ""),
            "bytes": len(r.content),
        },
        "evidence": evidence,
        "network_request_count": 1,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": output["network_request_count"] <= MAX_REQUESTS,
        "official host": output["viewer"]["host"] == HOST,
        "viewer available": r.status_code == 200 and len(text) > 0,
        "ajax helper found": bool(evidence.get(r"ajaxCall=function")),
        "loadDocument found": bool(evidence.get(r"loadDocument=function")),
        "initService found": bool(evidence.get(r"initService=function")),
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    for pat in TARGET_PATTERNS:
        print(pat, "contexts:", len(evidence[pat]))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview preflight API contract validation failed")


if __name__ == "__main__":
    main()
