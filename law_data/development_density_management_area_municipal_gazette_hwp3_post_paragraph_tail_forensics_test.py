# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-13
Development Density Management Area
Municipal Gazette HWP3 Post-Paragraph Tail Forensics

Offline-only forensics of the large decompressed remainder after the first validated
HWP3 top-level paragraph list in the 2003 gazette sample.

Why this stage exists
---------------------
T-28-S1-12 recovered meaningful searchable text but consumed only ~95 KB of a
~1.15 MB decompressed HWP3 body. A zero parse error does not prove that the remainder
is irrelevant. This stage classifies the remainder before any archive-scale search.

Actions
-------
- reproduce the validated raw-DEFLATE body
- reproduce font/style preamble and the first top-level paragraph list boundary
- inspect the remaining bytes for plausible HWP3 paragraph-list headers at bounded offsets
- inspect simple length-prefix / bitmap signatures to distinguish extra-info payloads
- do NOT scan the whole archive, OCR, or promote legal status
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T28S112 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_bounded_paragraph_text_extraction.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_post_paragraph_tail_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
MAX_SCAN_BYTES = 128 * 1024
MAX_CANDIDATES = 50


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def plausible_para_header(data: bytes, offset: int) -> Dict[str, Any] | None:
    if offset + 43 > len(data):
        return None
    follow_prev = data[offset]
    char_count = struct.unpack_from("<H", data, offset + 1)[0]
    line_count = struct.unpack_from("<H", data, offset + 3)[0]
    include_cs = data[offset + 5]
    style_idx = data[offset + 11]
    if follow_prev not in (0, 1):
        return None
    if char_count == 0:
        return {
            "offset": offset,
            "follow_prev": follow_prev,
            "char_count": 0,
            "line_count": line_count,
            "include_char_shape": include_cs,
            "style_index": style_idx,
            "kind": "EMPTY_SENTINEL_LIKE",
        }
    if not (1 <= char_count <= 60000 and 0 <= line_count <= 4096 and include_cs in (0, 1)):
        return None
    # Minimal size lower bound: fixed 43 + optional para shape + line info + at least 2 bytes per hchar.
    lower = 43 + (187 if follow_prev == 0 else 0) + line_count * 14 + char_count * 2
    if offset + lower > len(data):
        return None
    return {
        "offset": offset,
        "follow_prev": follow_prev,
        "char_count": char_count,
        "line_count": line_count,
        "include_char_shape": include_cs,
        "style_index": style_idx,
        "minimum_record_bytes": lower,
        "kind": "PARAGRAPH_HEADER_LIKE",
    }


