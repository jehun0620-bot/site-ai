import json
import re
from pathlib import Path


# ============================================================
# STEP 17-21-C-4
# 핵심 규정 후보 선별 테스트
#
# 입력:
#   law_data/output/law_core_rule_matches.json
#
# 목적:
# 1. 건폐율 / 용적률 검색 결과에서
#    실제 수치 기준 규정 후보를 선별
# 2. 단순 언급 / 절차 / 정의 규정을 낮은 점수로 분류
# 3. CORE / REFERENCE / NOISE 분류
# 4. 다음 단계 수치 추출용 데이터 저장
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_core_rule_matches.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_core_rule_filtered.json"
)


# ============================================================
# 분석 대상 카테고리
# ============================================================

TARGET_CATEGORIES = [
    "건폐율",
    "용적률",
]


# ============================================================
# 규정 중요도 점수
# ============================================================

CORE_TITLE_PATTERNS = {
    "건폐율": [
        "용도지역 안에서의 건폐율",
        "용도지역안에서의 건폐율",
        "건폐율의 완화",
        "건폐율 완화",
        "건폐율",
    ],

    "용적률": [
        "용도지역 안에서의 용적률",
        "용도지역안에서의 용적률",
        "용적률의 완화",
        "용적률 완화",
        "용적률",
    ],
}


# ------------------------------------------------------------
# 강하게 관련 있는 본문 표현
# ------------------------------------------------------------

STRONG_TEXT_PATTERNS = {
    "건폐율": [
        "건폐율은",
        "건폐율을",
        "건폐율의 최대한도",
        "건폐율의 최대 한도",
        "퍼센트 이하",
        "도시ㆍ군계획조례가 정하는 비율",
        "도시계획조례로 정하는 비율",
    ],

    "용적률": [
        "용적률은",
        "용적률을",
        "용적률의 최대한도",
        "용적률의 최대 한도",
        "퍼센트 이하",
        "퍼센트 이상",
        "도시ㆍ군계획조례가 정하는 비율",
        "도시계획조례로 정하는 비율",
    ],
}


# ------------------------------------------------------------
# 용도지역명
# ------------------------------------------------------------

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


# ------------------------------------------------------------
# 단순 언급 가능성이 높은 제목
# ------------------------------------------------------------

NOISE_TITLE_PATTERNS = [
    "정의",
    "입안",
    "제안",
    "의견청취",
    "결정권자",
    "관리계획의 결정",
    "권한위임",
    "사무위임",
    "지정대상",
    "내용의 제공",
]


# ------------------------------------------------------------
# 특례 / 완화 / 예외
#
# 핵심 수치 규정과 별도로 관리해야 함
# ------------------------------------------------------------

SPECIAL_RULE_PATTERNS = [
    "완화",
    "특례",
    "예외",
    "특별한 경우",
    "초과할 수",
    "불구하고",
    "기부채납",
    "공공시설",
    "지구단위계획",
    "방화지구",
    "방재지구",
]


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


def unique_list(values):

    result = []

    seen = set()

    for value in values:

        if value in seen:
            continue

        seen.add(value)
        result.append(value)

    return result


# ============================================================
# 숫자 후보 추출
# ============================================================

def extract_percentage_candidates(text):
    """
    50퍼센트
    300퍼센트
    1천500퍼센트
    120퍼센트
    등의 표현 추출
    """

    text = normalize_space(text)

    patterns = [
        r"(\d[\d,]*)\s*퍼센트",
        r"(\d+)\s*%",
        r"(\d+)천(\d*)\s*퍼센트",
    ]

    results = []

    # 일반 숫자 퍼센트
    for match in re.finditer(
        patterns[0],
        text
    ):

        raw = match.group(0)

        value_text = match.group(1).replace(
            ",",
            ""
        )

        try:
            value = float(value_text)

        except ValueError:
            value = None

        results.append(
            {
                "raw": raw,
                "value": value,
            }
        )

    # % 기호
    for match in re.finditer(
        patterns[1],
        text
    ):

        raw = match.group(0)

        try:
            value = float(
                match.group(1)
            )

        except ValueError:
            value = None

        results.append(
            {
                "raw": raw,
                "value": value,
            }
        )

    # "1천500퍼센트" 형태
    thousand_pattern = re.compile(
        r"(\d+)천\s*(\d*)\s*퍼센트"
    )

    for match in thousand_pattern.finditer(
        text
    ):

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

        value = (
            thousands * 1000
            + remainder
        )

        results.append(
            {
                "raw": match.group(0),
                "value": float(value),
            }
        )

    # 중복 제거
    deduplicated = []

    seen = set()

    for item in results:

        signature = (
            item["raw"],
            item["value"],
        )

        if signature in seen:
            continue

        seen.add(signature)

        deduplicated.append(
            item
        )

    return deduplicated


