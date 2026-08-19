# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-4A-2A
토지이음 개발밀도관리구역 명칭 / 코드체계 탐색 보정

목표
--------------------------------------------------
1. 토지이음 용어사전 pagination을 실제 순회한다.
2. '개발밀도관리구역' 용어가 공식 HTML에 존재하는지 확인한다.
3. 용어 주변의 링크 / onclick / hidden value 등을 수집한다.
4. 식별자 후보가 보여도 자동으로 공식 코드로 확정하지 않는다.
5. geometry source가 확보되지 않았으므로 SITE는 UNKNOWN 유지한다.

중요
--------------------------------------------------
- searchKeyword / keyword 등 검색 parameter를 추측하지 않는다.
- 페이지 번호 순회 방식으로 실제 HTML에서 용어를 찾는다.
- 단순 숫자, pageNo, listSize 등을 지역·지구 코드로 오인하지 않는다.
- geometry가 없으면 TRUE/FALSE 판정을 절대 하지 않는다.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests


# ============================================================
# 프로젝트 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

INPUT_PATH = (
    OUTPUT_DIR
    / "national_development_density_control_area_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "eum_development_density_control_area_code_probe.json"
)


# ============================================================
# 대상 조건
# ============================================================

TARGET_KEYWORD = "개발밀도관리구역"


# ============================================================
# 토지이음 URL
# ============================================================

EUM_BASE_URL = "https://www.eum.go.kr"

DICT_LIST_URL = (
    EUM_BASE_URL
    + "/web/in/dc/dcDictList.jsp"
)


# ============================================================
# HTTP 설정
# ============================================================

REQUEST_TIMEOUT = 20

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
        "image/avif,"
        "image/webp,"
        "*/*;q=0.8"
    ),
    "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    "Referer": "https://www.eum.go.kr/",
    "Connection": "keep-alive",
}


# ============================================================
# 데이터 클래스
# ============================================================

@dataclass
class HttpResult:
    url: str
    http_status: Optional[int]
    ok: bool
    text: str
    final_url: str
    error: Optional[str]


# ============================================================
# 공통 유틸
# ============================================================

def load_json(path: Path) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다:\n{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Dict[str, Any],
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(value)

    text = (
        text.replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
        .replace("&nbsp;", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def first_nonempty(
    *values: Any,
) -> Any:

    for value in values:

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


def dig(
    data: Any,
    *keys: str,
) -> Any:

    current = data

    for key in keys:

        if not isinstance(
            current,
            dict,
        ):
            return None

        current = current.get(key)

    return current


# ============================================================
# SITE context 복원
# ============================================================

def extract_site_context(
    source: Dict[str, Any],
) -> Dict[str, Any]:

    """
    이전 단계 JSON schema가 약간 달라도
    가능한 범위에서 SITE context를 복원한다.
    """

    candidates = [
        source,
        source.get("site", {}),
        source.get("site_context", {}),
        source.get("query_context", {}),
        source.get("target_site", {}),
        source.get("input", {}),
    ]

    site_id = None
    address = None
    zoning = None
    pnu = None

    for item in candidates:

        if not isinstance(
            item,
            dict,
        ):
            continue

        site_id = first_nonempty(
            site_id,
            item.get("site_id"),
            item.get("SITE_ID"),
            item.get("parcel_key"),
        )

        address = first_nonempty(
            address,
            item.get("address"),
            item.get("jibun_address"),
            item.get("주소"),
        )

        zoning = first_nonempty(
            zoning,
            item.get("zoning"),
            item.get("use_zone"),
            item.get("land_use_zone"),
            item.get("용도지역"),
        )

        pnu = first_nonempty(
            pnu,
            item.get("pnu"),
            item.get("PNU"),
        )

    # nested 결과에서 추가 탐색
    if not pnu:

        pnu = first_nonempty(
            dig(
                source,
                "site",
                "pnu",
            ),
            dig(
                source,
                "query_context",
                "pnu",
            ),
            dig(
                source,
                "target_site",
                "pnu",
            ),
        )

    # site_id → PNU 복원
    #
    # SITE ID:
    # 11680-10300-0012-0000
    #
    # PNU:
    # 11680 + 10300 + 1 + 0012 + 0000
    #
    if (
        not pnu
        and isinstance(
            site_id,
            str,
        )
    ):

        match = re.fullmatch(
            r"(\d{5})-(\d{5})-(\d{4})-(\d{4})",
            site_id.strip(),
        )

        if match:

            sigungu = match.group(1)
            bjdong = match.group(2)
            main_no = match.group(3)
            sub_no = match.group(4)

            # 현재 프로젝트에서는 일반번지를 1로 사용
            pnu = (
                sigungu
                + bjdong
                + "1"
                + main_no
                + sub_no
            )

    return {
        "site_id": site_id or "-",
        "address": address or "-",
        "zoning": zoning or "-",
        "pnu": str(pnu) if pnu else "-",
    }


# ============================================================
# HTTP
# ============================================================

def get_html(
    session: requests.Session,
    url: str,
    params: Optional[
        Dict[str, Any]
    ] = None,
) -> HttpResult:

    try:

        response = session.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT,
        )

        # requests가 encoding을 잘못 잡는 경우 보정
        if not response.encoding:

            response.encoding = (
                response.apparent_encoding
                or "utf-8"
            )

        text = response.text

        return HttpResult(
            url=response.url,
            http_status=response.status_code,
            ok=(
                response.status_code
                == 200
            ),
            text=text,
            final_url=response.url,
            error=None,
        )

    except requests.RequestException as exc:

        return HttpResult(
            url=url,
            http_status=None,
            ok=False,
            text="",
            final_url=url,
            error=str(exc),
        )


# ============================================================
# 용어사전 page scan
# ============================================================

def search_dictionary(
    session: requests.Session,
) -> Dict[str, Any]:

    """
    토지이음 용어사전을 pageNo 방식으로 순회한다.

    검색 parameter를 추측하지 않는다.
    """

    attempts: List[
        Dict[str, Any]
    ] = []

    best: Optional[
        Dict[str, Any]
    ] = None

    # 코드가 특정 페이지에 의존하지 않도록
    # 충분한 범위를 순회한다.
    MAX_PAGE = 100

    for page_no in range(
        1,
        MAX_PAGE + 1,
    ):

        params = {
            "listSize": 8,
            "pageNo": page_no,
        }

        response = get_html(
            session,
            DICT_LIST_URL,
            params=params,
        )

        normalized = normalize_text(
            response.text
        )

        keyword_found = (
            TARGET_KEYWORD
            in normalized
        )

        item = {
            "page_no": page_no,
            "params": params,
            "request_url":
                response.url,
            "final_url":
                response.final_url,
            "http_status":
                response.http_status,
            "ok":
                response.ok,
            "keyword_found":
                keyword_found,
            "text_preview":
                normalized[:1500],
            "error":
                response.error,
        }

        attempts.append(item)

        print(
            f"page {page_no:3d}"
            f" | HTTP="
            f"{response.http_status}"
            f" | keyword="
            f"{keyword_found}"
        )

        if keyword_found:

            item["raw_html"] = (
                response.text
            )

            best = item
            break

    return {
        "attempts": attempts,
        "best": best,
    }


# ============================================================
# HTML 구조 분석
# ============================================================

def extract_keyword_contexts(
    html: str,
    keyword: str,
    radius: int = 500,
) -> List[str]:

    contexts: List[str] = []

    if not html:
        return contexts

    for match in re.finditer(
        re.escape(keyword),
        html,
        flags=re.IGNORECASE,
    ):

        start = max(
            0,
            match.start() - radius,
        )

        end = min(
            len(html),
            match.end() + radius,
        )

        context = normalize_text(
            html[start:end]
        )

        if (
            context
            and context
            not in contexts
        ):
            contexts.append(
                context
            )

    return contexts


def extract_target_links(
    html: str,
    keyword: str,
) -> List[Dict[str, Any]]:

    """
    BeautifulSoup 없이도 실행 가능하도록
    anchor 태그를 정규식으로 분석한다.

    링크 자체를 '공식 코드'라고 보지 않는다.
    """

    results: List[
        Dict[str, Any]
    ] = []

    if not html:
        return results

    anchor_pattern = re.compile(
        r"<a\b(?P<attrs>[^>]*)>"
        r"(?P<body>.*?)"
        r"</a>",
        flags=(
            re.IGNORECASE
            | re.DOTALL
        ),
    )

    href_pattern = re.compile(
        r"""href\s*=\s*
        (?:
            "([^"]*)"
            |
            '([^']*)'
            |
            ([^\s>]+)
        )
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    onclick_pattern = re.compile(
        r"""onclick\s*=\s*
        (?:
            "([^"]*)"
            |
            '([^']*)'
        )
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    for match in anchor_pattern.finditer(
        html
    ):

        attrs = match.group(
            "attrs"
        )

        body = match.group(
            "body"
        )

        body_text = normalize_text(
            re.sub(
                r"<[^>]+>",
                " ",
                body,
            )
        )

        whole_anchor = (
            match.group(0)
        )

        if (
            keyword not in body_text
            and keyword
            not in whole_anchor
        ):
            continue

        href_match = (
            href_pattern.search(
                attrs
            )
        )

        onclick_match = (
            onclick_pattern.search(
                attrs
            )
        )

        href = None
        onclick = None

        if href_match:

            href = first_nonempty(
                href_match.group(1),
                href_match.group(2),
                href_match.group(3),
            )

        if onclick_match:

            onclick = first_nonempty(
                onclick_match.group(1),
                onclick_match.group(2),
            )

        absolute_href = None

        if (
            href
            and not href.lower().startswith(
                "javascript:"
            )
            and href != "#"
        ):

            absolute_href = urljoin(
                EUM_BASE_URL,
                href,
            )

        results.append(
            {
                "text": body_text,
                "href": href,
                "absolute_href":
                    absolute_href,
                "onclick": onclick,
                "raw":
                    normalize_text(
                        whole_anchor
                    )[:2000],
            }
        )

    return results


def extract_hidden_values(
    html: str,
    contexts: List[str],
) -> List[Dict[str, str]]:

    """
    keyword 주변 HTML에 hidden input이 존재하는 경우 기록한다.

    단, hidden value를 곧바로 개발밀도관리구역 공식 코드로
    인정하지 않는다.
    """

    results: List[
        Dict[str, str]
    ] = []

    source = "\n".join(
        contexts
    )

    if not source:
        return results

    pattern = re.compile(
        r"""<input\b
        (?=[^>]*type\s*=\s*["']?hidden["']?)
        (?P<attrs>[^>]*)>
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    name_pattern = re.compile(
        r"""name\s*=\s*
        (?:
            "([^"]*)"
            |
            '([^']*)'
            |
            ([^\s>]+)
        )
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    value_pattern = re.compile(
        r"""value\s*=\s*
        (?:
            "([^"]*)"
            |
            '([^']*)'
            |
            ([^\s>]+)
        )
        """,
        flags=(
            re.IGNORECASE
            | re.VERBOSE
        ),
    )

    for match in pattern.finditer(
        source
    ):

        attrs = match.group(
            "attrs"
        )

        name_match = (
            name_pattern.search(
                attrs
            )
        )

        value_match = (
            value_pattern.search(
                attrs
            )
        )

        name = None
        value = None

        if name_match:

            name = first_nonempty(
                name_match.group(1),
                name_match.group(2),
                name_match.group(3),
            )

        if value_match:

            value = first_nonempty(
                value_match.group(1),
                value_match.group(2),
                value_match.group(3),
            )

        if name or value:

            item = {
                "name": name or "",
                "value": value or "",
            }

            if item not in results:
                results.append(item)

    return results


# ============================================================
# 식별자 후보 추출
# ============================================================

def extract_identifier_candidates(
    contexts: List[str],
    links: List[
        Dict[str, Any]
    ],
) -> List[Dict[str, Any]]:

    """
    keyword 주변 HTML / href / onclick에서
    식별자로 보이는 값을 '후보'로만 수집한다.

    중요:
    이것은 verified_code가 아니다.
    """

    candidates: List[
        Dict[str, Any]
    ] = []

    texts: List[
        Dict[str, str]
    ] = []

    for index, context in enumerate(
        contexts,
        start=1,
    ):

        texts.append(
            {
                "source":
                    f"context_{index}",
                "text": context,
            }
        )

    for index, link in enumerate(
        links,
        start=1,
    ):

        for field in (
            "href",
            "onclick",
            "raw",
        ):

            value = link.get(
                field
            )

            if value:

                texts.append(
                    {
                        "source":
                            f"link_{index}_{field}",
                        "text":
                            str(value),
                    }
                )

    patterns = [
        # UQ 계열 코드
        (
            "UQ_CODE",
            re.compile(
                r"\bUQ\d{2,4}\b",
                re.IGNORECASE,
            ),
        ),

        # LT_C_* 형식
        (
            "LAYER_ID",
            re.compile(
                r"\bLT_C_[A-Z0-9_]+\b",
                re.IGNORECASE,
            ),
        ),

        # UQ 관리번호 계열
        (
            "UPIS_MANAGEMENT_ID",
            re.compile(
                r"\b\d{5}UQ\d{3}"
                r"[A-Z]{2}"
                r"\d{8,20}\b",
                re.IGNORECASE,
            ),
        ),

        # NTC 고시번호 계열
        (
            "NOTICE_MANAGEMENT_ID",
            re.compile(
                r"\b\d{5}NTC"
                r"\d{8,20}\b",
                re.IGNORECASE,
            ),
        ),

        # DSZ 관리코드 계열
        (
            "DISTRICT_MANAGEMENT_ID",
            re.compile(
                r"\b\d{5}DSZ"
                r"\d{8,20}\b",
                re.IGNORECASE,
            ),
        ),
    ]

    seen = set()

    for source in texts:

        text = source["text"]

        for kind, pattern in patterns:

            for match in pattern.finditer(
                text
            ):

                value = (
                    match.group(0)
                    .strip()
                )

                key = (
                    kind,
                    value.upper(),
                )

                if key in seen:
                    continue

                seen.add(key)

                candidates.append(
                    {
                        "type": kind,
                        "value": value,
                        "source":
                            source[
                                "source"
                            ],
                        "verified":
                            False,
                        "note": (
                            "HTML에서 추출된 "
                            "식별자 후보이며 "
                            "공식 개발밀도관리구역 "
                            "코드로 확정하지 않음"
                        ),
                    }
                )

    return candidates


# ============================================================
# 분석
# ============================================================

def analyze_dictionary_result(
    search_result: Dict[str, Any],
) -> Dict[str, Any]:

    best = search_result.get(
        "best"
    )

    if not best:

        return {
            "term_found": False,
            "found_page": None,
            "target_links": [],
            "keyword_contexts": [],
            "hidden_values": [],
            "identifier_candidates": [],
            "verified_code": None,
            "source_status":
                "TERM_SEARCH_FAILED",
            "reason": (
                "토지이음 용어사전 페이지를 "
                "순회했으나 현재 자동 조회에서는 "
                "개발밀도관리구역 문자열을 "
                "직접 검출하지 못함"
            ),
        }

    html = best.get(
        "raw_html",
        "",
    )

    contexts = (
        extract_keyword_contexts(
            html,
            TARGET_KEYWORD,
        )
    )

    links = (
        extract_target_links(
            html,
            TARGET_KEYWORD,
        )
    )

    hidden_values = (
        extract_hidden_values(
            html,
            contexts,
        )
    )

    identifier_candidates = (
        extract_identifier_candidates(
            contexts,
            links,
        )
    )

    # 여기서는 절대 자동확정하지 않는다.
    verified_code = None

    if identifier_candidates:

        source_status = (
            "TERM_CONFIRMED_"
            "IDENTIFIER_CANDIDATE"
        )

        reason = (
            "토지이음 공식 용어사전 HTML에서 "
            "개발밀도관리구역 명칭을 확인했고 "
            "주변 HTML에서 식별자 후보도 "
            "추출했으나 해당 값이 "
            "개발밀도관리구역 공식 공간관리 "
            "코드라는 의미 검증은 완료되지 않음"
        )

    else:

        source_status = (
            "TERM_CONFIRMED"
        )

        reason = (
            "토지이음 공식 용어사전 HTML에서 "
            "개발밀도관리구역 명칭을 확인했으나 "
            "공식 지역·지구 코드로 확정할 수 있는 "
            "식별자는 아직 확보하지 못함"
        )

    return {
        "term_found": True,
        "found_page":
            best.get(
                "page_no"
            ),
        "request_params":
            best.get(
                "params"
            ),
        "request_url":
            best.get(
                "request_url"
            ),
        "final_url":
            best.get(
                "final_url"
            ),
        "target_links":
            links,
        "keyword_contexts":
            contexts,
        "hidden_values":
            hidden_values,
        "identifier_candidates":
            identifier_candidates,
        "verified_code":
            verified_code,
        "source_status":
            source_status,
        "reason":
            reason,
    }


# ============================================================
# SITE 판정
# ============================================================

def build_site_resolution(
    analysis: Dict[str, Any],
) -> Dict[str, Any]:

    if analysis.get(
        "term_found"
    ):

        reason = (
            "토지이음 공식 용어사전 HTML에서 "
            "개발밀도관리구역 명칭을 확인했으나 "
            "공식 지역·지구 코드와 "
            "공간 geometry source가 아직 "
            "확정되지 않았으므로 대상 필지의 "
            "TRUE/FALSE를 판정하지 않음"
        )

    else:

        reason = (
            "토지이음 공식 용어사전에 대한 "
            "자동 조회에서 개발밀도관리구역 "
            "항목을 아직 직접 검출하지 못했고 "
            "공식 지역·지구 코드 및 "
            "공간 geometry source도 "
            "확정되지 않았으므로 대상 필지의 "
            "TRUE/FALSE를 판정하지 않음"
        )

    return {
        "condition":
            TARGET_KEYWORD,
        "query_status":
            "NOT_CONNECTED",
        "resolution":
            "UNKNOWN",
        "confidence":
            "NONE",
        "reason":
            reason,
        "evidence":
            [],
    }


# ============================================================
# 검증
# ============================================================

def build_validation(
    site: Dict[str, Any],
    search_result: Dict[str, Any],
    analysis: Dict[str, Any],
    resolution: Dict[str, Any],
) -> Dict[str, bool]:

    attempts = (
        search_result.get(
            "attempts",
            [],
        )
    )

    term_found = bool(
        analysis.get(
            "term_found"
        )
    )

    return {
        "PNU 19자리":
            (
                isinstance(
                    site.get("pnu"),
                    str,
                )
                and len(
                    site.get("pnu", "")
                )
                == 19
                and site[
                    "pnu"
                ].isdigit()
            ),

        "토지이음 검색 실행":
            len(attempts) > 0,

        "개발밀도관리구역 용어 존재 확인":
            term_found,

        "코드 추측 자동확정 없음":
            (
                analysis.get(
                    "verified_code"
                )
                is None
            ),

        "geometry 미확정 TRUE 금지":
            (
                resolution.get(
                    "resolution"
                )
                != "TRUE"
            ),

        "geometry 미확정 FALSE 금지":
            (
                resolution.get(
                    "resolution"
                )
                != "FALSE"
            ),

        "SITE UNKNOWN 유지":
            (
                resolution.get(
                    "resolution"
                )
                == "UNKNOWN"
            ),
    }


def print_validation(
    validation: Dict[str, bool],
) -> None:

    for name, passed in (
        validation.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{name}: {status}"
        )


# ============================================================
# main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-4A-2A "
        "토지이음 개발밀도관리구역 "
        "명칭 / 코드체계 탐색 보정 ==="
    )

    print()

    print(
        "입력:"
    )
    print(
        INPUT_PATH
    )

    source = load_json(
        INPUT_PATH
    )

    site = extract_site_context(
        source
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== 대상 SITE ==="
    )
    print(
        "=" * 70
    )

    print(
        f"SITE ID: "
        f"{site['site_id']}"
    )

    print(
        f"주소: "
        f"{site['address']}"
    )

    print(
        f"용도지역: "
        f"{site['zoning']}"
    )

    print(
        f"PNU: "
        f"{site['pnu']}"
    )

    # --------------------------------------------------------
    # 1. 용어사전 검색
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 1. 토지이음 용어사전 "
        "pagination 탐색 ==="
    )
    print(
        "=" * 70
    )

    session = requests.Session()

    search_result = (
        search_dictionary(
            session
        )
    )

    best = search_result.get(
        "best"
    )

    print()

    if best:

        print(
            "검색 성공: True"
        )

        print(
            "용어 발견 page:",
            best.get(
                "page_no"
            ),
        )

        print(
            "실제 요청 params:",
            best.get(
                "params"
            ),
        )

        print(
            "HTTP:",
            best.get(
                "http_status"
            ),
        )

    else:

        print(
            "검색 성공: False"
        )

    # --------------------------------------------------------
    # 2. HTML 분석
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 2. 개발밀도관리구역 "
        "HTML 구조 분석 ==="
    )
    print(
        "=" * 70
    )

    analysis = (
        analyze_dictionary_result(
            search_result
        )
    )

    print(
        "검색 성공:",
        analysis[
            "term_found"
        ],
    )

    print(
        "target link 수:",
        len(
            analysis[
                "target_links"
            ]
        ),
    )

    print(
        "keyword context 수:",
        len(
            analysis[
                "keyword_contexts"
            ]
        ),
    )

    print(
        "hidden value 수:",
        len(
            analysis[
                "hidden_values"
            ]
        ),
    )

    print(
        "식별자 후보 수:",
        len(
            analysis[
                "identifier_candidates"
            ]
        ),
    )

    # --------------------------------------------------------
    # 3. 상세 링크 후보
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 3. 상세페이지 / "
        "식별자 후보 분석 ==="
    )
    print(
        "=" * 70
    )

    links = analysis[
        "target_links"
    ]

    if links:

        for idx, link in enumerate(
            links,
            start=1,
        ):

            print()
            print(
                "-" * 70
            )

            print(
                f"Link {idx}"
            )

            print(
                "text:",
                link.get(
                    "text"
                )
                or "-",
            )

            print(
                "href:",
                link.get(
                    "href"
                )
                or "-",
            )

            print(
                "onclick:",
                link.get(
                    "onclick"
                )
                or "-",
            )

    else:

        print(
            "직접 조회 가능한 "
            "상세 링크 없음"
        )

    candidates = analysis[
        "identifier_candidates"
    ]

    if candidates:

        print()
        print(
            "식별자 후보:"
        )

        for idx, item in enumerate(
            candidates,
            start=1,
        ):

            print(
                f"{idx}. "
                f"{item['type']} "
                f"/ {item['value']} "
                f"/ verified=False"
            )

    # --------------------------------------------------------
    # 4. 코드 판정
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 4. 개발밀도관리구역 "
        "코드 판정 ==="
    )
    print(
        "=" * 70
    )

    verified_code = (
        analysis.get(
            "verified_code"
        )
    )

    print(
        "source_status:",
        analysis[
            "source_status"
        ],
    )

    print(
        "verified_code:",
        verified_code
        or "미확정",
    )

    print(
        "reason:",
        analysis[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # 5. SITE 판정
    # --------------------------------------------------------

    resolution = (
        build_site_resolution(
            analysis
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== 5. 현재 SITE 판정 ==="
    )
    print(
        "=" * 70
    )

    print(
        "query_status:",
        resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        resolution[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validation = (
        build_validation(
            site,
            search_result,
            analysis,
            resolution,
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== C-9-2-4A-2A 검증 ==="
    )
    print(
        "=" * 70
    )

    print_validation(
        validation
    )

    # --------------------------------------------------------
    # 결과 저장
    # --------------------------------------------------------

    output = {
        "step":
            "STEP 17-21-C-9-2-4A-2A",

        "condition":
            TARGET_KEYWORD,

        "site":
            site,

        "source": {
            "provider":
                "국토교통부",
            "service":
                "토지이음",
            "dictionary_url":
                DICT_LIST_URL,
        },

        "dictionary_search": {
            # raw_html은 결과 JSON을 불필요하게
            # 크게 만들지 않도록 제거
            "attempts": [
                {
                    key: value
                    for key, value
                    in item.items()
                    if key
                    != "raw_html"
                }
                for item
                in search_result.get(
                    "attempts",
                    [],
                )
            ],
            "found":
                bool(
                    search_result.get(
                        "best"
                    )
                ),
        },

        "analysis":
            analysis,

        "site_resolution":
            resolution,

        "validation":
            validation,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print(
        "=" * 70
    )
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print(
        "=" * 70
    )

    # --------------------------------------------------------
    # 최종 메시지
    # --------------------------------------------------------

    required_core = [
        validation[
            "PNU 19자리"
        ],
        validation[
            "토지이음 검색 실행"
        ],
        validation[
            "코드 추측 자동확정 없음"
        ],
        validation[
            "geometry 미확정 TRUE 금지"
        ],
        validation[
            "geometry 미확정 FALSE 금지"
        ],
        validation[
            "SITE UNKNOWN 유지"
        ],
    ]

    term_pass = validation[
        "개발밀도관리구역 용어 존재 확인"
    ]

    print()

    if (
        all(required_core)
        and term_pass
    ):

        print(
            "STEP 17-21-C-9-2-4A-2A 완료"
        )

        print()

        print(
            "토지이음 공식 용어사전에서 "
            "'개발밀도관리구역' 명칭을 "
            "직접 확인했습니다."
        )

        print()

        print(
            "현재 개발밀도관리구역:"
        )
        print(
            "UNKNOWN"
        )

        print()

        if candidates:

            print(
                "다음 단계:"
            )
            print(
                "STEP 17-21-C-9-2-4A-3"
            )
            print(
                "→ 검출된 용어 주변 HTML / "
                "onclick / 링크 식별자 의미 분석"
            )
            print(
                "→ 공식 지역·지구 관리코드 여부 검증"
            )
            print(
                "→ geometry source 연결 가능성 확인"
            )

        else:

            print(
                "공식 용어 존재는 확인됐지만 "
                "공간코드는 아직 미확정입니다."
            )

            print()

            print(
                "개발밀도관리구역은 UNKNOWN으로 "
                "보존하고 다음 공간조건 판정으로 "
                "진행할 수 있습니다."
            )

            print()

            print(
                "다음 우선 대상:"
            )
            print(
                "→ 자연경관지구"
            )

    else:

        print(
            "STEP 17-21-C-9-2-4A-2A "
            "검증 미완료"
        )

        print()

        if not term_pass:

            print(
                "토지이음 pagination 자동조회에서 "
                "'개발밀도관리구역' 문자열을 "
                "아직 직접 검출하지 못했습니다."
            )

        print()

        print(
            "코드나 SITE 상태를 "
            "임의 확정하지 않습니다."
        )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print()
        print(
            "사용자에 의해 중단되었습니다."
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 70
        )
        print(
            "ERROR"
        )
        print(
            "=" * 70
        )

        print(
            type(exc).__name__
            + ": "
            + str(exc)
        )

        raise