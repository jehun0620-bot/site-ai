# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S23
Exact bounded probe of the official Seongnam Synap preview XML resources
for Gazette 938 (pstSn=29098), based on the module-mode contract recovered
in S20-S22.

Requests at most:
1) info XML: rs + '/' + fn + '.xml'
2) first page XML: rs + '/' + file_name + '.files/' + file_name + '_1.xml'

No OCR, no cumulative state mutation, no legal promotion.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_exact_xml_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
RS = "/humanframe/global/html/preview/result/attach"
FN = "제938호(2009.12.07 월요일).hwp"
INFO_URL = BASE + RS + "/" + FN + ".xml"
TIMEOUT = 20
MAX_REQUESTS = 2

DIRECT_TERMS = ("개발밀도관리구역", "개발밀도 관리구역")
HIGH_SIGNAL = ("개발밀도", "밀도관리")
LOW_SIGNAL = ("관리구역",)


def host(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def xml_text_root(text: str):
    return ET.fromstring(text.encode("utf-8", errors="ignore"))


def find_index(root: ET.Element):
    if root.tag == "index":
        return root
    return root.find(".//index")


def child_text_or_attr(index: ET.Element, name: str):
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
    for tag in ("text", "cell"):
        for node in root.iter(tag):
            if node.text:
                chunks.append(node.text)
    if not chunks:
        chunks = [x.strip() for x in root.itertext() if x and x.strip()]
    return "\n".join(chunks)


def count_terms(text: str):
    return {
        "direct": {t: text.count(t) for t in DIRECT_TERMS},
        "high_signal": {t: text.count(t) for t in HIGH_SIGNAL},
        "low_signal": {t: text.count(t) for t in LOW_SIGNAL},
    }


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("LEGACY PREVIEW EXACT XML PROBE")
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
        "Referer": BASE + "/humanframe/global/html/preview/skin/doc.html",
    })

    records = []
    info_r = s.get(INFO_URL, timeout=TIMEOUT)
    info_record = {
        "kind": "INFO_XML",
        "requested_url": INFO_URL,
        "final_url": info_r.url,
        "host": host(info_r.url),
        "status": info_r.status_code,
        "content_type": info_r.headers.get("Content-Type", ""),
        "bytes": len(info_r.content),
    }
    records.append(info_record)
    print("INFO XML")
    print("URL:", info_r.url)
    print("HTTP:", info_r.status_code)
    print("Content-Type:", info_record["content_type"])
    print("Bytes:", info_record["bytes"])

    file_name = None
    page_count = None
    info_parse_ok = False
    if info_r.status_code == 200 and info_r.text.strip():
        try:
            root = xml_text_root(info_r.text)
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
            info_record["parse_error"] = repr(exc)

    print("Parsed file_name:", file_name)
    print("Parsed page_count:", page_count)
    print()

    page_url = None
    page_text = ""
    term_counts = None
    page_parse_ok = False
    if file_name:
        page_url = BASE + RS + "/" + file_name + ".files/" + file_name + "_1.xml"
        page_r = s.get(page_url, timeout=TIMEOUT)
        page_record = {
            "kind": "PAGE1_XML",
            "requested_url": page_url,
            "final_url": page_r.url,
            "host": host(page_r.url),
            "status": page_r.status_code,
            "content_type": page_r.headers.get("Content-Type", ""),
            "bytes": len(page_r.content),
        }
        records.append(page_record)
        print("PAGE 1 XML")
        print("URL:", page_r.url)
        print("HTTP:", page_r.status_code)
        print("Content-Type:", page_record["content_type"])
        print("Bytes:", page_record["bytes"])
        if page_r.status_code == 200 and page_r.text.strip():
            try:
                proot = xml_text_root(page_r.text)
                page_text = extract_page_text(proot)
                page_parse_ok = True
                term_counts = count_terms(page_text)
            except Exception as exc:
                page_record["parse_error"] = repr(exc)
        print("Text chars:", len(page_text))
        print("Term counts:", term_counts)
        if page_text:
            snippet = re.sub(r"\s+", " ", page_text)[:1200]
            print("Text sample:", snippet)
        print()

    output = {
        "step": "STEP 17-21-C-16-8-T-34-S23",
        "target": {
            "gazette_number": 938,
            "date": "2009-12-07",
            "pstSn": "29098",
            "fn": FN,
            "rs": RS,
        },
        "records": records,
        "info_parse_ok": info_parse_ok,
        "file_name": file_name,
        "page_count": page_count,
        "page_url": page_url,
        "page_parse_ok": page_parse_ok,
        "page_text_chars": len(page_text),
        "term_counts": term_counts,
        "network_request_count": len(records),
        "negative_evidence_allowed": False,
        "state_mutation_allowed": False,
        "legal_promotion_allowed": False,
    }
    OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")

    vals = {
        "request budget respected": len(records) <= MAX_REQUESTS,
        "all hosts official": all(r.get("host") == HOST for r in records),
        "info request performed": bool(records),
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print("SUMMARY")
    print("Requests:", len(records))
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
        raise AssertionError("legacy preview exact XML probe validation failed")


if __name__ == "__main__":
    main()
