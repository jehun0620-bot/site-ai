# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S45
Gazette 1296 / pstSn 29471 detail-page attachment reference probe.

Purpose:
- inspect the official detail HTML because the attachment metadata endpoint returned an empty list;
- recover any attachment/file identifiers or download references embedded in HTML/JS;
- do not download attachment bodies;
- do not infer legal negative evidence or promote SITE/runtime truth.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1296_detail_attachment_reference_probe.json"

PSTSN = "29471"
GAZETTE_NUMBER = 1296
DATE = "2015-03-04"
DETAIL_URL = f"https://www.seongnam.go.kr/bbs010308/{PSTSN}"
TIMEOUT = 20
MAX_BYTES = 8 * 1024 * 1024
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def host(u: str) -> str:
    try:
        return (urlparse(u).hostname or "").lower()
    except Exception:
        return ""


def official(h: str) -> bool:
    return bool(h) and (h == "go.kr" or h.endswith(".go.kr"))


def bounded_get(session: requests.Session, url: str) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "response_bytes": 0, "content_type": "", "text": "", "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            out["http_status"] = r.status_code
            out["final_url"] = str(r.url)
            out["content_type"] = r.headers.get("Content-Type", "")
            chunks = []
            total = 0
            for chunk in r.iter_content(131072):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("detail response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            out["response_bytes"] = len(raw)
            enc = r.encoding or r.apparent_encoding or "utf-8"
            out["text"] = raw.decode(enc, errors="replace")
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def unique(seq: List[str]) -> List[str]:
    seen = set()
    out = []
    for x in seq:
        x = norm(x)
        if x and x not in seen:
            seen.add(x)
            out.append(x)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1296 DETAIL ATTACHMENT REFERENCE PROBE")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("Attachment body download: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    response = bounded_get(session, DETAIL_URL)
    html = response.get("text") or ""

    hrefs = unique(re.findall(r'''href\s*=\s*["']([^"']+)["']''', html, flags=re.I))
    onclicks = unique(re.findall(r'''onclick\s*=\s*["']([^"']+)["']''', html, flags=re.I))
    srcs = unique(re.findall(r'''src\s*=\s*["']([^"']+)["']''', html, flags=re.I))

    attachment_hrefs = [x for x in hrefs if re.search(r"atch|attach|file|down|download|fileno|pstsn", x, flags=re.I)]
    attachment_onclicks = [x for x in onclicks if re.search(r"atch|attach|file|down|download|fileno|pstsn", x, flags=re.I)]
    attachment_srcs = [x for x in srcs if re.search(r"atch|attach|file|down|download|fileno|pstsn", x, flags=re.I)]

    file_no_tokens = unique(re.findall(r'''(?:fileNo|file_no|atchFileNo|atchfileno|fileId|fileSn)\s*[=:,(\s"']+([0-9]{2,})''', html, flags=re.I))
    pst_tokens = unique(re.findall(r'''pstSn\s*[=:,(\s"']+([0-9]{2,})''', html, flags=re.I))
    filename_tokens = unique(re.findall(r'''([\w가-힣().\-\s]{1,120}\.(?:hwp|hwpx|pdf|xls|xlsx|zip|doc|docx))''', html, flags=re.I))

    keyword_counts = {k: len(re.findall(k, html, flags=re.I)) for k in [
        "atchFileDetail", "atchFile", "fileDown", "download", "fileNo", "pstSn", "hwp", "pdf", "xls", "hwpx"
    ]}

    suspicious_lines = []
    for raw_line in html.splitlines():
        line = norm(raw_line)
        if line and re.search(r"atch|attach|file|down|download|hwp|pdf|xls|hwpx", line, flags=re.I):
            suspicious_lines.append(line[:1000])
    suspicious_lines = unique(suspicious_lines)[:200]

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S45",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "request": {"count": 1, "method": "GET", "url": DETAIL_URL},
        "response": {k: response[k] for k in ["http_status", "final_url", "response_bytes", "content_type", "error"]},
        "html_chars": len(html),
        "keyword_counts": keyword_counts,
        "attachment_like_hrefs": attachment_hrefs,
        "attachment_like_onclicks": attachment_onclicks,
        "attachment_like_srcs": attachment_srcs,
        "file_no_tokens": file_no_tokens,
        "pstSn_tokens": pst_tokens,
        "filename_tokens": filename_tokens,
        "suspicious_lines": suspicious_lines,
        "attachment_body_download_executed": False,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any(output[k] for k in [
        "verified_positive", "runtime_registration_allowed", "site_positive_allowed",
        "site_negative_allowed", "final_positive_promotion_allowed",
    ])
    vals = {
        "HTTP 200": response["http_status"] == 200,
        "official same host": official(host(response["final_url"])) and host(response["final_url"]) == host(DETAIL_URL),
        "single detail request": output["request"]["count"] == 1,
        "HTML recovered": len(html) > 0,
        "attachment body download disabled": not output["attachment_body_download_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("HTTP:", response["http_status"])
    print("Final URL:", response["final_url"])
    print("Content-Type:", response["content_type"])
    print("HTML chars:", len(html))
    print("Keyword counts:", keyword_counts)
    print("Attachment-like hrefs:", len(attachment_hrefs))
    for x in attachment_hrefs[:20]:
        print("HREF:", x)
    print("Attachment-like onclicks:", len(attachment_onclicks))
    for x in attachment_onclicks[:20]:
        print("ONCLICK:", x)
    print("FileNo tokens:", file_no_tokens)
    print("pstSn tokens:", pst_tokens)
    print("Filename tokens:", filename_tokens[:20])
    print("Suspicious lines:", len(suspicious_lines))
    for x in suspicious_lines[:30]:
        print("LINE:", x)
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1296 detail attachment reference probe failed")


if __name__ == "__main__":
    main()
