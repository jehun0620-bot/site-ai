import os
import sys
import requests
from dotenv import load_dotenv


# ==================================================
# STEP 17-19
# 자치법규 상세 데이터 정규화 테스트
# ==================================================


# --------------------------------------------------
# 프로젝트 루트
# --------------------------------------------------

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


# --------------------------------------------------
# 환경변수
# --------------------------------------------------

load_dotenv(
    os.path.join(BASE_DIR, ".env")
)

LAW_API_KEY = os.getenv("LAW_API_KEY")

if not LAW_API_KEY:
    print("ERROR: 국가법령정보 API 인증키를 찾을 수 없습니다.")
    sys.exit(1)


# --------------------------------------------------
# 대상 조례
# --------------------------------------------------

TARGET_REGION = "서울특별시 강남구"

TARGET_ORDINANCE = "서울특별시 강남구 도시계획 조례"

ORDINANCE_ID = "2072371"

MST = "1592205"


# --------------------------------------------------
# API
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawService.do"


# ==================================================
# 시작
# ==================================================

print("=== STEP 17-19 자치법규 상세 데이터 정규화 테스트 ===")

print()
print("대상 지역:", TARGET_REGION)
print("대상 조례:", TARGET_ORDINANCE)
print("자치법규ID:", ORDINANCE_ID)
print("자치법규일련번호(MST):", MST)

print()
print("=" * 70)
print()


# ==================================================
# API 요청
# ==================================================

params = {
    "OC": LAW_API_KEY,
    "target": "ordin",
    "MST": MST,
    "type": "JSON",
}


print("API 요청 중...")


try:

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

except requests.RequestException as e:

    print()
    print("ERROR: API 요청 중 오류가 발생했습니다.")
    print(e)

    sys.exit(1)


print("HTTP 상태코드:", response.status_code)


try:

    response.raise_for_status()

except requests.HTTPError as e:

    print()
    print("ERROR: HTTP 오류가 발생했습니다.")
    print(e)

    sys.exit(1)


# ==================================================
# JSON 응답
# ==================================================

try:

    data = response.json()

except ValueError:

    print()
    print("ERROR: JSON 응답으로 변환할 수 없습니다.")
    print(response.text[:1000])

    sys.exit(1)


print("API 요청 성공")
print("JSON 응답 확인 성공")


# ==================================================
# 최상위 구조
# ==================================================

print()
print("=== API 응답 구조 ===")

print("최상위 키:", data.keys())


law_service = data.get(
    "LawService",
    {}
)


if not isinstance(law_service, dict):

    print()
    print("ERROR: LawService 구조가 예상과 다릅니다.")

    sys.exit(1)


print("LawService 타입:", type(law_service))
print("LawService 키:", law_service.keys())


# ==================================================
# 1. 기본정보
# ==================================================

basic_info = law_service.get(
    "자치법규기본정보",
    {}
)


print()
print("=" * 70)
print("=== 1. 자치법규 기본정보 ===")
print("=" * 70)


if isinstance(basic_info, dict):

    print("자치법규명:",
          basic_info.get("자치법규명"))

    print("자치법규ID:",
          basic_info.get("자치법규ID"))

    print("자치법규일련번호:",
          basic_info.get("자치법규일련번호"))

    print("지자체기관명:",
          basic_info.get("지자체기관명"))

    print("시행일자:",
          basic_info.get("시행일자"))

    print("공포일자:",
          basic_info.get("공포일자"))

    print("제개정정보:",
          basic_info.get("제개정정보"))

    print("자치법규종류:",
          basic_info.get("자치법규종류"))

else:

    print("기본정보 구조 오류")


# ==================================================
# 2. 조문 데이터
# ==================================================

article_data = law_service.get(
    "조문",
    {}
)


print()
print("=" * 70)
print("=== 2. 조문 데이터 ===")
print("=" * 70)


articles = []


if isinstance(article_data, dict):

    raw_articles = article_data.get(
        "조",
        []
    )

    if isinstance(raw_articles, dict):

        articles = [raw_articles]

    elif isinstance(raw_articles, list):

        articles = raw_articles


print("전체 조문 수:", len(articles))


# ==================================================
# 조문 정규화
# ==================================================

normalized_articles = []


