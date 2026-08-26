# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-K
Development Density Management Area
Official Board Target Row / Pagination Discovery

목표
======================================================================
I-stage에서 확인된 searchable official endpoint를 대상으로
검색 결과 전체 페이지가 아니라 "검색 결과 행(row)" 단위로
개발밀도관리구역 target evidence를 정밀 판정한다.

입력:
    law_data/output/
    development_density_management_area_official_board_search_form_discovery.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700

핵심 안전정책
======================================================================
1. 검색 결과 페이지 자체는 VERIFIED POSITIVE가 아니다.
2. target이 검색 URL query에만 존재하면 row target evidence로 인정하지 않는다.
3. row 제목 / row 본문 / row 첨부 label 중 실제 target이 존재하는 경우에만
   target-bearing row로 인정한다.
4. 일반 도시계획 / 고시 / 공고 키워드만으로 detail seed를 만들지 않는다.
5. pagination 탐색에서도 동일한 row-level guard를 적용한다.
6. detail seed는 반드시 검색 결과 row에서 실제 href로 추출된 URL이어야 한다.
7. runtime spatial condition 등록은 계속 차단한다.
8. target row 미발견을 SITE FALSE로 해석하지 않는다.
9. VWorld LT_C_UQ141을 UQQ700 dataset으로 확정하지 않는다.

이번 단계 성공 조건
======================================================================
A. target-bearing result row를 1건 이상 발견하고 detail seed를 확보

또는

B. searchable endpoint / pagination / row parser가 정상 실행되며
   target-bearing row 0건 상태를 명시적으로 보존

즉 discovery regression이므로 target row 0건도 테스트 실패가 아니다.
"""

from __future__ import annotations

import html
import json
import re
import time

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple
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
    / "development_density_management_area_official_board_target_row_discovery.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"

TARGET_VARIANTS = (
    "개발밀도관리구역",
    "개발밀도 관리구역",
    "개발 밀도 관리구역",
)


# ============================================================
# REQUEST CONFIG
# ============================================================

REQUEST_TIMEOUT = 20
REQUEST_SLEEP = 0.20

MAX_CONTENT_LENGTH = 2_000_000
MAX_ENDPOINTS = 60

# 한 endpoint에서 pagination 폭주 방지
MAX_PAGES_PER_ENDPOINT = 8

# page number를 무한 생성하지 않는다.
MAX_SYNTHETIC_PAGE_NUMBER = 8

# 한 페이지에서 지나치게 많은 row/anchor 처리 방지
MAX_ANCHORS_PER_PAGE = 500
MAX_ROWS_PER_PAGE = 250

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


# ============================================================
# ALLOWED INPUT CLASSES
# ============================================================

ALLOWED_ENDPOINT_CLASSES = {
    "PRIMARY_GOSI_BOARD",
    "GAZETTE_ARCHIVE",
    "URBAN_PLANNING_BOARD",
}


# ============================================================
# FALSE POSITIVE / SEARCH URL GUARDS
# ============================================================

SEARCH_URL_HINTS = (
    "/search",
    "search.",
    "search/",
    "search?",
    "search.do",
    "search.jsp",
    "totalsearch",
    "tourresult",
)

STATIC_ASSET_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".svg",
    ".webp",
    ".css",
    ".js",
    ".ico",
)

ATTACHMENT_EXTENSIONS = (
    ".pdf",
    ".hwp",
    ".hwpx",
)

DETAIL_URL_HINTS = (
    "/view",
    "view.do",
    "view.htm",
    "view.jsp",
    "detail",
    "detail.do",
    "selectBoardArticle",
    "bbsMsgDetail",
    "AnnounceDetail",
    "post/view",
    "board/view",
    "notice/view",
    "idx=",
    "nttId=",
    "msg_seq=",
    "mgt_no=",
    "seq=",
    "notAncmtMgtNo=",
)


# ============================================================
# PAGINATION PARAMETER HINTS
# ============================================================

PAGINATION_PARAM_NAMES = {
    "page",
    "pageindex",
    "pageidx",
    "pageno",
    "curpage",
    "gotopage",
    "pagenum",
    "srchpage",
    "viewpage",
    "page.pageNo".lower(),
    "cpage",
}

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "jsessionid",
    "timestamp",
    "_",
}


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
# TEXT UTIL
# ============================================================

def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def strip_html(source: str) -> str:
    value = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", source)
    value = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", value)
    value = re.sub(r"(?is)<[^>]+>", " ", value)
    value = html.unescape(value)
    return normalize_space(value)


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", normalize_space(value))


def contains_target(value: str) -> bool:
    compact = compact_text(value)
    return compact_text(TARGET_NAME) in compact


def build_preview(
    value: str,
    *,
    radius: int = 260,
) -> str:
    text = normalize_space(value)

    index = -1

    for variant in TARGET_VARIANTS:
        index = text.find(variant)

        if index >= 0:
            break

    if index < 0:
        return text[: radius * 2]

    start = max(0, index - radius)
    end = min(
        len(text),
        index + len(TARGET_NAME) + radius,
    )

    return text[start:end]


# ============================================================
# URL UTIL
# ============================================================

def normalize_url(
    url: str,
    *,
    remove_pagination: bool = False,
) -> str:

    try:
        parsed = urlparse(url)

    except Exception:
        return url

    query_items = []

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):
        lower_key = key.lower().strip()

        if lower_key in VOLATILE_QUERY_KEYS:
            continue

        if remove_pagination and lower_key in PAGINATION_PARAM_NAMES:
            continue

        query_items.append((key, value))

    query_items.sort(
        key=lambda item: (
            item[0].lower(),
            item[1],
        )
    )

    return urlunparse(
        parsed._replace(
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
            urlparse(url).hostname
            or ""
        ).lower()

        base_host = (
            urlparse(base_url).hostname
            or ""
        ).lower()

    except Exception:
        return False

    if not target_host or not base_host:
        return False

    return (
        target_host == base_host
        or target_host.endswith("." + base_host)
        or base_host.endswith("." + target_host)
    )


def is_search_url(url: str) -> bool:
    lower = url.lower()

    return any(
        hint.lower() in lower
        for hint in SEARCH_URL_HINTS
    )


def is_static_asset_url(url: str) -> bool:
    path = urlparse(url).path.lower()

    return any(
        path.endswith(extension)
        for extension in STATIC_ASSET_EXTENSIONS
    )


def is_attachment_url(url: str) -> bool:
    path = urlparse(url).path.lower()

    return any(
        path.endswith(extension)
        for extension in ATTACHMENT_EXTENSIONS
    )


def has_detail_url_hint(url: str) -> bool:
    lower = url.lower()

    return any(
        hint.lower() in lower
        for hint in DETAIL_URL_HINTS
    )


def url_target_evidence(url: str) -> bool:
    decoded = requests.utils.unquote(url)

    return contains_target(decoded)


# ============================================================
# FETCH
# ============================================================

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
            request_url=url,
            final_url=None,
            http_status=None,
            content_type="",
            text="",
            error=repr(exc),
        )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
        or ""
    )

    content_type_lower = content_type.lower()

    text_like = (
        "text/" in content_type_lower
        or "html" in content_type_lower
        or "xml" in content_type_lower
        or "json" in content_type_lower
    )

    text = ""

    if text_like:
        text = response.text or ""

        if len(text) > MAX_CONTENT_LENGTH:
            text = text[:MAX_CONTENT_LENGTH]

    return FetchResult(
        request_url=url,
        final_url=response.url,
        http_status=response.status_code,
        content_type=content_type,
        text=text,
        error=None,
    )


# ============================================================
# ANCHOR EXTRACTION
# ============================================================

ANCHOR_PATTERN = re.compile(
    r"""
    (?is)
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


