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
# 기본 설정
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawSearch.do"

TARGET_REGION = "서울특별시 강남구"

TARGET_ORDINANCE = "서울특별시 강남구 도시계획 조례"

SEARCH_KEYWORDS = [
    "건폐율",
    "용적률",
    "용도지역",
    "국토의 계획 및 이용에 관한 법률",
    "서울특별시 도시계획 조례",
]


# --------------------------------------------------
# 자치법규 본문 검색 함수
# --------------------------------------------------

def search_ordinance_body(keyword):

    params = {
        "OC": LAW_API_KEY,
        "target": "ordin",
        "type": "JSON",

        # 현행
        "nw": 1,

        # 본문검색
        "search": 2,

        # 검색어
        "query": keyword,

        # 최대 100건
        "display": 100,

        "page": 1,
    }

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# --------------------------------------------------
# 결과에서 대상 자치구 필터링
# --------------------------------------------------

def extract_laws(data):

    ordin_search = data.get("OrdinSearch", {})

    laws = ordin_search.get("law", [])

    if isinstance(laws, dict):
        laws = [laws]

    return ordin_search, laws


# --------------------------------------------------
# 메인
# --------------------------------------------------

print("=== STEP 17-16 관련 법규 탐색 테스트 ===")
print()

print("대상 지역:", TARGET_REGION)
print("기준 조례:", TARGET_ORDINANCE)

print()
print("=" * 70)


all_results = {}


for keyword in SEARCH_KEYWORDS:

    print()
    print(f"=== 키워드 검색: {keyword} ===")
    print("API 요청 중...")

    try:

        data = search_ordinance_body(keyword)

    except Exception as e:

        print("API 요청 실패:", e)
        continue


    ordin_search, laws = extract_laws(data)

    print("전체 검색 결과:", ordin_search.get("totalCnt"))
    print("현재 페이지 결과:", len(laws))
    print("검색 범위:", ordin_search.get("section"))

    # --------------------------------------------------
    # 서울특별시 / 강남구 관련 결과만 우선 표시
    # --------------------------------------------------

    filtered = []

    for law in laws:

        org_name = law.get("지자체기관명", "")

        if (
            "서울특별시" in org_name
            or "강남구" in org_name
        ):
            filtered.append(law)


    all_results[keyword] = filtered


    print()
    print("=== 서울특별시 / 강남구 관련 결과 ===")
    print("검색 결과 수:", len(filtered))


    for index, law in enumerate(filtered[:10], start=1):

        print()
        print("-" * 60)
        print(f"결과 {index}")

        print(
            "자치법규명:",
            law.get("자치법규명")
        )

        print(
            "지자체기관명:",
            law.get("지자체기관명")
        )

        print(
            "자치법규ID:",
            law.get("자치법규ID")
        )

        print(
            "자치법규일련번호:",
            law.get("자치법규일련번호")
        )

        print(
            "시행일자:",
            law.get("시행일자")
        )

        print(
            "공포일자:",
            law.get("공포일자")
        )

        print(
            "상세링크:",
            law.get("자치법규상세링크")
        )


# --------------------------------------------------
# 요약
# --------------------------------------------------

print()
print("=" * 70)
print("=== STEP 17-16 검색 요약 ===")

for keyword, results in all_results.items():

    print()
    print(f"[{keyword}]")
    print("관련 결과:", len(results))

    # 대상 조례가 검색되었는지 확인
    target_found = False

    for law in results:

        if law.get("자치법규명") == TARGET_ORDINANCE:
            target_found = True
            break

    if target_found:
        print("→ 대상 조례 검색됨")
    else:
        print("→ 대상 조례 검색되지 않음")


print()
print("=" * 70)
print("STEP 17-16 1차 관련 법규 탐색 완료")
print("=" * 70)