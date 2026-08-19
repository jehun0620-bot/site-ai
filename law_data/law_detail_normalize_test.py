import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-2
# 자치법규 + 국가법령 상세 데이터 공통 정규화 테스트
# ============================================================


# ============================================================
# 기본 설정
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ------------------------------------------------------------
# 인증키
# ------------------------------------------------------------

POSSIBLE_KEY_NAMES = [
    "LAW_API_KEY",
    "LAW_SERVICE_KEY",
    "LAW_OC",
    "LAW_API_OC",
]

SERVICE_KEY = None
SERVICE_KEY_NAME = None

for key_name in POSSIBLE_KEY_NAMES:

    value = os.getenv(key_name)

    if value:

        SERVICE_KEY = value
        SERVICE_KEY_NAME = key_name
        break


if not SERVICE_KEY:

    raise RuntimeError(
        "법령 API 인증키를 찾을 수 없습니다."
    )


# ------------------------------------------------------------
# API
# ------------------------------------------------------------

API_URL = "http://www.law.go.kr/DRF/lawService.do"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.law.go.kr/",
}


# ============================================================
# 대상 법규
# ============================================================

TARGETS = [
    {
        "level": 1,
        "type_name": "자치구 조례",
        "name": "서울특별시 강남구 도시계획 조례",
        "target": "ordin",
        "mst": "1592205",
        "id": "2072371",
    },
    {
        "level": 2,
        "type_name": "서울특별시 조례",
        "name": "서울특별시 도시계획 조례",
        "target": "ordin",
        "mst": "2149501",
        "id": "2000719",
    },
    {
        "level": 3,
        "type_name": "국가 법률",
        "name": "국토의 계획 및 이용에 관한 법률",
        "target": "law",
        "mst": "284013",
        "id": "009294",
    },
    {
        "level": 4,
        "type_name": "국가 시행령",
        "name": "국토의 계획 및 이용에 관한 법률 시행령",
        "target": "law",
        "mst": "287269",
        "id": "009419",
    },
]


# ============================================================
# 공통 유틸
# ============================================================

