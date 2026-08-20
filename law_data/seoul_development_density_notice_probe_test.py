# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-13C
서울 개발밀도관리구역 지정·고시 evidence probe

목표
======================================================================
1. 개발밀도관리구역이 서울특별시에 실제 지정된 사례가 있는지 확인한다.
2. 지정 / 변경 / 해제 / 고시 관련 공식 문서 흔적을 수집한다.
3. 검색 실패 자체를 FALSE 근거로 사용하지 않는다.
4. 명확한 현행 미지정 근거가 확보되기 전에는 UNKNOWN 유지한다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List

import requests


STEP_NAME = (
    "STEP 17-21-C-9-2-13C "
    "서울 개발밀도관리구역 지정·고시 evidence probe"
)

TARGET = "개발밀도관리구역"

BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_development_density_notice_probe.json"
)

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

TIMEOUT = 20


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
        )


def compact(
    text: str,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def request_page(
    name: str,
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

        text = response.text

        return {
            "name": name,
            "http_status": (
                response.status_code
            ),
            "final_url": (
                response.url
            ),
            "target_present": (
                TARGET in text
            ),
            "designation_present": (
                "지정" in text
            ),
            "notice_present": (
                "고시" in text
            ),
            "release_present": (
                "해제" in text
            ),
            "text_preview": (
                compact(
                    text
                )[:2000]
            ),
            "error": None,
        }

    except Exception as exc:

        return {
            "name": name,
            "http_status": None,
            "final_url": url,
            "target_present": False,
            "designation_present": False,
            "notice_present": False,
            "release_present": False,
            "text_preview": "",
            "error": str(
                exc
            ),
        }


def main() -> int:

    # 서울시 공식 계열 페이지 probe
    #
    # endpoint가 현재 검색 UI와 정확히 맞지 않더라도
    # 실패를 FALSE로 사용하지 않는다.

    candidates = [
        {
            "name": (
                "서울시 통합검색"
            ),
            "url": (
                "https://www.seoul.go.kr/search"
            ),
            "params": {
                "query": TARGET,
            },
        },
        {
            "name": (
                "서울 열린데이터광장 검색"
            ),
            "url": (
                "https://data.seoul.go.kr/"
            ),
            "params": {
                "searchValue": TARGET,
            },
        },
        {
            "name": (
                "서울 정보소통광장"
            ),
            "url": (
                "https://opengov.seoul.go.kr/"
            ),
            "params": {
                "query": TARGET,
            },
        },
        {
            "name": (
                "서울기록원"
            ),
            "url": (
                "https://archives.seoul.go.kr/"
            ),
            "params": {
                "query": TARGET,
            },
        },
    ]

    results: List[
        Dict[str, Any]
    ] = []

    for candidate in candidates:

        result = request_page(
            candidate[
                "name"
            ],
            candidate[
                "url"
            ],
            candidate.get(
                "params"
            ),
        )

        results.append(
            result
        )

    successful = [
        item
        for item
        in results
        if item[
            "http_status"
        ] == 200
    ]

    target_hits = [
        item
        for item
        in results
        if item[
            "target_present"
        ]
    ]

    # 이 probe 자체로 FALSE를 확정하지 않는다.
    resolution = {
        "query_status": (
            "QUERY_SUCCESS"
            if successful
            else "QUERY_FAILED"
        ),
        "resolution": (
            "UNKNOWN"
        ),
        "confidence": (
            "NONE"
        ),
        "reason": (
            "서울시 공식 계열 자료에서 "
            "개발밀도관리구역 지정·고시 흔적을 "
            "탐색하는 단계이며, 검색 결과 부재만으로 "
            "미지정을 확정할 수 없으므로 UNKNOWN 유지"
        ),
    }

    save_json(
        {
            "step": STEP_NAME,
            "condition": TARGET,
            "results": results,
            "successful_count": (
                len(
                    successful
                )
            ),
            "target_hit_count": (
                len(
                    target_hits
                )
            ),
            "resolution": (
                resolution
            ),
        }
    )

    print(
        "HTTP success:",
        len(
            successful
        ),
    )

    print(
        "Target hits:",
        len(
            target_hits
        ),
    )

    for item in target_hits:

        print(
            "Hit:",
            item[
                "name"
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
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )