# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S46
Gazette 1296 / pstSn 29471 attachment topology probe.

Purpose:
- determine whether the empty attachment metadata on pstSn 29471 is isolated or part of a local board/storage transition;
- compare only nearby known gazette rows through the same official metadata endpoint;
- do not download attachment bodies;
- do not mutate cumulative search state;
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
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1296_attachment_topology_probe.json"

TARGET_PST = "29471"
ROWS = [
    {"gazette_number": 1294, "date": "2015-02-23", "pstSn": "29469"},
    {"gazette_number": 1295, "date": "2015-03-02", "pstSn": "29470"},
    {"gazette_number": 1296, "date": "2015-03-04", "pstSn": "29471"},
    {"gazette_number": 1297, "date": "2015-03-09", "pstSn": "89879"},
    {"gazette_number": 1298, "date": "2015-03-16", "pstSn": "96649"},
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
    }


def fetch_meta(session: requests.Session, pst: str) -> Dict[str, Any]:
    detail_url = f"https://www.seongnam.go.kr/bbs010308/{pst}"
    meta_url = urljoin(detail_url, "/bbs010308/atchFileDetail")
    out: Dict[str, Any] = {
        "pstSn": pst,
        "meta_url": meta_url,
        "http_status": None,
        "final_url": "",
        "response_bytes": 0,
        "json_detected": False,
        "attachments": [],
        "error": "",
    }
    try:
        headers = {"Referer": detail_url}
        with session.get(meta_url, params={"pstSn": pst}, headers=headers, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
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
            obj = None
            try:
                obj = r.json()
            except Exception:
                try:
                    obj = json.loads(text)
                except Exception:
                    pass
            out["json_detected"] = obj is not None
            items = flatten_items(obj) if obj is not None else []
            seen = set()
            normalized = []
            for item in items:
                x = normalize_item(item)
                key = (x["file_no"], x["file_name"], x["stored_file_name"])
                if key in seen:
                    continue
                seen.add(key)
                normalized.append(x)
            out["attachments"] = normalized
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1296 ATTACHMENT TOPOLOGY PROBE")
    print("=" * 60)
    print("Target pstSn:", TARGET_PST)
    print("Rows:", len(ROWS))
    print("Attachment body download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})

    results = []
    for row in ROWS:
        probe = fetch_meta(session, row["pstSn"])
        attachments = probe.get("attachments") or []
        ext_counts: Dict[str, int] = {}
        for x in attachments:
            ext = x.get("file_ext") or Path(x.get("file_name") or "").suffix.lower().lstrip(".") or "UNKNOWN"
            ext_counts[ext] = ext_counts.get(ext, 0) + 1
        rec = dict(row)
        rec.update({
            "http_status": probe.get("http_status"),
            "final_url": probe.get("final_url"),
            "response_bytes": probe.get("response_bytes"),
            "json_detected": probe.get("json_detected"),
            "attachment_count": len(attachments),
            "extension_counts": ext_counts,
            "attachments": attachments,
            "error": probe.get("error"),
        })
        results.append(rec)
        print("ROW:", {
            "gazette_number": rec["gazette_number"],
            "date": rec["date"],
            "pstSn": rec["pstSn"],
            "http": rec["http_status"],
            "json": rec["json_detected"],
            "attachment_count": rec["attachment_count"],
            "extension_counts": rec["extension_counts"],
            "error": rec["error"],
        })

    target = next(r for r in results if r["pstSn"] == TARGET_PST)
    neighbors = [r for r in results if r["pstSn"] != TARGET_PST]
    neighbor_nonempty = sum(1 for r in neighbors if r["attachment_count"] > 0)
    neighbor_all_transport_ok = all(r["http_status"] == 200 and r["json_detected"] and not r["error"] for r in neighbors)
    target_empty = target["http_status"] == 200 and target["json_detected"] and target["attachment_count"] == 0 and not target["error"]
    isolated_empty_pattern = target_empty and neighbor_all_transport_ok and neighbor_nonempty >= 2

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S46",
        "target_pstSn": TARGET_PST,
        "request_count": len(ROWS),
        "results": results,
        "summary": {
            "target_empty_metadata": target_empty,
            "neighbor_nonempty_count": neighbor_nonempty,
            "neighbor_count": len(neighbors),
            "neighbor_all_transport_ok": neighbor_all_transport_ok,
            "isolated_empty_pattern": isolated_empty_pattern,
        },
        "attachment_body_download_executed": False,
        "state_mutation_allowed": False,
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
        "exact row budget": output["request_count"] == len(ROWS),
        "target HTTP 200": target["http_status"] == 200,
        "target JSON detected": target["json_detected"],
        "target metadata empty": target["attachment_count"] == 0,
        "all final hosts official": all(official(host(r["final_url"])) for r in results if r["final_url"]),
        "attachment body download disabled": not output["attachment_body_download_executed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("\nSUMMARY")
    for k, v in output["summary"].items():
        print(f"{k}: {v}")
    print("Output:", OUT)

    print("\nVALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("Gazette 1296 attachment topology probe failed")


if __name__ == "__main__":
    main()
