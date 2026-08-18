import os
import sys

import requests
from dotenv import load_dotenv


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


print("=== 제84조 / 제85조 구조 확인 ===")

response = requests.get(
    URL,
    params=params,
    timeout=30
)

print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()

articles = data["법령"]["조문"]["조문단위"]

print("전체 조문단위:", len(articles))

print("\n=== 제84조 / 제85조 검색 ===")

for article in articles:

    article_number = str(article.get("조문번호", ""))

    if article_number in ("84", "85"):

        print("\n" + "=" * 80)

        print("조문번호:", article.get("조문번호"))
        print("조문시행일자:", article.get("조문시행일자"))
        print("조문키:", article.get("조문키"))
        print("조문여부:", article.get("조문여부"))

        print("\n조문 데이터 전체:")
        print(article)

        print("=" * 80)