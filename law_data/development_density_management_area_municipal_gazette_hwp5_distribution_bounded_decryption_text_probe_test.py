# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-10
Development Density Management Area
Municipal Gazette HWP5 Distribution Bounded Decryption Text Probe

Offline-only decryption of exactly ONE previously validated distribution ViewText stream
from the MIDPOINT 2014 municipal gazette HWP sample.

Pipeline:
1. Read ViewText/Section0.
2. Parse first HWP record (expected tag 28, payload 256 bytes).
3. Undo distribution-data XOR obfuscation with MSVC-compatible rand sequence.
4. Recover 16-byte AES key from decoded distribution data.
5. AES-128-ECB decrypt remaining section bytes.
6. raw-DEFLATE decompress decrypted bytes.
7. Parse HWP record headers and extract text only from PARA_TEXT (tag 67) payloads.

This is a single-document technical validation. No archive traversal, no brute force,
no password guessing, no OCR, and no legal/SITE promotion. Term absence => UNKNOWN.
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from pathlib import Path
from typing import Any, Dict, List, Tuple

import olefile
from Crypto.Cipher import AES

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T28S19 = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_distribution_stream_forensics.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_distribution_bounded_decryption_text_probe.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
STREAM = "ViewText/Section0"
EXPECTED_DISTRIBUTE_TAG = 28
EXPECTED_DISTRIBUTE_SIZE = 256
PARA_TEXT_TAG = 67
DIRECT = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED = ["개발밀도", "밀도관리", "관리구역"]


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_record_header(data: bytes, offset: int) -> Tuple[Dict[str, Any], int]:
    if offset + 4 > len(data):
        raise ValueError("truncated record header")
    value = struct.unpack_from("<I", data, offset)[0]
    tag_id = value & 0x3FF
    level = (value >> 10) & 0x3FF
    size = (value >> 20) & 0xFFF
    header_bytes = 4
    if size == 0xFFF:
        if offset + 8 > len(data):
            raise ValueError("truncated extended record header")
        size = struct.unpack_from("<I", data, offset + 4)[0]
        header_bytes = 8
    payload_offset = offset + header_bytes
    end = payload_offset + size
    if end > len(data):
        raise ValueError("record payload exceeds stream")
    return {
        "tag_id": tag_id,
        "level": level,
        "size": size,
        "header_bytes": header_bytes,
        "offset": offset,
        "payload_offset": payload_offset,
        "end": end,
    }, end


def msvc_rand_step(seed: int) -> Tuple[int, int]:
    seed = (seed * 214013 + 2531011) & 0xFFFFFFFF
    value = (seed >> 16) & 0x7FFF
    return seed, value


def decode_distribution_payload(payload: bytes) -> Dict[str, Any]:
    if len(payload) != EXPECTED_DISTRIBUTE_SIZE:
        raise ValueError("distribution payload must be exactly 256 bytes")
    buf = bytearray(payload)
    seed = struct.unpack_from("<I", buf, 0)[0]
    state = seed
    n = 0
    key_byte = 0
    for i in range(256):
        if n == 0:
            state, r1 = msvc_rand_step(state)
            state, r2 = msvc_rand_step(state)
            key_byte = r1 & 0xFF
            n = (r2 & 0x0F) + 1
        if i >= 4:
            buf[i] ^= key_byte
        n -= 1
    key_offset = 4 + (buf[0] & 0x0F)
    aes_key = bytes(buf[key_offset:key_offset + 16])
    hash_region = bytes(buf[key_offset:key_offset + 80])
    try:
        hash_text = hash_region.decode("utf-16le", errors="replace").rstrip("\x00")
    except Exception:
        hash_text = ""
    return {
        "seed": seed,
        "decoded_prefix_hex": bytes(buf[:64]).hex(" "),
        "key_offset": key_offset,
        "aes_key_hex": aes_key.hex(),
        "aes_key_bytes": aes_key,
        "sha1_text_candidate": hash_text,
        "sha1_text_candidate_hexlike": bool(re.fullmatch(r"[0-9A-Fa-f]{40}", hash_text[:40] or "")),
    }


