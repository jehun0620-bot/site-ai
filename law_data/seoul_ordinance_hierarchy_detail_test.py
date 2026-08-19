import os
import sys
import json
import requests
from dotenv import load_dotenv


# ============================================================
# 환경설정
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)

API_KEY = os.getenv("DATA_API_KEY")

if not API_KEY:
    print("ERROR: DATA_API_KEY를 찾을 수 없습니다.")
    sys.exit(1)


BASE_URL = "http://www.law.go.kr/DRF/lawService.do"


# ============================================================
# 테스트 대상 법규 계층
# ============================================================

LAW_HIERARCHY = [
    {
        "level": 1,
        "type": "자치구 조례",
        "name": "서울특별시 강남구 도시계획 조례",
        "target": "ordin",
        "mst": "1592205",
        "id": "2072371",
    },
    {
        "level": 2,
        "type": "서울특별시 조례",
        "name": "서울특별시 도시계획 조례",
        "target": "ordin",
        "mst": "2149501",
        "id": "2000719",
    },
    {
        "level": 3,
        "type": "국가 법률",
        "name": "국토의 계획 및 이용에 관한 법률",
        "target": "law",
        "mst": "284013",
        "id": "009294",
    },
    {
        "level": 4,
        "type": "국가 시행령",
        "name": "국토의 계획 및 이용에 관한 법률 시행령",
        "target": "law",
        "mst": "287269",
        "id": "009419",
    },
]


# ============================================================
# 상세 API 호출
# ============================================================

def request_detail(law):
    """
    법규 상세정보 조회

    핵심:
    - target
    - MST
    - type=JSON
    """

    params = {
        "OC": API_KEY,
        "target": law["target"],
        "MST": law["mst"],
        "type": "JSON",
    }

    print("API 요청 중...")
    print(f"target: {law['target']}")
    print(f"MST: {law['mst']}")
    print(f"법규명: {law['name']}")

    try:
        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30
        )

        print(f"HTTP 상태코드: {response.status_code}")

        response.raise_for_status()

        data = response.json()

        print("API 요청 성공")
        print("JSON 응답 확인 성공")

        return data

    except requests.exceptions.RequestException as e:
        print(f"ERROR: API 요청 실패: {e}")
        return None

    except json.JSONDecodeError:
        print("ERROR: JSON 응답으로 변환하지 못했습니다.")
        print(response.text[:1000])
        return None


# ============================================================
# API 오류 응답 검사
# ============================================================

def check_api_error(data):
    """
    law.go.kr API의 오류 응답을 확인한다.

    예:
    {
        "result": "...",
        "msg": "..."
    }
    """

    if not isinstance(data, dict):
        return False

    if "result" in data and "msg" in data:
        print()
        print("=== API 오류 응답 ===")
        print(f"result: {data.get('result')}")
        print(f"msg: {data.get('msg')}")
        return True

    return False


# ============================================================
# 조문 정규화
# ============================================================

def normalize_articles(article_data):
    """
    조문 데이터를 공통 구조로 변환
    """

    normalized = []

    if not article_data:
        return normalized

    # 조문 > 조
    articles = article_data.get("조", [])

    if isinstance(articles, dict):
        articles = [articles]

    if not isinstance(articles, list):
        return normalized

    for item in articles:

        if not isinstance(item, dict):
            continue

        article_number = item.get("조문번호", "")
        article_title = item.get("조제목", "")
        article_content = item.get("조내용", "")
        article_flag = item.get("조문여부", "")

        # API에서 조문번호가 리스트로 오는 경우
        if isinstance(article_number, list):
            if article_number:
                article_number = article_number[0]
            else:
                article_number = ""

        normalized.append({
            "조문번호": str(article_number),
            "조제목": str(article_title),
            "조내용": str(article_content),
            "조문여부": str(article_flag),
        })

    return normalized


# ============================================================
# 별표 정규화
# ============================================================

