# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S33
Inspect the deployed Synap viewer control flow after module-info retrieval failure.

Goal:
- recover exact load()/getXml()/ajax error handling
- recover 403/404 branches
- recover retry/sleep behavior
- recover any fallback/conversion/reload path that can explain why a preview shell is valid
  even when direct info XML returns 404

One official JS request only. No OCR, no state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_fallback_control_flow_probe.json"
JS_URL = "https://www.seongnam.go.kr/humanframe/global/html/preview/skin/js/newviewer.eb84793.js"
TIMEOUT = 20
PATTERNS = [
    r"load=function",
    r"getXml=function",
    r"ajaxCall=function",
    r"status===404",
    r"status==404",
    r"404",
    r"403",
    r"sleep",
    r"setTimeout",
    r"retry",
    r"reload",
    r"fallback",
    r"convert",
    r"conversion",
    r"imageConverting",
    r"htmlDone",
    r"imgDone",
    r"doAfterGetStatusForHTML",
    r"doAfterGetStatusForImage",
    r"openUrlAccessFailed",
    r"XMLHttpRequest",
]


def contexts(text: str, pat: str, limit: int = 12):
    rows = []
    seen = set()
    for m in re.finditer(pat, text, re.I):
        a = max(0, m.start() - 1200)
        b = min(len(text), m.end() + 2600)
        s = text[a:b]
        s = re.sub(r"\s+", " ", s).strip()
        if s not in seen:
            seen.add(s)
            rows.append(s[:7000])
        if len(rows) >= limit:
            break
    return rows


def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW FALLBACK CONTROL FLOW PROBE")
    print("=" * 60)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    r = requests.get(JS_URL, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.seongnam.go.kr/"}, timeout=TIMEOUT)
    print("JS status:", r.status_code)
    print("Content-Type:", r.headers.get("Content-Type", ""))
    print("Bytes:", len(r.content))

    ctx = {pat: contexts(r.text, pat) for pat in PATTERNS}
    for pat in PATTERNS:
        print(f"\n-- {pat} --")
        for i, row in enumerate(ctx[pat], 1):
            print(f"[{i}] {row}")

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S33",
        "js_url": JS_URL,
        "js_status": r.status_code,
        "contexts": ctx,
        "network_request_count": 1,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "js succeeded": r.status_code == 200,
        "load recovered": bool(ctx[r"load=function"]),
        "ajax recovered": bool(ctx[r"ajaxCall=function"]),
        "404 evidence recovered": bool(ctx[r"404"]),
        "request budget respected": output["network_request_count"] <= 1,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Requests: 1")
    print("load contexts:", len(ctx[r"load=function"]))
    print("404 contexts:", len(ctx[r"404"]))
    print("fallback contexts:", len(ctx[r"fallback"]))
    print("convert contexts:", len(ctx[r"convert"]))
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview fallback control-flow validation failed")


if __name__ == "__main__":
    main()
