import os
import sys
import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-20
# 법규 계층 연결 테스트
#
# LEVEL 1 : 자치구 도시계획 조례
# LEVEL 2 : 서울특별시 도시계획 조례
# LEVEL 3 : 국토의 계획 및 이용에 관한 법률
# LEVEL 4 : 국토의 계획 및 이용에 관한 법률 시행령
# ============================================================


# ============================================================
# 기본 설정
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ENV_PATH = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_PATH)


# ============================================================
# API 인증키
# ============================================================

LAW_API_KEY = os.getenv("LAW_API_KEY")


if not LAW_API_KEY:
    print("ERROR: LAW_API_KEY를 찾을 수 없습니다.")
    print(f"확인한 .env 경로: {ENV_PATH}")
    sys.exit(1)


# ============================================================
# API URL
# ============================================================

LAW_SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"


# ============================================================
# 대상 법규
# ============================================================

TARGET_REGION = "서울특별시 강남구"

LEVEL_1_NAME = "서울특별시 강남구 도시계획 조례"
LEVEL_2_NAME = "서울특별시 도시계획 조례"
LEVEL_3_NAME = "국토의 계획 및 이용에 관한 법률"
LEVEL_4_NAME = "국토의 계획 및 이용에 관한 법률 시행령"


# ============================================================
# 공통 API 요청
# ============================================================

def request_api(params):

    try:

        response = requests.get(
            LAW_SEARCH_URL,
            params=params,
            timeout=20
        )

        print(f"HTTP 상태코드: {response.status_code}")

        response.raise_for_status()

        try:
            data = response.json()
        except Exception as e:
            print("JSON 변환 실패")
            print(f"오류: {e}")
            print("응답 일부:")
            print(response.text[:1000])
            return None

        return data

    except requests.RequestException as e:

        print("API 요청 실패")
        print(f"오류: {e}")

        return None


# ============================================================
# 날짜 정규화
# ============================================================

def normalize_date(value):

    if value is None:
        return ""

    value = str(value).strip()

    return value.replace("-", "").replace(".", "").replace("/", "")


# ============================================================
# 자치법규 검색 결과 정규화
# ============================================================

def normalize_ordin_result(data):

    results = []

    if not isinstance(data, dict):
        return results

    ordin_search = data.get("OrdinSearch", {})

    if not isinstance(ordin_search, dict):
        return results

    law_data = ordin_search.get("law")

    if law_data is None:
        return results

    # --------------------------------------------------------
    # 1. law가 list인 경우
    # --------------------------------------------------------

    if isinstance(law_data, list):

        for item in law_data:

            if isinstance(item, dict):
                results.append(item)

    # --------------------------------------------------------
    # 2. law가 dict인 경우
    # --------------------------------------------------------

    elif isinstance(law_data, dict):

        results.append(law_data)

    return results


# ============================================================
# 국가법령 검색 결과 정규화
# ============================================================

def normalize_law_result(data):

    results = []

    if not isinstance(data, dict):
        return results

    # --------------------------------------------------------
    # 일반적인 LawSearch 구조
    # --------------------------------------------------------

    law_search = data.get("LawSearch")

    if isinstance(law_search, dict):

        law_data = law_search.get("law")

        if isinstance(law_data, list):

            for item in law_data:

                if isinstance(item, dict):
                    results.append(item)

        elif isinstance(law_data, dict):

            results.append(law_data)

    # --------------------------------------------------------
    # 혹시 다른 구조로 반환되는 경우
    # --------------------------------------------------------

    if not results:

        response = data.get("response")

        if isinstance(response, dict):

            body = response.get("body")

            if isinstance(body, dict):

                items = body.get("items")

                if isinstance(items, dict):
                    items = items.get("item")

                if isinstance(items, list):

                    for item in items:

                        if isinstance(item, dict):
                            results.append(item)

                elif isinstance(items, dict):

                    results.append(items)

    return results


# ============================================================
# 자치법규 정확한 이름 검색
# ============================================================

