# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S51
Attachment metadata forensic probe for Gazette 1597/1598.

Safety:
- exact targets only;
- metadata requests only, no attachment body download;
- no cumulative state mutation;
- no legal negative evidence;
- no SITE/runtime promotion.
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
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1597_1598_attachment_forensic.json"

TARGETS = [
    {"gazette_number": 1597, "date": "2019-04-09", "pstSn": "181109"},
    {"gazette_number": 1598, "date": "2019-04-15", "pstSn": "181376"},
]
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


def fetch_json(session: requests.Session, pst: str) -> Dict[str, Any]:
    detail_url = f"https://www.seongnam.go.kr/bbs010308/{pst}"
    meta_url = urljoin(detail_url, "/bbs010308/atchFileDetail")
    out = {"http_status": None, "final_url": "", "json": None, "text": "", "response_bytes": 0, "error": "", "meta_url": meta_url}
    try:
        with session.get(meta_url, params={"pstSn": pst}, timeout=TIMEOUT, allow_redirects=True, stream=True, headers={"Referer": detail_url}) as r:
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
    print("GAZETTE 1597 / 1598 ATTACHMENT FORENSIC")
    print("=" * 60)
    print("Attachment body download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    rows = []
    for target in TARGETS:
        pst = target["pstSn"]
        response = fetch_json(session, pst)
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

        row = {
            "target": target,
            "response": {k: response[k] for k in ["http_status", "final_url", "response_bytes", "error"]},
            "json_detected": response.get("json") is not None,
            "attachments": normalized,
            "attachment_count": len(normalized),
            "extension_counts": ext_counts,
            "hwp_attachment_count": sum(1 for x in normalized if x["file_ext"] == "hwp" or x["file_name"].lower().endswith(".hwp")),
        }
        rows.append(row)

        print("\n" + "-" * 60)
        print("Gazette:", target["gazette_number"], target["date"], "pstSn", pst)
        print("HTTP:", response["http_status"])
        print("Final URL:", response["final_url"])
        print("JSON detected:", row["json_detected"])
        print("Attachment count:", row["attachment_count"])
        print("Extension counts:", row["extension_counts"])
        print("HWP attachment count:", row["hwp_attachment_count"])
        for i, x in enumerate(normalized, 1):
            print(f"ATTACHMENT {i}:", {k: x[k] for k in ["file_no", "file_name", "stored_file_name", "file_ext", "file_size", "file_type", "file_class", "path"]})

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S51",
        "targets": rows,
        "request_count": len(TARGETS),
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
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
        "two exact targets": len(rows) == 2,
        "all HTTP 200": all(r["response"]["http_status"] == 200 for r in rows),
        "all official host": all(official(host(r["response"]["final_url"])) for r in rows),
        "all JSON detected": all(r["json_detected"] for r in rows),
        "body download disabled": not output["attachment_body_download_executed"],
        "state mutation disabled": not output["state_mutation_executed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nOutput:", OUT)
    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1597/1598 attachment forensic validation failed")


if __name__ == "__main__":
    main()
