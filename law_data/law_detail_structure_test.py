import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-1
# 자치법규 / 국가법령 상세 JSON 구조 분석
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


# ------------------------------------------------------------
# 인증키
# ------------------------------------------------------------

# 기존 프로젝트에서 사용 중인 환경변수명을 우선적으로 찾는다.
# 실제 키 값은 절대 출력하지 않는다.
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
        "법령 API 인증키를 찾을 수 없습니다.\n"
        f"확인한 환경변수: {', '.join(POSSIBLE_KEY_NAMES)}\n"
        "현재 프로젝트에서 사용 중인 실제 환경변수명을 "
        "POSSIBLE_KEY_NAMES에 추가하세요."
    )


# ------------------------------------------------------------
# API 설정
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


# ------------------------------------------------------------
# 테스트 대상
# ------------------------------------------------------------

TARGETS = [
    {
        "level": 1,
        "type_name": "자치구 조례",
        "name": "서울특별시 강남구 도시계획 조례",
        "target": "ordin",
        "MST": "1592205",
    },
    {
        "level": 2,
        "type_name": "서울특별시 조례",
        "name": "서울특별시 도시계획 조례",
        "target": "ordin",
        "MST": "2149501",
    },
    {
        "level": 3,
        "type_name": "국가 법률",
        "name": "국토의 계획 및 이용에 관한 법률",
        "target": "law",
        "MST": "284013",
    },
    {
        "level": 4,
        "type_name": "국가 시행령",
        "name": "국토의 계획 및 이용에 관한 법률 시행령",
        "target": "law",
        "MST": "287269",
    },
]


# ============================================================
# 공통 유틸
# ============================================================


def normalize_to_list(value: Any) -> list:
    """
    API에서 단일 객체일 경우 dict,
    여러 객체일 경우 list로 내려오는 구조를 통일한다.
    """

    if value is None:
        return []

    if isinstance(value, list):
        return value

    return [value]


def short_value(value: Any, limit: int = 160) -> str:
    """
    너무 긴 문자열이 콘솔을 가득 채우지 않도록 축약한다.
    """

    text = repr(value)

    if len(text) > limit:
        return text[:limit] + "..."

    return text


def print_separator(char="=", length=70):
    print(char * length)


# ============================================================
# JSON 구조 분석
# ============================================================


def analyze_structure(
    data: Any,
    path: str = "ROOT",
    depth: int = 0,
    max_depth: int = 5,
):
    """
    JSON 구조를 재귀적으로 분석한다.

    목적:
    - dict/list 위치 확인
    - 조문 구조 확인
    - 별표 구조 확인
    - 기본정보 구조 확인

    데이터 전체 내용을 출력하지 않고 구조 위주로 출력한다.
    """

    indent = "  " * depth

    if depth > max_depth:
        print(f"{indent}{path}: [MAX DEPTH]")
        return

    if isinstance(data, dict):

        print(
            f"{indent}{path} "
            f"| TYPE=dict "
            f"| KEYS={list(data.keys())}"
        )

        for key, value in data.items():

            child_path = f"{path}.{key}"

            if isinstance(value, (dict, list)):
                analyze_structure(
                    value,
                    child_path,
                    depth + 1,
                    max_depth,
                )

            else:
                print(
                    f"{indent}  {child_path} "
                    f"| TYPE={type(value).__name__} "
                    f"| VALUE={short_value(value)}"
                )

    elif isinstance(data, list):

        print(
            f"{indent}{path} "
            f"| TYPE=list "
            f"| LENGTH={len(data)}"
        )

        if data:

            # 모든 항목을 출력하면 국가법령은 매우 커지므로
            # 첫 번째 항목의 구조만 확인한다.
            print(
                f"{indent}  "
                f"첫 번째 항목 구조 분석"
            )

            analyze_structure(
                data[0],
                f"{path}[0]",
                depth + 1,
                max_depth,
            )

    else:

        print(
            f"{indent}{path} "
            f"| TYPE={type(data).__name__} "
            f"| VALUE={short_value(data)}"
        )


# ============================================================
# 키 검색
# ============================================================