for article in articles:

    if not isinstance(article, dict):
        continue


    article_number = article.get(
        "조문번호",
        ""
    )


    article_title = article.get(
        "조제목",
        ""
    )


    article_content = article.get(
        "조내용",
        ""
    )


    article_flag = article.get(
        "조문여부",
        ""
    )


    # 조문번호가 list인 경우
    if isinstance(article_number, list):

        if article_number:
            article_number = article_number[0]

        else:
            article_number = ""


    normalized_article = {

        "article_number": article_number,

        "article_title": article_title,

        "article_content": article_content,

        "article_flag": article_flag,

    }


    normalized_articles.append(
        normalized_article
    )


print("정규화된 조문 수:",
      len(normalized_articles))


# ==================================================
# 3. 별표 데이터
# ==================================================

appendix_data = law_service.get(
    "별표",
    {}
)


print()
print("=" * 70)
print("=== 3. 별표 데이터 ===")
print("=" * 70)


appendices = []


if isinstance(appendix_data, dict):

    appendix_unit = appendix_data.get(
        "별표단위"
    )


    if isinstance(appendix_unit, dict):

        appendices.append(
            appendix_unit
        )


    elif isinstance(appendix_unit, list):

        appendices.extend(
            appendix_unit
        )


print("별표/서식 수:",
      len(appendices))


for index, appendix in enumerate(
    appendices,
    start=1
):

    print()
    print("-" * 60)
    print("별표/서식:", index)

    print(
        "제목:",
        appendix.get("별표제목", "")
    )

    print(
        "번호:",
        appendix.get("별표번호", "")
    )

    print(
        "구분:",
        appendix.get("별표구분", "")
    )

    print(
        "내용:",
        appendix.get("별표내용", "")
    )

    print(
        "첨부파일:",
        appendix.get("별표첨부파일명", "")
    )


# ==================================================
# 4. 부칙
# ==================================================

supplementary = law_service.get(
    "부칙",
    {}
)


print()
print("=" * 70)
print("=== 4. 부칙 데이터 ===")
print("=" * 70)


if isinstance(supplementary, dict):

    supplementary_date = supplementary.get(
        "부칙공포일자",
        ""
    )

    supplementary_content = supplementary.get(
        "부칙내용",
        ""
    )

    print(
        "부칙공포일자:",
        supplementary_date
    )

    print(
        "부칙내용:",
        supplementary_content
    )


# ==================================================
# 5. 법규 검토용 핵심 키워드 분석
# ==================================================

KEYWORDS = {

    "건폐율": [
        "건폐율"
    ],

    "용적률": [
        "용적률"
    ],

    "용도지역": [
        "용도지역"
    ],

    "용도지구": [
        "용도지구"
    ],

    "용도구역": [
        "용도구역"
    ],

    "건축물용도": [
        "건축물",
        "용도"
    ],

    "높이": [
        "높이"
    ],

    "대지": [
        "대지"
    ],

    "도로": [
        "도로"
    ],

    "개발행위": [
        "개발행위"
    ],

    "지구단위계획": [
        "지구단위계획"
    ],

    "주차": [
        "주차"
    ],

}


# ==================================================
# 키워드별 조문 검색
# ==================================================

print()
print("=" * 70)
print("=== 5. 핵심 법규 키워드 분석 ===")
print("=" * 70)


keyword_results = {}


for category, keywords in KEYWORDS.items():

    matched = []


    for article in normalized_articles:

        content = article.get(
            "article_content",
            ""
        )

        title = article.get(
            "article_title",
            ""
        )


        search_text = (
            title + " " + content
        )


        found = False


        for keyword in keywords:

            if keyword in search_text:

                found = True
                break


        if found:

            matched.append(
                article
            )


    keyword_results[category] = matched


    print()
    print(
        f"[{category}]"
    )

    print(
        "관련 조문 수:",
        len(matched)
    )


    for article in matched:

        print(
            "  - 제"
            + str(
                article.get(
                    "article_number",
                    ""
                )
            )
            + " "
            + str(
                article.get(
                    "article_title",
                    ""
                )
            )
        )


# ==================================================
# 6. 정규화 결과 요약
# ==================================================

print()
print("=" * 70)
print("=== STEP 17-19 정규화 결과 요약 ===")
print("=" * 70)


print()
print("대상 조례:",
      TARGET_ORDINANCE)

print("MST:",
      MST)

print("조문 수:",
      len(normalized_articles))

print("별표/서식 수:",
      len(appendices))


print()
print("=== 핵심 법규 분류 ===")


for category, matched in keyword_results.items():

    print(
        f"{category}: {len(matched)}개 조문"
    )


print()
print("=" * 70)
print("STEP 17-19 완료")
print("=" * 70)