# ============================================================
# 용도지역 후보
# ============================================================

def extract_zone_candidates(text):

    found = []

    for zone in ZONE_NAMES:

        if zone in text:
            found.append(zone)

    return found


# ============================================================
# 특례 판정
# ============================================================

def detect_special_rule(text):

    found = []

    for pattern in SPECIAL_RULE_PATTERNS:

        if pattern in text:
            found.append(pattern)

    return unique_list(found)


# ============================================================
# 후보 점수 계산
# ============================================================

def calculate_score(
    match,
    category,
):

    score = 0

    reasons = []

    source_type = match.get(
        "source_type",
        ""
    )

    level = match.get(
        "level",
        0
    )

    title = normalize_space(
        match.get(
            "article_title",
            ""
        )
        or
        match.get(
            "appendix_title",
            ""
        )
    )

    text = normalize_space(
        match.get(
            "text",
            ""
        )
    )

    combined = (
        title
        + " "
        + text
    )

    # ========================================================
    # 1. 제목 점수
    # ========================================================

    for pattern in (
        CORE_TITLE_PATTERNS[
            category
        ]
    ):

        if pattern in title:

            if (
                "용도지역 안에서의"
                in pattern
                or
                "용도지역안에서의"
                in pattern
            ):

                score += 70

                reasons.append(
                    f"핵심 제목: {pattern}"
                )

            else:

                score += 30

                reasons.append(
                    f"관련 제목: {pattern}"
                )

            break

    # ========================================================
    # 2. 본문 핵심 표현
    # ========================================================

    strong_count = 0

    for pattern in (
        STRONG_TEXT_PATTERNS[
            category
        ]
    ):

        if pattern in text:

            strong_count += 1

    if strong_count:

        bonus = min(
            strong_count * 8,
            32,
        )

        score += bonus

        reasons.append(
            f"핵심 본문 표현 {strong_count}개"
        )

    # ========================================================
    # 3. 용도지역 포함 여부
    # ========================================================

    zones = (
        extract_zone_candidates(
            combined
        )
    )

    if zones:

        zone_bonus = min(
            len(zones) * 3,
            30,
        )

        score += zone_bonus

        reasons.append(
            f"용도지역 {len(zones)}개 포함"
        )

    # ========================================================
    # 4. 퍼센트 숫자 포함 여부
    # ========================================================

    percentages = (
        extract_percentage_candidates(
            text
        )
    )

    if percentages:

        score += 25

        reasons.append(
            f"퍼센트 수치 {len(percentages)}개 포함"
        )

    # ========================================================
    # 5. 국가 / 조례 계층 중요도
    # ========================================================

    if level == 2:

        score += 12

        reasons.append(
            "서울특별시 조례"
        )

    elif level == 4:

        score += 10

        reasons.append(
            "국가 시행령"
        )

    elif level == 3:

        score += 5

        reasons.append(
            "국가 법률"
        )

    # ========================================================
    # 6. 별표
    # ========================================================

    if source_type == "appendix":

        # 별표는 용도별 기준이나 특례가
        # 들어 있을 수 있으므로 무조건 제거하지 않음
        score += 5

        reasons.append(
            "별표/서식"
        )

    # ========================================================
    # 7. 단순 절차/정의 규정 감점
    # ========================================================

    for noise_pattern in (
        NOISE_TITLE_PATTERNS
    ):

        if noise_pattern in title:

            score -= 35

            reasons.append(
                f"절차/참고 규정 가능성: "
                f"{noise_pattern}"
            )

            break

    # ========================================================
    # 8. 카테고리 단어만 1회 등장하고
    #    수치 / 용도지역이 없으면 감점
    # ========================================================

    keyword_count = combined.count(
        category
    )

    if (
        keyword_count <= 1
        and not percentages
        and not zones
    ):

        score -= 20

        reasons.append(
            "단순 키워드 언급 가능성"
        )

    return {
        "score": score,
        "reasons": reasons,
        "zones": zones,
        "percentages": percentages,
        "special_rules": (
            detect_special_rule(
                combined
            )
        ),
    }


# ============================================================
# 등급 판정
# ============================================================

def classify_score(score):

    if score >= 80:
        return "CORE"

    if score >= 40:
        return "REFERENCE"

    return "NOISE"


# ============================================================
# match 정리
# ============================================================

