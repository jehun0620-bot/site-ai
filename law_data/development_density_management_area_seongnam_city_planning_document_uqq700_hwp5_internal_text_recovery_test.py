# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import re
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
OUT_DIR = BASE / "law_data" / "output"
PRIOR_OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_technical_unknown_attachment_recovery.json"
OUT = OUT_DIR / "development_density_management_area_seongnam_city_planning_document_uqq700_hwp5_internal_text_recovery.json"

TARGET = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE"

EXACT_TERMS = ["개발밀도관리구역"]
VARIANT_TERMS = ["개발밀도 관리구역"]
WEAK_TERMS = ["개발밀도", "밀도관리구역"]

OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
HWP5_FILE_HEADER_SIGNATURE = b"HWP Document File"
HWPTAG_PARA_TEXT = 67


def curl_bytes(url: str) -> dict:
    exe = shutil.which("curl.exe") or shutil.which("curl")
    if not exe:
        return {"http": None, "body": b"", "stderr": "curl not found"}
    cmd = [
        exe, "-L", "-sS", "--connect-timeout", "15", "--max-time", "120",
        "-A", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
        "-H", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "-w", "\n__META__%{http_code}",
        url,
    ]
    p = subprocess.run(cmd, capture_output=True)
    raw = p.stdout or b""
    marker = b"\n__META__"
    if marker in raw:
        body, meta = raw.rsplit(marker, 1)
        http = meta.decode("utf-8", errors="replace").strip()
    else:
        body, http = raw, None
    return {
        "http": http,
        "body": body,
        "stderr": (p.stderr or b"").decode("utf-8", errors="replace").strip(),
    }


def scan_terms(text: str) -> dict:
    exact = [t for t in EXACT_TERMS if t in text]
    variant = [t for t in VARIANT_TERMS if t in text]
    weak = [t for t in WEAK_TERMS if t in text]
    if exact:
        status = "EXACT_CONTENT_HIT"
    elif variant:
        status = "VARIANT_CONTENT_HIT"
    elif weak:
        status = "WEAK_CONTENT_HIT"
    else:
        status = "CONTENT_NO_HIT"
    return {"status": status, "exact_terms": exact, "variant_terms": variant, "weak_terms": weak}


def clean_hwp_text(text: str) -> str:
    # HWP paragraph text can contain control characters and inline control payloads.
    # Keep ordinary Korean/ASCII/Unicode text and convert control separators to spaces.
    chars = []
    for ch in text:
        code = ord(ch)
        if ch in "\r\n\t":
            chars.append(" ")
        elif code >= 0x20 and code != 0x7F:
            chars.append(ch)
        else:
            chars.append(" ")
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def parse_record_stream(data: bytes) -> tuple[list[dict], str | None]:
    records = []
    pos = 0
    total = len(data)
    try:
        while pos + 4 <= total:
            header = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            tag_id = header & 0x3FF
            level = (header >> 10) & 0x3FF
            size = (header >> 20) & 0xFFF
            if size == 0xFFF:
                if pos + 4 > total:
                    return records, "TRUNCATED_EXTENDED_SIZE"
                size = struct.unpack_from("<I", data, pos)[0]
                pos += 4
            if size < 0 or pos + size > total:
                return records, f"TRUNCATED_RECORD_PAYLOAD_AT_{pos}_SIZE_{size}_TOTAL_{total}"
            payload = data[pos:pos + size]
            pos += size
            records.append({"tag_id": tag_id, "level": level, "size": size, "payload": payload})
        if pos != total and any(data[pos:]):
            return records, f"TRAILING_BYTES:{total-pos}"
        return records, None
    except Exception as e:
        return records, f"RECORD_PARSE_ERROR:{type(e).__name__}:{e}"


def extract_para_text(records: list[dict]) -> tuple[str, int, int]:
    chunks = []
    para_record_count = 0
    decode_error_count = 0
    for rec in records:
        if rec["tag_id"] != HWPTAG_PARA_TEXT:
            continue
        para_record_count += 1
        payload = rec["payload"]
        if len(payload) % 2:
            payload = payload[:-1]
        try:
            text = payload.decode("utf-16le", errors="strict")
        except UnicodeDecodeError:
            decode_error_count += 1
            text = payload.decode("utf-16le", errors="replace")
        cleaned = clean_hwp_text(text)
        if cleaned:
            chunks.append(cleaned)
    return "\n".join(chunks), para_record_count, decode_error_count


