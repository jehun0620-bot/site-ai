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


MST = "287269"

URL = "http://www.law.go.kr/DRF/lawService.do"

params = {
    "OC": LAW_API_KEY,
    "target": "law",
    "MST": MST,
    "type": "JSON",
}


print("=== 법령 건폐율 / 용적률 자동 추출 테스트 ===")

response = requests.get(
    URL,
    params=params,
    timeout=30
)

print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()

articles = data["법령"]["조문"]["조문단위"]


building_coverage_ratio = find_article_ratio(
    articles,
    "84"
)

floor_area_ratio = find_article_ratio(
    articles,
    "85"
)


print()
print("용도지역: 제3종일반주거지역")
print("법정 건폐율:", building_coverage_ratio, "%")
print("법정 용적률:", floor_area_ratio, "%")