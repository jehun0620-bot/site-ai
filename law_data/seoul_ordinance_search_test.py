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
# 테스트 대상
# --------------------------------------------------

TEST_CITY = "서울특별시"
TEST_DISTRICT = "강남구"

TARGET_AGENCY = f"{TEST_CITY} {TEST_DISTRICT}"
TARGET_ORDINANCE_NAME = f"{TARGET_AGENCY} 도시계획 조례"


# --------------------------------------------------
# 국가법령정보 자치법규 API
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawSearch.do"

params = {
    "OC": LAW_API_KEY,
    "target": "ordin",
    "type": "JSON",
    "nw": 1,
    "query": "서울특별시 도시계획 조례",
    "display": 100,
    "page": 1,
}


# --------------------------------------------------
# API 요청
# --------------------------------------------------

print("=== STEP 17-14 자치구 도시계획 조례 선택 테스트 ===")
print()
print("대상 지역:", TARGET_AGENCY)
print("검색 조례:", TARGET_ORDINANCE_NAME)
print()
print("API 요청 중...")


response = requests.get(
    URL,
    params=params,
    timeout=30
)


print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()

print("API 요청 성공")
print("JSON 응답 확인 성공")


# --------------------------------------------------
# 응답 구조
# --------------------------------------------------

ordin_search = data.get("OrdinSearch", {})

ordinances = ordin_search.get("law", [])

print()
print("=== API 검색 결과 ===")
print("전체 검색 결과:", ordin_search.get("totalCnt"))
print("현재 페이지 결과:", len(ordinances))


# --------------------------------------------------
# 대상 자치구 조례 찾기
# --------------------------------------------------

selected_ordinance = None

for ordinance in ordinances:

    ordinance_name = ordinance.get("자치법규명", "")
    agency_name = ordinance.get("지자체기관명", "")

    if (
        ordinance_name == TARGET_ORDINANCE_NAME
        and agency_name == TARGET_AGENCY
    ):
        selected_ordinance = ordinance
        break


# --------------------------------------------------
# 결과 출력
# --------------------------------------------------

print()
print("=== 대상 자치구 조례 선택 결과 ===")

if selected_ordinance is None:

    print("조례를 찾지 못했습니다.")

    print()
    print("검색된 서울특별시 도시계획 조례 목록:")

    for ordinance in ordinances:

        ordinance_name = ordinance.get("자치법규명", "")
        agency_name = ordinance.get("지자체기관명", "")

        if "도시계획 조례" in ordinance_name:

            print(
                f"- {agency_name} / {ordinance_name}"
            )

    sys.exit(1)


print("조례 선택 성공")
print()
print("자치법규명:",
      selected_ordinance.get("자치법규명"))

print("자치법규ID:",
      selected_ordinance.get("자치법규ID"))

print("자치법규일련번호:",
      selected_ordinance.get("자치법규일련번호"))

print("지자체기관명:",
      selected_ordinance.get("지자체기관명"))

print("자치법규종류:",
      selected_ordinance.get("자치법규종류"))

print("시행일자:",
      selected_ordinance.get("시행일자"))

print("공포일자:",
      selected_ordinance.get("공포일자"))

print("자치법규상세링크:",
      selected_ordinance.get("자치법규상세링크"))


print()
print("=" * 70)
print("STEP 17-14 완료")
print("=" * 70)