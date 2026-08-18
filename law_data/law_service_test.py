import os
import sys

import requests
from dotenv import load_dotenv


# 프로젝트 루트
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# .env 로드
load_dotenv(os.path.join(BASE_DIR, ".env"))


# API 인증키
LAW_API_KEY = os.getenv("LAW_API_KEY")


if not LAW_API_KEY:
    print("ERROR: 국가법령정보 API 인증키를 찾을 수 없습니다.")
    sys.exit(1)


# STEP 17-7에서 확인한 국토계획법 시행령 MST
MST = "287269"


# 국가법령정보 현행법령 본문조회 API
URL = "http://www.law.go.kr/DRF/lawService.do"


params = {
    "OC": LAW_API_KEY,
    "target": "law",
    "MST": MST,
    "type": "JSON",
}


print("=== 국가법령정보 본문 조회 테스트 ===")
print("MST:", MST)
print("API 요청 중...")


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

    print("\n=== 최상위 키 ===")
    print(data.keys())

    print("\n=== 응답 구조 ===")

    if isinstance(data, dict):
        for key, value in data.items():

            if isinstance(value, dict):
                print(f"{key}: dict")
                print("  하위 키:", value.keys())

            elif isinstance(value, list):
                print(f"{key}: list")
                print("  데이터 개수:", len(value))

            else:
                print(f"{key}: {type(value).__name__}")


except requests.exceptions.RequestException as e:

    print("API 요청 오류:", e)
    sys.exit(1)


except ValueError as e:

    print("JSON 변환 오류:", e)

    print("\n=== API 원본 응답 일부 ===")
    print(response.text[:2000])

    sys.exit(1)