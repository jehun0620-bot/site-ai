# -*- coding: utf-8 -*-
"""
STEP 17-21-C-16-8-T-34-S25
Session-primed exact XML probe for Gazette 938 (pstSn=29098).

Replays the official sequence in one requests.Session:
1) detail page GET
2) attachment metadata GET
3) filePreview GET (allow redirects)
4) exact module info XML: rs/fn.xml
5) if info XML succeeds, first page XML derived from index.file_name

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
OUT = BASE_DIR / "law_data" / "output" / "development_density_management_area_municipal_gazette_legacy_preview_session_primed_exact_xml_probe.json"

BASE = "https://www.seongnam.go.kr"
HOST = "www.seongnam.go.kr"
PST_SN = "29098"
BBS_CRT_SN = "16002"
FILE_NO = "28559"
FN = "제938호(2009.12.07 월요일).hwp"
RS = "/humanframe/global/html/preview/result/attach"
DETAIL_URL = BASE + "/bbs010308/" + PST_SN
META_URL = BASE + "/bbs010308/atchFileDetail"
PREVIEW_URL = BASE + "/bbs010308/filePreview"
INFO_URL = BASE + RS + "/" + FN + ".xml"
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
    print("LEGACY PREVIEW SESSION-PRIMED EXACT XML PROBE")
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
    print("DETAIL:", r1.status_code, r1.url)

    r2 = s.get(META_URL, params={"pstSn": PST_SN}, headers={"X-Requested-With": "XMLHttpRequest", "Referer": r1.url}, timeout=TIMEOUT)
    records.append(record("ATTACH_META", r2))
    print("META:", r2.status_code, r2.url)

    r3 = s.get(PREVIEW_URL, params={"bbsCrtSn": BBS_CRT_SN, "pstSn": PST_SN, "fileNo": FILE_NO}, headers={"Referer": r1.url}, timeout=TIMEOUT, allow_redirects=True)
    records.append(record("FILE_PREVIEW", r3))
    print("PREVIEW:", r3.status_code, r3.url)
    print("Cookies:", sorted(s.cookies.get_dict().keys()))

    r4 = s.get(INFO_URL, headers={"Referer": r3.url}, timeout=TIMEOUT)
    records.append(record("INFO_XML", r4))
    print("INFO XML:", r4.status_code, r4.url)
    print("INFO Content-Type:", r4.headers.get("Content-Type", ""))
    print("INFO Bytes:", len(r4.content))

    file_name = None
    page_count = None
    info_parse_ok = False
    info_root_tag = None
    if r4.status_code == 200 and r4.text.strip():
        try:
            root = parse_xml(r4.text)
            info_root_tag = root.tag
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

    print("Info root tag:", info_root_tag)
    print("Parsed file_name:", file_name)
    print("Parsed page_count:", page_count)

    page_url = None
    page_parse_ok = False
    page_text = ""
    term_counts = None
    if file_name and len(records) < MAX_REQUESTS:
        page_url = BASE + RS + "/" + file_name + ".files/" + file_name + "_1.xml"
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
        "step": "STEP 17-21-C-16-8-T-34-S25",
        "target": {"gazette_number": 938, "date": "2009-12-07", "pstSn": PST_SN, "fileNo": FILE_NO, "fn": FN, "rs": RS},
        "records": records,
        "cookies": sorted(s.cookies.get_dict().keys()),
        "info_parse_ok": info_parse_ok,
        "info_root_tag": info_root_tag,
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
        "all hosts official": all(x.get("host") == HOST for x in records),
        "detail succeeded": r1.status_code == 200,
        "metadata succeeded": r2.status_code == 200,
        "preview shell succeeded": r3.status_code == 200,
        "negative evidence disabled": not output["negative_evidence_allowed"],
        "state mutation disabled": not output["state_mutation_allowed"],
        "legal promotion disabled": not output["legal_promotion_allowed"],
        "output written": OUT.exists() and OUT.stat().st_size > 0,
    }

    print()
    print("SUMMARY")
    print("Requests:", len(records))
    print("Info HTTP:", r4.status_code)
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
        raise AssertionError("session-primed exact XML probe validation failed")


if __name__ == "__main__":
    main()
