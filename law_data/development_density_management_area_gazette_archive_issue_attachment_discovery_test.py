# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-T
Development Density Management Area
Gazette Archive Issue / Attachment Discovery

목표
======================================================================
이전 단계에서 확보한 공식 공보 archive endpoint를 대상으로
실제 공보 게시물 행 / 호수 / 상세 URL / 첨부파일 URL을 추출한다.

공보 archive
    ↓
목록 페이지
    ↓
실제 게시물 행(row / item)
    ↓
제목 / 날짜 / 호수 / 고시·도시계획 문맥
    ↓
상세 URL
    ↓
PDF / HWP / HWPX / extensionless download endpoint
    ↓
다음 원문 검증 단계 seed

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 안전정책
======================================================================
1. 공보 목록 페이지 자체는 final positive가 아니다.
2. 단순 메뉴 링크 / 공통 navigation 링크는 candidate로 승격하지 않는다.
3. PDF / HWP / HWPX / extensionless download URL은
   원문 검증 전까지 seed일 뿐이다.
4. target text가 아직 발견되지 않아도 공보 issue/document seed는
   구조적 증거가 충분하면 수집할 수 있다.
5. 그러나 어떤 seed도 이번 단계에서 VERIFIED_POSITIVE가 될 수 없다.
6. 후보 0건은 SITE FALSE를 의미하지 않는다.
7. runtime spatial condition 등록은 계속 차단한다.
8. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.
9. 실제 원문 본문에서 target + action context + notice number가
   검증되기 전까지 condition은 UNKNOWN / UNRESOLVED 상태를 유지한다.

이번 단계 성공 조건
======================================================================
다음 중 하나면 성공이다.

A.
실제 공보 issue/detail/attachment seed 확보

B.
공식 archive를 정상 탐색했으나 seed 0건인 상태를
명시적으로 보존

즉 discovery regression이므로 0건도 테스트 실패가 아니다.
"""

from __future__ import annotations

import html
import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    unquote,
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

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

HISTORICAL_DISCOVERY_INPUT = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_archive_historical_discovery.json"
    )
)

STRONG_VERIFICATION_INPUT = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_historical_strong_detail_verification.json"
    )
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / (
        "development_density_management_area_"
        "gazette_archive_issue_attachment_discovery.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"

STANDARD_CODE = "UQQ700"


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20

REQUEST_SLEEP = 0.20

MAX_CONTENT_LENGTH = 3_000_000

MAX_ARCHIVE_PAGES_PER_ENDPOINT = 12

MAX_LINKS_PER_PAGE = 500

MAX_ITEMS_PER_PAGE = 250


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
    "Accept-Language": (
        "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7"
    ),
}


# ============================================================
# RELEVANCE TERMS
# ============================================================

TARGET_VARIANTS = [
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발 밀도 관리구역",
]


HIGH_RELEVANCE_TERMS = [
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발 밀도 관리구역",
    "도시관리계획",
    "도시계획",
    "지형도면",
    "용도지역",
    "용도지구",
    "용도구역",
]


NOTICE_TERMS = [
    "고시",
    "고시문",
    "공고",
    "공보",
    "시보",
    "구보",
    "군보",
    "지정",
    "결정",
    "변경",
    "해제",
]


URBAN_TERMS = [
    "도시관리계획",
    "도시계획",
    "지형도면",
    "개발",
    "밀도",
    "용도지역",
    "용도지구",
    "용도구역",
]


ACTION_TERMS = [
    "지정",
    "결정",
    "변경",
    "해제",
    "고시",
]


GENERIC_NAVIGATION_LABELS = {
    "",
    "홈",
    "메인",
    "목록",
    "이전",
    "다음",
    "처음",
    "마지막",
    "더보기",
    "바로가기",
    "새창",
    "검색",
    "검색하기",
    "전체",
    "전체보기",
    "맨위로",
    "top",
}


LIST_PATH_HINTS = [
    "/list.do",
    "/list.",
    "/board/list",
    "/bbs/list",
    "selectboardlist",
    "bbsmsglist",
]


DETAIL_PATH_HINTS = [
    "/view.do",
    "/detail.do",
    "/post/view",
    "selectboardarticle",
    "bbsmsgdetail",
    "announceDetail".lower(),
    "?act=view",
    "&act=view",
]


DOWNLOAD_HINTS = [
    "download",
    "filedown",
    "fileDown",
    "fileDownload",
    "filePreview",
    "atchFile",
    "attach",
    "fileSn",
    "file_id",
    "fileId",
    "fileSeq",
    "downFile",
]


ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)


BLOCKED_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".ico",
    ".mp3",
    ".mp4",
    ".avi",
    ".zip",
    ".7z",
    ".rar",
    ".xls",
    ".xlsx",
    ".doc",
    ".docx",
    ".ppt",
    ".pptx",
)


VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "jsessionid",
    "sessionid",
    "session",
    "timestamp",
    "_",
    "rnd",
    "random",
}


# ============================================================
# REGEX
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    <a
    \s+
    [^>]*?
    href
    \s*=\s*
    (?:
        "([^"]*)"
        |
        '([^']*)'
        |
        ([^\s>]+)
    )
    [^>]*>
    (.*?)
    </a>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


ONCLICK_PATTERN = re.compile(
    r"""
    onclick
    \s*=\s*
    (?:
        "([^"]*)"
        |
        '([^']*)'
    )
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


