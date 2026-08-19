import os
import sys
import requests
from dotenv import load_dotenv


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
# STEP 17-15에서 확인한 값 사용
# --------------------------------------------------

TARGET_REGION = "서울특별시 강남구"

ORDINANCE_NAME = "서울특별시 강남구 도시계획 조례"

LAW_ID = "2072371"

MST = "1592205"


# --------------------------------------------------
# API
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawService.do"

params = {
    "OC": LAW_API_KEY,
    "target": "ordin",
    "MST": MST,
    "type": "JSON",
}


# --------------------------------------------------
# 핵심 법규 분류
# --------------------------------------------------

KEYWORD_GROUPS = {

    "건폐율": [
        "건폐율",
    ],

    "용적률": [
        "용적률",
    ],

    "용도지역": [
        "용도지역",
    ],

    "용도지구": [
        "용도지구",
    ],

    "용도구역": [
        "용도구역",
    ],

    "건축물용도": [
        "건축물의 용도",
        "건축물 용도",
    ],

    "높이": [
        "높이",
        "최고높이",
    ],

    "대지": [
        "대지",
    ],

    "도로": [
        "도로",
        "도로에 접",
        "도로의 너비",
    ],

    "개발행위": [
        "개발행위",
    ],

    "도시계획": [
        "도시계획",
        "도시관리계획",
    ],

    "지구단위계획": [
        "지구단위계획",
    ],

    "도시계획위원회": [
        "도시계획위원회",
    ],

    "주차": [
        "주차",
    ],
}


# --------------------------------------------------
# API 요청
# --------------------------------------------------

print("=== STEP 17-17 핵심 법규 조문 정밀 추출 테스트 ===")
print()

print(f"대상 지역: {TARGET_REGION}")
print(f"대상 조례: {ORDINANCE_NAME}")
print(f"자치법규ID: {LAW_ID}")
print(f"자치법규일련번호(MST): {MST}")

print()
print("=" * 70)

print()
print("API 요청 중...")


try:

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

except requests.RequestException as e:

    print("ERROR: API 요청 실패")
    print(e)
    sys.exit(1)


print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

try:

    data = response.json()

except ValueError:

    print("ERROR: JSON 응답을 파싱할 수 없습니다.")
    print(response.text[:1000])
    sys.exit(1)


print("API 요청 성공")
print("JSON 응답 확인 성공")


# --------------------------------------------------
# 응답 구조
# --------------------------------------------------

law_service = data.get("LawService", {})

if not law_service:

    print()
    print("ERROR: LawService 데이터를 찾을 수 없습니다.")
    print(data)
    sys.exit(1)


articles_data = law_service.get("조문", {})

articles = articles_data.get("조", [])


# --------------------------------------------------
# 조문 데이터 정규화
# --------------------------------------------------

normalized_articles = []


for article in articles:

    article_numbers = article.get("조문번호", [])

    if isinstance(article_numbers, list):

        if len(article_numbers) > 0:
            article_number = article_numbers[0]
        else:
            article_number = ""

    else:

        article_number = str(article_numbers)


    title = article.get("조제목", "")
    content = article.get("조내용", "")
    is_article = article.get("조문여부", "")


    normalized_articles.append({
        "조문번호": article_number,
        "조제목": title,
        "조내용": content,
        "조문여부": is_article,
    })


# --------------------------------------------------
# 전체 조문 확인
# --------------------------------------------------

print()
print("=== 조문 데이터 확인 ===")
print("전체 조문 수:", len(normalized_articles))


# --------------------------------------------------
# 핵심 조문 검색
# --------------------------------------------------

matched_articles = []


for article in normalized_articles:

    content = article["조내용"] or ""
    title = article["조제목"] or ""

    search_text = title + " " + content

    matched_groups = []

    for group_name, keywords in KEYWORD_GROUPS.items():

        matched_keywords = []

        for keyword in keywords:

            if keyword in search_text:
                matched_keywords.append(keyword)

        if matched_keywords:

            matched_groups.append({
                "분류": group_name,
                "키워드": matched_keywords,
            })


    if matched_groups:

        matched_articles.append({
            "조문번호": article["조문번호"],
            "조제목": article["조제목"],
            "조내용": article["조내용"],
            "분류": matched_groups,
        })


# --------------------------------------------------
# 검색 결과 출력
# --------------------------------------------------

print()
print("=" * 70)
print("=== 핵심 법규 조문 검색 결과 ===")
print("검색된 조문 수:", len(matched_articles))


for index, article in enumerate(
    matched_articles,
    start=1
):

    print()
    print("-" * 70)

    print(f"결과 {index}")
    print(
        f"조문번호: {article['조문번호']}"
    )

    print(
        f"조문제목: {article['조제목']}"
    )

    print()
    print("분류:")

    for group in article["분류"]:

        print(
            f"  - {group['분류']}: "
            f"{', '.join(group['키워드'])}"
        )

    print()
    print("조문내용:")

    print(article["조내용"])


# --------------------------------------------------
# 분류별 결과 요약
# --------------------------------------------------

print()
print("=" * 70)
print("=== 분류별 검색 결과 ===")


for group_name in KEYWORD_GROUPS:

    group_articles = []

    for article in matched_articles:

        for group in article["분류"]:

            if group["분류"] == group_name:

                group_articles.append(article)
                break


    print()
    print(f"[{group_name}]")
    print(f"관련 조문 수: {len(group_articles)}")

    if group_articles:

        for article in group_articles:

            print(
                f"  - 제{article['조문번호']} "
                f"{article['조제목']}"
            )

    else:

        print("  → 관련 조문 없음")


# --------------------------------------------------
# STEP 완료
# --------------------------------------------------

print()
print("=" * 70)
print("STEP 17-17 완료")
print("=" * 70)