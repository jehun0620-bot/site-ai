# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-I
Development Density Management Area
Official Notice Recovery Discovery

목표
======================================================================
H-stage에서 정제된 공식 지자체 endpoint와
직전 target document verification 결과를 바탕으로
실제 개발밀도관리구역 지정·변경·해제 고시 원문 후보를
다시 탐색한다.

입력 1:
    law_data/output/
    development_density_management_area_official_board_endpoint_refinement.json

입력 2:
    law_data/output/
    development_density_management_area_target_document_candidate_verification.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 전략
======================================================================
1. H-stage의 searchable endpoint만 사용한다.
2. PRIMARY_GOSI_BOARD / GAZETTE_ARCHIVE / URBAN_PLANNING_BOARD만 탐색한다.
3. SECONDARY_REVIEW / EXCLUDED_GENERIC_BOARD는 직접 탐색하지 않는다.
4. target exact phrase 검색을 우선한다.
5. 관련 보조 검색어를 제한적으로 사용한다.
6. 검색/list 페이지 자체는 final positive가 아니다.
7. detail URL / attachment URL / download URL만 다음 단계 seed로 넘긴다.
8. 행정업무표·사무전결표·업무분장표 false positive를 별도 차단한다.
9. 실제 고시번호·지정·변경·해제 문맥은 ranking 보조 증거일 뿐,
   이 단계에서는 verified positive 승격을 금지한다.
10. runtime condition 등록은 계속 차단한다.

중요한 evidence contract
======================================================================
페이지 전체 page_text를 개별 링크 후보의 semantic evidence로
상속하지 않는다.

각 링크의 target / action / official / notice / date evidence는:

    1. anchor label
    2. anchor 주변 local DOM context

에서만 계산한다.

따라서 다음 false positive를 차단한다.

    - 부모 검색 페이지 target을 모든 링크에 복제
    - 부모 페이지 고시번호를 외부 링크에 복제
    - 부모 페이지 날짜를 unrelated attachment에 복제
    - 도시계획 board의 일반 navigation을 도시계획 고시로 승격
    - 지자체 홈페이지 root link를 TARGET_DIRECT_DETAIL_SEED로 승격
    - 타 기관 / 외부 서비스 링크를 verification pool로 승격

출력 분류
======================================================================

TARGET_DIRECT_DETAIL_SEED
    상세 URL 또는 링크 local context에 개발밀도관리구역 exact target이 존재.

URBAN_NOTICE_DETAIL_SEED
    target exact phrase는 없지만 링크 local context에서
    도시계획 + 고시 + 지정/변경/해제 문맥이 함께 존재하는 detail seed.

GAZETTE_ISSUE_SEED
    시보/군보/구보/공보 issue 단위 후보.

ATTACHMENT_DOCUMENT_SEED
    PDF/HWP/HWPX 등 직접 첨부 원문 seed.
    단, link-local 관련성 evidence가 있어야 한다.

EXTENSIONLESS_DOWNLOAD_SEED
    확장자 없는 download endpoint.
    단, link-local 관련성 evidence가 있어야 한다.

LOW_CONFIDENCE_DETAIL_SEED
    구조적으로 detail 가능성은 있으나 semantic evidence가 약함.

EXCLUDED_ADMINISTRATIVE_DUTY_REFERENCE
    사무전결/업무분장/단위사무표 계열 false positive.

EXCLUDED_GENERIC_LINK
    네비게이션, 외부사이트, 홈페이지 root,
    검색/list 페이지, unrelated attachment 등.