def normalize_appendices(appendix_data):
    """
    별표/서식 데이터를 공통 구조로 변환
    """

    normalized = []

    if not appendix_data:
        return normalized

    unit = appendix_data.get("별표단위")

    if unit is None:
        return normalized

    if isinstance(unit, dict):
        unit = [unit]

    if not isinstance(unit, list):
        return normalized

    for item in unit:

        if not isinstance(item, dict):
            continue

        normalized.append({
            "별표번호": item.get("별표번호", ""),
            "별표제목": item.get("별표제목", ""),
            "별표구분": item.get("별표구분", ""),
            "별표내용": item.get("별표내용", ""),
            "첨부파일": item.get("별표첨부파일명", ""),
        })

    return normalized


# ============================================================
# 부칙 정규화
# ============================================================

def normalize_addenda(addenda):
    """
    부칙 데이터를 공통 구조로 변환
    """

    if not addenda:
        return {
            "공포일자": "",
            "내용": "",
        }

    if not isinstance(addenda, dict):
        return {
            "공포일자": "",
            "내용": str(addenda),
        }

    return {
        "공포일자": addenda.get("부칙공포일자", ""),
        "내용": addenda.get("부칙내용", ""),
    }


# ============================================================
# 자치법규 기본정보 정규화
# ============================================================

def normalize_basic_info(info):
    """
    기본정보 공통 구조
    """

    if not isinstance(info, dict):
        return {}

    return {
        "법규명": info.get("자치법규명", ""),
        "법규ID": info.get("자치법규ID", ""),
        "MST": info.get("자치법규일련번호", ""),
        "기관명": info.get("지자체기관명", ""),
        "시행일자": info.get("시행일자", ""),
        "공포일자": info.get("공포일자", ""),
        "제개정정보": info.get("제개정정보", ""),
        "법규종류": info.get("자치법규종류", ""),
    }


# ============================================================
# 상세 응답 분석
# ============================================================

def parse_detail_response(data, law):
    """
    상세 API 응답을 분석하고
    시스템 내부 공통 구조로 변환한다.
    """

    if check_api_error(data):
        return None

    if not isinstance(data, dict):
        print("ERROR: 응답이 dict가 아닙니다.")
        return None

    print()
    print("=== API 응답 최상위 구조 ===")
    print(f"최상위 키: {list(data.keys())}")

    # --------------------------------------------------------
    # LawService 찾기
    # --------------------------------------------------------

    service = data.get("LawService")

    if service is None:

        print("LawService 구조를 찾을 수 없습니다.")

        print()
        print("=== 실제 응답 구조 ===")

        for key, value in data.items():
            print(f"{key}: {type(value)}")

        return None

    if not isinstance(service, dict):
        print("ERROR: LawService가 dict가 아닙니다.")
        return None

    print()
    print("=== LawService 구조 ===")
    print(f"키: {list(service.keys())}")

    # --------------------------------------------------------
    # 기본정보
    # --------------------------------------------------------

    basic = normalize_basic_info(
        service.get("자치법규기본정보", {})
    )

    # --------------------------------------------------------
    # 조문
    # --------------------------------------------------------

    articles = normalize_articles(
        service.get("조문", {})
    )

    # --------------------------------------------------------
    # 별표
    # --------------------------------------------------------

    appendices = normalize_appendices(
        service.get("별표", {})
    )

    # --------------------------------------------------------
    # 부칙
    # --------------------------------------------------------

    addenda = normalize_addenda(
        service.get("부칙", {})
    )

    # --------------------------------------------------------
    # 최종 공통 구조
    # --------------------------------------------------------

    result = {
        "level": law["level"],
        "법규종류": law["type"],
        "법규명": law["name"],
        "target": law["target"],
        "MST": law["mst"],
        "법규ID": law["id"],
        "기본정보": basic,
        "조문": articles,
        "별표": appendices,
        "부칙": addenda,
    }

    return result


# ============================================================
# 키워드 검색
# ============================================================

KEYWORDS = {
    "건폐율": ["건폐율"],
    "용적률": ["용적률"],
    "용도지역": ["용도지역"],
    "용도지구": ["용도지구"],
    "용도구역": ["용도구역"],
    "건축물용도": [
        "건축물의 용도",
        "건축물용도",
        "건축물",
    ],
    "높이": [
        "높이",
        "높이제한",
    ],
    "대지": [
        "대지",
        "대지면적",
    ],
    "도로": [
        "도로",
        "접도",
    ],
    "개발행위": [
        "개발행위",
    ],
    "지구단위계획": [
        "지구단위계획",
    ],
    "주차": [
        "주차",
        "부설주차장",
    ],
}