def main() -> None:
    print("=" * 78)
    print("SEONGNAM CITY PLANNING DOCUMENT UQQ700 HWP5 INTERNAL TEXT RECOVERY - S227G")
    print("=" * 78)
    print("Purpose: recover only verified OLE HWP attachments using olefile + HWP5 record parsing")
    print("Package auto-install: NOT EXECUTED")
    print("OCR: NOT EXECUTED")
    print("Recovered content hit/no-hit != designation/current validity/site inclusion/legal absence")
    print("UQQ700 final resolution: UNKNOWN")

    if not PRIOR_OUT.exists():
        raise FileNotFoundError(f"Required S227F output not found: {PRIOR_OUT}")
    prior = json.loads(PRIOR_OUT.read_text(encoding="utf-8"))
    targets = [r for r in (prior.get("results") or []) if r.get("extension") == "hwp" and r.get("signature") == "OLE_HWP"]

    try:
        import olefile
        olefile_available = True
    except Exception as e:
        olefile_available = False
        ole_import_error = f"{type(e).__name__}: {e}"

    results = []
    recovered = 0
    remaining = 0
    exact_hits = variant_hits = weak_hits = no_hits = 0

    for idx, row in enumerate(targets, 1):
        rec = {
            "pstSn": row.get("pstSn"), "fileNo": row.get("fileNo"), "name": row.get("name"),
            "download_url": row.get("download_url"), "http": None, "body_size": 0,
            "ole_signature_verified": False, "file_header_verified": False,
            "version_raw": None, "flags_raw": None, "compressed": None,
            "stream_count": 0, "bodytext_streams": [], "section_results": [],
            "para_text_record_count": 0, "decode_error_count": 0, "extracted_text_length": 0,
            "status": "TECHNICAL_UNKNOWN", "error": None,
            "exact_terms": [], "variant_terms": [], "weak_terms": [],
        }

        dl = curl_bytes(row.get("download_url") or "")
        body = dl.get("body") or b""
        rec["http"] = dl.get("http")
        rec["body_size"] = len(body)

        if dl.get("http") != "200" or not body.startswith(OLE_MAGIC):
            rec["error"] = f"DOWNLOAD_OR_OLE_SIGNATURE_FAILED:{dl.get('http')}:{dl.get('stderr')}"
            remaining += 1
            results.append(rec)
            continue
        rec["ole_signature_verified"] = True

        if not olefile_available:
            rec["error"] = f"OLEFILE_NOT_AVAILABLE:{ole_import_error}"
            remaining += 1
            results.append(rec)
            continue

        try:
            ole = olefile.OleFileIO(io.BytesIO(body))
            streams = ole.listdir(streams=True, storages=False)
            rec["stream_count"] = len(streams)
            stream_names = ["/".join(parts) for parts in streams]
            rec["bodytext_streams"] = sorted([s for s in stream_names if s.startswith("BodyText/Section")])

            if not ole.exists("FileHeader"):
                rec["error"] = "FILEHEADER_STREAM_MISSING"
                remaining += 1
                ole.close()
                results.append(rec)
                continue

            fh = ole.openstream("FileHeader").read()
            if not fh.startswith(HWP5_FILE_HEADER_SIGNATURE):
                rec["error"] = "HWP5_FILEHEADER_SIGNATURE_MISMATCH"
                remaining += 1
                ole.close()
                results.append(rec)
                continue
            rec["file_header_verified"] = True
            if len(fh) >= 40:
                version_bytes = fh[32:36]
                flags = struct.unpack_from("<I", fh, 36)[0]
                rec["version_raw"] = list(version_bytes)
                rec["flags_raw"] = flags
                rec["compressed"] = bool(flags & 0x01)
            else:
                rec["error"] = "FILEHEADER_TOO_SHORT"
                remaining += 1
                ole.close()
                results.append(rec)
                continue

            if not rec["bodytext_streams"]:
                rec["error"] = "BODYTEXT_SECTION_STREAM_MISSING"
                remaining += 1
                ole.close()
                results.append(rec)
                continue

            text_chunks = []
            fatal_section_error = False
            for stream_name in rec["bodytext_streams"]:
                raw = ole.openstream(stream_name).read()
                section = {"stream": stream_name, "raw_size": len(raw), "decoded_size": None, "record_count": 0, "record_parse_error": None, "para_text_record_count": 0, "decode_error_count": 0}
                decoded = raw
                if rec["compressed"]:
                    try:
                        decoded = zlib.decompress(raw, -15)
                    except Exception as e:
                        section["record_parse_error"] = f"DEFLATE_ERROR:{type(e).__name__}:{e}"
                        rec["section_results"].append(section)
                        fatal_section_error = True
                        continue
                section["decoded_size"] = len(decoded)
                records, parse_error = parse_record_stream(decoded)
                section["record_count"] = len(records)
                section["record_parse_error"] = parse_error
                text, para_count, decode_errors = extract_para_text(records)
                section["para_text_record_count"] = para_count
                section["decode_error_count"] = decode_errors
                rec["para_text_record_count"] += para_count
                rec["decode_error_count"] += decode_errors
                if text:
                    text_chunks.append(text)
                rec["section_results"].append(section)
                if parse_error:
                    fatal_section_error = True

            ole.close()
            full_text = "\n".join(text_chunks)
            rec["extracted_text_length"] = len(full_text)
            if fatal_section_error or rec["para_text_record_count"] == 0 or not full_text.strip():
                rec["error"] = "INCOMPLETE_HWP5_RECORD_OR_TEXT_RECOVERY"
                remaining += 1
            else:
                rec.update(scan_terms(full_text))
                recovered += 1
                if rec["status"] == "EXACT_CONTENT_HIT": exact_hits += 1
                elif rec["status"] == "VARIANT_CONTENT_HIT": variant_hits += 1
                elif rec["status"] == "WEAK_CONTENT_HIT": weak_hits += 1
                elif rec["status"] == "CONTENT_NO_HIT": no_hits += 1
        except Exception as e:
            rec["error"] = f"OLE_HWP_RECOVERY_ERROR:{type(e).__name__}:{e}"
            remaining += 1

        results.append(rec)
        print(f"HWP RECOVERY PROGRESS: {idx}/{len(targets)} | PSTSN={rec['pstSn']} | FILENO={rec['fileNo']} | COMPRESSED={rec['compressed']} | PARA={rec['para_text_record_count']} | STATUS={rec['status']}")

    if exact_hits or variant_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_RECOVERY_UQQ700_CANDIDATE_HIT"
        semantic = "RECOVERED_HWP5_CONTENT_CONTAINS_EXACT_OR_VARIANT_UQQ700_TERM_REQUIRING_CONTEXT_AND_OFFICIAL_NOTICE_TRACE"
        next_action = "REVIEW_ONLY_RECOVERED_HWP5_EXACT_OR_VARIANT_HITS_NON_PROMOTIONALLY_AND_TRACE_LITERAL_NOTICE_IDENTITY_IF_PRESENT"
    elif weak_hits:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_RECOVERY_WEAK_HIT"
        semantic = "RECOVERED_HWP5_CONTENT_CONTAINS_WEAK_DENSITY_TERM_WITHOUT_DESIGNATION_PROMOTION"
        next_action = "REVIEW_RECOVERED_HWP5_WEAK_CONTEXT_NON_PROMOTIONALLY_THEN_RETURN_TO_REMAINING_PDF_404_HARDENING"
    elif remaining == 0:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_INTERNAL_TEXT_RECOVERY_COMPLETE_NO_UQQ700_HIT"
        semantic = "ALL_VERIFIED_OLE_HWP_ATTACHMENTS_RECOVERED_BY_INTERNAL_HWP5_RECORD_PARSING_WITH_NO_UQQ700_TERM"
        next_action = "HARDEN_ONLY_REMAINING_LEGACY_PDF_404_ATTACHMENTS_WITHOUT_LEGAL_ABSENCE_INFERENCE"
    else:
        classification = "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_INTERNAL_TEXT_RECOVERY_TECHNICAL_UNKNOWN"
        semantic = "ONE_OR_MORE_VERIFIED_OLE_HWP_ATTACHMENTS_REMAIN_TECHNICALLY_UNRESOLVED_AFTER_INTERNAL_HWP5_PARSING"
        next_action = "HARDEN_ONLY_UNRESOLVED_HWP5_RECORD_OR_COMPRESSION_STRUCTURE_WITHOUT_NEGATIVE_INFERENCE"

    out = {
        "step": "STEP 17-21-C-16-8-T-153-S227G",
        "target_name": TARGET,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "prior_input_exists": PRIOR_OUT.exists(),
        "olefile_available": olefile_available,
        "target_hwp_count": len(targets),
        "recovered_hwp_count": recovered,
        "remaining_hwp_technical_unknown_count": remaining,
        "exact_content_hit_count": exact_hits,
        "variant_content_hit_count": variant_hits,
        "weak_content_hit_count": weak_hits,
        "content_no_hit_count": no_hits,
        "results": results,
        "classification": classification,
        "summary": {
            "semantic_state": semantic,
            "next_action": next_action,
            "hwp_recovery_hit_equals_designation_notice": False,
            "hwp_recovery_hit_equals_current_validity": False,
            "hwp_recovery_hit_equals_site_inclusion": False,
            "hwp_recovery_no_hit_equals_legal_absence": False,
            "remaining_hwp_unknown_equals_legal_absence": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "official_designation_identity_verified": False,
            "current_validity_verified": False,
            "site_spatial_inclusion_verified": False,
            "runtime_registration_allowed": False,
            "uqq700_final_resolution": "UNKNOWN",
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\nHWP5 INTERNAL TEXT RECOVERY SUMMARY")
    print("-" * 78)
    print(f"OLEFILE AVAILABLE: {olefile_available}")
    print(f"TARGET HWP COUNT: {len(targets)}")
    print(f"RECOVERED HWP COUNT: {recovered}")
    print(f"REMAINING HWP TECHNICAL UNKNOWN COUNT: {remaining}")
    print(f"EXACT CONTENT HIT COUNT: {exact_hits}")
    print(f"VARIANT CONTENT HIT COUNT: {variant_hits}")
    print(f"WEAK CONTENT HIT COUNT: {weak_hits}")
    print(f"CONTENT NO HIT COUNT: {no_hits}")

    print("\nDETAILS")
    print("-" * 78)
    for r in results:
        print(f"PSTSN={r['pstSn']} FILENO={r['fileNo']} NAME={r['name']} HTTP={r['http']} STATUS={r['status']}")
        print(f"  FILEHEADER={r['file_header_verified']} VERSION={r['version_raw']} FLAGS={r['flags_raw']} COMPRESSED={r['compressed']}")
        print(f"  STREAMS={r['stream_count']} BODYTEXT={r['bodytext_streams']} PARA_TEXT_RECORDS={r['para_text_record_count']} TEXT_LEN={r['extracted_text_length']}")
        print(f"  DECODE_ERRORS={r['decode_error_count']} ERROR={r['error']}")
        for s in r["section_results"]:
            print(f"    {s}")

    print("\n" + "=" * 78)
    print("RESOLUTION")
    print("=" * 78)
    print(f"CLASSIFICATION: {classification}")
    print(f"Semantic: {semantic}")
    print(f"Next action: {next_action}")
    print("HWP recovery hit == designation/current validity/site inclusion: False")
    print("HWP recovery no-hit == legal absence: False")
    print("Remaining HWP unknown == legal absence: False")
    print("SITE FALSE inference allowed: False")
    print("Runtime registration allowed: False")
    print("UQQ700 final resolution: UNKNOWN")

    validation = {
        "target name": out["target_name"] == TARGET,
        "standard code": out["standard_code"] == STANDARD_CODE,
        "resolution type hybrid spatial notice": out["resolution_type"] == RESOLUTION_TYPE,
        "S227F input exists": PRIOR_OUT.exists(),
        "verified OLE HWP targets present": len(targets) > 0,
        "olefile available": olefile_available,
        "HWP hit not designation": out["summary"]["hwp_recovery_hit_equals_designation_notice"] is False,
        "HWP hit not validity": out["summary"]["hwp_recovery_hit_equals_current_validity"] is False,
        "HWP hit not site inclusion": out["summary"]["hwp_recovery_hit_equals_site_inclusion"] is False,
        "HWP no-hit not legal absence": out["summary"]["hwp_recovery_no_hit_equals_legal_absence"] is False,
        "remaining HWP unknown not legal absence": out["summary"]["remaining_hwp_unknown_equals_legal_absence"] is False,
        "negative evidence disabled": out["summary"]["negative_evidence_allowed"] is False,
        "legal absence inference disabled": out["summary"]["legal_absence_inference_allowed"] is False,
        "SITE FALSE inference disabled": out["summary"]["site_false_inference_allowed"] is False,
        "designation identity not promoted": out["summary"]["official_designation_identity_verified"] is False,
        "current validity not promoted": out["summary"]["current_validity_verified"] is False,
        "site inclusion not promoted": out["summary"]["site_spatial_inclusion_verified"] is False,
        "runtime registration blocked": out["summary"]["runtime_registration_allowed"] is False,
        "UQQ700 remains UNKNOWN": out["summary"]["uqq700_final_resolution"] == "UNKNOWN",
        "classification emitted": classification in {
            "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_RECOVERY_UQQ700_CANDIDATE_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_RECOVERY_WEAK_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_INTERNAL_TEXT_RECOVERY_COMPLETE_NO_UQQ700_HIT",
            "SEONGNAM_CITY_PLANNING_DOCUMENT_HWP5_INTERNAL_TEXT_RECOVERY_TECHNICAL_UNKNOWN",
        },
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }
    print("\n" + "=" * 78)
    print("VALIDATION")
    print("=" * 78)
    for k, v in validation.items():
        print(f"{k}: {v}")
    print(f"all_pass: {all(validation.values())}")
    print(f"Output: {OUT}")
    if not all(validation.values()):
        raise AssertionError("S227G validation failed")


if __name__ == "__main__":
    main()
