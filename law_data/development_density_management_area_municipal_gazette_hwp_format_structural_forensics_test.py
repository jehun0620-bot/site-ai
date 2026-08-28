# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-8
Development Density Management Area
Municipal Gazette HWP Format Structural Forensics

Offline-only structural diagnostics for the TWO persisted HWP samples from T-28-S1-7.

EARLIEST sample:
- validate HWP 3.0 fixed 30-byte signature
- parse 128-byte document-info block at offset 30
- report compression flag (doc-info offset 124), sub-revision, info-block length
- no HWP3 body parser yet

MIDPOINT sample:
- validate OLE/CFB container
- enumerate streams with olefile
- parse HWP5 FileHeader signature/version/property flags
- inspect DocInfo and BodyText/Section* stream sizes and raw-deflate feasibility
- no record/body semantic extraction yet

No network, OCR, external converter, archive traversal, or legal/SITE promotion.
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
SAMPLE_DIR = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_samples"
T28S17 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_cross_era_bounded_extraction_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_format_structural_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
HWP3_SIGNATURE = b"HWP Document File V3.00 \x1a\x01\x02\x03\x04\x05"
OLE_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
HWP5_SIGNATURE_PREFIX = b"HWP Document File"


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def find_sample(doc: Dict[str, Any], role: str) -> Dict[str, Any]:
    s = next((x for x in doc.get("samples", []) if x.get("role") == role), None)
    if not s:
        raise AssertionError(f"missing role {role}")
    p = Path(norm(s.get("persisted_path")))
    if not p.exists():
        raise FileNotFoundError(p)
    return {**s, "path": p}


