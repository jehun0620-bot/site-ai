import os
import json
import requests
from dotenv import load_dotenv


# ==================================================
# 1. .env 읽기
# ==================================================

load_dotenv()


# ==================================================
# 2. API 인증키
# ==================================================

api_key = os.getenv("DATA_API_KEY")

if not api_key:
    print("ERROR: DATA_API_KEY를 찾을 수 없습니다.")
    exit()


# ==================================================
# 3. API URL
# ==================================================

url = "http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"


# ==================================================
# 4. 요청 파라미터
# ==================================================

params = {
    "sigunguCd": "11680",
    "bjdongCd": "10300",
    "bun": "0012",
    "ji": "0000",
    "serviceKey": api_key,
    "_type": "json",
    "numOfRows": "100",
    "pageNo": "1",
}


# ==================================================
# 5. API 호출
# ==================================================

response = requests.get(
    url,
    params=params,
    timeout=30
)


# ==================================================
# 6. HTTP 상태 확인
# ==================================================

print("HTTP 상태 코드:", response.status_code)

response.raise_for_status()


# ==================================================
# 7. JSON 변환
# ==================================================

data = response.json()


# ==================================================
# 8. JSON 구조 확인
# ==================================================

print()
print("JSON 최상위 구조:")
print(data.keys())


# ==================================================
# 9. response 가져오기
# ==================================================

api_response = data.get("response")

if api_response is None:

    print()
    print("ERROR: JSON에서 response를 찾을 수 없습니다.")

    print()
    print("실제 응답:")

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

    exit()


# ==================================================
# 10. header 가져오기
# ==================================================

header = api_response.get("header")

if header is None:

    print()
    print("ERROR: response에서 header를 찾을 수 없습니다.")

    exit()


print()
print("API 상태")
print("------------------------------")

print(
    "resultCode:",
    header.get("resultCode")
)

print(
    "resultMsg :",
    header.get("resultMsg")
)


# ==================================================
# 11. body 가져오기
# ==================================================

body = api_response.get("body")

if body is None:

    print()
    print("ERROR: response에서 body를 찾을 수 없습니다.")

    exit()


# ==================================================
# 12. 조회 정보
# ==================================================

print()
print("조회 정보")
print("------------------------------")

print(
    "전체 데이터 수 :",
    body.get("totalCount")
)

print(
    "현재 페이지    :",
    body.get("pageNo")
)

print(
    "페이지당 데이터:",
    body.get("numOfRows")
)


# ==================================================
# 13. items 가져오기
# ==================================================

items_data = body.get("items")

if not items_data:

    print()
    print("조회된 건축물 데이터가 없습니다.")

    exit()


# ==================================================
# 14. item 가져오기
# ==================================================

items = items_data.get("item", [])


# ==================================================
# 15. 1건 / 여러 건 대응
# ==================================================

if isinstance(items, dict):

    items = [items]


print()
print(
    "현재 받은 건축물 수:",
    len(items)
)


# ==================================================
# 16. 건축물 정보 출력
# ==================================================

print()
print("현재 받은 건축물 수:", len(items))

print()
print("건축물 목록")
print("------------------------------")

for i, building in enumerate(items, start=1):

    print(
        i,
        "|",
        building.get("dongNm"),
        "|",
        building.get("bldNm"),
        "|",
        building.get("mainPurpsCdNm")
    )