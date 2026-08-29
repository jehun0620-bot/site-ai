# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S4
Inner attachment metadata forensics for pstSn 28847 (Gazette 699).

Purpose
-------
The prior metadata probe confirmed HTTP 200 and top-level key `atchFileVO`, but
normal HWP selection returned None. This stage inspects only the inner attachment
objects and reports their filenames/extensions/file numbers so the next bounded
format-specific step can be chosen safely.

Safety
------
- metadata only
- no downloads
- no OCR
- no legal promotion
- no negative evidence
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from law_data import development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search_test as hwp5

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_missing_hwp_attachment_inner_forensics.json"
PST = "28847"


def flatten_attachments(obj: Any) -> List[Dict[str, Any]]:
    if not isinstance(obj, dict):
        return []
    inner = obj.get("atchFileVO")
    if inner is None:
        return []
    if isinstance(inner, list):
        return [x for x in inner if isinstance(x, dict)]
    if isinstance(inner, dict):
        # Some Seongnam responses wrap the actual list one level deeper.
        for key in ("list", "items", "files", "atchFileList", "fileList"):
            value = inner.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
        return [inner]
    return []


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MISSING HWP ATTACHMENT INNER FORENSICS")
    print("=" * 60)
    print("Target pstSn:", PST)
    print("Downloads: DISABLED")
    print("OCR: DISABLED")
    print()

    session = hwp5.requests.Session()
    session.headers.update({"User-Agent": hwp5.USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    hs, mu, obj = hwp5.get_json(session, PST)
    attachments = flatten_attachments(obj)

    print("Metadata HTTP:", hs)
    print("Metadata URL:", mu)
    print("Attachment count:", len(attachments))

    summaries: List[Dict[str, Any]] = []
    for idx, item in enumerate(attachments, start=1):
        summary = {
            "index": idx,
            "fileNo": item.get("fileNo") or item.get("file_no") or item.get("atchFileSn"),
            "orginlFileNm": item.get("orginlFileNm"),
            "originalFileName": item.get("originalFileName") or item.get("original_file_name"),
            "streFileNm": item.get("streFileNm"),
            "fileExtsn": item.get("fileExtsn") or item.get("fileExt") or item.get("extension"),
            "fileSize": item.get("fileSize") or item.get("fileMg") or item.get("size"),
            "raw": item,
        }
        summaries.append(summary)
        print(f"ATTACHMENT {idx}:", summary)

    lower_names = []
    for s in summaries:
        for key in ("orginlFileNm", "originalFileName", "streFileNm"):
            v = s.get(key)
            if isinstance(v, str):
                lower_names.append(v.lower())
    exts = []
    for s in summaries:
        v = s.get("fileExtsn")
        if isinstance(v, str):
            exts.append(v.lower().lstrip("."))

    detected_formats = sorted(set(
        [ext for ext in exts if ext]
        + [name.rsplit(".", 1)[-1] for name in lower_names if "." in name]
    ))

    output = {
        "pstSn": PST,
        "metadata_http": hs,
        "metadata_url": mu,
        "attachment_count": len(attachments),
        "attachments": summaries,
        "detected_formats": detected_formats,
        "negative_evidence_allowed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Detected formats:", detected_formats)
    print("Output:", OUT)

    unsafe = any([
        output["verified_positive"],
        output["runtime_registration_allowed"],
        output["site_positive_allowed"],
        output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "official metadata host": hwp5.host(mu) == "www.seongnam.go.kr",
        "metadata http 200": hs == 200,
        "attachment metadata present": len(attachments) > 0,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("missing HWP attachment inner forensics failed")


if __name__ == "__main__":
    main()
