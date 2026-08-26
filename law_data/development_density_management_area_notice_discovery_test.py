# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-B
Development Density Management Area Notice Discovery

목표
======================================================================
개발밀도관리구역(표준코드 UQQ700)의 runtime spatial source를
확정하기 전에 실제 지정 / 변경 / 해제 고시 사례를 먼저 발견한다.

C-16-8-A 결과
======================================================================
Target condition:
    개발밀도관리구역

Standard code:
    UQQ700

VWorld probe:
    LT_C_UQ141  => reachable
    LT_C_UQQ700 => INVALID_RANGE
    LT_C_UQ700  => INVALID_RANGE

LT_C_UQ141 전국 일부 지역 탐색 결과:
    개발밀도관리구역 feature 미발견

따라서:
    LT_C_UQ141을 runtime source로 등록하지 않는다.
    SITE FALSE도 판정하지 않는다.

이번 단계
======================================================================
공개 웹 검색을 discovery 용도로만 사용하여

1. "개발밀도관리구역" 실제 고시 후보 검색
2. go.kr / 지방자치단체 공식 도메인 후보 우선 수집
3. 지정 / 변경 / 해제 후보 분류
4. 행정구역 / 고시번호 / 위치 관련 단서 추출
5. 다음 spatial reverse-discovery 단계에 사용할 positive 후보 저장

중요
======================================================================
검색엔진 결과 자체는 법적 evidence가 아니다.

검색엔진:
    DISCOVERY TRANSPORT

실제 지자체 / 공공기관 페이지:
    POSSIBLE OFFICIAL SOURCE

로 구분한다.

