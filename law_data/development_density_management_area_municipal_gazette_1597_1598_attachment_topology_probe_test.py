# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S54
Attachment topology probe around Gazette 1597 / 1598.

Purpose:
- determine whether empty attachment metadata at pstSn 181109 / 181376 is a
  local orphan pattern or a wider board/storage transition;
- query the same official metadata endpoint for neighboring gazettes only;
- no attachment body download;
- no cumulative-state mutation;
- no legal negative evidence or SITE/runtime promotion.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
REGISTRY = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_1597_1598_attachment_topology_probe.json"
TARGET_PSTS = {"181109", "181376"}
TARGET_GAZETTES = {1597, 1598}
WINDOW_BEFORE = 3
WINDOW_AFTER = 3
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


def fetch_meta(session: requests.Session, pst: str) -> Dict[str, Any]:
    url = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"
    out = {"http_status": None, "final_url": "", "json_detected": False, "attachment_count": 0, "error": ""}
    try:
        with session.get(url, params={"pstSn": pst}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
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
            text = raw.decode(r.encoding or "utf-8", errors="replace")
            try:
                obj = r.json()
            except Exception:
                try:
                    obj = json.loads(text)
                except Exception:
                    obj = None
            out["json_detected"] = obj is not None
            if obj is not None:
                items = flatten_items(obj)
                seen = set()
                for item in items:
                    lower = {str(k).lower(): v for k, v in item.items()}
                    key = (
                        norm(lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno")),
                        norm(lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("strefilenm")),
                    )
                    if key != ("", ""):
                        seen.add(key)
                out["attachment_count"] = len(seen)
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("GAZETTE 1597 / 1598 ATTACHMENT TOPOLOGY PROBE")
    print("=" * 60)
    print("Attachment body download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    if not REGISTRY.exists():
        raise FileNotFoundError(REGISTRY)
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = list(reg.get("canonical_gazette_rows") or [])
    rows = [r for r in rows if norm(r.get("pstSn")) and r.get("gazette_number") is not None]
    rows.sort(key=lambda r: (int(r.get("gazette_number") or 0), norm(r.get("pstSn"))))

    idxs = [i for i, r in enumerate(rows) if norm(r.get("pstSn")) in TARGET_PSTS]
    if len(idxs) != 2:
        raise AssertionError(f"expected two targets in registry, got {len(idxs)}")
    lo = max(0, min(idxs) - WINDOW_BEFORE)
    hi = min(len(rows), max(idxs) + WINDOW_AFTER + 1)
    selected = rows[lo:hi]

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9"})
    results = []
    for r in selected:
        pst = norm(r.get("pstSn"))
        meta = fetch_meta(session, pst)
        rec = {
            "gazette_number": int(r.get("gazette_number") or 0),
            "date": norm(r.get("date")),
            "pstSn": pst,
            "is_target": pst in TARGET_PSTS,
            **meta,
        }
        results.append(rec)
        print({k: rec.get(k) for k in ["gazette_number", "date", "pstSn", "is_target", "http_status", "json_detected", "attachment_count", "error"]})

    target_rows = [r for r in results if r["is_target"]]
    neighbors = [r for r in results if not r["is_target"]]
    neighbor_nonempty = [r for r in neighbors if r["http_status"] == 200 and r["json_detected"] and r["attachment_count"] > 0]
    neighbor_empty = [r for r in neighbors if r["http_status"] == 200 and r["json_detected"] and r["attachment_count"] == 0]
    target_all_empty = all(r["http_status"] == 200 and r["json_detected"] and r["attachment_count"] == 0 for r in target_rows)
    neighbors_all_transport_ok = all(r["http_status"] == 200 and r["json_detected"] and not r["error"] for r in neighbors)
    local_orphan_pattern = target_all_empty and len(neighbor_nonempty) > 0 and len(neighbor_empty) == 0
    local_cluster_orphan_pattern = target_all_empty and len(neighbor_nonempty) > 0 and len(neighbor_empty) > 0

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S54",
        "targets": sorted(TARGET_PSTS),
        "rows": results,
        "summary": {
            "target_all_empty": target_all_empty,
            "neighbor_count": len(neighbors),
            "neighbor_nonempty_count": len(neighbor_nonempty),
            "neighbor_empty_count": len(neighbor_empty),
            "neighbors_all_transport_ok": neighbors_all_transport_ok,
            "local_orphan_pattern": local_orphan_pattern,
            "local_cluster_orphan_pattern": local_cluster_orphan_pattern,
        },
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

    unsafe = any(output[k] for k in ["verified_positive", "runtime_registration_allowed", "site_positive_allowed", "site_negative_allowed", "final_positive_promotion_allowed"])
    vals = {
        "two targets found": len(target_rows) == 2,
        "targets empty metadata": target_all_empty,
        "neighbors present": len(neighbors) > 0,
        "neighbor transport ok": neighbors_all_transport_ok,
        "at least one neighbor attachment": len(neighbor_nonempty) > 0,
        "body download disabled": not output["attachment_body_download_executed"],
        "state mutation disabled": not output["state_mutation_executed"],
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
        raise AssertionError("Gazette 1597/1598 attachment topology probe failed")


if __name__ == "__main__":
    main()
