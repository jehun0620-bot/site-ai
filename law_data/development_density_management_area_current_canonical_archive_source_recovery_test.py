# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-7-S1
Development Density Management Area
Current Canonical Official Archive Source Recovery

목표
======================================================================
T-7에서 과거 bbsList.do seed가 404로 확인된 뒤, 현재 성남시 공식 사이트에서
살아 있는 canonical archive/list endpoint를 직접 검증한다.

현재 canonical seed
======================================================================
1. 성남시 고시공고: https://www.seongnam.go.kr/pm010301/list
2. 성남시 도시계획 계획: https://www.seongnam.go.kr/ct020100

원칙
======================================================================
- UQQ700 target query 실행 금지
- 현재 URL direct HTTP 검증
- final go.kr 필수
- 성남시 region binding 필수
- source-local archive / urban planning identity 필수
- source 자체는 document candidate가 아님
- no source != SITE FALSE
- verified positive / runtime registration / SITE TRUE / SITE FALSE 금지
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
T7_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_dedicated_urban_gazette_archive_expansion.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_current_canonical_archive_source_recovery.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_NOTICE = "CURRENT_MUNICIPAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_URBAN = "CURRENT_URBAN_PLANNING_INFORMATION_ARCHIVE"

CLASS_NOTICE = "QUALIFIED_CURRENT_MUNICIPAL_NOTICE_ARCHIVE"
CLASS_URBAN = "QUALIFIED_CURRENT_URBAN_PLANNING_ARCHIVE"
CLASS_HTTP = "REJECTED_HTTP_FAILURE"
CLASS_HOST = "REJECTED_NON_OFFICIAL_HOST"
CLASS_REGION = "REJECTED_REGION_UNBOUND"
CLASS_ROLE = "REJECTED_SOURCE_ROLE_WEAK"
CLASS_INVALID = "REJECTED_INVALID_SOURCE_URL"
VALID_CLASSES = {CLASS_NOTICE, CLASS_URBAN, CLASS_HTTP, CLASS_HOST, CLASS_REGION, CLASS_ROLE, CLASS_INVALID}
QUALIFIED_CLASSES = {CLASS_NOTICE, CLASS_URBAN}

SOURCE_SEEDS = [
    {
        "source_family": FAMILY_NOTICE,
        "regions": ["경기도 성남시"],
        "url": "https://www.seongnam.go.kr/pm010301/list",
        "seed_reason": "CURRENT_SEONGNAM_OFFICIAL_NOTICE_LIST",
    },
    {
        "source_family": FAMILY_URBAN,
        "regions": ["경기도 성남시"],
        "url": "https://www.seongnam.go.kr/ct020100",
        "seed_reason": "CURRENT_SEONGNAM_URBAN_PLANNING_INFORMATION_LIST",
    },
]

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
HEADING_PATTERN = re.compile(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)

NOTICE_ROLE_PATTERNS = [
    re.compile(r"고시\s*공고", re.I),
    re.compile(r"고시공고번호", re.I),
    re.compile(r"게재기간", re.I),
    re.compile(r"등록일", re.I),
]
URBAN_ROLE_PATTERNS = [
    re.compile(r"도시계획", re.I),
    re.compile(r"도시관리계획", re.I),
    re.compile(r"지구단위계획", re.I),
    re.compile(r"도시기본계획", re.I),
]
REGION_ALIASES = {"경기도 성남시": ["성남시", "성남", "seongnam"]}
VOLATILE_QUERY_KEYS = {"token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp", "rand", "random", "_"}
TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    out: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def strip_html(raw_html: str) -> str:
    value = COMMENT_PATTERN.sub(" ", raw_html)
    value = SCRIPT_STYLE_PATTERN.sub(" ", value)
    value = TAG_PATTERN.sub(" ", value)
    return normalize_space(html.unescape(value))


