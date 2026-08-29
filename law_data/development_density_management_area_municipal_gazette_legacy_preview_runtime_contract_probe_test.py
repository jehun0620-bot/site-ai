# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S16
Inspect the official Seongnam document preview runtime JavaScript to recover
how query parameters fn/rs are mapped to generated preview assets.

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
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_preview_runtime_contract_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PREVIEW_BASE = f"{BASE}/humanframe/global/html/preview/skin/"
CONFIG_URL = PREVIEW_BASE + "js/config.js"
VIEWER_URL = PREVIEW_BASE + "js/newviewer.eb84793.js"
TIMEOUT = 20
MAX_REQUESTS = 2
MAX_TEXT_CHARS = 2_000_000

KEYWORDS = (
    "result/attach",
    "preview/result",
    "fn=",
    "rs=",
    "getParameter",
    "location.search",
    "window.location",
    "xml",
    "json",
    "txt",
    "page",
    "image",
    "resource",
    "document",
)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def snippets(text: str) -> list[str]:
    compact = text.replace("\r", " ").replace("\n", " ")
    out: list[str] = []
    seen = set()
    for kw in KEYWORDS:
        for m in re.finditer(re.escape(kw), compact, flags=re.I):
            a = max(0, m.start() - 500)
            b = min(len(compact), m.end() + 900)
            s = re.sub(r"\s+", " ", compact[a:b]).strip()
            if s not in seen:
                seen.add(s)
                out.append(s[:2200])
            if len(out) >= 80:
                return out
    return out


def literal_paths(text: str) -> list[str]:
    vals = []
    seen = set()
    for m in re.finditer(r'''["']([^"']{1,300})["']''', text):
        s = m.group(1)
        low = s.lower()
        if any(k in low for k in ("result", "attach", ".xml", ".json", ".txt", ".html", ".htm", "page", "image", "resource")):
            if s not in seen:
                seen.add(s)
                vals.append(s)
        if len(vals) >= 120:
            break
    return vals


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW RUNTIME CONTRACT PROBE")
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
    all_snips = {}
    all_literals = {}

    for name, url in (("config", CONFIG_URL), ("viewer", VIEWER_URL)):
        r = s.get(url, timeout=TIMEOUT)
        text = r.text[:MAX_TEXT_CHARS]
        rec = {
            "name": name,
            "status": r.status_code,
            "url": r.url,
            "host": host(r.url),
            "content_type": r.headers.get("Content-Type", ""),
            "text_chars": len(text),
        }
        records.append(rec)
        sn = snippets(text)
        lp = literal_paths(text)
        all_snips[name] = sn
        all_literals[name] = lp

        print(f"{name.upper()}:", rec)
        print(f"{name.upper()} LITERAL PATHS:")
        for i, x in enumerate(lp, 1):
            print(f"  [{i}] {x}")
        print(f"{name.upper()} SNIPPETS:")
        for i, x in enumerate(sn, 1):
            print(f"  [{i}] {x}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S16",
        "records": records,
        "literal_paths": all_literals,
        "snippets": all_snips,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(r.get("host") == HOST for r in records),
        "both scripts available": len(records) == 2 and all(r.get("status") == 200 and r.get("text_chars", 0) > 0 for r in records),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Config snippets:", len(all_snips.get("config", [])))
    print("Viewer snippets:", len(all_snips.get("viewer", [])))
    print("Config literal paths:", len(all_literals.get("config", [])))
    print("Viewer literal paths:", len(all_literals.get("viewer", [])))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview runtime contract probe validation failed")


if __name__ == "__main__":
    main()
