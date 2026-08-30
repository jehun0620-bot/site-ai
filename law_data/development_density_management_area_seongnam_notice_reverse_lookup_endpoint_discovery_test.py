# -*- coding: utf-8 -*-
"""S73: discover the official Seongnam notice-number reverse-lookup/search contract.

This stage only inspects the official /pm010301 notice family. It does not
search for UQQ700 yet, download attachments, mutate cumulative state, or create
legal negative evidence.
"""
from __future__ import annotations

import html
import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_seongnam_notice_reverse_lookup_endpoint_discovery.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
SOURCE_FAMILY = "NOTICE_NUMBER_REVERSE_LOOKUP"

LIST_URL = "https://www.seongnam.go.kr/pm010301/list"
KNOWN_DETAIL_URL = "https://www.seongnam.go.kr/pm010301/151718"
OFFICIAL_HOST = "www.seongnam.go.kr"
TIMEOUT = 20
MAX_TOTAL_REQUESTS = 4
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

FORM_PATTERN = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
INPUT_PATTERN = re.compile(r"<(?:input|select|textarea|button)\b(?P<attrs>[^>]*)>", re.I | re.S)
ATTR_PATTERN = re.compile(r"([:\w-]+)\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^\s>]+))", re.I)
ANCHOR_PATTERN = re.compile(r"<a\b[^>]*href\s*=\s*[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)
TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
NOTICE_NUMBER_PATTERN = re.compile(r"성남시\s*(?:[가-힣]+구\s*)?(?:고시|공고)\s*제?\s*\d{4}\s*[-－]\s*\d+\s*호")
DETAIL_LINK_PATTERN = re.compile(r"^/pm010301/(\d+)(?:[?#].*)?$")


def attrs(raw: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for m in ATTR_PATTERN.finditer(raw or ""):
        out[m.group(1).lower()] = html.unescape(m.group(2) or m.group(3) or m.group(4) or "")
    return out


def clean_text(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(TAG_PATTERN.sub(" ", raw or ""))).strip()


def page_title(text: str) -> str:
    m = TITLE_PATTERN.search(text or "")
    return clean_text(m.group(1)) if m else ""


def parse_forms(text: str, base_url: str) -> list[dict]:
    records = []
    for fm in FORM_PATTERN.finditer(text or ""):
        fa = attrs(fm.group("attrs"))
        controls = []
        for cm in INPUT_PATTERN.finditer(fm.group("body")):
            ca = attrs(cm.group("attrs"))
            name = ca.get("name", "")
            if name:
                controls.append({
                    "name": name,
                    "type": ca.get("type", ""),
                    "value": ca.get("value", ""),
                    "id": ca.get("id", ""),
                })
        action = fa.get("action", "")
        records.append({
            "method": (fa.get("method") or "get").upper(),
            "action_raw": action,
            "action_url": urljoin(base_url, action or base_url),
            "id": fa.get("id", ""),
            "name": fa.get("name", ""),
            "controls": controls,
            "control_names": sorted({c["name"] for c in controls}),
        })
    return records


def parse_detail_links(text: str, base_url: str) -> list[dict]:
    result = []
    seen = set()
    for href, body in ANCHOR_PATTERN.findall(text or ""):
        if not DETAIL_LINK_PATTERN.match(href.strip()):
            continue
        url = urljoin(base_url, href.strip())
        if url in seen:
            continue
        seen.add(url)
        result.append({"url": url, "anchor_text": clean_text(body)})
    return result[:30]


def fetch(session: requests.Session, url: str, request_counter: list[int]) -> dict:
    if request_counter[0] >= MAX_TOTAL_REQUESTS:
        raise AssertionError("request budget exceeded")
    request_counter[0] += 1
    r = session.get(url, timeout=TIMEOUT, allow_redirects=True)
    body = r.content[:MAX_RESPONSE_BYTES]
    text = body.decode(r.encoding or "utf-8", errors="replace")
    return {
        "request_url": url,
        "http_status": r.status_code,
        "final_url": str(r.url),
        "final_host": (urlparse(str(r.url)).hostname or "").lower(),
        "content_type": r.headers.get("Content-Type", ""),
        "body_bytes_read": len(body),
        "title": page_title(text),
        "text": text,
    }


def main() -> None:
    print("=" * 60)
    print("SEONGNAM NOTICE REVERSE LOOKUP ENDPOINT DISCOVERY - S73")
    print("=" * 60)
    print("Source family:", SOURCE_FAMILY)
    print("Attachment download: DISABLED")
    print("State mutation: DISABLED")
    print("Negative evidence: DISABLED")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "ko-KR,ko;q=0.9"})
    counter = [0]

    list_page = fetch(session, LIST_URL, counter)
    detail_page = fetch(session, KNOWN_DETAIL_URL, counter)

    list_forms = parse_forms(list_page["text"], list_page["final_url"])
    detail_forms = parse_forms(detail_page["text"], detail_page["final_url"])
    detail_links = parse_detail_links(list_page["text"], list_page["final_url"])

    search_like_forms = []
    search_name_terms = ("search", "keyword", "key", "query", "word", "srch", "gosi", "gonggo", "notice", "page")
    for form in list_forms:
        names = [n.lower() for n in form["control_names"]]
        if any(any(term in name for term in search_name_terms) for name in names):
            search_like_forms.append(form)

    list_notice_numbers = sorted(set(NOTICE_NUMBER_PATTERN.findall(clean_text(list_page["text"]))))
    detail_notice_numbers = sorted(set(NOTICE_NUMBER_PATTERN.findall(clean_text(detail_page["text"]))))

    summary = {
        "official_notice_list_reachable": list_page["http_status"] == 200 and list_page["final_host"] == OFFICIAL_HOST,
        "official_notice_detail_reachable": detail_page["http_status"] == 200 and detail_page["final_host"] == OFFICIAL_HOST,
        "list_form_count": len(list_forms),
        "search_like_form_count": len(search_like_forms),
        "detail_link_count_sampled": len(detail_links),
        "list_notice_number_count": len(list_notice_numbers),
        "detail_notice_number_count": len(detail_notice_numbers),
        "reverse_lookup_contract_discovered": bool(search_like_forms and detail_links),
        "request_count": counter[0],
    }

    payload = {
        "step": "STEP 17-21-C-16-8-T-35-S73",
        "target_name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "source_family": SOURCE_FAMILY,
        "list_page": {k: v for k, v in list_page.items() if k != "text"},
        "known_detail_page": {k: v for k, v in detail_page.items() if k != "text"},
        "list_forms": list_forms,
        "search_like_forms": search_like_forms,
        "detail_forms": detail_forms,
        "detail_links_sample": detail_links,
        "list_notice_numbers_sample": list_notice_numbers[:30],
        "detail_notice_numbers": detail_notice_numbers,
        "summary": summary,
        "attachment_body_download_executed": False,
        "state_mutation_executed": False,
        "negative_evidence_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "runtime_registration_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    validations = {
        "official list reachable": summary["official_notice_list_reachable"],
        "official detail reachable": summary["official_notice_detail_reachable"],
        "request budget respected": counter[0] <= MAX_TOTAL_REQUESTS,
        "attachment download disabled": not payload["attachment_body_download_executed"],
        "state mutation disabled": not payload["state_mutation_executed"],
        "negative evidence disabled": not payload["negative_evidence_allowed"],
        "unsafe promotion leakage zero": not any(payload[k] for k in ["site_positive_allowed", "site_negative_allowed", "runtime_registration_allowed", "final_positive_promotion_allowed"]),
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\nSUMMARY")
    for k, v in summary.items():
        print(f"{k}: {v}")
    print("Search-like forms:")
    for form in search_like_forms:
        print(" ", {"method": form["method"], "action_url": form["action_url"], "control_names": form["control_names"]})
    print("Detail links sample:", detail_links[:5])
    print("Notice numbers sample:", list_notice_numbers[:10])
    print("Output:", OUTPUT_PATH)

    print("\nVALIDATION")
    for k, v in validations.items():
        print(f"{k}: {v}")
    print("all_pass:", all(validations.values()))
    if not all(validations.values()):
        raise AssertionError("S73 endpoint discovery validation failed")


if __name__ == "__main__":
    main()
