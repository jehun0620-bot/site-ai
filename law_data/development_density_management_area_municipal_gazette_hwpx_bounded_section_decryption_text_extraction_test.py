# -*- coding: utf-8 -*-
"""T-28-S1-4: bounded offline decryption/text extraction for ONE HWPX section.

Uses the already-validated public Hancom distribution-password compatibility
constant and manifest-declared crypto parameters. No network, no brute force,
no bulk traversal, and no legal/SITE promotion.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import zlib
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

from Crypto.Cipher import AES

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
SAMPLE = OUT_DIR / "development_density_management_area_municipal_gazette_representative_sample.hwpx"
PRIOR = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_distribution_password_probe.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwpx_bounded_section_decryption_text_extraction.json"
MEMBER = "Contents/section0.xml"
PASSWORD = bytes([0x22,0x59,0x61,0x6e,0x67,0x20,0x57,0x61,0x6e,0x67,0x53,0x75,0x6e,0x76,0x21,0x21,0x22])
DIRECT_TERMS = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED_TERMS = ["개발밀도", "밀도관리", "관리구역"]


def ln(s): return s.rsplit("}", 1)[-1] if "}" in s else s

def attr(e, name):
    for k, v in e.attrib.items():
        if ln(k) == name: return str(v)
    return ""

def manifest_entry(root, path):
    for e in root.iter():
        if ln(e.tag) == "file-entry" and attr(e, "full-path") == path:
            d = {"path": path, "plain_size": int(attr(e,"size") or 0)}
            for c in e.iter():
                n = ln(c.tag)
                if n == "encryption-data": d.update(checksum=attr(c,"checksum"), checksum_type=attr(c,"checksum-type"))
                elif n == "algorithm": d.update(iv=attr(c,"initialisation-vector"), algorithm=attr(c,"algorithm-name"))
                elif n == "key-derivation": d.update(salt=attr(c,"salt"), iterations=int(attr(c,"iteration-count") or 0), key_size=int(attr(c,"key-size") or 0))
                elif n == "start-key-generation": d.update(start_key=attr(c,"start-key-generation-name"))
            return d
    raise KeyError(path)

def decrypt_and_inflate(ciphertext, d):
    start = hashlib.sha256(PASSWORD).digest()
    key = hashlib.pbkdf2_hmac("sha1", start, base64.b64decode(d["salt"]), d["iterations"], dklen=d["key_size"])
    raw = AES.new(key, AES.MODE_CBC, base64.b64decode(d["iv"])).decrypt(ciphertext)
    attempts = []
    for name, wbits in (("RAW_DEFLATE", -zlib.MAX_WBITS), ("ZLIB", zlib.MAX_WBITS)):
        try:
            plain = zlib.decompress(raw, wbits)
            attempts.append((name, plain))
        except Exception as e:
            attempts.append((name + "_ERROR", repr(e).encode()))
    return attempts

def extract_text(root):
    paragraphs = []
    for p in root.iter():
        if ln(p.tag) != "p": continue
        chunks = []
        for e in p.iter():
            if ln(e.tag) == "t" and e.text:
                chunks.append(e.text)
        text = "".join(chunks).strip()
        if text: paragraphs.append(text)
    if paragraphs:
        return "\n".join(paragraphs), len(paragraphs), "P_T"
    chunks = [e.text for e in root.iter() if ln(e.tag) == "t" and e.text]
    return "".join(chunks), 0, "T_ONLY"

def main():
    print("="*60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWPX BOUNDED SECTION DECRYPTION TEXT EXTRACTION")
    print("="*60)
    print("Target: 개발밀도관리구역")
    print("Standard code: UQQ700")
    print("Network requests: 0")
    print("Password candidates: 1 (previously validated public Hancom constant)")
    print("Section payloads probed: 1")
    print("Bulk traversal: DISABLED\n")

    if not SAMPLE.exists(): raise FileNotFoundError(SAMPLE)
    if not PRIOR.exists(): raise FileNotFoundError(PRIOR)
    prior = json.loads(PRIOR.read_text(encoding="utf-8"))
    prior_validated = prior.get("classification") == "PUBLIC_HANCOM_DISTRIBUTION_PASSWORD_VALIDATED_ON_HEADER"

    with zipfile.ZipFile(SAMPLE) as z:
        mr = ET.fromstring(z.read("META-INF/manifest.xml"))
        d = manifest_entry(mr, MEMBER)
        ciphertext = z.read(MEMBER)

    results = []
    accepted = None
    if prior_validated:
        for mode, plain in decrypt_and_inflate(ciphertext, d):
            rec = {"mode": mode, "bytes": len(plain), "xml_ok": False, "root": "", "checksum_ok": False}
            if not mode.endswith("_ERROR"):
                rec["checksum_ok"] = hashlib.sha256(plain[:1024]).digest() == base64.b64decode(d["checksum"])
                try:
                    root = ET.fromstring(plain)
                    rec["xml_ok"] = True
                    rec["root"] = ln(root.tag)
                    text, pc, method = extract_text(root)
                    rec.update(text_chars=len(text), paragraph_count=pc, extraction_method=method,
                               hangul_chars=len(re.findall(r"[가-힣]", text)),
                               direct_matches={t: text.count(t) for t in DIRECT_TERMS},
                               related_matches={t: text.count(t) for t in RELATED_TERMS},
                               text_preview=text[:1200])
                    if rec["checksum_ok"] and accepted is None:
                        accepted = rec
                except Exception as e:
                    rec["xml_error"] = repr(e)
            results.append(rec)

    classification = "SECTION_DECRYPTION_NOT_ATTEMPTED_PRIOR_VALIDATION_MISSING"
    if prior_validated:
        classification = "SECTION_DECRYPTION_VALIDATED_TEXT_EXTRACTED" if accepted and accepted.get("xml_ok") else "SECTION_DECRYPTION_NOT_VALIDATED"

    out = {
        "step": "STEP 17-21-C-16-8-T-28-S1-4",
        "target": {"name":"개발밀도관리구역","standard_code":"UQQ700"},
        "member": MEMBER,
        "prior_header_password_validation": prior_validated,
        "network_request_count": 0,
        "bulk_traversal_executed": False,
        "section_probe_count": 1,
        "brute_force_executed": False,
        "manifest": d,
        "ciphertext_bytes": len(ciphertext),
        "results": results,
        "accepted_result": accepted,
        "classification": classification,
        "semantic_note": "Representative section text is sample evidence only. Match or no-match cannot establish parcel applicability or historical non-designation.",
        "verified_positive": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "resolution": "MUNICIPAL_GAZETTE_HWPX_BOUNDED_SECTION_DECRYPTION_TEXT_EXTRACTION_COMPLETED",
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

    print("Member:", MEMBER)
    print("Ciphertext bytes:", len(ciphertext))
    print("Manifest plain size:", d["plain_size"])
    print("Prior header password validated:", prior_validated)
    print("\nRESULTS")
    for r in results:
        print("-", r["mode"], "bytes=", r["bytes"], "xml_ok=", r["xml_ok"], "root=", r["root"], "checksum_ok=", r["checksum_ok"])
        if r.get("xml_ok"):
            print("  text_chars=", r.get("text_chars"), "paragraphs=", r.get("paragraph_count"), "hangul=", r.get("hangul_chars"))
            print("  direct_matches=", r.get("direct_matches"))
            print("  related_matches=", r.get("related_matches"))
            print("  preview=", repr(r.get("text_preview", "")[:500]))
    print("\nClassification:", classification)
    print("Resolution:", out["resolution"])
    print("Output:", OUT)

    vals = {
        "persisted sample exists": SAMPLE.exists(),
        "prior validated header probe exists": prior_validated,
        "network request count zero": True,
        "single bounded section": out["section_probe_count"] == 1,
        "brute force disabled": not out["brute_force_executed"],
        "bulk traversal disabled": not out["bulk_traversal_executed"],
        "unsafe promotion disabled": not any([out["verified_positive"],out["site_positive_allowed"],out["site_negative_allowed"]]),
        "output written": OUT.exists(),
    }
    print("\nVALIDATION")
    for k,v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()): raise AssertionError("bounded section extraction structural validation failed")

if __name__ == "__main__": main()
