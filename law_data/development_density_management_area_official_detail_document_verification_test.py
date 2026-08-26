# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-J
Development Density Management Area
Official Detail Document Verification

목표
======================================================================
I 단계에서 확보한 detail seed 후보를 실제 원문 기준으로 재검증한다.

입력
======================================================================
law_data/output/
development_density_management_area_official_board_search_form_discovery.json

핵심 정책
======================================================================
1. 검색 결과 / 통합검색 / 여행검색 / file preview 화면은 VERIFIED_POSITIVE 금지
2. 본문에 "개발밀도관리구역" target이 실제 존재해야 함
3. target 주변 local context에 지정/변경/해제/고시/도시관리계획/결정/
   지형도면 중 하나 이상의 강한 행정 문맥이 있어야 함
4. target 문자열이 URL query에만 존재하고 본문에 없으면 false positive
5. 일반 도시계획위원회 / 도시계획조례 / unrelated 도시관리계획 문서는 제외
6. runtime 등록 및 SITE FALSE 판단은 계속 차단
"""

from __future__ import annotations

import html
import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse

import requests


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "development_density_management_area_official_board_search_form_discovery.json"
)

OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_official_detail_document_verification.json"
)

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

REQUEST_TIMEOUT = 20
REQUEST_SLEEP = 0.2
MAX_CONTENT_LENGTH = 2_000_000
LOCAL_CONTEXT_RADIUS = 500

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
}

STRONG_LOCAL_TERMS = [
    "고시",
    "고시문",
    "지정",
    "변경",
    "해제",
    "도시관리계획",
    "도시계획",
    "결정",
    "지형도면",
    "용적률",
    "기반시설",
]

DISALLOWED_PAGE_HINTS = [
    "/search",
    "search.",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
    "tourresult",
    "filepreview",
]

GENERAL_FALSE_POSITIVE_TERMS = [
    "도시계획위원회 개최 결과",
    "도시계획위원회」 개최 결과",
    "도시계획위원회 개최결과",
    "도시계획조례개정",
    "도시계획 조례 개정",
]

ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)

NOTICE_PATTERNS = [
    re.compile(
        r"("
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|충청북도|충청남도|"
        r"전북특별자치도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|[가-힣]+시|[가-힣]+군|[가-힣]+구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?"
        r")"
    ),
    re.compile(
        r"((?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호?)"
    ),
]

DATE_PATTERNS = [
    re.compile(
        r"(20\d{2})[.\-/년]\s*"
        r"(0?[1-9]|1[0-2])[.\-/월]\s*"
        r"(0?[1-9]|[12]\d|3[01])(?:일)?"
    ),
    re.compile(r"(20\d{2})(0[1-9]|1[0-2])([0-3]\d)"),
]


@dataclass
class FetchResult:
    url: str
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]
    final_url: Optional[str]


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(source: str) -> str:
    value = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", source)
    value = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    return normalize_space(html.unescape(value))


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value))


def contains_target(value: str) -> bool:
    return compact_text(TARGET_NAME) in compact_text(value)


def is_disallowed_final_url(url: str) -> bool:
    lower = str(url or "").lower()
    return any(hint in lower for hint in DISALLOWED_PAGE_HINTS)


def extract_local_context(text: str, radius: int = LOCAL_CONTEXT_RADIUS) -> str:
    normalized = normalize_space(text)

    variants = [
        TARGET_NAME,
        "개발밀도 관리구역",
        "개발 밀도 관리구역",
    ]

    index = -1

    for variant in variants:
        index = normalized.find(variant)
        if index >= 0:
            break

    if index < 0:
        return ""

    start = max(0, index - radius)
    end = min(len(normalized), index + len(TARGET_NAME) + radius)

    return normalized[start:end]


def has_strong_local_context(context: str) -> bool:
    return any(term in context for term in STRONG_LOCAL_TERMS)


def has_general_false_positive_context(text: str, context: str) -> bool:
    combined = normalize_space(text + " " + context)
    return any(term in combined for term in GENERAL_FALSE_POSITIVE_TERMS)


def extract_notice_numbers(text: str) -> List[str]:
    values = []
    seen = set()

    for pattern in NOTICE_PATTERNS:
        for match in pattern.finditer(text):
            value = normalize_space(match.group(1))

            if value and value not in seen:
                seen.add(value)
                values.append(value)

    return values


def extract_dates(text: str) -> List[str]:
    values = []
    seen = set()

    for pattern in DATE_PATTERNS:
        for match in pattern.finditer(text):
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))
            except (TypeError, ValueError):
                continue

            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue

            value = f"{year:04d}-{month:02d}-{day:02d}"

            if value in seen:
                continue

            seen.add(value)
            values.append(value)

    return values


def fetch_url(url: str) -> FetchResult:
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
    except requests.RequestException as exc:
        return FetchResult(
            url=url,
            http_status=None,
            content_type="",
            text="",
            error=repr(exc),
            final_url=None,
        )

    content_type = response.headers.get("Content-Type", "") or ""
    text = ""

    lower_type = content_type.lower()

    if (
        "text/" in lower_type
        or "html" in lower_type
        or "xml" in lower_type
        or "json" in lower_type
        or not lower_type
    ):
        text = response.text or ""

        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH]

    return FetchResult(
        url=url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
        final_url=response.url,
    )


ANCHOR_PATTERN = re.compile(
    r"""(?is)
    <a
    \s+
    [^>]*?
    href
    \s*=\s*
    (?:
        "([^"]+)"
        |
        '([^']+)'
        |
        ([^\s>]+)
    )
    [^>]*>
    (.*?)
    </a>
    """,
    re.VERBOSE,
)


def extract_attachment_links(source: str, base_url: str) -> List[Dict[str, str]]:
    results = []
    seen = set()

    for match in ANCHOR_PATTERN.finditer(source):
        href = (
            match.group(1)
            or match.group(2)
            or match.group(3)
            or ""
        ).strip()

        if not href:
            continue

        absolute = urljoin(base_url, html.unescape(href))
        lower_path = urlparse(absolute).path.lower()

        if not any(
            lower_path.endswith(extension)
            for extension in ATTACHMENT_EXTENSIONS
        ):
            continue

        if absolute in seen:
            continue

        seen.add(absolute)

        results.append(
            {
                "url": absolute,
                "label": strip_html(match.group(4) or ""),
            }
        )

    return results


def load_detail_seeds(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    candidates = data.get("detail_seed_candidates")

    if not isinstance(candidates, list):
        return []

    results = []
    seen = set()

    for item in candidates:
        if not isinstance(item, dict):
            continue

        url = str(item.get("url") or "").strip()

        if not url.startswith(("http://", "https://")):
            continue

        key = (item.get("region"), url)

        if key in seen:
            continue

        seen.add(key)
        results.append(item)

    return results


if not INPUT_PATH.exists():
    raise FileNotFoundError(
        f"I-stage output not found: {INPUT_PATH}"
    )


input_data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)

detail_seeds = load_detail_seeds(
    input_data
)

print("============================================================")
print("DEVELOPMENT DENSITY MANAGEMENT AREA")
print("OFFICIAL DETAIL DOCUMENT VERIFICATION")
print("============================================================")
print()
print("Target:", TARGET_NAME)
print("Standard code:", STANDARD_CODE)
print("Input:", INPUT_PATH)
print("Detail seed count:", len(detail_seeds))
print()


request_count = 0
http_success_count = 0
transport_error_count = 0
html_parse_count = 0

verified_positive_documents: List[Dict[str, Any]] = []
rejected_documents: List[Dict[str, Any]] = []

search_like_final_positive_leakage = 0
url_query_only_target_leakage = 0


for index, seed in enumerate(detail_seeds, start=1):
    region = str(seed.get("region") or "")
    url = str(seed.get("url") or "")
    label = normalize_space(seed.get("label"))

    print("------------------------------------------------------------")
    print(f"CANDIDATE {index}:", region)
    print("Seed label:", label)
    print("Seed URL:", url)

    result = fetch_url(url)
    request_count += 1

    if result.error:
        transport_error_count += 1

        rejected_documents.append(
            {
                **seed,
                "verification_status": "FETCH_ERROR",
                "fetch_error": result.error,
            }
        )

        print("Fetch error:", result.error)
        continue

    if result.http_status == 200:
        http_success_count += 1

    final_url = result.final_url or url
    text = strip_html(result.text)

    if result.text:
        html_parse_count += 1

    target_in_body = contains_target(text)
    target_in_seed_url = contains_target(
        requests.utils.unquote(url)
    )
    target_in_final_url = contains_target(
        requests.utils.unquote(final_url)
    )

    local_context = (
        extract_local_context(text)
        if target_in_body
        else ""
    )

    strong_local_context = (
        has_strong_local_context(local_context)
        if local_context
        else False
    )

    disallowed_final_url = is_disallowed_final_url(final_url)

    general_false_positive = (
        has_general_false_positive_context(
            text,
            local_context,
        )
    )

    notice_numbers = extract_notice_numbers(text)
    dates = extract_dates(text)

    attachments = extract_attachment_links(
        result.text,
        final_url,
    )

    if (
        not target_in_body
        and (
            target_in_seed_url
            or target_in_final_url
        )
    ):
        url_query_only_target_leakage += 1

    verified_positive = (
        result.http_status == 200
        and target_in_body
        and strong_local_context
        and not disallowed_final_url
        and not general_false_positive
    )

    if (
        verified_positive
        and is_disallowed_final_url(final_url)
    ):
        search_like_final_positive_leakage += 1

    verification_reasons = []

    if result.http_status != 200:
        verification_reasons.append("HTTP_NOT_200")

    if not target_in_body:
        verification_reasons.append("TARGET_NOT_IN_DOCUMENT_BODY")

    if target_in_body and not strong_local_context:
        verification_reasons.append("NO_STRONG_LOCAL_NOTICE_CONTEXT")

    if disallowed_final_url:
        verification_reasons.append("SEARCH_OR_PREVIEW_URL_PROHIBITED")

    if general_false_positive:
        verification_reasons.append("GENERAL_URBAN_PLANNING_FALSE_POSITIVE")

    record = {
        **seed,
        "final_url": final_url,
        "http_status": result.http_status,
        "content_type": result.content_type,
        "target_in_document_body": target_in_body,
        "target_in_seed_url": target_in_seed_url,
        "target_in_final_url": target_in_final_url,
        "strong_local_notice_context": strong_local_context,
        "search_or_preview_url": disallowed_final_url,
        "general_false_positive_context": general_false_positive,
        "notice_numbers": notice_numbers,
        "dates": dates,
        "attachment_count": len(attachments),
        "attachments": attachments,
        "local_context": local_context,
        "verified_positive": verified_positive,
        "verification_reasons": verification_reasons,
    }

    if verified_positive:
        record["verification_status"] = "VERIFIED_POSITIVE"
        verified_positive_documents.append(record)
    else:
        record["verification_status"] = "REJECTED_OR_UNVERIFIED"
        rejected_documents.append(record)

    print("HTTP:", result.http_status)
    print("Target in document body:", target_in_body)
    print("Strong local context:", strong_local_context)
    print("Search/preview URL:", disallowed_final_url)
    print("General false positive:", general_false_positive)
    print("Notice numbers:", notice_numbers)
    print("Dates:", dates)
    print("Attachments:", len(attachments))
    print("Verified positive:", verified_positive)

    if verification_reasons:
        print("Reasons:", verification_reasons)

    time.sleep(REQUEST_SLEEP)


# ============================================================
# DEDUPE VERIFIED
# ============================================================

deduped_verified = []
seen_verified: Set[str] = set()

for item in verified_positive_documents:
    key = str(item.get("final_url") or item.get("url") or "")

    if key in seen_verified:
        continue

    seen_verified.add(key)
    deduped_verified.append(item)


# ============================================================
# RESOLUTION
# ============================================================

if deduped_verified:
    resolution = (
        "OFFICIAL_DEVELOPMENT_DENSITY_MANAGEMENT_AREA_DOCUMENT_VERIFIED"
    )

    next_action = (
        "검증된 공식 원문에서 고시번호·지정일·행정구역·지정 범위·"
        "현재 유효 여부를 확정하고 positive PNU 및 spatial source를 역탐색한다."
    )
else:
    resolution = (
        "DETAIL_SEEDS_VERIFIED_NO_OFFICIAL_TARGET_DOCUMENT"
    )

    next_action = (
        "현재 I-stage detail seed를 false positive/unverified로 유지하고, "
        "검색 결과의 target-bearing row만 추출하도록 K 단계 검색결과 행 단위 "
        "정밀 파싱 및 pagination 탐색을 수행한다."
    )


runtime_registration_blocked = True
site_false_interpretation_blocked = True


output_data = {
    "step": (
        "STEP 17-21-C-16-8-J "
        "Development Density Management Area "
        "Official Detail Document Verification"
    ),
    "target": {
        "name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
    },
    "input": {
        "path": str(INPUT_PATH),
        "detail_seed_count": len(detail_seeds),
    },
    "summary": {
        "request_count": request_count,
        "http_success_count": http_success_count,
        "transport_error_count": transport_error_count,
        "html_parse_count": html_parse_count,
        "verified_positive_document_count": len(deduped_verified),
        "rejected_or_unverified_count": len(rejected_documents),
        "search_like_final_positive_leakage": (
            search_like_final_positive_leakage
        ),
        "url_query_only_target_leakage": (
            url_query_only_target_leakage
        ),
    },
    "verified_positive_documents": deduped_verified,
    "rejected_or_unverified_documents": rejected_documents,
    "resolution": resolution,
    "runtime_registration_blocked": runtime_registration_blocked,
    "site_false_interpretation_blocked": (
        site_false_interpretation_blocked
    ),
    "next_action": next_action,
}


OUTPUT_PATH.write_text(
    json.dumps(
        output_data,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print("============================================================")
print("VERIFICATION RESULT")
print("============================================================")
print("Detail seed count:", len(detail_seeds))
print("Request count:", request_count)
print("HTTP success count:", http_success_count)
print("Transport error count:", transport_error_count)
print("HTML parse count:", html_parse_count)
print(
    "Verified positive document count:",
    len(deduped_verified),
)
print(
    "Rejected / unverified count:",
    len(rejected_documents),
)
print(
    "Search-like final positive leakage:",
    search_like_final_positive_leakage,
)
print(
    "URL-query-only target leakage:",
    url_query_only_target_leakage,
)
print()


if deduped_verified:
    print("VERIFIED POSITIVE DOCUMENTS")
    print("------------------------------------------------------------")

    for index, item in enumerate(
        deduped_verified,
        start=1,
    ):
        print(f"[{index}]", item.get("region"))
        print("URL:", item.get("final_url"))
        print("Notice numbers:", item.get("notice_numbers"))
        print("Dates:", item.get("dates"))
        print("Attachments:", item.get("attachment_count"))
        print("Context:", item.get("local_context"))
        print()
else:
    print("No official target document verified.")
    print()


print("============================================================")
print("RESOLUTION")
print("============================================================")
print(resolution)
print()
print(next_action)
print()
print("Output:", OUTPUT_PATH)


# ============================================================
# VALIDATION
# ============================================================

verified_urls = {
    str(item.get("final_url") or item.get("url") or "")
    for item in deduped_verified
}

all_verified_have_target = all(
    item.get("target_in_document_body") is True
    for item in deduped_verified
)

all_verified_have_strong_context = all(
    item.get("strong_local_notice_context") is True
    for item in deduped_verified
)

all_verified_not_search_preview = all(
    item.get("search_or_preview_url") is False
    for item in deduped_verified
)

all_verified_not_general_false_positive = all(
    item.get("general_false_positive_context") is False
    for item in deduped_verified
)

validations = {
    "target name": TARGET_NAME == "개발밀도관리구역",
    "standard code": STANDARD_CODE == "UQQ700",
    "input exists": INPUT_PATH.exists(),
    "I-stage input parsed": isinstance(input_data, dict),
    "detail seeds loaded": len(detail_seeds) > 0,
    "requests executed": request_count > 0,
    "verified documents unique": (
        len(verified_urls)
        == len(deduped_verified)
    ),
    "all verified documents contain target in body": (
        all_verified_have_target
    ),
    "all verified documents have strong local context": (
        all_verified_have_strong_context
    ),
    "all verified documents are not search/preview URLs": (
        all_verified_not_search_preview
    ),
    "all verified documents are not general urban false positives": (
        all_verified_not_general_false_positive
    ),
    "search-like final positive leakage zero": (
        search_like_final_positive_leakage == 0
    ),
    "runtime registration remains blocked": (
        runtime_registration_blocked is True
    ),
    "SITE FALSE remains blocked": (
        site_false_interpretation_blocked is True
    ),
    "output written": (
        OUTPUT_PATH.exists()
        and OUTPUT_PATH.stat().st_size > 0
    ),
}


print()
print("============================================================")
print("VALIDATION")
print("============================================================")

for name, passed in validations.items():
    print(f"{name}:", passed)

all_pass = all(validations.values())

print()
print("all_pass:", all_pass)


if not all_pass:
    print()
    print("FAILED:")

    for name, passed in validations.items():
        if not passed:
            print("-", name)

    raise AssertionError(
        "Development density management area "
        "official detail document verification regression failed"
    )