안전정책
======================================================================
- 검색 결과 page는 final positive가 아니다.
- detail page도 이 단계에서는 final positive가 아니다.
- attachment도 이 단계에서는 final positive가 아니다.
- verified positive promotion은 다음 원문 검증 단계에서만 가능하다.
- runtime registration은 계속 차단한다.
- SITE FALSE 판정도 계속 차단한다.
"""

from __future__ import annotations

import html
import json
import re
import time

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
    urljoin,
    urlparse,
    urlunparse,
)

import requests


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

ENDPOINT_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "official_board_endpoint_refinement.json"
    )
)

VERIFICATION_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "target_document_candidate_verification.json"
    )
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "official_notice_recovery_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# HTTP CONFIG
# ============================================================

TIMEOUT = 20

MAX_RESPONSE_BYTES = (
    10
    * 1024
    * 1024
)

REQUEST_DELAY_SECONDS = 0.05

MAX_SEARCH_VARIANTS_PER_ENDPOINT = 10

MAX_DISCOVERED_LINKS_PER_RESPONSE = 500

# anchor 앞뒤 HTML 일부만 local evidence로 사용한다.
LINK_LOCAL_CONTEXT_RADIUS = 1200

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# ENDPOINT CLASSES
# ============================================================

ALLOWED_ENDPOINT_CLASSES = {
    "PRIMARY_GOSI_BOARD",
    "GAZETTE_ARCHIVE",
    "URBAN_PLANNING_BOARD",
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_TARGET_DIRECT = (
    "TARGET_DIRECT_DETAIL_SEED"
)

CLASS_URBAN_NOTICE = (
    "URBAN_NOTICE_DETAIL_SEED"
)

CLASS_GAZETTE_ISSUE = (
    "GAZETTE_ISSUE_SEED"
)

CLASS_ATTACHMENT = (
    "ATTACHMENT_DOCUMENT_SEED"
)

CLASS_EXTENSIONLESS = (
    "EXTENSIONLESS_DOWNLOAD_SEED"
)

CLASS_LOW_CONFIDENCE = (
    "LOW_CONFIDENCE_DETAIL_SEED"
)

CLASS_EXCLUDED_ADMIN_DUTY = (
    "EXCLUDED_ADMINISTRATIVE_DUTY_REFERENCE"
)

CLASS_EXCLUDED_GENERIC = (
    "EXCLUDED_GENERIC_LINK"
)

VALID_CANDIDATE_CLASSES = {
    CLASS_TARGET_DIRECT,
    CLASS_URBAN_NOTICE,
    CLASS_GAZETTE_ISSUE,
    CLASS_ATTACHMENT,
    CLASS_EXTENSIONLESS,
    CLASS_LOW_CONFIDENCE,
    CLASS_EXCLUDED_ADMIN_DUTY,
    CLASS_EXCLUDED_GENERIC,
}


# ============================================================
# SEARCH TERMS
# ============================================================

SEARCH_TERMS = [
    "개발밀도관리구역",
    "\"개발밀도관리구역\"",
    "개발밀도관리구역 지정",
    "개발밀도관리구역 고시",
    "개발밀도관리구역 변경",
    "개발밀도관리구역 해제",
    "개발밀도관리구역 도시관리계획",
    "기반시설부담구역 개발밀도관리구역",
]


# ============================================================
# SEMANTIC TERMS
# ============================================================

ACTION_TERMS = [
    "지정",
    "변경",
    "해제",
    "결정",
    "변경결정",
    "결정변경",
]

OFFICIAL_TERMS = [
    "고시",
    "고시문",
    "공고",
    "도시관리계획",
    "도시계획",
    "지형도면",
    "국토의 계획 및 이용에 관한 법률",
    "국토계획법",
]

GAZETTE_TERMS = [
    "시보",
    "군보",
    "구보",
    "공보",
    "호외",
]

URBAN_TERMS = [
    "도시관리계획",
    "도시계획",
    "도시정책",
    "용도지역",
    "용도지구",
    "용도구역",
    "지구단위계획",
    "지형도면",
    "기반시설부담구역",
]

ADMINISTRATIVE_DUTY_TERMS = [
    "단위사무명",
    "단 위 사 무 명",
    "전결권자",
    "전 결 권 자",
    "사무전결",
    "업무분장",
    "위임전결",
    "전결규정",
    "담당자",
    "팀장",
    "국장",
    "부시장",
]

GENERIC_LINK_LABEL_TERMS = [
    "목록",
    "이전글",
    "다음글",
    "이전",
    "다음",
    "처음",
    "마지막",
    "로그인",
    "회원가입",
    "사이트맵",
    "홈",
    "메인",
    "홈페이지",
    "대표홈페이지",
    "대표홈페이지가기",
    "더보기",
    "전체보기",
    "본문",
    "language 펼치기",
]

GENERIC_PATH_TERMS = [
    "/login",
    "/member",
    "/join",
    "/sitemap",
    "/privacy",
    "/search",
]

UNRELATED_ATTACHMENT_LABEL_TERMS = [
    "채용공고",
    "채용 공고",
    "입찰공고",
    "입찰 공고",
    "간판",
    "체크리스트",
    "매뉴얼",
    "업무계획",
    "일자리",
    "수영장",
    "주정차",
    "전세계약",
    "브라우저",
    "internet explorer",
    "웹배너",
    "홍보",
    "포스터",
]


# ============================================================
# URL / LINK PATTERNS
# ============================================================

FILE_EXTENSIONS = {
    ".pdf",
    ".hwp",
    ".hwpx",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".zip",
}

DOWNLOAD_HINT_TERMS = [
    "download",
    "filedown",
    "filedownload",
    "attach",
    "atchfile",
    "file.do",
    "filedown.do",
    "download.do",
    "down.do",
    "act=download",
]

DETAIL_HINT_TERMS = [
    "view",
    "detail",
    "select",
    "read",
    "article",
    "post",
    "notice.htm",
    "announceDetail",
    "gosi/view",
]

LIST_HINT_TERMS = [
    "list.do",
    "/list",
    "selectboardlist",
    "board/list",
    "bbs/list",
]


# ============================================================
# NOTICE PATTERNS
# ============================================================

NOTICE_PATTERNS = [
    re.compile(
        r"(?P<notice>"
        r"(?:서울특별시|부산광역시|대구광역시|인천광역시|"
        r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
        r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
        r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
        r"제주특별자치도|"
        r"[가-힣]{2,10}시|[가-힣]{2,10}군|[가-힣]{2,10}구)"
        r"\s*(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
    re.compile(
        r"(?P<notice>"
        r"(?:고시|공고)\s*제?\s*\d{4}\s*[-–]\s*\d+\s*호)"
    ),
]

DATE_PATTERN = re.compile(
    r"(?P<year>19\d{2}|20\d{2})"
    r"\s*[.\-/년]\s*"
    r"(?P<month>0?[1-9]|1[0-2])"
    r"\s*[.\-/월]\s*"
    r"(?P<day>0?[1-9]|[12]\d|3[01])"
    r"\s*일?"
)


# ============================================================
# HTML PATTERNS
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"<a\b(?P<attrs>[^>]*)>"
    r"(?P<body>.*?)"
    r"</a>",
    re.IGNORECASE
    | re.DOTALL,
)

HREF_PATTERN = re.compile(
    r"""href\s*=\s*["'](?P<href>[^"']+)["']""",
    re.IGNORECASE,
)

ONCLICK_PATTERN = re.compile(
    r"""onclick\s*=\s*["'](?P<onclick>[^"']+)["']""",
    re.IGNORECASE,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE
    | re.DOTALL,
)

HTML_COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)


# ============================================================
# UTIL
# ============================================================

def normalize_space(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        str(
            value
            or ""
        ),
    ).strip()


def unique_strings(
    values: Iterable[Any],
) -> List[str]:

    result: List[str] = []
    seen: Set[str] = set()

    for value in values:

        text = normalize_space(
            value
        )

        if not text:
            continue

        if text in seen:
            continue

        seen.add(
            text
        )

        result.append(
            text
        )

    return result


def contains_any(
    value: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        value
    ).lower()

    return any(
        term.lower()
        in lowered
        for term in terms
    )


def strip_html(
    raw_html: str,
) -> str:

    text = HTML_COMMENT_PATTERN.sub(
        " ",
        raw_html,
    )

    text = SCRIPT_STYLE_PATTERN.sub(
        " ",
        text,
    )

    text = TAG_PATTERN.sub(
        " ",
        text,
    )

    text = html.unescape(
        text
    )

    return normalize_space(
        text
    )


def extract_notice_numbers(
    text: str,
) -> List[str]:

    result: List[str] = []

    for pattern in NOTICE_PATTERNS:

        for match in pattern.finditer(
            text
        ):

            value = (
                match.groupdict().get(
                    "notice"
                )
                or match.group(0)
            )

            result.append(
                normalize_space(
                    value
                )
            )

    return unique_strings(
        result
    )


def extract_dates(
    text: str,
) -> List[str]:

    result: List[str] = []

    for match in DATE_PATTERN.finditer(
        text
    ):

        year = int(
            match.group(
                "year"
            )
        )

        month = int(
            match.group(
                "month"
            )
        )

        day = int(
            match.group(
                "day"
            )
        )

        result.append(
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

    return unique_strings(
        result
    )


# ============================================================
# URL NORMALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "csrftoken",
    "sessionid",
    "jsessionid",
    "_",
    "timestamp",
    "rand",
    "random",
    "cachebuster",
    "cache_buster",
    "cb",
    "ts",
}

TRACKING_QUERY_KEYS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
}

JSESSIONID_PATTERN = re.compile(
    r";jsessionid=[^/?]+",
    re.IGNORECASE,
)


def normalize_query_key(
    key: str,
) -> str:

    value = html.unescape(
        str(
            key
            or ""
        )
    ).strip()

    while value.lower().startswith(
        "amp;"
    ):
        value = value[
            4:
        ].strip()

    return value


def is_volatile_query_key(
    key: str,
) -> bool:

    lowered = normalize_query_key(
        key
    ).lower()

    if lowered in VOLATILE_QUERY_KEYS:
        return True

    if lowered in TRACKING_QUERY_KEYS:
        return True

    if "csrf" in lowered:
        return True

    if "session" in lowered:
        return True

    if re.search(
        r"(?:^|[_\-])token$",
        lowered,
    ):
        return True

    return False


def canonicalize_url(
    url: str,
) -> str:

    value = html.unescape(
        normalize_space(
            url
        )
    )

    if not value:
        return ""

    try:
        parsed = urlparse(
            value
        )

    except Exception:
        return value

    if not parsed.hostname:
        return value

    scheme = (
        parsed.scheme
        or "https"
    ).lower()

    host = (
        parsed.hostname
        or ""
    ).lower()

    try:
        port = parsed.port

    except ValueError:
        port = None

    if (
        port
        and not (
            scheme == "https"
            and port == 443
        )
        and not (
            scheme == "http"
            and port == 80
        )
    ):
        netloc = (
            f"{host}:{port}"
        )

    else:
        netloc = host

    path = (
        parsed.path
        or "/"
    )

    path = JSESSIONID_PATTERN.sub(
        "",
        path,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []
    seen_pairs = set()

    for raw_key, query_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_query_key(
            raw_key
        )

        if not key:
            continue

        if is_volatile_query_key(
            key
        ):
            continue

        pair = (
            key,
            query_value,
        )

        if pair in seen_pairs:
            continue

        seen_pairs.add(
            pair
        )

        query_items.append(
            pair
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    query = urlencode(
        query_items,
        doseq=True,
    )

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            query,
            "",
        )
    )


# ============================================================
# HOST / ORGANIZATION DOMAIN
# ============================================================

def hostname_of(
    url: str,
) -> str:

    try:
        return (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:
        return ""


def organization_domain(
    url: str,
) -> str:
    """
    지자체 subdomain 간 이동은 허용하되
    외부기관 링크는 차단하기 위한 단순 organization-domain 추출.

    예:
        www.seongnam.go.kr
        map.seongnam.go.kr
        eminwon.seongnam.go.kr

    -> seongnam.go.kr
    """

    host = hostname_of(
        url
    )

    if not host:
        return ""

    parts = [
        part
        for part in host.split(".")
        if part
    ]

    if len(parts) < 2:
        return host

    if (
        len(parts) >= 3
        and parts[-2:]
        in [
            ["go", "kr"],
            ["or", "kr"],
            ["co", "kr"],
            ["ac", "kr"],
            ["ne", "kr"],
        ]
    ):
        return ".".join(
            parts[-3:]
        )

    return ".".join(
        parts[-2:]
    )


def same_organization_domain(
    url_a: str,
    url_b: str,
) -> bool:

    domain_a = organization_domain(
        url_a
    )

    domain_b = organization_domain(
        url_b
    )

    return (
        bool(
            domain_a
        )
        and bool(
            domain_b
        )
        and domain_a == domain_b
    )


def is_root_navigation_url(
    url: str,
) -> bool:

    try:
        parsed = urlparse(
            url
        )

    except Exception:
        return False

    path = (
        parsed.path
        or "/"
    ).strip()

    if path in {
        "",
        "/",
    }:
        return True

    normalized = path.rstrip(
        "/"
    ).lower()

    if normalized in {
        "/index",
        "/index.do",
        "/main",
        "/main.do",
        "/home",
        "/home.do",
    }:
        return True

    return False


# ============================================================
# PRIOR Y-STAGE EXCLUSION MEMORY
# ============================================================

def load_prior_excluded_urls(
    verification_data: Dict[str, Any],
) -> Set[str]:

    excluded: Set[str] = set()

    for candidate in (
        verification_data.get(
            "candidates"
        )
        or []
    ):

        if not isinstance(
            candidate,
            dict,
        ):
            continue

        resolution = normalize_space(
            candidate.get(
                "resolution"
            )
        )

        if resolution not in {
            "ADMINISTRATIVE_DUTY_REFERENCE_ONLY",
            "LEGAL_REFERENCE_ONLY",
            "TARGET_MENTION_ONLY",
        }:
            continue

        url = canonicalize_url(
            candidate.get(
                "url"
            )
            or ""
        )

        if url:
            excluded.add(
                url
            )

    return excluded


# ============================================================
# ENDPOINT LOAD
# ============================================================

def load_searchable_endpoints(
    endpoint_data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    raw = endpoint_data.get(
        "next_stage_search_pool"
    )

    if not isinstance(
        raw,
        list,
    ):
        raw = []

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in raw:

        if not isinstance(
            item,
            dict,
        ):
            continue

        classification = normalize_space(
            item.get(
                "classification"
            )
        )

        if classification not in ALLOWED_ENDPOINT_CLASSES:
            continue

        region = normalize_space(
            item.get(
                "region"
            )
        )

        url = canonicalize_url(
            item.get(
                "canonical_url"
            )
            or item.get(
                "raw_url"
            )
            or ""
        )

        if not url:
            continue

        key = (
            region,
            url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        normalized = dict(
            item
        )

        normalized[
            "canonical_url"
        ] = url

        result.append(
            normalized
        )

    return result


# ============================================================
# SEARCH VARIANT GENERATION
# ============================================================

COMMON_SEARCH_PARAM_NAMES = [
    "searchKeyword",
    "searchWrd",
    "searchWord",
    "searchText",
    "searchTerm",
    "keyword",
    "query",
    "q",
    "srchText",
    "srchWord",
    "srchKeyword",
    "search",
]


def build_get_search_variants(
    endpoint_url: str,
    search_term: str,
) -> List[str]:

    variants: List[str] = []

    try:
        parsed = urlparse(
            endpoint_url
        )

    except Exception:
        return variants

    base_query = parse_qsl(
        parsed.query,
        keep_blank_values=True,
    )

    for param in COMMON_SEARCH_PARAM_NAMES:

        query = [
            (
                key,
                value,
            )
            for key, value in base_query
            if key.lower()
            != param.lower()
        ]

        query.append(
            (
                param,
                search_term,
            )
        )

        url = urlunparse(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                urlencode(
                    query,
                    doseq=True,
                ),
                parsed.fragment,
            )
        )

        variants.append(
            canonicalize_url(
                url
            )
        )

        if len(
            variants
        ) >= MAX_SEARCH_VARIANTS_PER_ENDPOINT:
            break

    return unique_strings(
        variants
    )


# ============================================================
# HTTP
# ============================================================

def request_html(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "url": url,
        "http_status": None,
        "final_url": "",
        "content_type": "",
        "response_bytes": 0,
        "html": "",
        "text": "",
        "error": "",
    }

    try:

        with session.get(
            url,
            timeout=TIMEOUT,
            allow_redirects=True,
            stream=True,
        ) as response:

            result[
                "http_status"
            ] = response.status_code

            result[
                "final_url"
            ] = canonicalize_url(
                str(
                    response.url
                )
            )

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            response.raise_for_status()

            chunks: List[bytes] = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=256 * 1024
            ):

                if not chunk:
                    continue

                total += len(
                    chunk
                )

                if total > MAX_RESPONSE_BYTES:

                    raise ValueError(
                        "response exceeds "
                        f"{MAX_RESPONSE_BYTES} bytes"
                    )

                chunks.append(
                    chunk
                )

            data = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                data
            )

            encoding = (
                response.encoding
                or response.apparent_encoding
                or "utf-8"
            )

            raw_html = data.decode(
                encoding,
                errors="replace",
            )

            result[
                "html"
            ] = raw_html

            result[
                "text"
            ] = strip_html(
                raw_html
            )

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# LINK LOCAL CONTEXT
# ============================================================

def extract_link_local_context(
    raw_html: str,
    start_index: int,
    end_index: int,
) -> str:
    """
    전체 page_text 대신 anchor 주변 HTML 조각만 사용한다.

    우선 tr / li 단위 container를 찾아보고,
    실패하면 anchor 앞뒤 제한된 window만 사용한다.
    """

    if not raw_html:
        return ""

    # --------------------------------------------------------
    # 1. table row
    # --------------------------------------------------------

    tr_start = raw_html.rfind(
        "<tr",
        0,
        start_index,
    )

    tr_end = raw_html.find(
        "</tr>",
        end_index,
    )

    if (
        tr_start >= 0
        and tr_end >= 0
        and tr_end - tr_start <= 12000
    ):
        return strip_html(
            raw_html[
                tr_start:
                tr_end
                + len(
                    "</tr>"
                )
            ]
        )

    # --------------------------------------------------------
    # 2. list item
    # --------------------------------------------------------

    li_start = raw_html.rfind(
        "<li",
        0,
        start_index,
    )

    li_end = raw_html.find(
        "</li>",
        end_index,
    )

    if (
        li_start >= 0
        and li_end >= 0
        and li_end - li_start <= 12000
    ):
        return strip_html(
            raw_html[
                li_start:
                li_end
                + len(
                    "</li>"
                )
            ]
        )

    # --------------------------------------------------------
    # 3. fallback local window
    # --------------------------------------------------------

    left = max(
        0,
        start_index
        - LINK_LOCAL_CONTEXT_RADIUS,
    )

    right = min(
        len(
            raw_html
        ),
        end_index
        + LINK_LOCAL_CONTEXT_RADIUS,
    )

    return strip_html(
        raw_html[
            left:right
        ]
    )


# ============================================================
# LINK EXTRACTION
# ============================================================

def extract_js_url(
    onclick: str,
) -> str:

    value = normalize_space(
        onclick
    )

    if not value:
        return ""

    patterns = [
        r"""location\.href\s*=\s*['"]([^'"]+)['"]""",
        r"""window\.open\s*\(\s*['"]([^'"]+)['"]""",
        r"""location\s*=\s*['"]([^'"]+)['"]""",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            value,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_space(
                match.group(1)
            )

    return ""


def extract_links(
    base_url: str,
    raw_html: str,
) -> List[Dict[str, str]]:

    results: List[
        Dict[str, str]
    ] = []

    seen: Set[
        Tuple[
            str,
            str,
        ]
    ] = set()

    for match in ANCHOR_PATTERN.finditer(
        raw_html
    ):

        attrs = match.group(
            "attrs"
        )

        body = match.group(
            "body"
        )

        label = strip_html(
            body
        )

        href_match = HREF_PATTERN.search(
            attrs
        )

        href = (
            normalize_space(
                href_match.group(
                    "href"
                )
            )
            if href_match
            else ""
        )

        onclick_match = ONCLICK_PATTERN.search(
            attrs
        )

        onclick = (
            normalize_space(
                onclick_match.group(
                    "onclick"
                )
            )
            if onclick_match
            else ""
        )

        if (
            not href
            or href.lower().startswith(
                "javascript:"
            )
            or href == "#"
        ):

            js_url = extract_js_url(
                onclick
            )

            if js_url:
                href = js_url

        if not href:
            continue

        if href.lower().startswith(
            (
                "mailto:",
                "tel:",
            )
        ):
            continue

        absolute_url = canonicalize_url(
            urljoin(
                base_url,
                html.unescape(
                    href
                ),
            )
        )

        if not absolute_url:
            continue

        local_context = (
            extract_link_local_context(
                raw_html=raw_html,
                start_index=match.start(),
                end_index=match.end(),
            )
        )

        key = (
            label,
            absolute_url,
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        results.append(
            {
                "label": label,
                "url": absolute_url,
                "onclick": onclick,
                "local_context": (
                    local_context
                ),
            }
        )

        if (
            len(
                results
            )
            >= MAX_DISCOVERED_LINKS_PER_RESPONSE
        ):
            break

    return results


# ============================================================
# LINK STRUCTURE
# ============================================================

def is_file_url(
    url: str,
) -> bool:

    try:

        path = (
            urlparse(
                url
            ).path
            or ""
        ).lower()

    except Exception:
        return False

    return any(
        path.endswith(
            extension
        )
        for extension in FILE_EXTENSIONS
    )


def is_extensionless_download_url(
    url: str,
) -> bool:

    if is_file_url(
        url
    ):
        return False

    return contains_any(
        url.lower(),
        DOWNLOAD_HINT_TERMS,
    )


def looks_list_endpoint(
    url: str,
) -> bool:

    return contains_any(
        url.lower(),
        LIST_HINT_TERMS,
    )


def looks_detail_endpoint(
    url: str,
) -> bool:

    lowered = url.lower()

    if looks_list_endpoint(
        url
    ):
        return False

    return contains_any(
        lowered,
        DETAIL_HINT_TERMS,
    )


def looks_generic_navigation(
    label: str,
    url: str,
) -> bool:

    normalized_label = normalize_space(
        label
    )

    lowered_label = (
        normalized_label
        .lower()
    )

    lowered_url = (
        url
        .lower()
    )

    if normalized_label:

        if any(
            term.lower()
            == lowered_label
            for term
            in GENERIC_LINK_LABEL_TERMS
        ):
            return True

    if contains_any(
        lowered_url,
        GENERIC_PATH_TERMS,
    ):
        return True

    if is_root_navigation_url(
        url
    ):
        return True

    return False


def has_unrelated_attachment_label(
    label: str,
) -> bool:

    return contains_any(
        label,
        UNRELATED_ATTACHMENT_LABEL_TERMS,
    )


# ============================================================
# ADMINISTRATIVE DUTY GUARD
# ============================================================

def detect_administrative_duty_reference(
    text: str,
) -> Tuple[
    bool,
    List[str],
]:

    compact = normalize_space(
        text
    )

    evidence: List[str] = []

    for term in ADMINISTRATIVE_DUTY_TERMS:

        if term in compact:

            evidence.append(
                term
            )

    draft_marker_count = len(
        re.findall(
            r"기안\s*[○●◎]?",
            compact,
        )
    )

    if draft_marker_count >= 10:

        evidence.append(
            f"기안 marker x{draft_marker_count}"
        )

    target_draft = re.search(
        r"개발밀도관리구역.{0,80}?기안",
        compact,
        flags=re.DOTALL,
    )

    if target_draft:

        evidence.append(
            normalize_space(
                target_draft.group(0)
            )
        )

    strong_structure = (
        (
            "단위사무명"
            in compact
            or "단 위 사 무 명"
            in compact
        )
        and (
            "전결권자"
            in compact
            or "전 결 권 자"
            in compact
        )
    )

    administrative_reference = (
        strong_structure
        or (
            target_draft
            is not None
            and draft_marker_count >= 5
        )
        or (
            len(
                evidence
            )
            >= 4
            and draft_marker_count >= 5
        )
    )

    return (
        administrative_reference,
        unique_strings(
            evidence
        ),
    )


# ============================================================
# LINK CLASSIFICATION
# ============================================================

def classify_discovered_link(
    *,
    endpoint: Dict[str, Any],
    search_url: str,
    search_term: str,
    link: Dict[str, str],
    prior_excluded_urls: Set[str],
) -> Dict[str, Any]:

    region = normalize_space(
        endpoint.get(
            "region"
        )
    )

    endpoint_class = normalize_space(
        endpoint.get(
            "classification"
        )
    )

    endpoint_url = canonicalize_url(
        endpoint.get(
            "canonical_url"
        )
        or ""
    )

    label = normalize_space(
        link.get(
            "label"
        )
    )

    url = canonicalize_url(
        link.get(
            "url"
        )
        or ""
    )

    local_context = normalize_space(
        link.get(
            "local_context"
        )
    )

    # ========================================================
    # CRITICAL:
    # page_text는 사용하지 않는다.
    # semantic evidence는 link-local scope에서만 계산한다.
    # ========================================================

    local_evidence_text = normalize_space(
        f"{label} {local_context}"
    )

    target_in_label = (
        TARGET_NAME
        in label
    )

    target_in_local_context = (
        TARGET_NAME
        in local_context
    )

    target_found = (
        target_in_label
        or target_in_local_context
    )

    action_terms = [
        term
        for term in ACTION_TERMS
        if term
        in local_evidence_text
    ]

    official_terms = [
        term
        for term in OFFICIAL_TERMS
        if term
        in local_evidence_text
    ]

    urban_terms = [
        term
        for term in URBAN_TERMS
        if term
        in local_evidence_text
    ]

    gazette_terms = [
        term
        for term in GAZETTE_TERMS
        if term
        in local_evidence_text
    ]

    notice_numbers = (
        extract_notice_numbers(
            local_evidence_text
        )
    )

    dates = extract_dates(
        local_evidence_text
    )

    is_attachment = is_file_url(
        url
    )

    is_extensionless_download = (
        is_extensionless_download_url(
            url
        )
    )

    detail_endpoint = (
        looks_detail_endpoint(
            url
        )
    )

    list_endpoint = (
        looks_list_endpoint(
            url
        )
    )

    generic_navigation = (
        looks_generic_navigation(
            label,
            url,
        )
    )

    same_organization = (
        same_organization_domain(
            endpoint_url,
            url,
        )
    )

    external_navigation = (
        not same_organization
    )

    root_navigation = (
        is_root_navigation_url(
            url
        )
    )

    prior_excluded = (
        url
        in prior_excluded_urls
    )

    unrelated_attachment_label = (
        has_unrelated_attachment_label(
            label
        )
    )

    (
        administrative_reference,
        administrative_evidence,
    ) = detect_administrative_duty_reference(
        local_evidence_text
    )

    # ========================================================
    # LOCAL RELEVANCE CONTRACT
    # ========================================================

    has_action = bool(
        action_terms
    )

    has_official = bool(
        official_terms
    )

    has_urban = bool(
        urban_terms
    )

    has_gazette = bool(
        gazette_terms
    )

    has_notice = bool(
        notice_numbers
    )

    has_strong_local_semantic = (
        target_found
        or (
            has_notice
            and has_official
        )
        or (
            has_urban
            and has_official
            and has_action
        )
    )

    attachment_locally_relevant = (
        target_found
        or (
            has_notice
            and (
                has_urban
                or has_action
            )
        )
        or (
            has_urban
            and has_official
            and has_action
        )
    )

    # unrelated 파일명은 target 자체가 파일명/local context에
    # 있을 경우에만 override 가능.
    if (
        unrelated_attachment_label
        and not target_found
    ):
        attachment_locally_relevant = False

    # ========================================================
    # SCORE
    # ========================================================

    score = 0

    reasons: List[str] = []

    if target_in_label:

        score += 25

        reasons.append(
            "TARGET_IN_LINK_LABEL"
        )

    elif target_in_local_context:

        score += 18

        reasons.append(
            "TARGET_IN_LINK_LOCAL_CONTEXT"
        )

    if has_action:

        score += 5

        reasons.append(
            "LOCAL_ACTION_CONTEXT"
        )

    if has_official:

        score += 5

        reasons.append(
            "LOCAL_OFFICIAL_CONTEXT"
        )

    if has_urban:

        score += 5

        reasons.append(
            "LOCAL_URBAN_PLANNING_CONTEXT"
        )

    if has_notice:

        score += 10

        reasons.append(
            "LOCAL_NOTICE_NUMBER_EVIDENCE"
        )

    if has_gazette:

        score += 4

        reasons.append(
            "LOCAL_GAZETTE_CONTEXT"
        )

    if detail_endpoint:

        score += 4

        reasons.append(
            "DETAIL_ENDPOINT_STRUCTURE"
        )

    if is_attachment:

        score += 6

        reasons.append(
            "DIRECT_ATTACHMENT"
        )

    if is_extensionless_download:

        score += 5

        reasons.append(
            "EXTENSIONLESS_DOWNLOAD"
        )

    if external_navigation:

        score -= 50

        reasons.append(
            "EXTERNAL_ORGANIZATION_LINK"
        )

    if root_navigation:

        score -= 40

        reasons.append(
            "ROOT_HOME_NAVIGATION"
        )

    if generic_navigation:

        score -= 30

        reasons.append(
            "GENERIC_NAVIGATION"
        )

    if list_endpoint:

        score -= 15

        reasons.append(
            "LIST_ENDPOINT"
        )

    if prior_excluded:

        score -= 50

        reasons.append(
            "PRIOR_FALSE_POSITIVE_URL"
        )

    if unrelated_attachment_label:

        score -= 15

        reasons.append(
            "UNRELATED_ATTACHMENT_LABEL"
        )

    if (
        (
            is_attachment
            or is_extensionless_download
        )
        and not attachment_locally_relevant
    ):
        score -= 30

        reasons.append(
            "ATTACHMENT_WITHOUT_LOCAL_RELEVANCE"
        )

    if administrative_reference:

        score -= 60

        reasons.append(
            "ADMINISTRATIVE_DUTY_REFERENCE"
        )

    # ========================================================
    # CLASSIFICATION PRIORITY
    # ========================================================

    if administrative_reference:

        classification = (
            CLASS_EXCLUDED_ADMIN_DUTY
        )

    elif prior_excluded:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif external_navigation:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif root_navigation:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif generic_navigation:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif (
        is_attachment
        and attachment_locally_relevant
    ):

        classification = (
            CLASS_ATTACHMENT
        )

    elif (
        is_extensionless_download
        and attachment_locally_relevant
    ):

        classification = (
            CLASS_EXTENSIONLESS
        )

    elif (
        (
            is_attachment
            or is_extensionless_download
        )
        and not attachment_locally_relevant
    ):

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    elif (
        target_found
        and detail_endpoint
        and not list_endpoint
    ):

        classification = (
            CLASS_TARGET_DIRECT
        )

    elif (
        target_found
        and not list_endpoint
        and has_strong_local_semantic
    ):

        classification = (
            CLASS_TARGET_DIRECT
        )

    elif (
        endpoint_class
        == "GAZETTE_ARCHIVE"
        and has_gazette
        and not list_endpoint
        and (
            detail_endpoint
            or has_notice
        )
    ):

        classification = (
            CLASS_GAZETTE_ISSUE
        )

    elif (
        detail_endpoint
        and has_urban
        and has_official
        and has_action
    ):

        classification = (
            CLASS_URBAN_NOTICE
        )

    elif (
        detail_endpoint
        and (
            has_notice
            or has_strong_local_semantic
        )
        and score >= 8
    ):

        classification = (
            CLASS_LOW_CONFIDENCE
        )

    else:

        classification = (
            CLASS_EXCLUDED_GENERIC
        )

    return {
        "region":
            region,

        "agency":
            normalize_space(
                endpoint.get(
                    "agency"
                )
            ),

        "endpoint_classification":
            endpoint_class,

        "endpoint_url":
            endpoint_url,

        "search_url":
            search_url,

        "search_term":
            search_term,

        "label":
            label,

        "url":
            url,

        "classification":
            classification,

        "score":
            score,

        # ----------------------------------------------------
        # link-local evidence diagnostics
        # ----------------------------------------------------

        "local_context":
            local_context,

        "local_context_length":
            len(
                local_context
            ),

        "page_level_evidence_inherited":
            False,

        "target_found":
            target_found,

        "target_in_label":
            target_in_label,

        "target_in_local_context":
            target_in_local_context,

        "action_terms":
            unique_strings(
                action_terms
            ),

        "official_terms":
            unique_strings(
                official_terms
            ),

        "urban_terms":
            unique_strings(
                urban_terms
            ),

        "gazette_terms":
            unique_strings(
                gazette_terms
            ),

        "notice_numbers":
            notice_numbers,

        "dates":
            dates,

        # ----------------------------------------------------
        # structural diagnostics
        # ----------------------------------------------------

        "is_attachment":
            is_attachment,

        "is_extensionless_download":
            is_extensionless_download,

        "detail_endpoint":
            detail_endpoint,

        "list_endpoint":
            list_endpoint,

        "same_organization_domain":
            same_organization,

        "external_navigation":
            external_navigation,

        "root_navigation":
            root_navigation,

        "generic_navigation":
            generic_navigation,

        "unrelated_attachment_label":
            unrelated_attachment_label,

        "attachment_locally_relevant":
            attachment_locally_relevant,

        "prior_excluded_url":
            prior_excluded,

        "administrative_duty_reference":
            administrative_reference,

        "administrative_duty_evidence":
            administrative_evidence,

        "reasons":
            unique_strings(
                reasons
            ),

        "final_positive":
            False,
    }


# ============================================================
# LOAD INPUT
# ============================================================

print(
    "=" * 60
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA"
)

print(
    "OFFICIAL NOTICE RECOVERY DISCOVERY"
)

print(
    "=" * 60
)

print()

print(
    f"Target: {TARGET_NAME}"
)

print(
    f"Standard code: {STANDARD_CODE}"
)

print(
    f"Endpoint input: {ENDPOINT_INPUT_PATH}"
)

print(
    f"Verification input: {VERIFICATION_INPUT_PATH}"
)

print()


if not ENDPOINT_INPUT_PATH.exists():

    raise FileNotFoundError(
        "H-stage endpoint input not found: "
        f"{ENDPOINT_INPUT_PATH}"
    )


if not VERIFICATION_INPUT_PATH.exists():

    raise FileNotFoundError(
        "Target verification input not found: "
        f"{VERIFICATION_INPUT_PATH}"
    )


endpoint_data = json.loads(
    ENDPOINT_INPUT_PATH.read_text(
        encoding="utf-8"
    )
)

verification_data = json.loads(
    VERIFICATION_INPUT_PATH.read_text(
        encoding="utf-8"
    )
)


# ============================================================
# INPUT NORMALIZATION
# ============================================================

searchable_endpoints = (
    load_searchable_endpoints(
        endpoint_data
    )
)

prior_excluded_urls = (
    load_prior_excluded_urls(
        verification_data
    )
)


print(
    "Searchable endpoint count:",
    len(
        searchable_endpoints
    ),
)

print(
    "Prior excluded target-document URL count:",
    len(
        prior_excluded_urls
    ),
)

print()


# ============================================================
# SESSION
# ============================================================

session = requests.Session()

session.headers.update(
    {
        "User-Agent":
            USER_AGENT,

        "Accept": (
            "text/html,"
            "application/xhtml+xml,"
            "application/xml;q=0.9,"
            "*/*;q=0.8"
        ),

        "Accept-Language": (
            "ko-KR,ko;q=0.9,"
            "en-US;q=0.7,en;q=0.5"
        ),
    }
)


# ============================================================
# DISCOVERY
# ============================================================

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0

raw_link_count = 0

classified_link_count = 0


endpoint_results: List[
    Dict[str, Any]
] = []

all_candidates: List[
    Dict[str, Any]
] = []


for endpoint_index, endpoint in enumerate(
    searchable_endpoints,
    start=1,
):

    region = normalize_space(
        endpoint.get(
            "region"
        )
    )

    endpoint_class = normalize_space(
        endpoint.get(
            "classification"
        )
    )

    endpoint_url = canonicalize_url(
        endpoint.get(
            "canonical_url"
        )
        or ""
    )

    print(
        "-" * 60
    )

    print(
        f"ENDPOINT {endpoint_index}: "
        f"{region or '-'}"
    )

    print(
        "Class:",
        endpoint_class,
    )

    print(
        "URL:",
        endpoint_url,
    )

    endpoint_request_count = 0
    endpoint_success_count = 0
    endpoint_error_count = 0

    endpoint_candidates: List[
        Dict[str, Any]
    ] = []

    search_variants: List[
        Tuple[
            str,
            str,
        ]
    ] = []

    # --------------------------------------------------------
    # Root endpoint 자체도 1회 probe
    # --------------------------------------------------------

    search_variants.append(
        (
            "",
            endpoint_url,
        )
    )

    # --------------------------------------------------------
    # GET query variants
    # --------------------------------------------------------

    for search_term in SEARCH_TERMS:

        urls = build_get_search_variants(
            endpoint_url,
            search_term,
        )

        for url in urls:

            search_variants.append(
                (
                    search_term,
                    url,
                )
            )

    # --------------------------------------------------------
    # exact duplicate 제거
    # --------------------------------------------------------

    deduped_variants: List[
        Tuple[
            str,
            str,
        ]
    ] = []

    seen_variant_urls: Set[str] = set()

    for (
        search_term,
        search_url,
    ) in search_variants:

        canonical_search_url = canonicalize_url(
            search_url
        )

        if not canonical_search_url:
            continue

        if canonical_search_url in seen_variant_urls:
            continue

        seen_variant_urls.add(
            canonical_search_url
        )

        deduped_variants.append(
            (
                search_term,
                canonical_search_url,
            )
        )

    deduped_variants = deduped_variants[
        :(
            1
            + MAX_SEARCH_VARIANTS_PER_ENDPOINT
            * len(
                SEARCH_TERMS
            )
        )
    ]

    for (
        search_term,
        search_url,
    ) in deduped_variants:

        request_count += 1

        endpoint_request_count += 1

        response = request_html(
            session,
            search_url,
        )

        if response[
            "http_status"
        ] == 200:

            http_success_count += 1

            endpoint_success_count += 1

        if response[
            "error"
        ]:

            transport_error_count += 1

            endpoint_error_count += 1

            continue

        raw_html = response[
            "html"
        ]

        if raw_html:

            html_parse_count += 1

        links = extract_links(
            response[
                "final_url"
            ]
            or search_url,
            raw_html,
        )

        raw_link_count += len(
            links
        )

        for link in links:

            candidate = classify_discovered_link(
                endpoint=endpoint,
                search_url=search_url,
                search_term=search_term,
                link=link,
                prior_excluded_urls=(
                    prior_excluded_urls
                ),
            )

            classified_link_count += 1

            endpoint_candidates.append(
                candidate
            )

            all_candidates.append(
                candidate
            )

        if REQUEST_DELAY_SECONDS > 0:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    class_counts = Counter(
        item[
            "classification"
        ]
        for item
        in endpoint_candidates
    )

    endpoint_result = {
        "region":
            region,

        "agency":
            normalize_space(
                endpoint.get(
                    "agency"
                )
            ),

        "classification":
            endpoint_class,

        "endpoint_url":
            endpoint_url,

        "request_count":
            endpoint_request_count,

        "http_success_count":
            endpoint_success_count,

        "transport_error_count":
            endpoint_error_count,

        "candidate_count":
            len(
                endpoint_candidates
            ),

        "classification_counts":
            dict(
                sorted(
                    class_counts.items()
                )
            ),
    }

    endpoint_results.append(
        endpoint_result
    )

    print(
        "Requests:",
        endpoint_request_count,
    )

    print(
        "HTTP success:",
        endpoint_success_count,
    )

    print(
        "Transport errors:",
        endpoint_error_count,
    )

    print(
        "Discovered candidates:",
        len(
            endpoint_candidates
        ),
    )


# ============================================================
# CANONICAL CANDIDATE DEDUPE
# ============================================================

CLASS_PRIORITY = {
    CLASS_TARGET_DIRECT:
        100,

    CLASS_ATTACHMENT:
        90,

    CLASS_EXTENSIONLESS:
        85,

    CLASS_URBAN_NOTICE:
        80,

    CLASS_GAZETTE_ISSUE:
        70,

    CLASS_LOW_CONFIDENCE:
        50,

    CLASS_EXCLUDED_ADMIN_DUTY:
        20,

    CLASS_EXCLUDED_GENERIC:
        10,
}


grouped_candidates: Dict[
    Tuple[
        str,
        str,
    ],
    List[
        Dict[str, Any]
    ],
] = defaultdict(
    list
)


for candidate in all_candidates:

    key = (
        candidate.get(
            "region"
        )
        or "",
        candidate.get(
            "url"
        )
        or "",
    )

    grouped_candidates[
        key
    ].append(
        candidate
    )


def choose_candidate_representative(
    group: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    ordered = sorted(
        group,
        key=lambda item: (
            -CLASS_PRIORITY.get(
                item.get(
                    "classification"
                ),
                0,
            ),
            -int(
                item.get(
                    "score"
                )
                or 0
            ),
            -int(
                item.get(
                    "target_in_label"
                )
                is True
            ),
            -int(
                item.get(
                    "target_in_local_context"
                )
                is True
            ),
            -len(
                item.get(
                    "label"
                )
                or ""
            ),
        ),
    )

    representative = dict(
        ordered[
            0
        ]
    )

    representative[
        "discovery_variant_count"
    ] = len(
        group
    )

    representative[
        "search_terms"
    ] = unique_strings(
        item.get(
            "search_term"
        )
        for item
        in group
    )

    representative[
        "search_urls"
    ] = unique_strings(
        item.get(
            "search_url"
        )
        for item
        in group
    )

    representative[
        "labels"
    ] = unique_strings(
        item.get(
            "label"
        )
        for item
        in group
    )

    representative[
        "all_reasons"
    ] = unique_strings(
        reason
        for item
        in group
        for reason
        in (
            item.get(
                "reasons"
            )
            or []
        )
    )

    representative[
        "all_notice_numbers"
    ] = unique_strings(
        notice
        for item
        in group
        for notice
        in (
            item.get(
                "notice_numbers"
            )
            or []
        )
    )

    representative[
        "all_dates"
    ] = unique_strings(
        date
        for item
        in group
        for date
        in (
            item.get(
                "dates"
            )
            or []
        )
    )

    representative[
        "final_positive"
    ] = False

    return representative


canonical_candidates = [
    choose_candidate_representative(
        group
    )
    for group
    in grouped_candidates.values()
    if (
        group
        and (
            group[
                0
            ].get(
                "url"
            )
            or ""
        )
    )
]


canonical_candidates.sort(
    key=lambda item: (
        -CLASS_PRIORITY.get(
            item.get(
                "classification"
            ),
            0,
        ),
        -int(
            item.get(
                "score"
            )
            or 0
        ),
        str(
            item.get(
                "region"
            )
            or ""
        ),
        str(
            item.get(
                "url"
            )
            or ""
        ),
    )
)


# ============================================================
# SPLIT CLASSES
# ============================================================

target_direct_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_TARGET_DIRECT
]

urban_notice_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_URBAN_NOTICE
]

gazette_issue_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_GAZETTE_ISSUE
]

attachment_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_ATTACHMENT
]

extensionless_download_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_EXTENSIONLESS
]

low_confidence_seeds = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_LOW_CONFIDENCE
]

excluded_admin_duty = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_EXCLUDED_ADMIN_DUTY
]

excluded_generic = [
    item
    for item
    in canonical_candidates
    if item.get(
        "classification"
    )
    == CLASS_EXCLUDED_GENERIC
]


# ============================================================
# NEXT-STAGE VERIFICATION POOL
# ============================================================

next_stage_verification_pool = (
    target_direct_seeds
    + attachment_seeds
    + extensionless_download_seeds
    + urban_notice_seeds
    + gazette_issue_seeds
)

next_stage_verification_pool.sort(
    key=lambda item: (
        -CLASS_PRIORITY.get(
            item.get(
                "classification"
            ),
            0,
        ),
        -int(
            item.get(
                "score"
            )
            or 0
        ),
        str(
            item.get(
                "region"
            )
            or ""
        ),
    )
)


# ============================================================
# SUMMARY
# ============================================================

classification_counts = Counter(
    item.get(
        "classification"
    )
    for item
    in canonical_candidates
)


# ============================================================
# RESOLUTION
# ============================================================

if target_direct_seeds:

    resolution = (
        "OFFICIAL_NOTICE_RECOVERY_TARGET_DIRECT_SEED_DISCOVERED"
    )

    next_action = (
        "link-local evidence로 확인된 TARGET_DIRECT_DETAIL_SEED와 "
        "직접 attachment/download seed를 실제 HTTP 조회하여 "
        "원문 전체 text를 추출하고, 개발밀도관리구역 "
        "지정·변경·해제 action context, 고시번호, 고시일, "
        "행정구역, 지정 범위를 검증한다."
    )

elif next_stage_verification_pool:

    resolution = (
        "OFFICIAL_NOTICE_RECOVERY_DOCUMENT_SEED_DISCOVERED"
    )

    next_action = (
        "link-local evidence contract를 통과한 도시계획 고시/detail/"
        "gazette/attachment seed를 개별 원문 조회하여 "
        "target exact phrase와 고시번호를 검증한다. "
        "이 단계의 seed 자체는 final positive가 아니다."
    )

else:

    resolution = (
        "OFFICIAL_NOTICE_RECOVERY_COMPLETED_NO_VERIFICATION_SEED"
    )

    next_action = (
        "현재 공식 endpoint의 link-local evidence 기반 탐색에서는 "
        "검증 가능한 고시 seed를 확보하지 못했다. "
        "국가기록원·관보·토지이음·지자체 구형 공보 archive 또는 "
        "고시번호 역탐색으로 확장한다."
    )


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-I "
        "Development Density Management Area "
        "Official Notice Recovery Discovery"
    ),

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            STANDARD_CODE,
    },

    "inputs": {
        "endpoint_refinement":
            str(
                ENDPOINT_INPUT_PATH
            ),

        "target_document_verification":
            str(
                VERIFICATION_INPUT_PATH
            ),

        "endpoint_resolution":
            endpoint_data.get(
                "resolution"
            ),

        "verification_resolution":
            verification_data.get(
                "resolution"
            ),
    },

    "method": {
        "official_endpoint_only":
            True,

        "allowed_endpoint_classes":
            sorted(
                ALLOWED_ENDPOINT_CLASSES
            ),

        "search_engine_scraping":
            False,

        "direct_http_search_probe":
            True,

        "target_exact_phrase_search":
            True,

        "detail_seed_discovery":
            True,

        "attachment_seed_discovery":
            True,

        "extensionless_download_discovery":
            True,

        "administrative_duty_false_positive_guard":
            True,

        "prior_false_positive_url_guard":
            True,

        # ----------------------------------------------------
        # New I-stage evidence contract
        # ----------------------------------------------------

        "link_local_evidence":
            True,

        "page_level_evidence_inheritance":
            False,

        "external_navigation_guard":
            True,

        "root_navigation_guard":
            True,

        "attachment_local_relevance_guard":
            True,

        "notice_number_local_scope":
            True,

        "date_local_scope":
            True,

        "target_local_scope":
            True,

        "search_page_final_positive_allowed":
            False,

        "detail_seed_final_positive_allowed":
            False,

        "attachment_final_positive_allowed":
            False,
    },

    "summary": {
        "searchable_endpoint_count":
            len(
                searchable_endpoints
            ),

        "prior_excluded_url_count":
            len(
                prior_excluded_urls
            ),

        "request_count":
            request_count,

        "http_success_count":
            http_success_count,

        "transport_error_count":
            transport_error_count,

        "html_parse_count":
            html_parse_count,

        "raw_link_count":
            raw_link_count,

        "classified_link_count":
            classified_link_count,

        "canonical_candidate_count":
            len(
                canonical_candidates
            ),

        "target_direct_seed_count":
            len(
                target_direct_seeds
            ),

        "urban_notice_seed_count":
            len(
                urban_notice_seeds
            ),

        "gazette_issue_seed_count":
            len(
                gazette_issue_seeds
            ),

        "attachment_seed_count":
            len(
                attachment_seeds
            ),

        "extensionless_download_seed_count":
            len(
                extensionless_download_seeds
            ),

        "low_confidence_seed_count":
            len(
                low_confidence_seeds
            ),

        "excluded_administrative_duty_count":
            len(
                excluded_admin_duty
            ),

        "excluded_generic_count":
            len(
                excluded_generic
            ),

        "next_stage_verification_pool_count":
            len(
                next_stage_verification_pool
            ),
    },

    "classification_counts":
        dict(
            sorted(
                classification_counts.items()
            )
        ),

    "endpoint_results":
        endpoint_results,

    "target_direct_seeds":
        target_direct_seeds,

    "urban_notice_seeds":
        urban_notice_seeds,

    "gazette_issue_seeds":
        gazette_issue_seeds,

    "attachment_seeds":
        attachment_seeds,

    "extensionless_download_seeds":
        extensionless_download_seeds,

    "low_confidence_seeds":
        low_confidence_seeds,

    "excluded_administrative_duty_references":
        excluded_admin_duty,

    "excluded_generic_links":
        excluded_generic,

    "next_stage_verification_pool":
        next_stage_verification_pool,

    "all_canonical_candidates":
        canonical_candidates,

    "resolution":
        resolution,

    "next_action":
        next_action,

    "runtime_registration_allowed":
        False,

    "site_positive_allowed":
        False,

    "final_positive_promotion_allowed":
        False,
}


OUTPUT_PATH.write_text(
    json.dumps(
        output_data,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# CONSOLE RESULT
# ============================================================

print()

print(
    "=" * 60
)

print(
    "DISCOVERY RESULT"
)

print(
    "=" * 60
)

print(
    "Searchable endpoint count:",
    len(
        searchable_endpoints
    ),
)

print(
    "Request count:",
    request_count,
)

print(
    "HTTP success count:",
    http_success_count,
)

print(
    "Transport error count:",
    transport_error_count,
)

print(
    "HTML parse count:",
    html_parse_count,
)

print(
    "Raw link count:",
    raw_link_count,
)

print(
    "Canonical candidate count:",
    len(
        canonical_candidates
    ),
)

print()

print(
    f"{CLASS_TARGET_DIRECT}:",
    len(
        target_direct_seeds
    ),
)

print(
    f"{CLASS_URBAN_NOTICE}:",
    len(
        urban_notice_seeds
    ),
)

print(
    f"{CLASS_GAZETTE_ISSUE}:",
    len(
        gazette_issue_seeds
    ),
)

print(
    f"{CLASS_ATTACHMENT}:",
    len(
        attachment_seeds
    ),
)

print(
    f"{CLASS_EXTENSIONLESS}:",
    len(
        extensionless_download_seeds
    ),
)

print(
    f"{CLASS_LOW_CONFIDENCE}:",
    len(
        low_confidence_seeds
    ),
)

print(
    f"{CLASS_EXCLUDED_ADMIN_DUTY}:",
    len(
        excluded_admin_duty
    ),
)

print(
    f"{CLASS_EXCLUDED_GENERIC}:",
    len(
        excluded_generic
    ),
)

print()

print(
    "Next-stage verification pool:",
    len(
        next_stage_verification_pool
    ),
)


# ============================================================
# PRINT HIGH VALUE
# ============================================================

def print_seed_group(
    title: str,
    items: List[
        Dict[str, Any]
    ],
    *,
    limit: int = 50,
) -> None:

    if not items:
        return

    print()

    print(
        title
    )

    print(
        "-" * 60
    )

    for index, item in enumerate(
        items[
            :limit
        ],
        start=1,
    ):

        print(
            f"[{index}] "
            f"{item.get('region') or '-'}"
        )

        print(
            "Class:",
            item.get(
                "classification"
            ),
        )

        print(
            "Score:",
            item.get(
                "score"
            ),
        )

        print(
            "Label:",
            item.get(
                "label"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print(
            "Target found:",
            item.get(
                "target_found"
            ),
        )

        print(
            "Target in label:",
            item.get(
                "target_in_label"
            ),
        )

        print(
            "Target in local context:",
            item.get(
                "target_in_local_context"
            ),
        )

        print(
            "Same organization:",
            item.get(
                "same_organization_domain"
            ),
        )

        print(
            "Notice numbers:",
            item.get(
                "all_notice_numbers"
            )
            or item.get(
                "notice_numbers"
            ),
        )

        print(
            "Dates:",
            item.get(
                "all_dates"
            )
            or item.get(
                "dates"
            ),
        )

        print(
            "Reasons:",
            item.get(
                "all_reasons"
            )
            or item.get(
                "reasons"
            ),
        )

        print()


print_seed_group(
    "TARGET DIRECT DETAIL SEEDS",
    target_direct_seeds,
)

print_seed_group(
    "URBAN NOTICE DETAIL SEEDS",
    urban_notice_seeds,
)

print_seed_group(
    "GAZETTE ISSUE SEEDS",
    gazette_issue_seeds,
)

print_seed_group(
    "ATTACHMENT DOCUMENT SEEDS",
    attachment_seeds,
)

print_seed_group(
    "EXTENSIONLESS DOWNLOAD SEEDS",
    extensionless_download_seeds,
)


# ============================================================
# RESOLUTION PRINT
# ============================================================

print(
    "=" * 60
)

print(
    "RESOLUTION"
)

print(
    "=" * 60
)

print(
    resolution
)

print()

print(
    next_action
)

print()

print(
    "Output:",
    OUTPUT_PATH,
)


# ============================================================
# VALIDATION
# ============================================================

canonical_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in canonical_candidates
}


verification_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "url"
        ),
    )
    for item
    in next_stage_verification_pool
}


all_classes_valid = all(
    item.get(
        "classification"
    )
    in VALID_CANDIDATE_CLASSES
    for item
    in canonical_candidates
)


all_candidate_urls_exist = all(
    bool(
        item.get(
            "url"
        )
    )
    for item
    in canonical_candidates
)


no_search_page_final_positive = all(
    item.get(
        "final_positive"
    )
    is False
    for item
    in canonical_candidates
)


verification_pool_allowed_classes = all(
    item.get(
        "classification"
    )
    in {
        CLASS_TARGET_DIRECT,
        CLASS_URBAN_NOTICE,
        CLASS_GAZETTE_ISSUE,
        CLASS_ATTACHMENT,
        CLASS_EXTENSIONLESS,
    }
    for item
    in next_stage_verification_pool
)


admin_duty_leakage = sum(
    1
    for item
    in next_stage_verification_pool
    if item.get(
        "administrative_duty_reference"
    )
    is True
)


generic_navigation_leakage = sum(
    1
    for item
    in next_stage_verification_pool
    if item.get(
        "generic_navigation"
    )
    is True
)


external_navigation_leakage = sum(
    1
    for item
    in next_stage_verification_pool
    if item.get(
        "external_navigation"
    )
    is True
)


root_navigation_leakage = sum(
    1
    for item
    in next_stage_verification_pool
    if item.get(
        "root_navigation"
    )
    is True
)


page_level_evidence_inheritance_leakage = sum(
    1
    for item
    in canonical_candidates
    if item.get(
        "page_level_evidence_inherited"
    )
    is True
)


target_direct_without_local_target = sum(
    1
    for item
    in target_direct_seeds
    if not (
        item.get(
            "target_in_label"
        )
        is True
        or item.get(
            "target_in_local_context"
        )
        is True
    )
)


unrelated_attachment_promotion = sum(
    1
    for item
    in next_stage_verification_pool
    if (
        item.get(
            "classification"
        )
        in {
            CLASS_ATTACHMENT,
            CLASS_EXTENSIONLESS,
        }
        and item.get(
            "attachment_locally_relevant"
        )
        is not True
    )
)


prior_excluded_url_leakage = sum(
    1
    for item
    in next_stage_verification_pool
    if item.get(
        "url"
    )
    in prior_excluded_urls
)


notice_scope_violation = sum(
    1
    for item
    in canonical_candidates
    if (
        item.get(
            "notice_numbers"
        )
        and not item.get(
            "local_context"
        )
        and not item.get(
            "label"
        )
    )
)


validations = {
    "target name": (
        TARGET_NAME
        == "개발밀도관리구역"
    ),

    "standard code": (
        STANDARD_CODE
        == "UQQ700"
    ),

    "endpoint input exists": (
        ENDPOINT_INPUT_PATH.exists()
    ),

    "verification input exists": (
        VERIFICATION_INPUT_PATH.exists()
    ),

    "H-stage endpoint input parsed": (
        isinstance(
            endpoint_data,
            dict,
        )
    ),

    "Y-stage verification input parsed": (
        isinstance(
            verification_data,
            dict,
        )
    ),

    "searchable endpoints loaded": (
        len(
            searchable_endpoints
        )
        > 0
    ),

    "only allowed endpoint classes executed": all(
        item.get(
            "classification"
        )
        in ALLOWED_ENDPOINT_CLASSES
        for item
        in searchable_endpoints
    ),

    "official endpoint direct probe enabled": (
        output_data[
            "method"
        ][
            "official_endpoint_only"
        ]
        is True
    ),

    "search engine scraping disabled": (
        output_data[
            "method"
        ][
            "search_engine_scraping"
        ]
        is False
    ),

    "target exact phrase search enabled": (
        output_data[
            "method"
        ][
            "target_exact_phrase_search"
        ]
        is True
    ),

    "detail seed discovery enabled": (
        output_data[
            "method"
        ][
            "detail_seed_discovery"
        ]
        is True
    ),

    "attachment discovery enabled": (
        output_data[
            "method"
        ][
            "attachment_seed_discovery"
        ]
        is True
    ),

    "extensionless discovery enabled": (
        output_data[
            "method"
        ][
            "extensionless_download_discovery"
        ]
        is True
    ),

    "administrative-duty false-positive guard enabled": (
        output_data[
            "method"
        ][
            "administrative_duty_false_positive_guard"
        ]
        is True
    ),

    "prior false-positive URL guard enabled": (
        output_data[
            "method"
        ][
            "prior_false_positive_url_guard"
        ]
        is True
    ),

    # --------------------------------------------------------
    # New regression guards
    # --------------------------------------------------------

    "link-local evidence enabled": (
        output_data[
            "method"
        ][
            "link_local_evidence"
        ]
        is True
    ),

    "page-level evidence inheritance disabled": (
        output_data[
            "method"
        ][
            "page_level_evidence_inheritance"
        ]
        is False
        and page_level_evidence_inheritance_leakage
        == 0
    ),

    "external navigation guard enabled": (
        output_data[
            "method"
        ][
            "external_navigation_guard"
        ]
        is True
    ),

    "root navigation guard enabled": (
        output_data[
            "method"
        ][
            "root_navigation_guard"
        ]
        is True
    ),

    "attachment local relevance guard enabled": (
        output_data[
            "method"
        ][
            "attachment_local_relevance_guard"
        ]
        is True
    ),

    "notice numbers are local-container scoped": (
        output_data[
            "method"
        ][
            "notice_number_local_scope"
        ]
        is True
        and notice_scope_violation
        == 0
    ),

    "dates are local-container scoped": (
        output_data[
            "method"
        ][
            "date_local_scope"
        ]
        is True
    ),

    "target evidence is local-container scoped": (
        output_data[
            "method"
        ][
            "target_local_scope"
        ]
        is True
    ),

    "requests executed": (
        request_count
        > 0
        if searchable_endpoints
        else True
    ),

    "canonical candidates unique": (
        len(
            canonical_keys
        )
        == len(
            canonical_candidates
        )
    ),

    "all candidate classes valid": (
        all_classes_valid
    ),

    "all candidate URLs exist": (
        all_candidate_urls_exist
    ),

    "verification pool unique": (
        len(
            verification_keys
        )
        == len(
            next_stage_verification_pool
        )
    ),

    "verification pool contains only allowed classes": (
        verification_pool_allowed_classes
    ),

    "search/list page final positive prohibited": (
        no_search_page_final_positive
    ),

    "administrative-duty leakage zero": (
        admin_duty_leakage
        == 0
    ),

    "generic navigation leakage zero": (
        generic_navigation_leakage
        == 0
    ),

    "external navigation promotion zero": (
        external_navigation_leakage
        == 0
    ),

    "homepage/root navigation promotion zero": (
        root_navigation_leakage
        == 0
    ),

    "target direct seed requires local target evidence": (
        target_direct_without_local_target
        == 0
    ),

    "unrelated attachment promotion zero": (
        unrelated_attachment_promotion
        == 0
    ),

    "prior excluded document leakage zero": (
        prior_excluded_url_leakage
        == 0
    ),

    "runtime registration remains blocked": (
        output_data[
            "runtime_registration_allowed"
        ]
        is False
    ),

    "SITE FALSE remains blocked": (
        output_data[
            "site_positive_allowed"
        ]
        is False
    ),

    "final positive promotion remains blocked": (
        output_data[
            "final_positive_promotion_allowed"
        ]
        is False
    ),

    "output written": (
        OUTPUT_PATH.exists()
        and OUTPUT_PATH.stat().st_size
        > 0
    ),
}


print()

print(
    "=" * 60
)

print(
    "VALIDATION"
)

print(
    "=" * 60
)


for name, passed in validations.items():

    print(
        f"{name}: {passed}"
    )


print()

print(
    "Administrative-duty leakage:",
    admin_duty_leakage,
)

print(
    "Generic navigation leakage:",
    generic_navigation_leakage,
)

print(
    "External navigation leakage:",
    external_navigation_leakage,
)

print(
    "Root navigation leakage:",
    root_navigation_leakage,
)

print(
    "Page-level evidence inheritance leakage:",
    page_level_evidence_inheritance_leakage,
)

print(
    "Target-direct without local target:",
    target_direct_without_local_target,
)

print(
    "Unrelated attachment promotion:",
    unrelated_attachment_promotion,
)

print(
    "Prior excluded document leakage:",
    prior_excluded_url_leakage,
)


all_pass = all(
    validations.values()
)


print()

print(
    f"all_pass: {all_pass}"
)


if not all_pass:

    failed = [
        name
        for name, passed
        in validations.items()
        if not passed
    ]

    print()

    print(
        "FAILED:"
    )

    for name in failed:

        print(
            f"- {name}"
        )

    raise AssertionError(
        "Development density management area "
        "official notice recovery discovery "
        "regression failed"
    )