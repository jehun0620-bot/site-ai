# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-11
Development Density Management Area
Municipal Gazette HWP3 Compressed Stream Boundary Probe

Offline-only validation of the compressed-stream boundary in the persisted EARLIEST
(2003) HWP 3.0 municipal gazette sample.

The HWP 3.0 format stores the fixed 30-byte signature, 128-byte document info,
1008-byte document summary, optional info block #0, then (when compression is enabled)
a single raw-DEFLATE stream containing font names, styles, paragraph list, and
additional info block #1. Additional info block #2 may follow outside that stream.

This stage only validates the compressed boundary and decompression mechanics.
It does not yet parse HWP3 font/style/paragraph semantics or promote legal status.
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
T28S18 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp_format_structural_forensics.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp3_compressed_stream_boundary_probe.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
FIXED_PREFIX = 30 + 128 + 1008


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def printable_scan(data: bytes) -> Dict[str, Any]:
    ascii_runs = [m.group(0).decode("latin1", errors="ignore") for m in re.finditer(rb"[ -~]{4,}", data)]
    cp949_candidates: List[str] = []
    # Bounded diagnostics only: decode chunks split around NUL/control-heavy regions.
    for chunk in re.split(rb"[\x00-\x08\x0b\x0c\x0e-\x1f]{2,}", data[: min(len(data), 2_000_000)]):
        if len(chunk) < 4:
            continue
        try:
            text = chunk.decode("cp949")
        except Exception:
            continue
        if re.search(r"[가-힣]", text):
            cp949_candidates.append(re.sub(r"\s+", " ", text).strip())
            if len(cp949_candidates) >= 20:
                break
    joined = "\n".join(cp949_candidates)
    return {
        "ascii_run_count": len(ascii_runs),
        "ascii_preview": "\n".join(ascii_runs[:30])[:1500],
        "cp949_candidate_count": len(cp949_candidates),
        "cp949_hangul_chars": len(re.findall(r"[가-힣]", joined)),
        "cp949_preview": joined[:1500],
    }