def prepare_candidate(
    match,
    category,
):

    analysis = calculate_score(
        match,
        category,
    )

    candidate = dict(
        match
    )

    candidate[
        "relevance_score"
    ] = analysis[
        "score"
    ]

    candidate[
        "classification"
    ] = classify_score(
        analysis["score"]
    )

    candidate[
        "score_reasons"
    ] = analysis[
        "reasons"
    ]

    candidate[
        "zone_candidates"
    ] = analysis[
        "zones"
    ]

    candidate[
        "percentage_candidates"
    ] = analysis[
        "percentages"
    ]

    candidate[
        "special_rule_candidates"
    ] = analysis[
        "special_rules"
    ]

    return candidate


# ============================================================
# C-3 JSON 읽기
# ============================================================

def load_input():

    if not INPUT_FILE.exists():

        raise FileNotFoundError(
            f"C-3 결과 파일이 없습니다:\n"
            f"{INPUT_FILE}"
        )

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(file)


# ============================================================
# 후보 수집
# ============================================================

def collect_candidates(
    data,
    category,
):

    candidates = []

    laws = data.get(
        "laws",
        []
    )

    for law in laws:

        matches = law.get(
            "matches",
            {}
        )

        category_data = matches.get(
            category,
            {}
        )

        # ----------------------------------------------------
        # 조문
        # ----------------------------------------------------

        for match in category_data.get(
            "articles",
            []
        ):

            candidate = (
                prepare_candidate(
                    match,
                    category,
                )
            )

            candidates.append(
                candidate
            )

        # ----------------------------------------------------
        # 별표
        # ----------------------------------------------------

        for match in category_data.get(
            "appendices",
            []
        ):

            candidate = (
                prepare_candidate(
                    match,
                    category,
                )
            )

            candidates.append(
                candidate
            )

    candidates.sort(
        key=lambda item: (
            item.get(
                "relevance_score",
                0
            )
        ),
        reverse=True,
    )

    return candidates


# ============================================================
# 출력 함수
# ============================================================

def article_label(candidate):

    source_type = candidate.get(
        "source_type"
    )

    if source_type == "article":

        number = candidate.get(
            "article_number",
            ""
        )

        branch = candidate.get(
            "article_branch_number",
            ""
        )

        title = candidate.get(
            "article_title",
            ""
        )

        if branch:

            number_text = (
                f"제{number}조의{branch}"
            )

        else:

            number_text = (
                f"제{number}조"
            )

        return (
            f"{number_text} {title}"
        ).strip()

    number = candidate.get(
        "appendix_number",
        ""
    )

    title = candidate.get(
        "appendix_title",
        ""
    )

    return (
        f"별표 {number} {title}"
    ).strip()


def preview_text(
    text,
    limit=280,
):

    text = normalize_space(
        text
    )

    if len(text) <= limit:
        return text

    return text[:limit] + "..."


# ============================================================
# 카테고리 결과 출력
# ============================================================

def print_category_result(
    category,
    candidates,
):

    print()
    print()
    print("=" * 70)

    print(
        f"[{category}]"
    )

    print("=" * 70)

    core = [
        item
        for item in candidates
        if item[
            "classification"
        ] == "CORE"
    ]

    reference = [
        item
        for item in candidates
        if item[
            "classification"
        ] == "REFERENCE"
    ]

    noise = [
        item
        for item in candidates
        if item[
            "classification"
        ] == "NOISE"
    ]

    print(
        f"전체 후보: "
        f"{len(candidates)}"
    )

    print(
        f"CORE: "
        f"{len(core)}"
    )

    print(
        f"REFERENCE: "
        f"{len(reference)}"
    )

    print(
        f"NOISE: "
        f"{len(noise)}"
    )

    # ========================================================
    # CORE 후보
    # ========================================================

    print()
    print(
        "--- CORE 후보 ---"
    )

    if not core:

        print(
            "CORE 후보 없음"
        )

    for index, candidate in enumerate(
        core[:10],
        start=1,
    ):

        print()
        print("-" * 70)

        print(
            f"CORE {index}"
        )

        print(
            "LEVEL:",
            candidate.get(
                "level"
            )
        )

        print(
            "법규:",
            candidate.get(
                "law_name"
            )
        )

        print(
            "규정:",
            article_label(
                candidate
            )
        )

        print(
            "점수:",
            candidate.get(
                "relevance_score"
            )
        )

        print(
            "근거:",
            ", ".join(
                candidate.get(
                    "score_reasons",
                    []
                )
            )
        )

        zones = candidate.get(
            "zone_candidates",
            []
        )

        if zones:

            print(
                "용도지역 후보:",
                ", ".join(zones)
            )

        percentages = (
            candidate.get(
                "percentage_candidates",
                []
            )
        )

        if percentages:

            values = [
                str(item.get("value"))
                for item
                in percentages[:20]
            ]

            print(
                "수치 후보:",
                ", ".join(values)
            )

        special_rules = (
            candidate.get(
                "special_rule_candidates",
                []
            )
        )

        if special_rules:

            print(
                "특례/예외 표현:",
                ", ".join(
                    special_rules
                )
            )

        print(
            "본문:",
            preview_text(
                candidate.get(
                    "text",
                    ""
                )
            )
        )

    # ========================================================
    # REFERENCE 상위 5개
    # ========================================================

    print()
    print(
        "--- REFERENCE 상위 후보 ---"
    )

    for index, candidate in enumerate(
        reference[:5],
        start=1,
    ):

        print()

        print(
            f"{index}. "
            f"L{candidate.get('level')} | "
            f"{candidate.get('law_name')}"
        )

        print(
            "   ",
            article_label(
                candidate
            )
        )

        print(
            "   점수:",
            candidate.get(
                "relevance_score"
            )
        )


