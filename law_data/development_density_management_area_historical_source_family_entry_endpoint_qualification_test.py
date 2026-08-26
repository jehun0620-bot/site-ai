# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S-2
Development Density Management Area
Historical Source Family Entry Endpoint Qualification

목표
======================================================================
S-stage에서 broad recovery된 historical source family endpoint candidate를
직접 HTTP 재검증하여 실제 T-stage query 실행 대상으로 사용할 수 있는
qualified historical endpoint만 남긴다.

입력:
    law_data/output/
    development_density_management_area_
    historical_source_family_entry_endpoint_recovery.json

보조 입력:
    law_data/output/
    development_density_management_area_
    historical_official_source_endpoint_discovery.json

    law_data/output/
    development_density_management_area_
    historical_official_source_expansion.json

대상 condition:
    개발밀도관리구역

표준 코드:
    UQQ700


배경
======================================================================
S-stage는 endpoint recall을 우선하여 broad candidate recovery를 수행했다.

그 결과 다음과 같은 false positive가 존재할 수 있다.

1. 일반 .kr / .or.kr host를 official로 오인
2. URL shortener / redirect intermediary를 official endpoint로 오인
3. 다른 기관 archive를 특정 지자체 historical archive로 오인
4. HTTP 직접 검증 없이 HTML link만으로 recovered 처리
5. source family와 실제 endpoint 역할이 불일치
6. host에 여러 지역을 결합해 region identity를 잘못 상속
7. generic navigation/content page를 archive endpoint로 오인
8. modern endpoint와 historical endpoint 역할 혼동

S-2에서는 S-stage classification을 신뢰하지 않는다.

모든 입력은 "raw endpoint candidate"로 취급하고,
직접 network requery 결과만으로 qualification을 수행한다.


핵심 원칙
======================================================================
1. S-stage recovered classification은 final qualification 근거가 아니다.

2. candidate URL을 직접 HTTP 조회해야 한다.

3. HTTP 2xx 성공이 qualification의 필요조건이다.

4. redirect 후 final URL을 별도로 검증한다.

5. URL shortener / tracking / unrelated redirect host는 차단한다.

6. .go.kr은 기본 official government host로 인정할 수 있다.

7. .or.kr / 일반 .kr은 suffix만으로 official 인정하지 않는다.

8. non-go.kr은 기존 공식 source provenance에 의해 명시적으로
   결합된 host만 허용한다.

9. candidate의 region을 기존 source seed에서 무조건 상속하지 않는다.

10. region은 endpoint URL / page title / page body / breadcrumb /
    source provenance가 결합될 때만 bound로 인정한다.

11. source family 역할과 endpoint semantic role이 일치해야 한다.

12. LEGACY_LOCAL_GAZETTE는 공보/시보/군보/구보 관련 evidence 필요.

13. LEGACY_LOCAL_NOTICE는 고시/공고/새올/공공고시 관련 evidence 필요.

14. URBAN_PLANNING_ARCHIVE는 도시계획/도시관리계획/
    지형도면 관련 evidence 필요.

15. NOTICE_NUMBER_REVERSE_LOOKUP은 고시번호/공고번호를
    실제 detail identity로 역탐색할 수 있는 구조 evidence 필요.

16. search/list endpoint 자체는 final positive가 아니다.

17. endpoint qualification과 document positive 판정은 분리한다.

18. runtime registration 금지.

19. SITE TRUE/FALSE 자동판정 금지.

20. T-stage에는 QUALIFIED endpoint만 넘긴다.


출력 classification
======================================================================

QUALIFIED_HISTORICAL_GAZETTE_ENDPOINT
    실제 지방 공보/시보/군보/구보 historical endpoint.

QUALIFIED_HISTORICAL_NOTICE_ENDPOINT
    실제 지자체 고시/공고 historical/search endpoint.

QUALIFIED_URBAN_PLANNING_ENDPOINT
    실제 도시관리계획/지형도면 historical endpoint.

QUALIFIED_NOTICE_REVERSE_LOOKUP_ENDPOINT
    고시번호 역탐색용 공식 endpoint.

REJECTED_HTTP_FAILURE
    HTTP 직접 조회 실패.

REJECTED_NON_OFFICIAL_HOST
    공식기관 host provenance를 충족하지 못함.

REJECTED_SHORTENER_OR_REDIRECTOR
    URL shortener 또는 intermediary redirect host.

REJECTED_EXTERNAL_REDIRECT
    최초 candidate와 무관한 외부 host로 redirect.

REJECTED_REGION_UNBOUND
    endpoint와 입력 region 사이의 identity 결합 실패.

REJECTED_ROLE_INCOMPATIBLE
    source family와 endpoint semantic role 불일치.

REJECTED_GENERIC_NAVIGATION
    홈/소개/일반 콘텐츠/navigation endpoint.

REJECTED_MODERN_ENDPOINT_REPEAT
    이미 현대 endpoint로 사용된 URL.

REJECTED_INVALID_URL
    URL 자체가 비정상.

REJECTED_DUPLICATE_ENDPOINT
    canonical duplicate.


안전 정책
======================================================================
- qualified endpoint 자체를 verified positive로 사용하지 않는다.
- endpoint는 T-stage query 실행 seed일 뿐이다.
- runtime registration 금지.
- SITE TRUE/FALSE 자동판정 금지.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import (
    parse_qsl,
    urlencode,
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

S_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_recovery.json"
    )
)

Q_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_source_endpoint_discovery.json"
    )
)

P_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_official_source_expansion.json"
    )
)

H_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "official_board_endpoint_refinement.json"
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
        "historical_source_family_entry_endpoint_qualification.json"
    )
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


# ============================================================
# SOURCE FAMILY
# ============================================================

SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

SOURCE_FAMILY_LEGACY_LOCAL_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

SOURCE_FAMILY_URBAN_PLANNING = (
    "URBAN_PLANNING_ARCHIVE"
)

SOURCE_FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)

QUALIFIABLE_SOURCE_FAMILIES = {
    SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE,
    SOURCE_FAMILY_LEGACY_LOCAL_NOTICE,
    SOURCE_FAMILY_URBAN_PLANNING,
    SOURCE_FAMILY_NOTICE_REVERSE,
}


# ============================================================
# CLASSIFICATION
# ============================================================

CLASS_QUALIFIED_GAZETTE = (
    "QUALIFIED_HISTORICAL_GAZETTE_ENDPOINT"
)

CLASS_QUALIFIED_NOTICE = (
    "QUALIFIED_HISTORICAL_NOTICE_ENDPOINT"
)

CLASS_QUALIFIED_URBAN = (
    "QUALIFIED_URBAN_PLANNING_ENDPOINT"
)

CLASS_QUALIFIED_NOTICE_REVERSE = (
    "QUALIFIED_NOTICE_REVERSE_LOOKUP_ENDPOINT"
)

CLASS_REJECT_HTTP = (
    "REJECTED_HTTP_FAILURE"
)

CLASS_REJECT_NON_OFFICIAL = (
    "REJECTED_NON_OFFICIAL_HOST"
)

CLASS_REJECT_SHORTENER = (
    "REJECTED_SHORTENER_OR_REDIRECTOR"
)

CLASS_REJECT_EXTERNAL_REDIRECT = (
    "REJECTED_EXTERNAL_REDIRECT"
)

CLASS_REJECT_REGION = (
    "REJECTED_REGION_UNBOUND"
)

CLASS_REJECT_ROLE = (
    "REJECTED_ROLE_INCOMPATIBLE"
)

CLASS_REJECT_GENERIC = (
    "REJECTED_GENERIC_NAVIGATION"
)

CLASS_REJECT_MODERN = (
    "REJECTED_MODERN_ENDPOINT_REPEAT"
)

CLASS_REJECT_INVALID = (
    "REJECTED_INVALID_URL"
)

CLASS_REJECT_DUPLICATE = (
    "REJECTED_DUPLICATE_ENDPOINT"
)

QUALIFIED_CLASSES = {
    CLASS_QUALIFIED_GAZETTE,
    CLASS_QUALIFIED_NOTICE,
    CLASS_QUALIFIED_URBAN,
    CLASS_QUALIFIED_NOTICE_REVERSE,
}

