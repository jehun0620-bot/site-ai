# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S20
Exact-identifier probe for the official Seongnam preview runtime.
Avoids substring false positives from prior ranking by matching whole-word
query parameter identifiers and concrete thumbnail/page resource symbols.

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_preview_exact_identifier_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
CONFIG_URL = BASE + "/humanframe/global/html/preview/skin/js/config.js"
VIEWER_URL = BASE + "/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
TIMEOUT = 20
MAX_REQUESTS = 2
MAX_TEXT_CHARS = 2_000_000

EXACT_PATTERNS = {
    "whole_word_fn": r"(?<![A-Za-z0-9_$])fn(?![A-Za-z0-9_$])",
    "whole_word_rs": r"(?<![A-Za-z0-9_$])rs(?![A-Za-z0-9_$])",
    "fn_string": r"[\"']fn[\"']",
    "rs_string": r"[\"']rs[\"']",
    "thumbnailxml": r"thumbnailxml",
    "getThumbnailXml": r"getThumbnailXml",
    "preview_result": r"preview/result",
    "result_attach": r"result/attach",
    "location_search": r"location\.search",
    "URLSearchParams": r"URLSearchParams",
    "getParameter": r"getParameter",
    "xml_page": r"getElementsByTagName\([\"']page[\"']\)",
    "xml_text": r"getElementsByTagName\([\"']text[\"']\)",
}


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def extract_contexts(text: str, pat: str, limit: int = 12) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(pat, text, flags=re.I):
        a = max(0, m.start() - 900)
        b = min(len(text), m.end() + 1800)
        s = re.sub(r"\s+", " ", text[a:b]).strip()
        if s not in seen:
            seen.add(s)
            out.append(s[:4200])
        if len(out) >= limit:
            break
    return out


def extract_nearby_literals(text: str, contexts: dict[str, list[str]]) -> list[str]:
    blob = "\n".join(x for vals in contexts.values() for x in vals)
    out = []
    seen = set()
    for m in re.finditer(r'''[\"']([^\"']{1,300})[\"']''', blob):
        s = m.group(1)
        low = s.lower()
        if any(k in low for k in (
            "thumbnail", "page", "xml", "json", "txt", "result", "attach",
            "resource", "fn", "rs", "preview"
        )):
            if s not in seen:
                seen.add(s)
                out.append(s)
        if len(out) >= 100:
            break
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW EXACT IDENTIFIER PROBE")
    print("=" * 60)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    records = []
    evidence = {}
    for name, url in (("config", CONFIG_URL), ("viewer", VIEWER_URL)):
        r = s.get(url, timeout=TIMEOUT)
        text = r.text[:MAX_TEXT_CHARS]
        records.append({
            "name": name,
            "status": r.status_code,
            "url": r.url,
            "host": host(r.url),
            "content_type": r.headers.get("Content-Type", ""),
            "text_chars": len(text),
        })
        ctx = {k: extract_contexts(text, pat) for k, pat in EXACT_PATTERNS.items()}
        ctx = {k: v for k, v in ctx.items() if v}
        lits = extract_nearby_literals(text, ctx)
        evidence[name] = {"contexts": ctx, "nearby_literals": lits}

        print(f"{name.upper()} EXACT CONTEXTS")
        for key, vals in ctx.items():
            print(f"-- {key} ({len(vals)}) --")
            for i, x in enumerate(vals, 1):
                print(f"[{i}] {x}")
        print()
        print(f"{name.upper()} NEARBY LITERALS")
        for i, x in enumerate(lits, 1):
            print(f"[{i}] {x}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S20",
        "records": records,
        "evidence": evidence,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    viewer = evidence.get("viewer", {})
    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(r.get("host") == HOST for r in records),
        "both scripts available": len(records) == 2 and all(r.get("status") == 200 and r.get("text_chars", 0) > 0 for r in records),
        "viewer exact evidence present": bool(viewer.get("contexts")),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Viewer exact context groups:", len(viewer.get("contexts", {})))
    print("Viewer nearby literals:", len(viewer.get("nearby_literals", [])))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview exact identifier probe validation failed")


if __name__ == "__main__":
    main()
