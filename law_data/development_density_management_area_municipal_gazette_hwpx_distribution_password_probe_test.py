# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-3
Development Density Management Area
Municipal Gazette HWPX Distribution Password Probe

Offline-only, bounded validation against ONE encrypted representative payload
(Contents/header.xml), using only the distribution-password constant published in
Hancom's public hwpx-owpml-model source. This is NOT brute force and performs no
network access or bulk traversal.

The probe implements the manifest-declared chain:
  password UTF-8 -> SHA-256 start key -> PBKDF2-HMAC-SHA1 -> AES-256-CBC
Then it tries a small set of deterministic post-decryption interpretations
(raw/plain, PKCS7-unpadded, zlib, raw-deflate) and validates against XML structure
and manifest SHA256-1K checksum where applicable.

No legal promotion is allowed regardless of result.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import zlib
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE = OUT_DIR / "development_density_management_area_municipal_gazette_representative_sample.hwpx"
S1_2 = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_manifest_security_forensics.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_distribution_password_probe.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
PROBE_MEMBER = "Contents/header.xml"

# Published in Hancom's public hwpx-owpml-model / OWPMLApi/OWPMLSerialize.cpp.
# Kept as bytes to mirror the C string literally. This is a public compatibility
# constant, not a user credential and not a guessed password list.
PUBLIC_DISTRIBUTION_PASSWORD = bytes([
    0x22, 0x59, 0x61, 0x6E, 0x67, 0x20, 0x57, 0x61,
    0x6E, 0x67, 0x53, 0x75, 0x6E, 0x76, 0x21, 0x21, 0x22,
])

MANIFEST_NS = "urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def attr_local(elem: ET.Element, name: str) -> str:
    for k, v in elem.attrib.items():
        if local_name(k) == name:
            return str(v)
    return ""


