# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-33
Development Density Management Area
Municipal Gazette HWP5 UQQ700 Bounded Batch Search

Actual candidate search for the HWP5 era.

Scope
-----
- HWP5 era: Gazette 526 / 2004-01-12 through Gazette 1872 / 2023-07-17
- first/next bounded batch: up to 10 previously unprocessed rows
- per row: attachment metadata + one HWP download
- supports both ordinary HWP5 BodyText and distribution-document ViewText
- searches all recovered section text for direct/related UQQ700 terms
- persists cumulative state for repeated runs

Safety
------
- no OCR
- no PDF search
- no HWP3/HWPX rows
- no legal/SITE promotion
- zero matches => UNKNOWN, never FALSE
"""
from __future__ import annotations

import json
import re
import struct
import zlib
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, urlparse

import olefile
import requests
from Crypto.Cipher import AES

BASE_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = BASE_DIR / "law_data" / "output"
T23 = OUT_DIR / "development_density_management_area_municipal_gazette_historical_row_registry_recovery.json"
OUT = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_bounded_batch_search.json"
STATE = OUT_DIR / "development_density_management_area_municipal_gazette_hwp5_uqq700_cumulative_state.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
DIRECT = ["개발밀도관리구역", "개발밀도 관리구역"]
RELATED = ["개발밀도", "밀도관리", "관리구역"]

HWP5_FIRST_PST = "28675"  # Gazette 526, 2004-01-12
HWP5_LAST_PST = "344241"  # Gazette 1872, 2023-07-17
BATCH_SIZE = 10
MAX_REQUESTS = 20
TIMEOUT = 30
MAX_META_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 16 * 1024 * 1024
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"
ATTACHMENT_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/atchFileDetail"
DOWNLOAD_ENDPOINT = "https://www.seongnam.go.kr/bbs010308/getFile"
BASE_DETAIL = "https://www.seongnam.go.kr/bbs010308/"
BBS_CRT_SN = "16002"
OLE_SIG = bytes.fromhex("D0CF11E0A1B11AE1")
EXPECTED_DISTRIBUTE_TAG = 28
EXPECTED_DISTRIBUTE_SIZE = 256
PARA_TEXT_TAG = 67


def norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def parse_date(v: Any) -> Optional[date]:
    try:
        y, m, d = [int(x) for x in norm(v).split("-")]
        return date(y, m, d)
    except Exception:
        return None


def host(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


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
    return {"tag_id": tag_id, "level": level, "size": size, "header_bytes": header_bytes, "offset": offset, "payload_offset": payload_offset, "end": end}, end


def msvc_rand_step(seed: int) -> Tuple[int, int]:
    seed = (seed * 214013 + 2531011) & 0xFFFFFFFF
    return seed, (seed >> 16) & 0x7FFF


def decode_distribution_payload(payload: bytes) -> bytes:
    if len(payload) != EXPECTED_DISTRIBUTE_SIZE:
        raise ValueError("distribution payload must be 256 bytes")
    buf = bytearray(payload)
    state = struct.unpack_from("<I", buf, 0)[0]
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
    key = bytes(buf[key_offset:key_offset + 16])
    if len(key) != 16:
        raise ValueError("distribution AES key invalid")
    return key


def sanitize_para_text(payload: bytes) -> str:
    if len(payload) % 2:
        payload = payload[:-1]
    text = payload.decode("utf-16le", errors="ignore")
    chars = []
    for ch in text:
        code = ord(ch)
        if ch in "\r\n\t":
            chars.append(" ")
        elif code >= 0x20 and code not in range(0x7F, 0xA0):
            chars.append(ch)
        else:
            chars.append(" ")
    return re.sub(r"\s+", " ", "".join(chars)).strip()


def parse_records_text(data: bytes) -> Dict[str, Any]:
    offset = 0
    records = 0
    paragraphs: List[str] = []
    para_count = 0
    error = ""
    while offset < len(data):
        try:
            rec, next_offset = parse_record_header(data, offset)
        except Exception as exc:
            error = repr(exc)
            break
        if rec["tag_id"] == PARA_TEXT_TAG:
            para_count += 1
            text = sanitize_para_text(data[rec["payload_offset"]:rec["end"]])
            if text:
                paragraphs.append(text)
        records += 1
        offset = next_offset
        if records > 200000:
            error = "record safety limit exceeded"
            break
    merged = "\n".join(paragraphs)
    return {"record_count": records, "para_text_record_count": para_count, "fully_consumed": offset == len(data), "parse_error": error, "text": merged}


def stream_names(ole: olefile.OleFileIO, prefix: str) -> List[str]:
    names = []
    for parts in ole.listdir(streams=True, storages=False):
        name = "/".join(parts)
        if name.startswith(prefix + "/Section"):
            names.append(name)
    def key(name: str):
        m = re.search(r"Section(\d+)$", name)
        return int(m.group(1)) if m else 10**9
    return sorted(names, key=key)


def file_header_flags(ole: olefile.OleFileIO) -> Dict[str, Any]:
    raw = ole.openstream("FileHeader").read()
    if len(raw) < 40 or not raw.startswith(b"HWP Document File"):
        raise ValueError("invalid HWP5 FileHeader")
    flags = struct.unpack_from("<I", raw, 36)[0]
    return {"compressed": bool(flags & 0x1), "password": bool(flags & 0x2), "distribution": bool(flags & 0x4), "flags": flags}


def extract_hwp5(raw: bytes) -> Dict[str, Any]:
    if not raw.startswith(OLE_SIG):
        return {"ok": False, "error": "not OLE HWP5", "text": ""}
    try:
        import io
        ole = olefile.OleFileIO(io.BytesIO(raw))
        try:
            flags = file_header_flags(ole)
            all_text: List[str] = []
            section_results = []
            if flags["distribution"]:
                names = stream_names(ole, "ViewText")
                if not names:
                    raise ValueError("distribution HWP has no ViewText sections")
                for name in names:
                    stored = ole.openstream(name).read()
                    first, body_offset = parse_record_header(stored, 0)
                    if first["tag_id"] != EXPECTED_DISTRIBUTE_TAG or first["size"] != EXPECTED_DISTRIBUTE_SIZE:
                        raise ValueError(f"unexpected distribution record in {name}")
                    key = decode_distribution_payload(stored[first["payload_offset"]:first["end"]])
                    ciphertext = stored[body_offset:]
                    if len(ciphertext) % 16:
                        raise ValueError(f"AES ciphertext not aligned in {name}")
                    decrypted = AES.new(key, AES.MODE_ECB).decrypt(ciphertext)
                    plain = zlib.decompress(decrypted, -zlib.MAX_WBITS)
                    parsed = parse_records_text(plain)
                    section_results.append({"stream": name, "stored_bytes": len(stored), "plain_bytes": len(plain), "records": parsed["record_count"], "para_text_records": parsed["para_text_record_count"], "fully_consumed": parsed["fully_consumed"], "parse_error": parsed["parse_error"], "text_chars": len(parsed["text"])})
                    if parsed["text"]:
                        all_text.append(parsed["text"])
            else:
                names = stream_names(ole, "BodyText")
                if not names:
                    raise ValueError("ordinary HWP has no BodyText sections")
                for name in names:
                    stored = ole.openstream(name).read()
                    plain = zlib.decompress(stored, -zlib.MAX_WBITS) if flags["compressed"] else stored
                    parsed = parse_records_text(plain)
                    section_results.append({"stream": name, "stored_bytes": len(stored), "plain_bytes": len(plain), "records": parsed["record_count"], "para_text_records": parsed["para_text_record_count"], "fully_consumed": parsed["fully_consumed"], "parse_error": parsed["parse_error"], "text_chars": len(parsed["text"])})
                    if parsed["text"]:
                        all_text.append(parsed["text"])
            merged = "\n".join(all_text)
            return {"ok": bool(merged) and all(not s["parse_error"] for s in section_results), "error": "", "text": merged, "flags": flags, "sections": section_results}
        finally:
            ole.close()
    except Exception as exc:
        return {"ok": False, "error": repr(exc), "text": ""}


def flatten_items(obj: Any) -> List[Dict[str, Any]]:
    found = []
    def walk(x: Any):
        if isinstance(x, dict):
            keys = {str(k).lower() for k in x}
            if any(k in keys for k in ["fileno", "file_no", "atchfileno", "orginlfilenm", "orignlfilenm", "strefilenm"]):
                found.append(x)
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(obj)
    return found


def hwp_attachment(obj: Any) -> Optional[Dict[str, str]]:
    for item in flatten_items(obj):
        lower = {str(k).lower(): v for k, v in item.items()}
        no = lower.get("fileno") or lower.get("file_no") or lower.get("atchfileno") or lower.get("fileid")
        name = norm(lower.get("orginlfilenm") or lower.get("orignlfilenm") or lower.get("filename") or lower.get("filenm") or lower.get("strefilenm"))
        if name.lower().endswith(".hwp") and norm(no):
            return {"file_no": norm(no), "file_name": name}
    return None


def get_json(session: requests.Session, pst: str):
    detail = urljoin(BASE_DETAIL, pst)
    with session.get(ATTACHMENT_ENDPOINT, params={"pstSn": pst}, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
        chunks = []; total = 0
        for c in r.iter_content(128 * 1024):
            if not c: continue
            total += len(c)
            if total > MAX_META_BYTES: raise ValueError("metadata too large")
            chunks.append(c)
        raw = b"".join(chunks)
        try: obj = r.json()
        except Exception: obj = json.loads(raw.decode(r.encoding or "utf-8", errors="replace"))
        return r.status_code, str(r.url), obj


def get_file(session: requests.Session, pst: str, file_no: str):
    detail = urljoin(BASE_DETAIL, pst)
    params = {"bbsCrtSn": BBS_CRT_SN, "pstSn": pst, "fileNo": file_no}
    with session.get(DOWNLOAD_ENDPOINT, params=params, headers={"Referer": detail}, timeout=TIMEOUT, allow_redirects=True, stream=True) as r:
        chunks = []; total = 0
        for c in r.iter_content(128 * 1024):
            if not c: continue
            total += len(c)
            if total > MAX_FILE_BYTES: raise ValueError("file too large")
            chunks.append(c)
        return r.status_code, str(r.url), b"".join(chunks)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("MUNICIPAL GAZETTE HWP5 UQQ700 BOUNDED BATCH SEARCH")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Batch size:", BATCH_SIZE)
    print("Max requests:", MAX_REQUESTS)
    print("OCR: DISABLED")
    print("PDF search: DISABLED")
    print()

    if not T23.exists(): raise FileNotFoundError(T23)
    reg = json.loads(T23.read_text(encoding="utf-8"))
    rows = [r for r in (reg.get("canonical_gazette_rows") or []) if parse_date(r.get("date")) and norm(r.get("pstSn"))]
    rows.sort(key=lambda r: (parse_date(r.get("date")), int(r.get("gazette_number") or 0), norm(r.get("pstSn"))))
    start = next(i for i, r in enumerate(rows) if norm(r.get("pstSn")) == HWP5_FIRST_PST)
    end = next(i for i, r in enumerate(rows) if norm(r.get("pstSn")) == HWP5_LAST_PST)
    era = rows[start:end + 1]

    state = {"processed_pstSn": [], "results": []} if not STATE.exists() else json.loads(STATE.read_text(encoding="utf-8"))
    done = set(state.get("processed_pstSn") or [])
    selected = [r for r in era if norm(r.get("pstSn")) not in done][:BATCH_SIZE]
    if not selected:
        print("No remaining HWP5 rows.")
        return

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    req = 0
    batch = []
    for row in selected:
        pst = norm(row.get("pstSn"))
        rec: Dict[str, Any] = {"date": norm(row.get("date")), "gazette_number": row.get("gazette_number"), "pstSn": pst, "status": "UNKNOWN", "direct_matches": {}, "related_matches": {}, "error": ""}
        try:
            hs, mu, obj = get_json(session, pst); req += 1
            att = hwp_attachment(obj)
            rec["metadata_http"] = hs; rec["metadata_url"] = mu; rec["attachment"] = att
            if not att: raise ValueError("HWP attachment not found")
            ds, du, raw = get_file(session, pst, att["file_no"]); req += 1
            rec["download_http"] = ds; rec["download_url"] = du; rec["download_bytes"] = len(raw)
            ext = extract_hwp5(raw)
            rec["extract_ok"] = ext.get("ok"); rec["extract_error"] = ext.get("error")
            rec["hwp_flags"] = ext.get("flags") or {}; rec["section_count"] = len(ext.get("sections") or [])
            rec["text_chars"] = len(ext.get("text", "") or "")
            if not ext.get("ok"): raise ValueError(ext.get("error") or "HWP5 extraction failed")
            text = ext["text"]
            rec["direct_matches"] = {t: text.count(t) for t in DIRECT}
            rec["related_matches"] = {t: text.count(t) for t in RELATED}
            if any(rec["direct_matches"].values()): rec["status"] = "DIRECT_CANDIDATE"
            elif any(rec["related_matches"].values()): rec["status"] = "RELATED_CANDIDATE"
            else: rec["status"] = "NO_TERM_IN_EXTRACTED_SAMPLE"
        except Exception as exc:
            rec["error"] = repr(exc)
            rec["status"] = "EXTRACTION_OR_REQUEST_UNKNOWN"
        batch.append(rec)
        print("ROW:", {k: rec.get(k) for k in ["gazette_number", "date", "pstSn", "status", "download_bytes", "hwp_flags", "section_count", "text_chars", "direct_matches", "related_matches", "error"]})

    merged_results = (state.get("results") or []) + batch
    processed = list(dict.fromkeys((state.get("processed_pstSn") or []) + [r["pstSn"] for r in batch]))
    candidates = [r for r in merged_results if r.get("status") in {"DIRECT_CANDIDATE", "RELATED_CANDIDATE"}]
    unresolved = [r for r in merged_results if r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN"]
    new_state = {"era": "HWP5", "era_row_count": len(era), "processed_count": len(processed), "remaining_count": len(era) - len(processed), "processed_pstSn": processed, "candidate_count": len(candidates), "unresolved_count": len(unresolved), "results": merged_results, "negative_evidence_allowed": False}
    STATE.write_text(json.dumps(new_state, ensure_ascii=False, indent=2), encoding="utf-8")

    output = {"step": "STEP 17-21-C-16-8-T-33 Municipal Gazette HWP5 UQQ700 Bounded Batch Search", "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE}, "network_request_count": req, "batch_size": len(batch), "era_row_count": len(era), "batch": batch, "cumulative_summary": {k: new_state[k] for k in ["processed_count", "remaining_count", "candidate_count", "unresolved_count"]}, "negative_evidence_allowed": False, "verified_positive": False, "runtime_registration_allowed": False, "site_positive_allowed": False, "site_negative_allowed": False, "final_positive_promotion_allowed": False, "resolution": "MUNICIPAL_GAZETTE_HWP5_UQQ700_BOUNDED_BATCH_SEARCH_COMPLETED"}
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    print(); print("SUMMARY")
    print("HWP5 era rows:", len(era)); print("Batch processed:", len(batch)); print("Cumulative processed:", new_state["processed_count"]); print("Remaining:", new_state["remaining_count"]); print("Candidates:", new_state["candidate_count"]); print("Unresolved:", new_state["unresolved_count"]); print("Network requests:", req); print("State:", STATE); print("Output:", OUT)

    unsafe = any([output["verified_positive"], output["runtime_registration_allowed"], output["site_positive_allowed"], output["site_negative_allowed"], output["final_positive_promotion_allowed"]])
    vals = {"T-23 registry exists": T23.exists(), "batch bounded": len(batch) <= BATCH_SIZE, "request budget respected": req <= MAX_REQUESTS, "all response hosts official": all((not r.get("metadata_url") or host(r.get("metadata_url")) == "www.seongnam.go.kr") and (not r.get("download_url") or host(r.get("download_url")) == "www.seongnam.go.kr") for r in batch), "no non-HWP5 signature rows silently accepted": all(r.get("status") == "EXTRACTION_OR_REQUEST_UNKNOWN" or r.get("extract_ok") for r in batch), "negative evidence disabled": not output["negative_evidence_allowed"], "unsafe promotion leakage zero": not unsafe, "state written": STATE.exists() and STATE.stat().st_size > 0, "output written": OUT.exists() and OUT.stat().st_size > 0}
    print(); print("VALIDATION")
    for k, v in vals.items(): print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()): raise AssertionError("HWP5 UQQ700 bounded batch search failed")


if __name__ == "__main__":
    main()