DATA_ATTRIBUTE_PATTERN = re.compile(
    r"""
    (data-[a-zA-Z0-9_-]+)
    \s*=\s*
    (?:
        "([^"]*)"
        |
        '([^']*)'
    )
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


TR_PATTERN = re.compile(
    r"<tr\b[^>]*>(.*?)</tr>",
    re.IGNORECASE | re.DOTALL,
)


LI_PATTERN = re.compile(
    r"<li\b[^>]*>(.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)


DL_PATTERN = re.compile(
    r"<dl\b[^>]*>(.*?)</dl>",
    re.IGNORECASE | re.DOTALL,
)


ARTICLE_PATTERN = re.compile(
    r"<article\b[^>]*>(.*?)</article>",
    re.IGNORECASE | re.DOTALL,
)


DIV_ITEM_PATTERN = re.compile(
    r"""
    <div
    \b
    [^>]*
    class
    \s*=\s*
    (?:
        "[^"]*
        (?:
            item|
            list|
            board|
            post|
            notice|
            gazette|
            news|
            row
        )
        [^"]*"
        |
        '[^']*
        (?:
            item|
            list|
            board|
            post|
            notice|
            gazette|
            news|
            row
        )
        [^']*'
    )
    [^>]*
    >
    (.*?)
    </div>
    """,
    re.IGNORECASE | re.DOTALL | re.VERBOSE,
)


DATE_PATTERN = re.compile(
    r"""
    (?P<year>20\d{2})
    \s*
    [.\-/년]
    \s*
    (?P<month>0?[1-9]|1[0-2])
    \s*
    [.\-/월]
    \s*
    (?P<day>0?[1-9]|[12]\d|3[01])
    \s*
    일?
    """,
    re.VERBOSE,
)


ISSUE_NUMBER_PATTERNS = [
    re.compile(
        r"""
        제
        \s*
        (?P<number>\d+)
        \s*
        호
        """,
        re.VERBOSE,
    ),
    re.compile(
        r"""
        (?P<year>20\d{2})
        \s*
        년
        \s*
        제?
        \s*
        (?P<number>\d+)
        \s*
        호
        """,
        re.VERBOSE,
    ),
]


NOTICE_NUMBER_PATTERNS = [
    re.compile(
        r"""
        (?:
            서울특별시|
            부산광역시|
            대구광역시|
            인천광역시|
            광주광역시|
            대전광역시|
            울산광역시|
            세종특별자치시|
            경기도|
            강원특별자치도|
            충청북도|
            충청남도|
            전북특별자치도|
            전라남도|
            경상북도|
            경상남도|
            제주특별자치도|
            [가-힣]+시|
            [가-힣]+군|
            [가-힣]+구
        )
        \s*
        (?:고시|공고)
        \s*
        제?
        \s*
        \d{4}
        \s*
        [-–]
        \s*
        \d+
        \s*
        호?
        """,
        re.VERBOSE,
    ),
    re.compile(
        r"""
        (?:고시|공고)
        \s*
        제?
        \s*
        \d{4}
        \s*
        [-–]
        \s*
        \d+
        \s*
        호?
        """,
        re.VERBOSE,
    ),
]


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class FetchResult:
    request_url: str
    final_url: Optional[str]
    http_status: Optional[int]
    content_type: str
    text: str
    error: Optional[str]


# ============================================================
# BASIC UTIL
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


def strip_html(
    source: str,
) -> str:

    value = re.sub(
        r"(?is)<script[^>]*>.*?</script>",
        " ",
        source,
    )

    value = re.sub(
        r"(?is)<style[^>]*>.*?</style>",
        " ",
        value,
    )

    value = re.sub(
        r"(?is)<[^>]+>",
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    return normalize_space(
        value
    )


def compact_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        "",
        normalize_space(
            value
        ),
    )


def contains_target(
    value: Any,
) -> bool:

    compact = compact_text(
        value
    )

    return any(
        compact_text(
            term
        )
        in compact
        for term in TARGET_VARIANTS
    )


def contains_any(
    value: Any,
    terms: Iterable[str],
) -> bool:

    text = normalize_space(
        value
    ).lower()

    return any(
        term.lower()
        in text
        for term in terms
    )


def count_matching_terms(
    value: Any,
    terms: Iterable[str],
) -> int:

    text = normalize_space(
        value
    ).lower()

    return sum(
        1
        for term in terms
        if term.lower()
        in text
    )


def build_preview(
    value: Any,
    max_length: int = 600,
) -> str:

    text = normalize_space(
        value
    )

    if len(
        text
    ) <= max_length:

        return text

    return (
        text[:max_length]
        + "..."
    )


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: Any,
) -> str:

    raw = html.unescape(
        str(
            url
            or ""
        )
    ).strip()

    if not raw:

        return ""

    try:

        parsed = urlparse(
            raw
        )

    except Exception:

        return raw

    query_items = []

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        if key.lower() in VOLATILE_QUERY_KEYS:

            continue

        query_items.append(
            (
                key,
                value,
            )
        )

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    path = re.sub(
        r";jsessionid=[^/?#]+",
        "",
        parsed.path,
        flags=re.IGNORECASE,
    )

    return urlunparse(
        parsed._replace(
            path=path,
            query=urlencode(
                query_items,
                doseq=True,
            ),
            fragment="",
        )
    )


def same_or_subdomain(
    url: str,
    base_url: str,
) -> bool:

    try:

        target_host = (
            urlparse(
                url
            ).hostname
            or ""
        ).lower()

        base_host = (
            urlparse(
                base_url
            ).hostname
            or ""
        ).lower()

    except Exception:

        return False

    if not (
        target_host
        and base_host
    ):

        return False

    return (
        target_host == base_host
        or target_host.endswith(
            "." + base_host
        )
        or base_host.endswith(
            "." + target_host
        )
    )


def is_http_url(
    url: str,
) -> bool:

    return url.startswith(
        (
            "http://",
            "https://",
        )
    )


def is_search_url(
    url: str,
) -> bool:

    lower = url.lower()

    return any(
        hint in lower
        for hint in (
            "/search",
            "search.do",
            "search.jsp",
            "totalsearch",
            "total_search",
        )
    )


def is_list_url(
    url: str,
) -> bool:

    lower = url.lower()

    return any(
        hint.lower()
        in lower
        for hint in LIST_PATH_HINTS
    )


def is_detail_url(
    url: str,
) -> bool:

    lower = url.lower()

    if any(
        hint.lower()
        in lower
        for hint in DETAIL_PATH_HINTS
    ):

        return True

    path = (
        urlparse(
            url
        ).path
        or ""
    )

    numeric_segments = [
        segment
        for segment in path.split("/")
        if segment.isdigit()
    ]

    return bool(
        numeric_segments
    )


def is_attachment_url(
    url: str,
) -> bool:

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    return any(
        path.endswith(
            extension
        )
        for extension
        in ATTACHMENT_EXTENSIONS
    )


def attachment_extension(
    url: str,
) -> Optional[str]:

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    for extension in ATTACHMENT_EXTENSIONS:

        if path.endswith(
            extension
        ):

            return extension[
                1:
            ]

    return None


def is_extensionless_download_url(
    url: str,
) -> bool:

    if is_attachment_url(
        url
    ):

        return False

    lower = unquote(
        url
    ).lower()

    if not any(
        hint.lower()
        in lower
        for hint in DOWNLOAD_HINTS
    ):

        return False

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    if any(
        path.endswith(
            extension
        )
        for extension
        in BLOCKED_EXTENSIONS
    ):

        return False

    return True


def is_blocked_asset_url(
    url: str,
) -> bool:

    path = (
        urlparse(
            url
        ).path
        or ""
    ).lower()

    return any(
        path.endswith(
            extension
        )
        for extension
        in BLOCKED_EXTENSIONS
    )


# ============================================================
# FETCH
# ============================================================

def fetch_url(
    url: str,
) -> FetchResult:

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:

        return FetchResult(
            request_url=url,
            final_url=None,
            http_status=None,
            content_type="",
            text="",
            error=repr(
                exc
            ),
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        or ""
    )

    text = ""

    lower_content_type = (
        content_type.lower()
    )

    if (
        "text/" in lower_content_type
        or "html" in lower_content_type
        or "xml" in lower_content_type
        or "json" in lower_content_type
    ):

        text = (
            response.text
            or ""
        )

        if len(
            text
        ) > MAX_CONTENT_LENGTH:

            text = text[
                :MAX_CONTENT_LENGTH
            ]

    return FetchResult(
        request_url=url,
        final_url=response.url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
    )


# ============================================================
# LOAD INPUT
# ============================================================

if not HISTORICAL_DISCOVERY_INPUT.exists():

    raise FileNotFoundError(
        f"Input not found: {HISTORICAL_DISCOVERY_INPUT}"
    )


historical_data = json.loads(
    HISTORICAL_DISCOVERY_INPUT.read_text(
        encoding="utf-8",
    )
)


strong_verification_data: Dict[str, Any] = {}

if STRONG_VERIFICATION_INPUT.exists():

    try:

        strong_verification_data = json.loads(
            STRONG_VERIFICATION_INPUT.read_text(
                encoding="utf-8",
            )
        )

    except Exception:

        strong_verification_data = {}


# ============================================================
# INPUT EXTRACTION
# ============================================================

def extract_archive_endpoint_records(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    candidate_lists: List[Any] = []

    for key in (
        "archive_results",
        "endpoint_results",
        "gazette_archive_endpoints",
        "archives",
        "site_results",
    ):

        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            candidate_lists.append(
                value
            )

    nested = data.get(
        "input"
    )

    if isinstance(
        nested,
        dict,
    ):

        for key in (
            "gazette_archive_endpoints",
            "next_stage_endpoints",
            "canonical_endpoints",
        ):

            value = nested.get(
                key
            )

            if isinstance(
                value,
                list,
            ):

                candidate_lists.append(
                    value
                )

    flattened: List[
        Dict[str, Any]
    ] = []

    for values in candidate_lists:

        for item in values:

            if not isinstance(
                item,
                dict,
            ):

                continue

            classification = normalize_space(
                item.get(
                    "classification"
                )
                or item.get(
                    "class"
                )
                or item.get(
                    "endpoint_class"
                )
            )

            label = normalize_space(
                item.get(
                    "label"
                )
                or item.get(
                    "archive_label"
                )
                or ""
            )

            url = normalize_url(
                item.get(
                    "canonical_url"
                )
                or item.get(
                    "url"
                )
                or item.get(
                    "archive_url"
                )
                or ""
            )

            region = normalize_space(
                item.get(
                    "region"
                )
                or item.get(
                    "agency"
                )
                or ""
            )

            agency = normalize_space(
                item.get(
                    "agency"
                )
                or region
            )

            gazette_evidence = (
                classification
                == "GAZETTE_ARCHIVE"
                or contains_any(
                    label,
                    [
                        "시보",
                        "구보",
                        "군보",
                        "공보",
                    ],
                )
            )

            if not (
                url
                and gazette_evidence
            ):

                continue

            flattened.append(
                {
                    "region": region,
                    "agency": agency,
                    "label": label,
                    "url": url,
                    "classification": (
                        classification
                        or "GAZETTE_ARCHIVE"
                    ),
                    "source_record": item,
                }
            )

    # historical discovery에서 endpoint 결과가 직접 발견되지 않을 때
    # 기존 알려진 archive_results의 archive_url 형태를 다시 검사한다.

    if not flattened:

        for key, value in data.items():

            if not isinstance(
                value,
                list,
            ):

                continue

            for item in value:

                if not isinstance(
                    item,
                    dict,
                ):

                    continue

                url = normalize_url(
                    item.get(
                        "archive_url"
                    )
                    or item.get(
                        "endpoint_url"
                    )
                    or item.get(
                        "url"
                    )
                    or ""
                )

                label = normalize_space(
                    item.get(
                        "label"
                    )
                    or item.get(
                        "archive_label"
                    )
                    or ""
                )

                if not (
                    url
                    and contains_any(
                        label,
                        [
                            "시보",
                            "구보",
                            "군보",
                            "공보",
                        ],
                    )
                ):

                    continue

                flattened.append(
                    {
                        "region": normalize_space(
                            item.get(
                                "region"
                            )
                        ),
                        "agency": normalize_space(
                            item.get(
                                "agency"
                            )
                            or item.get(
                                "region"
                            )
                        ),
                        "label": label,
                        "url": url,
                        "classification": "GAZETTE_ARCHIVE",
                        "source_record": item,
                    }
                )

    deduped = []

    seen = set()

    for item in flattened:

        key = (
            item.get(
                "region"
            ),
            normalize_url(
                item.get(
                    "url"
                )
            ),
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        deduped.append(
            item
        )

    return deduped


archive_endpoints = extract_archive_endpoint_records(
    historical_data
)


# ============================================================
# HTML LINK EXTRACTION
# ============================================================

def extract_anchor_records(
    source: str,
    *,
    base_url: str,
) -> List[Dict[str, Any]]:

    results: List[
        Dict[str, Any]
    ] = []

    seen = set()

    for match in ANCHOR_PATTERN.finditer(
        source
    ):

        href = (
            match.group(1)
            or match.group(2)
            or match.group(3)
            or ""
        ).strip()

        inner_html = (
            match.group(4)
            or ""
        )

        label = strip_html(
            inner_html
        )

        if not href:

            continue

        lower = href.lower()

        if lower.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#",
            )
        ):

            continue

        absolute = normalize_url(
            urljoin(
                base_url,
                html.unescape(
                    href
                ),
            )
        )

        if not is_http_url(
            absolute
        ):

            continue

        key = (
            absolute,
            label,
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        results.append(
            {
                "url": absolute,
                "label": label,
                "inner_html": inner_html,
            }
        )

        if len(
            results
        ) >= MAX_LINKS_PER_PAGE:

            break

    return results


def extract_javascript_and_data_urls(
    block_html: str,
    *,
    base_url: str,
) -> List[Dict[str, Any]]:

    results: List[
        Dict[str, Any]
    ] = []

    seen = set()

    # --------------------------------------------------------
    # onclick 문자열
    # --------------------------------------------------------

    for match in ONCLICK_PATTERN.finditer(
        block_html
    ):

        onclick = (
            match.group(1)
            or match.group(2)
            or ""
        )

        if not onclick:

            continue

        url_candidates = re.findall(
            r"""['"]([^'"]+(?:\.do|\.jsp|\.asp|\.web|\.htm|\.html)(?:\?[^'"]*)?)['"]""",
            onclick,
            flags=re.IGNORECASE,
        )

        for candidate in url_candidates:

            absolute = normalize_url(
                urljoin(
                    base_url,
                    html.unescape(
                        candidate
                    ),
                )
            )

            if not is_http_url(
                absolute
            ):

                continue

            if absolute in seen:

                continue

            seen.add(
                absolute
            )

            results.append(
                {
                    "url": absolute,
                    "source": "ONCLICK",
                    "raw": onclick,
                }
            )

    # --------------------------------------------------------
    # data-* 속성
    # --------------------------------------------------------

    for match in DATA_ATTRIBUTE_PATTERN.finditer(
        block_html
    ):

        key = (
            match.group(1)
            or ""
        )

        value = (
            match.group(2)
            or match.group(3)
            or ""
        )

        if not value:

            continue

        if value.startswith(
            (
                "/",
                "http://",
                "https://",
            )
        ):

            absolute = normalize_url(
                urljoin(
                    base_url,
                    html.unescape(
                        value
                    ),
                )
            )

            if (
                is_http_url(
                    absolute
                )
                and absolute not in seen
            ):

                seen.add(
                    absolute
                )

                results.append(
                    {
                        "url": absolute,
                        "source": key,
                        "raw": value,
                    }
                )

    return results