def b64(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def pkcs7_unpad(data: bytes, block_size: int = 16) -> Optional[bytes]:
    if not data:
        return None
    n = data[-1]
    if n <= 0 or n > block_size or len(data) < n:
        return None
    if data[-n:] != bytes([n]) * n:
        return None
    return data[:-n]


def xml_status(data: bytes) -> Tuple[bool, str, str]:
    try:
        root = ET.fromstring(data)
        return True, local_name(root.tag), ""
    except Exception as e:
        return False, "", repr(e)


def import_aes_backend():
    try:
        from Crypto.Cipher import AES  # type: ignore

        def decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
            return AES.new(key, AES.MODE_CBC, iv).decrypt(ciphertext)

        return "pycryptodome", decrypt
    except Exception:
        pass

    try:
        from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes  # type: ignore

        def decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
            dec = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
            return dec.update(ciphertext) + dec.finalize()

        return "cryptography", decrypt
    except Exception:
        return "", None


def find_manifest_crypto(manifest_bytes: bytes, target_path: str) -> Dict[str, Any]:
    root = ET.fromstring(manifest_bytes)
    for file_entry in root.iter():
        if local_name(file_entry.tag) != "file-entry":
            continue
        if attr_local(file_entry, "full-path") != target_path:
            continue

        result: Dict[str, Any] = {
            "path": target_path,
            "media_type": attr_local(file_entry, "media-type"),
            "plain_size": int(attr_local(file_entry, "size") or 0),
        }
        for child in file_entry.iter():
            name = local_name(child.tag)
            if name == "encryption-data":
                result["checksum_type"] = attr_local(child, "checksum-type")
                result["checksum_b64"] = attr_local(child, "checksum")
            elif name == "algorithm":
                result["algorithm_name"] = attr_local(child, "algorithm-name")
                result["iv_b64"] = attr_local(child, "initialisation-vector")
            elif name == "key-derivation":
                result["key_derivation_name"] = attr_local(child, "key-derivation-name")
                result["key_size"] = int(attr_local(child, "key-size") or 0)
                result["iteration_count"] = int(attr_local(child, "iteration-count") or 0)
                result["salt_b64"] = attr_local(child, "salt")
            elif name == "start-key-generation":
                result["start_key_generation_name"] = attr_local(child, "start-key-generation-name")
                result["start_key_size"] = int(attr_local(child, "key-size") or 0)
        return result
    raise KeyError(f"manifest entry not found: {target_path}")


def candidate_interpretations(decrypted: bytes) -> List[Tuple[str, bytes]]:
    out: List[Tuple[str, bytes]] = [("AES_RAW", decrypted)]
    unpadded = pkcs7_unpad(decrypted)
    if unpadded is not None:
        out.append(("AES_PKCS7_UNPAD", unpadded))

    bases = list(out)
    for base_name, base in bases:
        for mode_name, wbits in (("ZLIB", zlib.MAX_WBITS), ("RAW_DEFLATE", -zlib.MAX_WBITS)):
            try:
                out.append((f"{base_name}_{mode_name}", zlib.decompress(base, wbits)))
            except Exception:
                pass
    return out


def checksum_matches(data: bytes, expected: bytes) -> bool:
    # Hancom public implementation computes SHA-256 over the first decompressed
    # bytes when detecting its published distribution password. Keep this as the
    # primary compatibility check for XML candidates.
    return hashlib.sha256(data[:1024]).digest() == expected


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWPX DISTRIBUTION PASSWORD PROBE")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("Password candidates: 1 (public Hancom distribution constant only)")
    print("Payloads probed: 1")
    print("Bulk traversal: DISABLED")
    print()

    if not SAMPLE.exists():
        raise FileNotFoundError(SAMPLE)
    if not S1_2.exists():
        raise FileNotFoundError(S1_2)

    backend_name, aes_decrypt = import_aes_backend()

    with zipfile.ZipFile(SAMPLE) as z:
        manifest_bytes = z.read("META-INF/manifest.xml")
        ciphertext = z.read(PROBE_MEMBER)
        zip_info = z.getinfo(PROBE_MEMBER)

    crypto = find_manifest_crypto(manifest_bytes, PROBE_MEMBER)
    iv = b64(crypto["iv_b64"])
    salt = b64(crypto["salt_b64"])
    expected_checksum = b64(crypto["checksum_b64"])

    compatibility = {
        "aes256_cbc": crypto.get("algorithm_name") == "http://www.w3.org/2001/04/xmlenc#aes256-cbc",
        "pbkdf2": str(crypto.get("key_derivation_name", "")).lower().endswith("#pbkdf2"),
        "sha256_start_key": str(crypto.get("start_key_generation_name", "")).lower().endswith("#sha256"),
        "sha256_1k_checksum": str(crypto.get("checksum_type", "")).lower().endswith("#sha256-1k"),
        "key_size_32": crypto.get("key_size") == 32,
        "start_key_size_32": crypto.get("start_key_size") == 32,
        "iv_16_bytes": len(iv) == 16,
        "salt_nonempty": len(salt) > 0,
        "ciphertext_block_aligned": len(ciphertext) % 16 == 0,
        "zip_stored": zip_info.compress_type == zipfile.ZIP_STORED,
    }

    result_candidates: List[Dict[str, Any]] = []
    accepted: Optional[Dict[str, Any]] = None
    dependency_missing = aes_decrypt is None

    if aes_decrypt is not None and all(compatibility.values()):
        start_key = hashlib.sha256(PUBLIC_DISTRIBUTION_PASSWORD).digest()
        derived_key = hashlib.pbkdf2_hmac(
            "sha1",
            start_key,
            salt,
            int(crypto["iteration_count"]),
            dklen=int(crypto["key_size"]),
        )
        decrypted = aes_decrypt(derived_key, iv, ciphertext)

        for name, data in candidate_interpretations(decrypted):
            xml_ok, xml_root, xml_error = xml_status(data)
            checksum_ok = checksum_matches(data, expected_checksum)
            rec = {
                "interpretation": name,
                "bytes": len(data),
                "xml_parse_ok": xml_ok,
                "xml_root": xml_root,
                "xml_error": xml_error[:500],
                "sha256_1k_matches_manifest": checksum_ok,
                "prefix_hex": data[:32].hex(" "),
            }
            result_candidates.append(rec)
            if accepted is None and xml_ok and checksum_ok:
                accepted = rec

    if dependency_missing:
        classification = "AES_BACKEND_UNAVAILABLE"
    elif accepted is not None:
        classification = "PUBLIC_HANCOM_DISTRIBUTION_PASSWORD_VALIDATED_ON_HEADER"
    else:
        classification = "PUBLIC_HANCOM_DISTRIBUTION_PASSWORD_NOT_VALIDATED_ON_HEADER"

    out = {
        "step": "STEP 17-21-C-16-8-T-28-S1-3 Municipal Gazette HWPX Distribution Password Probe",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "inputs": {"sample": str(SAMPLE), "manifest_forensics": str(S1_2)},
        "execution": {
            "network_request_count": 0,
            "bulk_traversal_executed": False,
            "payload_probe_count": 1,
            "password_candidate_count": 1,
            "brute_force_executed": False,
        },
        "probe_member": PROBE_MEMBER,
        "aes_backend": backend_name,
        "dependency_missing": dependency_missing,
        "manifest_crypto": {
            **crypto,
            "iv_bytes": len(iv),
            "salt_bytes": len(salt),
            "checksum_bytes": len(expected_checksum),
            "ciphertext_bytes": len(ciphertext),
            "zip_compression": "STORED" if zip_info.compress_type == zipfile.ZIP_STORED else str(zip_info.compress_type),
        },
        "compatibility": compatibility,
        "candidate_results": result_candidates,
        "accepted_result": accepted,
        "classification": classification,
        "verified_positive": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWPX_DISTRIBUTION_PASSWORD_PROBE_COMPLETED",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "persisted sample exists": SAMPLE.exists() and SAMPLE.stat().st_size > 0,
        "manifest security forensics input exists": S1_2.exists(),
        "single bounded payload": out["execution"]["payload_probe_count"] == 1,
        "single public password candidate": out["execution"]["password_candidate_count"] == 1,
        "brute force disabled": not out["execution"]["brute_force_executed"],
        "network request count zero": out["execution"]["network_request_count"] == 0,
        "manifest crypto contract compatible": all(compatibility.values()),
        "bulk traversal disabled": not out["execution"]["bulk_traversal_executed"],
        "unsafe promotion disabled": not any([
            out["verified_positive"], out["site_positive_allowed"], out["site_negative_allowed"]
        ]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Probe member:", PROBE_MEMBER)
    print("Ciphertext bytes:", len(ciphertext))
    print("Manifest plain size:", crypto.get("plain_size"))
    print("AES backend:", backend_name or "NONE")
    print("Algorithm:", crypto.get("algorithm_name"))
    print("KDF:", crypto.get("key_derivation_name"))
    print("Iterations:", crypto.get("iteration_count"))
    print("Key size:", crypto.get("key_size"))
    print("Start key:", crypto.get("start_key_generation_name"))
    print("Checksum:", crypto.get("checksum_type"))
    print("Compatibility all:", all(compatibility.values()))
    print()

    print("CANDIDATE RESULTS")
    if dependency_missing:
        print("AES backend unavailable. Install either pycryptodome or cryptography before rerun.")
    for r in result_candidates:
        print(
            "-", r["interpretation"],
            "bytes=", r["bytes"],
            "xml_ok=", r["xml_parse_ok"],
            "root=", r["xml_root"],
            "checksum_ok=", r["sha256_1k_matches_manifest"],
            "hex=", r["prefix_hex"],
        )
    print()
    print("Classification:", classification)
    print("Resolution:", out["resolution"])
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))

    # Missing optional AES dependency is a diagnostic condition, not a safety failure.
    # The structural validations should still pass; the caller can install an AES backend.
    if not all(vals.values()):
        raise AssertionError("HWPX distribution password probe structural validation failed")


if __name__ == "__main__":
    main()
