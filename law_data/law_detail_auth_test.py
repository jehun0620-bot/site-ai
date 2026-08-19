import os
import sys
import json
import requests
from dotenv import load_dotenv


# ============================================================
# 환경설정
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(BASE_DIR, ".env"))

API_KEY = os.getenv("DATA_API_KEY")

if not API_KEY:
    print("ERROR: DATA_API_KEY를 찾을 수 없습니다.")
    sys.exit(1)


BASE_URL = "http://www.law.go.kr/DRF/lawService.do"


# ============================================================
# 테스트 대상
# ============================================================

TEST_CASES = [
    {
        "name": "강남구 도시계획 조례 - MST 조회",
        "target": "ordin",
        "mst": "1592205",
        "id": None,
    },
    {
        "name": "강남구 도시계획 조례 - ID 조회",
        "target": "ordin",
        "mst": None,
        "id": "2072371",
    },
    {
        "name": "서울시 도시계획 조례 - MST 조회",
        "target": "ordin",
        "mst": "2149501",
        "id": None,
    },
    {
        "name": "서울시 도시계획 조례 - ID 조회",
        "target": "ordin",
        "mst": None,
        "id": "2000719",
    },
    {
        "name": "국토계획법 - MST 조회",
        "target": "law",
        "mst": "284013",
        "id": None,
    },
    {
        "name": "국토계획법 - ID 조회",
        "target": "law",
        "mst": None,
        "id": "009294",
    },
    {
        "name": "국토계획법 시행령 - MST 조회",
        "target": "law",
        "mst": "287269",
        "id": None,
    },
    {
        "name": "국토계획법 시행령 - ID 조회",
        "target": "law",
        "mst": None,
        "id": "009419",
    },
]


# ============================================================
# 상세조회 테스트
# ============================================================

def test_detail(case):

    print()
    print("=" * 70)
    print(case["name"])
    print("=" * 70)

    params = {
        "OC": API_KEY,
        "target": case["target"],
        "type": "JSON",
    }

    if case["mst"]:
        params["MST"] = case["mst"]

    if case["id"]:
        params["ID"] = case["id"]

    print("요청 파라미터:")
    print(f"target = {case['target']}")
    print(f"MST    = {case['mst']}")
    print(f"ID     = {case['id']}")
    print("type   = JSON")

    try:

        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        print()
        print(f"HTTP 상태코드: {response.status_code}")

        print()
        print("실제 요청 URL:")
        print(response.url)

        data = response.json()

        print()
        print("응답 최상위 키:")
        print(list(data.keys()))

        # ----------------------------------------------------
        # 인증 오류
        # ----------------------------------------------------

        if "result" in data and "msg" in data:

            print()
            print("!!! API 인증 오류 !!!")
            print(f"result: {data['result']}")
            print(f"msg: {data['msg']}")

            return False

        # ----------------------------------------------------
        # 정상 응답
        # ----------------------------------------------------

        if "LawService" in data:

            service = data["LawService"]

            print()
            print(">>> 상세조회 성공")
            print("LawService 확인")

            if isinstance(service, dict):

                print()
                print("LawService 키:")
                print(list(service.keys()))

            return True

        # ----------------------------------------------------
        # 예상하지 못한 응답
        # ----------------------------------------------------

        print()
        print("!!! 예상하지 못한 응답 구조 !!!")
        print(json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )[:3000])

        return False

    except Exception as e:

        print()
        print("ERROR:")
        print(e)

        return False


# ============================================================
# MAIN
# ============================================================

def main():

    print("=== STEP 17-21-A 상세 API 인증 방식 비교 테스트 ===")
    print()

    success = 0
    fail = 0

    for case in TEST_CASES:

        result = test_detail(case)

        if result:
            success += 1
        else:
            fail += 1

    print()
    print("=" * 70)
    print("=== 테스트 결과 ===")
    print("=" * 70)

    print(f"성공: {success}")
    print(f"실패: {fail}")
    print(f"전체: {len(TEST_CASES)}")

    print()

    if success == len(TEST_CASES):
        print("모든 상세조회 방식이 정상입니다.")

    elif success > 0:
        print("일부 상세조회 방식만 정상입니다.")

    else:
        print("모든 상세조회가 인증 단계에서 실패했습니다.")

    print()
    print("=== STEP 17-21-A 완료 ===")


if __name__ == "__main__":
    main()