def signatures(data: bytes) -> Dict[str, Any]:
    sigs = []
    patterns = {
        "BMP": b"BM",
        "GIF87a": b"GIF87a",
        "GIF89a": b"GIF89a",
        "JPEG": b"\xff\xd8\xff",
        "PNG": b"\x89PNG\r\n\x1a\n",
        "OLE": bytes.fromhex("D0CF11E0A1B11AE1"),
        "HWP3": b"HWP Document File V3.00",
    }
    for name, pat in patterns.items():
        start = 0
        hits = []
        while True:
            i = data.find(pat, start)
            if i < 0:
                break
            hits.append(i)
            start = i + 1
            if len(hits) >= 20:
                break
        if hits:
            sigs.append({"name": name, "offsets": hits})
    return {"signatures": sigs}


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP3 POST-PARAGRAPH TAIL FORENSICS")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("Archive traversal: DISABLED")
    print()

    if not T28S112.exists():
        raise FileNotFoundError(T28S112)
    prior = json.loads(T28S112.read_text(encoding="utf-8"))
    path = Path(norm(prior.get("sample_path")))
    if not path.exists():
        raise FileNotFoundError(path)

    # Recover the exact compressed offset from prior HWP3 stage lineage.
    boundary_path = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_compressed_stream_boundary_probe.json"
    if not boundary_path.exists():
        raise FileNotFoundError(boundary_path)
    boundary = json.loads(boundary_path.read_text(encoding="utf-8"))
    offset = int(boundary.get("compressed_stream_offset") or 0)

    raw = path.read_bytes()
    dec = zlib.decompressobj(-zlib.MAX_WBITS)
    body = dec.decompress(raw[offset:]) + dec.flush()
    consumed = int((prior.get("parse") or {}).get("reader_consumed_bytes") or 0)
    if not (0 < consumed < len(body)):
        raise AssertionError("invalid prior consumed boundary")
    tail = body[consumed:]

    scan = tail[: min(len(tail), MAX_SCAN_BYTES)]
    candidates: List[Dict[str, Any]] = []
    for i in range(0, max(0, len(scan) - 43)):
        rec = plausible_para_header(scan, i)
        if rec:
            candidates.append(rec)
            if len(candidates) >= MAX_CANDIDATES:
                break

    prefix_u32 = struct.unpack_from("<I", tail, 0)[0] if len(tail) >= 4 else None
    prefix_u16 = struct.unpack_from("<H", tail, 0)[0] if len(tail) >= 2 else None
    sig = signatures(scan)

    immediate = plausible_para_header(tail, 0)
    if immediate and immediate.get("kind") == "PARAGRAPH_HEADER_LIKE":
        classification = "HWP3_TAIL_BEGINS_WITH_ADDITIONAL_PARAGRAPH_LIST_CANDIDATE"
    elif candidates:
        classification = "HWP3_TAIL_CONTAINS_BOUNDED_PARAGRAPH_LIKE_CANDIDATES"
    elif sig["signatures"]:
        classification = "HWP3_TAIL_APPEARS_BINARY_EXTRA_INFO_WITH_EMBEDDED_ASSETS"
    else:
        classification = "HWP3_TAIL_BINARY_EXTRA_INFO_NO_PARAGRAPH_SIGNATURE_IN_BOUNDED_SCAN"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-13 Municipal Gazette HWP3 Post-Paragraph Tail Forensics",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "sample_path": str(path),
        "decompressed_body_bytes": len(body),
        "prior_consumed_bytes": consumed,
        "tail_bytes": len(tail),
        "tail_prefix_hex": tail[:128].hex(" "),
        "tail_prefix_u16": prefix_u16,
        "tail_prefix_u32": prefix_u32,
        "bounded_scan_bytes": len(scan),
        "immediate_paragraph_candidate": immediate,
        "paragraph_like_candidates": candidates,
        "binary_signatures": sig["signatures"],
        "classification": classification,
        "bulk_archive_traversal_executed": False,
        "ocr_executed": False,
        "semantic_note": "Tail classification is parser-coverage evidence only. It does not establish UQQ700 presence or absence.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP3_POST_PARAGRAPH_TAIL_FORENSICS_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Decompressed body bytes:", len(body))
    print("Prior consumed bytes:", consumed)
    print("Tail bytes:", len(tail))
    print("Tail prefix u16/u32:", prefix_u16, prefix_u32)
    print("Tail prefix hex:", tail[:96].hex(" "))
    print("Immediate paragraph candidate:", immediate)
    print("Paragraph-like candidate count:", len(candidates))
    for c in candidates[:10]:
        print("  CANDIDATE:", c)
    print("Binary signatures:", sig["signatures"])
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["bulk_archive_traversal_executed"], output["ocr_executed"], output["verified_positive"],
        output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior HWP3 text extraction exists": T28S112.exists(),
        "sample exists": path.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "decompressed body reproduced": len(body) == int(prior.get("decompressed_body_bytes") or 0),
        "prior consumed boundary valid": 0 < consumed < len(body),
        "tail exists": len(tail) > 0,
        "bounded scan respected": len(scan) <= MAX_SCAN_BYTES,
        "classification produced": bool(classification),
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP3 post-paragraph tail forensics failed")


if __name__ == "__main__":
    main()
