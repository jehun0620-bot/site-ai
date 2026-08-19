# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-9A-2
수산자원보호구역 API 인증키 전달 방식 진단

검증 대상
--------------------------------------------------
1. requests params 방식
2. serviceKey 소문자
3. ServiceKey 대문자
4. raw URL + 현재 환경변수값
5. URL decode 후 전달
6. URL encode 후 전달

중요
--------------------------------------------------
- API Key 값 전체는 출력하지 않는다.
- HTTP 403 자체는 FALSE 근거가 아니다.
- 응답 XML/HTML 원문 앞부분을 확인하여 gateway 오류를 식별한다.
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote, unquote

import requests
from dotenv import load_dotenv


# ============================================================
# 경로 / 환경변수
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(
    BASE_DIR / ".env"
)

API_KEY = os.getenv(
    "FISHERY_RESOURCE_API_KEY"
)


# ============================================================
# API
# ============================================================

API_URL = (
    "http://apis.data.go.kr/1192000/"
    "apVhdService_FshrsrcPzn/"
    "getOpnFshrsrcPznWFS"
)

POSITIVE_CONTROL_NAME = (
    "영광보전지역"
)

TIMEOUT = 30


# ============================================================
# 공통
# ============================================================

def print_section(
    title: str
) -> None:

    print()
    print("=" * 78)
    print(
        f"=== {title} ==="
    )
    print("=" * 78)


def mask(
    value: str
) -> str:

    if not value:
        return value

    candidates = {
        API_KEY or "",
        quote(
            API_KEY or "",
            safe="",
        ),
        unquote(
            API_KEY or ""
        ),
    }

    result = value

    for candidate in candidates:

        if candidate:
            result = result.replace(
                candidate,
                "[HIDDEN]",
            )

    return result


def preview_text(
    text: str,
    limit: int = 1500,
) -> str:

    return (
        text[:limit]
        .replace(
            "\r",
            " "
        )
        .replace(
            "\n",
            " "
        )
    )


def run_case(
    name: str,
    url: str,
    params=None,
) -> None:

    print_section(
        name
    )

    try:

        response = requests.get(
            url,
            params=params,
            timeout=TIMEOUT,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/126.0 Safari/537.36"
                ),
                "Accept": (
                    "application/xml,"
                    "text/xml,"
                    "application/json,"
                    "*/*"
                ),
            },
        )

        print(
            "HTTP:",
            response.status_code,
        )

        print(
            "Content-Type:",
            response.headers.get(
                "Content-Type",
                "",
            ),
        )

        print(
            "Final URL:",
            mask(
                response.url
            ),
        )

        print(
            "Response length:",
            len(
                response.content
            ),
        )

        print(
            "Response preview:"
        )

        print(
            preview_text(
                response.text
            )
        )

    except Exception as e:

        print(
            "ERROR:",
            repr(e),
        )


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        "STEP 17-21-C-9-2-9A-2 "
        "수산자원보호구역 API 인증키 전달 방식 진단"
    )

    if not API_KEY:

        print(
            "ERROR: "
            "FISHERY_RESOURCE_API_KEY가 없습니다."
        )

        return 1

    print(
        "KEY FOUND:",
        True,
    )

    print(
        "KEY LENGTH:",
        len(API_KEY),
    )

    print(
        "KEY PREFIX:",
        API_KEY[:4] + "...",
    )

    print(
        "contains %:",
        "%" in API_KEY,
    )

    print(
        "contains +:",
        "+" in API_KEY,
    )

    print(
        "contains /:",
        "/" in API_KEY,
    )

    print(
        "contains =:",
        "=" in API_KEY,
    )

    decoded_key = unquote(
        API_KEY
    )

    encoded_key = quote(
        API_KEY,
        safe="",
    )

    print(
        "decoded length:",
        len(
            decoded_key
        ),
    )

    print(
        "encoded length:",
        len(
            encoded_key
        ),
    )

    print(
        "decoded differs:",
        decoded_key != API_KEY,
    )

    print(
        "encoded differs:",
        encoded_key != API_KEY,
    )

    # --------------------------------------------------------
    # CASE 1
    # requests 기본 params + serviceKey
    # --------------------------------------------------------

    run_case(
        "CASE 1 - serviceKey / 현재 ENV 값",
        API_URL,
        params={
            "serviceKey": API_KEY,
            "fshrsr_pzn_nm": (
                POSITIVE_CONTROL_NAME
            ),
            "maxFeatures": 10,
        },
    )

    # --------------------------------------------------------
    # CASE 2
    # ServiceKey 대문자 S
    # --------------------------------------------------------

    run_case(
        "CASE 2 - ServiceKey / 현재 ENV 값",
        API_URL,
        params={
            "ServiceKey": API_KEY,
            "fshrsr_pzn_nm": (
                POSITIVE_CONTROL_NAME
            ),
            "maxFeatures": 10,
        },
    )

    # --------------------------------------------------------
    # CASE 3
    # URL decode 값
    # --------------------------------------------------------

    run_case(
        "CASE 3 - serviceKey / URL decode 값",
        API_URL,
        params={
            "serviceKey": (
                decoded_key
            ),
            "fshrsr_pzn_nm": (
                POSITIVE_CONTROL_NAME
            ),
            "maxFeatures": 10,
        },
    )

    # --------------------------------------------------------
    # CASE 4
    # URL decode + ServiceKey
    # --------------------------------------------------------

    run_case(
        "CASE 4 - ServiceKey / URL decode 값",
        API_URL,
        params={
            "ServiceKey": (
                decoded_key
            ),
            "fshrsr_pzn_nm": (
                POSITIVE_CONTROL_NAME
            ),
            "maxFeatures": 10,
        },
    )

    # --------------------------------------------------------
    # CASE 5
    # raw URL
    #
    # 이미 인코딩된 인증키를 requests params에 넣으면
    # '%'가 다시 %25로 인코딩될 가능성을 확인하기 위한 테스트
    # --------------------------------------------------------

    raw_url = (
        API_URL
        + "?serviceKey="
        + API_KEY
        + "&fshrsr_pzn_nm="
        + quote(
            POSITIVE_CONTROL_NAME,
            safe="",
        )
        + "&maxFeatures=10"
    )

    run_case(
        "CASE 5 - RAW URL / 현재 ENV 값",
        raw_url,
    )

    # --------------------------------------------------------
    # CASE 6
    # raw URL + decoded key를 직접 quote
    # --------------------------------------------------------

    raw_decoded_url = (
        API_URL
        + "?serviceKey="
        + quote(
            decoded_key,
            safe="",
        )
        + "&fshrsr_pzn_nm="
        + quote(
            POSITIVE_CONTROL_NAME,
            safe="",
        )
        + "&maxFeatures=10"
    )

    run_case(
        "CASE 6 - RAW URL / decoded 후 encode",
        raw_decoded_url,
    )

    print_section(
        "진단 완료"
    )

    print(
        "HTTP 200이 나온 CASE와 "
        "각 CASE의 Response preview를 비교합니다."
    )

    print(
        "모든 CASE가 403이면 "
        "활용신청에 연결된 인증키 종류 또는 "
        "서비스 endpoint 자체를 다음 단계에서 검증합니다."
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )