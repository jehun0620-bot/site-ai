# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S17
Focused static extraction of the official Seongnam preview runtime contract.
Targets only the code paths that read fn/rs and construct document resource URLs.
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
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_preview_runtime_focused_contract.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
VIEWER_URL = BASE + "/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
CONFIG_URL = BASE + "/humanframe/global/html/preview/skin/js/config.js"
TIMEOUT = 20
MAX_REQUESTS = 2
MAX_TEXT_CHARS = 2_000_000

ANCHORS = (
    "getParameter",
    "location.search",
    "URLSearchParams",
    "fn",
    "rs",
    "result/attach",
    "preview/result",
    "pageList",
    "pageinfo",
    "pageInfo",
    "document.json",
    "document.xml",
    "info.json",
    "info.xml",
    "pages",
    "resource",
    "ajax",
    "$.get",
    "$.ajax",
    "fetch(",
)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def contexts(text: str, anchor: str, before: int = 700, after: int = 1400) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(re.escape(anchor), text, flags=re.I):
        a = max(0, m.start() - before)
        b = min(len(text), m.end() + after)
        s = re.sub(r"\s+", " ", text[a:b]).strip()
        if s not in seen:
            seen.add(s)
            out.append(s[:3200])
        if len(out) >= 8:
            break
    return out


def assignments(text: str) -> list[str]:
    pats = [
        r'''(?:var|let|const)\s+[A-Za-z_$][\w$]*\s*=\s*[^;]{0,1200}(?:fn|rs|result/attach|preview/result)[^;]{0,1200};''',
        r'''[A-Za-z_$][\w$]*\s*=\s*[^;]{0,1200}(?:getParameter|URLSearchParams|location\.search)[^;]{0,1200};''',
        r'''(?:url|src|href)\s*[:=]\s*[^,;\n]{0,1400}(?:rs|fn|result|attach)[^,;\n]{0,1400}''',
        r'''(?:ajax|fetch|\.get)\s*\([^)]{0,1800}\)''',
    ]
    out = []
    seen = set()
    for pat in pats:
        for m in re.finditer(pat, text, flags=re.I | re.S):
            s = re.sub(r"\s+", " ", m.group(0)).strip()
            if s not in seen:
                seen.add(s)
                out.append(s[:3600])
            if len(out) >= 60:
                return out
    return out


def interesting_literals(text: str) -> list[str]:
    out = []
    seen = set()
    for m in re.finditer(r'''["']([^"']{1,260})["']''', text):
        s = m.group(1)
        low = s.lower()
        if any(k in low for k in ("result/attach", "preview/result", "page", ".xml", ".json", ".txt", ".svg", ".png", ".jpg", "resource", "fn", "rs")):
            if s not in seen:
                seen.add(s)
                out.append(s)
        if len(out) >= 160:
            break
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW RUNTIME FOCUSED CONTRACT")
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
    focused = {}
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

        data = {
            "assignments": assignments(text),
            "literals": interesting_literals(text),
            "contexts": {a: contexts(text, a) for a in ANCHORS if re.search(re.escape(a), text, flags=re.I)},
        }
        focused[name] = data

        print(f"{name.upper()} ASSIGNMENTS")
        for i, x in enumerate(data["assignments"], 1):
            print(f"[{i}] {x}")
        print()
        print(f"{name.upper()} LITERALS")
        for i, x in enumerate(data["literals"], 1):
            print(f"[{i}] {x}")
        print()
        print(f"{name.upper()} KEY CONTEXTS")
        for anchor, vals in data["contexts"].items():
            print(f"-- {anchor} --")
            for i, x in enumerate(vals, 1):
                print(f"[{i}] {x}")
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S17",
        "records": records,
        "focused": focused,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    viewer = focused.get("viewer", {})
    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(r.get("host") == HOST for r in records),
        "both scripts available": len(records) == 2 and all(r.get("status") == 200 and r.get("text_chars", 0) > 0 for r in records),
        "viewer focused evidence present": bool(viewer.get("assignments") or viewer.get("contexts")),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Viewer assignments:", len(viewer.get("assignments", [])))
    print("Viewer literals:", len(viewer.get("literals", [])))
    print("Viewer context anchors:", len(viewer.get("contexts", {})))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("focused preview runtime contract validation failed")


if __name__ == "__main__":
    main()