def normalize_to_list(value: Any) -> list:

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def text_value(value: Any) -> str:
    """
    문자열/list/dict가 혼재하는 API 데이터를
    검색 가능한 문자열로 변환한다.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):

        parts = []

        for item in value:

            text = text_value(item)

            if text:
                parts.append(text)

        return "\n".join(parts)

    if isinstance(value, dict):

        parts = []

        for item in value.values():

            text = text_value(item)

            if text:
                parts.append(text)

        return "\n".join(parts)

    return str(value)


# ============================================================
# 국가법령 계층 텍스트 변환
# ============================================================

def flatten_national_article(article: dict) -> str:
    """
    국가법령의
    조 → 항 → 호 → 목
    구조를 하나의 검색 가능한 문자열로 만든다.
    """

    parts = []

    article_content = text_value(
        article.get("조문내용")
    )

    if article_content:
        parts.append(article_content)

    paragraphs = normalize_to_list(
        article.get("항")
    )

    for paragraph in paragraphs:

        if not isinstance(paragraph, dict):
            continue

        paragraph_content = text_value(
            paragraph.get("항내용")
        )

        if paragraph_content:
            parts.append(paragraph_content)

        items = normalize_to_list(
            paragraph.get("호")
        )

        for item in items:

            if not isinstance(item, dict):
                continue

            item_content = text_value(
                item.get("호내용")
            )

            if item_content:
                parts.append(item_content)

            subitems = normalize_to_list(
                item.get("목")
            )

            for subitem in subitems:

                if not isinstance(subitem, dict):
                    continue

                subitem_content = text_value(
                    subitem.get("목내용")
                )

                if subitem_content:
                    parts.append(subitem_content)

    return "\n".join(parts)


# ============================================================
# 자치법규 기본정보 정규화
# ============================================================

def normalize_ordin_basic_info(service: dict) -> dict:

    info = service.get(
        "자치법규기본정보",
        {}
    )

    if not isinstance(info, dict):
        return {}

    return {
        "name": text_value(
            info.get("자치법규명")
        ),
        "law_id": text_value(
            info.get("자치법규ID")
        ),
        "mst": text_value(
            info.get("자치법규일련번호")
        ),
        "organization": text_value(
            info.get("지자체기관명")
        ),
        "law_type": text_value(
            info.get("자치법규종류")
        ),
        "revision_type": text_value(
            info.get("제개정정보")
        ),
        "effective_date": text_value(
            info.get("시행일자")
        ),
        "publication_date": text_value(
            info.get("공포일자")
        ),
        "publication_number": text_value(
            info.get("공포번호")
        ),
    }


# ============================================================
# 국가법령 기본정보 정규화
# ============================================================

def normalize_law_basic_info(law: dict) -> dict:

    info = law.get(
        "기본정보",
        {}
    )

    if not isinstance(info, dict):
        return {}

    ministry = info.get(
        "소관부처",
        {}
    )

    if isinstance(ministry, dict):

        organization = text_value(
            ministry.get("content")
        )

    else:

        organization = text_value(
            ministry
        )

    law_type = info.get(
        "법종구분",
        {}
    )

    if isinstance(law_type, dict):

        law_type_name = text_value(
            law_type.get("content")
        )

    else:

        law_type_name = text_value(
            law_type
        )

    return {
        "name": text_value(
            info.get("법령명_한글")
        ),
        "law_id": text_value(
            info.get("법령ID")
        ),
        "mst": "",
        "organization": organization,
        "law_type": law_type_name,
        "revision_type": text_value(
            info.get("제개정구분")
        ),
        "effective_date": text_value(
            info.get("시행일자")
        ),
        "publication_date": text_value(
            info.get("공포일자")
        ),
        "publication_number": text_value(
            info.get("공포번호")
        ),
        "short_name": text_value(
            info.get("법령명약칭")
        ),
    }


# ============================================================
# 자치법규 조문 정규화
# ============================================================

def normalize_ordin_articles(service: dict) -> list:

    article_container = service.get(
        "조문",
        {}
    )

    if not isinstance(article_container, dict):
        return []

    raw_articles = normalize_to_list(
        article_container.get("조")
    )

    result = []

    for raw in raw_articles:

        if not isinstance(raw, dict):
            continue

        number = raw.get(
            "조문번호"
        )

        if isinstance(number, list):

            number = (
                number[0]
                if number
                else ""
            )

        content = text_value(
            raw.get("조내용")
        )

        result.append(
            {
                "article_number": text_value(
                    number
                ),
                "article_branch_number": "",
                "article_key": "",
                "article_title": text_value(
                    raw.get("조제목")
                ),
                "article_content": content,
                "article_full_text": content,
                "article_status": text_value(
                    raw.get("조문여부")
                ),
                "effective_date": "",
                "paragraphs": [],
                "source_format": "ordin",
            }
        )

    return result


# ============================================================
# 국가법령 조문 정규화
# ============================================================

def normalize_law_articles(law: dict) -> list:

    article_container = law.get(
        "조문",
        {}
    )

    if not isinstance(article_container, dict):
        return []

    raw_articles = normalize_to_list(
        article_container.get(
            "조문단위"
        )
    )

    result = []

    for raw in raw_articles:

        if not isinstance(raw, dict):
            continue

        full_text = flatten_national_article(
            raw
        )

        paragraphs = normalize_to_list(
            raw.get("항")
        )

        result.append(
            {
                "article_number": text_value(
                    raw.get("조문번호")
                ),
                "article_branch_number": text_value(
                    raw.get("조문가지번호")
                ),
                "article_key": text_value(
                    raw.get("조문키")
                ),
                "article_title": text_value(
                    raw.get("조문제목")
                ),
                "article_content": text_value(
                    raw.get("조문내용")
                ),
                "article_full_text": full_text,
                "article_status": text_value(
                    raw.get("조문여부")
                ),
                "effective_date": text_value(
                    raw.get("조문시행일자")
                ),
                "paragraphs": paragraphs,
                "source_format": "law",
            }
        )

    return result


# ============================================================
# 자치법규 별표 정규화
# ============================================================

def normalize_ordin_appendices(service: dict) -> list:
    """
    자치법규 API는 별표 구조가 두 가지 형태로 존재한다.

    강남구:
        LawService
        └─ 별표
           └─ 별표단위

    서울시:
        LawService
        └─ 별표단위
    """

    raw_units = []

    # --------------------------------------------------------
    # 형태 1
    # LawService.별표.별표단위
    # --------------------------------------------------------

    appendix_container = service.get(
        "별표"
    )

    if isinstance(
        appendix_container,
        dict
    ):

        raw_units.extend(
            normalize_to_list(
                appendix_container.get(
                    "별표단위"
                )
            )
        )

    # --------------------------------------------------------
    # 형태 2
    # LawService.별표단위
    # --------------------------------------------------------

    direct_units = service.get(
        "별표단위"
    )

    raw_units.extend(
        normalize_to_list(
            direct_units
        )
    )

    result = []

    for raw in raw_units:

        if not isinstance(raw, dict):
            continue

        result.append(
            {
                "number": text_value(
                    raw.get("별표번호")
                ),
                "branch_number": text_value(
                    raw.get("별표가지번호")
                ),
                "key": text_value(
                    raw.get("별표키")
                ),
                "title": text_value(
                    raw.get("별표제목")
                ),
                "type": text_value(
                    raw.get("별표구분")
                ),
                "content": text_value(
                    raw.get("별표내용")
                ),
                "file_url": text_value(
                    raw.get(
                        "별표첨부파일명"
                    )
                ),
                "source_format": "ordin",
            }
        )

    return result


# ============================================================
# 국가법령 별표 정규화
# ============================================================

def normalize_law_appendices(law: dict) -> list:

    appendix_container = law.get(
        "별표",
        {}
    )

    if not isinstance(
        appendix_container,
        dict
    ):
        return []

    raw_units = normalize_to_list(
        appendix_container.get(
            "별표단위"
        )
    )

    result = []

    for raw in raw_units:

        if not isinstance(raw, dict):
            continue

        result.append(
            {
                "number": text_value(
                    raw.get("별표번호")
                ),
                "branch_number": text_value(
                    raw.get("별표가지번호")
                ),
                "key": text_value(
                    raw.get("별표키")
                ),
                "title": text_value(
                    raw.get("별표제목")
                ),
                "type": text_value(
                    raw.get("별표구분")
                ),
                "content": text_value(
                    raw.get("별표내용")
                ),
                "pdf_file": text_value(
                    raw.get(
                        "별표PDF파일명"
                    )
                ),
                "hwp_file": text_value(
                    raw.get(
                        "별표HWP파일명"
                    )
                ),
                "pdf_link": text_value(
                    raw.get(
                        "별표서식PDF파일링크"
                    )
                ),
                "file_link": text_value(
                    raw.get(
                        "별표서식파일링크"
                    )
                ),
                "source_format": "law",
            }
        )

    return result


# ============================================================
# 자치법규 부칙 정규화
# ============================================================

def normalize_ordin_addenda(service: dict) -> list:

    raw = service.get(
        "부칙"
    )

    if raw is None:
        return []

    raw_units = normalize_to_list(
        raw
    )

    result = []

    for item in raw_units:

        if not isinstance(item, dict):
            continue

        result.append(
            {
                "key": "",
                "publication_date": text_value(
                    item.get(
                        "부칙공포일자"
                    )
                ),
                "publication_number": text_value(
                    item.get(
                        "부칙공포번호"
                    )
                ),
                "content": text_value(
                    item.get(
                        "부칙내용"
                    )
                ),
            }
        )

    return result


# ============================================================
# 국가법령 부칙 정규화
# ============================================================

def normalize_law_addenda(law: dict) -> list:

    container = law.get(
        "부칙",
        {}
    )

    if not isinstance(container, dict):
        return []

    raw_units = normalize_to_list(
        container.get(
            "부칙단위"
        )
    )

    result = []

    for item in raw_units:

        if not isinstance(item, dict):
            continue

        result.append(
            {
                "key": text_value(
                    item.get(
                        "부칙키"
                    )
                ),
                "publication_date": text_value(
                    item.get(
                        "부칙공포일자"
                    )
                ),
                "publication_number": text_value(
                    item.get(
                        "부칙공포번호"
                    )
                ),
                "content": text_value(
                    item.get(
                        "부칙내용"
                    )
                ),
            }
        )

    return result


# ============================================================
# 전체 상세 데이터 정규화
# ============================================================

def normalize_detail(
    data: dict,
    target_info: dict,
) -> dict | None:

    target = target_info["target"]

    # ========================================================
    # 자치법규
    # ========================================================

    if target == "ordin":

        service = data.get(
            "LawService"
        )

        if not isinstance(
            service,
            dict
        ):

            print(
                "ERROR: LawService 없음"
            )

            return None

        basic_info = (
            normalize_ordin_basic_info(
                service
            )
        )

        articles = (
            normalize_ordin_articles(
                service
            )
        )

        appendices = (
            normalize_ordin_appendices(
                service
            )
        )

        addenda = (
            normalize_ordin_addenda(
                service
            )
        )

    # ========================================================
    # 국가법령
    # ========================================================

    elif target == "law":

        law = data.get(
            "법령"
        )

        if not isinstance(
            law,
            dict
        ):

            print(
                "ERROR: 법령 구조 없음"
            )

            return None

        basic_info = (
            normalize_law_basic_info(
                law
            )
        )

        articles = (
            normalize_law_articles(
                law
            )
        )

        appendices = (
            normalize_law_appendices(
                law
            )
        )

        addenda = (
            normalize_law_addenda(
                law
            )
        )

    else:

        return None

    # --------------------------------------------------------
    # API 기본정보에 없는 MST는
    # 검색 단계에서 확보한 값을 넣는다.
    # --------------------------------------------------------

    if not basic_info.get("mst"):

        basic_info["mst"] = (
            target_info["mst"]
        )

    return {
        "level": target_info["level"],
        "hierarchy_type": (
            target_info["type_name"]
        ),
        "target": target,
        "basic_info": basic_info,
        "articles": articles,
        "appendices": appendices,
        "addenda": addenda,
    }


# ============================================================
# API 요청
# ============================================================

def request_detail(
    target_info: dict,
) -> dict | None:

    params = {
        "OC": SERVICE_KEY,
        "target": target_info[
            "target"
        ],
        "type": "JSON",
        "MST": target_info[
            "mst"
        ],
    }

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30,
    )

    print(
        "HTTP 상태코드:",
        response.status_code,
    )

    response.raise_for_status()

    data = response.json()

    if (
        isinstance(data, dict)
        and "result" in data
        and "msg" in data
    ):

        print(
            "API 오류:",
            data.get("result")
        )

        print(
            "msg:",
            data.get("msg")
        )

        return None

    return data


# ============================================================
# 결과 출력
# ============================================================

def print_result(
    normalized: dict,
):

    info = normalized[
        "basic_info"
    ]

    articles = normalized[
        "articles"
    ]

    appendices = normalized[
        "appendices"
    ]

    addenda = normalized[
        "addenda"
    ]

    print()
    print("=" * 70)

    print(
        f"LEVEL {normalized['level']} "
        f"| {normalized['hierarchy_type']}"
    )

    print("=" * 70)

    print(
        "법규명:",
        info.get("name")
    )

    print(
        "법규ID:",
        info.get("law_id")
    )

    print(
        "MST:",
        info.get("mst")
    )

    print(
        "기관:",
        info.get("organization")
    )

    print(
        "법규종류:",
        info.get("law_type")
    )

    print(
        "시행일자:",
        info.get("effective_date")
    )

    print(
        "공포일자:",
        info.get("publication_date")
    )

    print()

    print(
        "조문 수:",
        len(articles)
    )

    print(
        "별표/서식 수:",
        len(appendices)
    )

    print(
        "부칙 수:",
        len(addenda)
    )

    # --------------------------------------------------------
    # 실제 조문만 개수 확인
    # --------------------------------------------------------

    real_articles = [
        article
        for article in articles
        if article[
            "article_status"
        ] in (
            "Y",
            "조문",
        )
    ]

    print(
        "실제 조문 판정 수:",
        len(real_articles)
    )

    # --------------------------------------------------------
    # 조문 샘플
    # --------------------------------------------------------

    print()
    print("--- 조문 샘플 ---")

    sample_count = 0

    for article in articles:

        content = article.get(
            "article_content",
            ""
        )

        if not content:
            continue

        print()

        number = article.get(
            "article_number",
            ""
        )

        branch = article.get(
            "article_branch_number",
            ""
        )

        title = article.get(
            "article_title",
            ""
        )

        if branch:

            display_number = (
                f"{number}의{branch}"
            )

        else:

            display_number = number

        print(
            f"조문번호: {display_number}"
        )

        print(
            f"제목: {title}"
        )

        preview = content[:200]

        print(
            f"내용: {preview}"
        )

        sample_count += 1

        if sample_count >= 3:
            break

    # --------------------------------------------------------
    # 별표 샘플
    # --------------------------------------------------------

    if appendices:

        print()
        print("--- 별표 샘플 ---")

        appendix = appendices[0]

        print(
            "번호:",
            appendix.get("number")
        )

        print(
            "제목:",
            appendix.get("title")
        )

        print(
            "구분:",
            appendix.get("type")
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-2 "
        "법규 상세 데이터 통합 정규화 테스트 ==="
    )

    print()

    print(
        "사용 인증키 환경변수:",
        SERVICE_KEY_NAME,
    )

    print(
        "인증키 값: [HIDDEN]"
    )

    normalized_results = []

    # ========================================================
    # 법규 조회 / 정규화
    # ========================================================

    for target_info in TARGETS:

        print()
        print()
        print("=" * 70)

        print(
            f"조회 시작 | "
            f"LEVEL {target_info['level']}"
        )

        print(
            target_info["name"]
        )

        print("=" * 70)

        try:

            data = request_detail(
                target_info
            )

        except Exception as exc:

            print(
                "조회 실패:",
                exc
            )

            continue

        if data is None:
            continue

        normalized = normalize_detail(
            data,
            target_info,
        )

        if normalized is None:
            continue

        normalized_results.append(
            normalized
        )

        print_result(
            normalized
        )

    # ========================================================
    # 통합 결과
    # ========================================================

    print()
    print()
    print("=" * 70)

    print(
        "=== STEP 17-21-C-2 "
        "통합 정규화 결과 ==="
    )

    print("=" * 70)

    total_articles = sum(
        len(item["articles"])
        for item in normalized_results
    )

    total_appendices = sum(
        len(item["appendices"])
        for item in normalized_results
    )

    total_addenda = sum(
        len(item["addenda"])
        for item in normalized_results
    )

    print(
        "정규화 성공 법규:",
        f"{len(normalized_results)} "
        f"/ {len(TARGETS)}"
    )

    print(
        "전체 조문:",
        total_articles
    )

    print(
        "전체 별표/서식:",
        total_appendices
    )

    print(
        "전체 부칙:",
        total_addenda
    )

    print()

    for item in normalized_results:

        info = item["basic_info"]

        print(
            f"LEVEL {item['level']} | "
            f"{item['hierarchy_type']} | "
            f"{info.get('name')}"
        )

        print(
            f"  조문: "
            f"{len(item['articles'])}"
        )

        print(
            f"  별표: "
            f"{len(item['appendices'])}"
        )

        print(
            f"  부칙: "
            f"{len(item['addenda'])}"
        )

    print()

    if (
        len(normalized_results)
        == len(TARGETS)
    ):

        print(
            "4개 법규 계층 "
            "통합 정규화 성공"
        )

        print()
        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-3"
        )

        print(
            "→ 통합 법규 데이터에서 "
            "건폐율/용적률/용도지역 등 "
            "핵심 조문 자동 검색"
        )

    else:

        print(
            "일부 법규 정규화 실패"
        )

    print()
    print("=" * 70)

    print(
        "STEP 17-21-C-2 완료"
    )

    print("=" * 70)


if __name__ == "__main__":
    main()