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
# 대상 자치법규
# --------------------------------------------------

ORDINANCE_NAME = "서울특별시 강남구 도시계획 조례"
ORDINANCE_ID = "2072371"
MST = "1592205"


# --------------------------------------------------
# 국가법령정보 자치법규 상세 API
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawService.do"

params = {
    "OC": LAW_API_KEY,
    "target": "ordin",
    "type": "JSON",
    "MST": MST,
}


print("=== STEP 17-15 자치법규 상세 본문 조회 테스트 ===")
print()
print("대상 조례:", ORDINANCE_NAME)
print("자치법규ID:", ORDINANCE_ID)
print("자치법규일련번호(MST):", MST)
print()
print("API 요청 중...")


# --------------------------------------------------
# API 요청
# --------------------------------------------------

response = requests.get(
    URL,
    params=params,
    timeout=30
)


print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

print("API 요청 성공")


# --------------------------------------------------
# JSON 확인
# --------------------------------------------------

data = response.json()

print("JSON 응답 확인 성공")


# --------------------------------------------------
# 최상위 구조 확인
# --------------------------------------------------

print()
print("=== API 응답 최상위 키 ===")
print(data.keys())


# --------------------------------------------------
# 응답 전체 구조 확인
# --------------------------------------------------

print()
print("=== 상세 응답 구조 확인 ===")

if isinstance(data, dict):
    for key, value in data.items():

        print()
        print("KEY:", key)
        print("TYPE:", type(value).__name__)

        if isinstance(value, dict):
            print("SUB KEYS:", value.keys())

        elif isinstance(value, list):
            print("LIST LENGTH:", len(value))


# --------------------------------------------------
# JSON 일부 출력
# --------------------------------------------------

print()
print("=== API 응답 일부 확인 ===")

print(str(data)[:5000])


print()
print("=" * 70)
print("STEP 17-15 1차 상세 응답 확인 완료")
print("=" * 70)

# --------------------------------------------------
# STEP 17-15
# 건폐율 / 용적률 관련 조문 검색
# --------------------------------------------------

law_service = data.get("LawService", {})

article_data = law_service.get("조문", {})

articles = article_data.get("조", [])

print()
print("=== 조문 데이터 확인 ===")
print("전체 조문 수:", len(articles))

# --------------------------------------------------
# 키워드 검색
# --------------------------------------------------

keywords = [
    "건폐율",
    "용적률",
]


matched_articles = []


for article in articles:

    article_content = article.get("조내용", "")
    article_title = article.get("조제목", "")
    article_number = article.get("조문번호", "")

    if not article_content:
        continue

    matched_keywords = []

    for keyword in keywords:

        if keyword in article_content:
            matched_keywords.append(keyword)

    if matched_keywords:

        matched_articles.append({
            "조문번호": article_number,
            "조제목": article_title,
            "조내용": article_content,
            "검색키워드": matched_keywords,
        })


# --------------------------------------------------
# 검색 결과 출력
# --------------------------------------------------

print()
print("=== 건폐율 / 용적률 관련 조문 검색 결과 ===")
print("검색된 조문 수:", len(matched_articles))


for index, article in enumerate(
    matched_articles,
    start=1
):

    print()
    print("-" * 70)

    print("검색 결과:", index)
    print("조문번호:", article["조문번호"])
    print("조제목:", article["조제목"])
    print("검색키워드:", ", ".join(article["검색키워드"]))

    print()
    print("조문내용:")
    print(article["조내용"])


print()
print("=" * 70)
print("STEP 17-15 완료")
print("=" * 70)