def decrypt_body(ciphertext: bytes, key: bytes) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "ciphertext_bytes": len(ciphertext),
        "block_aligned": len(ciphertext) % 16 == 0,
        "aes_decrypt_ok": False,
        "decrypted_bytes": 0,
        "raw_deflate_ok": False,
        "plain_bytes": 0,
        "error": "",
    }
    if len(key) != 16:
        out["error"] = "AES key is not 16 bytes"
        return out
    if len(ciphertext) % 16:
        out["error"] = "ciphertext is not AES block aligned"
        return out
    try:
        decrypted = AES.new(key, AES.MODE_ECB).decrypt(ciphertext)
        out["aes_decrypt_ok"] = True
        out["decrypted_bytes"] = len(decrypted)
        out["decrypted_prefix_hex"] = decrypted[:64].hex(" ")
        plain = zlib.decompress(decrypted, -zlib.MAX_WBITS)
        out["raw_deflate_ok"] = True
        out["plain_bytes"] = len(plain)
        out["plain_prefix_hex"] = plain[:64].hex(" ")
        out["plain"] = plain
    except Exception as exc:
        out["error"] = repr(exc)
    return out


def sanitize_para_text(payload: bytes) -> str:
    if len(payload) % 2:
        payload = payload[:-1]
    try:
        text = payload.decode("utf-16le", errors="ignore")
    except Exception:
        return ""
    chars: List[str] = []
    for ch in text:
        code = ord(ch)
        if ch in "\r\n\t":
            chars.append(" ")
        elif code >= 0x20 and code not in range(0x7F, 0xA0):
            chars.append(ch)
        else:
            chars.append(" ")
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def parse_records_and_text(data: bytes) -> Dict[str, Any]:
    offset = 0
    records: List[Dict[str, Any]] = []
    paragraphs: List[str] = []
    tag_counts: Dict[str, int] = {}
    error = ""
    while offset < len(data):
        try:
            rec, next_offset = parse_record_header(data, offset)
        except Exception as exc:
            error = repr(exc)
            break
        payload = data[rec["payload_offset"]:rec["end"]]
        tag_counts[str(rec["tag_id"])] = tag_counts.get(str(rec["tag_id"]), 0) + 1
        summary = {k: rec[k] for k in ["tag_id", "level", "size", "offset", "header_bytes"]}
        if rec["tag_id"] == PARA_TEXT_TAG:
            text = sanitize_para_text(payload)
            summary["text_chars"] = len(text)
            summary["text_preview"] = text[:300]
            if text:
                paragraphs.append(text)
        records.append(summary)
        offset = next_offset
        if len(records) > 100000:
            error = "record safety limit exceeded"
            break
    merged = "\n".join(paragraphs)
    return {
        "record_count": len(records),
        "consumed_bytes": offset,
        "fully_consumed": offset == len(data),
        "parse_error": error,
        "tag_counts": tag_counts,
        "para_text_record_count": int(tag_counts.get(str(PARA_TEXT_TAG), 0)),
        "paragraph_count": len(paragraphs),
        "text_chars": len(merged),
        "hangul_chars": len(re.findall(r"[가-힣]", merged)),
        "direct_matches": {t: merged.count(t) for t in DIRECT},
        "related_matches": {t: merged.count(t) for t in RELATED},
        "text_preview": merged[:1500],
        "records_preview": records[:30],
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP5 DISTRIBUTION BOUNDED DECRYPTION TEXT PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("Distribution streams decrypted: 1")
    print("Password guessing: DISABLED")
    print("Brute force: DISABLED")
    print("Bulk archive traversal: DISABLED")
    print()

    if not T28S19.exists():
        raise FileNotFoundError(T28S19)
    prior = json.loads(T28S19.read_text(encoding="utf-8"))
    if prior.get("classification") != "HWP5_DISTRIBUTION_VIEWTEXT_CONTRACT_CONFIRMED":
        raise AssertionError("prior ViewText contract not validated")
    path = Path(norm(prior.get("sample_path")))
    if not path.exists():
        raise FileNotFoundError(path)

    ole = olefile.OleFileIO(str(path))
    try:
        raw = ole.openstream(STREAM).read()
    finally:
        ole.close()

    first, body_offset = parse_record_header(raw, 0)
    if first["tag_id"] != EXPECTED_DISTRIBUTE_TAG or first["size"] != EXPECTED_DISTRIBUTE_SIZE:
        raise AssertionError("unexpected distribution record contract")
    payload = raw[first["payload_offset"]:first["end"]]
    decoded = decode_distribution_payload(payload)
    key = decoded.pop("aes_key_bytes")
    ciphertext = raw[body_offset:]
    crypto = decrypt_body(ciphertext, key)
    plain = crypto.pop("plain", b"")
    parsed = parse_records_and_text(plain) if plain else {
        "record_count": 0, "fully_consumed": False, "parse_error": "no plaintext", "tag_counts": {},
        "para_text_record_count": 0, "paragraph_count": 0, "text_chars": 0, "hangul_chars": 0,
        "direct_matches": {t: 0 for t in DIRECT}, "related_matches": {t: 0 for t in RELATED}, "text_preview": "", "records_preview": []
    }

    technical_success = bool(
        crypto.get("aes_decrypt_ok")
        and crypto.get("raw_deflate_ok")
        and parsed.get("record_count", 0) > 0
        and parsed.get("para_text_record_count", 0) > 0
        and parsed.get("text_chars", 0) > 0
        and parsed.get("hangul_chars", 0) > 0
    )
    if technical_success and any(parsed["direct_matches"].values()):
        classification = "HWP5_DISTRIBUTION_TEXT_DECRYPTED_DIRECT_UQQ700_TERM_FOUND"
    elif technical_success and any(parsed["related_matches"].values()):
        classification = "HWP5_DISTRIBUTION_TEXT_DECRYPTED_RELATED_TERM_FOUND"
    elif technical_success:
        classification = "HWP5_DISTRIBUTION_TEXT_DECRYPTION_VALIDATED_NO_UQQ700_TERM_IN_SAMPLE"
    else:
        classification = "HWP5_DISTRIBUTION_TEXT_DECRYPTION_NOT_VALIDATED"

    output = {
        "step": "STEP 17-21-C-16-8-T-28-S1-10 Municipal Gazette HWP5 Distribution Bounded Decryption Text Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "network_request_count": 0,
        "sample_path": str(path),
        "stream": STREAM,
        "distribution_record": first,
        "distribution_payload_decoded": decoded,
        "crypto": crypto,
        "text_parse": parsed,
        "technical_success": technical_success,
        "classification": classification,
        "password_guessing_executed": False,
        "brute_force_executed": False,
        "bulk_archive_traversal_executed": False,
        "semantic_note": "This validates text recovery on one 2014 gazette sample only. No-match is not historical negative evidence and cannot produce UQQ700 FALSE.",
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWP5_DISTRIBUTION_BOUNDED_DECRYPTION_TEXT_PROBE_COMPLETED",
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Sample:", path)
    print("Stream:", STREAM)
    print("Stored stream bytes:", len(raw))
    print("Distribution tag/size:", first["tag_id"], first["size"])
    print("Key offset:", decoded["key_offset"])
    print("SHA1 text candidate:", repr(decoded["sha1_text_candidate"][:80]))
    print("SHA1 text candidate hexlike:", decoded["sha1_text_candidate_hexlike"])
    print("Ciphertext bytes:", crypto["ciphertext_bytes"])
    print("AES block aligned:", crypto["block_aligned"])
    print("AES decrypt OK:", crypto["aes_decrypt_ok"])
    print("Raw deflate OK:", crypto["raw_deflate_ok"])
    print("Plain bytes:", crypto["plain_bytes"])
    print("Record count:", parsed["record_count"])
    print("Fully consumed:", parsed.get("fully_consumed"))
    print("Parse error:", parsed.get("parse_error"))
    print("PARA_TEXT records:", parsed["para_text_record_count"])
    print("Text chars:", parsed["text_chars"])
    print("Hangul chars:", parsed["hangul_chars"])
    print("Direct matches:", parsed["direct_matches"])
    print("Related matches:", parsed["related_matches"])
    print("Text preview:", repr(parsed["text_preview"][:800]))
    print("Classification:", classification)
    print("Resolution:", output["resolution"])
    print("Output:", OUT)

    unsafe = any([
        output["password_guessing_executed"], output["brute_force_executed"], output["bulk_archive_traversal_executed"],
        output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"],
        output["site_negative_allowed"], output["final_positive_promotion_allowed"],
    ])
    vals = {
        "prior ViewText contract exists": T28S19.exists(),
        "sample exists": path.exists(),
        "network request count zero": output["network_request_count"] == 0,
        "single distribution stream only": output["stream"] == STREAM,
        "distribution record contract confirmed": first["tag_id"] == 28 and first["size"] == 256,
        "AES ciphertext block aligned": crypto["block_aligned"],
        "AES decrypt succeeds": crypto["aes_decrypt_ok"],
        "raw deflate succeeds": crypto["raw_deflate_ok"],
        "HWP records recovered": parsed["record_count"] > 0,
        "PARA_TEXT recovered": parsed["para_text_record_count"] > 0,
        "searchable Hangul text recovered": parsed["hangul_chars"] > 0,
        "password guessing disabled": not output["password_guessing_executed"],
        "brute force disabled": not output["brute_force_executed"],
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
        raise AssertionError("HWP5 distribution bounded decryption text probe failed")


if __name__ == "__main__":
    main()