# ============================================================
# ITEM BLOCK EXTRACTION
# ============================================================

def extract_structural_blocks(
    source: str,
) -> List[Tuple[str, str]]:

    results: List[
        Tuple[
            str,
            str,
        ]
    ] = []

    seen = set()

    patterns = [
        (
            "TR",
            TR_PATTERN,
        ),
        (
            "LI",
            LI_PATTERN,
        ),
        (
            "DL",
            DL_PATTERN,
        ),
        (
            "ARTICLE",
            ARTICLE_PATTERN,
        ),
        (
            "DIV",
            DIV_ITEM_PATTERN,
        ),
    ]

    for block_type, pattern in patterns:

        for match in pattern.finditer(
            source
        ):

            block = (
                match.group(0)
                if match.lastindex is None
                else match.group(0)
            )

            normalized = normalize_space(
                block
            )

            if len(
                normalized
            ) < 20:

                continue

            signature = normalized[
                :800
            ]

            if signature in seen:

                continue

            seen.add(
                signature
            )

            results.append(
                (
                    block_type,
                    block,
                )
            )

            if len(
                results
            ) >= MAX_ITEMS_PER_PAGE:

                return results

    return results


# ============================================================
# METADATA EXTRACTION
# ============================================================

def extract_dates(
    text: Any,
) -> List[str]:

    results = []

    seen = set()

    value = normalize_space(
        text
    )

    for match in DATE_PATTERN.finditer(
        value
    ):

        try:

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

        except (
            TypeError,
            ValueError,
        ):

            continue

        if not (
            1 <= month <= 12
            and 1 <= day <= 31
        ):

            continue

        date_value = (
            f"{year:04d}-"
            f"{month:02d}-"
            f"{day:02d}"
        )

        if date_value in seen:

            continue

        seen.add(
            date_value
        )

        results.append(
            date_value
        )

    return results


def extract_issue_numbers(
    text: Any,
) -> List[str]:

    value = normalize_space(
        text
    )

    results = []

    seen = set()

    for pattern in ISSUE_NUMBER_PATTERNS:

        for match in pattern.finditer(
            value
        ):

            matched = normalize_space(
                match.group(
                    0
                )
            )

            if (
                matched
                and matched not in seen
            ):

                seen.add(
                    matched
                )

                results.append(
                    matched
                )

    return results