def extract_anchors(
    source: str,
    *,
    base_url: str,
) -> List[Dict[str, str]]:

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

        lower_href = href.lower()

        if lower_href.startswith(
            (
                "javascript:",
                "mailto:",
                "tel:",
                "#",
            )
        ):
            continue

        url = normalize_url(
            urljoin(
                base_url,
                html.unescape(href),
            )
        )

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            continue

        label_html = match.group(4) or ""
        label = strip_html(label_html)

        key = (
            url,
            label,
        )

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "url": url,
                "label": label,
                "raw_label_html": label_html,
            }
        )

        if len(results) >= MAX_ANCHORS_PER_PAGE:
            break

    return results


# ============================================================
# ROW CONTAINER EXTRACTION
# ============================================================

# 공공기관 목록형 페이지의 대표 row container.
# 완전한 DOM parser가 아니라 안전한 heuristic discovery 용도.
ROW_CONTAINER_PATTERNS = (
    re.compile(
        r"(?is)<tr\b[^>]*>(.*?)</tr>"
    ),
    re.compile(
        r"(?is)<li\b[^>]*>(.*?)</li>"
    ),
    re.compile(
        r"""(?is)
        <div\b
        [^>]*?
        class\s*=\s*
        (?:
            "[^"]*(?:list|item|row|board|notice|bbs)[^"]*"
            |
            '[^']*(?:list|item|row|board|notice|bbs)[^']*'
        )
        [^>]*>
        (.*?)
        </div>
        """,
        re.VERBOSE,
    ),
)


def extract_row_fragments(
    source: str,
) -> List[str]:

    rows = []
    seen = set()

    for pattern in ROW_CONTAINER_PATTERNS:

        for match in pattern.finditer(source):

            fragment = match.group(1) or ""

            text = strip_html(fragment)

            if not text:
                continue

            # navigation/menu 수준의 과도하게 짧은 row 제거
            if len(text) < 2:
                continue

            signature = (
                compact_text(text)[:400],
                len(fragment),
            )

            if signature in seen:
                continue

            seen.add(signature)

            rows.append(fragment)

            if len(rows) >= MAX_ROWS_PER_PAGE:
                return rows

    return rows


# ============================================================
# ROW CLASSIFICATION
# ============================================================

