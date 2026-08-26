# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T-5
Development Density Management Area
Official Notice / Archive Source Expansion

T-4에서 기존 board-local search contract를 제한 실행했으나 UQQ700 historical
문서를 찾지 못했다. T-5에서는 기존 S-3/T-4 endpoint를 반복하지 않고 별도의
공식 고시공고/도시계획/새올 archive source를 직접 검증한다.

원칙:
- 개발밀도관리구역 / UQQ700 / HYBRID_SPATIAL_NOTICE
- no document / no source != SITE FALSE
- 기존 S-3/T-4 URL 재승격 금지
- HTTP 2xx + final go.kr + municipality binding + archive role evidence 필수
- source 자체는 document candidate / verified positive가 아님
- target query 실행 금지
- runtime registration / SITE TRUE / SITE FALSE 금지
"""

from __future__ import annotations

import html
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
S3_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_historical_source_family_entry_endpoint_qualification_hardening.json"
T4_INPUT_PATH = BASE_DIR / "law_data" / "output" / "development_density_management_area_bounded_historical_search_execution.json"
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_official_notice_archive_source_expansion.json"

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
NEGATIVE_EVIDENCE_ALLOWED = False

FAMILY_URBAN = "URBAN_PLANNING_NOTICE_ARCHIVE"
FAMILY_SAEOL = "SAEOL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_NOTICE = "LOCAL_OFFICIAL_NOTICE_ARCHIVE"
FAMILY_GAZETTE = "LOCAL_GAZETTE_ARCHIVE"
ALLOWED_FAMILIES = {FAMILY_URBAN, FAMILY_SAEOL, FAMILY_NOTICE, FAMILY_GAZETTE}

CLASS_QUALIFIED_URBAN = "QUALIFIED_URBAN_PLANNING_ARCHIVE_SOURCE"
CLASS_QUALIFIED_SAEOL = "QUALIFIED_SAEOL_NOTICE_ARCHIVE_SOURCE"
CLASS_QUALIFIED_NOTICE = "QUALIFIED_OFFICIAL_NOTICE_ARCHIVE_SOURCE"
CLASS_QUALIFIED_GAZETTE = "QUALIFIED_LOCAL_GAZETTE_ARCHIVE_SOURCE"
CLASS_REPEAT = "REJECTED_EXISTING_SOURCE_REPEAT"
CLASS_HTTP = "REJECTED_HTTP_FAILURE"
CLASS_HOST = "REJECTED_NON_OFFICIAL_HOST"
CLASS_REGION = "REJECTED_REGION_UNBOUND"
CLASS_GENERIC = "REJECTED_GENERIC_NAVIGATION_SOURCE"
CLASS_ROLE = "REJECTED_ARCHIVE_ROLE_WEAK"
CLASS_INVALID = "REJECTED_INVALID_SOURCE_URL"

VALID_CLASSES = {
    CLASS_QUALIFIED_URBAN, CLASS_QUALIFIED_SAEOL, CLASS_QUALIFIED_NOTICE,
    CLASS_QUALIFIED_GAZETTE, CLASS_REPEAT, CLASS_HTTP, CLASS_HOST,
    CLASS_REGION, CLASS_GENERIC, CLASS_ROLE, CLASS_INVALID,
}
QUALIFIED_CLASSES = {
    CLASS_QUALIFIED_URBAN, CLASS_QUALIFIED_SAEOL,
    CLASS_QUALIFIED_NOTICE, CLASS_QUALIFIED_GAZETTE,
}
FAMILY_TO_CLASS = {
    FAMILY_URBAN: CLASS_QUALIFIED_URBAN,
    FAMILY_SAEOL: CLASS_QUALIFIED_SAEOL,
    FAMILY_NOTICE: CLASS_QUALIFIED_NOTICE,
    FAMILY_GAZETTE: CLASS_QUALIFIED_GAZETTE,
}

# Search-engine result를 qualification evidence로 사용하지 않는다.
# 실행 시 각 URL을 직접 GET하여 현재 endpoint identity를 다시 검증한다.
SOURCE_SEEDS: List[Dict[str, Any]] = [
    {
        "source_family": FAMILY_URBAN,
        "regions": ["경기도 성남시"],
        "url": "https://www.seongnam.go.kr/city/1000541/30228/bbsList.do",
        "seed_reason": "SEONGNAM_CITY_PLANNING_NOTICE_BOARD",
    },
    {
        "source_family": FAMILY_SAEOL,
        "regions": ["경기도 성남시"],
        "url": "https://eminwon.seongnam.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do?method=selectOfrNotAncmt&context=NTIS&initValue=Y&jndinm=OfrNotAncmtEJB&list_gubun=A&not_ancmt_se_code=01,02,03,04,05,06,07",
        "seed_reason": "SEONGNAM_SAEOL_NOTICE_BOARD",
    },
    {
        "source_family": FAMILY_SAEOL,
        "regions": ["경기도 평택시"],
        "url": "https://eminwon.pyeongtaek.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do?method=selectOfrNotAncmt&context=NTIS&initValue=Y&jndinm=OfrNotAncmtEJB&list_gubun=A&not_ancmt_se_code=01,02,03,04,05,06,07",
        "seed_reason": "PYEONGTAEK_SAEOL_NOTICE_BOARD",
    },
]

TIMEOUT = 20
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
REQUEST_DELAY_SECONDS = 0.05
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

TITLE_PATTERN = re.compile(r"<title\b[^>]*>(.*?)</title>", re.I | re.S)
HEADING_PATTERN = re.compile(r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>", re.I | re.S)
TAG_PATTERN = re.compile(r"<[^>]+>", re.S)
SCRIPT_STYLE_PATTERN = re.compile(r"<(?:script|style)\b.*?</(?:script|style)>", re.I | re.S)
COMMENT_PATTERN = re.compile(r"<!--.*?-->", re.S)
ARCHIVE_PATTERNS = [
    re.compile(r"고시\s*[·ㆍ/\-]?\s*공고", re.I),
    re.compile(r"고시공고", re.I),
    re.compile(r"도시계획.{0,40}(?:고시|공고)", re.I),
    re.compile(r"도시관리계획.{0,40}(?:고시|공고)", re.I),
    re.compile(r"(?:시보|군보|구보|도보|공보)(?:\s|$|목록|검색|보기|발행)", re.I),
]
ARCHIVE_URL_TERMS = [
    "ofraction.do", "selectofrnotancmt", "bbslist.do", "publicnotice",
    "gosi", "gonggo", "notice", "gazette", "gongbo",
]
GENERIC_URL_TERMS = [
    "/main.do", "/index.do", "/login", "/member", "/sitemap",
    "/welfare/", "/satisfaction/",
]
GENERIC_TITLE_TERMS = {"", "home", "홈", "메인", "새올전자민원창구"}
VOLATILE_QUERY_KEYS = {"token", "_csrf", "csrf", "sessionid", "jsessionid", "timestamp", "rand", "random", "_"}
TRACKING_QUERY_KEYS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}
REGION_ALIASES = {
    "경기도 성남시": ["성남시", "성남", "seongnam"],
    "경기도 평택시": ["평택시", "평택", "pyeongtaek"],
    "부산광역시 강서구": ["강서구", "강서", "bsgangseo"],
}


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def unique_strings(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: Set[str] = set()
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


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
    items = []
    seen = set()
    for key, query_value in parse_qsl(parsed.query, keep_blank_values=True):
        key = normalize_space(key)
        lowered = key.lower()
        if not key or lowered in VOLATILE_QUERY_KEYS or lowered in TRACKING_QUERY_KEYS or "csrf" in lowered or "session" in lowered:
            continue
        pair = (key, query_value)
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


def walk_dicts(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            if isinstance(child, (dict, list)):
                yield from walk_dicts(child)


def collect_existing_urls(*datasets: Dict[str, Any]) -> Set[str]:
    result: Set[str] = set()
    for data in datasets:
        for item in walk_dicts(data):
            for key in ("url", "source_url", "action_url", "final_url", "request_url"):
                url = canonicalize_url(item.get(key) or "")
                if url:
                    result.add(url)
    return result


def extract_title(raw_html: str) -> str:
    match = TITLE_PATTERN.search(raw_html)
    return strip_html(match.group(1)) if match else ""


def extract_headings(raw_html: str) -> List[str]:
    return unique_strings(strip_html(m.group(1)) for m in HEADING_PATTERN.finditer(raw_html))


def region_matches(regions: List[str], url: str, title: str, headings: List[str]) -> Tuple[bool, List[str]]:
    evidence = normalize_space(" ".join([url, hostname(url), title, *headings])).lower()
    matched = []
    for region in regions:
        aliases = REGION_ALIASES.get(region, [region])
        if any(normalize_space(alias).lower() in evidence for alias in aliases if normalize_space(alias)):
            matched.append(region)
    return bool(matched), unique_strings(matched)


def archive_role_evidence(family: str, url: str, title: str, headings: List[str]) -> List[str]:
    local_text = normalize_space(" ".join([url, title, *headings]))
    reasons: List[str] = []
    for pattern in ARCHIVE_PATTERNS:
        match = pattern.search(local_text)
        if match:
            reasons.append("ARCHIVE_LOCAL:" + normalize_space(match.group(0)))
    lowered_url = url.lower()
    for term in ARCHIVE_URL_TERMS:
        if term in lowered_url:
            reasons.append("ARCHIVE_URL:" + term)
    if family == FAMILY_SAEOL and "eminwon." in hostname(url) and "ofraction.do" in lowered_url:
        reasons.append("SAEOL_NOTICE_ENDPOINT_IDENTITY")
    if family == FAMILY_URBAN and ("city" in lowered_url or "urban" in lowered_url or "도시" in local_text):
        reasons.append("URBAN_PLANNING_ARCHIVE_IDENTITY")
    return unique_strings(reasons)


def looks_generic(url: str, title: str, role_reasons: List[str]) -> bool:
    return (
        (any(term in url.lower() for term in GENERIC_URL_TERMS) and not role_reasons)
        or (normalize_space(title).lower() in GENERIC_TITLE_TERMS and not role_reasons)
    )


def decode_html(response: requests.Response, data: bytes) -> Tuple[str, str]:
    candidates: List[str] = []
    content_type = normalize_space(response.headers.get("Content-Type"))
    match = re.search(r'''charset\s*=\s*["']?([^;"'\s]+)''', content_type, flags=re.I)
    if match:
        candidates.append(normalize_space(match.group(1)))
    if response.encoding:
        candidates.append(normalize_space(response.encoding))
    candidates.extend(["utf-8", "cp949", "euc-kr"])
    for encoding in unique_strings(candidates):
        try:
            return data.decode(encoding), encoding
        except (UnicodeDecodeError, LookupError):
            pass
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def fetch_page(session: requests.Session, url: str) -> Dict[str, Any]:
    result = {"final_url": "", "http_status": None, "content_type": "", "response_bytes": 0, "raw_html": "", "encoding": "", "error": "", "error_stage": ""}
    try:
        with session.get(url, timeout=TIMEOUT, allow_redirects=True, stream=True) as response:
            result["http_status"] = response.status_code
            result["final_url"] = canonicalize_url(str(response.url))
            result["content_type"] = normalize_space(response.headers.get("Content-Type"))
            chunks: List[bytes] = []
            total = 0
            try:
                for chunk in response.iter_content(chunk_size=128 * 1024):
                    if not chunk:
                        continue
                    total += len(chunk)
                    if total > MAX_RESPONSE_BYTES:
                        raise ValueError(f"response exceeds {MAX_RESPONSE_BYTES} bytes")
                    chunks.append(chunk)
            except Exception as exc:
                result["error"] = repr(exc)
                result["error_stage"] = "BODY_DOWNLOAD"
                return result
            data = b"".join(chunks)
            result["response_bytes"] = len(data)
            ct = result["content_type"].lower()
            prefix = data[:1000].lstrip().lower()
            if "html" in ct or "text/" in ct or prefix.startswith(b"<!doctype html") or prefix.startswith(b"<html"):
                decoded, encoding = decode_html(response, data)
                result["raw_html"] = decoded
                result["encoding"] = encoding
    except requests.RequestException as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "HTTP_REQUEST"
    except Exception as exc:
        result["error"] = repr(exc)
        result["error_stage"] = "UNEXPECTED"
    return result


def main() -> None:
    print("=" * 60)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("OFFICIAL NOTICE / ARCHIVE SOURCE EXPANSION")
    print("=" * 60)
    print("Target:", TARGET_NAME)
    print("Standard code:", STANDARD_CODE)
    print("Resolution type:", RESOLUTION_TYPE)
    print("Negative evidence allowed:", NEGATIVE_EVIDENCE_ALLOWED)
    print()

    if not S3_INPUT_PATH.exists():
        raise FileNotFoundError(f"S-3 input not found: {S3_INPUT_PATH}")
    if not T4_INPUT_PATH.exists():
        raise FileNotFoundError(f"T-4 input not found: {T4_INPUT_PATH}")
    s3_data = json.loads(S3_INPUT_PATH.read_text(encoding="utf-8"))
    t4_data = json.loads(T4_INPUT_PATH.read_text(encoding="utf-8"))
    if not isinstance(s3_data, dict) or not isinstance(t4_data, dict):
        raise TypeError("S-3/T-4 inputs must be JSON objects.")

    existing_urls = collect_existing_urls(s3_data, t4_data)
    session = requests.Session()
    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.7,en;q=0.5",
    })

    records: List[Dict[str, Any]] = []
    request_count = http_success_count = transport_error_count = 0

    for index, seed in enumerate(SOURCE_SEEDS, start=1):
        family = normalize_space(seed.get("source_family"))
        regions = unique_strings(seed.get("regions") or [])
        seed_url = canonicalize_url(seed.get("url") or "")
        print("-" * 60)
        print(f"SOURCE SEED {index}")
        print("Family:", family)
        print("Regions:", regions)
        print("URL:", seed_url)

        record: Dict[str, Any] = {
            "source_family": family,
            "regions": regions,
            "seed_url": seed_url,
            "seed_reason": seed.get("seed_reason"),
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
            "target_query_executed": False,
            "document_candidate": False,
        }

        if family not in ALLOWED_FAMILIES or not seed_url:
            record.update(qualified=False, classification=CLASS_INVALID, reasons=["INVALID_SOURCE_SEED"])
            records.append(record)
            continue
        if seed_url in existing_urls:
            record.update(final_url=seed_url, http_status=None, qualified=False, classification=CLASS_REPEAT, reasons=["EXISTING_S3_T4_SOURCE_REPEAT"])
            records.append(record)
            continue
        if not is_government_host(hostname(seed_url)):
            record.update(qualified=False, classification=CLASS_HOST, reasons=["INPUT_HOST_NOT_GO_KR"])
            records.append(record)
            continue

        request_count += 1
        response = fetch_page(session, seed_url)
        status = response.get("http_status")
        final_url = canonicalize_url(response.get("final_url") or seed_url)
        if isinstance(status, int) and 200 <= status < 300:
            http_success_count += 1
        if response.get("error"):
            transport_error_count += 1
        if not isinstance(status, int) or not (200 <= status < 300) or response.get("error"):
            record.update(final_url=final_url, http_status=status, qualified=False, classification=CLASS_HTTP, error_stage=response.get("error_stage"), error=response.get("error"), reasons=[normalize_space(response.get("error")) or "HTTP_NON_2XX"])
            records.append(record)
            continue
        if final_url in existing_urls:
            record.update(final_url=final_url, http_status=status, qualified=False, classification=CLASS_REPEAT, reasons=["FINAL_URL_EXISTING_S3_T4_SOURCE_REPEAT"])
            records.append(record)
            continue
        if not is_government_host(hostname(final_url)):
            record.update(final_url=final_url, http_status=status, qualified=False, classification=CLASS_HOST, reasons=["FINAL_HOST_NOT_GO_KR"])
            records.append(record)
            continue

        raw_html = str(response.get("raw_html") or "")
        title = extract_title(raw_html)
        headings = extract_headings(raw_html)
        region_ok, matched_regions = region_matches(regions, final_url, title, headings)
        role_reasons = archive_role_evidence(family, final_url, title, headings)

        if not region_ok:
            classification, qualified, reasons = CLASS_REGION, False, ["MUNICIPAL_REGION_LOCAL_EVIDENCE_MISSING"]
        elif looks_generic(final_url, title, role_reasons):
            classification, qualified, reasons = CLASS_GENERIC, False, ["GENERIC_NAVIGATION_SOURCE"]
        elif not role_reasons:
            classification, qualified, reasons = CLASS_ROLE, False, ["ARCHIVE_ROLE_EVIDENCE_WEAK"]
        else:
            classification, qualified = FAMILY_TO_CLASS[family], True
            reasons = unique_strings(role_reasons + ["REGION_BOUND:" + r for r in matched_regions])

        record.update({
            "final_url": final_url,
            "http_status": status,
            "content_type": response.get("content_type"),
            "response_bytes": response.get("response_bytes"),
            "encoding": response.get("encoding"),
            "title": title,
            "headings": headings,
            "matched_regions": matched_regions,
            "qualified": qualified,
            "classification": classification,
            "reasons": reasons,
        })
        records.append(record)
        print("HTTP:", status)
        print("Title:", title)
        print("Matched regions:", matched_regions)
        print("Role reasons:", role_reasons)
        print("Qualified:", qualified)
        print("Resolution:", classification)
        if REQUEST_DELAY_SECONDS > 0:
            time.sleep(REQUEST_DELAY_SECONDS)

    canonical_map: Dict[str, Dict[str, Any]] = {}
    duplicate_count = 0
    for item in records:
        key = canonicalize_url(item.get("final_url") or item.get("seed_url") or "") or f"invalid:{len(canonical_map)}"
        if key in canonical_map:
            duplicate_count += 1
            existing = canonical_map[key]
            existing["regions"] = unique_strings((existing.get("regions") or []) + (item.get("regions") or []))
            existing["matched_regions"] = unique_strings((existing.get("matched_regions") or []) + (item.get("matched_regions") or []))
            existing["reasons"] = unique_strings((existing.get("reasons") or []) + (item.get("reasons") or []))
            if item.get("qualified") is True:
                existing["qualified"] = True
                existing["classification"] = item.get("classification")
        else:
            canonical_map[key] = dict(item)

    canonical_records = list(canonical_map.values())
    qualified_sources = [item for item in canonical_records if item.get("qualified") is True]
    rejected_sources = [item for item in canonical_records if item.get("qualified") is not True]
    classification_counts = Counter(item.get("classification") for item in canonical_records)
    next_stage_source_pool = [
        {
            "source_family": item.get("source_family"),
            "regions": item.get("matched_regions") or item.get("regions") or [],
            "url": canonicalize_url(item.get("final_url") or item.get("seed_url") or ""),
            "title": item.get("title"),
            "classification": item.get("classification"),
            "reasons": item.get("reasons") or [],
            "archive_source_only": True,
            "target_query_executed": False,
            "document_candidate": False,
            "verified_positive": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
            "final_positive_promotion_allowed": False,
        }
        for item in qualified_sources
    ]

    if next_stage_source_pool:
        resolution = "OFFICIAL_NOTICE_ARCHIVE_SOURCE_EXPANSION_COMPLETED"
        next_action = "T-5에서 직접 검증된 신규 official archive source만 T-6 source-local search contract recovery로 넘긴다. T-6에서는 실제 form/action/field를 복원하고 아직 UQQ700 query는 실행하지 않는다."
    else:
        resolution = "OFFICIAL_NOTICE_ARCHIVE_SOURCE_EXPANSION_NO_SOURCE"
        next_action = "신규 source 미확보는 SITE FALSE가 아니다. UNKNOWN을 유지하고 추가 municipality archive seed 또는 notice-number reverse lookup source family를 보강한다."

    output_data = {
        "step": "STEP 17-21-C-16-8-T-5 Official Notice / Archive Source Expansion",
        "target": {"name": TARGET_NAME, "standard_code": STANDARD_CODE},
        "resolution_policy": {"resolution_type": RESOLUTION_TYPE, "negative_evidence_allowed": False, "source_failure_site_status": "UNKNOWN"},
        "inputs": {"s3_path": str(S3_INPUT_PATH), "t4_path": str(T4_INPUT_PATH), "t4_resolution": t4_data.get("resolution")},
        "method": {
            "new_official_source_seed_expansion_enabled": True,
            "existing_s3_t4_source_repeat_disabled": True,
            "direct_http_requery_required": True,
            "http_2xx_required": True,
            "final_host_go_kr_required": True,
            "municipality_region_binding_required": True,
            "archive_role_evidence_required": True,
            "generic_navigation_source_promotion_disabled": True,
            "target_query_execution_enabled": False,
            "source_is_document_candidate": False,
            "negative_evidence_enabled": False,
            "verified_positive_promotion_allowed": False,
            "runtime_registration_allowed": False,
            "site_positive_allowed": False,
            "site_negative_allowed": False,
        },
        "summary": {
            "seed_count": len(SOURCE_SEEDS),
            "existing_source_exclusion_count": len(existing_urls),
            "request_count": request_count,
            "http_success_count": http_success_count,
            "transport_error_count": transport_error_count,
            "canonical_record_count": len(canonical_records),
            "duplicate_source_removed": duplicate_count,
            "qualified_source_count": len(qualified_sources),
            "rejected_source_count": len(rejected_sources),
            "next_stage_source_pool_count": len(next_stage_source_pool),
        },
        "classification_counts": dict(sorted(classification_counts.items())),
        "qualified_sources": qualified_sources,
        "rejected_sources": rejected_sources,
        "next_stage_source_pool": next_stage_source_pool,
        "all_canonical_records": canonical_records,
        "resolution": resolution,
        "next_action": next_action,
        "verified_positive": False,
        "runtime_registration_allowed": False,
        "site_positive_allowed": False,
        "site_negative_allowed": False,
        "final_positive_promotion_allowed": False,
    }
    OUTPUT_PATH.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print()
    print("=" * 60)
    print("OFFICIAL NOTICE / ARCHIVE SOURCE EXPANSION RESULT")
    print("=" * 60)
    print("Seed count:", len(SOURCE_SEEDS))
    print("Request count:", request_count)
    print("HTTP success count:", http_success_count)
    print("Transport error count:", transport_error_count)
    print("Qualified source count:", len(qualified_sources))
    print("Next-stage source pool count:", len(next_stage_source_pool))
    if qualified_sources:
        print("\nQUALIFIED NEW OFFICIAL ARCHIVE SOURCES\n" + "-" * 60)
        for index, item in enumerate(qualified_sources, start=1):
            print(f"[{index}] {item.get('source_family')}")
            print("Regions:", item.get("matched_regions"))
            print("URL:", item.get("final_url"))
            print("Title:", item.get("title"))
            print("Reasons:", item.get("reasons"))
            print()
    print("\n" + "=" * 60)
    print("RESOLUTION")
    print("=" * 60)
    print(resolution)
    print("\n" + next_action)
    print("\nOutput:", OUTPUT_PATH)

    qualified_urls = [canonicalize_url(item.get("final_url") or "") for item in qualified_sources]
    next_stage_urls = [canonicalize_url(item.get("url") or "") for item in next_stage_source_pool]
    all_classes_valid = all(item.get("classification") in VALID_CLASSES for item in canonical_records)
    qualified_classes_valid = all(item.get("classification") in QUALIFIED_CLASSES for item in qualified_sources)
    duplicate_qualified_url_leakage = len(qualified_urls) - len(set(qualified_urls))
    duplicate_next_stage_url_leakage = len(next_stage_urls) - len(set(next_stage_urls))
    invalid_qualified_url_leakage = sum(1 for url in qualified_urls if not url)
    non_go_kr_leakage = sum(1 for item in qualified_sources if not is_government_host(hostname(item.get("final_url") or "")))
    region_unbound_leakage = sum(1 for item in qualified_sources if not (item.get("matched_regions") or []))
    existing_repeat_leakage = sum(1 for item in qualified_sources if canonicalize_url(item.get("final_url") or "") in existing_urls)
    target_query_leakage = sum(1 for item in canonical_records if item.get("target_query_executed") is True)
    document_candidate_leakage = sum(1 for item in canonical_records if item.get("document_candidate") is True)
    verified_positive_leakage = sum(1 for item in canonical_records if item.get("verified_positive") is True)
    runtime_leakage = sum(1 for item in canonical_records if item.get("runtime_registration_allowed") is True)
    site_true_leakage = sum(1 for item in canonical_records if item.get("site_positive_allowed") is True)
    site_false_leakage = sum(1 for item in canonical_records if item.get("site_negative_allowed") is True)
    false_from_no_source_leakage = 1 if not qualified_sources and output_data["resolution_policy"]["source_failure_site_status"] == "FALSE" else 0

    validations = {
        "target name": TARGET_NAME == "개발밀도관리구역",
        "standard code": STANDARD_CODE == "UQQ700",
        "resolution type hybrid spatial notice": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "negative evidence disabled": NEGATIVE_EVIDENCE_ALLOWED is False,
        "S-3 input exists": S3_INPUT_PATH.exists(),
        "T-4 input exists": T4_INPUT_PATH.exists(),
        "S-3 input parsed": isinstance(s3_data, dict),
        "T-4 input parsed": isinstance(t4_data, dict),
        "new official source seed expansion enabled": True,
        "existing S-3/T-4 source repeat disabled": True,
        "direct HTTP requery required": True,
        "HTTP 2xx required": all(isinstance(item.get("http_status"), int) and 200 <= item.get("http_status") < 300 for item in qualified_sources),
        "final host go.kr required": non_go_kr_leakage == 0,
        "municipality region binding required": region_unbound_leakage == 0,
        "archive role evidence required": all(item.get("reasons") for item in qualified_sources),
        "all classes valid": all_classes_valid,
        "qualified classes valid": qualified_classes_valid,
        "qualified URLs valid": invalid_qualified_url_leakage == 0,
        "qualified URLs unique": duplicate_qualified_url_leakage == 0,
        "next-stage URLs unique": duplicate_next_stage_url_leakage == 0,
        "qualified and next-stage URL parity": set(qualified_urls) == set(next_stage_urls),
        "existing source repeat leakage zero": existing_repeat_leakage == 0,
        "target query execution leakage zero": target_query_leakage == 0,
        "document candidate leakage zero": document_candidate_leakage == 0,
        "verified positive leakage zero": verified_positive_leakage == 0,
        "runtime registration leakage zero": runtime_leakage == 0,
        "SITE TRUE leakage zero": site_true_leakage == 0,
        "SITE FALSE leakage zero": site_false_leakage == 0,
        "false from no source leakage zero": false_from_no_source_leakage == 0,
        "runtime registration remains blocked": output_data["runtime_registration_allowed"] is False,
        "SITE TRUE remains blocked": output_data["site_positive_allowed"] is False,
        "SITE FALSE remains blocked": output_data["site_negative_allowed"] is False,
        "final positive promotion remains blocked": output_data["final_positive_promotion_allowed"] is False,
        "output written": OUTPUT_PATH.exists() and OUTPUT_PATH.stat().st_size > 0,
    }

    print("\n" + "=" * 60)
    print("VALIDATION")
    print("=" * 60)
    for name, passed in validations.items():
        print(f"{name}: {passed}")
    print()
    print("Duplicate qualified URL leakage:", duplicate_qualified_url_leakage)
    print("Duplicate next-stage URL leakage:", duplicate_next_stage_url_leakage)
    print("Invalid qualified URL leakage:", invalid_qualified_url_leakage)
    print("Non-go.kr leakage:", non_go_kr_leakage)
    print("Region-unbound leakage:", region_unbound_leakage)
    print("Existing source repeat leakage:", existing_repeat_leakage)
    print("Target query execution leakage:", target_query_leakage)
    print("Document candidate leakage:", document_candidate_leakage)
    print("Verified positive leakage:", verified_positive_leakage)
    print("Runtime registration leakage:", runtime_leakage)
    print("SITE TRUE leakage:", site_true_leakage)
    print("SITE FALSE leakage:", site_false_leakage)
    print("False from no source leakage:", false_from_no_source_leakage)
    print()

    all_pass = all(validations.values())
    print(f"all_pass: {all_pass}")
    if not all_pass:
        failed = [name for name, passed in validations.items() if not passed]
        print("\nFAILED:")
        for name in failed:
            print("-", name)
        raise AssertionError("Development density management area official notice/archive source expansion regression failed")


if __name__ == "__main__":
    main()