def extract_notice_numbers(
    text: Any,
) -> List[str]:

    value = normalize_space(
        text
    )

    results = []

    seen = set()

    for pattern in NOTICE_NUMBER_PATTERNS:

        for match in pattern.finditer(
            value
        ):

            matched = normalize_space(
                match.group(
                    0
                )
            )

            if (
                matched
                and matched not in seen
            ):

                seen.add(
                    matched
                )

                results.append(
                    matched
                )

    return results


# ============================================================
# PAGINATION DISCOVERY
# ============================================================

PAGINATION_KEYS = [
    "page",
    "pageIndex",
    "pageIdx",
    "pageNum",
    "curPage",
    "cpage",
    "gotopage",
    "currentPageNo",
    "page.pageNo",
]


def detect_existing_pagination_keys(
    url: str,
    source: str,
) -> List[str]:

    found = set()

    parsed = urlparse(
        url
    )

    for key, _ in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        if key in PAGINATION_KEYS:

            found.add(
                key
            )

    for key in PAGINATION_KEYS:

        if re.search(
            rf"""
            (?:
                name|
                id
            )
            \s*=\s*
            ["']
            {re.escape(key)}
            ["']
            """,
            source,
            flags=re.IGNORECASE | re.VERBOSE,
        ):

            found.add(
                key
            )

        if re.search(
            rf"""
            [?&]
            {re.escape(key)}
            =
            \d+
            """,
            source,
            flags=re.IGNORECASE | re.VERBOSE,
        ):

            found.add(
                key
            )

    return sorted(
        found
    )


def build_pagination_urls(
    base_url: str,
    pagination_keys: List[str],
) -> List[str]:

    if not pagination_keys:

        return []

    results = []

    seen = set()

    parsed = urlparse(
        base_url
    )

    base_query = dict(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    # 공보가 오래된 경우 현재 page 근처만 보면 의미가 적으므로
    # 1~12 페이지를 구조적으로 확인한다.

    for page_number in range(
        1,
        MAX_ARCHIVE_PAGES_PER_ENDPOINT + 1,
    ):

        for key in pagination_keys:

            query = dict(
                base_query
            )

            query[
                key
            ] = str(
                page_number
            )

            candidate = normalize_url(
                urlunparse(
                    parsed._replace(
                        query=urlencode(
                            query,
                            doseq=True,
                        )
                    )
                )
            )

            if candidate in seen:

                continue

            seen.add(
                candidate
            )

            results.append(
                candidate
            )

    return results


# ============================================================
# ITEM RELEVANCE
# ============================================================

def is_generic_navigation_label(
    label: Any,
) -> bool:

    normalized = normalize_space(
        label
    ).lower()

    if normalized in GENERIC_NAVIGATION_LABELS:

        return True

    if re.fullmatch(
        r"\d+",
        normalized,
    ):

        return True

    return False


def compute_item_score(
    *,
    text: str,
    label: str,
    detail_urls: List[str],
    attachment_urls: List[str],
    extensionless_download_urls: List[str],
    issue_numbers: List[str],
    notice_numbers: List[str],
    dates: List[str],
) -> Tuple[int, List[str]]:

    score = 0

    reasons = []

    combined = normalize_space(
        label
        + " "
        + text
    )

    if contains_target(
        combined
    ):

        score += 12

        reasons.append(
            "TARGET_TEXT"
        )

    high_hits = count_matching_terms(
        combined,
        HIGH_RELEVANCE_TERMS,
    )

    if high_hits:

        score += min(
            high_hits * 3,
            9,
        )

        reasons.append(
            "HIGH_RELEVANCE_TERMS"
        )

    notice_hits = count_matching_terms(
        combined,
        NOTICE_TERMS,
    )

    if notice_hits:

        score += min(
            notice_hits * 2,
            6,
        )

        reasons.append(
            "NOTICE_CONTEXT"
        )

    urban_hits = count_matching_terms(
        combined,
        URBAN_TERMS,
    )

    if urban_hits:

        score += min(
            urban_hits * 2,
            6,
        )

        reasons.append(
            "URBAN_CONTEXT"
        )

    action_hits = count_matching_terms(
        combined,
        ACTION_TERMS,
    )

    if action_hits:

        score += min(
            action_hits,
            4,
        )

        reasons.append(
            "ACTION_CONTEXT"
        )

    if issue_numbers:

        score += 3

        reasons.append(
            "ISSUE_NUMBER"
        )

    if notice_numbers:

        score += 5

        reasons.append(
            "NOTICE_NUMBER"
        )

    if dates:

        score += 1

        reasons.append(
            "DATE"
        )

    if detail_urls:

        score += 2

        reasons.append(
            "DETAIL_URL"
        )

    if attachment_urls:

        score += 4

        reasons.append(
            "ATTACHMENT_URL"
        )

    if extensionless_download_urls:

        score += 3

        reasons.append(
            "EXTENSIONLESS_DOWNLOAD"
        )

    return (
        score,
        reasons,
    )


def classify_item_candidate(
    *,
    score: int,
    label: str,
    text: str,
    detail_urls: List[str],
    attachment_urls: List[str],
    extensionless_download_urls: List[str],
    issue_numbers: List[str],
    notice_numbers: List[str],
) -> str:

    combined = normalize_space(
        label
        + " "
        + text
    )

    target = contains_target(
        combined
    )

    strong_context = (
        contains_any(
            combined,
            HIGH_RELEVANCE_TERMS,
        )
        or contains_any(
            combined,
            NOTICE_TERMS,
        )
    )

    has_document_endpoint = bool(
        detail_urls
        or attachment_urls
        or extensionless_download_urls
    )

    has_issue_identity = bool(
        issue_numbers
        or notice_numbers
    )

    if (
        target
        and has_document_endpoint
    ):

        return "TARGET_BEARING_DOCUMENT_SEED"

    if (
        score >= 10
        and has_document_endpoint
        and strong_context
    ):

        return "HIGH_PRIORITY_DOCUMENT_SEED"

    if (
        has_issue_identity
        and has_document_endpoint
    ):

        return "GAZETTE_ISSUE_DOCUMENT_SEED"

    if (
        attachment_urls
        or extensionless_download_urls
    ):

        return "ATTACHMENT_SEED"

    if (
        detail_urls
        and strong_context
        and score >= 5
    ):

        return "DETAIL_DOCUMENT_SEED"

    return "EXCLUDED_LOW_EVIDENCE"


# ============================================================
# DISCOVERY STATE
# ============================================================

archive_results: List[
    Dict[str, Any]
] = []

raw_item_records: List[
    Dict[str, Any]
] = []

candidate_records: List[
    Dict[str, Any]
] = []

attachment_records: List[
    Dict[str, Any]
] = []

extensionless_records: List[
    Dict[str, Any]
] = []


visited_urls: Set[str] = set()

request_count = 0

http_success_count = 0

transport_error_count = 0

html_parse_count = 0

archive_page_probe_count = 0

raw_structural_block_count = 0

generic_navigation_filtered_count = 0

list_endpoint_filtered_count = 0

cross_domain_filtered_count = 0

low_evidence_filtered_count = 0


# ============================================================
# CONSOLE HEADER
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA"
)

print(
    "GAZETTE ARCHIVE ISSUE / ATTACHMENT DISCOVERY"
)

print(
    "============================================================"
)

print()

print(
    "Target:",
    TARGET_NAME,
)

print(
    "Standard code:",
    STANDARD_CODE,
)

print(
    "Historical input:",
    HISTORICAL_DISCOVERY_INPUT,
)

print(
    "Strong verification input:",
    STRONG_VERIFICATION_INPUT,
)

