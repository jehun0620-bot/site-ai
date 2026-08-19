import json
import re
from pathlib import Path


# ============================================================
# STEP 17-21-C-5-1
#
# 용도지역별 건폐율 / 용적률 구조화 테스트
#
# 목적
# ------------------------------------------------------------
# 1. C-4 CORE 후보에서
#    기본 건폐율 / 용적률 조문 식별
#
# 2. 조문 본문에서
#    용도지역 → 비율 매핑 자동 추출
#
# 3. 국가 시행령 기준과
#    서울특별시 조례 기준을 분리
#
# 4. 대상 SITE 용도지역
#    "제3종일반주거지역"에 실제 연결
#
# 5. 완화 / 강화 / 특례 규정은
#    기본값과 분리하여 저장
#
# 6. "100퍼센트 이상 300퍼센트 이하" 형태의
#    최소 / 최대 범위를 정확하게 분리
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_core_rule_filtered.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_zone_ratio_map.json"
)


# ============================================================
# 테스트 대상 용도지역
# ============================================================

TARGET_ZONE = "제3종일반주거지역"


# ============================================================
# 용도지역 목록
# ============================================================

ZONE_NAMES = [
    "제1종전용주거지역",
    "제2종전용주거지역",
    "제1종일반주거지역",
    "제2종일반주거지역",
    "제3종일반주거지역",
    "준주거지역",

    "중심상업지역",
    "일반상업지역",
    "근린상업지역",
    "유통상업지역",

    "전용공업지역",
    "일반공업지역",
    "준공업지역",

    "보전녹지지역",
    "생산녹지지역",
    "자연녹지지역",

    "보전관리지역",
    "생산관리지역",
    "계획관리지역",

    "농림지역",
    "자연환경보전지역",
]


# ============================================================
# 기본 규정 제목
#
# 특례 / 완화 / 강화가 아닌
# 일반 용도지역별 기본 기준만 대상으로 한다.
# ============================================================

BASE_RULE_TITLES = {
    "건폐율": {
        4: [
            "용도지역안에서의 건폐율",
            "용도지역 안에서의 건폐율",
        ],

        2: [
            "용도지역 안에서의 건폐율",
            "용도지역안에서의 건폐율",
        ],
    },

    "용적률": {
        4: [
            "용도지역 안에서의 용적률",
            "용도지역안에서의 용적률",
        ],

        2: [
            "용도지역 안에서의 용적률",
            "용도지역안에서의 용적률",
        ],
    },
}


# ============================================================
# 공통 함수
# ============================================================

def normalize_space(value):

    if value is None:
        return ""

    text = str(value)

    text = text.replace("\r", " ")
    text = text.replace("\n", " ")

    while "  " in text:
        text = text.replace("  ", " ")

    return text.strip()


def normalize_title(value):

    text = normalize_space(value)

    # API 응답에서
    #
    # 용도지역안에서의
    # 용도지역 안에서의
    #
    # 두 형식이 혼용되므로 통일한다.
    text = text.replace(
        "용도지역안에서의",
        "용도지역 안에서의",
    )

    return text


# ============================================================
# 한국어 숫자 퍼센트 변환
#
# 예:
#
# 50퍼센트
# 250퍼센트
# 1천퍼센트
# 1천500퍼센트
# 1,500퍼센트
# ============================================================

def parse_korean_percentage(raw):

    if raw is None:
        return None

    text = normalize_space(raw)

    text = text.replace(",", "")
    text = text.replace(" ", "")

    text = text.replace(
        "퍼센트",
        "",
    )

    text = text.replace(
        "%",
        "",
    )

    # --------------------------------------------------------
    # 1천500
    # 1천
    # --------------------------------------------------------

    match = re.fullmatch(
        r"(\d+)천(\d*)",
        text,
    )

    if match:

        thousands = int(
            match.group(1)
        )

        remainder_text = (
            match.group(2)
        )

        remainder = (
            int(remainder_text)
            if remainder_text
            else 0
        )

        return float(
            thousands * 1000
            + remainder
        )

    # --------------------------------------------------------
    # 일반 숫자
    # --------------------------------------------------------

    try:

        return float(text)

    except ValueError:

        return None


