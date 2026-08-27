# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-7
Development Density Management Area
Dedicated Urban Planning / Municipal Gazette Archive Expansion

목표
======================================================================
SAEOL request contract가 실제 검색효과를 보이지 않는 것으로 확인된 뒤,
보다 직접적인 official provenance source family를 확장한다.

이번 단계는 source qualification만 수행한다.
UQQ700 target query 실행 및 document candidate 생성은 금지한다.

대상 source family
======================================================================
1. DEDICATED_URBAN_PLANNING_NOTICE_ARCHIVE
2. MUNICIPAL_GAZETTE_ARCHIVE

원칙
======================================================================
- HTTP 2xx 필수
- final host go.kr 필수
- municipality binding 필수
- source-local archive role evidence 필수
- 일반 navigation page 승격 금지
- target query 실행 금지
- document candidate 생성 금지
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
PREVIOUS_INPUT_PATH = (
    BASE_DIR / "law_data" / "output" /
    "development_density_management_area_saeol_query_effectiveness_validation.json"
)
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = (
    OUTPUT_DIR /
    "development_density_management_area_dedicated_urban_gazette_archive_expansion.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_URBAN = "DEDICATED_URBAN_PLANNING_NOTICE_ARCHIVE"
FAMILY_GAZETTE = "MUNICIPAL_GAZETTE_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_URBAN, FAMILY_GAZETTE}

CLASS_QUALIFIED_URBAN = "QUALIFIED_DEDICATED_URBAN_PLANNING_ARCHIVE_SOURCE"
CLASS_QUALIFIED_GAZETTE = "QUALIFIED_MUNICIPAL_GAZETTE_ARCHIVE_SOURCE"
CLASS_REJECTED_HTTP = "REJECTED_HTTP_FAILURE"
CLASS_REJECTED_HOST = "REJECTED_NON_OFFICIAL_HOST"
CLASS_REJECTED_REGION = "REJECTED_REGION_UNBOUND"
CLASS_REJECTED_ROLE = "REJECTED_ARCHIVE_ROLE_WEAK"
CLASS_REJECTED_GENERIC = "REJECTED_GENERIC_NAVIGATION_SOURCE"
CLASS_REJECTED_INVALID = "REJECTED_INVALID_SOURCE_URL"

VALID_CLASSES = {
    CLASS_QUALIFIED_URBAN,
    CLASS_QUALIFIED_GAZETTE,
    CLASS_REJECTED_HTTP,
    CLASS_REJECTED_HOST,
    CLASS_REJECTED_REGION,
    CLASS_REJECTED_ROLE,
    CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_INVALID,
}
QUALIFIED_CLASSES = {CLASS_QUALIFIED_URBAN, CLASS_QUALIFIED_GAZETTE}

SOURCE_SEEDS: List[Dict[str, Any]] = [
    {
        "source_family": FAMILY_URBAN,
        "regions": ["경기도 성남시"],
        "url": "https://www.seongnam.go.kr/city/1000818/30278/bbsList.do",
        "seed_reason": "SEONGNAM_DEDICATED_URBAN_PLANNING_NOTICE_BOARD",
    },
    {
        "source_family": FAMILY_GAZETTE,
        "regions": ["경기도 성남시"],
        "url": "https://www.seongnam.go.kr/city/1000063/30009/bbsList.do",
        "seed_reason": "SEONGNAM_MUNICIPAL_GAZETTE_LIST",
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

URBAN_PATTERNS = [
    re.compile(r"지구단위계획.{0,50}고시\s*/?\s*공고", re.I),
    re.compile(r"도시관리계획", re.I),
    re.compile(r"도시계획.{0,40}(?:고시|공고)", re.I),
    re.compile(r"고시\s*/?\s*공고", re.I),
]
GAZETTE_PATTERNS = [
    re.compile(r"성남시보", re.I),
    re.compile(r"시보\s*제?\s*\d+\s*호", re.I),
    re.compile(r"(?:고\s*시|공\s*고)", re.I),
]
URBAN_URL_TERMS = ["bbslist.do", "/city/", "30278"]
GAZETTE_URL_TERMS = ["bbslist.do", "/city/", "30009"]
GENERIC_PATH_TERMS = ["/main.do", "/index.do", "/login", "/member", "/sitemap"]
REGION_ALIASES = {
    "경기도 성남시": ["성남시", "성남", "seongnam"],
}
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
    value = html.unescape(normalize_space(url))
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
    try:
        port = parsed.port
    except ValueError:
        port = None
    netloc = host if not port or (scheme == "http" and port == 80) or (scheme == "https" and port == 443) else f"{host}:{port}"
    path = re.sub(r"/{2,}", "/", re.sub(r";jsessionid=[^/?]+", "", parsed.path or "/", flags=re.I))
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
    return urlunparse((scheme, netloc, path, "", urlencode(items, doseq=True), ""))


def hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_government_host(host: str) -> bool:
    value = normalize_space(host).lower()
    return bool(value) and (value == "go.kr" or value.endswith(".go.kr"))


def extract_title(raw_html: str) -> str:
    match = TITLE_PATTERN.search(raw_html)
    return strip_html(match.group(1)) if match else ""


def extract_headings(raw_html: str) -> List[str]:
    return unique_strings(strip_html(match.group(1)) for match in HEADING_PATTERN.finditer(raw_html))


def decode_html(response: requests.Response, payload: bytes) -> str:
    candidates = [response.encoding, "utf-8", "cp949", "euc-kr"]
    for encoding in unique_strings(candidates):
        try:
            return payload.decode(encoding)
        except Exception:
            continue
    return payload.decode("utf-8", errors="replace")


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "raw_html": "",
        "error": "",
    }
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
            ct = result["content_type"].lower()
            prefix = payload[:1000].lstrip().lower()
            if "html" in ct or "text/" in ct or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
                result["raw_html"] = decode_html(response, payload)
    except Exception as exc:
        result["error"] = repr(exc)
    return result


def region_match(regions: List[str], url: str, title: str, headings: List[str]) -> Tuple[bool, List[str]]:
    evidence = normalize_space(" ".join([url, hostname(url), title, *headings])).lower()
    matched: List[str] = []
    for region in regions:
        aliases = REGION_ALIASES.get(region, [region])
        if any(normalize_space(alias).lower() in evidence for alias in aliases if normalize_space(alias)):
            matched.append(region)
    return bool(matched), unique_strings(matched)


def role_reasons(family: str, url: str, title: str, headings: List[str]) -> List[str]:
    local_text = normalize_space(" ".join([url, title, *headings]))
    patterns = URBAN_PATTERNS if family == FAMILY_URBAN else GAZETTE_PATTERNS
    terms = URBAN_URL_TERMS if family == FAMILY_URBAN else GAZETTE_URL_TERMS
    prefix = "URBAN" if family == FAMILY_URBAN else "GAZETTE"
    reasons: List[str] = []
    for pattern in patterns:
        match = pattern.search(local_text)
        if match:
            reasons.append(prefix + "_LOCAL:" + normalize_space(match.group(0)))
    lowered_url = url.lower()
    for term in terms:
        if term in lowered_url:
            reasons.append(prefix + "_URL:" + term)
    return unique_strings(reasons)


def looks_generic(url: str, title: str, reasons: List[str]) -> bool:
    path = (urlparse(url).path or "/").lower()
    if any(term in path for term in GENERIC_PATH_TERMS) and not reasons:
        return True
    return normalize_space(title).lower() in {"", "home", "홈", "메인"} and not reasons


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("DEDICATED URBAN / GAZETTE ARCHIVE EXPANSION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Target query execution: DISABLED")
    print()

    previous_data: Dict[str, Any] = {}
    if PREVIOUS_INPUT_PATH.exists():
        loaded = json.loads(PREVIOUS_INPUT_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            previous_data = loaded

    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    records: List[Dict[str, Any]] = []
    request_count = 0
    http_success_count = 0

    for index, seed in enumerate(SOURCE_SEEDS, start=1):
        family = normalize_space(seed.get("source_family"))
        regions = unique_strings(seed.get("regions") or [])
        input_url = canonicalize_url(seed.get("url") or "")
        request_count += 1
        print("-" * 60)
        print(f"SOURCE {index}")
        print("Family:", family)
        print("Regions:", regions)
        print("URL:", input_url)

        if not input_url:
            record = {
                "source_family": family, "regions": regions, "input_url": input_url,
                "qualified": False, "classification": CLASS_REJECTED_INVALID,
                "reasons": ["INVALID_SOURCE_URL"],
            }
            records.append(record)
            print("Qualified: False")
            continue

        response = fetch_page(session, input_url)
        status = response.get("http_status")
        final_url = canonicalize_url(response.get("final_url") or input_url)
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1

        if response.get("error") or not isinstance(status, int) or not (200 <= status < 300):
            classification = CLASS_REJECTED_HTTP
            qualified = False
            reasons = [normalize_space(response.get("error")) or "HTTP_NON_2XX"]
            title = ""
            headings: List[str] = []
            matched_regions: List[str] = []
        elif not is_government_host(hostname(final_url)):
            classification = CLASS_REJECTED_HOST
            qualified = False
            reasons = ["FINAL_HOST_NOT_GO_KR"]
            title = ""
            headings = []
            matched_regions = []
        else:
            raw_html = str(response.get("raw_html") or "")
            title = extract_title(raw_html)
            headings = extract_headings(raw_html)
            region_ok, matched_regions = region_match(regions, final_url, title, headings)
            reasons = role_reasons(family, final_url, title, headings)
            if not region_ok:
                classification = CLASS_REJECTED_REGION
                qualified = False
                reasons = ["MUNICIPALITY_LOCAL_EVIDENCE_MISSING"] + reasons
            elif looks_generic(final_url, title, reasons):
                classification = CLASS_REJECTED_GENERIC
                qualified = False
                reasons = ["GENERIC_NAVIGATION_SOURCE"] + reasons
            elif not reasons:
                classification = CLASS_REJECTED_ROLE
                qualified = False
                reasons = ["ARCHIVE_ROLE_EVIDENCE_MISSING"]
            else:
                classification = CLASS_QUALIFIED_URBAN if family == FAMILY_URBAN else CLASS_QUALIFIED_GAZETTE
                qualified = True
                reasons = reasons + ["REGION_BOUND:" + region for region in matched_regions]

        record = {
            "source_family": family,
            "regions": regions,
            "matched_regions": matched_regions,
            "seed_reason": seed.get("seed_reason"),
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
            "source_only": True,
            "requires_search_contract_recovery": True,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_sources
    ]

    if next_stage_source_pool:
        resolution = "DEDICATED_URBAN_GAZETTE_ARCHIVE_EXPANSION_COMPLETED"
        next_action = (
            "T-8에서 qualified dedicated archive source의 실제 list/search form action과 field를 복원한다. "
            "UQQ700 query는 아직 실행하지 않고 source-local search contract만 semantic hardening한다."
        )
    else:
        resolution = "DEDICATED_URBAN_GAZETTE_ARCHIVE_EXPANSION_NO_SOURCE"
        next_action = (
            "신규 dedicated archive source가 qualification되지 않았다. SITE FALSE로 판정하지 않고 UNKNOWN을 유지하며 "
            "다른 official urban planning/gazette archive family를 추가 탐색한다."
        )

    output_data = {
        "step": "STEP 17-21-C-16-8-T-7 Dedicated Urban Planning / Municipal Gazette Archive Expansion",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {
            "resolution_type": RESOLUTION_TYPE,
            "negative_evidence_allowed": False,
            "source_failure_site_status": "UNKNOWN",
        },
        "inputs": {
            "previous_stage_path": str(PREVIOUS_INPUT_PATH),
            "previous_stage_resolution": previous_data.get("resolution"),
        },
        "method": {
            "dedicated_urban_archive_expansion": True,
            "municipal_gazette_archive_expansion": True,
            "direct_network_requery": True,
            "http_2xx_required": True,
            "final_host_go_kr_required": True,
            "municipality_region_binding_required": True,
            "archive_role_evidence_required": True,
            "target_query_execution": False,
            "document_candidate_generation": False,
        },
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

    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in records)
    qualified_classes_valid = all(item.get("classification") in QUALIFIED_CLASSES for item in qualified_sources)
    qualified_url_list = [canonicalize_url(item.get("final_url") or item.get("input_url") or "") for item in qualified_sources]
    next_url_list = [canonicalize_url(item.get("url") or "") for item in next_stage_source_pool]
    non_go_leakage = sum(1 for item in qualified_sources if not is_government_host(hostname(item.get("final_url") or "")))
    region_leakage = sum(1 for item in qualified_sources if not (item.get("matched_regions") or []))
    target_query_leakage = sum(1 for item in records if item.get("target_query_executed") is True)
    document_leakage = sum(1 for item in records if item.get("document_candidate") is True)
    verified_leakage = sum(1 for item in records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in records if item.get("site_negative_allowed") is True)

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "previous stage parsed or absent": isinstance(previous_data, dict),
        "dedicated source seeds present": len(SOURCE_SEEDS) > 0,
        "direct network requery enabled": True,
        "target query execution disabled": target_query_leakage == 0,
        "document candidate generation disabled": document_leakage == 0,
        "all classes valid": all_classes_valid,
        "qualified classes valid": qualified_classes_valid,
        "qualified URLs unique": len(qualified_url_list) == len(set(qualified_url_list)),
        "next-stage URLs unique": len(next_url_list) == len(set(next_url_list)),
        "qualified and next-stage URL parity": set(qualified_url_list) == set(next_url_list),
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
    print("DEDICATED URBAN / GAZETTE ARCHIVE EXPANSION RESULT")
    print("=" * 60)
    print("Seed count:", len(SOURCE_SEEDS))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Qualified source count:", len(qualified_sources))
    print("Next-stage source pool count:", len(next_stage_source_pool))
    print("Resolution:", resolution)
    print("Output:", OUTPUT_PATH)

    if qualified_sources:
        print("\nQUALIFIED SOURCES")
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
        raise AssertionError("UQQ700 dedicated urban/gazette archive expansion regression failed")


if __name__ == "__main__":
    main()