print(
    "Gazette archive endpoint count:",
    len(
        archive_endpoints
    ),
)

print()


# ============================================================
# MAIN LOOP
# ============================================================

for archive_index, archive in enumerate(
    archive_endpoints,
    start=1,
):

    region = normalize_space(
        archive.get(
            "region"
        )
    )

    agency = normalize_space(
        archive.get(
            "agency"
        )
        or region
    )

    archive_label = normalize_space(
        archive.get(
            "label"
        )
    )

    archive_url = normalize_url(
        archive.get(
            "url"
        )
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"ARCHIVE {archive_index}:",
        region,
    )

    print(
        "Label:",
        archive_label,
    )

    print(
        "URL:",
        archive_url,
    )

    local_pages = []

    local_items = []

    local_candidates = []

    local_attachments = []

    local_extensionless = []

    # ========================================================
    # ROOT ARCHIVE
    # ========================================================

    root = fetch_url(
        archive_url
    )

    request_count += 1

    if root.error:

        transport_error_count += 1

        print(
            "Transport error:",
            root.error,
        )

        archive_results.append(
            {
                "region": region,
                "agency": agency,
                "label": archive_label,
                "url": archive_url,
                "root_http": None,
                "root_error": root.error,
                "pagination_params": [],
                "pages_probed": 0,
                "raw_item_count": 0,
                "candidate_count": 0,
                "attachment_count": 0,
                "extensionless_download_count": 0,
            }
        )

        continue

    if root.http_status == 200:

        http_success_count += 1

    if root.text:

        html_parse_count += 1

    root_final_url = normalize_url(
        root.final_url
        or archive_url
    )

    pagination_keys = detect_existing_pagination_keys(
        root_final_url,
        root.text,
    )

    page_urls = [
        root_final_url,
    ]

    page_urls.extend(
        build_pagination_urls(
            root_final_url,
            pagination_keys,
        )
    )

    # ========================================================
    # DEDUPE PAGE URLS
    # ========================================================

    deduped_page_urls = []

    local_page_seen = set()

    for page_url in page_urls:

        normalized_page_url = normalize_url(
            page_url
        )

        if normalized_page_url in local_page_seen:

            continue

        local_page_seen.add(
            normalized_page_url
        )

        deduped_page_urls.append(
            normalized_page_url
        )

    # ========================================================
    # PAGE PROBES
    # ========================================================

    for page_index, page_url in enumerate(
        deduped_page_urls,
        start=1,
    ):

        if page_url in visited_urls:

            continue

        visited_urls.add(
            page_url
        )

        if page_index == 1:

            page_result = root

        else:

            page_result = fetch_url(
                page_url
            )

            request_count += 1

        archive_page_probe_count += 1

        if page_result.error:

            transport_error_count += 1

            local_pages.append(
                {
                    "url": page_url,
                    "http_status": None,
                    "error": page_result.error,
                }
            )

            continue

        if (
            page_index != 1
            and page_result.http_status == 200
        ):

            http_success_count += 1

        if (
            page_index != 1
            and page_result.text
        ):

            html_parse_count += 1

        final_page_url = normalize_url(
            page_result.final_url
            or page_url
        )

        page_text = strip_html(
            page_result.text
        )

        page_target = contains_target(
            page_text
        )

        structural_blocks = extract_structural_blocks(
            page_result.text
        )

        raw_structural_block_count += len(
            structural_blocks
        )

        page_raw_item_count = 0

        page_candidate_count = 0

        # ====================================================
        # STRUCTURAL ITEM LOOP
        # ====================================================

        for block_index, (
            block_type,
            block_html,
        ) in enumerate(
            structural_blocks,
            start=1,
        ):

            block_text = strip_html(
                block_html
            )

            if not block_text:

                continue

            anchors = extract_anchor_records(
                block_html,
                base_url=final_page_url,
            )

            javascript_urls = (
                extract_javascript_and_data_urls(
                    block_html,
                    base_url=final_page_url,
                )
            )

            # ------------------------------------------------
            # 가장 대표적인 label 결정
            # ------------------------------------------------

            label_candidates = [
                normalize_space(
                    anchor.get(
                        "label"
                    )
                )
                for anchor in anchors
                if normalize_space(
                    anchor.get(
                        "label"
                    )
                )
            ]

            label = ""

            for label_candidate in label_candidates:

                if is_generic_navigation_label(
                    label_candidate
                ):

                    continue

                label = label_candidate

                break

            if not label:

                label = build_preview(
                    block_text,
                    max_length=180,
                )

            # ------------------------------------------------
            # URL 분류
            # ------------------------------------------------

            detail_urls = []

            attachment_urls = []

            extensionless_urls = []

            seen_block_urls = set()

            url_records = []

            for anchor in anchors:

                url_records.append(
                    {
                        "url": anchor.get(
                            "url"
                        ),
                        "source": "ANCHOR",
                    }
                )

            url_records.extend(
                javascript_urls
            )

            for url_record in url_records:

                candidate_url = normalize_url(
                    url_record.get(
                        "url"
                    )
                )

                if not candidate_url:

                    continue

                if candidate_url in seen_block_urls:

                    continue

                seen_block_urls.add(
                    candidate_url
                )

                if not same_or_subdomain(
                    candidate_url,
                    archive_url,
                ):

                    cross_domain_filtered_count += 1

                    continue

                if is_search_url(
                    candidate_url
                ):

                    continue

                if is_blocked_asset_url(
                    candidate_url
                ):

                    continue

                if is_attachment_url(
                    candidate_url
                ):

                    attachment_urls.append(
                        candidate_url
                    )

                    continue

                if is_extensionless_download_url(
                    candidate_url
                ):

                    extensionless_urls.append(
                        candidate_url
                    )

                    continue

                if is_list_url(
                    candidate_url
                ):

                    list_endpoint_filtered_count += 1

                    continue

                if is_detail_url(
                    candidate_url
                ):

                    detail_urls.append(
                        candidate_url
                    )

            detail_urls = list(
                dict.fromkeys(
                    detail_urls
                )
            )

            attachment_urls = list(
                dict.fromkeys(
                    attachment_urls
                )
            )

            extensionless_urls = list(
                dict.fromkeys(
                    extensionless_urls
                )
            )

            # ------------------------------------------------
            # 단순 navigation block 제거
            # ------------------------------------------------

            if (
                is_generic_navigation_label(
                    label
                )
                and not (
                    detail_urls
                    or attachment_urls
                    or extensionless_urls
                )
            ):

                generic_navigation_filtered_count += 1

                continue

            dates = extract_dates(
                block_text
            )

            issue_numbers = extract_issue_numbers(
                block_text
            )

            notice_numbers = extract_notice_numbers(
                block_text
            )

            score, score_reasons = compute_item_score(
                text=block_text,
                label=label,
                detail_urls=detail_urls,
                attachment_urls=attachment_urls,
                extensionless_download_urls=extensionless_urls,
                issue_numbers=issue_numbers,
                notice_numbers=notice_numbers,
                dates=dates,
            )

            classification = classify_item_candidate(
                score=score,
                label=label,
                text=block_text,
                detail_urls=detail_urls,
                attachment_urls=attachment_urls,
                extensionless_download_urls=extensionless_urls,
                issue_numbers=issue_numbers,
                notice_numbers=notice_numbers,
            )

            item_record = {
                "region": region,
                "agency": agency,
                "archive_label": archive_label,
                "archive_url": archive_url,
                "page_url": final_page_url,
                "page_index": page_index,
                "block_index": block_index,
                "block_type": block_type,
                "label": label,
                "target_found": contains_target(
                    block_text
                ),
                "notice_context": contains_any(
                    block_text,
                    NOTICE_TERMS,
                ),
                "urban_context": contains_any(
                    block_text,
                    URBAN_TERMS,
                ),
                "action_context": contains_any(
                    block_text,
                    ACTION_TERMS,
                ),
                "dates": dates,
                "issue_numbers": issue_numbers,
                "notice_numbers": notice_numbers,
                "detail_urls": detail_urls,
                "attachment_urls": attachment_urls,
                "extensionless_download_urls": extensionless_urls,
                "score": score,
                "score_reasons": score_reasons,
                "classification": classification,
                "preview": build_preview(
                    block_text
                ),
                "final_positive": False,
            }

            raw_item_records.append(
                item_record
            )

            local_items.append(
                item_record
            )

            page_raw_item_count += 1

            if classification == "EXCLUDED_LOW_EVIDENCE":

                low_evidence_filtered_count += 1

                continue

            candidate_records.append(
                item_record
            )

            local_candidates.append(
                item_record
            )

            page_candidate_count += 1

            for attachment_url in attachment_urls:

                attachment_record = {
                    "region": region,
                    "agency": agency,
                    "archive_label": archive_label,
                    "archive_url": archive_url,
                    "parent_page_url": final_page_url,
                    "parent_item_label": label,
                    "url": attachment_url,
                    "extension": attachment_extension(
                        attachment_url
                    ),
                    "target_in_parent_item": contains_target(
                        block_text
                    ),
                    "notice_context_in_parent_item": contains_any(
                        block_text,
                        NOTICE_TERMS,
                    ),
                    "urban_context_in_parent_item": contains_any(
                        block_text,
                        URBAN_TERMS,
                    ),
                    "issue_numbers": issue_numbers,
                    "notice_numbers": notice_numbers,
                    "dates": dates,
                    "parent_score": score,
                    "parent_classification": classification,
                    "final_positive": False,
                }

                attachment_records.append(
                    attachment_record
                )

                local_attachments.append(
                    attachment_record
                )

            for extensionless_url in extensionless_urls:

                extensionless_record = {
                    "region": region,
                    "agency": agency,
                    "archive_label": archive_label,
                    "archive_url": archive_url,
                    "parent_page_url": final_page_url,
                    "parent_item_label": label,
                    "url": extensionless_url,
                    "target_in_parent_item": contains_target(
                        block_text
                    ),
                    "notice_context_in_parent_item": contains_any(
                        block_text,
                        NOTICE_TERMS,
                    ),
                    "urban_context_in_parent_item": contains_any(
                        block_text,
                        URBAN_TERMS,
                    ),
                    "issue_numbers": issue_numbers,
                    "notice_numbers": notice_numbers,
                    "dates": dates,
                    "parent_score": score,
                    "parent_classification": classification,
                    "final_positive": False,
                }

                extensionless_records.append(
                    extensionless_record
                )

                local_extensionless.append(
                    extensionless_record
                )

        local_pages.append(
            {
                "url": final_page_url,
                "http_status": page_result.http_status,
                "target_found": page_target,
                "raw_item_count": page_raw_item_count,
                "candidate_count": page_candidate_count,
            }
        )

        time.sleep(
            REQUEST_SLEEP
        )

    # ========================================================
    # LOCAL DEDUPE
    # ========================================================

    local_candidate_keys = {
        (
            item.get(
                "classification"
            ),
            item.get(
                "region"
            ),
            tuple(
                item.get(
                    "detail_urls",
                    []
                )
            ),
            tuple(
                item.get(
                    "attachment_urls",
                    []
                )
            ),
            tuple(
                item.get(
                    "extensionless_download_urls",
                    []
                )
            ),
            item.get(
                "label"
            ),
        )
        for item in local_candidates
    }

    print(
        "Root HTTP:",
        root.http_status,
    )

    print(
        "Pagination params:",
        pagination_keys,
    )

    print(
        "Pages probed:",
        len(
            local_pages
        ),
    )

    print(
        "Raw item records:",
        len(
            local_items
        ),
    )

    print(
        "Issue/detail seeds:",
        len(
            local_candidate_keys
        ),
    )

    print(
        "Attachment seeds:",
        len(
            local_attachments
        ),
    )

    print(
        "Extensionless download seeds:",
        len(
            local_extensionless
        ),
    )

    archive_results.append(
        {
            "region": region,
            "agency": agency,
            "label": archive_label,
            "url": archive_url,
            "root_http": root.http_status,
            "root_final_url": root.final_url,
            "pagination_params": pagination_keys,
            "pages_probed": len(
                local_pages
            ),
            "page_results": local_pages,
            "raw_item_count": len(
                local_items
            ),
            "candidate_count": len(
                local_candidate_keys
            ),
            "attachment_count": len(
                local_attachments
            ),
            "extensionless_download_count": len(
                local_extensionless
            ),
        }
    )

    time.sleep(
        REQUEST_SLEEP
    )


