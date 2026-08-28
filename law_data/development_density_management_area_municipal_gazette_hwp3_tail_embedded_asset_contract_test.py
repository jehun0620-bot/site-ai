# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-13-1
Development Density Management Area
Municipal Gazette HWP3 Tail Embedded Asset Contract

Offline refinement of T-28-S1-13.

The prior bounded scan found many byte-aligned paragraph-like false positives inside
binary data. This stage anchors classification on the tail's actual leading structure:
- small integer/count-like prefix
- embedded asset filename ending in .jpg/.bmp/.gif/.png
- image magic shortly after the filename
- repeated image signatures within a bounded window

No text or legal semantics are inferred from binary assets.
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
T28S113 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_post_paragraph_tail_forensics.json"
T28S112 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_bounded_paragraph_text_extraction.json"
BOUNDARY = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_compressed_stream_boundary_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_tail_embedded_asset_contract.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
MAX_SCAN = 256 * 1024
IMAGE_MAGICS = {
    "JPEG": b"\xff\xd8\xff",
    "BMP": b"BM",
    "GIF87a": b"GIF87a",
    "GIF89a": b"GIF89a",
    "PNG": b"\x89PNG\r\n\x1a\n",
}


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def find_ascii_filename(data: bytes, limit: int = 256) -> Dict[str, Any] | None:
    head = data[:limit]
    for m in re.finditer(rb"[A-Za-z0-9_$().+\-]{3,}\.(?:jpg|jpeg|bmp|gif|png)\x00?", head, re.I):
        raw = m.group(0).rstrip(b"\x00")
        return {
            "offset": m.start(),
            "end": m.end(),
            "filename": raw.decode("ascii", errors="replace"),
        }
    return None


def collect_signatures(data: bytes) -> List[Dict[str, Any]]:
    out = []
    for name, magic in IMAGE_MAGICS.items():
        offsets = []
        start = 0
        while True:
            i = data.find(magic, start)
            if i < 0:
                break
            offsets.append(i)
            start = i + 1
            if len(offsets) >= 50:
                break
        if offsets:
            out.append({"name": name, "offsets": offsets})
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP3 TAIL EMBEDDED ASSET CONTRACT")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("OCR: DISABLED")
    print("Archive traversal: DISABLED")
    print()

    for p in (T28S113, T28S112, BOUNDARY):
        if not p.exists():
            raise FileNotFoundError(p)
    prior_tail = json.loads(T28S113.read_text(encoding="utf-8"))
    prior_text = json.loads(T28S112.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY.read_text(encoding="utf-8"))

    path = Path(norm(prior_text.get("sample_path")))
    if not path.exists():
        raise FileNotFoundError(path)

    raw = path.read_bytes()
    comp_offset = int(boundary.get("compressed_stream_offset") or 0)
    dec = zlib.decompressobj(-zlib.MAX_WBITS)
    body = dec.decompress(raw[comp_offset:]) + dec.flush()
    consumed = int((prior_text.get("parse") or {}).get("reader_consumed_bytes") or 0)
    tail = body[consumed:]
    scan = tail[: min(len(tail), MAX_SCAN)]

    prefix_u32 = [struct.unpack_from("<I", tail, i)[0] for i in (0, 4) if len(tail) >= i + 4]
    filename = find_ascii_filename(tail)
    signatures = collect_signatures(scan)
    first_sig = None
    if signatures:
        first_sig = min(({"name": s["name"], "offset": off} for s in signatures for off in s["offsets"]), key=lambda x: x["offset"])

    filename_before_first_magic = bool(filename and first_sig and filename["offset"] < first_sig["offset"] <= filename["end"] + 64)
    multiple_image_signatures = sum(len(s["offsets"]) for s in signatures) >= 2
    prefix_count_like = bool(prefix_u32 and 0 < prefix_u32[0] < 100000)

    asset_contract = bool(filename and first_sig and filename_before_first_magic and prefix_count_like)
    if asset_contract and multiple_image_signatures:
        classification = "HWP3_POST_PARAGRAPH_TAIL_CONFIRMED_EMBEDDED_ASSET_REGION"
    elif asset_contract:
        classification = "HWP3_POST_PARAGRAPH_TAIL_LEADING_EMBEDDED_ASSET_CONFIRMED"
    else:
        classification = "HWP3_POST_PARAGRAPH_TAIL_ASSET_CONTRACT_NOT_CONFIRMED"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-13-1 Municipal Gazette HWP3 Tail Embedded Asset Contract",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "sample_path": str(path),
        "decompressed_body_bytes": len(body),
        "paragraph_consumed_bytes": consumed,
        "tail_bytes": len(tail),
        "tail_prefix_hex": tail[:96].hex(" "),
        "prefix_u32": prefix_u32,
        "filename_candidate": filename,
        "first_image_signature": first_sig,
        "bounded_image_signatures": signatures,
        "filename_before_first_magic": filename_before_first_magic,
        "multiple_image_signatures": multiple_image_signatures,
        "prefix_count_like": prefix_count_like,
        "embedded_asset_contract_confirmed": asset_contract,
        "prior_paragraph_like_candidates_reinterpreted_as_binary_false_positives": bool(asset_contract),
        "classification": classification,
        "ocr_executed": False,
        "bulk_archive_traversal_executed": False,
        "semantic_note": "The post-paragraph remainder is binary embedded-asset data. It is not additional searchable paragraph text evidence.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP3_TAIL_EMBEDDED_ASSET_CONTRACT_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Decompressed body bytes:", len(body))
    print("Paragraph consumed bytes:", consumed)
    print("Tail bytes:", len(tail))
    print("Prefix u32:", prefix_u32)
    print("Filename candidate:", filename)
    print("First image signature:", first_sig)
    print("Filename before first magic:", filename_before_first_magic)
    print("Image signatures:", signatures)
    print("Multiple image signatures:", multiple_image_signatures)
    print("Embedded asset contract confirmed:", asset_contract)
    print("Prior paragraph-like candidates are binary false positives:", output["prior_paragraph_like_candidates_reinterpreted_as_binary_false_positives"])
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["ocr_executed"], output["bulk_archive_traversal_executed"], output["verified_positive"],
        output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"],
        output["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior tail forensics exists": T28S113.exists(),
        "sample exists": path.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "paragraph boundary reproduced": consumed == int(prior_tail.get("prior_consumed_bytes") or -1),
        "embedded filename recovered": bool(filename),
        "image magic recovered": bool(first_sig),
        "filename precedes nearby image magic": filename_before_first_magic,
        "embedded asset contract confirmed": asset_contract,
        "paragraph-like false positives reclassified": output["prior_paragraph_like_candidates_reinterpreted_as_binary_false_positives"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP3 tail embedded asset contract validation failed")


if __name__ == "__main__":
    main()
