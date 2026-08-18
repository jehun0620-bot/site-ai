import os
import sys

import requests
from dotenv import load_dotenv


# 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env 로드
load_dotenv(os.path.join(BASE_DIR, ".env"))


# 국가법령정보 API 인증키
LAW_API_KEY = os.getenv("LAW_API_KEY")


if not LAW_API_KEY:
    print("ERROR: 국가법령정보 API 인증키를 찾을 수 없습니다.")
    sys.exit(1)


# 국가법령정보 현행법령 목록조회 API
URL = "http://www.law.go.kr/DRF/lawSearch.do"


params = {
    "OC": LAW_API_KEY,
    "target": "law",
    "type": "JSON",
    "query": "국토의 계획 및 이용에 관한 법률",
    "display": 5,
    "page": 1,
}


print("국가법령정보 API 요청 중...")


try:

    response = requests.get(
        URL,
        params=params,
        timeout=30
    )

    print("HTTP 상태코드:", response.status_code)

    response.raise_for_status()

    print("API 요청 성공")

    data = response.json()

    print("JSON 응답 확인 성공")

    print("최상위 키:", data.keys())

    print("\n=== API 응답 일부 ===")
    print(data)


except requests.exceptions.RequestException as e:

    print("API 요청 오류:", e)
    sys.exit(1)


except ValueError as e:

    print("JSON 변환 오류:", e)
    print("응답 내용:")
    print(response.text[:1000])
    sys.exit(1)