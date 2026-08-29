# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S13
Forensic recovery of the exact legacy attachment download contract for
Gazette 938 / pstSn 29098 by inspecting official metadata and detail-page
HTML/JavaScript. No file extraction, no cumulative-state mutation, no legal
promotion.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_legacy_attachment_contract_source_forensics.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
FILE_NO = "28559"
BBS_CRT_SN = "16002"
TIMEOUT = 20
MAX_REQUESTS = 3
MAX_TEXT_CHARS = 500000

PATTERNS = [
    r".{0,240}28559.{0,400}",
    r".{0,240}29098.{0,400}",
    r".{0,240}getFile.{0,400}",
    r".{0,240}fileDownload.{0,400}",
    r".{0,240}download.{0,400}",
    r".{0,240}atchFile.{0,400}",
    r"function\s+[A-Za-z0-9_$]+\s*\([^)]*\)\s*\{.{0,1200}",
]


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def text_snippets(text: str):
    compact = html.unescape(text).replace("\r", " ").replace("\n", " ")
    out = []
    seen = set()
    for pat in PATTERNS:
        for m in re.finditer(pat, compact, flags=re.I | re.S):
            s = re.sub(r"\s+", " ", m.group(0)).strip()
            if s and s not in seen:
                seen.add(s)
                out.append(s[:1800])
            if len(out) >= 40:
                return out
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY ATTACHMENT CONTRACT SOURCE FORENSICS")
    print("=" * 60)
    print("Target pstSn:", PST_SN)
    print("Target fileNo:", FILE_NO)
    print("State mutation: DISABLED")
    print("Binary extraction: DISABLED")
    print()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": f"{BASE}/bbs010308",
    })

    requests_made = []

    # 1) Exact attachment metadata raw payload.
    meta_url = f"{BASE}/bbs010308/atchFileDetail"
    meta = session.get(meta_url, params={"pstSn": PST_SN}, timeout=TIMEOUT)
    requests_made.append({"kind": "metadata", "status": meta.status_code, "url": meta.url, "host": host(meta.url)})
    meta_text = meta.text[:MAX_TEXT_CHARS]
    print("METADATA HTTP:", meta.status_code)
    print("METADATA URL:", meta.url)
    print("METADATA RAW:")
    print(meta_text[:12000])
    print()

    # 2) Exact detail contract previously validated for this board: POST /bbs010308/{pstSn}
    detail_url = f"{BASE}/bbs010308/{PST_SN}"
    detail_post = session.post(detail_url, data={}, timeout=TIMEOUT)
    requests_made.append({"kind": "detail_post", "status": detail_post.status_code, "url": detail_post.url, "host": host(detail_post.url)})
    detail_post_text = detail_post.text[:MAX_TEXT_CHARS]
    print("DETAIL POST HTTP:", detail_post.status_code)
    print("DETAIL POST URL:", detail_post.url)
    post_snips = text_snippets(detail_post_text)
    print("DETAIL POST SNIPPETS:")
    for i, s in enumerate(post_snips, 1):
        print(f"[{i}] {s}")
    print()

    # 3) GET detail as a bounded contrast in case legacy rows render differently.
    detail_get = session.get(detail_url, timeout=TIMEOUT)
    requests_made.append({"kind": "detail_get", "status": detail_get.status_code, "url": detail_get.url, "host": host(detail_get.url)})
    detail_get_text = detail_get.text[:MAX_TEXT_CHARS]
    get_snips = text_snippets(detail_get_text)
    print("DETAIL GET HTTP:", detail_get.status_code)
    print("DETAIL GET URL:", detail_get.url)
    print("DETAIL GET SNIPPETS:")
    for i, s in enumerate(get_snips, 1):
        print(f"[{i}] {s}")
    print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S13",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO, "bbsCrtSn": BBS_CRT_SN},
        "requests": requests_made,
        "metadata_raw": meta_text,
        "detail_post_snippets": post_snips,
        "detail_get_snippets": get_snips,
        "network_request_count": len(requests_made),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(requests_made) <= MAX_REQUESTS,
        "all hosts official": all(r["host"] == HOST for r in requests_made),
        "metadata available": meta.status_code == 200 and bool(meta_text.strip()),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    print("Output:", OUT)
    if not all(vals.values()):
        raise AssertionError("legacy attachment contract source forensics failed")


if __name__ == "__main__":
    main()
