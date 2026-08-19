import os
import sys
import requests
from dotenv import load_dotenv


# ==================================================
# STEP 17-18
# 최신 자치구 도시계획 조례 판별 테스트
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
# 대상 지역 / 조례
# --------------------------------------------------

TARGET_REGION = "서울특별시 강남구"

TARGET_ORDINANCE = "서울특별시 강남구 도시계획 조례"


# --------------------------------------------------
# 국가법령정보 자치법규 검색 API
# --------------------------------------------------

URL = "http://www.law.go.kr/DRF/lawSearch.do"


# --------------------------------------------------
# API 요청 파라미터
# --------------------------------------------------

params = {
    "OC": LAW_API_KEY,
    "target": "ordin",
    "type": "JSON",

    # 정확한 조례명 검색
    "query": TARGET_ORDINANCE,

    # 자치법규명 기준 검색
    "section": "ordinNm",

    # 충분한 결과 확보
    "display": 100,
    "page": 1,
}


# ==================================================
# 시작
# ==================================================

print("=== STEP 17-18 최신 자치구 도시계획 조례 판별 테스트 ===")
print()
print(f"대상 지역: {TARGET_REGION}")
print(f"검색 조례: {TARGET_ORDINANCE}")

print()
print("=" * 70)
print()


# ==================================================
# API 요청
# ==================================================

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


# --------------------------------------------------
# JSON 변환
# --------------------------------------------------

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
# API 응답 구조 확인
# ==================================================

print()
print("=== API 응답 구조 확인 ===")

print("최상위 키:", data.keys())


ordin_search = data.get("OrdinSearch", {})


if not isinstance(ordin_search, dict):

    print()
    print("ERROR: OrdinSearch 구조가 예상과 다릅니다.")
    print("OrdinSearch 타입:", type(ordin_search))

    sys.exit(1)


print("OrdinSearch 타입:", type(ordin_search))
print("OrdinSearch 키:", ordin_search.keys())


# ==================================================
# 검색 결과 기본 정보
# ==================================================

total_count = ordin_search.get(
    "totalCnt",
    0
)

print()
print("=== API 검색 결과 ===")
print("전체 검색 결과:", total_count)


# ==================================================
# law 데이터 확인
# ==================================================

law_data = ordin_search.get(
    "law",
    []
)


print()
print("=== law 구조 확인 ===")
print("law 타입:", type(law_data))


# --------------------------------------------------
# law 구조 출력
# --------------------------------------------------

if isinstance(law_data, dict):

    print("law 키:")
    print(law_data.keys())

    print()
    print("law 데이터:")
    print(law_data)

elif isinstance(law_data, list):

    print("law 리스트 항목 수:", len(law_data))

    if law_data:

        print()
        print("첫 번째 law 항목 타입:")
        print(type(law_data[0]))

        if isinstance(law_data[0], dict):

            print()
            print("첫 번째 law 항목 키:")
            print(law_data[0].keys())

else:

    print()
    print("WARNING: 예상하지 못한 law 데이터 구조입니다.")


# ==================================================
# law 데이터 정규화
# ==================================================

"""
국가법령정보 API는 검색 결과 개수에 따라

1. 결과가 1개인 경우
   law = dict

2. 결과가 여러 개인 경우
   law = list

형태로 반환될 수 있다.

따라서 내부 처리에서는 항상

    normalized_laws = [dict, dict, ...]

형태로 통일한다.
"""


normalized_laws = []


# --------------------------------------------------
# 결과가 1개인 경우
# --------------------------------------------------

if isinstance(law_data, dict):

    normalized_laws.append(
        law_data
    )


# --------------------------------------------------
# 결과가 여러 개인 경우
# --------------------------------------------------

elif isinstance(law_data, list):

    for item in law_data:

        if isinstance(item, dict):

            normalized_laws.append(
                item
            )


# --------------------------------------------------
# 그 외
# --------------------------------------------------

else:

    print()
    print("WARNING: law 데이터를 정규화하지 못했습니다.")


# ==================================================
# 정규화 결과 확인
# ==================================================

print()
print("=== 정규화된 검색 결과 ===")

print("전체 검색 결과:", total_count)
print("정규화된 결과 수:", len(normalized_laws))


# ==================================================
# 대상 조례 필터링
# ==================================================

target_laws = []


for item in normalized_laws:

    # 안전성 검사
    if not isinstance(item, dict):
        continue


    ordinance_name = item.get(
        "자치법규명",
        ""
    )


    agency = item.get(
        "지자체기관명",
        ""
    )


    # --------------------------------------------------
    # 지역 + 조례명 일치
    # --------------------------------------------------

    if (
        ordinance_name == TARGET_ORDINANCE
        and
        agency == TARGET_REGION
    ):

        target_laws.append(
            item
        )


# ==================================================
# 대상 조례 필터 결과
# ==================================================

print()
print("=== 대상 조례 필터 결과 ===")
print("검색 결과 수:", len(target_laws))


# ==================================================
# 대상 조례 선택
# ==================================================

if not target_laws:

    print()
    print("대상 조례를 자동 선택하지 못했습니다.")

    print()
    print("=" * 70)
    print("STEP 17-18 실패")
    print("=" * 70)

    sys.exit(1)


# --------------------------------------------------
# 최신 조례 선택
# --------------------------------------------------

"""
현재 검색 조건에서 동일 조례가 여러 건 반환될 가능성을 고려하여
시행일자를 기준으로 최신 데이터를 선택한다.

시행일자는 YYYYMMDD 형태의 문자열이므로
문자열 비교가 가능하다.
"""


def get_effective_date(item):

    return item.get(
        "시행일자",
        ""
    )


target_laws.sort(
    key=get_effective_date,
    reverse=True
)


latest = target_laws[0]


# ==================================================
# 최신 조례 결과
# ==================================================

print()
print("=== 최신 대상 조례 선택 성공 ===")

print()
print("자치법규명:",
      latest.get("자치법규명"))

print("지자체기관명:",
      latest.get("지자체기관명"))

print("자치법규ID:",
      latest.get("자치법규ID"))

print("자치법규일련번호(MST):",
      latest.get("자치법규일련번호"))

print("자치법규종류:",
      latest.get("자치법규종류"))

print("제개정구분명:",
      latest.get("제개정구분명"))

print("시행일자:",
      latest.get("시행일자"))

print("공포일자:",
      latest.get("공포일자"))

print("공포번호:",
      latest.get("공포번호"))

print("자치법규상세링크:",
      latest.get("자치법규상세링크"))


# ==================================================
# 핵심 식별자 확인
# ==================================================

ordinance_id = latest.get(
    "자치법규ID"
)

mst = latest.get(
    "자치법규일련번호"
)

detail_link = latest.get(
    "자치법규상세링크"
)


print()
print("=== 상세 API 연결용 핵심 데이터 ===")

print("자치법규ID:", ordinance_id)
print("MST:", mst)


# ==================================================
# 데이터 검증
# ==================================================

if not ordinance_id:

    print()
    print("WARNING: 자치법규ID가 없습니다.")


if not mst:

    print()
    print("WARNING: 자치법규일련번호(MST)가 없습니다.")


if not detail_link:

    print()
    print("WARNING: 자치법규상세링크가 없습니다.")


# ==================================================
# 최종 결과
# ==================================================

print()
print("=" * 70)

print("STEP 17-18 완료")

print("=" * 70)