# ============================================================
# 퍼센트 표현 정규식
#
# 예:
#
# 50퍼센트
# 250 퍼센트
# 1천퍼센트
# 1천500퍼센트
# 1,500퍼센트
# 50%
# ============================================================

PERCENT_TOKEN = (
    r"(?:"
    r"\d+천\s*\d*"
    r"|"
    r"\d[\d,]*"
    r")"
    r"\s*"
    r"(?:퍼센트|%)"
)


# ============================================================
# 용도지역별 문장 / 항목 추출
#
# 예:
#
# 제3종일반주거지역 : 50퍼센트 이하
#
# 또는
#
# 제3종일반주거지역 :
# 100퍼센트 이상 300퍼센트 이하
# ============================================================

def extract_zone_segment(
    text,
    zone,
):

    text = normalize_space(text)

    start = text.find(zone)

    if start == -1:
        return ""

    # --------------------------------------------------------
    # 현재 용도지역 다음에 등장하는
    # 다른 용도지역 위치를 찾는다.
    # --------------------------------------------------------

    end_candidates = []

    for other_zone in ZONE_NAMES:

        if other_zone == zone:
            continue

        position = text.find(
            other_zone,
            start + len(zone),
        )

        if position != -1:

            end_candidates.append(
                position
            )

    if end_candidates:

        end = min(
            end_candidates
        )

    else:

        # 다음 용도지역이 없을 경우
        # 특례 본문 전체가 붙는 것을 방지한다.
        end = min(
            len(text),
            start + 500,
        )

    return text[
        start:end
    ].strip()


# ============================================================
# 용도지역 구간에서 비율 추출
#
# 중요 수정사항:
#
# 기존 방식:
#
#   100퍼센트 뒤 15글자를 검색
#
#   "이상 300퍼센트 이하"
#
# → 이상과 이하가 모두 발견되어
#   100이 max로 잘못 분류되는 문제 발생
#
#
# 수정 방식:
#
#   퍼센트 토큰 바로 뒤에 붙는
#   이상 / 이하 / 초과 / 미만만 연결한다.
#
# 결과:
#
#   100퍼센트 이상 → min
#   300퍼센트 이하 → max
# ============================================================

def extract_percentages_from_segment(
    segment,
):

    results = []

    pattern = re.compile(
        rf"(?P<percent>{PERCENT_TOKEN})"
        rf"\s*"
        rf"(?P<condition>이상|이하|초과|미만)?"
    )

    for match in pattern.finditer(
        segment
    ):

        raw = match.group(
            "percent"
        )

        condition_text = match.group(
            "condition"
        )

        value = (
            parse_korean_percentage(
                raw
            )
        )

        if value is None:
            continue

        condition = None

        if condition_text == "이상":

            condition = "min"

        elif condition_text == "이하":

            condition = "max"

        elif condition_text == "초과":

            condition = "over"

        elif condition_text == "미만":

            condition = "under"

        before_text = segment[
            max(
                0,
                match.start() - 20,
            ):
            match.start()
        ]

        after_text = segment[
            match.end():
            match.end() + 20
        ]

        results.append(
            {
                "raw": raw,
                "value": value,
                "condition": condition,
                "condition_text": condition_text,
                "before": before_text,
                "after": after_text,
            }
        )

    return results


# ============================================================
# 기본 규정 후보인지 판정
# ============================================================

def is_base_rule(
    candidate,
    category,
):

    level = candidate.get(
        "level"
    )

    title = normalize_title(
        candidate.get(
            "article_title",
            "",
        )
        or
        candidate.get(
            "appendix_title",
            "",
        )
    )

    allowed_titles = (
        BASE_RULE_TITLES
        .get(
            category,
            {},
        )
        .get(
            level,
            [],
        )
    )

    for allowed_title in allowed_titles:

        if (
            normalize_title(
                allowed_title
            )
            == title
        ):

            return True

    return False


# ============================================================
# 기본 규정 후보 찾기
# ============================================================

def find_base_rule_candidates(
    data,
    category,
):

    category_data = (
        data
        .get(
            "categories",
            {},
        )
        .get(
            category,
            {},
        )
    )

    core_candidates = (
        category_data.get(
            "core",
            [],
        )
    )

    results = []

    for candidate in core_candidates:

        if is_base_rule(
            candidate,
            category,
        ):

            results.append(
                candidate
            )

    return results


# ============================================================
# 용도지역 하나의 기준 추출
# ============================================================

def extract_zone_ratio(
    candidate,
    zone,
    category,
):

    text = normalize_space(
        candidate.get(
            "text",
            "",
        )
    )

    segment = (
        extract_zone_segment(
            text,
            zone,
        )
    )

    if not segment:
        return None

    percentages = (
        extract_percentages_from_segment(
            segment
        )
    )

    if not percentages:
        return None

    minimum = None
    maximum = None

    unclassified = []

    over_values = []
    under_values = []

    # ========================================================
    # 최소 / 최대값 분석
    # ========================================================

    for item in percentages:

        condition = item[
            "condition"
        ]

        value = item[
            "value"
        ]

        # ----------------------------------------------------
        # 이상
        #
        # 여러 값이 있는 경우
        # 가장 강한 최소조건 = 큰 값
        # ----------------------------------------------------

        if condition == "min":

            if minimum is None:

                minimum = value

            else:

                minimum = max(
                    minimum,
                    value,
                )

        # ----------------------------------------------------
        # 이하
        #
        # 여러 값이 있는 경우
        # 가장 강한 최대조건 = 작은 값
        # ----------------------------------------------------

        elif condition == "max":

            if maximum is None:

                maximum = value

            else:

                maximum = min(
                    maximum,
                    value,
                )

        # ----------------------------------------------------
        # 초과
        # ----------------------------------------------------

        elif condition == "over":

            over_values.append(
                value
            )

        # ----------------------------------------------------
        # 미만
        # ----------------------------------------------------

        elif condition == "under":

            under_values.append(
                value
            )

        # ----------------------------------------------------
        # 조건 없음
        #
        # 예:
        # 제3종일반주거지역: 250퍼센트
        # ----------------------------------------------------

        else:

            unclassified.append(
                value
            )

    # ========================================================
    # 서울특별시 조례처럼
    #
    # 제3종일반주거지역: 250퍼센트
    #
    # 라고 적혀 있지만
    #
    # 조문 서두에
    #
    # "다음 각 호의 비율 이하로 한다"
    #
    # 라고 규정된 경우
    #
    # 해당 숫자를 maximum으로 판정한다.
    # ========================================================

    if (
        maximum is None
        and unclassified
    ):

        if (
            "비율 이하로 한다"
            in text
        ):

            maximum = (
                unclassified[0]
            )

    # ========================================================
    # 건폐율 조례의 단일 숫자
    #
    # 혹시 문구 변화로
    # "비율 이하로 한다" 탐지가 되지 않더라도
    # 건폐율 기본규정에서 단일값이면 최대값으로 취급
    # ========================================================

    if (
        maximum is None
        and category == "건폐율"
        and unclassified
    ):

        maximum = (
            unclassified[0]
        )

    return {
        "zone": zone,

        "minimum": minimum,

        "maximum": maximum,

        "over_values": over_values,

        "under_values": under_values,

        "unclassified_values": (
            unclassified
        ),

        "raw_values": [
            item["value"]
            for item
            in percentages
        ],

        "percentage_details": (
            percentages
        ),

        "segment": segment,

        "law_name": (
            candidate.get(
                "law_name",
                "",
            )
        ),

        "level": (
            candidate.get(
                "level"
            )
        ),

        "article_number": (
            candidate.get(
                "article_number",
                "",
            )
        ),

        "article_branch_number": (
            candidate.get(
                "article_branch_number",
                "",
            )
        ),

        "article_title": (
            candidate.get(
                "article_title",
                "",
            )
        ),

        "source_type": (
            candidate.get(
                "source_type",
                "",
            )
        ),
    }


# ============================================================
# 전체 용도지역 맵 생성
# ============================================================

def build_zone_map(
    candidates,
    category,
):

    result = {}

    for candidate in candidates:

        level = str(
            candidate.get(
                "level"
            )
        )

        for zone in ZONE_NAMES:

            ratio = extract_zone_ratio(
                candidate,
                zone,
                category,
            )

            if ratio is None:
                continue

            if zone not in result:

                result[
                    zone
                ] = {}

            result[
                zone
            ][
                level
            ] = ratio

    return result


# ============================================================
# 특례 후보 분리
# ============================================================

def collect_special_candidates(
    data,
    category,
):

    category_data = (
        data
        .get(
            "categories",
            {},
        )
        .get(
            category,
            {},
        )
    )

    candidates = []

    for group_name in [
        "core",
        "reference",
    ]:

        group = category_data.get(
            group_name,
            [],
        )

        for candidate in group:

            # 기본 용도지역 규정은 제외
            if is_base_rule(
                candidate,
                category,
            ):

                continue

            special = candidate.get(
                "special_rule_candidates",
                [],
            )

            title = normalize_space(
                candidate.get(
                    "article_title",
                    "",
                )
                or
                candidate.get(
                    "appendix_title",
                    "",
                )
            )

            # ------------------------------------------------
            # 완화 / 강화 / 특례 / 기타 적용기준 후보만 유지
            # ------------------------------------------------

            if (
                special
                or "완화" in title
                or "강화" in title
                or "특례" in title
                or "그 밖의" in title
            ):

                candidates.append(
                    candidate
                )

    return candidates


# ============================================================
# 대상 용도지역 최종 기본값 판정
# ============================================================

def determine_base_value(
    zone_map,
    zone,
):

    zone_data = zone_map.get(
        zone,
        {},
    )

    # LEVEL 4
    # 국토계획법 시행령
    national = zone_data.get(
        "4"
    )

    # LEVEL 2
    # 서울특별시 도시계획 조례
    seoul = zone_data.get(
        "2"
    )

    result = {
        "zone": zone,

        "national_standard": (
            national
        ),

        "seoul_standard": (
            seoul
        ),

        "selected_value": None,

        "selected_source": None,

        "validation": None,

        "validation_detail": None,
    }

    # ========================================================
    # 기본 적용값 선택
    #
    # 시행령:
    # 조례가 정할 수 있는 상위 허용범위
    #
    # 서울특별시 조례:
    # 서울특별시에서 적용되는 기본 기준
    # ========================================================

    if (
        seoul
        and seoul.get(
            "maximum"
        ) is not None
    ):

        result[
            "selected_value"
        ] = seoul[
            "maximum"
        ]

        result[
            "selected_source"
        ] = (
            "서울특별시 도시계획 조례"
        )

    elif (
        national
        and national.get(
            "maximum"
        ) is not None
    ):

        result[
            "selected_value"
        ] = national[
            "maximum"
        ]

        result[
            "selected_source"
        ] = (
            "국토의 계획 및 이용에 관한 "
            "법률 시행령"
        )

    # ========================================================
    # 상위법 범위 검증
    #
    # 서울 조례값이
    # 시행령 최소 이상 + 최대 이하인지 검사
    # ========================================================

    if (
        national
        and seoul
        and seoul.get(
            "maximum"
        ) is not None
    ):

        national_min = (
            national.get(
                "minimum"
            )
        )

        national_max = (
            national.get(
                "maximum"
            )
        )

        seoul_value = (
            seoul.get(
                "maximum"
            )
        )

        min_pass = True
        max_pass = True

        if national_min is not None:

            min_pass = (
                seoul_value
                >= national_min
            )

        if national_max is not None:

            max_pass = (
                seoul_value
                <= national_max
            )

        if (
            min_pass
            and max_pass
        ):

            result[
                "validation"
            ] = "PASS"

        else:

            result[
                "validation"
            ] = "FAIL"

        result[
            "validation_detail"
        ] = {
            "national_minimum": (
                national_min
            ),

            "national_maximum": (
                national_max
            ),

            "seoul_value": (
                seoul_value
            ),

            "minimum_check": (
                min_pass
            ),

            "maximum_check": (
                max_pass
            ),
        }

    return result