# ============================================================
# DEDUPE ITEM CANDIDATES
# ============================================================

deduped_candidates = []

seen_candidate_keys = set()

for item in candidate_records:

    detail_urls = tuple(
        normalize_url(
            url
        )
        for url in item.get(
            "detail_urls",
            []
        )
    )

    attachment_urls = tuple(
        normalize_url(
            url
        )
        for url in item.get(
            "attachment_urls",
            []
        )
    )

    extensionless_urls = tuple(
        normalize_url(
            url
        )
        for url in item.get(
            "extensionless_download_urls",
            []
        )
    )

    key = (
        item.get(
            "region"
        ),
        item.get(
            "classification"
        ),
        detail_urls,
        attachment_urls,
        extensionless_urls,
        normalize_space(
            item.get(
                "label"
            )
        ),
    )

    if key in seen_candidate_keys:

        continue

    seen_candidate_keys.add(
        key
    )

    deduped_candidates.append(
        item
    )


# ============================================================
# DEDUPE ATTACHMENTS
# ============================================================

deduped_attachments = []

seen_attachment_keys = set()

for item in attachment_records:

    normalized_url = normalize_url(
        item.get(
            "url"
        )
    )

    key = (
        item.get(
            "region"
        ),
        normalized_url,
    )

    if key in seen_attachment_keys:

        continue

    seen_attachment_keys.add(
        key
    )

    normalized_item = dict(
        item
    )

    normalized_item[
        "url"
    ] = normalized_url

    deduped_attachments.append(
        normalized_item
    )


# ============================================================
# DEDUPE EXTENSIONLESS
# ============================================================

deduped_extensionless = []

seen_extensionless_keys = set()

for item in extensionless_records:

    normalized_url = normalize_url(
        item.get(
            "url"
        )
    )

    key = (
        item.get(
            "region"
        ),
        normalized_url,
    )

    if key in seen_extensionless_keys:

        continue

    seen_extensionless_keys.add(
        key
    )

    normalized_item = dict(
        item
    )

    normalized_item[
        "url"
    ] = normalized_url

    deduped_extensionless.append(
        normalized_item
    )


# ============================================================
# PRIORITY SORT
# ============================================================

deduped_candidates.sort(
    key=lambda item: (
        -int(
            item.get(
                "score",
                0,
            )
        ),
        0
        if item.get(
            "target_found"
        )
        else 1,
        str(
            item.get(
                "region",
                "",
            )
        ),
        str(
            item.get(
                "label",
                "",
            )
        ),
    )
)


deduped_attachments.sort(
    key=lambda item: (
        -int(
            item.get(
                "parent_score",
                0,
            )
        ),
        0
        if item.get(
            "target_in_parent_item"
        )
        else 1,
        str(
            item.get(
                "region",
                "",
            )
        ),
        str(
            item.get(
                "url",
                "",
            )
        ),
    )
)


deduped_extensionless.sort(
    key=lambda item: (
        -int(
            item.get(
                "parent_score",
                0,
            )
        ),
        0
        if item.get(
            "target_in_parent_item"
        )
        else 1,
        str(
            item.get(
                "region",
                "",
            )
        ),
        str(
            item.get(
                "url",
                "",
            )
        ),
    )
)


