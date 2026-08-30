# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S41
Gazette 1241 / pstSn 29416 attachment metadata forensic probe.

Purpose:
- explain why the HWP-only selector reports "HWP attachment not found";
- enumerate every official attachment metadata item for this exact gazette row;
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
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1241_attachment_forensic.json"

PSTSN = "29416"
GAZETTE_NUMBER = 1241
DATE = "2014-04-14"
DETAIL_URL = f"https://www.seongnam.go.kr/bbs010308/{PSTSN}"
META_URL = urljoin(DETAIL_URL, "/bbs010308/atchFileDetail")
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


def fetch_json(session: requests.Session) -> Dict[str, Any]:
    out = {"http_status": None, "final_url": "", "json": None, "text": "", "response_bytes": 0, "error": ""}
    try:
        with session.get(META_URL, params={"pstSn": PSTSN}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
            out["http_status"] = r.status_code
            out["final_url"] = str(r.url)
            chunks = []
            total = 0
            for chunk in r.iter_content(131072):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_BYTES:
                    raise ValueError("metadata response too large")
                chunks.append(chunk)
            raw = b"".join(chunks)
            out["response_bytes"] = len(raw)
            text = raw.decode(r.encoding or "utf-8", errors="replace")
            out["text"] = text
            try:
                out["json"] = r.json()
            except Exception:
                try:
                    out["json"] = json.loads(text)
                except Exception:
                    pass
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    found: List[Dict[str, Any]] = []
    def walk(x: Any) -> None:
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x}
            if any(k in keys for k in ["fileno", "file_no", "atchfileno", "orginlfilenm", "strefilenm"]):
                found.append(x)
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)
    walk(obj)
    return found


def normalize_item(item: Dict[str, Any]) -> Dict[str, Any]:
    lower = {str(k).lower(): v for k, v in item.items()}
    file_no = lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
    name = lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm")
    stored = lower.get("strefilenm") or ""
    ext = lower.get("fileextsn") or lower.get("fileext") or ""
    return {
        "file_no": str(file_no or ""),
        "file_name": norm(name),
        "stored_file_name": norm(stored),
        "file_ext": norm(ext).lower(),
        "file_size": lower.get("filesize"),
        "file_type": norm(lower.get("filety")),
        "file_class": norm(lower.get("fileclsf")),
        "path": norm(lower.get("flpth")),
        "raw": item,
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1241 ATTACHMENT FORENSIC")
    print("=" * 60)
    print("Gazette:", GAZETTE_NUMBER, DATE, "pstSn", PSTSN)
    print("Attachment body download: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", "Referer": DETAIL_URL})
    response = fetch_json(session)
    items = flatten_items(response.get("json")) if response.get("json") is not None else []
    normalized = []
    seen = set()
    for item in items:
        x = normalize_item(item)
        key = (x["file_no"], x["file_name"], x["stored_file_name"])
        if key in seen:
            continue
        seen.add(key)
        normalized.append(x)

    ext_counts: Dict[str, int] = {}
    for x in normalized:
        ext = x["file_ext"] or Path(x["file_name"]).suffix.lower().lstrip(".") or "UNKNOWN"
        ext_counts[ext] = ext_counts.get(ext, 0) + 1

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S41",
        "target": {"gazette_number": GAZETTE_NUMBER, "date": DATE, "pstSn": PSTSN},
        "request": {"count": 1, "method": "GET", "endpoint": META_URL, "params": {"pstSn": PSTSN}},
        "response": {k: response[k] for k in ["http_status", "final_url", "response_bytes", "error"]},
        "json_detected": response.get("json") is not None,
        "attachments": normalized,
        "attachment_count": len(normalized),
        "extension_counts": ext_counts,
        "hwp_attachment_count": sum(1 for x in normalized if x["file_ext"] == "hwp" or x["file_name"].lower().endswith(".hwp")),
        "attachment_body_download_executed": False,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    unsafe = any(output[k] for k in ["verified_positive", "runtime_registration_allowed", "site_positive_allowed", "site_negative_allowed", "final_positive_promotion_allowed"])
    vals = {
        "HTTP 200": response["http_status"] == 200,
        "official same host": official(host(response["final_url"])) and host(response["final_url"]) == host(META_URL),
        "single metadata request": output["request"]["count"] == 1,
        "JSON detected": output["json_detected"],
        "attachment metadata recovered": len(normalized) > 0,
        "attachment body download disabled": not output["attachment_body_download_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("HTTP:", response["http_status"])
    print("Final URL:", response["final_url"])
    print("JSON detected:", output["json_detected"])
    print("Attachment count:", len(normalized))
    print("Extension counts:", ext_counts)
    print("HWP attachment count:", output["hwp_attachment_count"])
    for i, x in enumerate(normalized, 1):
        print(f"ATTACHMENT {i}:", {k: x[k] for k in ["file_no", "file_name", "stored_file_name", "file_ext", "file_size", "file_type", "file_class", "path"]})
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1241 attachment forensic validation failed")


if __name__ == "__main__":
    main()
