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


print("=== 법령 조문 구조 테스트 ===")

response = requests.get(
    URL,
    params=params,
    timeout=30
)

print("HTTP 상태코드:", response.status_code)

response.raise_for_status()

data = response.json()

law = data["법령"]

articles = law["조문"]

print("\n=== 조문 데이터 타입 ===")
print(type(articles))

print("\n=== 조문 데이터 일부 ===")

if isinstance(articles, dict):

    print("조문 하위 키:")
    print(articles.keys())

    for key, value in articles.items():

        print(f"\n[{key}]")
        print("타입:", type(value))

        if isinstance(value, list):
            print("개수:", len(value))

            if value:
                print("첫 번째 데이터:")
                print(value[0])

        elif isinstance(value, dict):
            print("하위 키:")
            print(value.keys())

        else:
            print("값:", value)

elif isinstance(articles, list):

    print("조문 개수:", len(articles))

    if articles:
        print("\n첫 번째 조문:")
        print(articles[0])

else:

    print("조문 데이터:")
    print(articles)