# ============================================================
# CLASSIFICATION COUNTS
# ============================================================

classification_counts: Dict[
    str,
    int,
] = {}

for item in deduped_candidates:

    classification = str(
        item.get(
            "classification"
        )
        or ""
    )

    classification_counts[
        classification
    ] = (
        classification_counts.get(
            classification,
            0,
        )
        + 1
    )


target_bearing_candidate_count = sum(
    1
    for item in deduped_candidates
    if item.get(
        "target_found"
    )
    is True
)


# ============================================================
# RESOLUTION
# ============================================================

if (
    deduped_candidates
    or deduped_attachments
    or deduped_extensionless
):

    resolution = (
        "GAZETTE_ARCHIVE_ISSUE_OR_ATTACHMENT_SEED_DISCOVERED"
    )

    next_action = (
        "확보된 공보 issue/detail/attachment seed를 실제 HTTP 조회하고 "
        "PDF/HWP/HWPX 또는 상세 본문에서 개발밀도관리구역 target, "
        "지정·변경·해제 action context, 고시번호, 고시일, 행정구역 및 "
        "지정 범위를 검증한다. 원문에서 해당 증거가 모두 확보된 문서만 "
        "verified positive 후보로 승격한다."
    )

else:

    resolution = (
        "GAZETTE_ARCHIVE_ISSUE_ATTACHMENT_DISCOVERY_COMPLETED_NO_SEED"
    )

    next_action = (
        "현재 공보 archive 목록 HTML에서는 신뢰 가능한 issue/detail/"
        "attachment seed가 확인되지 않았다. POST pagination, 연도/호수 "
        "필터, JavaScript/AJAX 공보 endpoint 및 개별 지자체 공보 전용 "
        "다운로드 API를 분석한다."
    )


runtime_registration_blocked = True

site_false_interpretation_blocked = True

verified_positive_promotion_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-T "
        "Development Density Management Area "
        "Gazette Archive Issue / Attachment Discovery"
    ),

    "target": {
        "name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
    },

    "inputs": {
        "historical_discovery": str(
            HISTORICAL_DISCOVERY_INPUT
        ),
        "strong_verification": str(
            STRONG_VERIFICATION_INPUT
        ),
        "historical_discovery_exists": (
            HISTORICAL_DISCOVERY_INPUT.exists()
        ),
        "strong_verification_exists": (
            STRONG_VERIFICATION_INPUT.exists()
        ),
    },

    "method": {
        "official_gazette_archive_direct_probe": True,
        "search_engine_scraping": False,
        "historical_archive_item_extraction": True,
        "row_level_structural_extraction": True,
        "detail_url_discovery": True,
        "attachment_discovery": True,
        "extensionless_download_discovery": True,
        "list_page_final_positive_allowed": False,
        "attachment_final_positive_allowed": False,
        "verified_positive_promotion_allowed": False,
    },

    "summary": {
        "archive_endpoint_count": len(
            archive_endpoints
        ),
        "request_count": request_count,
        "http_success_count": http_success_count,
        "transport_error_count": transport_error_count,
        "html_parse_count": html_parse_count,
        "archive_page_probe_count": archive_page_probe_count,
        "raw_structural_block_count": raw_structural_block_count,
        "raw_item_record_count": len(
            raw_item_records
        ),
        "candidate_count": len(
            deduped_candidates
        ),
        "target_bearing_candidate_count": (
            target_bearing_candidate_count
        ),
        "attachment_seed_count": len(
            deduped_attachments
        ),
        "extensionless_download_seed_count": len(
            deduped_extensionless
        ),
        "generic_navigation_filtered_count": (
            generic_navigation_filtered_count
        ),
        "list_endpoint_filtered_count": (
            list_endpoint_filtered_count
        ),
        "cross_domain_filtered_count": (
            cross_domain_filtered_count
        ),
        "low_evidence_filtered_count": (
            low_evidence_filtered_count
        ),
        "classification_counts": (
            classification_counts
        ),
    },

    "archive_results": (
        archive_results
    ),

    "issue_detail_candidates": (
        deduped_candidates
    ),

    "attachment_seeds": (
        deduped_attachments
    ),

    "extensionless_download_seeds": (
        deduped_extensionless
    ),

    "resolution": resolution,

    "next_action": next_action,

    "runtime_registration_blocked": (
        runtime_registration_blocked
    ),

    "site_false_interpretation_blocked": (
        site_false_interpretation_blocked
    ),

    "verified_positive_promotion_blocked": (
        verified_positive_promotion_blocked
    ),
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
# CONSOLE SUMMARY
# ============================================================

print()

print(
    "============================================================"
)

print(
    "DISCOVERY RESULT"
)

print(
    "============================================================"
)

print(
    "Gazette archive endpoint count:",
    len(
        archive_endpoints
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
    "Archive page probe count:",
    archive_page_probe_count,
)

print(
    "Raw structural block count:",
    raw_structural_block_count,
)

print(
    "Raw item record count:",
    len(
        raw_item_records
    ),
)

print(
    "Issue/detail candidate count:",
    len(
        deduped_candidates
    ),
)

print(
    "Target-bearing candidate count:",
    target_bearing_candidate_count,
)

print(
    "Attachment seed count:",
    len(
        deduped_attachments
    ),
)

print(
    "Extensionless download seed count:",
    len(
        deduped_extensionless
    ),
)

print(
    "Generic navigation filtered:",
    generic_navigation_filtered_count,
)

print(
    "List endpoint filtered:",
    list_endpoint_filtered_count,
)

print(
    "Low evidence filtered:",
    low_evidence_filtered_count,
)

print()

for classification, count in sorted(
    classification_counts.items()
):

    print(
        f"{classification}:",
        count,
    )


# ============================================================
# PRINT CANDIDATES
# ============================================================

if deduped_candidates:

    print()

    print(
        "GAZETTE ISSUE / DETAIL SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        deduped_candidates[
            :80
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
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
            "Target found:",
            item.get(
                "target_found"
            ),
        )

        print(
            "Issue numbers:",
            item.get(
                "issue_numbers"
            ),
        )

        print(
            "Notice numbers:",
            item.get(
                "notice_numbers"
            ),
        )

        print(
            "Dates:",
            item.get(
                "dates"
            ),
        )

        print(
            "Detail URLs:",
            item.get(
                "detail_urls"
            ),
        )

        print(
            "Attachment URLs:",
            item.get(
                "attachment_urls"
            ),
        )

        print(
            "Extensionless URLs:",
            item.get(
                "extensionless_download_urls"
            ),
        )

        print(
            "Preview:",
            item.get(
                "preview"
            ),
        )

        print()


if deduped_attachments:

    print()

    print(
        "ATTACHMENT SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        deduped_attachments[
            :80
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Type:",
            item.get(
                "extension"
            ),
        )

        print(
            "Parent score:",
            item.get(
                "parent_score"
            ),
        )

        print(
            "Parent label:",
            item.get(
                "parent_item_label"
            ),
        )

        print(
            "Target in parent:",
            item.get(
                "target_in_parent_item"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print()


if deduped_extensionless:

    print()

    print(
        "EXTENSIONLESS DOWNLOAD SEEDS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, item in enumerate(
        deduped_extensionless[
            :80
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            item.get(
                "region"
            ),
        )

        print(
            "Parent score:",
            item.get(
                "parent_score"
            ),
        )

        print(
            "Parent label:",
            item.get(
                "parent_item_label"
            ),
        )

        print(
            "Target in parent:",
            item.get(
                "target_in_parent_item"
            ),
        )

        print(
            "URL:",
            item.get(
                "url"
            ),
        )

        print()


if not (
    deduped_candidates
    or deduped_attachments
    or deduped_extensionless
):

    print()

    print(
        "No gazette issue/detail/attachment seed discovered."
    )


print()

print(
    "============================================================"
)

print(
    "RESOLUTION"
)

print(
    "============================================================"
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
# VALIDATION HELPERS
# ============================================================

archive_endpoint_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            item.get(
                "url"
            )
        ),
    )
    for item in archive_endpoints
}


candidate_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "classification"
        ),
        tuple(
            normalize_url(
                url
            )
            for url in item.get(
                "detail_urls",
                []
            )
        ),
        tuple(
            normalize_url(
                url
            )
            for url in item.get(
                "attachment_urls",
                []
            )
        ),
        tuple(
            normalize_url(
                url
            )
            for url in item.get(
                "extensionless_download_urls",
                []
            )
        ),
        normalize_space(
            item.get(
                "label"
            )
        ),
    )
    for item in deduped_candidates
}