def search_keywords(articles):
    """
    전체 조문에서 핵심 법규 키워드를 검색
    """

    result = {}

    for category, keywords in KEYWORDS.items():

        matches = []

        for article in articles:

            content = article.get("조내용", "")

            if not content:
                continue

            for keyword in keywords:

                if keyword in content:

                    matches.append(article)
                    break

        result[category] = matches

    return result


# ============================================================
# 조문 출력
# ============================================================

def print_keyword_result(keyword_result):

    print()
    print("=" * 70)
    print("=== 핵심 법규 키워드 분석 ===")
    print("=" * 70)

    for category, articles in keyword_result.items():

        print()
        print(f"[{category}]")
        print(f"관련 조문 수: {len(articles)}")

        for article in articles:

            number = article.get("조문번호", "")
            title = article.get("조제목", "")

            print(f"  - 제{number} {title}")


# ============================================================
# 메인
# ============================================================

def main():

    print("=== STEP 17-21 법규 계층별 상세 본문 통합 조회 테스트 ===")
    print()

    results = []

    # ========================================================
    # 4개 법규 조회
    # ========================================================

    for law in LAW_HIERARCHY:

        print()
        print("=" * 70)
        print(
            f"LEVEL {law['level']} | "
            f"{law['type']}"
        )
        print(law["name"])
        print("=" * 70)

        data = request_detail(law)

        if data is None:
            print("상세 API 요청 실패")
            continue

        parsed = parse_detail_response(data, law)

        if parsed is None:
            print("상세 데이터 정규화 실패")
            continue

        results.append(parsed)

        # ----------------------------------------------------
        # 결과 출력
        # ----------------------------------------------------

        print()
        print("=== 정규화 결과 ===")

        print(f"법규명: {parsed['법규명']}")
        print(f"MST: {parsed['MST']}")

        print(
            f"조문 수: "
            f"{len(parsed['조문'])}"
        )

        print(
            f"별표/서식 수: "
            f"{len(parsed['별표'])}"
        )

        addenda_content = parsed["부칙"].get("내용", "")

        print(
            f"부칙: "
            f"{'있음' if addenda_content else '없음'}"
        )

        # ----------------------------------------------------
        # 키워드 검색
        # ----------------------------------------------------

        keyword_result = search_keywords(
            parsed["조문"]
        )

        print_keyword_result(keyword_result)

        parsed["키워드분석"] = keyword_result

    # ========================================================
    # 통합 결과
    # ========================================================

    print()
    print("=" * 70)
    print("=== STEP 17-21 법규 계층 통합 결과 ===")
    print("=" * 70)

    for result in results:

        print(
            f"LEVEL {result['level']} | "
            f"{result['법규종류']} | "
            f"{result['법규명']}"
        )

        print(
            f"  조문: {len(result['조문'])}개"
        )

        print(
            f"  별표/서식: {len(result['별표'])}개"
        )

    # ========================================================
    # 전체 통계
    # ========================================================

    total_articles = sum(
        len(r["조문"])
        for r in results
    )

    total_appendices = sum(
        len(r["별표"])
        for r in results
    )

    print()
    print("=" * 70)
    print("=== 전체 통합 통계 ===")
    print("=" * 70)

    print(
        f"조회 성공 법규 수: "
        f"{len(results)} / {len(LAW_HIERARCHY)}"
    )

    print(
        f"전체 조문 수: "
        f"{total_articles}"
    )

    print(
        f"전체 별표/서식 수: "
        f"{total_appendices}"
    )

    # ========================================================
    # 성공 여부
    # ========================================================

    print()

    if len(results) == len(LAW_HIERARCHY):

        print("=" * 70)
        print("STEP 17-21 완료")
        print("=" * 70)
        print(
            "4개 법규 계층의 상세 본문 통합 조회에 성공했습니다."
        )

    else:

        print("=" * 70)
        print("STEP 17-21 부분 완료")
        print("=" * 70)

        print(
            "일부 법규의 상세 본문 조회가 실패했습니다."
        )


if __name__ == "__main__":
    main()