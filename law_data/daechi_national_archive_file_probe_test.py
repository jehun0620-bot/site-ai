# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14F-2
국가기록원 DA0138776 대치/개포 택지개발 기록철 구조 probe

목표
======================================================================
1. 공식 기록철 rfile_no를 직접 조회한다.
2. 기록철 내 ritem_no / 건제목을 수집한다.
3. 개포 / 대치 / 수서 / 택지개발 관련 기록을 우선 분류한다.
4. 상세페이지의 실제 기록 메타데이터를 DOM table 기준으로 파싱한다.
5. 공개구분은 실제 metadata row에서만 판정한다.
6. 온라인사본신청은 실제 버튼/링크 존재 여부로 판정한다.
7. 원문 온라인 제공 여부는 명시적 metadata 또는 원문 link가 없으면
   UNVERIFIED로 유지한다.
8. 원문 상태 불명확성을 FALSE 근거로 사용하지 않는다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from bs4 import BeautifulSoup


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-14F-2 "
    "국가기록원 DA0138776 기록철 구조 probe"
)


# ============================================================
# 경로
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "daechi_national_archive_file_probe.json"
)


# ============================================================
# 공식 기록철
# ============================================================

RFILE_NO = "200902337177"
MANAGEMENT_NO = "DA0138776"

FILE_URL = (
    "https://www.archives.go.kr/"
    "next/newsearch/popArchiveList.do"
)

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
    "Accept-Language": "ko-KR,ko;q=0.9",
}


# ============================================================
# 후보 분류
# ============================================================

TARGET_TERMS = [
    "개포",
    "대치",
    "수서",
    "택지개발",
    "예정지구",
]

HIGH_VALUE_TERMS = [
    "지정신청",
    "지정을 위한 협의",
    "지정요청",
    "변경지정 요청",
    "보완사항",
    "보완",
    "협의",
]

HISTORY_TERMS = [
    "개발제한구역",
    "시가화조정구역",
    "녹지지역",
    "자연녹지",
    "생산녹지",
    "보전녹지",
    "도시지역",
    "편입",
    "해제",
]


# ============================================================
# 공통
# ============================================================

def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def normalize_text(
    value: Any,
) -> str:

    return re.sub(
        r"\s+",
        " ",
        safe_string(value),
    ).strip()


def compact(
    value: Any,
    limit: int = 250,
) -> str:

    text = normalize_text(
        value
    )

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
# HTTP
# ============================================================

def request_html(
    url: str,
    params: Dict[str, Any],
) -> str:

    response = requests.get(
        url,
        params=params,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    return response.text


# ============================================================
# 기록철 목록 파싱
# ============================================================

def extract_items_from_page(
    html: str,
) -> List[Dict[str, Any]]:

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    results = []

    for anchor in soup.find_all("a"):

        href = safe_string(
            anchor.get("href")
        )

        title = compact(
            anchor.get_text(
                " ",
                strip=True,
            ),
            300,
        )

        if not href or not title:
            continue

        # ritem_no 직접 링크
        match = re.search(
            r"ritem_no=(\d+)",
            href,
        )

        if match:

            results.append(
                {
                    "ritem_no": match.group(1),
                    "title": title,
                    "href": href,
                }
            )

            continue

        # javascript bindDetail 대응
        match = re.search(
            (
                r"bindDetail"
                r"\("
                r"[^,]+,"
                r"\s*['\"]?"
                r"(\d+)"
                r"['\"]?"
            ),
            href,
        )

        if match:

            results.append(
                {
                    "ritem_no": match.group(1),
                    "title": title,
                    "href": href,
                }
            )

    unique = {}

    for item in results:
        unique[
            item["ritem_no"]
        ] = item

    return list(
        unique.values()
    )


# ============================================================
# 상세 metadata 파싱
# ============================================================

def extract_detail_metadata(
    soup: BeautifulSoup,
) -> Dict[str, str]:

    """
    실제 상세정보 table row만 사용한다.

    검색조건 영역의
    '전체 공개 부분공개 비공개'
    '전체 온라인제공 온라인 미제공'
    같은 UI 문구는 metadata로 사용하지 않는다.
    """

    metadata: Dict[str, str] = {}

    for tr in soup.find_all("tr"):

        cells = tr.find_all(
            ["th", "td"],
            recursive=False,
        )

        if not cells:
            # nested 구조 대응
            cells = tr.find_all(
                ["th", "td"]
            )

        texts = [
            normalize_text(
                cell.get_text(
                    " ",
                    strip=True,
                )
            )
            for cell in cells
        ]

        texts = [
            value
            for value in texts
            if value
        ]

        if len(texts) < 2:
            continue

        # 여러 label/value가 한 row에 존재할 수 있음
        index = 0

        while (
            index + 1
            < len(texts)
        ):

            label = texts[index]
            value = texts[
                index + 1
            ]

            # 실제 상세정보에서 필요한 label만
            recognized = (
                label.startswith(
                    "기록물 건제목"
                )
                or label.startswith(
                    "기록물 철제목"
                )
                or label == "생산년도"
                or label == "관리번호"
                or label == "생산기관"
                or label == "기록물형태"
                or label == "소장위치"
                or label == "공개구분"
            )

            if recognized:

                # 검색 UI label은 제외
                if "도움말" not in label:

                    metadata[
                        label
                    ] = value

            index += 2

    return metadata


def get_metadata_value(
    metadata: Dict[str, str],
    prefix: str,
) -> str:

    for key, value in metadata.items():

        if key.startswith(
            prefix
        ):
            return value

    return ""


# ============================================================
# 실제 버튼/링크 판정
# ============================================================

def find_copy_request_action(
    soup: BeautifulSoup,
) -> bool:

    """
    '온라인사본신청'이라는 실제 clickable element가
    존재하는지 확인한다.

    단순 전체 페이지 text 포함 여부만 사용하지 않는다.
    """

    for tag in soup.find_all(
        ["a", "button", "input"]
    ):

        text = normalize_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        value = normalize_text(
            tag.get(
                "value"
            )
        )

        title = normalize_text(
            tag.get(
                "title"
            )
        )

        combined = (
            f"{text} {value} {title}"
        )

        if (
            "온라인사본신청"
            in combined
        ):

            return True

    return False


def find_original_document_action(
    soup: BeautifulSoup,
) -> Tuple[
    str,
    List[Dict[str, str]],
]:

    """
    온라인 원문 제공 여부는 매우 보수적으로 판정한다.

    검색필터의 '온라인제공' 문자열은 사용하지 않는다.

    실제 상세페이지 내 clickable 원문보기/원문열람/
    원문다운로드 등의 action이 확인되면 AVAILABLE.

    명시적인 '원문없음' metadata/detail 영역이 확인되면
    NOT_AVAILABLE.

    둘 다 아니면 UNVERIFIED.
    """

    actions = []

    for tag in soup.find_all(
        ["a", "button"]
    ):

        text = normalize_text(
            tag.get_text(
                " ",
                strip=True,
            )
        )

        title = normalize_text(
            tag.get(
                "title"
            )
        )

        href = safe_string(
            tag.get(
                "href"
            )
        )

        combined = (
            f"{text} {title}"
        )

        positive_tokens = [
            "원문보기",
            "원문 보기",
            "원문열람",
            "원문 열람",
            "원문다운로드",
            "원문 다운로드",
        ]

        if any(
            token in combined
            for token
            in positive_tokens
        ):

            actions.append(
                {
                    "text": text,
                    "title": title,
                    "href": href,
                }
            )

    if actions:

        return (
            "AVAILABLE",
            actions,
        )

    # --------------------------------------------------------
    # '원문없음'도 검색 UI가 아니라 실제 상세영역인지
    # 최대한 제한적으로 검사
    # --------------------------------------------------------

    for tr in soup.find_all("tr"):

        text = normalize_text(
            tr.get_text(
                " ",
                strip=True,
            )
        )

        if (
            "원문없음"
            in text
            and "원문서비스 도움말"
            not in text
        ):

            return (
                "NOT_AVAILABLE",
                [],
            )

    return (
        "UNVERIFIED",
        [],
    )


# ============================================================
# 상세페이지
# ============================================================

def fetch_detail(
    ritem_no: str,
) -> Dict[str, Any]:

    try:

        html = request_html(
            DETAIL_URL,
            {
                "rfile_no": RFILE_NO,
                "ritem_no": ritem_no,
            },
        )

    except Exception as exc:

        return {
            "ritem_no": ritem_no,
            "http_success": False,
            "error": str(exc),
        }

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    full_text = normalize_text(
        soup.get_text(
            " ",
            strip=True,
        )
    )

    metadata = (
        extract_detail_metadata(
            soup
        )
    )

    title = get_metadata_value(
        metadata,
        "기록물 건제목",
    )

    archive_title = (
        get_metadata_value(
            metadata,
            "기록물 철제목",
        )
    )

    public_value = (
        get_metadata_value(
            metadata,
            "공개구분",
        )
    )

    # --------------------------------------------------------
    # 공개 상태
    # --------------------------------------------------------

    if public_value.startswith(
        "공개"
    ):

        public_status = (
            "PUBLIC"
        )

    elif public_value.startswith(
        "부분공개"
    ):

        public_status = (
            "PARTIAL"
        )

    elif public_value.startswith(
        "비공개"
    ):

        public_status = (
            "PRIVATE"
        )

    else:

        public_status = (
            "UNVERIFIED"
        )

    # --------------------------------------------------------
    # 원문 / 사본신청
    # --------------------------------------------------------

    (
        original_status,
        original_actions,
    ) = find_original_document_action(
        soup
    )

    copy_request_available = (
        find_copy_request_action(
            soup
        )
    )

    history_terms = [
        term
        for term
        in HISTORY_TERMS
        if term in full_text
    ]

    return {
        "ritem_no": ritem_no,

        "http_success": True,

        "title": title,

        "archive_title": (
            archive_title
        ),

        "production_year": (
            get_metadata_value(
                metadata,
                "생산년도",
            )
        ),

        "management_no": (
            get_metadata_value(
                metadata,
                "관리번호",
            )
        ),

        "producer": (
            get_metadata_value(
                metadata,
                "생산기관",
            )
        ),

        "record_type": (
            get_metadata_value(
                metadata,
                "기록물형태",
            )
        ),

        "location": (
            get_metadata_value(
                metadata,
                "소장위치",
            )
        ),

        "public_value": (
            public_value
        ),

        "public_status": (
            public_status
        ),

        # 핵심 변경
        "original_status": (
            original_status
        ),

        "original_actions": (
            original_actions
        ),

        "copy_request_available": (
            copy_request_available
        ),

        "history_terms": (
            history_terms
        ),

        "metadata": (
            metadata
        ),

        "text_preview": (
            compact(
                full_text,
                1200,
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    all_items = []

    # ========================================================
    # 기록철 목록
    # ========================================================

    for page_no in range(
        1,
        10,
    ):

        try:

            html = request_html(
                FILE_URL,
                {
                    "rfile_no": RFILE_NO,
                    "pageNo": page_no,
                },
            )

        except Exception:
            continue

        items = (
            extract_items_from_page(
                html
            )
        )

        if not items:

            if page_no > 1:
                break

            continue

        all_items.extend(
            items
        )

    unique = {}

    for item in all_items:

        unique[
            item["ritem_no"]
        ] = item

    items = list(
        unique.values()
    )

    # ========================================================
    # 후보
    # ========================================================

    candidates = []

    for item in items:

        title = safe_string(
            item.get(
                "title"
            )
        )

        target_matches = [
            term
            for term
            in TARGET_TERMS
            if term in title
        ]

        if not target_matches:
            continue

        high_matches = [
            term
            for term
            in HIGH_VALUE_TERMS
            if term in title
        ]

        score = (
            len(
                target_matches
            )
            * 2
            + len(
                high_matches
            )
            * 3
        )

        if "개포" in title:
            score += 4

        if "대치" in title:
            score += 4

        if "지정신청" in title:
            score += 3

        if "보완" in title:
            score += 2

        candidates.append(
            {
                **item,
                "target_matches": (
                    target_matches
                ),
                "high_value_matches": (
                    high_matches
                ),
                "score": score,
            }
        )

    candidates.sort(
        key=lambda item: (
            item.get(
                "score",
                0,
            )
        ),
        reverse=True,
    )

    # ========================================================
    # 상세조회
    # ========================================================

    details = []

    for item in candidates[:15]:

        detail = fetch_detail(
            item[
                "ritem_no"
            ]
        )

        details.append(
            {
                **item,
                "detail": detail,
            }
        )

    # ========================================================
    # 통계
    # ========================================================

    public_count = sum(
        1
        for item in details
        if item.get(
            "detail",
            {},
        ).get(
            "public_status"
        )
        == "PUBLIC"
    )

    original_available_count = sum(
        1
        for item in details
        if item.get(
            "detail",
            {},
        ).get(
            "original_status"
        )
        == "AVAILABLE"
    )

    original_not_available_count = sum(
        1
        for item in details
        if item.get(
            "detail",
            {},
        ).get(
            "original_status"
        )
        == "NOT_AVAILABLE"
    )

    original_unverified_count = sum(
        1
        for item in details
        if item.get(
            "detail",
            {},
        ).get(
            "original_status"
        )
        == "UNVERIFIED"
    )

    copy_request_count = sum(
        1
        for item in details
        if item.get(
            "detail",
            {},
        ).get(
            "copy_request_available"
        )
        is True
    )

    evidence = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "official_source": {
            "provider": (
                "국가기록원"
            ),
            "rfile_no": (
                RFILE_NO
            ),
            "management_no": (
                MANAGEMENT_NO
            ),
            "production_year": 1988,
        },

        "total_item_count": (
            len(
                items
            )
        ),

        "candidate_count": (
            len(
                candidates
            )
        ),

        "detail_checked_count": (
            len(
                details
            )
        ),

        "public_count": (
            public_count
        ),

        "original_available_count": (
            original_available_count
        ),

        "original_not_available_count": (
            original_not_available_count
        ),

        "original_unverified_count": (
            original_unverified_count
        ),

        "copy_request_count": (
            copy_request_count
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
                "국가기록원 공식 기록건의 공개상태와 "
                "원문/사본신청 상태를 실제 상세 DOM "
                "metadata 기준으로 검증한 단계"
            ),
        },
    }

    save_json(
        evidence
    )

    # ========================================================
    # 초간략 콘솔
    # ========================================================

    print(
        "Archive items:",
        len(
            items
        ),
    )

    print(
        "Relevant candidates:",
        len(
            candidates
        ),
    )

    print(
        "Details checked:",
        len(
            details
        ),
    )

    print(
        "Public:",
        public_count,
    )

    print(
        "Original available:",
        original_available_count,
    )

    print(
        "Original unavailable:",
        original_not_available_count,
    )

    print(
        "Original unverified:",
        original_unverified_count,
    )

    print(
        "Copy request:",
        copy_request_count,
    )

    print()

    for index, item in enumerate(
        details[:5],
        start=1,
    ):

        detail = item[
            "detail"
        ]

        print(
            f"[{index}] "
            f"ritem={item['ritem_no']}"
        )

        print(
            "title:",
            item.get(
                "title"
            ),
        )

        print(
            "public:",
            detail.get(
                "public_status"
            ),
        )

        print(
            "original:",
            detail.get(
                "original_status"
            ),
        )

        print(
            "copy request:",
            detail.get(
                "copy_request_available"
            ),
        )

        print(
            "history:",
            detail.get(
                "history_terms"
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