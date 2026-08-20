# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14F-1
서울기록원 과거 용도지역 / 개발제한구역 기록 source probe

목표
======================================================================
1. 서울기록원의 공식 기록 검색을 사용한다.
2. 다음 역사 source를 우선 탐색한다.

   - SR228 용도지역 설정 기록
   - SR172 개발제한구역 기록
   - SR143 택지개발사업 계획
   - SR119894 공동주택건설 기록 : 대치지구

3. 대치 / 개포 / 수서 관련 기록 제목을 수집한다.
4. 자연녹지 / 용도지역변경 / 개발제한구역 관련 기록을 우선한다.
5. 검색 결과 부재만으로 FALSE 판정하지 않는다.
6. 콘솔에는 핵심 후보만 출력한다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


STEP_NAME = (
    "STEP 17-21-C-9-2-14F-1 "
    "서울기록원 과거 용도지역/개발제한구역 기록 probe"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_historic_zoning_archive_probe.json"
)


# ============================================================
# 서울기록원
# ============================================================

BASE_URL = (
    "https://archives.seoul.go.kr"
)

SEARCH_URL = (
    "https://archives.seoul.go.kr/search"
)

TIMEOUT = 30

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": (
        "ko-KR,ko;q=0.9"
    ),
}


# ============================================================
# 검색어
# ============================================================

QUERIES = [
    "대치지구 용도지역",
    "대치 용도지역 변경",
    "개포동 용도지역",
    "개포 자연녹지",
    "대치 자연녹지",
    "수서 대치 자연녹지",
    "대치 개발제한구역",
    "개포 개발제한구역",
    "대치 택지개발예정지구",
]


TARGET_TERMS = [
    "대치",
    "개포",
    "수서",
]

ZONING_TERMS = [
    "용도지역",
    "자연녹지",
    "녹지지역",
    "개발제한구역",
    "택지개발",
    "예정지구",
    "지정",
    "변경",
    "해제",
]


# ============================================================
# util
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def compact(
    value: Any,
    limit: int = 250,
) -> str:

    text = re.sub(
        r"\s+",
        " ",
        safe_string(value),
    ).strip()

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
            default=str,
        )


# ============================================================
# 검색
# ============================================================

def request_search(
    query: str,
) -> Dict[str, Any]:

    # 서울기록원 검색 화면의 query parameter는
    # UI 변경 가능성이 있으므로 q/query/keyword를 함께 시도
    cases = [
        {"q": query},
        {"query": query},
        {"keyword": query},
    ]

    results = []

    for params in cases:

        try:

            response = requests.get(
                SEARCH_URL,
                params=params,
                headers=HEADERS,
                timeout=TIMEOUT,
            )

            results.append(
                {
                    "params": params,
                    "http_status": (
                        response.status_code
                    ),
                    "url": response.url,
                    "html": response.text,
                }
            )

        except Exception as exc:

            results.append(
                {
                    "params": params,
                    "http_status": None,
                    "url": SEARCH_URL,
                    "html": "",
                    "error": str(exc),
                }
            )

    return {
        "query": query,
        "cases": results,
    }


def extract_candidates(
    html: str,
    query: str,
) -> List[Dict[str, Any]]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    candidates = []

    for anchor in soup.find_all(
        "a"
    ):

        href = safe_string(
            anchor.get(
                "href"
            )
        )

        title = compact(
            anchor.get_text(
                " ",
                strip=True,
            ),
            220,
        )

        if not href or not title:
            continue

        # 서울기록원 기록/기록철 링크만 우선
        if not any(
            token in href
            for token in (
                "/item/",
                "/aggregation/",
                "/series/",
            )
        ):
            continue

        full_url = urljoin(
            BASE_URL,
            href,
        )

        text = title

        target_matches = [
            term
            for term
            in TARGET_TERMS
            if term in text
        ]

        zoning_matches = [
            term
            for term
            in ZONING_TERMS
            if term in text
        ]

        if not (
            target_matches
            or zoning_matches
        ):
            continue

        candidates.append(
            {
                "query": query,
                "title": title,
                "url": full_url,
                "target_terms": (
                    target_matches
                ),
                "zoning_terms": (
                    zoning_matches
                ),
            }
        )

    # URL 기준 중복 제거
    unique = {}

    for item in candidates:

        unique[
            item[
                "url"
            ]
        ] = item

    return list(
        unique.values()
    )


# ============================================================
# 후보 상세 조회
# ============================================================

