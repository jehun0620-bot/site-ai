# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S27
Probe exact browser-style query decoding semantics for the official legacy
preview URL. The viewer JS uses decodeURIComponent() directly, so '+' is
preserved as '+' rather than decoded to a space.

Replays official detail -> metadata -> filePreview, then derives fn/rs from
r3.url using percent-decoding only (urllib.parse.unquote, not unquote_plus),
and requests the exact runtime info XML. If successful, derives page 1 XML.

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse, urlsplit, unquote

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_plus_semantics_xml_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
BBS_CRT_SN = "16002"
FILE_NO = "28559"
DETAIL_URL = BASE + "/bbs010308/" + PST_SN
META_URL = BASE + "/bbs010308/atchFileDetail"
PREVIEW_URL = BASE + "/bbs010308/filePreview"
TIMEOUT = 20
MAX_REQUESTS = 5

DIRECT_TERMS = ("개발밀도관리구역", "개발밀도 관리구역")
HIGH_SIGNAL = ("개발밀도", "밀도관리")
LOW_SIGNAL = ("관리구역",)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def record(kind: str, r: requests.Response) -> dict:
    return {
        "kind": kind,
        "status": r.status_code,
        "url": r.url,
        "host": host(r.url),
        "content_type": r.headers.get("Content-Type", ""),
        "bytes": len(r.content),
    }


def js_decode_query(url: str) -> dict[str, str]:
    query = urlsplit(url).query
    out = {}
    for pair in query.split("&"):
        if not pair:
            continue
        parts = pair.split("=", 1)
        key = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        out[key] = unquote(value)
    return out


def parse_xml(text: str) -> ET.Element:
    return ET.fromstring(text.encode("utf-8", errors="ignore"))


def find_index(root: ET.Element):
    if root.tag == "index":
        return root
    return root.find(".//index")


def child_text_or_attr(index: ET.Element | None, name: str):
    if index is None:
        return None
    if name in index.attrib:
        return index.attrib.get(name)
    node = index.find(name)
    if node is not None and node.text:
        return node.text.strip()
    node = index.find(f".//{name}")
    if node is not None and node.text:
        return node.text.strip()
    return None


def extract_page_text(root: ET.Element) -> str:
    chunks = []
    for node in root.iter("text"):
        if node.text:
            chunks.append(node.text)
    if not chunks:
        chunks = [x.strip() for x in root.itertext() if x and x.strip()]
    return "\n".join(chunks)


def count_terms(text: str) -> dict:
    return {
        "direct": {t: text.count(t) for t in DIRECT_TERMS},
        "high_signal": {t: text.count(t) for t in HIGH_SIGNAL},
        "low_signal": {t: text.count(t) for t in LOW_SIGNAL},
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW PLUS-SIGN SEMANTICS XML PROBE")
    print("=" * 60)
    print("Gazette: 938")
    print("pstSn: 29098")
    print("OCR: DISABLED")
    print("State mutation: DISABLED")
    print()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/128 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })

    records = []
    r1 = s.get(DETAIL_URL, timeout=TIMEOUT)
    records.append(record("DETAIL", r1))
    r2 = s.get(META_URL, params={"pstSn": PST_SN}, headers={"X-Requested-With": "XMLHttpRequest", "Referer": r1.url}, timeout=TIMEOUT)
    records.append(record("META", r2))
    r3 = s.get(PREVIEW_URL, params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}, headers={"Referer": r1.url}, timeout=TIMEOUT, allow_redirects=True)
    records.append(record("PREVIEW", r3))

    params = js_decode_query(r3.url)
    fn_runtime = params.get("fn")
    rs_runtime = params.get("rs")

    print("PREVIEW URL:", r3.url)
    print("Runtime fn:", repr(fn_runtime))
    print("Runtime rs:", repr(rs_runtime))
    print("Runtime fn contains plus:", bool(fn_runtime and "+" in fn_runtime))

    info_url = None
    info_parse_ok = False
    file_name = None
    page_count = None
    page_url = None
    page_parse_ok = False
    page_text = ""
    term_counts = None

    if fn_runtime and rs_runtime:
        info_url = BASE + rs_runtime.rstrip("/") + "/" + fn_runtime + ".xml"
        r4 = s.get(info_url, headers={"Referer": r3.url}, timeout=TIMEOUT)
        records.append(record("INFO_XML", r4))
        print("INFO XML:", r4.status_code, r4.url)
        print("INFO Content-Type:", r4.headers.get("Content-Type", ""))
        print("INFO Bytes:", len(r4.content))

        if r4.status_code == 200 and r4.text.strip():
            try:
                root = parse_xml(r4.text)
                index = find_index(root)
                file_name = child_text_or_attr(index, "file_name")
                page_count = (
                    child_text_or_attr(index, "page_cnt")
                    or child_text_or_attr(index, "pdf_cnt")
                    or child_text_or_attr(index, "slide_cnt")
                    or child_text_or_attr(index, "sheet_cnt")
                )
                info_parse_ok = index is not None
            except Exception as exc:
                records[-1]["parse_error"] = repr(exc)

        print("Parsed file_name:", file_name)
        print("Parsed page_count:", page_count)

        if file_name and len(records) < MAX_REQUESTS:
            page_url = BASE + rs_runtime.rstrip("/") + "/" + file_name + ".files/" + file_name + "_1.xml"
            r5 = s.get(page_url, headers={"Referer": r3.url}, timeout=TIMEOUT)
            records.append(record("PAGE1_XML", r5))
            print("PAGE 1 XML:", r5.status_code, r5.url)
            print("PAGE Content-Type:", r5.headers.get("Content-Type", ""))
            print("PAGE Bytes:", len(r5.content))
            if r5.status_code == 200 and r5.text.strip():
                try:
                    proot = parse_xml(r5.text)
                    page_text = extract_page_text(proot)
                    page_parse_ok = True
                    term_counts = count_terms(page_text)
                except Exception as exc:
                    records[-1]["parse_error"] = repr(exc)
            print("Page text chars:", len(page_text))
            print("Term counts:", term_counts)
            if page_text:
                print("Text sample:", re.sub(r"\s+", " ", page_text)[:1200])

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S27",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO},
        "preview_url": r3.url,
        "runtime_params": params,
        "fn_runtime": fn_runtime,
        "rs_runtime": rs_runtime,
        "info_url": info_url,
        "info_parse_ok": info_parse_ok,
        "file_name": file_name,
        "page_count": page_count,
        "page_url": page_url,
        "page_parse_ok": page_parse_ok,
        "page_text_chars": len(page_text),
        "term_counts": term_counts,
        "records": records,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(x["host"] == HOST for x in records),
        "detail succeeded": r1.status_code == 200,
        "metadata succeeded": r2.status_code == 200,
        "preview succeeded": r3.status_code == 200,
        "runtime fn recovered": bool(fn_runtime),
        "runtime rs recovered": bool(rs_runtime),
        "plus semantics observed": bool(fn_runtime and "+" in fn_runtime),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print()
    print("SUMMARY")
    print("Requests:", len(records))
    print("Runtime fn:", repr(fn_runtime))
    print("Info URL:", info_url)
    print("Info parse ok:", info_parse_ok)
    print("File name:", file_name)
    print("Page 1 requested:", bool(page_url))
    print("Page parse ok:", page_parse_ok)
    print("Output:", OUT)
    print()
    print("VALIDATION")
    for k, v in vals.items():
        print(f"{k}: {v}")
    print("all_pass:", all(vals.values()))
    if not all(vals.values()):
        raise AssertionError("legacy preview plus-sign semantics probe validation failed")


if __name__ == "__main__":
    main()