def search_ordinance(ordinance_name):

    print()
    print("=== 자치법규 검색 ===")
    print(f"검색 대상: {ordinance_name}")
    print()

    params = {
        "OC": LAW_API_KEY,
        "target": "ordin",
        "type": "JSON",

        # 자치법규명 검색
        "search": "1",

        # 정확한 검색을 위해 전체 명칭 전달
        "query": ordinance_name,

        "display": "100",
        "page": "1",

        # 현행 자치법규
        "nw": "1",
    }

    print("API 요청 중...")
    print(f"target: {params['target']}")
    print(f"search: {params['search']}")
    print(f"query: {params['query']}")
    print(f"display: {params['display']}")
    print()

    data = request_api(params)

    if data is None:
        return None

    print("JSON 응답 확인 성공")

    # --------------------------------------------------------
    # 응답 구조
    # --------------------------------------------------------

    ordin_search = data.get("OrdinSearch", {})

    if isinstance(ordin_search, dict):

        print()
        print("=== OrdinSearch 구조 ===")
        print(f"키: {ordin_search.keys()}")

        total_cnt = ordin_search.get("totalCnt", "")

        print(f"API 전체 검색 결과: {total_cnt}")

    # --------------------------------------------------------
    # 결과 정규화
    # --------------------------------------------------------

    results = normalize_ordin_result(data)

    print(f"정규화된 결과 수: {len(results)}")

    if not results:

        print("검색 결과가 없습니다.")

        return None

    # --------------------------------------------------------
    # 정확한 명칭 우선
    # --------------------------------------------------------

    exact_results = []

    for item in results:

        name = str(
            item.get("자치법규명", "")
        ).strip()

        if name == ordinance_name:

            exact_results.append(item)

    print(f"정확한 조례명 일치 결과: {len(exact_results)}")

    candidates = exact_results if exact_results else results

    # --------------------------------------------------------
    # 대상 조례 출력
    # --------------------------------------------------------

    print()
    print("=== 자치법규 후보 ===")

    for index, item in enumerate(candidates[:10], start=1):

        print()
        print(f"결과 {index}")

        print(
            f"자치법규명: "
            f"{item.get('자치법규명', '')}"
        )

        print(
            f"지자체기관명: "
            f"{item.get('지자체기관명', '')}"
        )

        print(
            f"자치법규ID: "
            f"{item.get('자치법규ID', '')}"
        )

        print(
            f"MST: "
            f"{item.get('자치법규일련번호', '')}"
        )

        print(
            f"시행일자: "
            f"{item.get('시행일자', '')}"
        )

        print(
            f"공포일자: "
            f"{item.get('공포일자', '')}"
        )

    # ========================================================
    # 정확한 결과 선택
    # ========================================================

    selected = None

    for item in candidates:

        name = str(
            item.get("자치법규명", "")
        ).strip()

        if name == ordinance_name:

            selected = item
            break

    if selected is None:

        # 정확한 명칭이 없을 경우
        # 첫 번째 후보를 사용하지 않고 실패 처리
        print()
        print("정확한 조례명을 가진 결과를 선택하지 못했습니다.")

        return None

    # ========================================================
    # 선택 결과
    # ========================================================

    print()
    print("=== 자치법규 선택 성공 ===")

    print(
        f"자치법규명: "
        f"{selected.get('자치법규명', '')}"
    )

    print(
        f"지자체기관명: "
        f"{selected.get('지자체기관명', '')}"
    )

    print(
        f"자치법규ID: "
        f"{selected.get('자치법규ID', '')}"
    )

    print(
        f"MST: "
        f"{selected.get('자치법규일련번호', '')}"
    )

    print(
        f"시행일자: "
        f"{selected.get('시행일자', '')}"
    )

    print(
        f"공포일자: "
        f"{selected.get('공포일자', '')}"
    )

    print(
        f"자치법규상세링크: "
        f"{selected.get('자치법규상세링크', '')}"
    )

    return selected


# ============================================================
# 국가법령 검색
# ============================================================

def search_national_law(law_name):

    print()
    print("=== 국가법령 검색 ===")
    print(f"검색 대상: {law_name}")
    print()

    params = {
        "OC": LAW_API_KEY,
        "target": "law",
        "type": "JSON",

        # 법령명 검색
        "search": "1",

        "query": law_name,

        "display": "100",
        "page": "1",
    }

    print("API 요청 중...")
    print(f"target: {params['target']}")
    print(f"search: {params['search']}")
    print(f"query: {params['query']}")
    print(f"display: {params['display']}")
    print()

    data = request_api(params)

    if data is None:
        return None

    print("JSON 응답 확인 성공")

    # --------------------------------------------------------
    # 응답 구조 확인
    # --------------------------------------------------------

    print()
    print("=== 국가법령 API 응답 구조 ===")

    print(
        f"최상위 키: "
        f"{data.keys()}"
    )

    law_search = data.get("LawSearch")

    if isinstance(law_search, dict):

        print(
            f"LawSearch 키: "
            f"{law_search.keys()}"
        )

        print(
            f"API 전체 검색 결과: "
            f"{law_search.get('totalCnt', '')}"
        )

    # --------------------------------------------------------
    # 결과 정규화
    # --------------------------------------------------------

    results = normalize_law_result(data)

    print(
        f"정규화된 결과 수: "
        f"{len(results)}"
    )

    if not results:

        print()
        print("국가법령 검색 결과가 없습니다.")

        return None

    # --------------------------------------------------------
    # 후보 출력
    # --------------------------------------------------------

    print()
    print("=== 국가법령 후보 ===")

    for index, item in enumerate(results[:10], start=1):

        name = (
            item.get("법령명한글")
            or item.get("법령명")
            or ""
        )

        print()
        print(f"결과 {index}")

        print(f"법령명: {name}")

        print(
            f"법령ID: "
            f"{item.get('법령ID', '')}"
        )

        print(
            f"법령일련번호: "
            f"{item.get('법령일련번호', '')}"
        )

        print(
            f"시행일자: "
            f"{item.get('시행일자', '')}"
        )

        print(
            f"공포일자: "
            f"{item.get('공포일자', '')}"
        )

        print(
            f"법령구분명: "
            f"{item.get('법령구분명', '')}"
        )

    # ========================================================
    # 정확한 명칭 우선 선택
    # ========================================================

    selected = None

    for item in results:

        name = (
            item.get("법령명한글")
            or item.get("법령명")
            or ""
        )

        name = str(name).strip()

        if name == law_name:

            selected = item
            break

    # --------------------------------------------------------
    # 정확한 결과가 없을 경우
    # --------------------------------------------------------

    if selected is None:

        print()
        print("정확한 법령명을 가진 결과를 찾지 못했습니다.")

        # 후보 중 이름에 검색어가 포함되는지 확인
        for item in results:

            name = (
                item.get("법령명한글")
                or item.get("법령명")
                or ""
            )

            name = str(name).strip()

            if law_name in name:

                selected = item
                break

    if selected is None:

        print("대상 국가법령을 자동 선택하지 못했습니다.")

        return None

    # ========================================================
    # 선택 결과
    # ========================================================

    selected_name = (
        selected.get("법령명한글")
        or selected.get("법령명")
        or ""
    )

    print()
    print("=== 국가법령 선택 성공 ===")

    print(f"법령명: {selected_name}")

    print(
        f"법령ID: "
        f"{selected.get('법령ID', '')}"
    )

    print(
        f"법령일련번호: "
        f"{selected.get('법령일련번호', '')}"
    )

    print(
        f"현행연혁코드: "
        f"{selected.get('현행연혁코드', '')}"
    )

    print(
        f"시행일자: "
        f"{selected.get('시행일자', '')}"
    )

    print(
        f"공포일자: "
        f"{selected.get('공포일자', '')}"
    )

    print(
        f"법령상세링크: "
        f"{selected.get('법령상세링크', '')}"
    )

    return selected


# ============================================================
# LEVEL 출력
# ============================================================

def print_level(level, law_type, name, result):

    print()
    print("=" * 70)

    print(f"LEVEL {level}")

    print(f"법규 종류: {law_type}")

    print(f"법규명: {name}")

    print("=" * 70)

    if result:

        print("상태: 검색 성공")

    else:

        print("상태: 검색 실패")


# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":

    print(
        "=== STEP 17-20 법규 계층 연결 테스트 ==="
    )

    print()

    print(
        f"대상 지역: {TARGET_REGION}"
    )

    print(
        f"기준 조례: {LEVEL_1_NAME}"
    )

    print()
    print("=" * 70)

    # ========================================================
    # LEVEL 1
    # ========================================================

    print()
    print("=" * 70)
    print("LEVEL 1")
    print("자치구 조례")
    print(LEVEL_1_NAME)
    print("=" * 70)

    level1 = search_ordinance(
        LEVEL_1_NAME
    )

    print_level(
        1,
        "자치구 조례",
        LEVEL_1_NAME,
        level1
    )

    # ========================================================
    # LEVEL 2
    # ========================================================

    print()
    print("=" * 70)
    print("LEVEL 2")
    print("서울특별시 조례")
    print(LEVEL_2_NAME)
    print("=" * 70)

    level2 = search_ordinance(
        LEVEL_2_NAME
    )

    print_level(
        2,
        "서울특별시 조례",
        LEVEL_2_NAME,
        level2
    )

    # ========================================================
    # LEVEL 3
    # ========================================================

    print()
    print("=" * 70)
    print("LEVEL 3")
    print("국가 법률")
    print(LEVEL_3_NAME)
    print("=" * 70)

    level3 = search_national_law(
        LEVEL_3_NAME
    )

    print_level(
        3,
        "국가 법률",
        LEVEL_3_NAME,
        level3
    )

    # ========================================================
    # LEVEL 4
    # ========================================================

    print()
    print("=" * 70)
    print("LEVEL 4")
    print("국가 시행령")
    print(LEVEL_4_NAME)
    print("=" * 70)

    level4 = search_national_law(
        LEVEL_4_NAME
    )

    print_level(
        4,
        "국가 시행령",
        LEVEL_4_NAME,
        level4
    )

    # ========================================================
    # 최종 계층
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("=== STEP 17-20 법규 계층 연결 결과 ===")
    print("=" * 70)

    print(
        f"LEVEL 1 | 자치구 조례 | "
        f"{LEVEL_1_NAME} | "
        f"{'검색 성공' if level1 else '검색 실패'}"
    )

    print(
        f"LEVEL 2 | 서울특별시 조례 | "
        f"{LEVEL_2_NAME} | "
        f"{'검색 성공' if level2 else '검색 실패'}"
    )

    print(
        f"LEVEL 3 | 국가 법률 | "
        f"{LEVEL_3_NAME} | "
        f"{'검색 성공' if level3 else '검색 실패'}"
    )

    print(
        f"LEVEL 4 | 국가 시행령 | "
        f"{LEVEL_4_NAME} | "
        f"{'검색 성공' if level4 else '검색 실패'}"
    )

    # ========================================================
    # 식별자 출력
    # ========================================================

    print()
    print()
    print("=" * 70)
    print("=== 상세 API 연결용 식별자 ===")
    print("=" * 70)

    # --------------------------------------------------------
    # LEVEL 1
    # --------------------------------------------------------

    if level1:

        print()
        print(
            f"[LEVEL 1] {LEVEL_1_NAME}"
        )

        print(
            f"MST: "
            f"{level1.get('자치법규일련번호', '')}"
        )

        print(
            f"자치법규ID: "
            f"{level1.get('자치법규ID', '')}"
        )

    # --------------------------------------------------------
    # LEVEL 2
    # --------------------------------------------------------

    if level2:

        print()
        print(
            f"[LEVEL 2] {LEVEL_2_NAME}"
        )

        print(
            f"MST: "
            f"{level2.get('자치법규일련번호', '')}"
        )

        print(
            f"자치법규ID: "
            f"{level2.get('자치법규ID', '')}"
        )

    # --------------------------------------------------------
    # LEVEL 3
    # --------------------------------------------------------

    if level3:

        print()
        print(
            f"[LEVEL 3] {LEVEL_3_NAME}"
        )

        print(
            f"법령ID: "
            f"{level3.get('법령ID', '')}"
        )

        print(
            f"법령일련번호: "
            f"{level3.get('법령일련번호', '')}"
        )

    # --------------------------------------------------------
    # LEVEL 4
    # --------------------------------------------------------

    if level4:

        print()
        print(
            f"[LEVEL 4] {LEVEL_4_NAME}"
        )

        print(
            f"법령ID: "
            f"{level4.get('법령ID', '')}"
        )

        print(
            f"법령일련번호: "
            f"{level4.get('법령일련번호', '')}"
        )

    # ========================================================
    # 완료
    # ========================================================

    print()
    print("=" * 70)
    print(
        "STEP 17-20 3차 법규 계층 연결 테스트 완료"
    )
    print("=" * 70)