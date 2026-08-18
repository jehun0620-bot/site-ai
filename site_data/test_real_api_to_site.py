import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os


# --------------------------------------------------
# 프로젝트 루트 경로
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

sys.path.append(str(BASE_DIR / "site_data"))


# --------------------------------------------------
# 우리 시스템 데이터 구조
# --------------------------------------------------

from site_builder import create_site


# --------------------------------------------------
# 환경변수
# --------------------------------------------------

load_dotenv(BASE_DIR / ".env")

SERVICE_KEY = os.getenv("DATA_API_KEY")

if not SERVICE_KEY:
    print("ERROR: API 인증키를 찾을 수 없습니다.")
    sys.exit(1)

print("API 인증키를 정상적으로 읽었습니다.")


# --------------------------------------------------
# 건축HUB API
# --------------------------------------------------

url = (
    "http://apis.data.go.kr/"
    "1613000/BldRgstHubService/getBrTitleInfo"
)


params = {

    "sigunguCd": "11680",

    "bjdongCd": "10300",

    "bun": "0012",

    "ji": "0000",

    "serviceKey": SERVICE_KEY,

    "numOfRows": "100",

    "pageNo": "1",

    "_type": "json",
}


# --------------------------------------------------
# API 요청
# --------------------------------------------------

response = requests.get(
    url,
    params=params,
    timeout=30
)


print("HTTP 상태 코드:", response.status_code)


if response.status_code != 200:

    print("API 요청 실패")

    print(response.text)

    sys.exit(1)


# --------------------------------------------------
# JSON 변환
# --------------------------------------------------

data = response.json()


# --------------------------------------------------
# API 응답 확인
# --------------------------------------------------

if "response" not in data:

    print("ERROR: response가 없습니다.")

    print(data)

    sys.exit(1)


api_response = data["response"]


header = api_response["header"]


print()
print("API 상태")
print("--------------------------------")

print(
    "resultCode:",
    header.get("resultCode")
)

print(
    "resultMsg :",
    header.get("resultMsg")
)


if header.get("resultCode") != "00":

    print()
    print("API 오류")

    print(data)

    sys.exit(1)


# --------------------------------------------------
# 건축물 데이터 추출
# --------------------------------------------------

body = api_response["body"]

items_data = body["items"]

items = items_data.get("item", [])


# --------------------------------------------------
# item이 하나일 경우 처리
# --------------------------------------------------

if isinstance(items, dict):

    items = [items]


print()
print("건축물 조회")
print("--------------------------------")

print(
    "전체 데이터 수:",
    body.get("totalCount")
)

print(
    "현재 받은 건축물 수:",
    len(items)
)


# --------------------------------------------------
# Site 생성
# --------------------------------------------------

site = create_site(items)


if site is None:

    print("ERROR: Site 생성 실패")

    sys.exit(1)


# --------------------------------------------------
# 결과 출력
# --------------------------------------------------

print()
print("SITE 데이터")
print("--------------------------------")

print("SITE ID:", site.site_id)

print("주소:", site.address)

print("도로명주소:", site.road_address)

print("시군구코드:", site.sigungu_cd)

print("법정동코드:", site.bjdong_cd)

print("본번:", site.bun)

print("부번:", site.ji)


print()
print("건축물 수:", len(site.buildings))


print()
print("건축물 목록")
print("--------------------------------")


for index, building in enumerate(
    site.buildings,
    start=1
):

    print(
        f"{index:2d} | "
        f"{building.dong_name:15s} | "
        f"{building.building_name:25s} | "
        f"{building.main_use}"
    )