def inspect_detail(
    candidate: Dict[str, Any],
) -> Dict[str, Any]:

    try:

        response = requests.get(
            candidate[
                "url"
            ],
            headers=HEADERS,
            timeout=TIMEOUT,
        )

        html = response.text

    except Exception as exc:

        return {
            **candidate,
            "http_status": None,
            "error": str(exc),
        }

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    text = compact(
        soup.get_text(
            " ",
            strip=True,
        ),
        3000,
    )

    terms = [
        term
        for term in (
            TARGET_TERMS
            + ZONING_TERMS
        )
        if term in text
    ]

    # 기록 식별번호 계열
    identifiers = sorted(
        set(
            re.findall(
                r"\b(?:RG|SR|FI|IT|VO)"
                r"[A-Za-z0-9\-]+",
                text,
            )
        )
    )

    return {
        **candidate,
        "http_status": (
            response.status_code
        ),
        "detail_terms": (
            terms
        ),
        "identifiers": (
            identifiers[:20]
        ),
        "preview": (
            compact(
                text,
                500,
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    all_candidates = []

    search_results = []

    for query in QUERIES:

        result = request_search(
            query
        )

        search_results.append(
            {
                "query": query,
                "case_count": len(
                    result[
                        "cases"
                    ]
                ),
                "http_success": sum(
                    1
                    for case
                    in result[
                        "cases"
                    ]
                    if case.get(
                        "http_status"
                    )
                    == 200
                ),
            }
        )

        for case in result[
            "cases"
        ]:

            html = case.get(
                "html",
                "",
            )

            if not html:
                continue

            candidates = (
                extract_candidates(
                    html,
                    query,
                )
            )

            all_candidates.extend(
                candidates
            )

    # --------------------------------------------------------
    # URL 중복 제거
    # --------------------------------------------------------

    unique = {}

    for item in all_candidates:

        unique[
            item[
                "url"
            ]
        ] = item

    candidates = list(
        unique.values()
    )

    # --------------------------------------------------------
    # 상세 조회
    # --------------------------------------------------------

    details = []

    for candidate in candidates:

        details.append(
            inspect_detail(
                candidate
            )
        )

    # --------------------------------------------------------
    # 점수
    # --------------------------------------------------------

    for item in details:

        score = 0

        terms = item.get(
            "detail_terms",
            [],
        )

        if "대치" in terms:
            score += 5

        if "개포" in terms:
            score += 5

        if "자연녹지" in terms:
            score += 5

        if "녹지지역" in terms:
            score += 4

        if "용도지역" in terms:
            score += 4

        if "개발제한구역" in terms:
            score += 4

        if "택지개발" in terms:
            score += 2

        if "변경" in terms:
            score += 1

        if "해제" in terms:
            score += 2

        item[
            "score"
        ] = score

    details.sort(
        key=lambda item: item.get(
            "score",
            0,
        ),
        reverse=True,
    )

    evidence = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "official_source": {
            "provider": (
                "서울기록원"
            ),
            "relevant_series": [
                {
                    "code": "SR228",
                    "name": (
                        "용도지역 설정 기록"
                    ),
                },
                {
                    "code": "SR172",
                    "name": (
                        "개발제한구역 기록"
                    ),
                },
                {
                    "code": "SR143",
                    "name": (
                        "도시개발사업 기록 : "
                        "택지개발사업 계획"
                    ),
                },
                {
                    "code": "SR119894",
                    "name": (
                        "공동주택건설 기록 : "
                        "대치지구"
                    ),
                },
            ],
        },

        "search_results": (
            search_results
        ),

        "candidate_count": (
            len(
                details
            )
        ),

        "candidates": (
            details
        ),

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "서울기록원의 과거 용도지역·"
                "개발제한구역·택지개발 기록에서 "
                "대치/개포 관련 원기록 후보를 "
                "식별하는 단계"
            ),
        },
    }

    save_json(
        evidence
    )

    # ========================================================
    # 짧은 콘솔
    # ========================================================

    print(
        "Search queries:",
        len(
            QUERIES
        ),
    )

    print(
        "Candidates:",
        len(
            details
        ),
    )

    print()

    for index, item in enumerate(
        details[
            :10
        ],
        start=1,
    ):

        print(
            f"[{index}] score={item.get('score')}"
        )

        print(
            "title:",
            item.get(
                "title"
            ),
        )

        print(
            "terms:",
            item.get(
                "detail_terms"
            ),
        )

        print(
            "ids:",
            item.get(
                "identifiers"
            ),
        )

        print(
            "url:",
            item.get(
                "url"
            ),
        )

    print()

    print(
        "resolution: UNKNOWN"
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )