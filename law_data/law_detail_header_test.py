import os
import json
import requests
from pathlib import Path
from urllib.parse import urlparse


# ============================================================
# STEP 17-21-B
# 법제처 상세 API 요청 방식 비교 테스트
#
# 목적
# 1. 기존 요청 방식 확인
# 2. Referer 추가 여부 확인
# 3. User-Agent 추가 여부 확인
# 4. Referer + User-Agent 조합 확인
# 5. HTTP / HTTPS 차이 확인
#
# 중요:
# - 인증키 자체는 절대로 출력하지 않는다.
# - 인증키는 .env의 LAW_API_KEY 환경변수에서 읽는다.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


# ============================================================
# .env 로드
# ============================================================

def load_env_file(path):
    """
    python-dotenv가 설치되어 있지 않아도 동작하도록
    간단한 .env 로더를 사용한다.
    """

    if not path.exists():
        return

    try:
        from dotenv import load_dotenv

        load_dotenv(path)

    except ImportError:
        # python-dotenv가 없는 경우 직접 읽는다.
        with open(path, "r", encoding="utf-8") as f:

            for line in f:
                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                key = key.strip()
                value = value.strip()

                if (
                    len(value) >= 2
                    and value[0] == '"'
                    and value[-1] == '"'
                ):
                    value = value[1:-1]

                if (
                    len(value) >= 2
                    and value[0] == "'"
                    and value[-1] == "'"
                ):
                    value = value[1:-1]

                os.environ.setdefault(key, value)


load_env_file(ENV_FILE)


# ============================================================
# 인증키 환경변수
# ============================================================

LAW_API_KEY = os.getenv("LAW_API_KEY")


# ============================================================
# 기본 설정
# ============================================================

TIMEOUT = 20

BASE_HTTP_URL = "http://www.law.go.kr/DRF/lawService.do"
BASE_HTTPS_URL = "https://www.law.go.kr/DRF/lawService.do"


# ============================================================
# 테스트 대상
# ============================================================

TEST_TARGETS = [

    {
        "name": "강남구 도시계획 조례 - MST",
        "target": "ordin",
        "mst": "1592205",
        "id": None,
    },

    {
        "name": "강남구 도시계획 조례 - ID",
        "target": "ordin",
        "mst": None,
        "id": "2072371",
    },

    {
        "name": "서울시 도시계획 조례 - MST",
        "target": "ordin",
        "mst": "2149501",
        "id": None,
    },

    {
        "name": "서울시 도시계획 조례 - ID",
        "target": "ordin",
        "mst": None,
        "id": "2000719",
    },

    {
        "name": "국토계획법 - MST",
        "target": "law",
        "mst": "284013",
        "id": None,
    },

    {
        "name": "국토계획법 - ID",
        "target": "law",
        "mst": None,
        "id": "009294",
    },

    {
        "name": "국토계획법 시행령 - MST",
        "target": "law",
        "mst": "287269",
        "id": None,
    },

    {
        "name": "국토계획법 시행령 - ID",
        "target": "law",
        "mst": None,
        "id": "009419",
    },
]


# ============================================================
# 헤더 정의
# ============================================================

HEADERS_NONE = {
}


HEADERS_REFERER = {
    "Referer": "https://www.law.go.kr/"
}


HEADERS_USER_AGENT = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}


HEADERS_BOTH = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.law.go.kr/",
}


# ============================================================
# 테스트 CASE
# ============================================================

TEST_CASES = [

    {
        "name": "CASE 1 - 현재 방식",
        "url": BASE_HTTP_URL,
        "headers": HEADERS_NONE,
    },

    {
        "name": "CASE 2 - Referer 추가",
        "url": BASE_HTTP_URL,
        "headers": HEADERS_REFERER,
    },

    {
        "name": "CASE 3 - User-Agent 추가",
        "url": BASE_HTTP_URL,
        "headers": HEADERS_USER_AGENT,
    },

    {
        "name": "CASE 4 - Referer + User-Agent",
        "url": BASE_HTTP_URL,
        "headers": HEADERS_BOTH,
    },

    {
        "name": "CASE 5 - HTTPS + Referer + User-Agent",
        "url": BASE_HTTPS_URL,
        "headers": HEADERS_BOTH,
    },
]


# ============================================================
# 인증키 상태 확인
# ============================================================