def find_keys(
    data: Any,
    keywords: list[str],
    path: str = "ROOT",
    results: list | None = None,
):
    """
    JSON 전체에서 특정 키워드를 포함하는 key의 위치를 찾는다.
    """

    if results is None:
        results = []

    if isinstance(data, dict):

        for key, value in data.items():

            current_path = f"{path}.{key}"

            for keyword in keywords:

                if keyword in str(key):

                    results.append(
                        {
                            "keyword": keyword,
                            "key": key,
                            "path": current_path,
                            "type": type(value).__name__,
                        }
                    )

                    break

            find_keys(
                value,
                keywords,
                current_path,
                results,
            )

    elif isinstance(data, list):

        # 동일 구조의 대량 조문이 있을 수 있으므로
        # 구조 검색에서는 최대 3개까지만 확인
        for index, item in enumerate(data[:3]):

            find_keys(
                item,
                keywords,
                f"{path}[{index}]",
                results,
            )

    return results


# ============================================================
# 자치법규 구조 분석
# ============================================================


def analyze_ordinance(data: dict):
    """
    target=ordin 상세 응답 분석
    """

    print()
    print_separator()
    print("=== 자치법규 상세 구조 분석 ===")
    print_separator()

    law_service = data.get("LawService")

    if not isinstance(law_service, dict):

        print("ERROR: LawService 구조를 찾을 수 없습니다.")
        return False

    print()
    print("LawService 발견")
    print("LawService 키:")
    print(list(law_service.keys()))

    print()
    print("--- 자치법규 기본정보 ---")

    basic_info = law_service.get("자치법규기본정보")

    if isinstance(basic_info, dict):

        print("TYPE: dict")
        print("KEYS:")
        print(list(basic_info.keys()))

        print()
        print("주요 값:")

        important_keys = [
            "자치법규명",
            "자치법규ID",
            "자치법규일련번호",
            "지자체기관명",
            "시행일자",
            "공포일자",
            "제개정정보",
        ]

        for key in important_keys:

            if key in basic_info:
                print(f"{key}: {basic_info.get(key)}")

    else:
        print(
            "기본정보 TYPE:",
            type(basic_info).__name__,
        )

    print()
    print("--- 조문 구조 ---")

    articles = law_service.get("조문")

    if articles is None:

        print("조문 없음")

    else:

        print("조문 TYPE:", type(articles).__name__)

        if isinstance(articles, dict):

            print("조문 KEYS:")
            print(list(articles.keys()))

            article_data = articles.get("조")

            normalized_articles = normalize_to_list(
                article_data
            )

            print(
                "정규화된 조문 수:",
                len(normalized_articles),
            )

            if normalized_articles:

                first = normalized_articles[0]

                print()
                print("첫 번째 조문 TYPE:")
                print(type(first).__name__)

                if isinstance(first, dict):

                    print("첫 번째 조문 KEYS:")
                    print(list(first.keys()))

                    print()
                    print("첫 번째 조문 주요 값:")

                    for key in [
                        "조문번호",
                        "조제목",
                        "조내용",
                        "조문여부",
                    ]:

                        if key in first:
                            print(
                                f"{key}: "
                                f"{short_value(first.get(key), 300)}"
                            )

    print()
    print("--- 별표 구조 ---")

    appendix = law_service.get("별표")

    if appendix is None:

        print("별표 없음")

    else:

        print("별표 TYPE:", type(appendix).__name__)

        if isinstance(appendix, dict):

            print("별표 KEYS:")
            print(list(appendix.keys()))

            appendix_data = appendix.get("별표단위")

            normalized_appendix = normalize_to_list(
                appendix_data
            )

            print(
                "정규화된 별표/서식 수:",
                len(normalized_appendix),
            )

            if normalized_appendix:

                first = normalized_appendix[0]

                if isinstance(first, dict):

                    print("첫 번째 별표 KEYS:")
                    print(list(first.keys()))

    print()
    print("--- 부칙 구조 ---")

    supplementary = law_service.get("부칙")

    print(
        "부칙 TYPE:",
        type(supplementary).__name__,
    )

    if isinstance(supplementary, dict):

        print("부칙 KEYS:")
        print(list(supplementary.keys()))

    return True


# ============================================================
# 국가법령 구조 분석
# ============================================================


