# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14F-2A
국가기록원 상세페이지 DOM 구조 probe

목표
======================================================================
1. 대표 기록건 1건만 조회한다.
2. 상세페이지의 label/value 구조를 확인한다.
3. 공개구분 / 원문 / 사본신청 상태를 추측하지 않는다.
4. HTML 전체 문자열 검색 대신 실제 DOM 구조를 파악한다.
5. 콘솔은 관련 row만 간략 출력한다.
"""

from __future__ import annotations

import re
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# ============================================================
# 대상
# ============================================================

RFILE_NO = "200902337177"
RITEM_NO = "000000000005"

DETAIL_URL = (
    "https://www.archives.go.kr/"
    "next/newsearch/viewArchiveDetail.do"
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
# 관심 키워드
# ============================================================

KEYWORDS = [
    "공개",
    "공개구분",
    "원문",
    "사본",
    "온라인",
    "열람",
    "기록물",
    "건제목",
    "관리번호",
    "생산기관",
]


def clean(
    value,
) -> str:

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value),
    ).strip()


def relevant(
    text: str,
) -> bool:

    return any(
        keyword in text
        for keyword in KEYWORDS
    )


def main() -> int:

    response = requests.get(
        DETAIL_URL,
        params={
            "rfile_no": RFILE_NO,
            "ritem_no": RITEM_NO,
        },
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    print(
        "HTTP:",
        response.status_code,
    )

    print(
        "URL:",
        response.url,
    )

    soup = BeautifulSoup(
        response.text,
        "html.parser",
    )

    # ========================================================
    # 1. table rows
    # ========================================================

    print()
    print("=== TABLE ROWS ===")

    table_results = []

    for tr in soup.find_all("tr"):

        cells = [
            clean(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in tr.find_all(
                ["th", "td"]
            )
        ]

        cells = [
            value
            for value in cells
            if value
        ]

        if not cells:
            continue

        text = " | ".join(
            cells
        )

        if relevant(text):

            table_results.append(
                text
            )

    for row in table_results[:30]:

        print(
            "-",
            row[:500],
        )

    # ========================================================
    # 2. dt/dd 구조
    # ========================================================

    print()
    print("=== DT / DD ===")

    dt_results = []

    for dt in soup.find_all("dt"):

        label = clean(
            dt.get_text(
                " ",
                strip=True,
            )
        )

        dd = dt.find_next_sibling(
            "dd"
        )

        value = (
            clean(
                dd.get_text(
                    " ",
                    strip=True,
                )
            )
            if dd
            else ""
        )

        text = (
            f"{label} | {value}"
        )

        if relevant(text):

            dt_results.append(
                text
            )

    for row in dt_results[:30]:

        print(
            "-",
            row[:500],
        )

    # ========================================================
    # 3. th -> td 직접 대응
    # ========================================================

    print()
    print("=== TH / TD ===")

    th_results = []

    for th in soup.find_all("th"):

        label = clean(
            th.get_text(
                " ",
                strip=True,
            )
        )

        if not relevant(label):
            continue

        td = th.find_next_sibling(
            "td"
        )

        value = (
            clean(
                td.get_text(
                    " ",
                    strip=True,
                )
            )
            if td
            else ""
        )

        th_results.append(
            (
                label,
                value,
            )
        )

    for label, value in th_results[:30]:

        print(
            f"- {label}: {value[:500]}"
        )

    # ========================================================
    # 4. 관심 문자열의 부모 DOM 확인
    # ========================================================

    print()
    print("=== KEYWORD ELEMENTS ===")

    seen = set()

    for string in soup.stripped_strings:

        text = clean(
            string
        )

        if not relevant(text):
            continue

        if text in seen:
            continue

        seen.add(
            text
        )

        parent = (
            string.parent
            if hasattr(
                string,
                "parent",
            )
            else None
        )

        tag_name = (
            parent.name
            if parent
            else ""
        )

        parent_text = (
            clean(
                parent.get_text(
                    " ",
                    strip=True,
                )
            )
            if parent
            else text
        )

        print(
            f"- tag={tag_name} "
            f"text={parent_text[:400]}"
        )

        if len(seen) >= 40:
            break

    # ========================================================
    # 5. 전체 페이지 길이
    # ========================================================

    full_text = clean(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    print()
    print(
        "Full text length:",
        len(
            full_text
        ),
    )

    print(
        "Contains 원문없음:",
        "원문없음" in full_text,
    )

    print(
        "Contains 온라인사본신청:",
        "온라인사본신청" in full_text,
    )

    print(
        "Contains 공개구분:",
        "공개구분" in full_text,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )