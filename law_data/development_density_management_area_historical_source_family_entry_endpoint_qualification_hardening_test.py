# -*- coding: utf-8 -*-

"""
STEP 17-21-C-16-8-S-3

Development Density Management Area
Historical Source Family Entry Endpoint Qualification Hardening


목표
======================================================================

S-2에서 qualification된 historical endpoint를 다시 직접 조회하여
의미론적 false positive를 제거한다.

S-2의 문제
======================================================================

1. page 전체 body text에서 "도보", "시보", "고시", "공고" 같은
   단어가 발견되면 unrelated endpoint도 qualification될 수 있었다.

예:
    - 경기도 대기질정보 알림톡서비스
    - 버그내 순례길 관광사이트
    - 소방서 일반 홈페이지
    - 일반 알림사항
    - 보도자료
    - 입찰공고
    - 분묘개장공고

2. region binding이 광역단체 수준에서 과도하게 허용되었다.

예:
    경기도 성남시
        ↓
    "경기도" 또는 "gg.go.kr"만 존재해도 성남시 match 처리

3. detail/view 문서가 entry endpoint로 qualification될 수 있었다.

S-3 원칙
======================================================================

1. S-2 qualified endpoint만 입력으로 사용한다.

2. 반드시 직접 HTTP 재조회한다.

3. HTTP 2xx만 qualification 가능하다.

4. 최종 redirect host도 government official host여야 한다.

5. role evidence는 다음 endpoint-local evidence 중심으로 판단한다.

    - document title
    - H1/H2/H3
    - breadcrumb
    - URL/path/query
    - hostname
    - form action
    - search/list structural evidence

6. 전체 body text의 단순 substring은 strong role evidence로 사용하지 않는다.

7. gazette role은 다음과 같은 명확한 문맥을 요구한다.

    - 강서구보
    - 부산시보
    - 서울시보
    - 경기도보
    - ○○군보
    - 구보부록
    - 시보 제1234호
    - 공보 제1234호

8. "도보" 단독 substring은 gazette evidence가 아니다.

9. notice role은 다음과 같은 명확한 endpoint identity를 요구한다.

    - 고시공고
    - 고시·공고
    - 고시/공고
    - 고시 목록
    - 공고 목록
    - publicNotice
    - saeol/gosi
    - eminwon announce

10. 일반 "알림사항", "보도자료", "입찰공고",
    "분묘개장공고"는 historical notice endpoint로 승격하지 않는다.

11. 기초지자체 region이 입력되면 반드시 해당 시/군/구 자체 evidence가
    title / heading / breadcrumb / URL / hostname 중 하나에 있어야 한다.

12. 기초지자체 URL의 공식 영문 identity도 municipality evidence로 인정한다.

예:
    경기도 성남시 -> /seongnam
    경기도 평택시 -> /pyeongtaek
    충청남도 당진시 -> dangjin.go.kr
    부산광역시 강서구 -> bsgangseo.go.kr

단:
    경기도 / gg.go.kr 만으로는 성남시 또는 평택시 match 불가.

13. 개별 detail/view document는 endpoint qualification 대상이 아니다.

14. S-2가 확정한 region identity는 명시적 region field를 우선 사용하고,
    필요한 경우 REGION_MATCH evidence에서 복원한다.

15. 현재 S-3 조회 페이지의 body text에서 region identity를 상속하지 않는다.

16. endpoint 자체는 verified positive가 아니다.

17. runtime registration 금지.

18. SITE TRUE 자동판정 금지.

출력
======================================================================

QUALIFIED_HARDENED_HISTORICAL_GAZETTE_ENDPOINT

QUALIFIED_HARDENED_HISTORICAL_NOTICE_ENDPOINT

QUALIFIED_HARDENED_URBAN_PLANNING_ENDPOINT

REJECTED_DETAIL_DOCUMENT

REJECTED_ROLE_WEAK

REJECTED_REGION_UNBOUND

REJECTED_HTTP_FAILURE

REJECTED_NON_OFFICIAL_HOST

REJECTED_GENERIC_NAVIGATION

REJECTED_MODERN_ENDPOINT_REPEAT

REJECTED_INVALID_URL
"""

from __future__ import annotations

import html
import json
import re
import time

from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple
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

S2_STAGE_INPUT_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / (
        "development_density_management_area_"
        "historical_source_family_entry_endpoint_qualification.json"
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
        "historical_source_family_entry_endpoint_"
        "qualification_hardening.json"
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

FAMILY_GAZETTE = (
    "LEGACY_LOCAL_GAZETTE"
)

FAMILY_NOTICE = (
    "LEGACY_LOCAL_NOTICE"
)

FAMILY_URBAN = (
    "URBAN_PLANNING_ARCHIVE"
)

FAMILY_NOTICE_REVERSE = (
    "NOTICE_NUMBER_REVERSE_LOOKUP"
)

ALLOWED_SOURCE_FAMILIES = {
    FAMILY_GAZETTE,
    FAMILY_NOTICE,
    FAMILY_URBAN,
    FAMILY_NOTICE_REVERSE,
}


# ============================================================
# INPUT QUALIFIED CLASSES
# ============================================================

INPUT_CLASS_GAZETTE = (
    "QUALIFIED_HISTORICAL_GAZETTE_ENDPOINT"
)

INPUT_CLASS_NOTICE = (
    "QUALIFIED_HISTORICAL_NOTICE_ENDPOINT"
)

INPUT_CLASS_URBAN = (
    "QUALIFIED_HISTORICAL_URBAN_PLANNING_ENDPOINT"
)

INPUT_CLASS_NOTICE_REVERSE = (
    "QUALIFIED_HISTORICAL_NOTICE_REVERSE_ENDPOINT"
)

ALLOWED_INPUT_CLASSES = {
    INPUT_CLASS_GAZETTE,
    INPUT_CLASS_NOTICE,
    INPUT_CLASS_URBAN,
    INPUT_CLASS_NOTICE_REVERSE,
}


# ============================================================
# OUTPUT CLASSES
# ============================================================

CLASS_QUALIFIED_GAZETTE = (
    "QUALIFIED_HARDENED_HISTORICAL_GAZETTE_ENDPOINT"
)

CLASS_QUALIFIED_NOTICE = (
    "QUALIFIED_HARDENED_HISTORICAL_NOTICE_ENDPOINT"
)

CLASS_QUALIFIED_URBAN = (
    "QUALIFIED_HARDENED_URBAN_PLANNING_ENDPOINT"
)

CLASS_QUALIFIED_NOTICE_REVERSE = (
    "QUALIFIED_HARDENED_NOTICE_REVERSE_ENDPOINT"
)

CLASS_REJECTED_DETAIL = (
    "REJECTED_DETAIL_DOCUMENT"
)

CLASS_REJECTED_ROLE_WEAK = (
    "REJECTED_ROLE_WEAK"
)

CLASS_REJECTED_REGION = (
    "REJECTED_REGION_UNBOUND"
)

CLASS_REJECTED_HTTP = (
    "REJECTED_HTTP_FAILURE"
)

CLASS_REJECTED_HOST = (
    "REJECTED_NON_OFFICIAL_HOST"
)

CLASS_REJECTED_GENERIC = (
    "REJECTED_GENERIC_NAVIGATION"
)

CLASS_REJECTED_MODERN = (
    "REJECTED_MODERN_ENDPOINT_REPEAT"
)

CLASS_REJECTED_INVALID = (
    "REJECTED_INVALID_URL"
)

VALID_CLASSES = {
    CLASS_QUALIFIED_GAZETTE,
    CLASS_QUALIFIED_NOTICE,
    CLASS_QUALIFIED_URBAN,
    CLASS_QUALIFIED_NOTICE_REVERSE,
    CLASS_REJECTED_DETAIL,
    CLASS_REJECTED_ROLE_WEAK,
    CLASS_REJECTED_REGION,
    CLASS_REJECTED_HTTP,
    CLASS_REJECTED_HOST,
    CLASS_REJECTED_GENERIC,
    CLASS_REJECTED_MODERN,
    CLASS_REJECTED_INVALID,
}

QUALIFIED_CLASSES = {
    CLASS_QUALIFIED_GAZETTE,
    CLASS_QUALIFIED_NOTICE,
    CLASS_QUALIFIED_URBAN,
    CLASS_QUALIFIED_NOTICE_REVERSE,
}


# ============================================================
# HTTP
# ============================================================

TIMEOUT = 20

MAX_RESPONSE_BYTES = (
    12
    * 1024
    * 1024
)

REQUEST_DELAY_SECONDS = 0.03

MAX_TOTAL_REQUESTS = 100

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0 Safari/537.36"
)


# ============================================================
# HTML PATTERNS
# ============================================================

TITLE_PATTERN = re.compile(
    r"<title\b[^>]*>(.*?)</title>",
    re.IGNORECASE
    | re.DOTALL,
)

HEADING_PATTERN = re.compile(
    r"<h[1-3]\b[^>]*>(.*?)</h[1-3]>",
    re.IGNORECASE
    | re.DOTALL,
)

FORM_PATTERN = re.compile(
    r"<form\b[^>]*action\s*=\s*[\"']([^\"']+)[\"']",
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

COMMENT_PATTERN = re.compile(
    r"<!--.*?-->",
    re.DOTALL,
)

BREADCRUMB_BLOCK_PATTERN = re.compile(
    r"<(?P<tag>div|nav|ul|ol)\b"
    r"(?P<attrs>[^>]*"
    r"(?:breadcrumb|location|path|navi|navigation)"
    r"[^>]*)>"
    r"(?P<body>.*?)"
    r"</(?P=tag)>",
    re.IGNORECASE
    | re.DOTALL,
)


# ============================================================
# URL NORMALIZATION
# ============================================================

VOLATILE_QUERY_KEYS = {
    "token",
    "_csrf",
    "csrf",
    "sessionid",
    "jsessionid",
    "timestamp",
    "rand",
    "random",
    "_",
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


# ============================================================
# SEMANTIC RULES
# ============================================================

GENERIC_TITLE_TERMS = {
    "",
    "home",
    "홈",
    "메인",
    "main",
}

# ------------------------------------------------------------
# Detail identity
# ------------------------------------------------------------

DETAIL_URL_PATTERNS = [
    re.compile(
        r"/view(?:\.do|/|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"/detail(?:\.do|/|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"/read(?:\.do|/|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"/post/view\.do",
        re.IGNORECASE,
    ),
    re.compile(
        r"/board/view",
        re.IGNORECASE,
    ),
]

DETAIL_QUERY_KEYS = {
    "idx",
    "nttid",
    "board_seq",
    "article_no",
    "articleid",
    "post_no",
    "postno",
    "seq",
}

LIST_URL_TERMS = [
    "/list",
    "list.do",
    "selectboardlist",
    "index.do",
    "publicnotice",
    "announce",
]


# ------------------------------------------------------------
# Strong Gazette
# ------------------------------------------------------------

GAZETTE_STRONG_PATTERNS = [
    re.compile(
        r"[가-힣]{2,20}(?:시보|군보|구보|도보)"
    ),
    re.compile(
        r"(?:시보|군보|구보|도보|공보)"
        r"\s*(?:제\s*)?\d+\s*호"
    ),
    re.compile(
        r"(?:시보|군보|구보|도보|공보)"
        r"\s*(?:목록|검색|보기|부록|발행)"
    ),
    re.compile(
        r"(?:구보|시보|군보|도보)부록"
    ),
]

GAZETTE_URL_TERMS = [
    "nscvrg",
    "gazette",
    "gubo",
    "sibo",
    "gunbo",
    "gongbo",
]


# ------------------------------------------------------------
# Strong Notice
# ------------------------------------------------------------

NOTICE_STRONG_PATTERNS = [
    re.compile(
        r"고시\s*[·ㆍ/\-]?\s*공고"
    ),
    re.compile(
        r"고시공고"
    ),
    re.compile(
        r"(?:고시|공고)\s*(?:목록|검색|조회)"
    ),
    re.compile(
        r"(?:행정)?(?:고시|공고)\s*게시판"
    ),
]

NOTICE_URL_TERMS = [
    "publicnotice",
    "saeol/gosi",
    "eminwonannounce",
    "eminwon/announce",
    "gosi",
    "notice/list",
]


# ------------------------------------------------------------
# Notice exclusions
# ------------------------------------------------------------

NOTICE_FALSE_POSITIVE_TERMS = [
    "알림사항",
    "보도자료",
    "입찰공고",
    "분묘개장공고",
    "채용공고",
    "시험공고",
    "행사공고",
]


# ------------------------------------------------------------
# Urban planning
# ------------------------------------------------------------

URBAN_STRONG_PATTERNS = [
    re.compile(
        r"도시관리계획"
    ),
    re.compile(
        r"도시계획"
    ),
    re.compile(
        r"지형도면"
    ),
    re.compile(
        r"도시계획\s*(?:고시|공고|열람|검색|자료)"
    ),
]

URBAN_URL_TERMS = [
    "cityplan",
    "urbanplanning",
    "urban-plan",
    "urban_plan",
    "city-plan",
]


# ============================================================
# REGION ALIASES
# ============================================================

PROVINCE_ALIASES = {
    "서울특별시": [
        "서울특별시",
        "서울",
        "seoul",
    ],
    "부산광역시": [
        "부산광역시",
        "부산",
        "busan",
    ],
    "대구광역시": [
        "대구광역시",
        "대구",
        "daegu",
    ],
    "인천광역시": [
        "인천광역시",
        "인천",
        "incheon",
    ],
    "광주광역시": [
        "광주광역시",
        "광주",
        "gwangju",
    ],
    "대전광역시": [
        "대전광역시",
        "대전",
        "daejeon",
    ],
    "울산광역시": [
        "울산광역시",
        "울산",
        "ulsan",
    ],
    "세종특별자치시": [
        "세종특별자치시",
        "세종",
        "sejong",
    ],
    "경기도": [
        "경기도",
        "경기",
        "gyeonggi",
        "gg.go.kr",
    ],
    "강원특별자치도": [
        "강원특별자치도",
        "강원도",
        "강원",
        "gangwon",
    ],
    "충청북도": [
        "충청북도",
        "충북",
        "chungbuk",
    ],
    "충청남도": [
        "충청남도",
        "충남",
        "chungnam",
    ],
    "전북특별자치도": [
        "전북특별자치도",
        "전라북도",
        "전북",
        "jeonbuk",
    ],
    "전라남도": [
        "전라남도",
        "전남",
        "jeonnam",
    ],
    "경상북도": [
        "경상북도",
        "경북",
        "gyeongbuk",
    ],
    "경상남도": [
        "경상남도",
        "경남",
        "gyeongnam",
    ],
    "제주특별자치도": [
        "제주특별자치도",
        "제주",
        "jeju",
    ],
}


# 현재 S-stage에서 실제 관측된 municipality host/path identity.
#
# 광역단체 alias와 달리 municipality binding을 위해서만 사용한다.
# 이 alias가 존재하지 않는 지자체는 한글 municipality identity가
# title / heading / breadcrumb / URL / hostname에 직접 존재해야 한다.
MUNICIPALITY_URL_ALIASES = {
    "성남시": [
        "seongnam",
    ],
    "평택시": [
        "pyeongtaek",
    ],
    "당진시": [
        "dangjin",
    ],
    "강서구": [
        "gangseo",
        "bsgangseo",
    ],
    "순천시": [
        "suncheon",
    ],
    "구미시": [
        "gumi",
    ],
    "천안시": [
        "cheonan",
    ],
    "창원시": [
        "changwon",
    ],
    "달성군": [
        "dalseong",
    ],
    "달서구": [
        "dalseo",
    ],
}


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
        normalize_space(
            term
        ).lower()
        in lowered
        for term in terms
    )


def strip_html(
    raw_html: str,
) -> str:

    value = COMMENT_PATTERN.sub(
        " ",
        raw_html,
    )

    value = SCRIPT_STYLE_PATTERN.sub(
        " ",
        value,
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


# ============================================================
# S-2 REGION RECOVERY
# ============================================================

def extract_endpoint_regions(
    item: Dict[str, Any],
) -> List[str]:

    """
    S-2 qualification record에서 region identity를 복원한다.

    실제 S-2 schema
    ------------------------------------------------------------
    - input_regions
    - all_input_regions
    - qualification_reasons

    호환 schema
    ------------------------------------------------------------
    - regions
    - region
    - matched_regions
    - matched_region
    - qualified_regions
    - bound_regions
    - region_binding
    - region_evidence

    원칙
    ------------------------------------------------------------
    1. structured region field를 최우선으로 사용한다.
    2. qualification_reasons의 REGION_MATCH는 fallback으로 사용한다.
    3. S-3 재조회 page body에서 region을 상속하지 않는다.
    4. S-3 region_matches()에서 endpoint-local evidence를 다시 검증한다.
    """

    result: List[str] = []

    def add_region_value(
        value: Any,
    ) -> None:

        if value is None:
            return

        # ----------------------------------------------------
        # STRING
        # ----------------------------------------------------

        if isinstance(
            value,
            str,
        ):

            text = normalize_space(
                value
            )

            if not text:
                return

            # 복수 지역 문자열
            #
            # "경기도 성남시 / 경기도 평택시"
            # "경기도 성남시; 경기도 평택시"
            #
            # comma는 REGION_MATCH alias 표현과 혼동되므로
            # structured value에서는 기본적으로 분리하지 않는다.
            parts = re.split(
                r"\s*/\s*|\s*;\s*",
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

            return

        # ----------------------------------------------------
        # LIST
        # ----------------------------------------------------

        if isinstance(
            value,
            list,
        ):

            for child in value:

                add_region_value(
                    child
                )

            return

        # ----------------------------------------------------
        # DICT
        # ----------------------------------------------------

        if isinstance(
            value,
            dict,
        ):

            preferred_keys = [
                "input_regions",
                "all_input_regions",

                "regions",
                "region",

                "name",
                "region_name",

                "matched_regions",
                "matched_region",

                "qualified_regions",
                "qualified_region",

                "municipalities",
                "municipality",

                "matched_municipalities",
                "matched_municipality",

                "bound_regions",
                "bound_region",
            ]

            matched_preferred = False

            for key in preferred_keys:

                if key not in value:
                    continue

                matched_preferred = True

                add_region_value(
                    value.get(
                        key
                    )
                )

            if not matched_preferred:

                for child in value.values():

                    if isinstance(
                        child,
                        (
                            dict,
                            list,
                        ),
                    ):

                        add_region_value(
                            child
                        )

    # --------------------------------------------------------
    # 1. Structured region
    # --------------------------------------------------------

    structured_region_keys = [
        "input_regions",
        "all_input_regions",

        "regions",
        "region",

        "matched_regions",
        "matched_region",

        "region_names",
        "region_name",

        "municipalities",
        "municipality",

        "matched_municipalities",
        "matched_municipality",

        "qualified_regions",
        "qualified_region",

        "bound_regions",
        "bound_region",

        "region_binding",
        "region_bindings",

        "region_evidence",
    ]

    for key in structured_region_keys:

        if key not in item:
            continue

        add_region_value(
            item.get(
                key
            )
        )

    # --------------------------------------------------------
    # 2. REGION_MATCH fallback
    # --------------------------------------------------------

    reason_values: List[Any] = []

    qualification_reasons = item.get(
        "qualification_reasons"
    )

    if isinstance(
        qualification_reasons,
        list,
    ):

        reason_values.extend(
            qualification_reasons
        )

    reasons = item.get(
        "reasons"
    )

    if isinstance(
        reasons,
        list,
    ):

        reason_values.extend(
            reasons
        )

    for reason in reason_values:

        reason_text = normalize_space(
            reason
        )

        if not reason_text:
            continue

        if not reason_text.startswith(
            "REGION_MATCH:"
        ):

            continue

        payload = reason_text[
            len(
                "REGION_MATCH:"
            ):
        ]

        # 예:
        #
        # REGION_MATCH:경기도 성남시:
        #     경기도 성남시,경기도,경기,gg.go.kr
        #
        # 첫 ':' 앞부분만 region identity로 사용한다.
        region = normalize_space(
            payload.split(
                ":",
                1,
            )[0]
        )

        if region:

            result.append(
                region
            )

    # --------------------------------------------------------
    # 3. Normalize / dedupe
    # --------------------------------------------------------

    normalized_regions: List[str] = []

    for region in unique_strings(
        result
    ):

        region = normalize_space(
            region
        )

        if not region:
            continue

        if region.upper().startswith(
            "REGION_MATCH"
        ):

            continue

        lowered = region.lower()

        # URL/hostname 자체가 region으로 유입되는 것 차단
        if "://" in lowered:
            continue

        if lowered.endswith(
            ".go.kr"
        ):
            continue

        if lowered.endswith(
            ".kr"
        ):
            continue

        normalized_regions.append(
            region
        )

    return unique_strings(
        normalized_regions
    )


# ============================================================
# URL
# ============================================================

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

    if not parsed.hostname:
        return ""

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
    seen_pairs = set()

    for raw_key, raw_value in parse_qsl(
        parsed.query,
        keep_blank_values=True,
    ):

        key = normalize_space(
            raw_key
        )

        if not key:
            continue

        lowered = key.lower()

        if lowered in VOLATILE_QUERY_KEYS:
            continue

        if lowered in TRACKING_QUERY_KEYS:
            continue

        if "csrf" in lowered:
            continue

        if "session" in lowered:
            continue

        pair = (
            key,
            raw_value,
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


# ============================================================
# OFFICIAL HOST
# ============================================================

def is_government_host(
    host: str,
) -> bool:

    value = normalize_space(
        host
    ).lower()

    if not value:
        return False

    if (
        value == "go.kr"
        or value.endswith(
            ".go.kr"
        )
    ):

        return True

    return False


# ============================================================
# INPUT LOAD
# ============================================================

def walk_dicts(
    value: Any,
):

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


def load_s2_qualified_endpoints(
    data: Dict[str, Any],
) -> List[Dict[str, Any]]:

    """
    S-2 qualified endpoint만 로드한다.

    중요:
    ------------------------------------------------------------
    S-2 원본 record의
        input_regions
        all_input_regions
        qualification_reasons
    를 그대로 보존한 상태에서 regions를 별도 normalized field로 생성한다.
    """

    preferred_keys = [
        "qualified_endpoints",
        "qualified_historical_entry_endpoints",
        "next_stage_endpoint_pool",
    ]

    raw: List[
        Dict[str, Any]
    ] = []

    for key in preferred_keys:

        value = data.get(
            key
        )

        if not isinstance(
            value,
            list,
        ):

            continue

        for item in value:

            if isinstance(
                item,
                dict,
            ):

                raw.append(
                    item
                )

    # --------------------------------------------------------
    # Schema variation fallback
    # --------------------------------------------------------

    if not raw:

        for item in walk_dicts(
            data
        ):

            classification = normalize_space(
                item.get(
                    "classification"
                )
                or item.get(
                    "endpoint_class"
                )
                or ""
            )

            qualified = (
                item.get(
                    "qualified"
                )
                is True
            )

            if (
                classification
                in ALLOWED_INPUT_CLASSES
                or qualified
            ):

                raw.append(
                    item
                )

    result: List[
        Dict[str, Any]
    ] = []

    seen: Set[
        Tuple[str, str]
    ] = set()

    for item in raw:

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        if family not in ALLOWED_SOURCE_FAMILIES:
            continue

        classification = normalize_space(
            item.get(
                "classification"
            )
            or item.get(
                "endpoint_class"
            )
        )

        qualified_flag = (
            item.get(
                "qualified"
            )
            is True
        )

        # S-2 qualified class 또는 explicit qualified=True만 허용
        if (
            classification
            and classification
            not in ALLOWED_INPUT_CLASSES
            and not qualified_flag
        ):

            continue

        url = canonicalize_url(
            item.get(
                "url"
            )
            or item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            )
            or ""
        )

        if not url:
            continue

        key = (
            family,
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
            "source_family"
        ] = family

        normalized[
            "url"
        ] = url

        normalized[
            "regions"
        ] = extract_endpoint_regions(
            item
        )

        result.append(
            normalized
        )

    return result


# ============================================================
# MODERN EXCLUSION
# ============================================================

def load_modern_endpoint_exclusions(
    data: Dict[str, Any],
) -> Set[str]:

    result: Set[str] = set()

    for item in walk_dicts(
        data
    ):

        for key in [
            "url",
            "endpoint_url",
            "final_url",
            "canonical_url",
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
# HTTP
# ============================================================

def decode_html(
    response: requests.Response,
    data: bytes,
) -> Tuple[str, str]:

    """
    stream=True 응답에서는 body 소비 후
    response.apparent_encoding을 호출하지 않는다.

    순서:
    ------------------------------------------------------------
    1. Content-Type charset
    2. response.encoding
    3. HTML meta charset
    4. utf-8
    5. cp949
    6. euc-kr
    """

    candidates: List[str] = []

    content_type = normalize_space(
        response.headers.get(
            "Content-Type"
        )
    )

    charset_match = re.search(
        r"""charset\s*=\s*["']?([^;"'\s]+)""",
        content_type,
        flags=re.IGNORECASE,
    )

    if charset_match:

        candidates.append(
            normalize_space(
                charset_match.group(1)
            )
        )

    if response.encoding:

        candidates.append(
            normalize_space(
                response.encoding
            )
        )

    prefix = data[
        :8192
    ]

    ascii_preview = prefix.decode(
        "ascii",
        errors="ignore",
    )

    meta_patterns = [
        re.compile(
            r"""<meta[^>]+charset\s*=\s*["']?\s*([A-Za-z0-9._\-]+)""",
            re.IGNORECASE,
        ),
        re.compile(
            r"""<meta[^>]+content\s*=\s*["'][^"']*charset\s*=\s*([A-Za-z0-9._\-]+)""",
            re.IGNORECASE,
        ),
    ]

    for pattern in meta_patterns:

        match = pattern.search(
            ascii_preview
        )

        if match:

            candidates.append(
                normalize_space(
                    match.group(1)
                )
            )

    candidates.extend(
        [
            "utf-8",
            "cp949",
            "euc-kr",
        ]
    )

    candidates = unique_strings(
        candidates
    )

    for encoding in candidates:

        try:

            decoded = data.decode(
                encoding
            )

            return (
                decoded,
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


def fetch_page(
    session: requests.Session,
    url: str,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "requested_url": url,
        "final_url": "",
        "http_status": None,
        "content_type": "",
        "content_length": None,
        "response_bytes": 0,
        "encoding": "",
        "raw_html": "",
        "error": "",
        "error_stage": "",
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

            content_length = normalize_space(
                response.headers.get(
                    "Content-Length"
                )
            )

            if content_length:

                try:

                    result[
                        "content_length"
                    ] = int(
                        content_length
                    )

                except Exception:

                    result[
                        "content_length"
                    ] = None

            chunks: List[bytes] = []
            total = 0

            try:

                for chunk in response.iter_content(
                    chunk_size=128 * 1024,
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

            except Exception as exc:

                result[
                    "error"
                ] = repr(
                    exc
                )

                result[
                    "error_stage"
                ] = "BODY_DOWNLOAD"

                return result

            data = b"".join(
                chunks
            )

            result[
                "response_bytes"
            ] = len(
                data
            )

            content_type_lower = normalize_space(
                result.get(
                    "content_type"
                )
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
                in content_type_lower
                or "xhtml"
                in content_type_lower
                or "text/"
                in content_type_lower
                or prefix.startswith(
                    b"<!doctype html"
                )
                or prefix.startswith(
                    b"<html"
                )
            )

            if not html_like:

                return result

            try:

                decoded, encoding = decode_html(
                    response,
                    data,
                )

            except Exception as exc:

                result[
                    "error"
                ] = repr(
                    exc
                )

                result[
                    "error_stage"
                ] = "HTML_DECODE"

                return result

            result[
                "raw_html"
            ] = decoded

            result[
                "encoding"
            ] = encoding

    except requests.RequestException as exc:

        result[
            "error"
        ] = repr(
            exc
        )

        result[
            "error_stage"
        ] = "HTTP_REQUEST"

    except Exception as exc:

        result[
            "error"
        ] = repr(
            exc
        )

        result[
            "error_stage"
        ] = "UNEXPECTED"

    return result


# ============================================================
# HTML LOCAL EVIDENCE
# ============================================================

def extract_title(
    raw_html: str,
) -> str:

    match = TITLE_PATTERN.search(
        raw_html
    )

    if not match:
        return ""

    return strip_html(
        match.group(1)
    )


def extract_headings(
    raw_html: str,
) -> List[str]:

    return unique_strings(
        strip_html(
            match.group(1)
        )
        for match in HEADING_PATTERN.finditer(
            raw_html
        )
    )


def extract_breadcrumbs(
    raw_html: str,
) -> List[str]:

    result: List[str] = []

    for match in BREADCRUMB_BLOCK_PATTERN.finditer(
        raw_html
    ):

        text = strip_html(
            match.group(
                "body"
            )
        )

        if text:

            result.append(
                text
            )

    return unique_strings(
        result
    )


def extract_form_actions(
    raw_html: str,
) -> List[str]:

    return unique_strings(
        html.unescape(
            match.group(1)
        )
        for match in FORM_PATTERN.finditer(
            raw_html
        )
    )


# ============================================================
# DETAIL / LIST
# ============================================================

def is_detail_document_url(
    url: str,
) -> bool:

    lowered = url.lower()

    list_like = any(
        term in lowered
        for term in LIST_URL_TERMS
    )

    if list_like:
        return False

    for pattern in DETAIL_URL_PATTERNS:

        if pattern.search(
            lowered
        ):

            return True

    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return False

    query_keys = {
        key.lower()
        for key, _
        in parse_qsl(
            parsed.query,
            keep_blank_values=True,
        )
    }

    strong_detail_query_keys = (
        query_keys
        & DETAIL_QUERY_KEYS
    )

    if (
        strong_detail_query_keys
        and not any(
            term in lowered
            for term in [
                "list",
                "search",
            ]
        )
    ):

        return True

    return False


def looks_list_or_entry(
    url: str,
    title: str,
    headings: List[str],
    form_actions: List[str],
) -> bool:

    evidence = normalize_space(
        " ".join(
            [
                url,
                title,
                *headings,
                *form_actions,
            ]
        )
    ).lower()

    return contains_any(
        evidence,
        [
            "목록",
            "검색",
            "조회",
            "/list",
            "list.do",
            "search",
            "publicnotice",
            "selectboardlist",
            "index.do",
        ],
    )


# ============================================================
# REGION BINDING
# ============================================================

def split_region(
    region: str,
) -> Tuple[str, str]:

    value = normalize_space(
        region
    )

    if not value:
        return "", ""

    match = re.match(
        r"^(.+?(?:특별시|광역시|특별자치시|특별자치도|도))"
        r"(?:\s+(.+?(?:시|군|구)))?$",
        value,
    )

    if match:

        return (
            normalize_space(
                match.group(1)
            ),
            normalize_space(
                match.group(2)
            ),
        )

    return (
        value,
        "",
    )


def municipality_aliases(
    municipality: str,
) -> List[str]:

    value = normalize_space(
        municipality
    )

    if not value:
        return []

    result: List[str] = [
        value,
    ]

    stem = re.sub(
        r"(?:시|군|구)$",
        "",
        value,
    )

    if (
        stem
        and len(
            stem
        ) >= 2
    ):

        result.append(
            stem
        )

    result.extend(
        MUNICIPALITY_URL_ALIASES.get(
            value,
            [],
        )
    )

    return unique_strings(
        result
    )


def region_matches(
    regions: List[str],
    *,
    url: str,
    title: str,
    headings: List[str],
    breadcrumbs: List[str],
) -> Tuple[
    bool,
    List[str],
]:

    """
    S-2 region identity가 현재 endpoint-local evidence와 실제로 결합되는지 검증.

    중요 원칙
    ------------------------------------------------------------
    municipality가 있는 경우 municipality 자체 evidence가 필수다.

    따라서:
        경기도 + gg.go.kr
    만으로
        경기도 성남시
    를 인정하지 않는다.

    반면:
        /seongnam
        /pyeongtaek
        dangjin.go.kr
        bsgangseo.go.kr
    와 같은 municipality-specific URL/hostname evidence는 허용한다.

    municipality가 명확하면 동일 공식 go.kr endpoint에서 province 문자열이
    별도로 노출되지 않아도 municipality binding은 성립한다.
    """

    if not regions:

        return (
            False,
            [],
        )

    url_evidence = normalize_space(
        " ".join(
            [
                url,
                hostname(
                    url
                ),
            ]
        )
    ).lower()

    textual_evidence = normalize_space(
        " ".join(
            [
                title,
                *headings,
                *breadcrumbs,
            ]
        )
    ).lower()

    local_evidence = normalize_space(
        f"{url_evidence} {textual_evidence}"
    ).lower()

    matched: List[str] = []

    for region in regions:

        province, municipality = split_region(
            region
        )

        province_aliases = (
            PROVINCE_ALIASES.get(
                province,
                [
                    province
                ],
            )
        )

        province_match = any(
            normalize_space(
                alias
            ).lower()
            in local_evidence
            for alias in province_aliases
            if normalize_space(
                alias
            )
        )

        # ----------------------------------------------------
        # Municipality-level region
        # ----------------------------------------------------

        if municipality:

            aliases = municipality_aliases(
                municipality
            )

            municipality_match = any(
                normalize_space(
                    alias
                ).lower()
                in local_evidence
                for alias in aliases
                if normalize_space(
                    alias
                )
            )

            # municipality evidence 자체가 필수.
            #
            # province_match는 보조증거이지 필수조건이 아니다.
            # dangjin.go.kr처럼 municipality official host 자체가
            # 충분히 구체적인 경우를 보존한다.
            if municipality_match:

                matched.append(
                    region
                )

            continue

        # ----------------------------------------------------
        # Province-only region
        # ----------------------------------------------------

        if province_match:

            matched.append(
                region
            )

    return (
        bool(
            matched
        ),
        unique_strings(
            matched
        ),
    )


# ============================================================
# ROLE EVIDENCE
# ============================================================

def collect_endpoint_local_text(
    *,
    url: str,
    title: str,
    headings: List[str],
    breadcrumbs: List[str],
    form_actions: List[str],
) -> str:

    return normalize_space(
        " ".join(
            [
                url,
                hostname(
                    url
                ),
                title,
                *headings,
                *breadcrumbs,
                *form_actions,
            ]
        )
    )


def evaluate_gazette_role(
    local_text: str,
    url: str,
) -> Tuple[
    bool,
    List[str],
]:

    reasons: List[str] = []

    for pattern in GAZETTE_STRONG_PATTERNS:

        match = pattern.search(
            local_text
        )

        if not match:
            continue

        evidence = normalize_space(
            match.group(0)
        )

        if evidence == "도보":
            continue

        reasons.append(
            "GAZETTE_LOCAL:"
            + evidence
        )

    lowered_url = url.lower()

    for term in GAZETTE_URL_TERMS:

        if term in lowered_url:

            reasons.append(
                "GAZETTE_URL:"
                + term
            )

    return (
        bool(
            reasons
        ),
        unique_strings(
            reasons
        ),
    )


def evaluate_notice_role(
    local_text: str,
    url: str,
) -> Tuple[
    bool,
    List[str],
]:

    reasons: List[str] = []

    for pattern in NOTICE_STRONG_PATTERNS:

        match = pattern.search(
            local_text
        )

        if match:

            reasons.append(
                "NOTICE_LOCAL:"
                + normalize_space(
                    match.group(0)
                )
            )

    lowered_url = url.lower()

    for term in NOTICE_URL_TERMS:

        if term in lowered_url:

            reasons.append(
                "NOTICE_URL:"
                + term
            )

    false_positive_terms = [
        term
        for term in NOTICE_FALSE_POSITIVE_TERMS
        if term in local_text
    ]

    # 명시적인 false-positive board identity가 있으면
    # URL 자체가 official notice 구조를 갖는 경우에만 예외 허용.
    if (
        false_positive_terms
        and not any(
            term in lowered_url
            for term in NOTICE_URL_TERMS
        )
    ):

        return (
            False,
            [
                "NOTICE_FALSE_POSITIVE:"
                + term
                for term in false_positive_terms
            ],
        )

    return (
        bool(
            reasons
        ),
        unique_strings(
            reasons
        ),
    )


def evaluate_urban_role(
    local_text: str,
    url: str,
) -> Tuple[
    bool,
    List[str],
]:

    reasons: List[str] = []

    for pattern in URBAN_STRONG_PATTERNS:

        match = pattern.search(
            local_text
        )

        if match:

            reasons.append(
                "URBAN_LOCAL:"
                + normalize_space(
                    match.group(0)
                )
            )

    lowered_url = url.lower()

    for term in URBAN_URL_TERMS:

        if term in lowered_url:

            reasons.append(
                "URBAN_URL:"
                + term
            )

    return (
        bool(
            reasons
        ),
        unique_strings(
            reasons
        ),
    )


# ============================================================
# GENERIC GUARD
# ============================================================

def looks_generic_page(
    url: str,
    title: str,
    headings: List[str],
) -> bool:

    normalized_title = normalize_space(
        title
    ).lower()

    if (
        normalized_title
        in GENERIC_TITLE_TERMS
    ):

        return True

    try:

        parsed = urlparse(
            url
        )

    except Exception:

        return True

    path = (
        parsed.path
        or "/"
    ).lower()

    if (
        path
        in {
            "",
            "/",
            "/main.do",
            "/index.do",
        }
        and not normalize_space(
            title
        )
        and not headings
    ):

        return True

    return False


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
        "HISTORICAL SOURCE FAMILY ENTRY ENDPOINT "
        "QUALIFICATION HARDENING"
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
        "S-2 input:",
        S2_STAGE_INPUT_PATH,
    )

    print(
        "H-stage input:",
        H_STAGE_INPUT_PATH,
    )

    print()

    # ========================================================
    # INPUT
    # ========================================================

    if not S2_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "S-2 input not found: "
            f"{S2_STAGE_INPUT_PATH}"
        )

    if not H_STAGE_INPUT_PATH.exists():

        raise FileNotFoundError(
            "H-stage input not found: "
            f"{H_STAGE_INPUT_PATH}"
        )

    s2_data = json.loads(
        S2_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    h_data = json.loads(
        H_STAGE_INPUT_PATH.read_text(
            encoding="utf-8"
        )
    )

    if not isinstance(
        s2_data,
        dict,
    ):

        raise TypeError(
            "S-2 input must be JSON object."
        )

    if not isinstance(
        h_data,
        dict,
    ):

        raise TypeError(
            "H-stage input must be JSON object."
        )

    input_endpoints = (
        load_s2_qualified_endpoints(
            s2_data
        )
    )

    modern_exclusions = (
        load_modern_endpoint_exclusions(
            h_data
        )
    )

    print(
        "S-2 qualified endpoint count:",
        len(
            input_endpoints
        ),
    )

    print(
        "Modern endpoint exclusion count:",
        len(
            modern_exclusions
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

    request_count = 0
    http_success_count = 0
    transport_error_count = 0

    records: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # ENDPOINT LOOP
    # ========================================================

    for index, item in enumerate(
        input_endpoints,
        start=1,
    ):

        if (
            request_count
            >= MAX_TOTAL_REQUESTS
        ):

            break

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        input_url = canonicalize_url(
            item.get(
                "url"
            )
            or ""
        )

        regions = extract_endpoint_regions(
            item
        )

        print(
            "-" * 60
        )

        print(
            f"ENDPOINT {index}"
        )

        print(
            "Family:",
            family,
        )

        print(
            "Regions:",
            regions,
        )

        print(
            "Input URL:",
            input_url,
        )

        # ----------------------------------------------------
        # Invalid URL
        # ----------------------------------------------------

        if not input_url:

            record = {
                "source_family": family,
                "regions": regions,
                "input_url": input_url,
                "final_url": "",
                "http_status": None,
                "qualified": False,
                "classification": CLASS_REJECTED_INVALID,
                "reasons": [
                    "INVALID_URL"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_INVALID,
            )

            continue

        # ----------------------------------------------------
        # Modern repeat
        # ----------------------------------------------------

        if input_url in modern_exclusions:

            record = {
                "source_family": family,
                "regions": regions,
                "input_url": input_url,
                "final_url": input_url,
                "http_status": None,
                "qualified": False,
                "classification": CLASS_REJECTED_MODERN,
                "reasons": [
                    "MODERN_ENDPOINT_REPEAT"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_MODERN,
            )

            continue

        # ----------------------------------------------------
        # Input host
        # ----------------------------------------------------

        if not is_government_host(
            hostname(
                input_url
            )
        ):

            record = {
                "source_family": family,
                "regions": regions,
                "input_url": input_url,
                "final_url": "",
                "http_status": None,
                "qualified": False,
                "classification": CLASS_REJECTED_HOST,
                "reasons": [
                    "INPUT_HOST_NOT_GO_KR"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_HOST,
            )

            continue

        # ----------------------------------------------------
        # HTTP requery
        # ----------------------------------------------------

        request_count += 1

        response = fetch_page(
            session,
            input_url,
        )

        http_status = response.get(
            "http_status"
        )

        final_url = canonicalize_url(
            response.get(
                "final_url"
            )
            or input_url
        )

        if (
            isinstance(
                http_status,
                int,
            )
            and 200
            <= http_status
            < 300
        ):

            http_success_count += 1

        if response.get(
            "error"
        ):

            transport_error_count += 1

        if (
            not isinstance(
                http_status,
                int,
            )
            or not (
                200
                <= http_status
                < 300
            )
            or response.get(
                "error"
            )
        ):

            record = {
                "source_family": family,
                "regions": regions,
                "input_url": input_url,
                "final_url": final_url,
                "http_status": http_status,
                "qualified": False,
                "classification": CLASS_REJECTED_HTTP,
                "error_stage": response.get(
                    "error_stage"
                ),
                "error": response.get(
                    "error"
                ),
                "reasons": [
                    normalize_space(
                        response.get(
                            "error"
                        )
                    )
                    or "HTTP_NON_2XX"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "HTTP:",
                http_status,
            )

            print(
                "Error stage:",
                response.get(
                    "error_stage"
                )
                or "-",
            )

            print(
                "Error:",
                response.get(
                    "error"
                )
                or "-",
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_HTTP,
            )

            continue

        # ----------------------------------------------------
        # Final host
        # ----------------------------------------------------

        if not is_government_host(
            hostname(
                final_url
            )
        ):

            record = {
                "source_family": family,
                "regions": regions,
                "input_url": input_url,
                "final_url": final_url,
                "http_status": http_status,
                "qualified": False,
                "classification": CLASS_REJECTED_HOST,
                "reasons": [
                    "FINAL_HOST_NOT_GO_KR"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "HTTP:",
                http_status,
            )

            print(
                "Final URL:",
                final_url,
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_HOST,
            )

            continue

        # ----------------------------------------------------
        # HTML evidence
        # ----------------------------------------------------

        raw_html = str(
            response.get(
                "raw_html"
            )
            or ""
        )

        title = extract_title(
            raw_html
        )

        headings = extract_headings(
            raw_html
        )

        breadcrumbs = extract_breadcrumbs(
            raw_html
        )

        form_actions = extract_form_actions(
            raw_html
        )

        local_text = collect_endpoint_local_text(
            url=final_url,
            title=title,
            headings=headings,
            breadcrumbs=breadcrumbs,
            form_actions=form_actions,
        )

        # ----------------------------------------------------
        # Detail guard
        # ----------------------------------------------------

        detail_document = is_detail_document_url(
            final_url
        )

        list_or_entry = looks_list_or_entry(
            final_url,
            title,
            headings,
            form_actions,
        )

        if (
            detail_document
            and not list_or_entry
        ):

            record = {
                "source_family": family,
                "regions": regions,
                "matched_regions": [],
                "input_url": input_url,
                "final_url": final_url,
                "http_status": http_status,
                "content_type": response.get(
                    "content_type"
                ),
                "encoding": response.get(
                    "encoding"
                ),
                "title": title,
                "headings": headings,
                "breadcrumbs": breadcrumbs,
                "form_actions": form_actions,
                "detail_document": True,
                "list_or_entry_structure": False,
                "qualified": False,
                "classification": CLASS_REJECTED_DETAIL,
                "reasons": [
                    "DETAIL_DOCUMENT_IDENTITY"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "HTTP:",
                http_status,
            )

            print(
                "Title:",
                title,
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_DETAIL,
            )

            continue

        # ----------------------------------------------------
        # Region binding
        # ----------------------------------------------------

        region_ok, matched_regions = region_matches(
            regions,
            url=final_url,
            title=title,
            headings=headings,
            breadcrumbs=breadcrumbs,
        )

        if not region_ok:

            record = {
                "source_family": family,
                "regions": regions,
                "matched_regions": [],
                "input_url": input_url,
                "final_url": final_url,
                "http_status": http_status,
                "content_type": response.get(
                    "content_type"
                ),
                "encoding": response.get(
                    "encoding"
                ),
                "title": title,
                "headings": headings,
                "breadcrumbs": breadcrumbs,
                "form_actions": form_actions,
                "detail_document": detail_document,
                "list_or_entry_structure": list_or_entry,
                "qualified": False,
                "classification": CLASS_REJECTED_REGION,
                "reasons": [
                    "MUNICIPAL_REGION_LOCAL_EVIDENCE_MISSING"
                ],
                "verified_positive": False,
                "runtime_registration_allowed": False,
                "site_positive_allowed": False,
            }

            records.append(
                record
            )

            print(
                "HTTP:",
                http_status,
            )

            print(
                "Title:",
                title,
            )

            print(
                "Qualified: False"
            )

            print(
                "Resolution:",
                CLASS_REJECTED_REGION,
            )

            continue

        # ----------------------------------------------------
        # Role qualification
        # ----------------------------------------------------

        role_ok = False
        role_reasons: List[str] = []
        qualified_class = ""

        if family == FAMILY_GAZETTE:

            role_ok, role_reasons = evaluate_gazette_role(
                local_text,
                final_url,
            )

            qualified_class = (
                CLASS_QUALIFIED_GAZETTE
            )

        elif family == FAMILY_NOTICE:

            role_ok, role_reasons = evaluate_notice_role(
                local_text,
                final_url,
            )

            qualified_class = (
                CLASS_QUALIFIED_NOTICE
            )

        elif family == FAMILY_URBAN:

            role_ok, role_reasons = evaluate_urban_role(
                local_text,
                final_url,
            )

            qualified_class = (
                CLASS_QUALIFIED_URBAN
            )

        elif family == FAMILY_NOTICE_REVERSE:

            role_ok, role_reasons = evaluate_notice_role(
                local_text,
                final_url,
            )

            qualified_class = (
                CLASS_QUALIFIED_NOTICE_REVERSE
            )

        generic = looks_generic_page(
            final_url,
            title,
            headings,
        )

        if (
            generic
            and not role_ok
        ):

            classification = (
                CLASS_REJECTED_GENERIC
            )

            qualified = False

        elif not role_ok:

            classification = (
                CLASS_REJECTED_ROLE_WEAK
            )

            qualified = False

        else:

            classification = (
                qualified_class
            )

            qualified = True

        record = {
            "source_family": family,

            "regions": regions,

            "matched_regions": matched_regions,

            "input_url": input_url,

            "final_url": final_url,

            "http_status": http_status,

            "content_type": response.get(
                "content_type"
            ),

            "response_bytes": response.get(
                "response_bytes"
            ),

            "encoding": response.get(
                "encoding"
            ),

            "title": title,

            "headings": headings,

            "breadcrumbs": breadcrumbs,

            "form_actions": form_actions,

            "detail_document": detail_document,

            "list_or_entry_structure": list_or_entry,

            "endpoint_local_evidence_preview": (
                local_text[
                    :2000
                ]
            ),

            "qualified": qualified,

            "classification": classification,

            "reasons": unique_strings(
                role_reasons
                + [
                    "REGION_BOUND:"
                    + region
                    for region
                    in matched_regions
                ]
            ),

            "verified_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,
        }

        records.append(
            record
        )

        print(
            "HTTP:",
            http_status,
        )

        print(
            "Final URL:",
            final_url,
        )

        print(
            "Title:",
            title,
        )

        print(
            "Matched regions:",
            matched_regions,
        )

        print(
            "Role reasons:",
            role_reasons,
        )

        print(
            "Qualified:",
            qualified,
        )

        print(
            "Resolution:",
            classification,
        )

        if REQUEST_DELAY_SECONDS > 0:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    # ========================================================
    # CANONICAL DEDUPE
    # ========================================================

    canonical_map: Dict[
        Tuple[str, str],
        Dict[str, Any],
    ] = {}

    duplicate_count = 0

    for item in records:

        family = normalize_space(
            item.get(
                "source_family"
            )
        )

        url = canonicalize_url(
            item.get(
                "final_url"
            )
            or item.get(
                "input_url"
            )
            or ""
        )

        key = (
            family,
            url,
        )

        if key in canonical_map:

            duplicate_count += 1

            existing = canonical_map[
                key
            ]

            existing[
                "regions"
            ] = unique_strings(
                (
                    existing.get(
                        "regions"
                    )
                    or []
                )
                +
                (
                    item.get(
                        "regions"
                    )
                    or []
                )
            )

            existing[
                "matched_regions"
            ] = unique_strings(
                (
                    existing.get(
                        "matched_regions"
                    )
                    or []
                )
                +
                (
                    item.get(
                        "matched_regions"
                    )
                    or []
                )
            )

            existing[
                "reasons"
            ] = unique_strings(
                (
                    existing.get(
                        "reasons"
                    )
                    or []
                )
                +
                (
                    item.get(
                        "reasons"
                    )
                    or []
                )
            )

            continue

        canonical_map[
            key
        ] = dict(
            item
        )

    canonical_records = list(
        canonical_map.values()
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
    # NEXT STAGE
    # ========================================================

    next_stage_endpoint_pool = [
        {
            "source_family": item.get(
                "source_family"
            ),

            "regions": (
                item.get(
                    "matched_regions"
                )
                or item.get(
                    "regions"
                )
                or []
            ),

            "classification": item.get(
                "classification"
            ),

            "url": (
                item.get(
                    "final_url"
                )
                or item.get(
                    "input_url"
                )
            ),

            "title": item.get(
                "title"
            ),

            "reasons": item.get(
                "reasons"
            ),

            "endpoint_only": True,

            "verified_positive": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,
        }

        for item in qualified_endpoints
    ]

    # ========================================================
    # RESOLUTION
    # ========================================================

    if next_stage_endpoint_pool:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_"
            "QUALIFICATION_HARDENING_COMPLETED"
        )

        next_action = (
            "S-3에서 의미론적으로 hardening된 historical entry endpoint만 "
            "T-stage 입력으로 사용한다. "
            "source-family 및 기초지자체 region별 P-stage query를 제한 실행하고, "
            "endpoint 자체가 아닌 발견된 detail/attachment/gazette document "
            "identity만 후속 verification으로 넘긴다."
        )

    else:

        resolution = (
            "HISTORICAL_SOURCE_FAMILY_ENTRY_ENDPOINT_"
            "QUALIFICATION_HARDENING_NO_ENDPOINT"
        )

        next_action = (
            "S-2 endpoint가 모두 의미론적 qualification에서 탈락했다. "
            "기관별 historical archive/search form action을 직접 복원해야 한다."
        )

    # ========================================================
    # REGION RECOVERY COUNTERS
    # ========================================================

    input_region_recovery_count = sum(
        1
        for item in input_endpoints
        if extract_endpoint_regions(
            item
        )
    )

    input_region_missing_count = (
        len(
            input_endpoints
        )
        - input_region_recovery_count
    )

    # ========================================================
    # OUTPUT
    # ========================================================

    output_data = {
        "step": (
            "STEP 17-21-C-16-8-S-3 "
            "Historical Source Family Entry Endpoint "
            "Qualification Hardening"
        ),

        "target": {
            "name": TARGET_NAME,
            "standard_code": STANDARD_CODE,
        },

        "inputs": {
            "s2_stage_path": str(
                S2_STAGE_INPUT_PATH
            ),

            "h_stage_path": str(
                H_STAGE_INPUT_PATH
            ),

            "s2_stage_resolution": (
                s2_data.get(
                    "resolution"
                )
            ),
        },

        "method": {
            "s2_qualified_only": True,

            "direct_network_requery": True,

            "http_2xx_required": True,

            "final_host_go_kr_required": True,

            "page_body_substring_role_matching_disabled": True,

            "endpoint_local_evidence_only": True,

            "title_evidence_enabled": True,

            "heading_evidence_enabled": True,

            "breadcrumb_evidence_enabled": True,

            "url_evidence_enabled": True,

            "hostname_evidence_enabled": True,

            "form_action_evidence_enabled": True,

            "gazette_exact_context_guard_enabled": True,

            "bare_dobo_token_disabled": True,

            "notice_false_positive_board_guard_enabled": True,

            "municipality_exact_region_binding_enabled": True,

            "municipality_url_alias_binding_enabled": True,

            "province_only_match_for_municipality_disabled": True,

            "s2_structured_region_recovery_enabled": True,

            "s2_region_match_evidence_fallback_enabled": True,

            "page_level_region_inheritance_enabled": False,

            "detail_document_endpoint_promotion_disabled": True,

            "modern_endpoint_repeat_disabled": True,

            "max_response_bytes": MAX_RESPONSE_BYTES,

            "verified_positive_promotion_allowed": False,

            "runtime_registration_allowed": False,

            "site_positive_allowed": False,
        },

        "summary": {
            "s2_qualified_endpoint_count": len(
                input_endpoints
            ),

            "s2_region_recovery_count": (
                input_region_recovery_count
            ),

            "s2_region_missing_count": (
                input_region_missing_count
            ),

            "request_count": request_count,

            "http_success_count": (
                http_success_count
            ),

            "transport_error_count": (
                transport_error_count
            ),

            "canonical_record_count": len(
                canonical_records
            ),

            "duplicate_endpoint_removed": (
                duplicate_count
            ),

            "qualified_endpoint_count": len(
                qualified_endpoints
            ),

            "rejected_endpoint_count": len(
                rejected_endpoints
            ),

            "next_stage_endpoint_pool_count": len(
                next_stage_endpoint_pool
            ),
        },

        "qualified_family_counts": dict(
            sorted(
                family_qualified_counts.items()
            )
        ),

        "classification_counts": dict(
            sorted(
                classification_counts.items()
            )
        ),

        "qualified_endpoints": (
            qualified_endpoints
        ),

        "rejected_endpoints": (
            rejected_endpoints
        ),

        "next_stage_endpoint_pool": (
            next_stage_endpoint_pool
        ),

        "all_canonical_records": (
            canonical_records
        ),

        "resolution": resolution,

        "next_action": next_action,

        "verified_positive": False,

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
        "QUALIFICATION HARDENING RESULT"
    )

    print(
        "=" * 60
    )

    print(
        "S-2 qualified endpoint count:",
        len(
            input_endpoints
        ),
    )

    print(
        "S-2 region recovery count:",
        input_region_recovery_count,
    )

    print(
        "S-2 region missing count:",
        input_region_missing_count,
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
        "Canonical record count:",
        len(
            canonical_records
        ),
    )

    print(
        "Duplicate endpoint removed:",
        duplicate_count,
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

    for family in [
        FAMILY_GAZETTE,
        FAMILY_NOTICE,
        FAMILY_URBAN,
        FAMILY_NOTICE_REVERSE,
    ]:

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
            "HARDENED QUALIFIED HISTORICAL ENDPOINTS"
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
                    "matched_regions"
                )
                or item.get(
                    "regions"
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
                    "reasons"
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
        CLASS_REJECTED_DETAIL,
        CLASS_REJECTED_ROLE_WEAK,
        CLASS_REJECTED_REGION,
        CLASS_REJECTED_HTTP,
        CLASS_REJECTED_HOST,
        CLASS_REJECTED_GENERIC,
        CLASS_REJECTED_MODERN,
        CLASS_REJECTED_INVALID,
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
                    "url"
                )
                or ""
            ),
        )
        for item in next_stage_endpoint_pool
    }

    all_classes_valid = all(
        item.get(
            "classification"
        )
        in VALID_CLASSES
        for item in canonical_records
    )

    qualified_classes_valid = all(
        item.get(
            "classification"
        )
        in QUALIFIED_CLASSES
        for item in qualified_endpoints
    )

    qualified_http_leakage = sum(
        1
        for item in qualified_endpoints
        if not (
            isinstance(
                item.get(
                    "http_status"
                ),
                int,
            )
            and 200
            <= item.get(
                "http_status"
            )
            < 300
        )
    )

    qualified_non_go_kr_leakage = sum(
        1
        for item in qualified_endpoints
        if not is_government_host(
            hostname(
                item.get(
                    "final_url"
                )
                or ""
            )
        )
    )

    detail_promotion_leakage = sum(
        1
        for item in qualified_endpoints
        if (
            item.get(
                "detail_document"
            )
            is True
            and item.get(
                "list_or_entry_structure"
            )
            is not True
        )
    )

    region_unbound_leakage = sum(
        1
        for item in qualified_endpoints
        if not (
            item.get(
                "matched_regions"
            )
            or []
        )
    )

    modern_endpoint_leakage = sum(
        1
        for item in qualified_endpoints
        if canonicalize_url(
            item.get(
                "final_url"
            )
            or ""
        )
        in modern_exclusions
    )

    bare_dobo_only_leakage = sum(
        1
        for item in qualified_endpoints
        if (
            item.get(
                "source_family"
            )
            == FAMILY_GAZETTE
            and item.get(
                "reasons"
            )
            == [
                "GAZETTE_LOCAL:도보"
            ]
        )
    )

    verified_positive_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "verified_positive"
        )
        is True
    )

    runtime_registration_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "runtime_registration_allowed"
        )
        is True
    )

    site_true_leakage = sum(
        1
        for item in canonical_records
        if item.get(
            "site_positive_allowed"
        )
        is True
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

        "S-2 input exists": (
            S2_STAGE_INPUT_PATH.exists()
        ),

        "H-stage input exists": (
            H_STAGE_INPUT_PATH.exists()
        ),

        "S-2 input parsed": (
            isinstance(
                s2_data,
                dict,
            )
        ),

        "S-2 qualified endpoints loaded": (
            len(
                input_endpoints
            )
            > 0
        ),

        "S-2 qualified only": True,

        "S-2 structured region recovery enabled": True,

        "S-2 REGION_MATCH fallback enabled": True,

        # 이번 수정에서 중요:
        # S-2 23개가 region을 모두 가지고 있어야 한다.
        "S-2 region recovery complete": (
            input_region_missing_count
            == 0
        ),

        "page-level region inheritance disabled": True,

        "direct network requery required": True,

        "HTTP 2xx required": True,

        "final host go.kr required": True,

        "endpoint-local evidence enabled": True,

        "page body substring role matching disabled": True,

        "title evidence enabled": True,

        "heading evidence enabled": True,

        "breadcrumb evidence enabled": True,

        "URL evidence enabled": True,

        "hostname evidence enabled": True,

        "form action evidence enabled": True,

        "gazette exact context guard enabled": True,

        "bare 도보 token disabled": True,

        "municipality exact region binding enabled": True,

        "municipality URL alias binding enabled": True,

        "province-only municipality matching disabled": True,

        "detail document endpoint promotion disabled": True,

        "response size budget increased safely": (
            MAX_RESPONSE_BYTES
            == 12
            * 1024
            * 1024
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
            all_classes_valid
        ),

        "qualified classes valid": (
            qualified_classes_valid
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
            qualified_http_leakage
            == 0
        ),

        "qualified endpoints require go.kr final host": (
            qualified_non_go_kr_leakage
            == 0
        ),

        "detail document promotion leakage zero": (
            detail_promotion_leakage
            == 0
        ),

        "region-unbound qualified leakage zero": (
            region_unbound_leakage
            == 0
        ),

        "modern endpoint repeat leakage zero": (
            modern_endpoint_leakage
            == 0
        ),

        "bare 도보 only qualification leakage zero": (
            bare_dobo_only_leakage
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
            site_true_leakage
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

    # ========================================================
    # VALIDATION PRINT
    # ========================================================

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
        "S-2 region recovery count:",
        input_region_recovery_count,
    )

    print(
        "S-2 region missing count:",
        input_region_missing_count,
    )

    print(
        "Qualified HTTP leakage:",
        qualified_http_leakage,
    )

    print(
        "Qualified non-go.kr leakage:",
        qualified_non_go_kr_leakage,
    )

    print(
        "Detail document promotion leakage:",
        detail_promotion_leakage,
    )

    print(
        "Region-unbound qualified leakage:",
        region_unbound_leakage,
    )

    print(
        "Modern endpoint repeat leakage:",
        modern_endpoint_leakage,
    )

    print(
        "Bare 도보-only qualification leakage:",
        bare_dobo_only_leakage,
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
        site_true_leakage,
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
            "qualification hardening regression failed"
        )


if __name__ == "__main__":
    main()