def raw_deflate_probe(data: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "input_bytes": len(data),
        "ok": False,
        "eof": False,
        "plain_bytes": 0,
        "unused_data_bytes": 0,
        "unconsumed_tail_bytes": 0,
        "consumed_input_bytes": 0,
        "error": "",
    }
    try:
        dec = zlib.decompressobj(-zlib.MAX_WBITS)
        plain = dec.decompress(data)
        plain += dec.flush()
        out["ok"] = True
        out["eof"] = dec.eof
        out["plain_bytes"] = len(plain)
        out["unused_data_bytes"] = len(dec.unused_data)
        out["unconsumed_tail_bytes"] = len(dec.unconsumed_tail)
        out["consumed_input_bytes"] = len(data) - len(dec.unused_data) - len(dec.unconsumed_tail)
        out["plain_prefix_hex"] = plain[:64].hex(" ")
        out["plain_suffix_hex"] = plain[-64:].hex(" ") if plain else ""
        out["unused_data_prefix_hex"] = dec.unused_data[:64].hex(" ")
        out["plain"] = plain
        out["unused_data"] = dec.unused_data
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP3 COMPRESSED STREAM BOUNDARY PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("HWP3 semantic parser: DISABLED")
    print("OCR: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T28S18.exists():
        raise FileNotFoundError(T28S18)
    prior = json.loads(T28S18.read_text(encoding="utf-8"))
    hwp3_prior = prior.get("hwp3") or {}
    path = Path(norm(hwp3_prior.get("path")))
    if not path.exists():
        raise FileNotFoundError(path)

    data = path.read_bytes()
    if len(data) < FIXED_PREFIX:
        raise AssertionError("HWP3 sample shorter than fixed prefix")
    info_block_len = int(hwp3_prior.get("info_block_length") or 0)
    stream_offset = FIXED_PREFIX + info_block_len
    if stream_offset >= len(data):
        raise AssertionError("invalid HWP3 compressed stream offset")
    compression_flag = int(hwp3_prior.get("compression_flag") or 0)
    if compression_flag == 0:
        raise AssertionError("HWP3 sample is not marked compressed")

    compressed_region = data[stream_offset:]
    probe = raw_deflate_probe(compressed_region)
    plain = probe.pop("plain", b"")
    unused = probe.pop("unused_data", b"")
    diagnostics = printable_scan(plain) if plain else {
        "ascii_run_count": 0, "ascii_preview": "", "cp949_candidate_count": 0,
        "cp949_hangul_chars": 0, "cp949_preview": ""
    }

    technical_success = bool(probe.get("ok") and probe.get("eof") and probe.get("plain_bytes", 0) > 0)
    if technical_success and probe.get("unused_data_bytes", 0) > 0:
        classification = "HWP3_RAW_DEFLATE_STREAM_VALIDATED_WITH_TRAILING_UNCOMPRESSED_DATA"
    elif technical_success:
        classification = "HWP3_RAW_DEFLATE_STREAM_VALIDATED_NO_TRAILING_DATA"
    else:
        classification = "HWP3_RAW_DEFLATE_STREAM_NOT_VALIDATED"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-11 Municipal Gazette HWP3 Compressed Stream Boundary Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "sample_path": str(path),
        "sample_bytes": len(data),
        "hwp3_signature_confirmed_prior": bool(hwp3_prior.get("signature_ok")),
        "compression_flag": compression_flag,
        "info_block_length": info_block_len,
        "fixed_prefix_bytes": FIXED_PREFIX,
        "compressed_stream_offset": stream_offset,
        "compressed_region_bytes": len(compressed_region),
        "decompression": probe,
        "decompressed_diagnostics": diagnostics,
        "technical_success": technical_success,
        "classification": classification,
        "hwp3_semantic_parser_executed": False,
        "ocr_executed": False,
        "bulk_archive_traversal_executed": False,
        "semantic_note": "This validates HWP3 compressed-stream mechanics only. Diagnostic text absence is not UQQ700 negative evidence.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP3_COMPRESSED_STREAM_BOUNDARY_PROBE_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Sample bytes:", len(data))
    print("Compression flag:", compression_flag)
    print("Info block length:", info_block_len)
    print("Fixed prefix bytes:", FIXED_PREFIX)
    print("Compressed stream offset:", stream_offset)
    print("Compressed region bytes:", len(compressed_region))
    print("Raw deflate OK:", probe.get("ok"))
    print("DEFLATE EOF reached:", probe.get("eof"))
    print("Consumed compressed bytes:", probe.get("consumed_input_bytes"))
    print("Plain bytes:", probe.get("plain_bytes"))
    print("Unused trailing bytes:", probe.get("unused_data_bytes"))
    print("Unconsumed tail bytes:", probe.get("unconsumed_tail_bytes"))
    print("Plain prefix hex:", probe.get("plain_prefix_hex"))
    print("Unused prefix hex:", probe.get("unused_data_prefix_hex"))
    print("ASCII runs:", diagnostics["ascii_run_count"])
    print("CP949 candidate runs:", diagnostics["cp949_candidate_count"])
    print("CP949 Hangul chars:", diagnostics["cp949_hangul_chars"])
    print("CP949 preview:", repr(diagnostics["cp949_preview"][:700]))
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["hwp3_semantic_parser_executed"], output["ocr_executed"], output["bulk_archive_traversal_executed"],
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior HWP structural forensics exists": T28S18.exists(),
        "sample exists": path.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "HWP3 prior signature confirmed": output["hwp3_signature_confirmed_prior"],
        "compression flag enabled": compression_flag != 0,
        "compressed offset inside file": 0 < stream_offset < len(data),
        "raw deflate succeeds": bool(probe.get("ok")),
        "raw deflate reaches EOF": bool(probe.get("eof")),
        "decompressed payload recovered": int(probe.get("plain_bytes") or 0) > 0,
        "semantic parser disabled": not output["hwp3_semantic_parser_executed"],
        "OCR disabled": not output["ocr_executed"],
        "bulk archive traversal disabled": not output["bulk_archive_traversal_executed"],
        "unsafe promotion leakage zero": not unsafe,
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWP3 compressed stream boundary probe failed")


if __name__ == "__main__":
    main()
