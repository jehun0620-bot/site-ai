# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-9
Development Density Management Area
Municipal Gazette HWP5 Distribution Stream Forensics

Offline-only forensic pass over the MIDPOINT HWP5 sample previously persisted by
T-28-S1-7 and structurally confirmed by T-28-S1-8.

Goals
-----
- confirm whether a distribution document uses ViewText/Section* streams
- enumerate BodyText and ViewText streams separately
- inspect the first record header of each ViewText section without decrypting it
- verify the expected HWPTAG_DISTRIBUTE_DOC_DATA-style 256-byte payload shape
- do NOT derive/decrypt distribution-document keys yet

No network, OCR, external converter, brute force, bulk traversal, or legal/SITE promotion.
"""
from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any, Dict, List

import olefile

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T28S18 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_format_structural_forensics.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_distribution_stream_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
EXPECTED_DISTRIBUTION_PAYLOAD_SIZE = 256


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_record_header(data: bytes) -> Dict[str, Any]:
    if len(data) < 4:
        return {"ok": False, "error": "stream shorter than 4-byte record header"}
    value = struct.unpack_from("<I", data, 0)[0]
    tag_id = value & 0x3FF
    level = (value >> 10) & 0x3FF
    size = (value >> 20) & 0xFFF
    header_bytes = 4
    if size == 0xFFF:
        if len(data) < 8:
            return {"ok": False, "error": "extended record header truncated", "tag_id": tag_id, "level": level}
        size = struct.unpack_from("<I", data, 4)[0]
        header_bytes = 8
    return {
        "ok": True,
        "raw_value": value,
        "tag_id": tag_id,
        "level": level,
        "size": size,
        "header_bytes": header_bytes,
        "payload_available": max(0, len(data) - header_bytes),
        "payload_fully_available": len(data) >= header_bytes + size,
        "payload_prefix_hex": data[header_bytes:header_bytes + min(size, 32)].hex(" "),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP5 DISTRIBUTION STREAM FORENSICS")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("Distribution decryption: DISABLED")
    print("Brute force: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T28S18.exists():
        raise FileNotFoundError(T28S18)
    prior = json.loads(T28S18.read_text(encoding="utf-8"))
    hwp5 = prior.get("hwp5") or {}
    path = Path(norm(hwp5.get("path")))
    if not path.exists():
        raise FileNotFoundError(path)

    header_flags = (hwp5.get("file_header") or {}).get("flags") or {}
    prior_distribution = bool(header_flags.get("distribution_document"))

    result: Dict[str, Any] = {
        "step": "STEP 17-21-C-16-8-T-28-S1-9 Municipal Gazette HWP5 Distribution Stream Forensics",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "input": str(T28S18),
        "sample_path": str(path),
        "prior_distribution_flag": prior_distribution,
        "streams": [],
        "bodytext_streams": [],
        "viewtext_streams": [],
        "viewtext_records": [],
        "distribution_decryption_executed": False,
        "brute_force_executed": False,
        "bulk_archive_traversal_executed": False,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }

    ole = olefile.OleFileIO(str(path))
    try:
        streams = ["/".join(parts) for parts in ole.listdir()]
        body = sorted(
            [s for s in streams if re.fullmatch(r"BodyText/Section\d+", s)],
            key=lambda x: int(re.search(r"Section(\d+)$", x).group(1)),
        )
        view = sorted(
            [s for s in streams if re.fullmatch(r"ViewText/Section\d+", s)],
            key=lambda x: int(re.search(r"Section(\d+)$", x).group(1)),
        )
        result["streams"] = streams
        result["bodytext_streams"] = body
        result["viewtext_streams"] = view

        for name in view:
            raw = ole.openstream(name).read()
            rec = parse_record_header(raw)
            rec.update({
                "stream": name,
                "stored_bytes": len(raw),
                "starts_with_record_header": bool(rec.get("ok")),
                "payload_size_matches_distribution_contract": bool(rec.get("ok") and rec.get("size") == EXPECTED_DISTRIBUTION_PAYLOAD_SIZE),
                "body_after_first_record_bytes": max(0, len(raw) - int(rec.get("header_bytes") or 0) - int(rec.get("size") or 0)) if rec.get("ok") else 0,
            })
            result["viewtext_records"].append(rec)
    finally:
        ole.close()

    has_viewtext = len(result["viewtext_streams"]) > 0
    all_distribution_shape = bool(result["viewtext_records"]) and all(
        r.get("payload_size_matches_distribution_contract") and r.get("payload_fully_available")
        for r in result["viewtext_records"]
    )

    if prior_distribution and has_viewtext and all_distribution_shape:
        classification = "HWP5_DISTRIBUTION_VIEWTEXT_CONTRACT_CONFIRMED"
    elif prior_distribution and has_viewtext:
        classification = "HWP5_DISTRIBUTION_VIEWTEXT_PRESENT_RECORD_SHAPE_NEEDS_REFINEMENT"
    elif prior_distribution:
        classification = "HWP5_DISTRIBUTION_FLAG_WITHOUT_VIEWTEXT_STREAMS"
    else:
        classification = "HWP5_SAMPLE_NOT_MARKED_DISTRIBUTION_DOCUMENT"

    result["classification"] = classification
    result["semantic_note"] = "ViewText structure is file-format evidence only. No UQQ700 body evidence or legal status is established."
    result["resolution"] = "MUNICIPAL_GAZETTE_HWP5_DISTRIBUTION_STREAM_FORENSICS_COMPLETED"
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Prior distribution flag:", prior_distribution)
    print("Total streams:", len(result["streams"]))
    print("BodyText streams:", result["bodytext_streams"])
    print("ViewText streams:", result["viewtext_streams"])
    print()
    print("VIEWTEXT RECORDS")
    for r in result["viewtext_records"]:
        print("-", r["stream"])
        print("  stored_bytes:", r["stored_bytes"])
        print("  tag_id:", r.get("tag_id"))
        print("  level:", r.get("level"))
        print("  size:", r.get("size"))
        print("  header_bytes:", r.get("header_bytes"))
        print("  payload_fully_available:", r.get("payload_fully_available"))
        print("  distribution_payload_size_match:", r.get("payload_size_matches_distribution_contract"))
        print("  body_after_first_record_bytes:", r.get("body_after_first_record_bytes"))
        print("  payload_prefix_hex:", r.get("payload_prefix_hex"))

    print()
    print("Classification:", classification)
    print("Resolution:", result["resolution"])
    print("Output:", OUT)

    unsafe = any([
        result["distribution_decryption_executed"],
        result["brute_force_executed"],
        result["bulk_archive_traversal_executed"],
        result["verified_positive"],
        result["runtime_registration_allowed"],
        result["site_positive_allowed"],
        result["site_negative_allowed"],
        result["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior HWP structural forensics exists": T28S18.exists(),
        "sample exists": path.exists(),
        "network request count zero": result["network_request_count"] == 0,
        "distribution flag confirmed from prior stage": prior_distribution,
        "ViewText stream recovered": has_viewtext,
        "ViewText record headers parseable": bool(result["viewtext_records"]) and all(r.get("ok") for r in result["viewtext_records"]),
        "256-byte distribution payload shape confirmed": all_distribution_shape,
        "decryption disabled": not result["distribution_decryption_executed"],
        "brute force disabled": not result["brute_force_executed"],
        "bulk archive traversal disabled": not result["bulk_archive_traversal_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP5 distribution stream forensics validation failed")


if __name__ == "__main__":
    main()
