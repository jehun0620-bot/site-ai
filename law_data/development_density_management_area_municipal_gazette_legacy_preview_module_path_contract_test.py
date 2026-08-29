# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S21
Extract exact module-mode path construction functions from the official
Seongnam Synap preview runtime: isModuleType, getContextPath, getInfoURL,
doAfterGetStatusForHTMLServer, and nearby resultPath/fileName assignments.

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_module_path_contract.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
VIEWER_URL = BASE + "/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
TIMEOUT = 20
MAX_REQUESTS = 1
MAX_TEXT_CHARS = 2_000_000

SYMBOLS = (
    "isModuleType",
    "getContextPath",
    "getInfoURL",
    "doAfterGetStatusForHTMLServer",
    "doAfterGetStatusForHTML",
    "resultPath",
    "fileName",
)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def contexts(text: str, token: str, limit: int = 12) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(re.escape(token), text):
        a = max(0, m.start() - 1200)
        b = min(len(text), m.end() + 2600)
        s = re.sub(r"\s+", " ", text[a:b]).strip()
        if s not in seen:
            seen.add(s)
            out.append(s[:5200])
        if len(out) >= limit:
            break
    return out


def function_like(text: str, name: str) -> list[str]:
    patterns = [
        rf"this\.{re.escape(name)}\s*=\s*function\([^)]*\)\{{",
        rf"{re.escape(name)}\s*=\s*function\([^)]*\)\{{",
        rf"{re.escape(name)}\s*:\s*function\([^)]*\)\{{",
    ]
    out = []
    seen = set()
    for pat in patterns:
        for m in re.finditer(pat, text):
            a = m.start()
            b = min(len(text), a + 7000)
            s = re.sub(r"\s+", " ", text[a:b]).strip()
            if s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= 4:
                return out
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW MODULE PATH CONTRACT")
    print("=" * 60)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    r = s.get(VIEWER_URL, timeout=TIMEOUT)
    text = r.text[:MAX_TEXT_CHARS]

    evidence = {}
    for symbol in SYMBOLS:
        evidence[symbol] = {
            "function_like": function_like(text, symbol),
            "contexts": contexts(text, symbol),
        }

    for symbol in SYMBOLS:
        print(f"-- {symbol} --")
        fl = evidence[symbol]["function_like"]
        if fl:
            print("FUNCTION-LIKE")
            for i, x in enumerate(fl, 1):
                print(f"[{i}] {x}")
        print("CONTEXTS")
        for i, x in enumerate(evidence[symbol]["contexts"], 1):
            print(f"[{i}] {x}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S21",
        "viewer": {
            "status": r.status_code,
            "url": r.url,
            "host": host(r.url),
            "content_type": r.headers.get("Content-Type", ""),
            "text_chars": len(text),
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
        "core symbols found": all(bool(evidence[x]["contexts"]) for x in ("isModuleType", "getContextPath", "getInfoURL", "resultPath", "fileName")),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    for symbol in SYMBOLS:
        print(symbol, "contexts:", len(evidence[symbol]["contexts"]), "functions:", len(evidence[symbol]["function_like"]))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview module path contract validation failed")


if __name__ == "__main__":
    main()