실제 고시 원문이 확인되지 않은 검색결과만으로
runtime condition을 등록하거나 SITE TRUE/FALSE를 판정하지 않는다.
"""

from __future__ import annotations

import html
import json
import re
import time

from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import (
    parse_qs,
    quote_plus,
    unquote,
    urlparse,
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_management_area_notice_discovery.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = (
    "개발밀도관리구역"
)

TARGET_STANDARD_CODE = (
    "UQQ700"
)


# ============================================================
# SEARCH
# ============================================================

SEARCH_TIMEOUT = 30

SEARCH_DELAY_SECONDS = 1.0

MAX_RESULT_PER_QUERY = 30


SEARCH_QUERIES = [

    '"개발밀도관리구역" "고시"',

    '"개발밀도관리구역" "지정"',

    '"개발밀도관리구역" "지정 고시"',

    '"개발밀도관리구역" "변경 고시"',

    '"개발밀도관리구역" "해제 고시"',

    '"개발밀도관리구역" "용적률"',

    '"개발밀도관리구역" "도시계획위원회"',

    '"개발밀도관리구역" site:go.kr',

    '"개발밀도관리구역" "고시" site:go.kr',

    '"개발밀도관리구역" "지정" site:go.kr',
]


# ============================================================
# HTTP
# ============================================================

HEADERS = {

    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),

    "Accept": (
        "text/html,"
        "application/xhtml+xml,"
        "application/xml;q=0.9,"
        "*/*;q=0.8"
    ),

    "Accept-Language": (
        "ko-KR,ko;q=0.9,en;q=0.7"
    ),
}


# ============================================================
# OFFICIAL DOMAIN RULES
# ============================================================

OFFICIAL_DOMAIN_SUFFIXES = (
    ".go.kr",
)

OFFICIAL_EXACT_DOMAINS = {
    "go.kr",
    "www.go.kr",
}


# ============================================================
# REGION TOKENS
# ============================================================

REGION_TOKENS = [

    "서울특별시",
    "부산광역시",
    "대구광역시",
    "인천광역시",
    "광주광역시",
    "대전광역시",
    "울산광역시",
    "세종특별자치시",

    "경기도",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전북특별자치도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]


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


def strip_tags(
    value: str,
) -> str:

    value = re.sub(
        r"<script\b[^>]*>.*?</script>",
        " ",
        value,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    value = re.sub(
        r"<style\b[^>]*>.*?</style>",
        " ",
        value,
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    value = re.sub(
        r"<[^>]+>",
        " ",
        value,
    )

    return normalize_space(
        html.unescape(
            value
        )
    )


def safe_hostname(
    url: str,
) -> str:

    try:

        hostname = (
            urlparse(
                url
            ).hostname
            or ""
        )

    except Exception:

        return ""

    return (
        hostname
        .lower()
        .strip(".")
    )


def is_official_domain(
    url: str,
) -> bool:

    hostname = (
        safe_hostname(
            url
        )
    )

    if not hostname:

        return False

    if (
        hostname
        in OFFICIAL_EXACT_DOMAINS
    ):

        return True

    return any(
        hostname.endswith(
            suffix
        )
        for suffix
        in OFFICIAL_DOMAIN_SUFFIXES
    )


def decode_search_redirect(
    url: str,
) -> str:

    """
    검색엔진 redirect URL에서 원본 URL을 최대한 복원한다.
    """

    raw = html.unescape(
        str(
            url
            or ""
        )
    ).strip()

    if not raw:

        return ""

    if raw.startswith(
        "//"
    ):

        raw = (
            "https:"
            + raw
        )

    try:

        parsed = urlparse(
            raw
        )

    except Exception:

        return raw

    query = parse_qs(
        parsed.query
    )

    for key in (
        "url",
        "u",
        "q",
        "target",
        "r",
    ):

        values = (
            query.get(
                key
            )
            or []
        )

        for value in values:

            decoded = unquote(
                value
            )

            if decoded.startswith(
                (
                    "http://",
                    "https://",
                )
            ):

                return decoded

    return raw


def extract_notice_number(
    text: str,
) -> Optional[str]:

    patterns = [

        r"([가-힣A-Za-z0-9·\-\s]+고시\s*제?\s*\d{4}\s*-\s*\d+\s*호?)",

        r"(고시\s*제?\s*\d{4}\s*-\s*\d+\s*호?)",

        r"(제\s*\d{4}\s*-\s*\d+\s*호)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:

            return normalize_space(
                match.group(
                    1
                )
            )

    return None


def detect_action(
    text: str,
) -> str:

    normalized = normalize_space(
        text
    )

    if re.search(
        r"해제|폐지",
        normalized,
    ):

        return "RELEASE"

    if re.search(
        r"변경",
        normalized,
    ):

        return "CHANGE"

    if re.search(
        r"지정",
        normalized,
    ):

        return "DESIGNATION"

    return "UNKNOWN"


def detect_regions(
    text: str,
) -> List[str]:

    normalized = normalize_space(
        text
    )

    return [
        token
        for token
        in REGION_TOKENS
        if token
        in normalized
    ]


def candidate_score(
    *,
    title: str,
    snippet: str,
    url: str,
) -> int:

    combined = normalize_space(
        title
        + " "
        + snippet
    )

    score = 0

    if (
        TARGET_NAME
        in combined
    ):

        score += 50

    if is_official_domain(
        url
    ):

        score += 40

    if re.search(
        r"고시",
        combined,
    ):

        score += 20

    if re.search(
        r"지정|변경|해제|폐지",
        combined,
    ):

        score += 15

    if re.search(
        r"용적률|건폐율",
        combined,
    ):

        score += 10

    if re.search(
        r"위치|범위|면적",
        combined,
    ):

        score += 10

    if extract_notice_number(
        combined
    ):

        score += 20

    return score


# ============================================================
# SEARCH RESULT EXTRACTION
# ============================================================

def extract_anchor_candidates(
    source_html: str,
) -> List[Dict[str, str]]:

    """
    범용 anchor parser.

    검색엔진 HTML 구조가 변경될 수 있으므로
    특정 CSS selector에 강하게 의존하지 않는다.
    """

    pattern = re.compile(
        r"""
        <a
        \s+
        [^>]*?
        href=
        ["']
        (?P<href>[^"']+)
        ["']
        [^>]*?
        >
        (?P<body>.*?)
        </a>
        """,
        flags=(
            re.IGNORECASE
            | re.DOTALL
            | re.VERBOSE
        ),
    )

    results: List[
        Dict[str, str]
    ] = []

    for match in pattern.finditer(
        source_html
    ):

        href = (
            match.group(
                "href"
            )
            or ""
        )

        body = (
            match.group(
                "body"
            )
            or ""
        )

        title = strip_tags(
            body
        )

        url = decode_search_redirect(
            href
        )

        if not title:

            continue

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):

            continue

        results.append(
            {
                "title":
                    title,

                "url":
                    url,
            }
        )

    return results


# ============================================================
# GOOGLE DISCOVERY
# ============================================================

def google_search(
    query: str,
) -> Dict[str, Any]:

    url = (
        "https://www.google.com/search"
    )

    params = {

        "q":
            query,

        "num":
            str(
                MAX_RESULT_PER_QUERY
            ),

        "hl":
            "ko",
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=SEARCH_TIMEOUT,
        )

    except requests.RequestException as exc:

        return {
            "engine":
                "GOOGLE",

            "query":
                query,

            "http_status":
                None,

            "transport_error":
                repr(
                    exc
                ),

            "results":
                [],
        }

    source_html = (
        response.text
        or ""
    )

    anchors = (
        extract_anchor_candidates(
            source_html
        )
    )

    results = []

    seen = set()

    for anchor in anchors:

        target_url = (
            anchor[
                "url"
            ]
        )

        hostname = safe_hostname(
            target_url
        )

        # 검색엔진 자체 링크 제거
        if (
            "google."
            in hostname
        ):

            continue

        key = (
            target_url
        )

        if key in seen:

            continue

        seen.add(
            key
        )

        title = (
            anchor[
                "title"
            ]
        )

        results.append(
            {
                "title":
                    title,

                "url":
                    target_url,

                "hostname":
                    hostname,

                "official_domain":
                    is_official_domain(
                        target_url
                    ),
            }
        )

    return {
        "engine":
            "GOOGLE",

        "query":
            query,

        "http_status":
            response.status_code,

        "content_type":
            response.headers.get(
                "Content-Type"
            ),

        "response_length":
            len(
                source_html
            ),

        "transport_error":
            None,

        "results":
            results[
                :MAX_RESULT_PER_QUERY
            ],
    }


# ============================================================
# BING DISCOVERY
# ============================================================

def bing_search(
    query: str,
) -> Dict[str, Any]:

    url = (
        "https://www.bing.com/search"
    )

    params = {

        "q":
            query,

        "count":
            str(
                MAX_RESULT_PER_QUERY
            ),

        "setlang":
            "ko",
    }

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=SEARCH_TIMEOUT,
        )

    except requests.RequestException as exc:

        return {
            "engine":
                "BING",

            "query":
                query,

            "http_status":
                None,

            "transport_error":
                repr(
                    exc
                ),

            "results":
                [],
        }

    source_html = (
        response.text
        or ""
    )

    anchors = (
        extract_anchor_candidates(
            source_html
        )
    )

    results = []

    seen = set()

    for anchor in anchors:

        target_url = (
            anchor[
                "url"
            ]
        )

        hostname = safe_hostname(
            target_url
        )

        if (
            "bing.com"
            in hostname
            or "microsoft.com"
            in hostname
        ):

            continue

        if (
            target_url
            in seen
        ):

            continue

        seen.add(
            target_url
        )

        results.append(
            {
                "title":
                    anchor[
                        "title"
                    ],

                "url":
                    target_url,

                "hostname":
                    hostname,

                "official_domain":
                    is_official_domain(
                        target_url
                    ),
            }
        )

    return {
        "engine":
            "BING",

        "query":
            query,

        "http_status":
            response.status_code,

        "content_type":
            response.headers.get(
                "Content-Type"
            ),

        "response_length":
            len(
                source_html
            ),

        "transport_error":
            None,

        "results":
            results[
                :MAX_RESULT_PER_QUERY
            ],
    }


# ============================================================
# OFFICIAL PAGE PROBE
# ============================================================

def probe_official_page(
    url: str,
) -> Dict[str, Any]:

    """
    검색 결과 중 공식 도메인만 실제 페이지를 조회한다.

    주의:
    PDF/HWP 첨부파일 자체의 본문 파싱은 하지 않는다.
    이번 단계에서는 landing page / 게시물 HTML까지만 확인한다.
    """

    try:

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=SEARCH_TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as exc:

        return {
            "url":
                url,

            "http_status":
                None,

            "transport_error":
                repr(
                    exc
                ),

            "official_domain":
                is_official_domain(
                    url
                ),

            "target_text_found":
                False,
        }

    text = (
        response.text
        or ""
    )

    content_type = (
        response.headers.get(
            "Content-Type",
            "",
        )
    )

    normalized_text = ""

    if (
        "html"
        in content_type.lower()
        or "text"
        in content_type.lower()
    ):

        normalized_text = (
            strip_tags(
                text
            )
        )

    return {
        "url":
            url,

        "final_url":
            response.url,

        "http_status":
            response.status_code,

        "content_type":
            content_type,

        "response_length":
            len(
                response.content
                or b""
            ),

        "transport_error":
            None,

        "official_domain":
            (
                is_official_domain(
                    response.url
                )
                or is_official_domain(
                    url
                )
            ),

        "target_text_found":
            (
                TARGET_NAME
                in normalized_text
            ),

        "notice_number":
            extract_notice_number(
                normalized_text
            ),

        "action":
            detect_action(
                normalized_text
            ),

        "regions":
            detect_regions(
                normalized_text
            ),

        "text_preview":
            normalized_text[
                :1200
            ],
    }


# ============================================================
# MAIN
# ============================================================

print(
    "============================================================"
)

print(
    "DEVELOPMENT DENSITY MANAGEMENT AREA NOTICE DISCOVERY"
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
    TARGET_STANDARD_CODE,
)

print()


# ============================================================
# 1. SEARCH
# ============================================================

search_runs: List[
    Dict[str, Any]
] = []


for index, query in enumerate(
    SEARCH_QUERIES,
    start=1,
):

    print(
        "------------------------------------------------------------"
    )

    print(
        f"QUERY {index}:",
        query,
    )

    google_result = (
        google_search(
            query
        )
    )

    search_runs.append(
        google_result
    )

    print(
        "Google HTTP:",
        google_result.get(
            "http_status"
        ),
    )

    print(
        "Google results:",
        len(
            google_result.get(
                "results",
                [],
            )
        ),
    )

    time.sleep(
        SEARCH_DELAY_SECONDS
    )

    bing_result = (
        bing_search(
            query
        )
    )

    search_runs.append(
        bing_result
    )

    print(
        "Bing HTTP:",
        bing_result.get(
            "http_status"
        ),
    )

    print(
        "Bing results:",
        len(
            bing_result.get(
                "results",
                [],
            )
        ),
    )

    time.sleep(
        SEARCH_DELAY_SECONDS
    )


# ============================================================
# 2. COLLECT UNIQUE
# ============================================================

unique_map: Dict[
    str,
    Dict[str, Any]
] = {}


for run in search_runs:

    engine = (
        run.get(
            "engine"
        )
    )

    query = (
        run.get(
            "query"
        )
    )

    for item in (
        run.get(
            "results",
            []
        )
    ):

        if not isinstance(
            item,
            dict,
        ):

            continue

        url = normalize_space(
            item.get(
                "url"
            )
        )

        title = normalize_space(
            item.get(
                "title"
            )
        )

        if not url:

            continue

        current = (
            unique_map.get(
                url
            )
        )

        if current is None:

            current = {
                "url":
                    url,

                "hostname":
                    safe_hostname(
                        url
                    ),

                "official_domain":
                    is_official_domain(
                        url
                    ),

                "titles":
                    [],

                "engines":
                    [],

                "queries":
                    [],
            }

            unique_map[
                url
            ] = current

        if (
            title
            and title
            not in current[
                "titles"
            ]
        ):

            current[
                "titles"
            ].append(
                title
            )

        if (
            engine
            and engine
            not in current[
                "engines"
            ]
        ):

            current[
                "engines"
            ].append(
                engine
            )

        if (
            query
            and query
            not in current[
                "queries"
            ]
        ):

            current[
                "queries"
            ].append(
                query
            )


all_candidates = list(
    unique_map.values()
)


# ============================================================
# 3. SEARCH RESULT CLASSIFICATION
# ============================================================

for item in all_candidates:

    title_text = normalize_space(
        " ".join(
            item.get(
                "titles",
                []
            )
        )
    )

    item[
        "search_action"
    ] = (
        detect_action(
            title_text
        )
    )

    item[
        "search_notice_number"
    ] = (
        extract_notice_number(
            title_text
        )
    )

    item[
        "search_regions"
    ] = (
        detect_regions(
            title_text
        )
    )

    item[
        "score"
    ] = (
        candidate_score(
            title=title_text,
            snippet="",
            url=item[
                "url"
            ],
        )
    )


all_candidates.sort(
    key=lambda x: (
        bool(
            x.get(
                "official_domain"
            )
        ),
        int(
            x.get(
                "score"
            )
            or 0
        ),
    ),
    reverse=True,
)


# ============================================================
# 4. OFFICIAL CANDIDATES
# ============================================================

official_candidates = [

    item
    for item
    in all_candidates

    if item.get(
        "official_domain"
    )
]


print()

print(
    "============================================================"
)

print(
    "SEARCH RESULT SUMMARY"
)

print(
    "============================================================"
)

print(
    "Unique result count:",
    len(
        all_candidates
    ),
)

print(
    "Official-domain candidate count:",
    len(
        official_candidates
    ),
)


# ============================================================
# 5. PROBE OFFICIAL CANDIDATES
# ============================================================

official_probes: List[
    Dict[str, Any]
] = []


for index, item in enumerate(
    official_candidates[
        :30
    ],
    start=1,
):

    print()

    print(
        "------------------------------------------------------------"
    )

    print(
        "OFFICIAL CANDIDATE",
        index,
    )

    print(
        "Title:",
        (
            item.get(
                "titles"
            )
            or [""]
        )[0],
    )

    print(
        "URL:",
        item.get(
            "url"
        ),
    )

    print(
        "Search score:",
        item.get(
            "score"
        ),
    )

    probe = (
        probe_official_page(
            item[
                "url"
            ]
        )
    )

    probe[
        "search_metadata"
    ] = item

    official_probes.append(
        probe
    )

    print(
        "HTTP:",
        probe.get(
            "http_status"
        ),
    )

    print(
        "Final URL:",
        probe.get(
            "final_url"
        ),
    )

    print(
        "Target text:",
        probe.get(
            "target_text_found"
        ),
    )

    print(
        "Notice number:",
        probe.get(
            "notice_number"
        ),
    )

    print(
        "Action:",
        probe.get(
            "action"
        ),
    )

    print(
        "Regions:",
        probe.get(
            "regions"
        ),
    )

    if probe.get(
        "transport_error"
    ):

        print(
            "Transport error:",
            probe.get(
                "transport_error"
            ),
        )

    time.sleep(
        SEARCH_DELAY_SECONDS
    )


# ============================================================
# 6. POSITIVE NOTICE CANDIDATES
# ============================================================

positive_notice_candidates = [

    probe
    for probe
    in official_probes

    if (
        probe.get(
            "http_status"
        )
        == 200

        and probe.get(
            "official_domain"
        )
        is True

        and probe.get(
            "target_text_found"
        )
        is True

        and probe.get(
            "action"
        )
        in {
            "DESIGNATION",
            "CHANGE",
            "RELEASE",
        }
    )
]


# ============================================================
# 7. RANK
# ============================================================

def positive_rank(
    item: Dict[str, Any],
) -> int:

    score = 0

    if item.get(
        "target_text_found"
    ):

        score += 100

    if item.get(
        "notice_number"
    ):

        score += 40

    if item.get(
        "regions"
    ):

        score += 20

    if (
        item.get(
            "action"
        )
        == "DESIGNATION"
    ):

        score += 30

    elif (
        item.get(
            "action"
        )
        == "CHANGE"
    ):

        score += 20

    elif (
        item.get(
            "action"
        )
        == "RELEASE"
    ):

        score += 10

    search_score = (
        item.get(
            "search_metadata",
            {},
        ).get(
            "score",
            0,
        )
    )

    score += int(
        search_score
        or 0
    )

    return score


for item in positive_notice_candidates:

    item[
        "positive_rank"
    ] = (
        positive_rank(
            item
        )
    )


positive_notice_candidates.sort(
    key=lambda x: int(
        x.get(
            "positive_rank"
        )
        or 0
    ),
    reverse=True,
)


# ============================================================
# 8. OUTPUT CONSOLE
# ============================================================

print()

print(
    "============================================================"
)

print(
    "POSITIVE NOTICE CANDIDATES"
)

print(
    "============================================================"
)


if not positive_notice_candidates:

    print(
        "No official positive notice candidate confirmed."
    )

else:

    for index, item in enumerate(
        positive_notice_candidates,
        start=1,
    ):

        search_metadata = (
            item.get(
                "search_metadata",
                {},
            )
        )

        print()

        print(
            f"[{index}]"
        )

        print(
            "Rank:",
            item.get(
                "positive_rank"
            ),
        )

        print(
            "Title:",
            (
                search_metadata.get(
                    "titles"
                )
                or [""]
            )[0],
        )

        print(
            "URL:",
            item.get(
                "final_url"
            )
            or item.get(
                "url"
            ),
        )

        print(
            "Notice:",
            item.get(
                "notice_number"
            ),
        )

        print(
            "Action:",
            item.get(
                "action"
            ),
        )

        print(
            "Regions:",
            item.get(
                "regions"
            ),
        )

        print(
            "Preview:",
            normalize_space(
                item.get(
                    "text_preview"
                )
            )[
                :500
            ],
        )


# ============================================================
# 9. RESOLUTION
# ============================================================

if positive_notice_candidates:

    resolution = (
        "OFFICIAL_NOTICE_CANDIDATE_DISCOVERED"
    )

else:

    resolution = (
        "OFFICIAL_NOTICE_NOT_YET_DISCOVERED"
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
    "Do not register runtime spatial condition yet."
)

print(
    "Do not interpret missing notice discovery as SITE FALSE."
)


# ============================================================
# 10. SAVE
# ============================================================

output = {

    "step":
        "STEP 17-21-C-16-8-B",

    "target": {
        "name":
            TARGET_NAME,

        "standard_code":
            TARGET_STANDARD_CODE,
    },

    "previous_resolution": {
        "LT_C_UQ141":
            "REACHABLE_BUT_TARGET_NOT_DISCOVERED",

        "LT_C_UQQ700":
            "INVALID_RANGE",

        "LT_C_UQ700":
            "INVALID_RANGE",
    },

    "search": {
        "query_count":
            len(
                SEARCH_QUERIES
            ),

        "engine_run_count":
            len(
                search_runs
            ),

        "unique_result_count":
            len(
                all_candidates
            ),

        "official_candidate_count":
            len(
                official_candidates
            ),

        "official_probe_count":
            len(
                official_probes
            ),

        "positive_notice_candidate_count":
            len(
                positive_notice_candidates
            ),
    },

    "positive_notice_candidates":
        positive_notice_candidates,

    "official_candidates":
        official_candidates,

    "resolution":
        resolution,

    "runtime_registration_allowed":
        False,

    "site_false_allowed":
        False,
}


OUTPUT_PATH.write_text(
    json.dumps(
        output,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()

print(
    "Output:",
    OUTPUT_PATH,
)


# ============================================================
# VALIDATION
# ============================================================

successful_search_runs = [

    item
    for item
    in search_runs

    if item.get(
        "http_status"
    )
    == 200
]


validations = {

    "target name": (
        TARGET_NAME
        == "개발밀도관리구역"
    ),

    "standard code": (
        TARGET_STANDARD_CODE
        == "UQQ700"
    ),

    "search queries exist": (
        len(
            SEARCH_QUERIES
        )
        >= 5
    ),

    "search executed": (
        len(
            search_runs
        )
        > 0
    ),

    "at least one search engine responded": (
        len(
            successful_search_runs
        )
        > 0
    ),

    "candidate collection completed": (
        isinstance(
            all_candidates,
            list,
        )
    ),

    "official filtering completed": (
        isinstance(
            official_candidates,
            list,
        )
    ),

    "positive candidate collection completed": (
        isinstance(
            positive_notice_candidates,
            list,
        )
    ),

    "runtime registration remains blocked": (
        output[
            "runtime_registration_allowed"
        ]
        is False
    ),

    "SITE FALSE remains blocked": (
        output[
            "site_false_allowed"
        ]
        is False
    ),

    "output written": (
        OUTPUT_PATH.exists()
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


for name, passed in (
    validations.items()
):

    print(
        f"{name}:",
        passed,
    )


all_pass = all(
    validations.values()
)


print()

print(
    "Successful search runs:",
    len(
        successful_search_runs
    ),
)

print(
    "Official candidate count:",
    len(
        official_candidates
    ),
)

print(
    "Positive notice candidate count:",
    len(
        positive_notice_candidates
    ),
)

print()

print(
    "all_pass:",
    all_pass,
)


if not all_pass:

    raise AssertionError(
        "Development density management area notice discovery failed"
    )