def classify_row(
    *,
    region: str,
    agency: str,
    endpoint_class: str,
    endpoint_url: str,
    page_url: str,
    page_number: int,
    row_index: int,
    row_source: str,
) -> Dict[str, Any]:

    row_text = strip_html(row_source)

    anchors = extract_anchors(
        row_source,
        base_url=page_url,
    )

    row_target_in_text = contains_target(
        row_text
    )

    target_anchor_labels = [
        anchor
        for anchor in anchors
        if contains_target(
            anchor.get(
                "label",
                "",
            )
        )
    ]

    target_in_anchor_label = bool(
        target_anchor_labels
    )

    target_in_href_only = (
        any(
            url_target_evidence(
                anchor.get(
                    "url",
                    "",
                )
            )
            for anchor in anchors
        )
        and not row_target_in_text
        and not target_in_anchor_label
    )

    # --------------------------------------------------------
    # 실제 row visible text 또는 anchor label에 target이 있어야 한다.
    # URL query string만 target인 경우 금지.
    # --------------------------------------------------------

    row_target_evidence = (
        (
            row_target_in_text
            or target_in_anchor_label
        )
        and not (
            target_in_href_only
            and not row_target_in_text
            and not target_in_anchor_label
        )
    )

    detail_links = []

    for anchor in anchors:

        link_url = anchor.get(
            "url",
            "",
        )

        label = anchor.get(
            "label",
            "",
        )

        if not link_url:
            continue

        if is_search_url(
            link_url
        ):
            continue

        if is_static_asset_url(
            link_url
        ):
            continue

        if is_attachment_url(
            link_url
        ):
            continue

        if not same_or_subdomain(
            link_url,
            endpoint_url,
        ):
            continue

        # row-level target evidence가 없는 경우 detail link 승격 금지
        if not row_target_evidence:
            continue

        score = 0

        if contains_target(label):
            score += 5

        if has_detail_url_hint(
            link_url
        ):
            score += 4

        if label:
            score += 1

        # 단순 pagination / 목록 링크 방지
        canonical_link = normalize_url(
            link_url,
            remove_pagination=True,
        )

        canonical_page = normalize_url(
            page_url,
            remove_pagination=True,
        )

        if canonical_link == canonical_page:
            continue

        detail_links.append(
            {
                "url": normalize_url(
                    link_url
                ),
                "label": label,
                "score": score,
                "target_in_label": (
                    contains_target(
                        label
                    )
                ),
                "detail_url_hint": (
                    has_detail_url_hint(
                        link_url
                    )
                ),
            }
        )

    detail_links.sort(
        key=lambda item: (
            -int(
                item.get(
                    "score",
                    0,
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

    return {
        "region": region,
        "agency": agency,
        "endpoint_class": endpoint_class,
        "endpoint_url": endpoint_url,
        "page_url": page_url,
        "page_number": page_number,
        "row_index": row_index,
        "row_text": row_text,
        "row_preview": (
            build_preview(
                row_text
            )
            if row_target_evidence
            else row_text[:400]
        ),
        "row_target_in_text": row_target_in_text,
        "target_in_anchor_label": target_in_anchor_label,
        "target_in_href_only": target_in_href_only,
        "row_target_evidence": row_target_evidence,
        "anchor_count": len(
            anchors
        ),
        "detail_links": detail_links,
    }


# ============================================================
# FALLBACK ANCHOR-CENTRIC ROW EXTRACTION
# ============================================================

def build_anchor_fallback_rows(
    *,
    source: str,
    page_url: str,
) -> List[str]:

    """
    table/li 구조가 없는 페이지에서 target-bearing anchor를 최소 row로 사용한다.
    URL query에만 target이 존재하는 anchor는 여기서 승격하지 않는다.
    """

    rows = []

    anchors = extract_anchors(
        source,
        base_url=page_url,
    )

    for anchor in anchors:

        label = anchor.get(
            "label",
            "",
        )

        if not contains_target(
            label
        ):
            continue

        url = anchor.get(
            "url",
            "",
        )

        escaped_label = html.escape(
            label
        )

        escaped_url = html.escape(
            url,
            quote=True,
        )

        rows.append(
            (
                '<div class="synthetic-target-row">'
                f'<a href="{escaped_url}">'
                f"{escaped_label}"
                "</a>"
                "</div>"
            )
        )

    return rows


# ============================================================
# PAGINATION URL DISCOVERY
# ============================================================

def infer_pagination_params_from_url(
    url: str,
) -> List[str]:

    names = []

    for key, _ in parse_qsl(
        urlparse(url).query,
        keep_blank_values=True,
    ):

        if key.lower() in PAGINATION_PARAM_NAMES:
            names.append(key)

    return names


def extract_pagination_links(
    source: str,
    *,
    page_url: str,
    endpoint_url: str,
) -> List[str]:

    candidates = []
    seen = set()

    for anchor in extract_anchors(
        source,
        base_url=page_url,
    ):

        url = anchor.get(
            "url",
            "",
        )

        label = normalize_space(
            anchor.get(
                "label",
                "",
            )
        )

        if not same_or_subdomain(
            url,
            endpoint_url,
        ):
            continue

        params = parse_qsl(
            urlparse(url).query,
            keep_blank_values=True,
        )

        has_pagination_param = any(
            key.lower()
            in PAGINATION_PARAM_NAMES
            for key, _
            in params
        )

        numeric_label = bool(
            re.fullmatch(
                r"\d{1,4}",
                label,
            )
        )

        paging_label = any(
            token in label
            for token in (
                "다음",
                "이전",
                "처음",
                "마지막",
                "next",
                "prev",
            )
        )

        if not (
            has_pagination_param
            or numeric_label
            or paging_label
        ):
            continue

        normalized = normalize_url(
            url
        )

        if normalized in seen:
            continue

        seen.add(normalized)
        candidates.append(normalized)

    return candidates


def synthesize_pagination_urls(
    endpoint_url: str,
    pagination_params: Sequence[str],
) -> List[str]:

    if not pagination_params:
        return []

    parsed = urlparse(
        endpoint_url
    )

    base_items = list(
        parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    )

    candidates = []
    seen = set()

    # 가장 대표적인 pagination key 하나를 우선 사용한다.
    chosen = None

    for param in pagination_params:

        if param.lower() in PAGINATION_PARAM_NAMES:
            chosen = param
            break

    if not chosen:
        return []

    for page_number in range(
        2,
        MAX_SYNTHETIC_PAGE_NUMBER + 1,
    ):

        new_items = []

        replaced = False

        for key, value in base_items:

            if key == chosen:
                new_items.append(
                    (
                        key,
                        str(
                            page_number
                        ),
                    )
                )
                replaced = True

            else:
                new_items.append(
                    (
                        key,
                        value,
                    )
                )

        if not replaced:
            new_items.append(
                (
                    chosen,
                    str(
                        page_number
                    ),
                )
            )

        url = urlunparse(
            parsed._replace(
                query=urlencode(
                    new_items,
                    doseq=True,
                )
            )
        )

        url = normalize_url(
            url
        )

        if url in seen:
            continue

        seen.add(url)
        candidates.append(url)

    return candidates


# ============================================================
# INPUT PARSING
# ============================================================

def load_input() -> Dict[str, Any]:

    if not INPUT_PATH.exists():

        raise FileNotFoundError(
            f"I-stage output not found: {INPUT_PATH}"
        )

    return json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )


def extract_searchable_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    # --------------------------------------------------------
    # I-stage 예상 키를 우선 사용
    # --------------------------------------------------------

    possible_keys = (
        "searchable_endpoints",
        "searchable_official_endpoints",
        "endpoint_results",
        "execution_results",
        "results",
    )

    raw_records = []

    for key in possible_keys:

        value = data.get(
            key
        )

        if isinstance(
            value,
            list,
        ):
            raw_records.extend(
                item
                for item in value
                if isinstance(
                    item,
                    dict,
                )
            )

    # --------------------------------------------------------
    # 직접 리스트 키가 없으면 JSON 전체에서 endpoint record 구조를 탐색
    # --------------------------------------------------------

    if not raw_records:

        def walk(
            value: Any,
        ) -> Iterable[Dict[str, Any]]:

            if isinstance(
                value,
                dict,
            ):

                if (
                    (
                        "canonical_url"
                        in value
                        or "url"
                        in value
                        or "endpoint_url"
                        in value
                    )
                    and (
                        "classification"
                        in value
                        or "endpoint_class"
                        in value
                        or "safe_search_form_count"
                        in value
                        or "safe_forms"
                        in value
                    )
                ):
                    yield value

                for child in value.values():
                    yield from walk(
                        child
                    )

            elif isinstance(
                value,
                list,
            ):

                for child in value:
                    yield from walk(
                        child
                    )

        raw_records.extend(
            walk(
                data
            )
        )

    normalized = []
    seen = set()

    for record in raw_records:

        endpoint_class = (
            record.get(
                "endpoint_class"
            )
            or record.get(
                "classification"
            )
            or record.get(
                "class"
            )
            or ""
        )

        if endpoint_class not in ALLOWED_ENDPOINT_CLASSES:
            continue

        url = (
            record.get(
                "canonical_url"
            )
            or record.get(
                "endpoint_url"
            )
            or record.get(
                "url"
            )
            or ""
        )

        if not url:
            continue

        if is_search_url(
            str(
                url
            )
        ):
            continue

        safe_form_count = (
            record.get(
                "safe_search_form_count"
            )
            or record.get(
                "safe_forms"
            )
            or record.get(
                "safe_form_count"
            )
            or 0
        )

        try:
            safe_form_count = int(
                safe_form_count
            )

        except (
            TypeError,
            ValueError,
        ):
            safe_form_count = 0

        pagination_params = (
            record.get(
                "pagination_params"
            )
            or record.get(
                "pagination"
            )
            or []
        )

        if isinstance(
            pagination_params,
            str,
        ):
            pagination_params = [
                pagination_params
            ]

        # I-stage에서 safe form을 찾은 endpoint 우선.
        # 구조상 값이 저장되지 않은 경우도 있으므로 완전히 배제하지는 않는다.
        normalized_url = normalize_url(
            str(
                url
            )
        )

        key = (
            record.get(
                "region"
            ),
            endpoint_class,
            normalized_url,
        )

        if key in seen:
            continue

        seen.add(key)

        normalized.append(
            {
                "region": (
                    record.get(
                        "region"
                    )
                    or ""
                ),
                "agency": (
                    record.get(
                        "agency"
                    )
                    or record.get(
                        "region"
                    )
                    or ""
                ),
                "endpoint_class": endpoint_class,
                "label": (
                    record.get(
                        "label"
                    )
                    or ""
                ),
                "url": normalized_url,
                "safe_form_count": safe_form_count,
                "pagination_params": sorted(
                    {
                        str(param)
                        for param
                        in pagination_params
                        if str(
                            param
                        ).strip()
                    }
                ),
            }
        )

    normalized.sort(
        key=lambda item: (
            0
            if item.get(
                "endpoint_class"
            )
            == "PRIMARY_GOSI_BOARD"
            else 1
            if item.get(
                "endpoint_class"
            )
            == "GAZETTE_ARCHIVE"
            else 2,
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

    return normalized[
        :MAX_ENDPOINTS
    ]


# ============================================================
# DISCOVERY STATE
# ============================================================

input_data = load_input()

searchable_endpoints = extract_searchable_endpoints(
    input_data
)

request_count = 0
http_success_count = 0
transport_error_count = 0
html_parse_count = 0

page_probe_count = 0
pagination_page_probe_count = 0

raw_row_count = 0
target_row_count = 0
url_query_only_row_leakage = 0

endpoint_results: List[
    Dict[
        str,
        Any
    ]
] = []

target_rows: List[
    Dict[
        str,
        Any
    ]
] = []

detail_seed_candidates: List[
    Dict[
        str,
        Any
    ]
] = []

visited_page_urls: Set[str] = set()


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
    "OFFICIAL BOARD TARGET ROW / PAGINATION DISCOVERY"
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
    "Input:",
    INPUT_PATH,
)

print(
    "Searchable endpoint count:",
    len(
        searchable_endpoints
    ),
)

print()


# ============================================================
# MAIN LOOP
# ============================================================

for endpoint_index, endpoint in enumerate(
    searchable_endpoints,
    start=1,
):

    region = endpoint[
        "region"
    ]

    agency = endpoint[
        "agency"
    ]

    endpoint_class = endpoint[
        "endpoint_class"
    ]

    endpoint_url = endpoint[
        "url"
    ]

    label = endpoint[
        "label"
    ]

    pagination_params = list(
        endpoint.get(
            "pagination_params"
        )
        or []
    )

    # endpoint URL 자체에서 pagination key 보완
    pagination_params = sorted(
        set(
            pagination_params
            + infer_pagination_params_from_url(
                endpoint_url
            )
        )
    )

    print(
        "------------------------------------------------------------"
    )

    print(
        f"ENDPOINT {endpoint_index}:",
        region,
        "/",
        endpoint_class,
    )

    print(
        "Label:",
        label,
    )

    print(
        "URL:",
        endpoint_url,
    )

    local_pages = []
    local_target_rows = []
    local_detail_seeds = []

    page_queue: List[
        Tuple[
            str,
            int,
            bool,
        ]
    ] = [
        (
            endpoint_url,
            1,
            False,
        )
    ]

    queued = {
        normalize_url(
            endpoint_url
        )
    }

    # synthetic pagination seed
    for page_no, pagination_url in enumerate(
        synthesize_pagination_urls(
            endpoint_url,
            pagination_params,
        ),
        start=2,
    ):

        normalized_pagination_url = normalize_url(
            pagination_url
        )

        if normalized_pagination_url in queued:
            continue

        queued.add(
            normalized_pagination_url
        )

        page_queue.append(
            (
                normalized_pagination_url,
                page_no,
                True,
            )
        )

    queue_index = 0

    while (
        queue_index
        < len(
            page_queue
        )
        and len(
            local_pages
        )
        < MAX_PAGES_PER_ENDPOINT
    ):

        page_url, page_number, is_pagination = (
            page_queue[
                queue_index
            ]
        )

        queue_index += 1

        normalized_page_url = normalize_url(
            page_url
        )

        if normalized_page_url in visited_page_urls:
            continue

        visited_page_urls.add(
            normalized_page_url
        )

        result = fetch_url(
            normalized_page_url
        )

        request_count += 1
        page_probe_count += 1

        if is_pagination:
            pagination_page_probe_count += 1

        if result.error:

            transport_error_count += 1

            local_pages.append(
                {
                    "page_number": page_number,
                    "request_url": normalized_page_url,
                    "final_url": None,
                    "http_status": None,
                    "error": result.error,
                    "row_count": 0,
                    "target_row_count": 0,
                }
            )

            continue

        if result.http_status == 200:
            http_success_count += 1

        final_url = (
            result.final_url
            or normalized_page_url
        )

        source = result.text

        if source:
            html_parse_count += 1

        row_fragments = extract_row_fragments(
            source
        )

        # target-bearing anchor fallback
        fallback_rows = build_anchor_fallback_rows(
            source=source,
            page_url=final_url,
        )

        if fallback_rows:

            existing_text = {
                compact_text(
                    strip_html(
                        fragment
                    )
                )
                for fragment in row_fragments
            }

            for fragment in fallback_rows:

                signature = compact_text(
                    strip_html(
                        fragment
                    )
                )

                if signature in existing_text:
                    continue

                existing_text.add(
                    signature
                )

                row_fragments.append(
                    fragment
                )

        raw_row_count += len(
            row_fragments
        )

        page_target_rows = []

        for row_index, row_source in enumerate(
            row_fragments,
            start=1,
        ):

            row = classify_row(
                region=region,
                agency=agency,
                endpoint_class=endpoint_class,
                endpoint_url=endpoint_url,
                page_url=final_url,
                page_number=page_number,
                row_index=row_index,
                row_source=row_source,
            )

            if (
                row[
                    "target_in_href_only"
                ]
                and not row[
                    "row_target_evidence"
                ]
            ):

                url_query_only_row_leakage += 1

            if not row[
                "row_target_evidence"
            ]:
                continue

            page_target_rows.append(
                row
            )

            local_target_rows.append(
                row
            )

            target_rows.append(
                row
            )

            # ------------------------------------------------
            # row-level target evidence가 있는 경우에만
            # 실제 상세 링크를 seed로 승격
            # ------------------------------------------------

            for detail_link in row[
                "detail_links"
            ]:

                seed = {
                    "region": region,
                    "agency": agency,
                    "endpoint_class": endpoint_class,
                    "endpoint_url": endpoint_url,
                    "source_page_url": final_url,
                    "page_number": page_number,
                    "row_index": row_index,
                    "row_preview": row[
                        "row_preview"
                    ],
                    "row_target_evidence": True,
                    "target_in_href_only": row[
                        "target_in_href_only"
                    ],
                    "label": detail_link.get(
                        "label",
                        "",
                    ),
                    "url": detail_link[
                        "url"
                    ],
                    "detail_url_hint": detail_link[
                        "detail_url_hint"
                    ],
                    "target_in_label": detail_link[
                        "target_in_label"
                    ],
                    "seed_score": detail_link[
                        "score"
                    ],
                }

                local_detail_seeds.append(
                    seed
                )

                detail_seed_candidates.append(
                    seed
                )

        target_row_count += len(
            page_target_rows
        )

        local_pages.append(
            {
                "page_number": page_number,
                "request_url": normalized_page_url,
                "final_url": result.final_url,
                "http_status": result.http_status,
                "content_type": result.content_type,
                "is_pagination_page": is_pagination,
                "row_count": len(
                    row_fragments
                ),
                "target_row_count": len(
                    page_target_rows
                ),
                "target_rows": page_target_rows,
            }
        )

        # ----------------------------------------------------
        # 실제 HTML pagination link 추출
        # ----------------------------------------------------

        discovered_pagination_urls = extract_pagination_links(
            source,
            page_url=final_url,
            endpoint_url=endpoint_url,
        )

        for discovered_url in discovered_pagination_urls:

            normalized_discovered = normalize_url(
                discovered_url
            )

            if normalized_discovered in queued:
                continue

            if normalized_discovered in visited_page_urls:
                continue

            queued.add(
                normalized_discovered
            )

            page_queue.append(
                (
                    normalized_discovered,
                    page_number + 1,
                    True,
                )
            )

        time.sleep(
            REQUEST_SLEEP
        )

    print(
        "Pages probed:",
        len(
            local_pages
        ),
    )

    print(
        "Target-bearing rows:",
        len(
            local_target_rows
        ),
    )

    print(
        "Detail seeds:",
        len(
            local_detail_seeds
        ),
    )

    for row in local_target_rows[
        :3
    ]:

        print(
            "  TARGET ROW:",
            row.get(
                "row_preview"
            ),
        )

    endpoint_results.append(
        {
            "region": region,
            "agency": agency,
            "endpoint_class": endpoint_class,
            "label": label,
            "endpoint_url": endpoint_url,
            "pagination_params": pagination_params,
            "page_probe_count": len(
                local_pages
            ),
            "target_row_count": len(
                local_target_rows
            ),
            "detail_seed_count": len(
                local_detail_seeds
            ),
            "pages": local_pages,
        }
    )


# ============================================================
# DEDUPE TARGET ROWS
# ============================================================

deduped_target_rows = []
seen_target_rows = set()

for row in target_rows:

    key = (
        row.get(
            "region"
        ),
        normalize_url(
            str(
                row.get(
                    "page_url"
                )
                or ""
            )
        ),
        compact_text(
            str(
                row.get(
                    "row_text"
                )
                or ""
            )
        )[:800],
    )

    if key in seen_target_rows:
        continue

    seen_target_rows.add(
        key
    )

    deduped_target_rows.append(
        row
    )


# ============================================================
# DEDUPE DETAIL SEEDS
# ============================================================

deduped_detail_seeds = []
seen_detail_seeds = set()

for seed in detail_seed_candidates:

    normalized_seed_url = normalize_url(
        str(
            seed.get(
                "url"
            )
            or ""
        )
    )

    key = (
        seed.get(
            "region"
        ),
        normalized_seed_url,
    )

    if key in seen_detail_seeds:
        continue

    seen_detail_seeds.add(
        key
    )

    normalized_seed = dict(
        seed
    )

    normalized_seed[
        "url"
    ] = normalized_seed_url

    deduped_detail_seeds.append(
        normalized_seed
    )


deduped_detail_seeds.sort(
    key=lambda item: (
        -int(
            item.get(
                "seed_score",
                0,
            )
        ),
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
# RESOLUTION
# ============================================================

if deduped_detail_seeds:

    resolution = (
        "TARGET_BEARING_RESULT_ROW_DETAIL_SEED_DISCOVERED"
    )

    next_action = (
        "K-stage에서 확보한 row-target-evidence 기반 상세 게시물 URL만 "
        "L-stage 원문 검증 대상으로 사용하여 실제 개발밀도관리구역 "
        "지정·변경·해제 고시 여부, 고시번호, 지정일, 행정구역, "
        "첨부파일, 지정 범위 및 현재 유효 여부를 검증한다."
    )

elif deduped_target_rows:

    resolution = (
        "TARGET_BEARING_RESULT_ROW_DISCOVERED_NO_DETAIL_LINK"
    )

    next_action = (
        "target-bearing row는 확인되었으나 상세 href가 추출되지 않았다. "
        "onclick/data-* 속성 및 JavaScript 상세보기 함수에서 document key를 "
        "추출하는 L-stage dynamic detail endpoint discovery를 수행한다."
    )

else:

    resolution = (
        "ROW_LEVEL_PAGINATION_DISCOVERY_COMPLETED_NO_TARGET_ROW"
    )

    next_action = (
        "현재 searchable endpoint의 GET pagination에서는 target row가 확인되지 않았다. "
        "POST pagination, hidden field 유지 검색, 과거 공보 archive, "
        "동적 JavaScript API 및 전용 행정전자민원 고시공고 endpoint로 탐색 범위를 확장한다."
    )


runtime_registration_blocked = True
site_false_interpretation_blocked = True


# ============================================================
# OUTPUT
# ============================================================

output_data = {
    "step": (
        "STEP 17-21-C-16-8-K "
        "Development Density Management Area "
        "Official Board Target Row / Pagination Discovery"
    ),

    "target": {
        "name": TARGET_NAME,
        "standard_code": STANDARD_CODE,
    },

    "input": {
        "path": str(
            INPUT_PATH
        ),
        "searchable_endpoint_count": len(
            searchable_endpoints
        ),
    },

    "method": {
        "row_level_target_evidence_required": True,
        "url_query_only_target_prohibited": True,
        "search_page_final_positive_allowed": False,
        "pagination_discovery_enabled": True,
        "synthetic_pagination_enabled": True,
        "detail_seed_requires_target_row": True,
        "runtime_registration_allowed": False,
        "site_false_interpretation_allowed": False,
        "max_pages_per_endpoint": MAX_PAGES_PER_ENDPOINT,
    },

    "summary": {
        "endpoint_count": len(
            searchable_endpoints
        ),
        "request_count": request_count,
        "http_success_count": http_success_count,
        "transport_error_count": transport_error_count,
        "html_parse_count": html_parse_count,
        "page_probe_count": page_probe_count,
        "pagination_page_probe_count": pagination_page_probe_count,
        "raw_row_count": raw_row_count,
        "target_row_count": len(
            deduped_target_rows
        ),
        "detail_seed_candidate_count": len(
            deduped_detail_seeds
        ),
        "url_query_only_row_leakage": (
            url_query_only_row_leakage
        ),
    },

    "target_rows": (
        deduped_target_rows
    ),

    "detail_seed_candidates": (
        deduped_detail_seeds
    ),

    "endpoint_results": (
        endpoint_results
    ),

    "resolution": resolution,

    "runtime_registration_blocked": (
        runtime_registration_blocked
    ),

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
    "Endpoint count:",
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
    "Page probe count:",
    page_probe_count,
)

print(
    "Pagination page probe count:",
    pagination_page_probe_count,
)

print(
    "Raw row count:",
    raw_row_count,
)

print(
    "Target-bearing row count:",
    len(
        deduped_target_rows
    ),
)

print(
    "Detail seed candidate count:",
    len(
        deduped_detail_seeds
    ),
)

print(
    "URL-query-only row leakage:",
    url_query_only_row_leakage,
)

print()


if deduped_target_rows:

    print(
        "TARGET-BEARING RESULT ROWS"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, row in enumerate(
        deduped_target_rows[
            :50
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            row.get(
                "region"
            ),
        )

        print(
            "Class:",
            row.get(
                "endpoint_class"
            ),
        )

        print(
            "Page:",
            row.get(
                "page_number"
            ),
        )

        print(
            "Target in text:",
            row.get(
                "row_target_in_text"
            ),
        )

        print(
            "Target in anchor label:",
            row.get(
                "target_in_anchor_label"
            ),
        )

        print(
            "Target in href only:",
            row.get(
                "target_in_href_only"
            ),
        )

        print(
            "Detail links:",
            len(
                row.get(
                    "detail_links"
                )
                or []
            ),
        )

        print(
            "Preview:",
            row.get(
                "row_preview"
            ),
        )

        print()


if deduped_detail_seeds:

    print(
        "TARGET DETAIL SEED CANDIDATES"
    )

    print(
        "------------------------------------------------------------"
    )

    for index, seed in enumerate(
        deduped_detail_seeds[
            :100
        ],
        start=1,
    ):

        print(
            f"[{index}]",
            seed.get(
                "region"
            ),
        )

        print(
            "Class:",
            seed.get(
                "endpoint_class"
            ),
        )

        print(
            "Score:",
            seed.get(
                "seed_score"
            ),
        )

        print(
            "Label:",
            seed.get(
                "label"
            ),
        )

        print(
            "Row target evidence:",
            seed.get(
                "row_target_evidence"
            ),
        )

        print(
            "URL:",
            seed.get(
                "url"
            ),
        )

        print()


if not deduped_target_rows:

    print(
        "No target-bearing result row discovered."
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

endpoint_keys = {
    (
        item.get(
            "region"
        ),
        item.get(
            "endpoint_class"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in searchable_endpoints
}


target_row_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "page_url"
                )
                or ""
            )
        ),
        compact_text(
            str(
                item.get(
                    "row_text"
                )
                or ""
            )
        )[:800],
    )
    for item in deduped_target_rows
}


detail_seed_keys = {
    (
        item.get(
            "region"
        ),
        normalize_url(
            str(
                item.get(
                    "url"
                )
                or ""
            )
        ),
    )
    for item in deduped_detail_seeds
}


all_target_rows_have_evidence = all(
    item.get(
        "row_target_evidence"
    )
    is True
    for item in deduped_target_rows
)


all_target_rows_have_visible_target = all(
    (
        item.get(
            "row_target_in_text"
        )
        is True
        or item.get(
            "target_in_anchor_label"
        )
        is True
    )
    for item in deduped_target_rows
)


all_detail_seeds_have_row_evidence = all(
    item.get(
        "row_target_evidence"
    )
    is True
    for item in deduped_detail_seeds
)


all_detail_seeds_have_url = all(
    bool(
        item.get(
            "url"
        )
    )
    for item in deduped_detail_seeds
)


all_detail_seeds_not_search_urls = all(
    not is_search_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in deduped_detail_seeds
)


all_detail_seeds_not_attachment_urls = all(
    not is_attachment_url(
        str(
            item.get(
                "url"
            )
            or ""
        )
    )
    for item in deduped_detail_seeds
)


all_endpoint_classes_allowed = all(
    item.get(
        "endpoint_class"
    )
    in ALLOWED_ENDPOINT_CLASSES
    for item in searchable_endpoints
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

    "input exists": (
        INPUT_PATH.exists()
    ),

    "I-stage input parsed": (
        isinstance(
            input_data,
            dict,
        )
    ),

    "searchable endpoints loaded": (
        len(
            searchable_endpoints
        )
        > 0
    ),

    "row-level target evidence guard enabled": (
        output_data[
            "method"
        ][
            "row_level_target_evidence_required"
        ]
        is True
    ),

    "URL-query-only target prohibited": (
        output_data[
            "method"
        ][
            "url_query_only_target_prohibited"
        ]
        is True
    ),

    "search page final positive prohibited": (
        output_data[
            "method"
        ][
            "search_page_final_positive_allowed"
        ]
        is False
    ),

    "pagination discovery enabled": (
        output_data[
            "method"
        ][
            "pagination_discovery_enabled"
        ]
        is True
    ),

    "detail seed requires target row": (
        output_data[
            "method"
        ][
            "detail_seed_requires_target_row"
        ]
        is True
    ),

    "endpoint candidates unique": (
        len(
            endpoint_keys
        )
        == len(
            searchable_endpoints
        )
    ),

    "all endpoint classes allowed": (
        all_endpoint_classes_allowed
    ),

    "requests executed": (
        request_count
        > 0
    ),

    "page probes executed": (
        page_probe_count
        > 0
    ),

    "target rows unique": (
        len(
            target_row_keys
        )
        == len(
            deduped_target_rows
        )
    ),

    "detail seed candidates unique": (
        len(
            detail_seed_keys
        )
        == len(
            deduped_detail_seeds
        )
    ),

    "all target rows have row evidence": (
        all_target_rows_have_evidence
    ),

    "all target rows have visible target": (
        all_target_rows_have_visible_target
    ),

    "all detail seeds have row target evidence": (
        all_detail_seeds_have_row_evidence
    ),

    "all detail seeds have URL": (
        all_detail_seeds_have_url
    ),

    "all detail seeds are not search URLs": (
        all_detail_seeds_not_search_urls
    ),

    "all detail seeds are not attachment URLs": (
        all_detail_seeds_not_attachment_urls
    ),

    "runtime registration remains blocked": (
        runtime_registration_blocked
        is True
    ),

    "SITE FALSE remains blocked": (
        site_false_interpretation_blocked
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
        "official board target row / pagination discovery regression failed"
    )
