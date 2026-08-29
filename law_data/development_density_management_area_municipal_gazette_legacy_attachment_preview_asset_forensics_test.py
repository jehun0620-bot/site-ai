# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S15
Inspect official Seongnam preview HTML for Gazette 938 legacy attachment and
recover bounded references to preview-generated assets. No OCR, no cumulative
state mutation, no legal promotion.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_attachment_preview_asset_forensics.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
FILE_NO = "28559"
BBS_CRT_SN = "16002"
TIMEOUT = 20
MAX_REQUESTS = 6
MAX_TEXT_CHARS = 500000


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def classify(raw: bytes) -> str:
    low = raw.lstrip().lower()
    if raw.startswith(b"%PDF-"):
        return "PDF"
    if raw.startswith(b"PK\x03\x04"):
        return "ZIP_CONTAINER"
    if raw.startswith(bytes.fromhex("D0CF11E0A1B11AE1")):
        return "OLE_CFB"
    if raw.startswith(b"HWP Document File V3.00"):
        return "HWP3"
    if low.startswith((b"<!doctype html", b"<html")):
        return "HTML"
    if raw.startswith(b"{") or raw.startswith(b"["):
        return "JSON_LIKE"
    return "UNKNOWN"


def extract_refs(text: str, base_url: str) -> list[str]:
    decoded = html.unescape(text)
    refs = []
    seen = set()
    patterns = [
        r'''(?:src|href)\s*=\s*["']([^"']+)["']''',
        r'''(?:url|file|path|xml|json|text|html|page|image)["']?\s*[:=]\s*["']([^"']+)["']''',
        r'''["']([^"']*(?:result/attach|preview/result|\.xml|\.json|\.txt|\.html|\.htm|\.svg|\.png|\.jpg|\.jpeg|\.gif)[^"']*)["']''',
    ]
    for pat in patterns:
        for m in re.finditer(pat, decoded, flags=re.I):
            raw = m.group(1).strip()
            if not raw or raw.startswith(("javascript:", "data:", "#")):
                continue
            full = urljoin(base_url, raw)
            if host(full) != HOST:
                continue
            if full not in seen:
                seen.add(full)
                refs.append(full)
    return refs


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY ATTACHMENT PREVIEW ASSET FORENSICS")
    print("=" * 60)
    print("Target pstSn:", PST_SN)
    print("Target fileNo:", FILE_NO)
    print("State mutation: DISABLED")
    print("OCR: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    records = []

    detail_url = f"{BASE}/bbs010308/{PST_SN}"
    r1 = s.get(detail_url, timeout=TIMEOUT)
    records.append({"kind": "detail", "status": r1.status_code, "url": r1.url, "host": host(r1.url)})

    r2 = s.get(
        f"{BASE}/bbs010308/atchFileDetail",
        params={"pstSn": PST_SN},
        headers={"Referer": detail_url, "X-Requested-With": "XMLHttpRequest"},
        timeout=TIMEOUT,
    )
    records.append({"kind": "metadata", "status": r2.status_code, "url": r2.url, "host": host(r2.url)})

    r3 = s.get(
        f"{BASE}/bbs010308/filePreview",
        params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO},
        headers={"Referer": detail_url},
        timeout=TIMEOUT,
        allow_redirects=True,
    )
    preview_text = r3.text[:MAX_TEXT_CHARS]
    records.append({
        "kind": "preview",
        "status": r3.status_code,
        "url": r3.url,
        "host": host(r3.url),
        "content_type": r3.headers.get("Content-Type", ""),
        "signature_class": classify(r3.content[:64]),
        "text_chars": len(preview_text),
    })

    print("PREVIEW URL:", r3.url)
    print("PREVIEW HTTP:", r3.status_code)
    print("PREVIEW TEXT CHARS:", len(preview_text))

    refs = extract_refs(preview_text, r3.url)
    prioritized = []
    for u in refs:
        lu = u.lower()
        if any(k in lu for k in ("result/attach", "preview/result", ".xml", ".json", ".txt", ".htm", ".html")):
            prioritized.append(u)
    prioritized = prioritized[: max(0, MAX_REQUESTS - len(records))]

    print("DISCOVERED REFS:", len(refs))
    for i, u in enumerate(refs[:80], 1):
        print(f"REF {i}: {u}")

    fetched = []
    for u in prioritized:
        try:
            rr = s.get(u, headers={"Referer": r3.url}, timeout=TIMEOUT, allow_redirects=True)
            raw = rr.content[:2 * 1024 * 1024]
            text = ""
            if classify(raw) in {"HTML", "JSON_LIKE", "UNKNOWN"}:
                try:
                    text = rr.text[:MAX_TEXT_CHARS]
                except Exception:
                    text = ""
            rec = {
                "kind": "preview_asset",
                "status": rr.status_code,
                "url": rr.url,
                "host": host(rr.url),
                "content_type": rr.headers.get("Content-Type", ""),
                "body_bytes": len(raw),
                "signature_class": classify(raw),
                "text_chars": len(text),
                "contains_direct": any(x in text for x in ("개발밀도관리구역", "개발밀도 관리구역")),
                "contains_high_signal": any(x in text for x in ("개발밀도", "밀도관리")),
                "head_text": re.sub(r"\s+", " ", text[:1200]),
            }
        except Exception as exc:
            rec = {"kind": "preview_asset", "url": u, "error": repr(exc)}
        fetched.append(rec)
        records.append({k: v for k, v in rec.items() if k != "head_text"})
        print("ASSET:", rec)

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S15",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO},
        "preview_url": r3.url,
        "discovered_refs": refs,
        "fetched_assets": fetched,
        "records": records,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all request hosts official": all((not r.get("host")) or r.get("host") == HOST for r in records),
        "preview available": r3.status_code == 200 and bool(preview_text.strip()),
        "preview refs discovered": len(refs) > 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("SUMMARY")
    print("Preview refs:", len(refs))
    print("Fetched candidate assets:", len(fetched))
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("preview asset forensics validation failed")


if __name__ == "__main__":
    main()
