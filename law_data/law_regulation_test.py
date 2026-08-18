import os
import sys

import requests
from dotenv import load_dotenv

from law_article_parser import find_article_ratio

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))

LAW_API_KEY = os.getenv("LAW_API_KEY")

if not LAW_API_KEY:
    print("ERROR: 국가법령정보 API 인증키를 찾을 수 없습니다.")
    sys.exit(1)

# site_data 폴더의 Regulation 모델 가져오기
SITE_DATA_DIR = os.path.join(BASE_DIR, "site_data")

sys.path.insert(0, SITE_DATA_DIR)

from regulation_model import Regulation

MST = "287269"

URL = "http://www.law.go.kr/DRF/lawService.do"

params = {
    "OC": LAW_API_KEY,
    "target": "law",
    "MST": MST,
    "type": "JSON",
}


print("=== 법령 API → Regulation 연결 테스트 ===")


# --------------------------------------------------
# 1. 국가법령정보 API 요청
# --------------------------------------------------

response = requests.get(
    URL,
    params=params,
    timeout=30
)

print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()


# --------------------------------------------------
# 2. 조문 데이터 가져오기
# --------------------------------------------------

articles = data["법령"]["조문"]["조문단위"]


# --------------------------------------------------
# 3. 건폐율 / 용적률 추출
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
# 4. Regulation 객체 생성
# --------------------------------------------------

regulation = Regulation(
    zoning="제3종일반주거지역",

    building_coverage_ratio=building_coverage_ratio,

    floor_area_ratio=floor_area_ratio,

    source="국토의 계획 및 이용에 관한 법률 시행령",

    legal_basis="제84조(용도지역안에서의 건폐율), 제85조(용도지역 안에서의 용적률)",

    priority=1
)


# --------------------------------------------------
# 5. 결과 출력
# --------------------------------------------------

print()
print("=== Regulation 결과 ===")

print("용도지역:", regulation.zoning)

print(
    "법정 건폐율:",
    regulation.building_coverage_ratio,
    "%"
)

print(
    "법정 용적률:",
    regulation.floor_area_ratio,
    "%"
)

print("높이 제한:", regulation.height_limit)

print("용도 제한:", regulation.use_restriction)

print("출처:", regulation.source)

print("법적 근거:", regulation.legal_basis)

print("우선순위:", regulation.priority)