VALID_CLASSES = (
    QUALIFIED_CLASSES
    | {
        CLASS_REJECT_HTTP,
        CLASS_REJECT_NON_OFFICIAL,
        CLASS_REJECT_SHORTENER,
        CLASS_REJECT_EXTERNAL_REDIRECT,
        CLASS_REJECT_REGION,
        CLASS_REJECT_ROLE,
        CLASS_REJECT_GENERIC,
        CLASS_REJECT_MODERN,
        CLASS_REJECT_INVALID,
        CLASS_REJECT_DUPLICATE,
    }
)


# ============================================================
# HTTP CONFIG
# ============================================================

TIMEOUT = 18

MAX_RESPONSE_BYTES = (
    8
    * 1024
    * 1024
)

MAX_TOTAL_REQUESTS = 400

MAX_REQUESTS_PER_HOST = 40

REQUEST_DELAY_SECONDS = 0.025

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# SHORTENER / REDIRECTOR
# ============================================================

BLOCKED_REDIRECT_HOSTS = {
    "buly.kr",
    "bit.ly",
    "tinyurl.com",
    "url.kr",
    "han.gl",
    "vo.la",
    "me2.do",
    "naver.me",
    "lrl.kr",
    "t.co",
    "goo.gl",
}


# ============================================================
# EXPLICIT NON-GOVERNMENT HOST BLOCK
# ============================================================

"""
suffix가 .or.kr / .kr이라고 해서 공식 지자체 host로 인정하지 않는다.

현재 S-stage에서 실제 false positive가 확인된 대표 host는
명시적으로 차단한다.
"""

KNOWN_UNRELATED_ARCHIVE_HOSTS = {
    "archives.saemaul.or.kr",
}


# ============================================================
# GOVERNMENT HOST
# ============================================================

def is_government_host(
    host: str,
) -> bool:

    host = normalize_space(
        host
    ).lower()

    if not host:
        return False

    return (
        host.endswith(
            ".go.kr"
        )
        or host == "go.kr"
    )


# ============================================================
# SEMANTIC TERMS
# ============================================================

GAZETTE_TERMS = [
    "시보",
    "군보",
    "구보",
    "공보",
    "도보",
    "관보",
    "호외",
    "공보실",
    "공보게시",
]

NOTICE_TERMS = [
    "고시",
    "공고",
    "고시공고",
    "고시·공고",
    "고시/공고",
    "새올",
    "saeol",
    "publicnotice",
    "eminwon",
    "announce",
    "announcement",
]

URBAN_TERMS = [
    "도시계획",
    "도시관리계획",
    "도시관리",
    "도시정책",
    "도시기본계획",
    "지형도면",
    "지구단위계획",
    "용도지역",
    "용도지구",
    "용도구역",
    "urbanplanning",
    "cityplan",
    "cityplanning",
]

NOTICE_REVERSE_TERMS = [
    "고시번호",
    "공고번호",
    "고시 제",
    "공고 제",
    "notice",
    "ancmtmgtno",
    "mgt_no",
    "noticeno",
]

ARCHIVE_TERMS = [
    "과거",
    "이전",
    "옛",
    "구",
    "archive",
    "archives",
    "history",
    "historical",
    "지난",
]

SEARCH_TERMS = [
    "검색",
    "search",
    "keyword",
    "query",
    "searchwrd",
    "searchword",
]

GENERIC_PAGE_TERMS = [
    "기관소개",
    "소개",
    "오시는길",
    "연혁",
    "사이트맵",
    "개인정보",
    "회원가입",
    "로그인",
    "family site",
    "패밀리사이트",
    "기부",
    "기증",
    "인사말",
    "조직도",
]

GENERIC_PATH_TERMS = [
    "/about/",
    "/location",
    "/contact",
    "/login",
    "/logout",
    "/member",
    "/join",
    "/privacy",
    "/sitemap",
    "/family",
]


# ============================================================
# REGION
# ============================================================

REGION_PATTERN = re.compile(
    r"(서울특별시|부산광역시|대구광역시|인천광역시|"
    r"광주광역시|대전광역시|울산광역시|세종특별자치시|"
    r"경기도|강원특별자치도|강원도|충청북도|충청남도|"
    r"전북특별자치도|전라북도|전라남도|경상북도|경상남도|"
    r"제주특별자치도|"
    r"[가-힣]{2,12}시|[가-힣]{2,12}군|[가-힣]{2,12}구)"
)

REGION_ALIASES = {
    "서울특별시": ["서울", "seoul"],
    "부산광역시": ["부산", "busan"],
    "대구광역시": ["대구", "daegu"],
    "인천광역시": ["인천", "incheon"],
    "광주광역시": ["광주", "gwangju"],
    "대전광역시": ["대전", "daejeon"],
    "울산광역시": ["울산", "ulsan"],
    "세종특별자치시": ["세종", "sejong"],
    "경기도": ["경기", "gg.go.kr"],
    "충청남도": ["충남", "chungnam"],
    "충청북도": ["충북", "chungbuk"],
    "전라남도": ["전남", "jeonnam"],
    "전라북도": ["전북", "jeonbuk"],
    "전북특별자치도": ["전북", "jeonbuk"],
    "경상남도": ["경남", "gyeongnam"],
    "경상북도": ["경북", "gyeongbuk"],
}


# ============================================================
# HTML
# ============================================================

SCRIPT_STYLE_PATTERN = re.compile(
    r"<(?:script|style)\b.*?</(?:script|style)>",
    re.IGNORECASE
    | re.DOTALL,
)

TAG_PATTERN = re.compile(
    r"<[^>]+>",
    re.DOTALL,
)

TITLE_PATTERN = re.compile(
    r"<title\b[^>]*>(.*?)</title>",
    re.IGNORECASE
    | re.DOTALL,
)

META_REFRESH_PATTERN = re.compile(
    r"""<meta\b[^>]*http-equiv\s*=\s*["']?refresh["']?[^>]*>""",
    re.IGNORECASE,
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
    text: str,
    terms: Iterable[str],
) -> bool:

    lowered = normalize_space(
        text
    ).lower()

    return any(
        normalize_space(
            term
        ).lower()
        in lowered
        for term in terms
    )


def strip_html(
    raw_html: str,
) -> str:

    value = SCRIPT_STYLE_PATTERN.sub(
        " ",
        raw_html,
    )

    value = TAG_PATTERN.sub(
        " ",
        value,
    )

    value = html.unescape(
        value
    )

    return normalize_space(
        value
    )


def sha256_bytes(
    data: bytes,
) -> str:

    return hashlib.sha256(
        data
    ).hexdigest()


def walk_dicts(
    value: Any,
) -> Iterable[Dict[str, Any]]:

    if isinstance(
        value,
        dict,
    ):

        yield value

        for child in value.values():

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    child
                )

    elif isinstance(
        value,
        list,
    ):

        for child in value:

            if isinstance(
                child,
                (
                    dict,
                    list,
                ),
            ):

                yield from walk_dicts(
                    child
                )