# ============================================================
# 출력
# ============================================================

def print_ratio_result(
    category,
    result,
):

    print()
    print("=" * 70)

    print(
        f"[{category}]"
    )

    print("=" * 70)

    national = result.get(
        "national_standard"
    )

    seoul = result.get(
        "seoul_standard"
    )

    print(
        "대상 용도지역:",
        result.get(
            "zone"
        )
    )

    print()

    # --------------------------------------------------------
    # 국가 시행령
    # --------------------------------------------------------

    print(
        "--- 국가 시행령 기준 ---"
    )

    if national:

        print(
            "법규:",
            national.get(
                "law_name"
            )
        )

        print(
            "조문:",
            national.get(
                "article_title"
            )
        )

        print(
            "최소:",
            national.get(
                "minimum"
            )
        )

        print(
            "최대:",
            national.get(
                "maximum"
            )
        )

        print(
            "원문 구간:",
            national.get(
                "segment",
                "",
            )[:350]
        )

    else:

        print(
            "조회되지 않음"
        )

    print()

    # --------------------------------------------------------
    # 서울특별시 조례
    # --------------------------------------------------------

    print(
        "--- 서울특별시 조례 기준 ---"
    )

    if seoul:

        print(
            "법규:",
            seoul.get(
                "law_name"
            )
        )

        print(
            "조문:",
            seoul.get(
                "article_title"
            )
        )

        print(
            "최소:",
            seoul.get(
                "minimum"
            )
        )

        print(
            "최대:",
            seoul.get(
                "maximum"
            )
        )

        print(
            "원문 구간:",
            seoul.get(
                "segment",
                "",
            )[:350]
        )

    else:

        print(
            "조회되지 않음"
        )

    print()

    # --------------------------------------------------------
    # 기본값
    # --------------------------------------------------------

    print(
        "--- 기본값 선택 ---"
    )

    print(
        "선택값:",
        result.get(
            "selected_value"
        ),
        "%"
    )

    print(
        "출처:",
        result.get(
            "selected_source"
        )
    )

    print(
        "상위 기준 검증:",
        result.get(
            "validation"
        )
    )

    validation_detail = (
        result.get(
            "validation_detail"
        )
    )

    if validation_detail:

        print(
            "검증 상세:"
        )

        print(
            "  시행령 최소:",
            validation_detail.get(
                "national_minimum"
            )
        )

        print(
            "  시행령 최대:",
            validation_detail.get(
                "national_maximum"
            )
        )

        print(
            "  서울 조례값:",
            validation_detail.get(
                "seoul_value"
            )
        )


# ============================================================
# 특례 출력
# ============================================================