def parse_hwp3(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    if len(data) < 30 + 128:
        raise AssertionError("HWP3 sample too short")
    sig = data[:30]
    info = data[30:158]
    compression_flag = info[124]
    sub_revision = info[125]
    info_block_len = struct.unpack_from("<H", info, 126)[0]
    protected = struct.unpack_from("<I", info, 24)[0]
    external_doc_flags = struct.unpack_from("<H", info, 28)[0]
    compressed_region_offset_min = 30 + 128 + 1008 + info_block_len
    rec = {
        "path": str(path),
        "bytes": len(data),
        "signature_hex": sig.hex(" "),
        "signature_ok": sig == HWP3_SIGNATURE,
        "protected": protected,
        "external_doc_flags": external_doc_flags,
        "compression_flag": compression_flag,
        "compressed": compression_flag != 0,
        "sub_revision": sub_revision,
        "info_block_length": info_block_len,
        "fixed_prefix_bytes": 30 + 128 + 1008,
        "compressed_region_offset_min": compressed_region_offset_min,
        "body_parser_executed": False,
    }
    return rec


def try_raw_deflate(data: bytes) -> Dict[str, Any]:
    out = {"attempted": True, "ok": False, "output_bytes": 0, "prefix_hex": "", "error": ""}
    try:
        plain = zlib.decompress(data, -zlib.MAX_WBITS)
        out["ok"] = True
        out["output_bytes"] = len(plain)
        out["prefix_hex"] = plain[:32].hex(" ")
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def parse_hwp5(path: Path) -> Dict[str, Any]:
    try:
        import olefile  # type: ignore
    except Exception as exc:
        return {
            "path": str(path),
            "bytes": path.stat().st_size,
            "ole_signature_ok": path.read_bytes()[:8] == OLE_SIGNATURE,
            "olefile_available": False,
            "error": repr(exc),
        }

    data = path.read_bytes()
    rec: Dict[str, Any] = {
        "path": str(path),
        "bytes": len(data),
        "ole_signature_ok": data[:8] == OLE_SIGNATURE,
        "olefile_available": True,
        "ole_opened": False,
        "streams": [],
        "file_header": {},
        "docinfo": {},
        "body_sections": [],
    }
    try:
        ole = olefile.OleFileIO(str(path))
        rec["ole_opened"] = True
        streams = ["/".join(x) for x in ole.listdir()]
        rec["streams"] = streams

        fh = ole.openstream("FileHeader").read()
        sig = fh[:32].rstrip(b"\x00")
        version_raw = fh[32:36]
        props = struct.unpack_from("<I", fh, 36)[0] if len(fh) >= 40 else 0
        version = ".".join(str(x) for x in reversed(version_raw)) if len(version_raw) == 4 else ""
        flags = {
            "compressed": bool(props & (1 << 0)),
            "password_encrypted": bool(props & (1 << 1)),
            "distribution_document": bool(props & (1 << 2)),
            "script": bool(props & (1 << 3)),
            "drm": bool(props & (1 << 4)),
            "xml_template": bool(props & (1 << 5)),
            "history": bool(props & (1 << 6)),
            "cert_signed": bool(props & (1 << 7)),
            "cert_encrypted": bool(props & (1 << 8)),
            "cert_drm": bool(props & (1 << 9)),
            "ccl": bool(props & (1 << 10)),
        }
        rec["file_header"] = {
            "bytes": len(fh),
            "signature": sig.decode("latin1", errors="replace"),
            "signature_ok": sig.startswith(HWP5_SIGNATURE_PREFIX),
            "version_raw_hex": version_raw.hex(" "),
            "version": version,
            "property_flags_value": props,
            "flags": flags,
        }

        if ole.exists("DocInfo"):
            raw = ole.openstream("DocInfo").read()
            d = {"stored_bytes": len(raw), "raw_deflate": None}
            if flags["compressed"]:
                d["raw_deflate"] = try_raw_deflate(raw)
            rec["docinfo"] = d

        section_names = sorted(
            [s for s in streams if re.fullmatch(r"BodyText/Section\d+", s)],
            key=lambda x: int(re.search(r"Section(\d+)$", x).group(1)),
        )
        for name in section_names:
            raw = ole.openstream(name).read()
            srec = {"stream": name, "stored_bytes": len(raw), "raw_deflate": None}
            if flags["compressed"]:
                srec["raw_deflate"] = try_raw_deflate(raw)
            rec["body_sections"].append(srec)
        ole.close()
    except Exception as exc:
        rec["error"] = repr(exc)
    return rec


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP FORMAT STRUCTURAL FORENSICS")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("OCR: DISABLED")
    print("External converter: DISABLED")
    print("Body semantic parser: DISABLED")
    print()

    if not T28S17.exists():
        raise FileNotFoundError(T28S17)
    prior = json.loads(T28S17.read_text(encoding="utf-8"))
    earliest = find_sample(prior, "EARLIEST")
    midpoint = find_sample(prior, "MIDPOINT")

    hwp3 = parse_hwp3(earliest["path"])
    hwp5 = parse_hwp5(midpoint["path"])

    hwp5_structural = bool(
        hwp5.get("ole_signature_ok")
        and hwp5.get("olefile_available")
        and hwp5.get("ole_opened")
        and hwp5.get("file_header", {}).get("signature_ok")
        and len(hwp5.get("body_sections", [])) > 0
    )
    hwp5_deflate_ok = bool(
        hwp5_structural
        and (not hwp5["file_header"]["flags"].get("compressed") or all(
            bool(x.get("raw_deflate", {}).get("ok")) for x in hwp5.get("body_sections", [])
        ))
    )

    if hwp3["signature_ok"] and hwp5_structural and hwp5_deflate_ok:
        classification = "HWP3_AND_HWP5_FORMAT_CONTRACTS_STRUCTURALLY_CONFIRMED"
    elif hwp3["signature_ok"] and not hwp5.get("olefile_available"):
        classification = "HWP3_CONFIRMED_HWP5_DEPENDENCY_MISSING"
    elif hwp3["signature_ok"] and hwp5_structural:
        classification = "HWP3_AND_HWP5_CONTAINERS_CONFIRMED_HWP5_COMPRESSION_NEEDS_REFINEMENT"
    else:
        classification = "HWP_FORMAT_STRUCTURAL_CONTRACT_INCOMPLETE"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-8 Municipal Gazette HWP Format Structural Forensics",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "inputs": {"prior": str(T28S17)},
        "hwp3": hwp3,
        "hwp5": hwp5,
        "classification": classification,
        "semantic_note": "This establishes file-format handling only. No body-level UQQ700 evidence is produced.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP_FORMAT_STRUCTURAL_FORENSICS_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("HWP3")
    print("- Path:", hwp3["path"])
    print("- Bytes:", hwp3["bytes"])
    print("- Signature OK:", hwp3["signature_ok"])
    print("- Compression flag:", hwp3["compression_flag"])
    print("- Compressed:", hwp3["compressed"])
    print("- Sub revision:", hwp3["sub_revision"])
    print("- Info block length:", hwp3["info_block_length"])
    print("- Minimum compressed-region offset:", hwp3["compressed_region_offset_min"])
    print()

    print("HWP5")
    print("- Path:", hwp5["path"])
    print("- Bytes:", hwp5["bytes"])
    print("- OLE signature OK:", hwp5.get("ole_signature_ok"))
    print("- olefile available:", hwp5.get("olefile_available"))
    print("- OLE opened:", hwp5.get("ole_opened"))
    if hwp5.get("file_header"):
        print("- FileHeader signature:", hwp5["file_header"].get("signature"))
        print("- FileHeader signature OK:", hwp5["file_header"].get("signature_ok"))
        print("- Version:", hwp5["file_header"].get("version"))
        print("- Property flags:", hwp5["file_header"].get("flags"))
    print("- Stream count:", len(hwp5.get("streams", [])))
    print("- Body section count:", len(hwp5.get("body_sections", [])))
    for s in hwp5.get("body_sections", []):
        rd = s.get("raw_deflate") or {}
        print("  SECTION", s["stream"], "stored=", s["stored_bytes"], "deflate_ok=", rd.get("ok"), "plain=", rd.get("output_bytes"), "error=", rd.get("error", ""))
    if hwp5.get("error"):
        print("- Error:", hwp5["error"])

    print()
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"], hwp3["body_parser_executed"],
    ])
    vals = {
        "prior bounded HWP samples exist": T28S17.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "HWP3 sample signature confirmed": hwp3["signature_ok"],
        "HWP3 doc-info parsed": hwp3["compression_flag"] >= 0,
        "HWP5 OLE signature confirmed": bool(hwp5.get("ole_signature_ok")),
        "olefile dependency available": bool(hwp5.get("olefile_available")),
        "HWP5 OLE opened": bool(hwp5.get("ole_opened")),
        "HWP5 FileHeader signature confirmed": bool(hwp5.get("file_header", {}).get("signature_ok")),
        "HWP5 BodyText sections recovered": len(hwp5.get("body_sections", [])) > 0,
        "HWP5 compressed sections raw-deflate validated": hwp5_deflate_ok,
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP structural forensics validation failed")


if __name__ == "__main__":
    main()
