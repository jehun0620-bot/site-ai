import os
import sys

import requests
from dotenv import load_dotenv


# 프로젝트 루트 경로를 Python import 경로에 추가
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)


from site_data.site_data_model import Site, Land
from site_data.regulation_model import Regulation
from law_data.law_article_parser import find_article_ratio


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))

LAW_API_KEY = os.getenv("LAW_API_KEY")

if not LAW_API_KEY:
    print("ERROR: 국가법령정보 API 인증키를 찾을 수 없습니다.")
    sys.exit(1)


# --------------------------------------------------
# 1. 실제 Site의 Land 정보 생성
# --------------------------------------------------

land = Land(
    land_area=121040.4,
    land_category="대",
    zoning="제3종일반주거지역",
    district="",
    land_use_regulation=""
)


site = Site(
    site_id="11680-10300-0012-0000",
    address="서울특별시 강남구 개포동 12번지",
    road_address="서울특별시 강남구 개포로109길 21 (개포동)",
    sigungu_cd="11680",
    bjdong_cd="10300",
    bun="0012",
    ji="0000",
    land=land
)


# --------------------------------------------------
# 2. 국가법령정보 API 요청
# --------------------------------------------------

MST = "287269"

URL = "http://www.law.go.kr/DRF/lawService.do"

params = {
    "OC": LAW_API_KEY,
    "target": "law",
    "MST": MST,
    "type": "JSON",
}

print("=== Site → Regulation API 연결 테스트 ===")

response = requests.get(
    URL,
    params=params,
    timeout=30
)

print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()


# --------------------------------------------------
# 3. 법령 조문 가져오기
# --------------------------------------------------

articles = data["법령"]["조문"]["조문단위"]


# --------------------------------------------------
# 4. Site의 용도지역 사용
# --------------------------------------------------

zoning = site.land.zoning


# --------------------------------------------------
# 5. 건폐율 / 용적률 추출
# --------------------------------------------------

building_coverage_ratio = find_article_ratio(
    articles,
    "84"
)

floor_area_ratio = find_article_ratio(
    articles,
    "85"
)


# --------------------------------------------------
# 6. Regulation 생성
# --------------------------------------------------

regulation = Regulation(
    zoning=zoning,
    building_coverage_ratio=building_coverage_ratio,
    floor_area_ratio=floor_area_ratio,
    source="국토의 계획 및 이용에 관한 법률 시행령",
    legal_basis="제84조(용도지역안에서의 건폐율), 제85조(용도지역 안에서의 용적률)",
    priority=1
)


# --------------------------------------------------
# 7. Site에 Regulation 연결
# --------------------------------------------------

site.regulation = regulation


# --------------------------------------------------
# 8. 결과 출력
# --------------------------------------------------

print()
print("=== 최종 Site ===")

print("Site ID:", site.site_id)
print("주소:", site.address)

print()
print("=== Land ===")

print("대지면적:", site.land.land_area, "㎡")
print("지목:", site.land.land_category)
print("용도지역:", site.land.zoning)

print()
print("=== Regulation ===")

print("법정 건폐율:", site.regulation.building_coverage_ratio, "%")
print("법정 용적률:", site.regulation.floor_area_ratio, "%")
print("출처:", site.regulation.source)
print("법적 근거:", site.regulation.legal_basis)
print("우선순위:", site.regulation.priority)