# ============================================================
# 저장 데이터 생성
# ============================================================

def build_output(
    category_results,
):

    output = {
        "categories": {}
    }

    for (
        category,
        candidates
    ) in category_results.items():

        output[
            "categories"
        ][
            category
        ] = {
            "core": [
                item
                for item in candidates
                if item[
                    "classification"
                ] == "CORE"
            ],

            "reference": [
                item
                for item in candidates
                if item[
                    "classification"
                ] == "REFERENCE"
            ],

            "noise": [
                item
                for item in candidates
                if item[
                    "classification"
                ] == "NOISE"
            ],
        }

    return output


# ============================================================
# 특정 용도지역 핵심 후보 별도 확인
# ============================================================

def print_target_zone_summary(
    category_results,
    target_zone,
):

    print()
    print()
    print("=" * 70)

    print(
        "=== 대상 용도지역 관련 후보 ==="
    )

    print("=" * 70)

    print(
        "대상 용도지역:",
        target_zone
    )

    for category in (
        TARGET_CATEGORIES
    ):

        print()
        print(
            f"[{category}]"
        )

        candidates = (
            category_results[
                category
            ]
        )

        zone_matches = []

        for candidate in candidates:

            zones = candidate.get(
                "zone_candidates",
                []
            )

            if (
                target_zone
                in zones
            ):

                zone_matches.append(
                    candidate
                )

        if not zone_matches:

            print(
                "관련 후보 없음"
            )

            continue

        for candidate in (
            zone_matches[:10]
        ):

            print()

            print(
                f"L{candidate.get('level')} "
                f"| "
                f"{candidate.get('classification')} "
                f"| "
                f"{candidate.get('relevance_score')}"
            )

            print(
                candidate.get(
                    "law_name"
                )
            )

            print(
                article_label(
                    candidate
                )
            )

            percentages = (
                candidate.get(
                    "percentage_candidates",
                    []
                )
            )

            if percentages:

                print(
                    "수치 후보:",
                    ", ".join(
                        str(
                            item.get(
                                "value"
                            )
                        )
                        for item
                        in percentages
                    )
                )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-4 "
        "실제 적용 규정 후보 선별 테스트 ==="
    )

    print()
    print(
        "입력 파일:"
    )
    print(
        INPUT_FILE
    )

    # ========================================================
    # 입력
    # ========================================================

    data = load_input()

    category_results = {}

    # ========================================================
    # 건폐율 / 용적률 후보 점수화
    # ========================================================

    for category in (
        TARGET_CATEGORIES
    ):

        candidates = (
            collect_candidates(
                data,
                category,
            )
        )

        category_results[
            category
        ] = candidates

        print_category_result(
            category,
            candidates,
        )

    # ========================================================
    # 현재 테스트 SITE 용도지역
    # ========================================================

    TARGET_ZONE = (
        "제3종일반주거지역"
    )

    print_target_zone_summary(
        category_results,
        TARGET_ZONE,
    )

    # ========================================================
    # 저장
    # ========================================================

    output_data = build_output(
        category_results
    )

    output_data[
        "test_target_zone"
    ] = TARGET_ZONE

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
        "STEP 17-21-C-4 완료"
    )

    print()
    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-5"
    )

    print(
        "→ CORE 후보에서 "
        "용도지역별 건폐율/용적률 "
        "수치를 구조적으로 추출"
    )

    print(
        "→ 상위 시행령 기준과 "
        "서울특별시 조례 기준을 분리"
    )

    print(
        "→ 제3종일반주거지역에 "
        "실제 연결"
    )


if __name__ == "__main__":
    main()