def print_key_status():

    print("=" * 70)
    print("=== 인증키 환경변수 확인 ===")
    print("=" * 70)

    if not LAW_API_KEY:

        print("ERROR: LAW_API_KEY를 찾을 수 없습니다.")
        print()
        print("확인 대상:")
        print(ENV_FILE)

        return False

    print("LAW_API_KEY 존재: YES")
    print("LAW_API_KEY 길이:", len(LAW_API_KEY))

    if len(LAW_API_KEY) >= 8:

        print(
            "LAW_API_KEY 확인용:",
            LAW_API_KEY[:4] + "..." + LAW_API_KEY[-4:]
        )

    else:

        print("LAW_API_KEY 확인용: 길이가 너무 짧아 표시하지 않음")

    print()
    print("※ 전체 인증키는 출력하지 않습니다.")

    return True


# ============================================================
# 요청 파라미터 생성
# ============================================================

def make_params(target_info):

    params = {
        "OC": LAW_API_KEY,
        "target": target_info["target"],
        "type": "JSON",
    }

    if target_info["mst"]:

        params["MST"] = target_info["mst"]

    elif target_info["id"]:

        params["ID"] = target_info["id"]

    return params


# ============================================================
# 응답 분석
# ============================================================

def analyze_response(response):

    print("HTTP 상태코드:", response.status_code)

    print(
        "Content-Type:",
        response.headers.get("Content-Type", "")
    )

    print(
        "응답 크기:",
        len(response.content),
        "bytes"
    )

    print()

    # --------------------------------------------------------
    # JSON 확인
    # --------------------------------------------------------

    try:

        data = response.json()

        print("JSON 파싱: 성공")

    except Exception as e:

        print("JSON 파싱: 실패")
        print("오류:", e)

        print()
        print("응답 앞부분:")
        print(response.text[:500])

        return {
            "json": False,
            "success": False,
            "data": None,
        }

    # --------------------------------------------------------
    # 최상위 구조
    # --------------------------------------------------------

    if isinstance(data, dict):

        print("최상위 키:", list(data.keys()))

    else:

        print("최상위 TYPE:", type(data))

    # --------------------------------------------------------
    # 법제처 인증 오류 구조
    # --------------------------------------------------------

    if isinstance(data, dict):

        if "result" in data:

            print()
            print("result:", data.get("result"))

        if "msg" in data:

            print("msg:", data.get("msg"))

    # --------------------------------------------------------
    # 정상 상세조회 여부
    # --------------------------------------------------------

    if isinstance(data, dict):

        if "LawService" in data:

            print()
            print(">>> LawService 발견")
            print(">>> 상세조회 성공 가능성 높음")

            return {
                "json": True,
                "success": True,
                "data": data,
            }

    # --------------------------------------------------------
    # 정상 응답인데 구조가 다른 경우
    # --------------------------------------------------------

    if isinstance(data, dict):

        if "LawService" not in data:

            print()
            print("LawService 없음")

    return {
        "json": True,
        "success": False,
        "data": data,
    }


# ============================================================
# 단일 요청
# ============================================================

def run_request(test_case, target_info):

    print()
    print("-" * 70)
    print(test_case["name"])
    print("-" * 70)

    print("대상:", target_info["name"])
    print("target:", target_info["target"])

    if target_info["mst"]:

        print("MST:", target_info["mst"])

    if target_info["id"]:

        print("ID:", target_info["id"])

    print("URL:", test_case["url"])

    # --------------------------------------------------------
    # 헤더 출력
    # --------------------------------------------------------

    print()
    print("요청 헤더:")

    if not test_case["headers"]:

        print("  (없음)")

    else:

        for key, value in test_case["headers"].items():

            print(f"  {key}: {value}")

    # --------------------------------------------------------
    # 파라미터
    # --------------------------------------------------------

    params = make_params(target_info)

    # --------------------------------------------------------
    # 중요:
    # URL에 인증키가 포함된 전체 URL은 출력하지 않는다.
    # --------------------------------------------------------

    print()
    print("요청 파라미터:")

    print("  OC: [HIDDEN]")

    print(
        "  target:",
        params.get("target")
    )

    print(
        "  type:",
        params.get("type")
    )

    if "MST" in params:

        print(
            "  MST:",
            params["MST"]
        )

    if "ID" in params:

        print(
            "  ID:",
            params["ID"]
        )

    # --------------------------------------------------------
    # 요청
    # --------------------------------------------------------

    try:

        response = requests.get(
            test_case["url"],
            params=params,
            headers=test_case["headers"],
            timeout=TIMEOUT,
            allow_redirects=True,
        )

    except requests.RequestException as e:

        print()
        print("REQUEST ERROR")
        print(type(e).__name__)
        print(str(e))

        return {
            "success": False,
            "request_error": True,
        }

    # --------------------------------------------------------
    # 최종 URL
    # --------------------------------------------------------

    parsed = urlparse(response.url)

    safe_query = []

    for part in parsed.query.split("&"):

        if part.startswith("OC="):

            safe_query.append("OC=[HIDDEN]")

        elif part:

            safe_query.append(part)

    safe_url = parsed.scheme + "://" + parsed.netloc + parsed.path

    if safe_query:

        safe_url += "?" + "&".join(safe_query)

    print()
    print("실제 요청 URL(인증키 숨김):")
    print(safe_url)

    # --------------------------------------------------------
    # 응답 분석
    # --------------------------------------------------------

    return analyze_response(response)


