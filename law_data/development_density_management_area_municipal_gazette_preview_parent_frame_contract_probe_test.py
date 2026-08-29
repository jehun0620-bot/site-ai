# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S32
Inspect the official parent-page/frame contract around filePreview.

For Gazette 938 and Gazette 2087:
- fetch detail page and attachment metadata
- locate filePreview/open/iframe/localSynap/newviewer contexts in detail HTML
- request filePreview without following redirects to capture exact status/location
- follow once to preview shell and inspect whether opener/parent/frame assumptions are visible

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_preview_parent_frame_contract_probe.json"
BASE = "https://www.seongnam.go.kr"
BBS = "16002"
TIMEOUT = 20
MAX_REQUESTS = 8
TARGETS = [
    {"label": "LEGACY_938", "pstSn": "29098", "fileNo": "28559"},
    {"label": "MODERN_2087", "pstSn": "404960", "fileNo": "2"},
]
PATTERNS = [
    r"filePreview",
    r"window\.open",
    r"iframe",
    r"localSynap",
    r"humanframe",
    r"preview",
    r"opener",
    r"parent",
]


def contexts(text: str, pattern: str, limit: int = 8):
    rows = []
    seen = set()
    for m in re.finditer(pattern, text, re.I):
        a = max(0, m.start() - 900)
        b = min(len(text), m.end() + 1800)
        s = re.sub(r"\s+", " ", text[a:b]).strip()
        if s not in seen:
            seen.add(s)
            rows.append(s[:4200])
        if len(rows) >= limit:
            break
    return rows


def main():
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("PREVIEW PARENT FRAME CONTRACT PROBE")
    print("=" * 60)
    print("OCR: DISABLED")
    print("State mutation: DISABLED")

    s = requests.Session()
    s.headers.update({"User-Agent": "Mozilla/5.0", "Accept-Language": "ko-KR,ko;q=0.9"})
    reqs = 0
    rows = []

    for t in TARGETS:
        print("\n--", t["label"], "--")
        detail = s.get(f"{BASE}/bbs010308/{t['pstSn']}", timeout=TIMEOUT); reqs += 1
        meta = s.get(f"{BASE}/bbs010308/atchFileDetail", params={"pstSn": t["pstSn"]}, headers={"X-Requested-With": "XMLHttpRequest", "Referer": detail.url}, timeout=TIMEOUT); reqs += 1
        fp = s.get(
            f"{BASE}/bbs010308/filePreview",
            params={"bbsCrtSn": BBS, "pstSn": t["pstSn"], "fileNo": t["fileNo"]},
            headers={"Referer": detail.url},
            allow_redirects=False,
            timeout=TIMEOUT,
        ); reqs += 1
        location = fp.headers.get("Location")
        resolved_location = urljoin(fp.url, location) if location else None
        preview = None
        if resolved_location:
            preview = s.get(resolved_location, headers={"Referer": detail.url}, timeout=TIMEOUT); reqs += 1

        detail_ctx = {pat: contexts(detail.text, pat) for pat in PATTERNS}
        meta_ctx = {pat: contexts(meta.text, pat) for pat in PATTERNS}
        preview_ctx = {pat: contexts(preview.text, pat) for pat in PATTERNS} if preview is not None else {}

        print("filePreview status:", fp.status_code)
        print("Location:", location)
        print("Resolved Location:", resolved_location)
        print("Preview status:", preview.status_code if preview is not None else None)
        print("DETAIL FOCUSED CONTEXTS")
        for pat in PATTERNS:
            for i, c in enumerate(detail_ctx[pat], 1):
                print(f"[{pat} #{i}] {c}")
        print("META FOCUSED CONTEXTS")
        for pat in PATTERNS:
            for i, c in enumerate(meta_ctx[pat], 1):
                print(f"[{pat} #{i}] {c}")
        print("PREVIEW FOCUSED CONTEXTS")
        for pat in PATTERNS:
            for i, c in enumerate(preview_ctx.get(pat, []), 1):
                print(f"[{pat} #{i}] {c}")

        rows.append({
            "target": t,
            "detail_status": detail.status_code,
            "meta_status": meta.status_code,
            "file_preview_status": fp.status_code,
            "file_preview_location": location,
            "resolved_location": resolved_location,
            "preview_status": preview.status_code if preview is not None else None,
            "detail_contexts": detail_ctx,
            "meta_contexts": meta_ctx,
            "preview_contexts": preview_ctx,
        })

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S32",
        "rows": rows,
        "network_request_count": reqs,
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": reqs <= MAX_REQUESTS,
        "both targets evaluated": len(rows) == 2,
        "detail/meta succeeded": all(r["detail_status"] == 200 and r["meta_status"] == 200 for r in rows),
        "filePreview contract captured": all(r["file_preview_status"] in (200, 301, 302, 303, 307, 308) for r in rows),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    print("Requests:", reqs)
    for r in rows:
        print(r["target"]["label"], "filePreview=", r["file_preview_status"], "location=", r["resolved_location"])
    print("Output:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview parent frame contract validation failed")


if __name__ == "__main__":
    main()
