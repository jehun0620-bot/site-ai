import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from site_data.land_converter import (
    select_latest_land_record,
    convert_land_record,
)


# ============================================================
# 1. 프로젝트 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# 2. .env 파일 불러오기
# ============================================================

load_dotenv(BASE_DIR / ".env")


# ============================================================
# 3. VWorld API 인증키 읽기
# ============================================================

VWORLD_API_KEY = os.getenv("VWORLD_API_KEY")


if not VWORLD_API_KEY:
    print("ERROR: VWORLD_API_KEY를 찾을 수 없습니다.")
    sys.exit(1)


print("VWORLD_API_KEY를 정상적으로 읽었습니다.")
print(f"인증키 길이: {len(VWORLD_API_KEY)}")


# ============================================================
# 4. VWorld API 설정
# ============================================================

API_URL = "https://api.vworld.kr/ned/data/getLandCharacteristics"


# 테스트 지번
sigungu_cd = "11680"
bjdong_cd = "10300"
bun = "0012"
ji = "0000"


# 일반 토지 PNU 생성
pnu = (
    sigungu_cd
    + bjdong_cd
    + "1"
    + bun
    + ji
)


print()
print("테스트 PNU")
print("----------------------------------------")
print(pnu)


# ============================================================
# 5. API 요청 파라미터
# ============================================================

params = {
    "key": VWORLD_API_KEY,
    "pnu": pnu,
    "stdrYear": "2024",
    "format": "json",
    "numOfRows": "10",
    "pageNo": "1",
}


# ============================================================
# 6. API 호출
# ============================================================

print()
print("VWorld 토지특성정보 API 호출 중...")
print("----------------------------------------")


try:
    response = requests.get(
        API_URL,
        params=params,
        timeout=30,
    )

except requests.RequestException as e:
    print("ERROR: API 요청 중 오류가 발생했습니다.")
    print(e)
    sys.exit(1)


# ============================================================
# 7. HTTP 상태 확인
# ============================================================

print(f"HTTP 상태코드: {response.status_code}")


if response.status_code != 200:
    print("ERROR: HTTP 요청이 정상적으로 처리되지 않았습니다.")
    print(response.text)
    sys.exit(1)


# ============================================================
# 8. JSON 변환
# ============================================================

try:
    data = response.json()

except ValueError:
    print("ERROR: JSON 형식으로 응답을 변환할 수 없습니다.")
    print(response.text)
    sys.exit(1)


# ============================================================
# 9. API 응답에서 field 추출
# ============================================================

try:
    records = data["landCharacteristicss"]["field"]

except (KeyError, TypeError):
    print("ERROR: 예상한 API 응답 구조를 찾을 수 없습니다.")
    print(data)
    sys.exit(1)


print()
print(f"API에서 받은 토지 데이터 수: {len(records)}")


# ============================================================
# 10. 최신 토지 데이터 선택
# ============================================================

latest_record = select_latest_land_record(records)


if latest_record is None:
    print("ERROR: 토지 데이터가 없습니다.")
    sys.exit(1)


print()
print("최신 토지 데이터")
print("----------------------------------------")
print(f"기준연도: {latest_record.get('stdrYear')}")
print(f"최종수정일: {latest_record.get('lastUpdtDt')}")
print(f"지번: {latest_record.get('mnnmSlno')}")


# ============================================================
# 11. Land 객체로 변환
# ============================================================

land = convert_land_record(latest_record)


# ============================================================
# 12. Land 객체 출력
# ============================================================

print()
print("Land 객체")
print("----------------------------------------")
print(land)