attachment_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            item.get(
                "url"
            )
        ),
    )
    for item in deduped_attachments
}


extensionless_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            item.get(
                "url"
            )
        ),
    )
    for item in deduped_extensionless
}


allowed_candidate_classes = {
    "TARGET_BEARING_DOCUMENT_SEED",
    "HIGH_PRIORITY_DOCUMENT_SEED",
    "GAZETTE_ISSUE_DOCUMENT_SEED",
    "ATTACHMENT_SEED",
    "DETAIL_DOCUMENT_SEED",
}


all_candidates_have_archive_context = all(
    bool(
        item.get(
            "archive_url"
        )
    )
    and bool(
        item.get(
            "page_url"
        )
    )
    for item in deduped_candidates
)


all_candidate_classes_valid = all(
    item.get(
        "classification"
    )
    in allowed_candidate_classes
    for item in deduped_candidates
)


all_candidates_not_final_positive = all(
    item.get(
        "final_positive"
    )
    is False
    for item in deduped_candidates
)


all_attachments_supported = all(
    item.get(
        "extension"
    )
    in {
        "pdf",
        "hwp",
        "hwpx",
    }
    for item in deduped_attachments
)


all_attachment_urls_valid = all(
    bool(
        item.get(
            "url"
        )
    )
    and is_attachment_url(
        item.get(
            "url"
        )
    )
    for item in deduped_attachments
)


all_attachment_not_final_positive = all(
    item.get(
        "final_positive"
    )
    is False
    for item in deduped_attachments
)


all_extensionless_have_download_hint = all(
    is_extensionless_download_url(
        item.get(
            "url"
        )
    )
    for item in deduped_extensionless
)


all_extensionless_not_attachment = all(
    not is_attachment_url(
        item.get(
            "url"
        )
    )
    for item in deduped_extensionless
)


all_extensionless_not_final_positive = all(
    item.get(
        "final_positive"
    )
    is False
    for item in deduped_extensionless
)


list_only_candidate_leakage = sum(
    1
    for item in deduped_candidates
    if (
        item.get(
            "detail_urls"
        )
        and all(
            is_list_url(
                url
            )
            for url in item.get(
                "detail_urls",
                []
            )
        )
    )
)


search_url_candidate_leakage = sum(
    1
    for item in deduped_candidates
    for url in (
        item.get(
            "detail_urls",
            []
        )
        + item.get(
            "attachment_urls",
            []
        )
        + item.get(
            "extensionless_download_urls",
            []
        )
    )
    if is_search_url(
        url
    )
)


# ============================================================
# VALIDATION
# ============================================================

validations = {

    "target name": (
        TARGET_NAME
        == "개발밀도관리구역"
    ),

    "standard code": (
        STANDARD_CODE
        == "UQQ700"
    ),

    "historical input exists": (
        HISTORICAL_DISCOVERY_INPUT.exists()
    ),

    "historical input parsed": (
        isinstance(
            historical_data,
            dict,
        )
    ),

    "archive endpoint extraction enabled": (
        isinstance(
            archive_endpoints,
            list,
        )
    ),

    "archive endpoints unique": (
        len(
            archive_endpoint_keys
        )
        == len(
            archive_endpoints
        )
    ),

    "all archive endpoint URLs exist": all(
        bool(
            item.get(
                "url"
            )
        )
        for item in archive_endpoints
    ),

    "official archive direct probe enabled": (
        output_data[
            "method"
        ][
            "official_gazette_archive_direct_probe"
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

    "row-level structural extraction enabled": (
        output_data[
            "method"
        ][
            "row_level_structural_extraction"
        ]
        is True
    ),

    "detail URL discovery enabled": (
        output_data[
            "method"
        ][
            "detail_url_discovery"
        ]
        is True
    ),

    "attachment discovery enabled": (
        output_data[
            "method"
        ][
            "attachment_discovery"
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

    "list page final positive prohibited": (
        output_data[
            "method"
        ][
            "list_page_final_positive_allowed"
        ]
        is False
    ),

    "attachment final positive prohibited": (
        output_data[
            "method"
        ][
            "attachment_final_positive_allowed"
        ]
        is False
    ),

    "verified positive promotion prohibited": (
        output_data[
            "method"
        ][
            "verified_positive_promotion_allowed"
        ]
        is False
    ),

    "endpoint result accounting": (
        len(
            archive_results
        )
        == len(
            archive_endpoints
        )
    ),

    "requests executed when archives exist": (
        (
            not archive_endpoints
        )
        or request_count > 0
    ),

    "candidates unique": (
        len(
            candidate_keys
        )
        == len(
            deduped_candidates
        )
    ),

    "attachment seeds unique": (
        len(
            attachment_keys
        )
        == len(
            deduped_attachments
        )
    ),

    "extensionless seeds unique": (
        len(
            extensionless_keys
        )
        == len(
            deduped_extensionless
        )
    ),

    "all candidate classes valid": (
        all_candidate_classes_valid
    ),

    "all candidates have archive context": (
        all_candidates_have_archive_context
    ),

    "all candidates are not final positive": (
        all_candidates_not_final_positive
    ),

    "all attachment seeds supported": (
        all_attachments_supported
    ),

    "all attachment URLs valid": (
        all_attachment_urls_valid
    ),

    "all attachments are not final positive": (
        all_attachment_not_final_positive
    ),

    "all extensionless seeds have download hint": (
        all_extensionless_have_download_hint
    ),

    "all extensionless seeds are not file extensions": (
        all_extensionless_not_attachment
    ),

    "all extensionless seeds are not final positive": (
        all_extensionless_not_final_positive
    ),

    "list-only candidate leakage zero": (
        list_only_candidate_leakage
        == 0
    ),

    "search URL candidate leakage zero": (
        search_url_candidate_leakage
        == 0
    ),

    "runtime registration remains blocked": (
        runtime_registration_blocked
        is True
    ),

    "SITE FALSE remains blocked": (
        site_false_interpretation_blocked
        is True
    ),

    "verified positive promotion remains blocked": (
        verified_positive_promotion_blocked
        is True
    ),

    "output written": (
        OUTPUT_PATH.exists()
        and OUTPUT_PATH.stat().st_size
        > 0
    ),
}


print()

print(
    "============================================================"
)

print(
    "VALIDATION"
)

print(
    "============================================================"
)


for name, passed in validations.items():

    print(
        f"{name}:",
        passed,
    )


print()

print(
    "List-only candidate leakage:",
    list_only_candidate_leakage,
)

print(
    "Search URL candidate leakage:",
    search_url_candidate_leakage,
)


all_pass = all(
    validations.values()
)


print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    print()

    print(
        "FAILED:"
    )

    for name, passed in validations.items():

        if not passed:

            print(
                "-",
                name,
            )

    raise AssertionError(
        "Development density management area "
        "gazette archive issue / attachment discovery "
        "regression failed"
    )