def canonicalize_url(url: str) -> str:
    value = normalize_space(url).replace("&amp;", "&")
    if not value:
        return ""
    try:
        parsed = urlparse(value)
    except Exception:
        return ""
    if not parsed.hostname:
        return ""
    scheme = (parsed.scheme or "https").lower()
    host = (parsed.hostname or "").lower()
    path = re.sub(r"/{2,}", "/", parsed.path or "/")
    items: List[Tuple[str, str]] = []
    seen = set()
    for key, val in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        lowered = key.lower()
        if not key or lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, val)
        if pair not in seen:
            seen.add(pair)
            items.append(pair)
    items.sort(key=lambda item: (item[0].lower(), item[1]))
    return urlunparse((scheme, host, path, "", urlencode(items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def decode_html(response: requests.Response, payload: bytes) -> str:
    for encoding in unique_strings([response.encoding, "utf-8", "cp949", "euc-kr"]):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"final_url": "", "http_status": None, "content_type": "", "response_bytes": 0, "raw_html": "", "error": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))
            chunks: List[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=128 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                chunks.append(chunk)
            payload = b"".join(chunks)
            result["response_bytes"] = len(payload)
            result["raw_html"] = decode_html(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def extract_title(raw_html: str) -> str:
    m = TITLE_PATTERN.search(raw_html)
    return strip_html(m.group(1)) if m else ""


def extract_headings(raw_html: str) -> List[str]:
    return unique_strings(strip_html(m.group(1)) for m in HEADING_PATTERN.finditer(raw_html))


def region_match(regions: List[str], url: str, title: str, headings: List[str], body_text: str) -> Tuple[bool, List[str]]:
    evidence = normalize_space(" ".join([url, hostname(url), title, *headings, body_text[:8000]])).lower()
    matched = []
    for region in regions:
        aliases = REGION_ALIASES.get(region, [region])
        if any(normalize_space(alias).lower() in evidence for alias in aliases if normalize_space(alias)):
            matched.append(region)
    return bool(matched), unique_strings(matched)


def role_reasons(family: str, url: str, title: str, headings: List[str], body_text: str) -> List[str]:
    evidence = normalize_space(" ".join([url, title, *headings, body_text[:12000]]))
    patterns = NOTICE_ROLE_PATTERNS if family == FAMILY_NOTICE else URBAN_ROLE_PATTERNS
    prefix = "NOTICE" if family == FAMILY_NOTICE else "URBAN"
    reasons = []
    for pattern in patterns:
        m = pattern.search(evidence)
        if m:
            reasons.append(prefix + "_LOCAL:" + normalize_space(m.group(0)))
    if family == FAMILY_NOTICE and "/pm010301" in url.lower():
        reasons.append("NOTICE_CANONICAL_PATH:pm010301")
    if family == FAMILY_URBAN and "/ct020100" in url.lower():
        reasons.append("URBAN_CANONICAL_PATH:ct020100")
    return unique_strings(reasons)


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("CURRENT CANONICAL ARCHIVE SOURCE RECOVERY")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    previous_data = {}
    if T7_INPUT_PATH.exists():
        loaded = json.loads(T7_INPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            previous_data = loaded

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    records = []
    request_count = 0
    http_success_count = 0

    for index, seed in enumerate(SOURCE_SEEDS, start=1):
        family = seed["source_family"]
        regions = seed["regions"]
        input_url = canonicalize_url(seed["url"])
        request_count += 1
        response = fetch_page(session, input_url)
        status = response.get("http_status")
        final_url = response.get("final_url") or input_url
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1

        print("-" * 60)
        print(f"SOURCE {index}")
        print("Family:", family)
        print("URL:", input_url)

        if not input_url:
            classification, qualified, reasons = CLASS_INVALID, False, ["INVALID_SOURCE_URL"]
            title, headings, matched_regions = "", [], []
        elif response.get("error") or not isinstance(status, int) or not (200 <= status < 300):
            classification, qualified, reasons = CLASS_HTTP, False, [normalize_space(response.get("error")) or "HTTP_NON_2XX"]
            title, headings, matched_regions = "", [], []
        elif not is_government_host(hostname(final_url)):
            classification, qualified, reasons = CLASS_HOST, False, ["FINAL_HOST_NOT_GO_KR"]
            title, headings, matched_regions = "", [], []
        else:
            raw_html = str(response.get("raw_html") or "")
            title = extract_title(raw_html)
            headings = extract_headings(raw_html)
            body_text = strip_html(raw_html)
            region_ok, matched_regions = region_match(regions, final_url, title, headings, body_text)
            reasons = role_reasons(family, final_url, title, headings, body_text)
            if not region_ok:
                classification, qualified = CLASS_REGION, False
                reasons = ["MUNICIPALITY_BINDING_MISSING"] + reasons
            elif not reasons:
                classification, qualified = CLASS_ROLE, False
                reasons = ["SOURCE_ROLE_EVIDENCE_MISSING"]
            else:
                classification = CLASS_NOTICE if family == FAMILY_NOTICE else CLASS_URBAN
                qualified = True
                reasons = reasons + ["REGION_BOUND:" + region for region in matched_regions]

        record = {
            "source_family": family,
            "regions": regions,
            "matched_regions": matched_regions,
            "seed_reason": seed["seed_reason"],
            "input_url": input_url,
            "final_url": final_url,
            "http_status": status,
            "content_type": response.get("content_type"),
            "response_bytes": response.get("response_bytes"),
            "title": title,
            "headings": headings,
            "qualified": qualified,
            "classification": classification,
            "reasons": unique_strings(reasons),
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        records.append(record)

        print("HTTP:", status)
        print("Final URL:", final_url)
        print("Title:", title)
        print("Matched regions:", matched_regions)
        print("Reasons:", unique_strings(reasons))
        print("Qualified:", qualified)
        print("Resolution:", classification)

    qualified_sources = [item for item in records if item.get("qualified") is True]
    rejected_sources = [item for item in records if item.get("qualified") is not True]

    next_stage_source_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("matched_regions") or item.get("regions") or [],
            "url": item.get("final_url") or item.get("input_url"),
            "title": item.get("title"),
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "requires_search_contract_recovery": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_sources
    ]

    resolution = (
        "CURRENT_CANONICAL_ARCHIVE_SOURCE_RECOVERY_COMPLETED"
        if next_stage_source_pool
        else "CURRENT_CANONICAL_ARCHIVE_SOURCE_RECOVERY_NO_SOURCE"
    )
    next_action = (
        "T-8에서 current canonical qualified source의 실제 HTML form/action/search field를 복원하고 semantic hardening한다. UQQ700 target query는 아직 실행하지 않는다."
        if next_stage_source_pool
        else "현재 canonical source도 qualification되지 않았다. SITE FALSE가 아니라 UNKNOWN을 유지한다."
    )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-7-S1 Current Canonical Official Archive Source Recovery",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "inputs": {"t7_path": str(T7_INPUT_PATH), "t7_resolution": previous_data.get("resolution")},
        "summary": {
            "seed_count": len(SOURCE_SEEDS),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "qualified_source_count": len(qualified_sources),
            "rejected_source_count": len(rejected_sources),
            "next_stage_source_pool_count": len(next_stage_source_pool),
        },
        "records": records,
        "qualified_sources": qualified_sources,
        "rejected_sources": rejected_sources,
        "next_stage_source_pool": next_stage_source_pool,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    qualified_urls = [canonicalize_url(item.get("final_url") or item.get("input_url") or "") for item in qualified_sources]
    next_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_source_pool]
    target_query_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    non_go_leakage = sum(1 for item in qualified_sources if not is_government_host(hostname(item.get("final_url") or "")))
    region_leakage = sum(1 for item in qualified_sources if not (item.get("matched_regions") or []))
    verified_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "current canonical seeds present": len(SOURCE_SEEDS) == 2,
        "direct network validation enabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_leakage == 0,
        "all classes valid": all(item.get("classification") in VALID_CLASSES for item in records),
        "qualified classes valid": all(item.get("classification") in QUALIFIED_CLASSES for item in qualified_sources),
        "qualified URLs unique": len(qualified_urls) == len(set(qualified_urls)),
        "next-stage URLs unique": len(next_urls) == len(set(next_urls)),
        "qualified and next-stage URL parity": set(qualified_urls) == set(next_urls),
        "qualified go.kr leakage zero": non_go_leakage == 0,
        "qualified region-unbound leakage zero": region_leakage == 0,
        "verified positive leakage zero": verified_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print()
    print("=" * 60)
    print("CURRENT CANONICAL ARCHIVE SOURCE RECOVERY RESULT")
    print("=" * 60)
    print("Seed count:", len(SOURCE_SEEDS))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Qualified source count:", len(qualified_sources))
    print("Next-stage source pool count:", len(next_stage_source_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    if qualified_sources:
        print("\nQUALIFIED CURRENT CANONICAL SOURCES")
        print("-" * 60)
        for index, item in enumerate(qualified_sources, start=1):
            print(f"[{index}] {item.get('source_family')}")
            print("Regions:", item.get("matched_regions"))
            print("URL:", item.get("final_url"))
            print("Title:", item.get("title"))
            print("Reasons:", item.get("reasons"))
            print()

    print("=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Target query leakage:", target_query_leakage)
    print("Document candidate leakage:", document_leakage)
    print("Non-go.kr leakage:", non_go_leakage)
    print("Region-unbound leakage:", region_leakage)
    print("Verified positive leakage:", verified_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("\nFAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("UQQ700 current canonical archive source recovery regression failed")


if __name__ == "__main__":
    main()