def print_special_candidates(
    category,
    candidates,
):

    print()
    print("=" * 70)

    print(
        f"[{category}] "
        "별도 검토가 필요한 특례/완화/강화 후보"
    )

    print("=" * 70)

    if not candidates:

        print(
            "특례 후보 없음"
        )

        return

    for index, candidate in enumerate(
        candidates[:15],
        start=1,
    ):

        title = (
            candidate.get(
                "article_title",
                "",
            )
            or
            candidate.get(
                "appendix_title",
                "",
            )
        )

        print()

        print(
            f"{index}. "
            f"L{candidate.get('level')} "
            f"| "
            f"{candidate.get('law_name')}"
        )

        print(
            "   규정:",
            title
        )

        print(
            "   분류:",
            candidate.get(
                "classification"
            )
        )

        print(
            "   점수:",
            candidate.get(
                "relevance_score"
            )
        )

        special = candidate.get(
            "special_rule_candidates",
            [],
        )

        if special:

            print(
                "   특례 표현:",
                ", ".join(
                    special
                )
            )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-5-1 "
        "용도지역별 건폐율 / 용적률 "
        "구조화 테스트 ==="
    )

    print()

    print(
        "입력 파일:"
    )

    print(
        INPUT_FILE
    )

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"입력 파일이 없습니다:\n"
            f"{INPUT_FILE}"
        )

    # ========================================================
    # C-4 결과 로드
    # ========================================================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    category_maps = {}

    special_maps = {}

    final_results = {}

    # ========================================================
    # 카테고리별 처리
    # ========================================================

    for category in [
        "건폐율",
        "용적률",
    ]:

        print()
        print()
        print("=" * 70)

        print(
            f"{category} 기본 규정 탐색"
        )

        print("=" * 70)

        candidates = (
            find_base_rule_candidates(
                data,
                category,
            )
        )

        print(
            "기본 규정 후보:",
            len(candidates)
        )

        for candidate in candidates:

            print(
                f"L{candidate.get('level')} | "
                f"{candidate.get('law_name')} | "
                f"{candidate.get('article_title')}"
            )

        # ----------------------------------------------------
        # 용도지역 맵
        # ----------------------------------------------------

        zone_map = build_zone_map(
            candidates,
            category,
        )

        category_maps[
            category
        ] = zone_map

        # ----------------------------------------------------
        # 특례
        # ----------------------------------------------------

        specials = (
            collect_special_candidates(
                data,
                category,
            )
        )

        special_maps[
            category
        ] = specials

        # ----------------------------------------------------
        # 대상 용도지역 기본값 판정
        # ----------------------------------------------------

        final_result = (
            determine_base_value(
                zone_map,
                TARGET_ZONE,
            )
        )

        final_results[
            category
        ] = final_result

        print_ratio_result(
            category,
            final_result,
        )

        print_special_candidates(
            category,
            specials,
        )

    # ========================================================
    # 대상 SITE 결과
    # ========================================================

    print()
    print()
    print("=" * 70)

    print(
        "=== 대상 SITE 기본 법규값 ==="
    )

    print("=" * 70)

    print(
        "용도지역:",
        TARGET_ZONE
    )

    coverage = (
        final_results[
            "건폐율"
        ]
    )

    far = (
        final_results[
            "용적률"
        ]
    )

    print()

    print(
        "기본 건폐율:",
        coverage.get(
            "selected_value"
        ),
        "%"
    )

    print(
        "건폐율 출처:",
        coverage.get(
            "selected_source"
        )
    )

    print(
        "상위법 검증:",
        coverage.get(
            "validation"
        )
    )

    print()

    print(
        "기본 용적률:",
        far.get(
            "selected_value"
        ),
        "%"
    )

    print(
        "용적률 출처:",
        far.get(
            "selected_source"
        )
    )

    print(
        "상위법 검증:",
        far.get(
            "validation"
        )
    )

    print()

    print(
        "※ 위 값은 기본 용도지역 기준입니다."
    )

    print(
        "※ 지구단위계획 / 용적률 완화 / "
        "건폐율 완화 / 경관지구 / 기타 특례는 "
        "아직 적용하지 않았습니다."
    )

    # ========================================================
    # 저장
    # ========================================================

    output_data = {
        "target_zone": (
            TARGET_ZONE
        ),

        "zone_maps": (
            category_maps
        ),

        "target_result": (
            final_results
        ),

        "special_candidates": (
            special_maps
        ),
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output_data,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print()
    print()
    print("=" * 70)

    print(
        "결과 저장:"
    )

    print(
        OUTPUT_FILE
    )

    print("=" * 70)

    print()

    print(
        "STEP 17-21-C-5-1 완료"
    )

    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-6"
    )

    print(
        "→ 기본값과 특례 규정을 분리하여 "
        "적용조건 분석"
    )

    print(
        "→ 지구단위계획 / 용도지구 / "
        "기타 SITE 조건과 결합"
    )

    print(
        "→ 최종 적용 가능한 "
        "건폐율 / 용적률 판정 구조 구축"
    )


if __name__ == "__main__":
    main()