# ============================================================
# 메인 테스트
# ============================================================

def main():

    print()
    print("=" * 70)
    print("=== STEP 17-21-B 상세 API HTTP 요청 방식 비교 테스트 ===")
    print("=" * 70)

    print()
    print("목적:")
    print("1. 현재 요청 방식")
    print("2. Referer 추가")
    print("3. User-Agent 추가")
    print("4. Referer + User-Agent")
    print("5. HTTPS + Referer + User-Agent")
    print()

    # --------------------------------------------------------
    # 인증키 확인
    # --------------------------------------------------------

    if not print_key_status():

        return

    # --------------------------------------------------------
    # 테스트 통계
    # --------------------------------------------------------

    total_tests = 0
    success_tests = 0

    results = []

    # --------------------------------------------------------
    # 모든 법규 × 모든 요청 방식
    # --------------------------------------------------------

    for target_info in TEST_TARGETS:

        print()
        print("=" * 70)
        print("대상 법규")
        print("=" * 70)

        print(target_info["name"])

        for test_case in TEST_CASES:

            total_tests += 1

            result = run_request(
                test_case,
                target_info
            )

            success = result.get("success", False)

            if success:

                success_tests += 1

            results.append({
                "target": target_info["name"],
                "case": test_case["name"],
                "success": success,
            })

    # ========================================================
    # 결과 요약
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("=== STEP 17-21-B 결과 요약 ===")
    print("=" * 70)

    print()

    print(
        "성공:",
        success_tests,
        "/",
        total_tests
    )

    print(
        "실패:",
        total_tests - success_tests,
        "/",
        total_tests
    )

    print()

    # --------------------------------------------------------
    # CASE별 결과
    # --------------------------------------------------------

    for case in TEST_CASES:

        case_name = case["name"]

        case_results = [
            r for r in results
            if r["case"] == case_name
        ]

        case_success = sum(
            1 for r in case_results
            if r["success"]
        )

        print(
            f"{case_name}: "
            f"{case_success}/{len(case_results)} 성공"
        )

    # ========================================================
    # 대상별 결과
    # ========================================================

    print()
    print("=" * 70)
    print("=== 법규별 결과 ===")
    print("=" * 70)

    for target in TEST_TARGETS:

        target_name = target["name"]

        target_results = [
            r for r in results
            if r["target"] == target_name
        ]

        target_success = sum(
            1 for r in target_results
            if r["success"]
        )

        print(
            f"{target_name}: "
            f"{target_success}/{len(target_results)} 성공"
        )

    # ========================================================
    # 최종 판정
    # ========================================================

    print()
    print("=" * 70)
    print("=== 진단 방향 ===")
    print("=" * 70)

    if success_tests > 0:

        print()
        print("상세 API 호출 자체는 성공하는 요청 조건이 존재합니다.")
        print()
        print("다음 단계:")
        print("→ 성공한 요청 조건을 기존 상세조회 코드에 적용")
        print("→ STEP 17-21 통합 파서 재구축")

    else:

        print()
        print("모든 요청 조건에서 상세 API가 실패했습니다.")
        print()
        print("따라서 Referer/User-Agent만으로는 해결되지 않습니다.")
        print()
        print("다음 조사 대상:")
        print("1. OC 인증키와 API 신청정보")
        print("2. law.go.kr API 인증 정책")
        print("3. HTTP/HTTPS 및 API 서버 정책")
        print("4. 상세조회 API의 다른 필수 조건")
        print("5. API 인증키가 연결된 시스템/도메인/IP 설정")
        print("6. 검색 API와 상세 API의 인증 정책 차이")

    print()
    print("=" * 70)
    print("STEP 17-21-B 완료")
    print("=" * 70)


if __name__ == "__main__":
    main()