# ============================================================
# URL
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "csrf",
    "_csrf",
    "session",
    "sessionid",
    "jsessionid",
    "timestamp",
    "_",
}


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

        return ""

    if (
        parsed.scheme.lower()
        not in {
            "http",
            "https",
        }
    ):
        return ""

    host = (
        parsed.hostname
        or ""
    ).lower()

    if not host:
        return ""

    scheme = parsed.scheme.lower()

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

    path = re.sub(
        r";jsessionid=[^/?]+",
        "",
        path,
        flags=re.IGNORECASE,
    )

    path = re.sub(
        r"/{2,}",
        "/",
        path,
    )

    query_items = []
    seen_pairs: Set[
        Tuple[str, str]
    ] = set()

    for key, value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_space(
            key
        )

        if not key:
            continue

        if key.lower() in VOLATILE_QUERY_KEYS:
            continue

        pair = (
            key,
            value,
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

    return urlunparse(
        (
            scheme,
            netloc,
            path,
            "",
            urlencode(
                query_items,
                doseq=True,
            ),
            "",
        )
    )


def hostname(
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


def registrable_like_host(
    host: str,
) -> str:

    """
    full PSL 구현이 목적은 아니다.

    redirect가 동일 정부기관 하위 host인지 판단하는
    보수적 helper다.
    """

    parts = [
        part
        for part in host.lower().split(".")
        if part
    ]

    if len(parts) <= 3:
        return ".".join(
            parts
        )

    if host.endswith(
        ".go.kr"
    ):

        return ".".join(
            parts[
                -3:
            ]
        )

    return ".".join(
        parts[
            -2:
        ]
    )


def related_hosts(
    first: str,
    second: str,
) -> bool:

    first = normalize_space(
        first
    ).lower()

    second = normalize_space(
        second
    ).lower()

    if (
        not first
        or not second
    ):
        return False

    if first == second:
        return True

    if first.endswith(
        "." + second
    ):
        return True

    if second.endswith(
        "." + first
    ):
        return True

    if (
        is_government_host(
            first
        )
        and is_government_host(
            second
        )
        and registrable_like_host(
            first
        )
        == registrable_like_host(
            second
        )
    ):
        return True

    return False


# ============================================================
# SOURCE CANDIDATE LOAD
# ============================================================

def infer_source_family(
    item: Dict[str, Any],
) -> str:

    candidates = [
        item.get(
            "source_family"
        ),
        item.get(
            "family"
        ),
        item.get(
            "classification"
        ),
        item.get(
            "role"
        ),
        item.get(
            "name"
        ),
    ]

    combined = " ".join(
        normalize_space(
            value
        )
        for value in candidates
        if value
    ).upper()

    for family in QUALIFIABLE_SOURCE_FAMILIES:

        if family in combined:
            return family

    return ""


def extract_candidate_url(
    item: Dict[str, Any],
) -> str:

    for key in [
        "url",
        "endpoint_url",
        "canonical_url",
        "source_url",
    ]:

        value = canonicalize_url(
            item.get(
                key
            )
            or ""
        )

        if value:
            return value

    return ""


def looks_endpoint_candidate(
    item: Dict[str, Any],
) -> bool:

    family = infer_source_family(
        item
    )

    if family not in QUALIFIABLE_SOURCE_FAMILIES:
        return False

    url = extract_candidate_url(
        item
    )

    if not url:
        return False

    classification = normalize_space(
        item.get(
            "classification"
        )
    ).upper()

    role = normalize_space(
        item.get(
            "role"
        )
    ).upper()

    if (
        "ENDPOINT"
        in classification
        or "RECOVER"
        in classification
        or role
        in {
            "ARCHIVE",
            "GAZETTE",
            "NOTICE",
            "URBAN_PLANNING",
            "NOTICE_REVERSE",
        }
        or item.get(
            "recovered"
        )
        is True
    ):

        return True

    return False


def extract_regions(
    item: Dict[str, Any],
) -> List[str]:

    raw_values: List[Any] = []

    for key in [
        "region",
        "regions",
        "source_region",
        "jurisdiction",
    ]:

        value = item.get(
            key
        )

        if isinstance(
            value,
            list,
        ):

            raw_values.extend(
                value
            )

        elif value:

            raw_values.append(
                value
            )

    result: List[str] = []

    for value in raw_values:

        text = normalize_space(
            value
        )

        if not text:
            continue

        # "A / B" 형태를 강제 하나의 region으로 사용하지 않는다.
        parts = re.split(
            r"\s*/\s*|\s*\|\s*|,\s*",
            text,
        )

        for part in parts:

            part = normalize_space(
                part
            )

            if part:

                result.append(
                    part
                )

    return unique_strings(
        result
    )


def load_s_stage_candidates(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str, Tuple[str, ...]]
    ] = set()

    for item in walk_dicts(
        data
    ):

        if not looks_endpoint_candidate(
            item
        ):

            continue

        family = infer_source_family(
            item
        )

        url = extract_candidate_url(
            item
        )

        regions = extract_regions(
            item
        )

        key = (
            family,
            url,
            tuple(
                sorted(
                    regions
                )
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            {
                "source_family": family,

                "url": url,

                "input_regions": regions,

                "input_role": normalize_space(
                    item.get(
                        "role"
                    )
                ),

                "input_classification": normalize_space(
                    item.get(
                        "classification"
                    )
                ),

                "input_score": int(
                    item.get(
                        "score"
                    )
                    or 0
                ),

                "input_http_status": item.get(
                    "http_status"
                ),

                "raw_source_record": {
                    "region": item.get(
                        "region"
                    ),
                    "role": item.get(
                        "role"
                    ),
                    "classification": item.get(
                        "classification"
                    ),
                },
            }
        )

    result.sort(
        key=lambda item: (
            item.get(
                "source_family"
            ),
            item.get(
                "url"
            ),
        )
    )

    return result


# ============================================================
# MODERN ENDPOINT EXCLUSION
# ============================================================

def load_modern_endpoint_urls(
    data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    for item in walk_dicts(
        data
    ):

        for key in [
            "url",
            "endpoint_url",
            "canonical_url",
            "source_url",
        ]:

            url = canonicalize_url(
                item.get(
                    key
                )
                or ""
            )

            if url:

                result.add(
                    url
                )

    return result


# ============================================================
# TRUSTED NON-GO.KR HOST MEMORY
# ============================================================

def load_trusted_non_government_hosts(
    *datasets: Dict[str, Any],
) -> Set[str]:

    """
    non-go.kr은 자동 official 처리하지 않는다.

    단 이전 단계의 명시적인 official source 기록에
    provenance가 존재하는 host만 제한적으로 기억한다.

    S-stage candidate 자체는 신뢰 source로 사용하지 않는다.
    """

    result: Set[str] = set()

    for data in datasets:

        for item in walk_dicts(
            data
        ):

            official_flag = (
                item.get(
                    "official"
                )
                is True
                or item.get(
                    "official_source"
                )
                is True
                or item.get(
                    "is_official"
                )
                is True
            )

            classification = normalize_space(
                item.get(
                    "classification"
                )
            ).upper()

            source_class = normalize_space(
                item.get(
                    "source_class"
                )
            ).upper()

            explicit_official = (
                official_flag
                or "OFFICIAL"
                in classification
                or "OFFICIAL"
                in source_class
            )

            if not explicit_official:
                continue

            for key in [
                "url",
                "source_url",
                "endpoint_url",
                "canonical_url",
            ]:

                url = canonicalize_url(
                    item.get(
                        key
                    )
                    or ""
                )

                host = hostname(
                    url
                )

                if (
                    host
                    and not is_government_host(
                        host
                    )
                    and host not in KNOWN_UNRELATED_ARCHIVE_HOSTS
                    and host not in BLOCKED_REDIRECT_HOSTS
                ):

                    result.add(
                        host
                    )

    return result


# ============================================================
# HTTP
# ============================================================

def extract_charset(
    content_type: str,
) -> str:

    match = re.search(
        r"charset\s*=\s*[\"']?([^;\"'\s]+)",
        normalize_space(
            content_type
        ),
        flags=re.IGNORECASE,
    )

    if not match:
        return ""

    return normalize_space(
        match.group(1)
    )


def decode_bytes(
    data: bytes,
    *,
    content_type: str = "",
    response_encoding: str = "",
) -> Tuple[str, str]:

    candidates = unique_strings(
        [
            extract_charset(
                content_type
            ),
            response_encoding,
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    for encoding in candidates:

        try:

            return (
                data.decode(
                    encoding
                ),
                encoding,
            )

        except (
            UnicodeDecodeError,
            LookupError,
        ):

            continue

    return (
        data.decode(
            "utf-8",
            errors="replace",
        ),
        "utf-8-replace",
    )


def fetch_endpoint(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "requested_url": canonicalize_url(
            url
        ),
        "final_url": "",
        "redirected": False,
        "redirect_count": 0,
        "redirect_chain": [],
        "http_status": None,
        "content_type": "",
        "response_bytes": 0,
        "response_sha256": "",
        "raw_html": "",
        "text": "",
        "title": "",
        "encoding": "",
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
                "redirected"
            ] = bool(
                response.history
            )

            result[
                "redirect_count"
            ] = len(
                response.history
            )

            result[
                "redirect_chain"
            ] = [
                {
                    "status": history.status_code,
                    "url": canonicalize_url(
                        str(
                            history.url
                        )
                    ),
                }
                for history in response.history
            ]

            result[
                "content_type"
            ] = normalize_space(
                response.headers.get(
                    "Content-Type"
                )
            )

            # HTTP status를 먼저 기록하되 non-2xx는 error로 반환.
            response.raise_for_status()

            chunks: List[bytes] = []
            total = 0

            for chunk in response.iter_content(
                chunk_size=256 * 1024,
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

            result[
                "response_sha256"
            ] = sha256_bytes(
                data
            )

            content_type = normalize_space(
                result[
                    "content_type"
                ]
            ).lower()

            prefix = (
                data[
                    :1000
                ]
                .lstrip()
                .lower()
            )

            html_like = (
                "html"
                in content_type
                or "text/"
                in content_type
                or prefix.startswith(
                    b"<!doctype html"
                )
                or prefix.startswith(
                    b"<html"
                )
            )

            if html_like:

                decoded, encoding = decode_bytes(
                    data,
                    content_type=result[
                        "content_type"
                    ],
                    response_encoding=(
                        response.encoding
                        or ""
                    ),
                )

                result[
                    "raw_html"
                ] = decoded

                result[
                    "text"
                ] = strip_html(
                    decoded
                )

                result[
                    "encoding"
                ] = encoding

                title_match = TITLE_PATTERN.search(
                    decoded
                )

                if title_match:

                    result[
                        "title"
                    ] = strip_html(
                        title_match.group(1)
                    )

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

    return result


# ============================================================
# HOST QUALIFICATION
# ============================================================

def is_shortener_host(
    host: str,
) -> bool:

    return (
        normalize_space(
            host
        ).lower()
        in BLOCKED_REDIRECT_HOSTS
    )


def host_is_qualified_official(
    host: str,
    trusted_non_government_hosts: Set[str],
) -> Tuple[
    bool,
    str,
]:

    host = normalize_space(
        host
    ).lower()

    if not host:

        return (
            False,
            "EMPTY_HOST",
        )

    if host in BLOCKED_REDIRECT_HOSTS:

        return (
            False,
            "BLOCKED_REDIRECT_HOST",
        )

    if host in KNOWN_UNRELATED_ARCHIVE_HOSTS:

        return (
            False,
            "KNOWN_UNRELATED_ARCHIVE_HOST",
        )

    if is_government_host(
        host
    ):

        return (
            True,
            "GO_KR_GOVERNMENT_HOST",
        )

    if host in trusted_non_government_hosts:

        return (
            True,
            "EXPLICIT_TRUSTED_OFFICIAL_PROVENANCE",
        )

    return (
        False,
        "NON_GOVERNMENT_HOST_WITHOUT_PROVENANCE",
    )


# ============================================================
# REGION BINDING
# ============================================================

def region_terms(
    region: str,
) -> List[str]:

    region = normalize_space(
        region
    )

    if not region:
        return []

    values = [
        region
    ]

    match = REGION_PATTERN.search(
        region
    )

    if match:

        region_name = normalize_space(
            match.group(0)
        )

        values.append(
            region_name
        )

        values.extend(
            REGION_ALIASES.get(
                region_name,
                []
            )
        )

        # 시/군/구 suffix 제외 alias도 보조 사용
        stripped = re.sub(
            r"(특별자치도|특별자치시|특별시|광역시|시|군|구|도)$",
            "",
            region_name,
        )

        if len(
            stripped
        ) >= 2:

            values.append(
                stripped
            )

    return unique_strings(
        values
    )


def evaluate_region_binding(
    input_regions: List[str],
    *,
    url: str,
    final_url: str,
    title: str,
    text: str,
) -> Dict[str, Any]:

    if not input_regions:

        return {
            "required": False,
            "bound": True,
            "matched_regions": [],
            "evidence": [
                "NO_INPUT_REGION_REQUIREMENT"
            ],
        }

    evidence_text = normalize_space(
        " ".join(
            [
                url,
                final_url,
                title,
                text[
                    :12000
                ],
            ]
        )
    ).lower()

    matched_regions: List[str] = []
    evidence: List[str] = []

    for region in input_regions:

        terms = region_terms(
            region
        )

        matched_terms = [
            term
            for term in terms
            if normalize_space(
                term
            ).lower()
            in evidence_text
        ]

        if matched_terms:

            matched_regions.append(
                region
            )

            evidence.append(
                "REGION_MATCH:"
                + region
                + ":"
                + ",".join(
                    matched_terms[
                        :5
                    ]
                )
            )

    # 여러 지역이 입력되어 있어도 그중 하나가 endpoint와
    # 실제 결합되면 해당 record는 그 matched region으로 좁힌다.
    return {
        "required": True,
        "bound": bool(
            matched_regions
        ),
        "matched_regions": unique_strings(
            matched_regions
        ),
        "evidence": evidence,
    }


# ============================================================
# GENERIC PAGE
# ============================================================

def detect_generic_page(
    url: str,
    title: str,
    text: str,
) -> Tuple[
    bool,
    List[str],
]:

    evidence: List[str] = []

    if contains_any(
        url.lower(),
        GENERIC_PATH_TERMS,
    ):

        evidence.append(
            "GENERIC_PATH"
        )

    semantic_text = normalize_space(
        f"{title} {text[:8000]}"
    )

    found_generic = [
        term
        for term in GENERIC_PAGE_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    # generic term 하나만으로 탈락시키지는 않는다.
    # role-specific semantic evidence가 전혀 없는 경우에 사용.
    if found_generic:

        evidence.extend(
            f"GENERIC_TERM:{term}"
            for term in found_generic[
                :10
            ]
        )

    return (
        bool(
            evidence
        ),
        evidence,
    )


# ============================================================
# ROLE QUALIFICATION
# ============================================================

def evaluate_role(
    source_family: str,
    *,
    url: str,
    title: str,
    text: str,
) -> Dict[str, Any]:

    semantic_text = normalize_space(
        f"{url} {title} {text[:15000]}"
    )

    gazette_hits = [
        term
        for term in GAZETTE_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    notice_hits = [
        term
        for term in NOTICE_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    urban_hits = [
        term
        for term in URBAN_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    notice_reverse_hits = [
        term
        for term in NOTICE_REVERSE_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    archive_hits = [
        term
        for term in ARCHIVE_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    search_hits = [
        term
        for term in SEARCH_TERMS
        if term.lower()
        in semantic_text.lower()
    ]

    compatible = False
    qualification_class = ""
    evidence: List[str] = []

    if (
        source_family
        == SOURCE_FAMILY_LEGACY_LOCAL_GAZETTE
    ):

        compatible = bool(
            gazette_hits
        )

        qualification_class = (
            CLASS_QUALIFIED_GAZETTE
        )

        evidence.extend(
            "GAZETTE:" + term
            for term in gazette_hits
        )

        if archive_hits:

            evidence.extend(
                "ARCHIVE:" + term
                for term in archive_hits
            )

    elif (
        source_family
        == SOURCE_FAMILY_LEGACY_LOCAL_NOTICE
    ):

        compatible = bool(
            notice_hits
        )

        qualification_class = (
            CLASS_QUALIFIED_NOTICE
        )

        evidence.extend(
            "NOTICE:" + term
            for term in notice_hits
        )

        if search_hits:

            evidence.extend(
                "SEARCH:" + term
                for term in search_hits
            )

    elif (
        source_family
        == SOURCE_FAMILY_URBAN_PLANNING
    ):

        compatible = bool(
            urban_hits
        )

        qualification_class = (
            CLASS_QUALIFIED_URBAN
        )

        evidence.extend(
            "URBAN:" + term
            for term in urban_hits
        )

    elif (
        source_family
        == SOURCE_FAMILY_NOTICE_REVERSE
    ):

        compatible = (
            bool(
                notice_reverse_hits
            )
            and (
                bool(
                    search_hits
                )
                or bool(
                    notice_hits
                )
            )
        )

        qualification_class = (
            CLASS_QUALIFIED_NOTICE_REVERSE
        )

        evidence.extend(
            "NOTICE_REVERSE:" + term
            for term in notice_reverse_hits
        )

        evidence.extend(
            "SEARCH:" + term
            for term in search_hits
        )

    return {
        "compatible": compatible,

        "qualification_class": (
            qualification_class
        ),

        "gazette_hits": unique_strings(
            gazette_hits
        ),

        "notice_hits": unique_strings(
            notice_hits
        ),

        "urban_hits": unique_strings(
            urban_hits
        ),

        "notice_reverse_hits": unique_strings(
            notice_reverse_hits
        ),

        "archive_hits": unique_strings(
            archive_hits
        ),

        "search_hits": unique_strings(
            search_hits
        ),

        "evidence": unique_strings(
            evidence
        ),
    }


# ============================================================
# QUALIFY ONE CANDIDATE
# ============================================================

def qualify_candidate(
    *,
    candidate: Dict[str, Any],
    response: Dict[str, Any],
    trusted_non_government_hosts: Set[str],
    modern_endpoint_urls: Set[str],
) -> Dict[str, Any]:

    source_family = normalize_space(
        candidate.get(
            "source_family"
        )
    )

    input_url = canonicalize_url(
        candidate.get(
            "url"
        )
        or ""
    )

    input_host = hostname(
        input_url
    )

    final_url = canonicalize_url(
        response.get(
            "final_url"
        )
        or ""
    )

    final_host = hostname(
        final_url
    )

    reasons: List[str] = []

    classification = ""

    # --------------------------------------------------------
    # URL validation
    # --------------------------------------------------------

    if (
        not input_url
        or not input_host
    ):

        classification = (
            CLASS_REJECT_INVALID
        )

        reasons.append(
            "INVALID_INPUT_URL"
        )

    # --------------------------------------------------------
    # Shortener
    # --------------------------------------------------------

    elif is_shortener_host(
        input_host
    ):

        classification = (
            CLASS_REJECT_SHORTENER
        )

        reasons.append(
            "INPUT_SHORTENER_HOST"
        )

    # --------------------------------------------------------
    # HTTP
    # --------------------------------------------------------

    elif (
        response.get(
            "error"
        )
        or not isinstance(
            response.get(
                "http_status"
            ),
            int,
        )
        or not (
            200
            <= int(
                response.get(
                    "http_status"
                )
            )
            < 300
        )
    ):

        classification = (
            CLASS_REJECT_HTTP
        )

        reasons.append(
            "DIRECT_HTTP_2XX_REQUIRED"
        )

    elif (
        not final_url
        or not final_host
    ):

        classification = (
            CLASS_REJECT_HTTP
        )

        reasons.append(
            "FINAL_URL_MISSING"
        )

    elif is_shortener_host(
        final_host
    ):

        classification = (
            CLASS_REJECT_SHORTENER
        )

        reasons.append(
            "FINAL_SHORTENER_HOST"
        )

    else:

        # ----------------------------------------------------
        # Official host
        # ----------------------------------------------------

        (
            input_official,
            input_official_reason,
        ) = host_is_qualified_official(
            input_host,
            trusted_non_government_hosts,
        )

        (
            final_official,
            final_official_reason,
        ) = host_is_qualified_official(
            final_host,
            trusted_non_government_hosts,
        )

        reasons.append(
            "INPUT_HOST:"
            + input_official_reason
        )

        reasons.append(
            "FINAL_HOST:"
            + final_official_reason
        )

        if not input_official:

            classification = (
                CLASS_REJECT_NON_OFFICIAL
            )

        elif not final_official:

            classification = (
                CLASS_REJECT_NON_OFFICIAL
            )

        # ----------------------------------------------------
        # External redirect
        # ----------------------------------------------------

        elif (
            response.get(
                "redirected"
            )
            is True
            and not related_hosts(
                input_host,
                final_host,
            )
        ):

            classification = (
                CLASS_REJECT_EXTERNAL_REDIRECT
            )

            reasons.append(
                "UNRELATED_FINAL_REDIRECT_HOST"
            )

        # ----------------------------------------------------
        # Modern endpoint repeat
        # ----------------------------------------------------

        elif (
            input_url
            in modern_endpoint_urls
            or final_url
            in modern_endpoint_urls
        ):

            classification = (
                CLASS_REJECT_MODERN
            )

            reasons.append(
                "MODERN_ENDPOINT_MEMORY_MATCH"
            )

        else:

            title = normalize_space(
                response.get(
                    "title"
                )
            )

            text = normalize_space(
                response.get(
                    "text"
                )
            )

            # ------------------------------------------------
            # Role
            # ------------------------------------------------

            role_result = evaluate_role(
                source_family,
                url=final_url,
                title=title,
                text=text,
            )

            # ------------------------------------------------
            # Region
            # ------------------------------------------------

            region_result = (
                evaluate_region_binding(
                    candidate.get(
                        "input_regions"
                    )
                    or [],
                    url=input_url,
                    final_url=final_url,
                    title=title,
                    text=text,
                )
            )

            # ------------------------------------------------
            # Generic
            # ------------------------------------------------

            (
                generic_page,
                generic_evidence,
            ) = detect_generic_page(
                final_url,
                title,
                text,
            )

            strong_role_evidence = (
                len(
                    role_result.get(
                        "evidence"
                    )
                    or []
                )
                >= 1
            )

            if (
                generic_page
                and not strong_role_evidence
            ):

                classification = (
                    CLASS_REJECT_GENERIC
                )

                reasons.extend(
                    generic_evidence
                )

            elif not role_result.get(
                "compatible"
            ):

                classification = (
                    CLASS_REJECT_ROLE
                )

                reasons.append(
                    "SOURCE_FAMILY_ROLE_EVIDENCE_MISSING"
                )

            elif not region_result.get(
                "bound"
            ):

                classification = (
                    CLASS_REJECT_REGION
                )

                reasons.append(
                    "INPUT_REGION_NOT_BOUND_TO_ENDPOINT"
                )

            else:

                classification = normalize_space(
                    role_result.get(
                        "qualification_class"
                    )
                )

                reasons.extend(
                    role_result.get(
                        "evidence"
                    )
                    or []
                )

                reasons.extend(
                    region_result.get(
                        "evidence"
                    )
                    or []
                )

    qualified = (
        classification
        in QUALIFIED_CLASSES
    )

    return {
        "source_family": source_family,

        "input_url": input_url,

        "input_host": input_host,

        "input_regions": (
            candidate.get(
                "input_regions"
            )
            or []
        ),

        "input_role": candidate.get(
            "input_role"
        ),

        "input_classification": (
            candidate.get(
                "input_classification"
            )
        ),

        "input_score": candidate.get(
            "input_score"
        ),

        "input_http_status": candidate.get(
            "input_http_status"
        ),

        "final_url": final_url,

        "final_host": final_host,

        "http_status": response.get(
            "http_status"
        ),

        "redirected": response.get(
            "redirected"
        ),

        "redirect_count": response.get(
            "redirect_count"
        ),

        "redirect_chain": response.get(
            "redirect_chain"
        )
        or [],

        "content_type": response.get(
            "content_type"
        ),

        "response_bytes": response.get(
            "response_bytes"
        ),

        "response_sha256": response.get(
            "response_sha256"
        ),

        "title": response.get(
            "title"
        ),

        "text_preview": normalize_space(
            response.get(
                "text"
            )
        )[
            :1800
        ],

        "network_error": response.get(
            "error"
        ),

        "classification": classification,

        "qualified": qualified,

        "qualification_reasons": (
            unique_strings(
                reasons
            )
        ),

        "verified_positive": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        "final_positive_promotion_allowed": False,
    }


# ============================================================
# MAIN
# ============================================================

def main() -> None:

    print(
        "=" * 60
    )

    print(
        "DEVELOPMENT DENSITY MANAGEMENT AREA"
    )

    print(
        "HISTORICAL SOURCE FAMILY ENTRY ENDPOINT QUALIFICATION"
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

    print()

    print(
        "S-stage input:",
        S_STAGE_INPUT_PATH,
    )

    print(
        "Q-stage input:",
        Q_STAGE_INPUT_PATH,
    )

    print(
        "P-stage input:",
        P_STAGE_INPUT_PATH,
    )

    print(
        "H-stage input:",
        H_STAGE_INPUT_PATH,
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not S_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "S-stage input not found: "
            f"{S_STAGE_INPUT_PATH}"
        )

    s_data = json.loads(
        S_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        s_data,
        dict,
    ):

        raise TypeError(
            "S-stage input must be JSON object."
        )

    q_data: Dict[str, Any] = {}

    if Q_STAGE_INPUT_PATH.exists():

        q_data = json.loads(
            Q_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    p_data: Dict[str, Any] = {}

    if P_STAGE_INPUT_PATH.exists():

        p_data = json.loads(
            P_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    h_data: Dict[str, Any] = {}

    if H_STAGE_INPUT_PATH.exists():

        h_data = json.loads(
            H_STAGE_INPUT_PATH.read_text(
                encoding="utf-8"
            )
        )

    candidates = load_s_stage_candidates(
        s_data
    )

    modern_endpoint_urls = (
        load_modern_endpoint_urls(
            h_data
        )
        if h_data
        else set()
    )

    trusted_non_government_hosts = (
        load_trusted_non_government_hosts(
            q_data,
            p_data,
        )
    )

    print(
        "Raw S-stage candidate count:",
        len(
            candidates
        ),
    )

    print(
        "Modern endpoint exclusion count:",
        len(
            modern_endpoint_urls
        ),
    )

    print(
        "Trusted non-go.kr host count:",
        len(
            trusted_non_government_hosts
        ),
    )

    print()

    # ========================================================
    # SESSION
    # ========================================================

    session = requests.Session()

    session.headers.update(
        {
            "User-Agent": USER_AGENT,

            "Accept": (
                "text/html,"
                "application/xhtml+xml,"
                "application/xml;q=0.9,"
                "*/*;q=0.8"
            ),

            "Accept-Language": (
                "ko-KR,ko;q=0.9,"
                "en-US;q=0.7,"
                "en;q=0.5"
            ),
        }
    )

    # ========================================================
    # COUNTERS
    # ========================================================

    total_request_count = 0

    http_success_count = 0

    transport_error_count = 0

    host_request_counts: Counter = (
        Counter()
    )

    response_hash_counts: Counter = (
        Counter()
    )

    # ========================================================
    # RESULTS
    # ========================================================

    qualification_records: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # CANDIDATE LOOP
    # ========================================================

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):

        input_url = canonicalize_url(
            candidate.get(
                "url"
            )
            or ""
        )

        input_host = hostname(
            input_url
        )

        print(
            "-" * 60
        )

        print(
            f"CANDIDATE {index}"
        )

        print(
            "Family:",
            candidate.get(
                "source_family"
            ),
        )

        print(
            "Region:",
            " / ".join(
                candidate.get(
                    "input_regions"
                )
                or []
            )
            or "-",
        )

        print(
            "URL:",
            input_url,
        )

        # ----------------------------------------------------
        # Invalid URL
        # ----------------------------------------------------

        if (
            not input_url
            or not input_host
        ):

            record = {
                "source_family": (
                    candidate.get(
                        "source_family"
                    )
                ),

                "input_url": input_url,

                "input_regions": (
                    candidate.get(
                        "input_regions"
                    )
                    or []
                ),

                "classification": (
                    CLASS_REJECT_INVALID
                ),

                "qualified": False,

                "qualification_reasons": [
                    "INVALID_INPUT_URL"
                ],

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }

            qualification_records.append(
                record
            )

            print(
                "Resolution:",
                CLASS_REJECT_INVALID,
            )

            continue

        # ----------------------------------------------------
        # Shortener pre-block
        # ----------------------------------------------------

        if is_shortener_host(
            input_host
        ):

            record = {
                "source_family": (
                    candidate.get(
                        "source_family"
                    )
                ),

                "input_url": input_url,

                "input_host": input_host,

                "input_regions": (
                    candidate.get(
                        "input_regions"
                    )
                    or []
                ),

                "classification": (
                    CLASS_REJECT_SHORTENER
                ),

                "qualified": False,

                "qualification_reasons": [
                    "INPUT_SHORTENER_HOST"
                ],

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }

            qualification_records.append(
                record
            )

            print(
                "Resolution:",
                CLASS_REJECT_SHORTENER,
            )

            continue

        # ----------------------------------------------------
        # Known unrelated host pre-block
        # ----------------------------------------------------

        if (
            input_host
            in KNOWN_UNRELATED_ARCHIVE_HOSTS
        ):

            record = {
                "source_family": (
                    candidate.get(
                        "source_family"
                    )
                ),

                "input_url": input_url,

                "input_host": input_host,

                "input_regions": (
                    candidate.get(
                        "input_regions"
                    )
                    or []
                ),

                "classification": (
                    CLASS_REJECT_NON_OFFICIAL
                ),

                "qualified": False,

                "qualification_reasons": [
                    "KNOWN_UNRELATED_ARCHIVE_HOST"
                ],

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }

            qualification_records.append(
                record
            )

            print(
                "Resolution:",
                CLASS_REJECT_NON_OFFICIAL,
            )

            continue

        # ----------------------------------------------------
        # Global request budget
        # ----------------------------------------------------

        if (
            total_request_count
            >= MAX_TOTAL_REQUESTS
        ):

            record = {
                "source_family": (
                    candidate.get(
                        "source_family"
                    )
                ),

                "input_url": input_url,

                "input_host": input_host,

                "input_regions": (
                    candidate.get(
                        "input_regions"
                    )
                    or []
                ),

                "classification": (
                    CLASS_REJECT_HTTP
                ),

                "qualified": False,

                "qualification_reasons": [
                    "GLOBAL_REQUEST_BUDGET_EXHAUSTED"
                ],

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }

            qualification_records.append(
                record
            )

            continue

        # ----------------------------------------------------
        # Host request budget
        # ----------------------------------------------------

        if (
            host_request_counts[
                input_host
            ]
            >= MAX_REQUESTS_PER_HOST
        ):

            record = {
                "source_family": (
                    candidate.get(
                        "source_family"
                    )
                ),

                "input_url": input_url,

                "input_host": input_host,

                "input_regions": (
                    candidate.get(
                        "input_regions"
                    )
                    or []
                ),

                "classification": (
                    CLASS_REJECT_HTTP
                ),

                "qualified": False,

                "qualification_reasons": [
                    "HOST_REQUEST_BUDGET_EXHAUSTED"
                ],

                "verified_positive": False,

                "runtime_registration_allowed": False,

                "site_positive_allowed": False,

                "final_positive_promotion_allowed": False,
            }

            qualification_records.append(
                record
            )

            continue

        total_request_count += 1

        host_request_counts[
            input_host
        ] += 1

        response = fetch_endpoint(
            session,
            input_url,
        )

        if (
            isinstance(
                response.get(
                    "http_status"
                ),
                int,
            )
            and 200
            <= response[
                "http_status"
            ]
            < 300
        ):

            http_success_count += 1

        if response.get(
            "error"
        ):

            transport_error_count += 1

        response_hash = normalize_space(
            response.get(
                "response_sha256"
            )
        )

        if response_hash:

            response_hash_counts[
                response_hash
            ] += 1

        record = qualify_candidate(
            candidate=candidate,
            response=response,
            trusted_non_government_hosts=(
                trusted_non_government_hosts
            ),
            modern_endpoint_urls=(
                modern_endpoint_urls
            ),
        )

        qualification_records.append(
            record
        )

        print(
            "HTTP:",
            record.get(
                "http_status"
            ),
        )

        print(
            "Final URL:",
            record.get(
                "final_url"
            ),
        )

        print(
            "Qualified:",
            record.get(
                "qualified"
            ),
        )

        print(
            "Resolution:",
            record.get(
                "classification"
            ),
        )

        if REQUEST_DELAY_SECONDS > 0:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    grouped: Dict[
        Tuple[str, str],
        List[Dict[str, Any]],
    ] = defaultdict(
        list
    )

    for record in qualification_records:

        canonical_endpoint = canonicalize_url(
            record.get(
                "final_url"
            )
            or record.get(
                "input_url"
            )
            or ""
        )

        key = (
            normalize_space(
                record.get(
                    "source_family"
                )
            ),
            canonical_endpoint,
        )

        grouped[
            key
        ].append(
            record
        )

    canonical_records: List[
        Dict[str, Any]
    ] = []

    duplicate_endpoint_count = 0

    for (
        _key,
        group
    ) in grouped.items():

        if len(
            group
        ) > 1:

            duplicate_endpoint_count += (
                len(
                    group
                )
                - 1
            )

        # qualified record 우선
        ordered = sorted(
            group,
            key=lambda item: (
                -int(
                    item.get(
                        "qualified"
                    )
                    is True
                ),
                -int(
                    item.get(
                        "http_status"
                    )
                    or 0
                ),
                normalize_space(
                    item.get(
                        "classification"
                    )
                ),
            ),
        )

        representative = dict(
            ordered[
                0
            ]
        )

        representative[
            "duplicate_variant_count"
        ] = len(
            group
        )

        representative[
            "all_input_regions"
        ] = unique_strings(
            region
            for item in group
            for region in (
                item.get(
                    "input_regions"
                )
                or []
            )
        )

        canonical_records.append(
            representative
        )

    canonical_records.sort(
        key=lambda item: (
            -int(
                item.get(
                    "qualified"
                )
                is True
            ),
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            normalize_space(
                item.get(
                    "final_url"
                )
                or item.get(
                    "input_url"
                )
            ),
        )
    )

    # ========================================================
    # QUALIFIED
    # ========================================================

    qualified_endpoints = [
        item
        for item in canonical_records
        if item.get(
            "qualified"
        )
        is True
    ]

    rejected_endpoints = [
        item
        for item in canonical_records
        if item.get(
            "qualified"
        )
        is not True
    ]

    classification_counts = Counter(
        item.get(
            "classification"
        )
        for item in canonical_records
    )

    family_qualified_counts = Counter(
        item.get(
            "source_family"
        )
        for item in qualified_endpoints
    )

    # ========================================================
    # T-STAGE POOL
    # ========================================================

    next_stage_endpoint_pool = [
        {
            "source_family": item.get(
                "source_family"
            ),

            "endpoint_url": (
                item.get(
                    "final_url"
                )
                or item.get(
                    "input_url"
                )
            ),

            "regions": (
                item.get(
                    "all_input_regions"
                )
                or item.get(
                    "input_regions"
                )
                or []
            ),

            "qualification_class": (
                item.get(
                    "classification"
                )
            ),

            "http_status": item.get(
                "http_status"
            ),

            "title": item.get(
                "title"
            ),

            "qualification_reasons": (
                item.get(
                    "qualification_reasons"
                )
                or []
            ),

            "verified_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "final_positive_promotion_allowed": False,
        }
        for item in qualified_endpoints
    ]

    # ========================================================
    # RESOLUTION
    # ========================================================

    if next_stage_endpoint_pool:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_"
            "QUALIFICATION_COMPLETED"
        )

        next_action = (
            "qualified historical endpoint만 대상으로 "
            "P-stage query matrix를 source-family 및 region별로 "
            "제한 실행한다. T-stage에서도 endpoint 자체를 "
            "positive로 승격하지 않고 발견된 detail/attachment/"
            "gazette identity만 후속 document verification으로 넘긴다."
        )

    else:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_"
            "QUALIFICATION_COMPLETED_NO_ENDPOINT"
        )

        next_action = (
            "S-stage broad candidate 중 직접 HTTP, official host, "
            "region binding, source-family role qualification을 "
            "모두 충족한 endpoint가 없다. "
            "기관별 archive/search form action 또는 공개 검색 API를 "
            "개별 복원한다."
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-S-2 "
            "Development Density Management Area "
            "Historical Source Family Entry Endpoint Qualification"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "s_stage_path": str(
                S_STAGE_INPUT_PATH
            ),
            "q_stage_path": str(
                Q_STAGE_INPUT_PATH
            ),
            "p_stage_path": str(
                P_STAGE_INPUT_PATH
            ),
            "h_stage_path": str(
                H_STAGE_INPUT_PATH
            ),
            "s_stage_resolution": (
                s_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "s_stage_recovered_classification_trusted": False,

            "direct_network_requery_required": True,

            "http_2xx_required": True,

            "final_redirect_host_validation_enabled": True,

            "url_shortener_guard_enabled": True,

            "go_kr_default_official_enabled": True,

            "generic_kr_suffix_official_disabled": True,

            "generic_or_kr_suffix_official_disabled": True,

            "explicit_non_government_provenance_required": True,

            "known_unrelated_archive_guard_enabled": True,

            "region_binding_required_when_region_present": True,

            "source_family_role_qualification_enabled": True,

            "modern_endpoint_repeat_guard_enabled": True,

            "endpoint_document_role_separation_enabled": True,

            "verified_positive_promotion_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,

            "max_total_requests": (
                MAX_TOTAL_REQUESTS
            ),

            "max_requests_per_host": (
                MAX_REQUESTS_PER_HOST
            ),
        },

        "summary": {
            "raw_s_stage_candidate_count": len(
                candidates
            ),

            "request_count": (
                total_request_count
            ),

            "http_success_count": (
                http_success_count
            ),

            "transport_error_count": (
                transport_error_count
            ),

            "canonical_record_count": len(
                canonical_records
            ),

            "duplicate_endpoint_removed_count": (
                duplicate_endpoint_count
            ),

            "qualified_endpoint_count": len(
                qualified_endpoints
            ),

            "rejected_endpoint_count": len(
                rejected_endpoints
            ),

            "qualified_source_family_count": len(
                family_qualified_counts
            ),

            "modern_endpoint_exclusion_count": len(
                modern_endpoint_urls
            ),

            "trusted_non_government_host_count": len(
                trusted_non_government_hosts
            ),

            "next_stage_endpoint_pool_count": len(
                next_stage_endpoint_pool
            ),
        },

        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "qualified_family_counts": dict(
            sorted(
                family_qualified_counts.items()
            )
        ),

        "trusted_non_government_hosts": sorted(
            trusted_non_government_hosts
        ),

        "qualified_endpoints": (
            qualified_endpoints
        ),

        "rejected_endpoints": (
            rejected_endpoints
        ),

        "all_qualification_records": (
            canonical_records
        ),

        "next_stage_endpoint_pool": (
            next_stage_endpoint_pool
        ),

        "resolution": resolution,

        "next_action": next_action,

        "verified_positive_promotion_allowed": False,

        "runtime_registration_allowed": False,

        "site_positive_allowed": False,

        "final_positive_promotion_allowed": False,
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output_data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    # ========================================================
    # RESULT
    # ========================================================

    print()

    print(
        "=" * 60
    )

    print(
        "HISTORICAL SOURCE FAMILY ENTRY ENDPOINT "
        "QUALIFICATION RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "Raw S-stage candidate count:",
        len(
            candidates
        ),
    )

    print(
        "Request count:",
        total_request_count,
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
        "Canonical record count:",
        len(
            canonical_records
        ),
    )

    print(
        "Duplicate endpoint removed:",
        duplicate_endpoint_count,
    )

    print(
        "Qualified endpoint count:",
        len(
            qualified_endpoints
        ),
    )

    print(
        "Rejected endpoint count:",
        len(
            rejected_endpoints
        ),
    )

    print()

    for family in sorted(
        QUALIFIABLE_SOURCE_FAMILIES
    ):

        print(
            f"{family}:",
            family_qualified_counts.get(
                family,
                0,
            ),
        )

    # ========================================================
    # QUALIFIED PRINT
    # ========================================================

    if qualified_endpoints:

        print()

        print(
            "QUALIFIED HISTORICAL ENTRY ENDPOINTS"
        )

        print(
            "-" * 60
        )

        for index, item in enumerate(
            qualified_endpoints,
            start=1,
        ):

            print(
                f"[{index}] "
                f"{item.get('source_family')}"
            )

            print(
                "Class:",
                item.get(
                    "classification"
                ),
            )

            print(
                "Regions:",
                item.get(
                    "all_input_regions"
                )
                or item.get(
                    "input_regions"
                ),
            )

            print(
                "URL:",
                item.get(
                    "final_url"
                )
                or item.get(
                    "input_url"
                ),
            )

            print(
                "HTTP:",
                item.get(
                    "http_status"
                ),
            )

            print(
                "Title:",
                item.get(
                    "title"
                ),
            )

            print(
                "Reasons:",
                item.get(
                    "qualification_reasons"
                ),
            )

            print()

    # ========================================================
    # REJECTION SUMMARY
    # ========================================================

    print()

    print(
        "REJECTION SUMMARY"
    )

    print(
        "-" * 60
    )

    for classification in [
        CLASS_REJECT_HTTP,
        CLASS_REJECT_NON_OFFICIAL,
        CLASS_REJECT_SHORTENER,
        CLASS_REJECT_EXTERNAL_REDIRECT,
        CLASS_REJECT_REGION,
        CLASS_REJECT_ROLE,
        CLASS_REJECT_GENERIC,
        CLASS_REJECT_MODERN,
        CLASS_REJECT_INVALID,
        CLASS_REJECT_DUPLICATE,
    ]:

        print(
            f"{classification}:",
            classification_counts.get(
                classification,
                0,
            ),
        )

    # ========================================================
    # RESOLUTION
    # ========================================================

    print()

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

    # ========================================================
    # VALIDATION
    # ========================================================

    qualified_urls = [
        canonicalize_url(
            item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            )
            or ""
        )
        for item in qualified_endpoints
    ]

    qualified_hosts = [
        hostname(
            url
        )
        for url in qualified_urls
    ]

    canonical_keys = {
        (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            canonicalize_url(
                item.get(
                    "final_url"
                )
                or item.get(
                    "input_url"
                )
                or ""
            ),
        )
        for item in canonical_records
    }

    next_stage_keys = {
        (
            normalize_space(
                item.get(
                    "source_family"
                )
            ),
            canonicalize_url(
                item.get(
                    "endpoint_url"
                )
                or ""
            ),
        )
        for item in next_stage_endpoint_pool
    }

    non_http_qualified_leakage = sum(
        1
        for item in qualified_endpoints
        if (
            not isinstance(
                item.get(
                    "http_status"
                ),
                int,
            )
            or not (
                200
                <= item.get(
                    "http_status"
                )
                < 300
            )
        )
    )

    shortener_qualified_leakage = sum(
        1
        for host in qualified_hosts
        if host in BLOCKED_REDIRECT_HOSTS
    )

    unrelated_archive_qualified_leakage = sum(
        1
        for host in qualified_hosts
        if host
        in KNOWN_UNRELATED_ARCHIVE_HOSTS
    )

    generic_non_go_kr_leakage = sum(
        1
        for host in qualified_hosts
        if (
            not is_government_host(
                host
            )
            and host
            not in trusted_non_government_hosts
        )
    )

    modern_endpoint_leakage = sum(
        1
        for url in qualified_urls
        if url
        in modern_endpoint_urls
    )

    invalid_class_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "classification"
        )
        not in VALID_CLASSES
    )

    qualified_class_leakage = sum(
        1
        for item in qualified_endpoints
        if item.get(
            "classification"
        )
        not in QUALIFIED_CLASSES
    )

    verified_positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "verified_positive"
        )
        is not False
    )

    runtime_registration_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "runtime_registration_allowed"
        )
        is not False
    )

    site_positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "site_positive_allowed"
        )
        is not False
    )

    # S-stage에서 실제 문제였던 buly.kr가 qualification pool에
    # 절대 진입하지 않아야 한다.
    buly_qualified_leakage = sum(
        1
        for host in qualified_hosts
        if host == "buly.kr"
    )

    saemaul_archive_qualified_leakage = sum(
        1
        for host in qualified_hosts
        if host == "archives.saemaul.or.kr"
    )

    region_unbound_qualified_leakage = sum(
        1
        for item in qualified_endpoints
        if (
            item.get(
                "input_regions"
            )
            and not any(
                reason.startswith(
                    "REGION_MATCH:"
                )
                for reason in (
                    item.get(
                        "qualification_reasons"
                    )
                    or []
                )
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

        "S-stage input exists": (
            S_STAGE_INPUT_PATH.exists()
        ),

        "S-stage input parsed": (
            isinstance(
                s_data,
                dict,
            )
        ),

        "S-stage candidates loaded": (
            len(
                candidates
            )
            > 0
        ),

        "S-stage recovered classification not trusted": (
            output_data[
                "method"
            ][
                "s_stage_recovered_classification_trusted"
            ]
            is False
        ),

        "direct network requery required": (
            output_data[
                "method"
            ][
                "direct_network_requery_required"
            ]
            is True
        ),

        "HTTP 2xx required": (
            output_data[
                "method"
            ][
                "http_2xx_required"
            ]
            is True
        ),

        "final redirect host validation enabled": (
            output_data[
                "method"
            ][
                "final_redirect_host_validation_enabled"
            ]
            is True
        ),

        "URL shortener guard enabled": (
            output_data[
                "method"
            ][
                "url_shortener_guard_enabled"
            ]
            is True
        ),

        "generic .kr suffix official disabled": (
            output_data[
                "method"
            ][
                "generic_kr_suffix_official_disabled"
            ]
            is True
        ),

        "generic .or.kr suffix official disabled": (
            output_data[
                "method"
            ][
                "generic_or_kr_suffix_official_disabled"
            ]
            is True
        ),

        "region binding enabled": (
            output_data[
                "method"
            ][
                "region_binding_required_when_region_present"
            ]
            is True
        ),

        "source-family role qualification enabled": (
            output_data[
                "method"
            ][
                "source_family_role_qualification_enabled"
            ]
            is True
        ),

        "canonical records unique": (
            len(
                canonical_keys
            )
            == len(
                canonical_records
            )
        ),

        "all classes valid": (
            invalid_class_leakage
            == 0
        ),

        "qualified classes valid": (
            qualified_class_leakage
            == 0
        ),

        "next-stage endpoint pool unique": (
            len(
                next_stage_keys
            )
            == len(
                next_stage_endpoint_pool
            )
        ),

        "qualified endpoints require HTTP 2xx": (
            non_http_qualified_leakage
            == 0
        ),

        "shortener qualified leakage zero": (
            shortener_qualified_leakage
            == 0
        ),

        "unrelated archive qualified leakage zero": (
            unrelated_archive_qualified_leakage
            == 0
        ),

        "untrusted non-go.kr qualified leakage zero": (
            generic_non_go_kr_leakage
            == 0
        ),

        "modern endpoint repeat leakage zero": (
            modern_endpoint_leakage
            == 0
        ),

        "region-unbound qualified leakage zero": (
            region_unbound_qualified_leakage
            == 0
        ),

        "buly.kr qualified leakage zero": (
            buly_qualified_leakage
            == 0
        ),

        "saemaul archive qualified leakage zero": (
            saemaul_archive_qualified_leakage
            == 0
        ),

        "verified positive leakage zero": (
            verified_positive_leakage
            == 0
        ),

        "runtime registration leakage zero": (
            runtime_registration_leakage
            == 0
        ),

        "SITE TRUE leakage zero": (
            site_positive_leakage
            == 0
        ),

        "runtime registration remains blocked": (
            output_data[
                "runtime_registration_allowed"
            ]
            is False
        ),

        "SITE TRUE remains blocked": (
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
        "Non-HTTP qualified leakage:",
        non_http_qualified_leakage,
    )

    print(
        "Shortener qualified leakage:",
        shortener_qualified_leakage,
    )

    print(
        "Unrelated archive qualified leakage:",
        unrelated_archive_qualified_leakage,
    )

    print(
        "Untrusted non-go.kr qualified leakage:",
        generic_non_go_kr_leakage,
    )

    print(
        "Modern endpoint repeat leakage:",
        modern_endpoint_leakage,
    )

    print(
        "Region-unbound qualified leakage:",
        region_unbound_qualified_leakage,
    )

    print(
        "buly.kr qualified leakage:",
        buly_qualified_leakage,
    )

    print(
        "Saemaul archive qualified leakage:",
        saemaul_archive_qualified_leakage,
    )

    print(
        "Verified positive leakage:",
        verified_positive_leakage,
    )

    print(
        "Runtime registration leakage:",
        runtime_registration_leakage,
    )

    print(
        "SITE TRUE leakage:",
        site_positive_leakage,
    )

    print()

    all_pass = all(
        validations.values()
    )

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
            "historical source family entry endpoint "
            "qualification regression failed"
        )


if __name__ == "__main__":
    main()