# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14E-4
대치택지개발 최초 고시 원문 source 식별 probe

목표
======================================================================
1. 토지이음 고시정보 검색을 직접 조회한다.
2. 건설부 고시 제123호 / 제608호의 실제 row를 탐색한다.
3. 날짜를 미리 확정하지 않고 1989년 전체 범위에서 검색한다.
4. 대치 / 수서 / 택지개발예정지구 문맥을 확인한다.
5. PDF/JPG 등 원문 첨부 존재 여부를 확인한다.
6. 원문 확보 전 도시지역편입해제구역 TRUE/FALSE 판정 금지.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup


STEP_NAME = (
    "STEP 17-21-C-9-2-14E-4 "
    "대치택지개발 최초 고시 원문 source 식별"
)

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_original_notice_source_probe.json"
)


# ============================================================
# 토지이음
# ============================================================

LIST_URL = (
    "https://www.eum.go.kr/web/gs/gv/gvGosiList.jsp"
)

DETAIL_BASE = (
    "https://www.eum.go.kr/web/gs/gv/gvGosiDet.jsp"
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
# 검색 대상
# ============================================================

TARGETS = [
    {
        "label": "INITIAL_DESIGNATION",
        "notice_number": "123",
        "year": "1989",
        "expected_terms": [
            "대치",
            "수서",
            "택지",
        ],
    },
    {
        "label": "DEVELOPMENT_PLAN",
        "notice_number": "608",
        "year": "1989",
        "expected_terms": [
            "대치",
            "택지",
        ],
    },
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
    limit: int = 300,
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
# HTML
# ============================================================

def request_html(
    url: str,
    params=None,
) -> Dict[str, Any]:

    try:

        response = requests.get(
            url,
            params=params,
            headers=HEADERS,
            timeout=TIMEOUT,
        )

        return {
            "http_status": (
                response.status_code
            ),
            "url": (
                response.url
            ),
            "html": (
                response.text
            ),
            "error": None,
        }

    except Exception as exc:

        return {
            "http_status": None,
            "url": url,
            "html": "",
            "error": str(exc),
        }


def extract_detail_links(
    html: str,
) -> List[Dict[str, str]]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    results = []

    for anchor in soup.find_all(
        "a"
    ):

        href = safe_string(
            anchor.get(
                "href"
            )
        )

        text = compact(
            anchor.get_text(
                " ",
                strip=True,
            ),
            200,
        )

        if not href:
            continue

        if (
            "gvGosiDet.jsp"
            not in href
        ):
            continue

        seq_match = re.search(
            r"seq=(\d+)",
            href,
        )

        if not seq_match:
            continue

        results.append(
            {
                "seq": (
                    seq_match.group(
                        1
                    )
                ),
                "text": (
                    text
                ),
                "href": (
                    href
                ),
            }
        )

    # 중복 제거
    unique = {}

    for item in results:

        unique[
            item[
                "seq"
            ]
        ] = item

    return list(
        unique.values()
    )


def parse_detail(
    seq: str,
) -> Dict[str, Any]:

    result = request_html(
        DETAIL_BASE,
        params={
            "seq": seq,
        },
    )

    html = result.get(
        "html",
        "",
    )

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    text = compact(
        soup.get_text(
            " ",
            strip=True,
        ),
        5000,
    )

    # --------------------------------------------------------
    # 첨부파일
    # --------------------------------------------------------

    attachments = []

    for anchor in soup.find_all(
        "a"
    ):

        name = compact(
            anchor.get_text(
                " ",
                strip=True,
            ),
            200,
        )

        href = safe_string(
            anchor.get(
                "href"
            )
        )

        if not name:
            continue

        lowered = name.lower()

        if any(
            ext in lowered
            for ext in (
                ".pdf",
                ".jpg",
                ".jpeg",
                ".png",
                ".zip",
                ".hwp",
            )
        ):

            attachments.append(
                {
                    "name": name,
                    "href": href,
                }
            )

    return {
        "seq": seq,
        "http_status": (
            result.get(
                "http_status"
            )
        ),
        "url": (
            result.get(
                "url"
            )
        ),
        "text": (
            text
        ),
        "attachments": (
            attachments
        ),
    }


# ============================================================
# 검색
# ============================================================

def search_target(
    target: Dict[str, Any],
) -> Dict[str, Any]:

    notice_number = (
        target[
            "notice_number"
        ]
    )

    # 토지이음 검색 파라미터는 화면 변경 가능성이 있으므로
    # 연도 + 고시번호 중심으로 여러 형태를 시도한다.
    cases = [
        {
            "gosino": (
                f"{target['year']}-{notice_number}"
            ),
            "startdt": (
                f"{target['year']}-01-01"
            ),
            "enddt": (
                f"{target['year']}-12-31"
            ),
        },
        {
            "gosino": (
                notice_number
            ),
            "startdt": (
                f"{target['year']}-01-01"
            ),
            "enddt": (
                f"{target['year']}-12-31"
            ),
        },
    ]

    discovered = {}

    case_results = []

    for case in cases:

        response = request_html(
            LIST_URL,
            params=case,
        )

        links = extract_detail_links(
            response.get(
                "html",
                "",
            )
        )

        case_results.append(
            {
                "params": case,
                "http_status": (
                    response.get(
                        "http_status"
                    )
                ),
                "link_count": (
                    len(
                        links
                    )
                ),
            }
        )

        for link in links:

            seq = link[
                "seq"
            ]

            if seq in discovered:
                continue

            detail = parse_detail(
                seq
            )

            full_text = detail[
                "text"
            ]

            # 1989 + 고시번호가 둘 다 포함되는 row만 유지
            number_patterns = [
                f"1989-{notice_number}",
                f"제1989-{notice_number}호",
                f"제 {notice_number}호",
                f"제{notice_number}호",
            ]

            number_match = any(
                pattern
                in full_text
                for pattern
                in number_patterns
            )

            if not number_match:
                continue

            expected_matches = [
                term
                for term
                in target[
                    "expected_terms"
                ]
                if term in full_text
            ]

            discovered[
                seq
            ] = {
                **detail,
                "expected_matches": (
                    expected_matches
                ),
            }

    candidates = list(
        discovered.values()
    )

    candidates.sort(
        key=lambda item: (
            len(
                item[
                    "expected_matches"
                ]
            )
        ),
        reverse=True,
    )

    return {
        "target": target,
        "cases": (
            case_results
        ),
        "candidate_count": (
            len(
                candidates
            )
        ),
        "candidates": (
            candidates
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    results = []

    for target in TARGETS:

        results.append(
            search_target(
                target
            )
        )

    evidence = {
        "step": (
            STEP_NAME
        ),
        "condition": (
            "도시지역편입해제구역"
        ),
        "targets": (
            results
        ),
        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "1989 최초 택지개발 고시의 "
                "토지이음 원문/첨부 source를 "
                "식별하는 단계"
            ),
        },
    }

    save_json(
        evidence
    )

    # ========================================================
    # 간략 출력
    # ========================================================

    for result in results:

        target = result[
            "target"
        ]

        print()

        print(
            f"[{target['label']}]"
        )

        print(
            "Notice:",
            (
                f"{target['year']}-"
                f"{target['notice_number']}"
            ),
        )

        print(
            "Candidates:",
            result[
                "candidate_count"
            ],
        )

        for index, item in enumerate(
            result[
                "candidates"
            ][
                :5
            ],
            start=1,
        ):

            print(
                f"  [{index}] seq={item['seq']}"
            )

            print(
                "      terms:",
                item[
                    "expected_matches"
                ],
            )

            print(
                "      attachments:",
                len(
                    item[
                        "attachments"
                    ]
                ),
            )

            print(
                "      preview:",
                compact(
                    item[
                        "text"
                    ],
                    350,
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