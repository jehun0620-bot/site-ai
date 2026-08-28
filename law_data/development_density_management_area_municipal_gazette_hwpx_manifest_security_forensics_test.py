# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-28-S1-2
Development Density Management Area
Municipal Gazette HWPX Manifest Security Forensics

Offline-only analysis of one already persisted representative HWPX package.
Inspect META-INF/manifest.xml, Contents/content.hpf, and other parseable XML metadata
for explicit encryption/DRM/transform declarations and correlate them with the
high-entropy non-XML package entries. No network requests, no decryption attempts,
no bulk traversal, and no legal promotion.
"""
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List
import xml.etree.ElementTree as ET

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SAMPLE = OUT_DIR / "development_density_management_area_municipal_gazette_representative_sample.hwpx"
S1_2_OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_package_entry_forensics.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_manifest_security_forensics.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

SECURITY_WORDS = (
    "encrypt", "encrypted", "encryption", "cipher", "algorithm", "key", "salt",
    "iteration", "checksum", "digest", "password", "drm", "rights", "license",
    "protect", "protected", "security", "transform", "compression", "certificate",
    "signature", "signed", "crypto", "aes", "sha", "pbkdf", "kdf", "iv",
)


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def ns_uri(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag[1:].split("}", 1)[0]
    return ""


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def security_hit(text: str) -> bool:
    low = text.lower()
    return any(word in low for word in SECURITY_WORDS)


def flatten_element(elem: ET.Element, member: str) -> Dict[str, Any]:
    attrs = []
    for k, v in elem.attrib.items():
        attrs.append({
            "name": local_name(k),
            "namespace": ns_uri(k),
            "value": norm(v)[:500],
        })
    text = norm(elem.text)
    searchable = " ".join(
        [member, local_name(elem.tag), ns_uri(elem.tag), text]
        + [f"{a['name']} {a['namespace']} {a['value']}" for a in attrs]
    )
    return {
        "member": member,
        "tag": local_name(elem.tag),
        "namespace": ns_uri(elem.tag),
        "attributes": attrs,
        "text": text[:1000],
        "security_related": security_hit(searchable),
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWPX MANIFEST SECURITY FORENSICS")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Network requests: 0")
    print("Decryption attempts: 0")
    print("Bulk traversal: DISABLED")
    print()

    if not SAMPLE.exists():
        raise FileNotFoundError(SAMPLE)
    if not S1_2_OUT.exists():
        raise FileNotFoundError(S1_2_OUT)

    package_forensics = json.loads(S1_2_OUT.read_text(encoding="utf-8"))
    failed_xml_members = {
        str(x.get("member"))
        for x in (package_forensics.get("entries") or [])
        if x.get("xml_candidate") and not x.get("xml_parse_ok")
    }

    parsed_members: List[str] = []
    all_elements: List[Dict[str, Any]] = []
    security_elements: List[Dict[str, Any]] = []
    manifest_file_entries: List[Dict[str, Any]] = []
    parse_errors: List[Dict[str, str]] = []

    with zipfile.ZipFile(SAMPLE) as z:
        for member in z.namelist():
            if not member.lower().endswith((".xml", ".hpf")):
                continue
            data = z.read(member)
            try:
                root = ET.fromstring(data)
            except Exception as e:
                parse_errors.append({"member": member, "error": repr(e)})
                continue

            parsed_members.append(member)
            for elem in root.iter():
                record = flatten_element(elem, member)
                all_elements.append(record)
                if record["security_related"]:
                    security_elements.append(record)

                if member.lower() == "meta-inf/manifest.xml":
                    attrs = {local_name(k): norm(v) for k, v in elem.attrib.items()}
                    path_value = (
                        attrs.get("full-path")
                        or attrs.get("path")
                        or attrs.get("href")
                        or attrs.get("id")
                        or ""
                    )
                    media_type = attrs.get("media-type") or attrs.get("type") or ""
                    if path_value or media_type:
                        manifest_file_entries.append({
                            "tag": local_name(elem.tag),
                            "path": path_value,
                            "media_type": media_type,
                            "attributes": attrs,
                            "references_failed_xml_member": path_value in failed_xml_members,
                        })

    explicit_crypto_signals = []
    explicit_drm_signals = []
    transform_signals = []
    for r in security_elements:
        blob = json.dumps(r, ensure_ascii=False).lower()
        if any(w in blob for w in ("encrypt", "cipher", "aes", "pbkdf", "kdf", "salt", "iteration", "crypto")):
            explicit_crypto_signals.append(r)
        if any(w in blob for w in ("drm", "rights", "license", "certificate", "protected")):
            explicit_drm_signals.append(r)
        if any(w in blob for w in ("transform", "compression", "algorithm")):
            transform_signals.append(r)

    manifest_failed_refs = [x for x in manifest_file_entries if x["references_failed_xml_member"]]

    if explicit_crypto_signals:
        classification = "EXPLICIT_PACKAGE_CRYPTO_METADATA_PRESENT"
    elif explicit_drm_signals:
        classification = "EXPLICIT_DRM_OR_RIGHTS_METADATA_PRESENT"
    elif transform_signals:
        classification = "EXPLICIT_TRANSFORM_METADATA_PRESENT_NO_CRYPTO_DECLARATION"
    elif failed_xml_members and manifest_failed_refs:
        classification = "OPAQUE_PAYLOADS_REFERENCED_BY_MANIFEST_WITHOUT_EXPLICIT_SECURITY_DECLARATION"
    elif failed_xml_members:
        classification = "OPAQUE_PAYLOADS_PRESENT_WITHOUT_EXPLICIT_SECURITY_DECLARATION"
    else:
        classification = "NO_OPAQUE_XML_PAYLOADS_DETECTED"

    out = {
        "step": "STEP 17-21-C-16-8-T-28-S1-2 Municipal Gazette HWPX Manifest Security Forensics",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "inputs": {
            "sample": str(SAMPLE),
            "package_entry_forensics": str(S1_2_OUT),
        },
        "execution": {
            "network_request_count": 0,
            "decryption_attempt_count": 0,
            "bulk_traversal_executed": False,
        },
        "summary": {
            "parsed_metadata_member_count": len(parsed_members),
            "metadata_parse_error_count": len(parse_errors),
            "security_related_element_count": len(security_elements),
            "explicit_crypto_signal_count": len(explicit_crypto_signals),
            "explicit_drm_signal_count": len(explicit_drm_signals),
            "transform_signal_count": len(transform_signals),
            "manifest_file_entry_count": len(manifest_file_entries),
            "manifest_failed_payload_reference_count": len(manifest_failed_refs),
            "failed_xml_member_count": len(failed_xml_members),
            "classification": classification,
        },
        "parsed_metadata_members": parsed_members,
        "metadata_parse_errors": parse_errors,
        "manifest_file_entries": manifest_file_entries,
        "security_related_elements": security_elements,
        "explicit_crypto_signals": explicit_crypto_signals,
        "explicit_drm_signals": explicit_drm_signals,
        "transform_signals": transform_signals,
        "failed_xml_members": sorted(failed_xml_members),
        "verified_positive": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWPX_MANIFEST_SECURITY_FORENSICS_COMPLETED",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "persisted sample exists": SAMPLE.exists() and SAMPLE.stat().st_size > 0,
        "package entry forensics input exists": S1_2_OUT.exists(),
        "network request count zero": out["execution"]["network_request_count"] == 0,
        "decryption attempts zero": out["execution"]["decryption_attempt_count"] == 0,
        "manifest parsed": "META-INF/manifest.xml" in parsed_members,
        "content.hpf parsed": "Contents/content.hpf" in parsed_members,
        "failed payload set recovered": len(failed_xml_members) > 0,
        "classification produced": bool(classification),
        "bulk traversal disabled": not out["execution"]["bulk_traversal_executed"],
        "unsafe promotion disabled": not any([
            out["verified_positive"], out["site_positive_allowed"], out["site_negative_allowed"]
        ]),
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("Sample:", SAMPLE)
    print("Parsed metadata members:", len(parsed_members), parsed_members)
    print("Metadata parse errors:", len(parse_errors))
    print("Failed XML members from prior stage:", len(failed_xml_members))
    print("Manifest file entries:", len(manifest_file_entries))
    print("Manifest refs to failed payloads:", len(manifest_failed_refs))
    print("Security-related elements:", len(security_elements))
    print("Explicit crypto signals:", len(explicit_crypto_signals))
    print("Explicit DRM signals:", len(explicit_drm_signals))
    print("Transform signals:", len(transform_signals))
    print("Classification:", classification)
    print()

    print("SECURITY SIGNALS")
    for r in security_elements[:80]:
        print("-", r["member"], r["tag"], "ns=", r["namespace"])
        for a in r["attributes"]:
            print("   ATTR", a["name"], "=", a["value"][:240])
        if r["text"]:
            print("   TEXT", r["text"][:240])
    print()

    print("MANIFEST REFERENCES TO FAILED PAYLOADS")
    for r in manifest_failed_refs:
        print("-", r["path"], "media_type=", r["media_type"], "attrs=", r["attributes"])
    print()

    print("Resolution:", out["resolution"])
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("HWPX manifest security forensics failed")


if __name__ == "__main__":
    main()