def analyze_national_law(data: dict):
    """
    target=law 상세 응답 분석
    """

    print()
    print_separator()
    print("=== 국가법령 상세 구조 분석 ===")
    print_separator()

    law = data.get("법령")

    if not isinstance(law, dict):

        print("ERROR: '법령' 구조를 찾을 수 없습니다.")
        return False

    print()
    print("'법령' 발견")
    print("법령 최상위 키:")
    print(list(law.keys()))

    print()
    print("--- 핵심 키 자동 검색 ---")

    keywords = [
        "기본정보",
        "조문",
        "조문단위",
        "조",
        "항",
        "호",
        "목",
        "별표",
        "서식",
        "부칙",
        "법령명",
        "법령ID",
        "법령일련번호",
    ]

    results = find_keys(
        law,
        keywords,
    )

    seen = set()

    for result in results:

        signature = (
            result["keyword"],
            result["path"],
        )

        if signature in seen:
            continue

        seen.add(signature)

        print(
            f"[{result['keyword']}] "
            f"{result['path']} "
            f"| TYPE={result['type']}"
        )

    print()
    print("--- 국가법령 전체 구조 ---")
    print(
        "※ 대량 본문 출력을 막기 위해 "
        "list는 첫 번째 항목만 분석합니다."
    )

    analyze_structure(
        law,
        path="ROOT.법령",
        max_depth=5,
    )

    return True


# ============================================================
# API 요청
# ============================================================


def request_detail(item: dict):
    """
    상세 API 요청
    """

    params = {
        "OC": SERVICE_KEY,
        "target": item["target"],
        "type": "JSON",
        "MST": item["MST"],
    }

    print()
    print("API 요청 중...")
    print(f"target: {item['target']}")
    print(f"MST: {item['MST']}")
    print("OC: [HIDDEN]")

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

    print(
        "Content-Type:",
        response.headers.get(
            "Content-Type",
            "",
        ),
    )

    print(
        "응답 크기:",
        len(response.content),
        "bytes",
    )

    response.raise_for_status()

    try:

        data = response.json()

    except Exception as exc:

        print(
            "ERROR: JSON 파싱 실패:",
            exc,
        )

        print()
        print("응답 일부:")
        print(response.text[:1000])

        return None

    print("JSON 파싱 성공")

    if isinstance(data, dict):

        print(
            "최상위 키:",
            list(data.keys()),
        )

    else:

        print(
            "최상위 TYPE:",
            type(data).__name__,
        )

    # API 인증 오류 구조 검사
    if (
        isinstance(data, dict)
        and "result" in data
        and "msg" in data
    ):

        print()
        print("!!! API 오류 응답 !!!")
        print("result:", data.get("result"))
        print("msg:", data.get("msg"))

        return None

    return data


# ============================================================
# MAIN
# ============================================================


def main():

    print(
        "=== STEP 17-21-C-1 "
        "법규 상세 JSON 구조 분석 ==="
    )

    print()
    print(
        "사용 인증키 환경변수:",
        SERVICE_KEY_NAME,
    )

    print(
        "인증키 값:",
        "[HIDDEN]",
    )

    print()
    print(
        "분석 대상:",
        len(TARGETS),
        "개 법규",
    )

    success_count = 0

    national_structure_found = False

    for item in TARGETS:

        print()
        print()
        print_separator()
        print(
            f"LEVEL {item['level']} | "
            f"{item['type_name']}"
        )
        print(item["name"])
        print_separator()

        try:

            data = request_detail(item)

        except requests.RequestException as exc:

            print(
                "HTTP 요청 실패:",
                exc,
            )

            continue

        if data is None:
            continue

        if item["target"] == "ordin":

            success = analyze_ordinance(data)

        elif item["target"] == "law":

            success = analyze_national_law(data)

            if success:
                national_structure_found = True

        else:

            print(
                "지원하지 않는 target:",
                item["target"],
            )

            success = False

        if success:
            success_count += 1

    print()
    print()
    print_separator()
    print(
        "=== STEP 17-21-C-1 결과 요약 ==="
    )
    print_separator()

    print(
        f"구조 분석 성공: "
        f"{success_count} / {len(TARGETS)}"
    )

    print()

    if national_structure_found:

        print(
            "국가법령 '법령' 구조 확인 성공"
        )

        print()
        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-2"
        )

        print(
            "→ 자치법규와 국가법령의 "
            "조문 구조를 표준 데이터 구조로 정규화"
        )

    else:

        print(
            "국가법령 구조를 확인하지 못했습니다."
        )

        print(
            "출력된 실제 JSON 구조를 기준으로 "
            "추가 분석이 필요합니다."
        )

    print()
    print_separator()
    print(
        "STEP 17-21-C-1 완료"
    )
    print_separator()


if __name__ == "__main__":
    main()