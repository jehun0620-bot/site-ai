import json
import re
from pathlib import Path


# ============================================================
# STEP 17-21-C-6
#
# 특례 / 완화 / 강화 규정 조건 분석 테스트
#
# 목적
# ------------------------------------------------------------
# 1. C-5 결과의 special_candidates 분석
# 2. 각 규정을 조건형 Rule 객체로 변환
# 3. 적용 용도지역 후보 추출
# 4. 적용 조건 키워드 추출
# 5. 효과 유형 분류
# 6. SITE 조건이 아직 없으면 UNKNOWN 처리
# 7. 기본값과 특례값을 분리하여 다음 단계 준비
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_zone_ratio_map.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_special_rule_conditions.json"
)


# ============================================================
# 현재 테스트 SITE
# ============================================================

TARGET_ZONE = "제3종일반주거지역"


# ============================================================
# 용도지역
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
# 적용조건 키워드
# ============================================================

CONDITION_KEYWORDS = {
    "지구단위계획": [
        "지구단위계획",
        "지구단위계획구역",
    ],

    "공공시설제공": [
        "공공시설등의 부지를 제공",
        "공공시설등을 설치하여 제공",
        "공공시설등",
        "공공시설",
    ],

    "기부채납": [
        "기부채납",
        "기부 채납",
    ],

    "임대주택": [
        "임대주택",
        "공공임대주택",
        "민간임대주택",
    ],

    "공공주택": [
        "공공주택",
    ],

    "역세권": [
        "역세권",
    ],

    "공동주택": [
        "공동주택",
    ],

    "주거복합": [
        "주거복합",
        "주거복합건물",
    ],

    "기존공장": [
        "기존 공장",
        "기존공장",
    ],

    "공장": [
        "공장",
    ],

    "녹지지역": [
        "녹지지역",
    ],

    "자연경관지구": [
        "자연경관지구",
    ],

    "방화지구": [
        "방화지구",
    ],

    "방재지구": [
        "방재지구",
    ],

    "도시계획위원회심의": [
        "도시계획위원회의 심의",
        "도시계획위원회 심의",
        "시도시계획위원회의 심의",
    ],

    "건축위원회심의": [
        "건축위원회의 심의",
        "건축위원회 심의",
    ],
}


# ============================================================
# 효과 유형
# ============================================================

EFFECT_PATTERNS = {
    "relaxation": [
        "완화",
        "완화할 수",
        "초과할 수",
        "상향",
    ],

    "restriction": [
        "강화",
        "낮출 수",
        "제한",
        "이하로 낮",
    ],

    "exception": [
        "특례",
        "예외",
        "불구하고",
    ],
}


# ============================================================
# 숫자 표현
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
# 공통
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


def parse_korean_percentage(raw):

    if raw is None:
        return None

    text = normalize_space(raw)

    text = text.replace(",", "")
    text = text.replace(" ", "")
    text = text.replace("퍼센트", "")
    text = text.replace("%", "")

    # --------------------------------------------------------
    # 1천500
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

    try:

        return float(text)

    except ValueError:

        return None


# ============================================================
# 숫자 후보
# ============================================================

def extract_percentage_candidates(text):

    text = normalize_space(text)

    results = []

    pattern = re.compile(
        rf"(?P<percent>{PERCENT_TOKEN})"
        rf"\s*"
        rf"(?P<condition>이상|이하|초과|미만)?"
    )

    for match in pattern.finditer(
        text
    ):

        raw = match.group(
            "percent"
        )

        value = parse_korean_percentage(
            raw
        )

        if value is None:
            continue

        condition_text = match.group(
            "condition"
        )

        condition = None

        if condition_text == "이상":

            condition = "min"

        elif condition_text == "이하":

            condition = "max"

        elif condition_text == "초과":

            condition = "over"

        elif condition_text == "미만":

            condition = "under"

        results.append(
            {
                "raw": raw,
                "value": value,
                "condition": condition,
                "condition_text": condition_text,
            }
        )

    return results


# ============================================================
# 배율 후보
#
# 예:
# 해당 용도지역별 건폐율의 120퍼센트 이하
#
# 이는 "건폐율 120%"가 아니라
# 기존 건폐율 × 1.2 의미이므로 별도 분리
# ============================================================

def extract_multiplier_candidates(text):

    text = normalize_space(text)

    results = []

    patterns = [
        r"건폐율의\s*(" + PERCENT_TOKEN + r")",
        r"용적률의\s*(" + PERCENT_TOKEN + r")",
        r"기준의\s*(" + PERCENT_TOKEN + r")",
    ]

    for pattern_text in patterns:

        pattern = re.compile(
            pattern_text
        )

        for match in pattern.finditer(
            text
        ):

            raw = match.group(1)

            value = (
                parse_korean_percentage(
                    raw
                )
            )

            if value is None:
                continue

            results.append(
                {
                    "raw": raw,
                    "percentage": value,
                    "multiplier": value / 100.0,
                }
            )

    return results


# ============================================================
# 용도지역 후보
# ============================================================

def extract_zones(text):

    found = []

    for zone in ZONE_NAMES:

        if zone in text:

            found.append(
                zone
            )

    return found


# ============================================================
# 조건 추출
# ============================================================

def extract_conditions(text):

    found = []

    for (
        condition_name,
        keywords
    ) in CONDITION_KEYWORDS.items():

        matched_keywords = []

        for keyword in keywords:

            if keyword in text:

                matched_keywords.append(
                    keyword
                )

        if matched_keywords:

            found.append(
                {
                    "condition": (
                        condition_name
                    ),

                    "matched_keywords": (
                        matched_keywords
                    ),
                }
            )

    return found


# ============================================================
# 효과 유형 판정
# ============================================================

def detect_effect_type(
    title,
    text,
):

    combined = (
        normalize_space(title)
        + " "
        + normalize_space(text)
    )

    # --------------------------------------------------------
    # 제목 우선
    # --------------------------------------------------------

    if "완화" in title:

        return "relaxation"

    if "강화" in title:

        return "restriction"

    if "특례" in title:

        return "exception"

    # --------------------------------------------------------
    # 본문
    # --------------------------------------------------------

    scores = {
        "relaxation": 0,
        "restriction": 0,
        "exception": 0,
    }

    for (
        effect_type,
        patterns
    ) in EFFECT_PATTERNS.items():

        for pattern in patterns:

            if pattern in combined:

                scores[
                    effect_type
                ] += 1

    max_score = max(
        scores.values()
    )

    if max_score == 0:

        return "conditional"

    return max(
        scores,
        key=scores.get,
    )


# ============================================================
# 규정 제목
# ============================================================

def get_rule_title(candidate):

    return normalize_space(
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


# ============================================================
# 대상 용도지역 관련 여부
# ============================================================

def determine_zone_relevance(
    zones,
    text,
    target_zone,
):

    # --------------------------------------------------------
    # 직접 명시
    # --------------------------------------------------------

    if target_zone in zones:

        return "DIRECT"

    # --------------------------------------------------------
    # 주거지역 전체를 대상으로 하는 규정
    # --------------------------------------------------------

    if (
        "주거지역" in text
        and
        target_zone.endswith(
            "주거지역"
        )
    ):

        return "GENERAL"

    # --------------------------------------------------------
    # 용도지역 전체
    # --------------------------------------------------------

    if (
        "용도지역별" in text
        or
        "해당 용도지역" in text
    ):

        return "POSSIBLE"

    return "NONE"


# ============================================================
# SITE 조건
#
# 현재는 아직 실제 지구단위계획 등 데이터를
# SITE 모델에 붙이지 않았으므로 UNKNOWN 사용
# ============================================================

SITE_CONDITIONS = {
    "지구단위계획": None,
    "공공시설제공": None,
    "기부채납": None,
    "임대주택": None,
    "공공주택": None,
    "역세권": None,
    "공동주택": None,
    "주거복합": None,
    "기존공장": False,
    "공장": False,
    "녹지지역": False,
    "자연경관지구": None,
    "방화지구": None,
    "방재지구": None,
    "도시계획위원회심의": None,
    "건축위원회심의": None,
}


# ============================================================
# SITE 적용 가능성 판정
# ============================================================

def evaluate_site_match(
    conditions,
    zone_relevance,
):

    # --------------------------------------------------------
    # 대상 용도지역과 무관
    # --------------------------------------------------------

    if zone_relevance == "NONE":

        return {
            "status": "NOT_APPLICABLE",
            "reason": (
                "대상 용도지역과 직접적인 "
                "관련성이 확인되지 않음"
            ),
        }

    # --------------------------------------------------------
    # 조건이 없는 경우
    # --------------------------------------------------------

    if not conditions:

        return {
            "status": "UNKNOWN",
            "reason": (
                "적용조건 자동 추출 결과 없음"
            ),
        }

    unknown_conditions = []
    false_conditions = []
    true_conditions = []

    for condition_item in conditions:

        condition_name = (
            condition_item[
                "condition"
            ]
        )

        site_value = (
            SITE_CONDITIONS.get(
                condition_name
            )
        )

        if site_value is True:

            true_conditions.append(
                condition_name
            )

        elif site_value is False:

            false_conditions.append(
                condition_name
            )

        else:

            unknown_conditions.append(
                condition_name
            )

    # --------------------------------------------------------
    # 명백히 배제되는 조건이 있을 경우
    #
    # 단, 키워드 추출은 OR/AND 법률구조까지 아직
    # 분석하지 않으므로 단순 FALSE 하나만으로
    # 전체 규정을 무조건 배제하면 위험하다.
    #
    # 따라서 POSSIBILITY 상태로 둔다.
    # --------------------------------------------------------

    if (
        false_conditions
        and not unknown_conditions
        and not true_conditions
    ):

        return {
            "status": (
                "LOW_POSSIBILITY"
            ),

            "reason": (
                "현재 SITE 조건과 "
                "일치하지 않는 조건 발견"
            ),

            "false_conditions": (
                false_conditions
            ),
        }

    # --------------------------------------------------------
    # 아직 확인할 조건이 존재
    # --------------------------------------------------------

    if unknown_conditions:

        return {
            "status": "NEEDS_SITE_DATA",

            "reason": (
                "SITE 추가 데이터 필요"
            ),

            "unknown_conditions": (
                unknown_conditions
            ),

            "matched_conditions": (
                true_conditions
            ),

            "false_conditions": (
                false_conditions
            ),
        }

    # --------------------------------------------------------
    # 모두 true
    # --------------------------------------------------------

    if true_conditions:

        return {
            "status": (
                "POTENTIALLY_APPLICABLE"
            ),

            "reason": (
                "현재 SITE 조건과 "
                "규정 조건이 일치"
            ),

            "matched_conditions": (
                true_conditions
            ),
        }

    return {
        "status": "UNKNOWN",
        "reason": (
            "적용 여부 추가 분석 필요"
        ),
    }


# ============================================================
# 특례 후보 하나 정규화
# ============================================================

def normalize_special_rule(
    candidate,
    category,
):

    title = get_rule_title(
        candidate
    )

    text = normalize_space(
        candidate.get(
            "text",
            "",
        )
    )

    zones = extract_zones(
        text
    )

    conditions = (
        extract_conditions(
            text
        )
    )

    percentages = (
        extract_percentage_candidates(
            text
        )
    )

    multipliers = (
        extract_multiplier_candidates(
            text
        )
    )

    effect_type = (
        detect_effect_type(
            title,
            text,
        )
    )

    zone_relevance = (
        determine_zone_relevance(
            zones,
            text,
            TARGET_ZONE,
        )
    )

    site_match = (
        evaluate_site_match(
            conditions,
            zone_relevance,
        )
    )

    return {
        "category": (
            category
        ),

        "rule_name": (
            title
        ),

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

        "source_type": (
            candidate.get(
                "source_type",
                "",
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

        "classification": (
            candidate.get(
                "classification",
                "",
            )
        ),

        "relevance_score": (
            candidate.get(
                "relevance_score"
            )
        ),

        "effect_type": (
            effect_type
        ),

        "zone_candidates": (
            zones
        ),

        "target_zone_relevance": (
            zone_relevance
        ),

        "conditions": (
            conditions
        ),

        "percentage_candidates": (
            percentages
        ),

        "multiplier_candidates": (
            multipliers
        ),

        "site_match": (
            site_match
        ),

        "special_rule_keywords": (
            candidate.get(
                "special_rule_candidates",
                [],
            )
        ),

        "text": (
            text
        ),
    }


# ============================================================
# 규정 우선순위
# ============================================================

def get_rule_priority(rule):

    score = 0

    # --------------------------------------------------------
    # 대상 용도지역 직접 언급
    # --------------------------------------------------------

    relevance = rule.get(
        "target_zone_relevance"
    )

    if relevance == "DIRECT":

        score += 100

    elif relevance == "GENERAL":

        score += 60

    elif relevance == "POSSIBLE":

        score += 30

    # --------------------------------------------------------
    # 서울 조례 우선
    # --------------------------------------------------------

    level = rule.get(
        "level"
    )

    if level == 2:

        score += 30

    elif level == 4:

        score += 20

    elif level == 3:

        score += 10

    # --------------------------------------------------------
    # C-4 점수
    # --------------------------------------------------------

    relevance_score = (
        rule.get(
            "relevance_score"
        )
        or 0
    )

    score += min(
        int(
            relevance_score / 10
        ),
        20,
    )

    return score


# ============================================================
# 결과 출력
# ============================================================

def print_rule(
    index,
    rule,
):

    print()
    print("-" * 70)

    print(
        f"후보 {index}"
    )

    print(
        "카테고리:",
        rule.get(
            "category"
        )
    )

    print(
        "법규:",
        rule.get(
            "law_name"
        )
    )

    print(
        "LEVEL:",
        rule.get(
            "level"
        )
    )

    print(
        "규정:",
        rule.get(
            "rule_name"
        )
    )

    print(
        "효과 유형:",
        rule.get(
            "effect_type"
        )
    )

    print(
        "대상 용도지역 관련성:",
        rule.get(
            "target_zone_relevance"
        )
    )

    zones = rule.get(
        "zone_candidates",
        []
    )

    if zones:

        print(
            "용도지역 후보:",
            ", ".join(zones)
        )

    conditions = (
        rule.get(
            "conditions",
            []
        )
    )

    if conditions:

        print(
            "적용조건:"
        )

        for item in conditions:

            print(
                "  -",
                item.get(
                    "condition"
                ),
                ":",
                ", ".join(
                    item.get(
                        "matched_keywords",
                        []
                    )
                ),
            )

    percentage_candidates = (
        rule.get(
            "percentage_candidates",
            []
        )
    )

    if percentage_candidates:

        print(
            "퍼센트 후보:",
            ", ".join(
                str(
                    item.get(
                        "value"
                    )
                )
                for item
                in percentage_candidates[
                    :20
                ]
            )
        )

    multipliers = rule.get(
        "multiplier_candidates",
        []
    )

    if multipliers:

        print(
            "배율 후보:"
        )

        for item in multipliers:

            print(
                "  -",
                item.get(
                    "percentage"
                ),
                "% →",
                item.get(
                    "multiplier"
                ),
                "배",
            )

    site_match = rule.get(
        "site_match",
        {}
    )

    print(
        "SITE 적용 판정:",
        site_match.get(
            "status"
        )
    )

    print(
        "판정 이유:",
        site_match.get(
            "reason"
        )
    )

    print(
        "우선순위 점수:",
        rule.get(
            "priority_score"
        )
    )

    print(
        "본문:",
        rule.get(
            "text",
            ""
        )[:500]
    )


# ============================================================
# 카테고리 분석
# ============================================================

def process_category(
    data,
    category,
):

    candidates = (
        data
        .get(
            "special_candidates",
            {},
        )
        .get(
            category,
            [],
        )
    )

    rules = []

    for candidate in candidates:

        rule = normalize_special_rule(
            candidate,
            category,
        )

        rule[
            "priority_score"
        ] = get_rule_priority(
            rule
        )

        rules.append(
            rule
        )

    rules.sort(
        key=lambda item: (
            item.get(
                "priority_score",
                0
            )
        ),
        reverse=True,
    )

    return rules


# ============================================================
# 요약
# ============================================================

def summarize_rules(
    rules,
):

    summary = {
        "total": len(rules),
        "DIRECT": 0,
        "GENERAL": 0,
        "POSSIBLE": 0,
        "NONE": 0,
        "NEEDS_SITE_DATA": 0,
        "POTENTIALLY_APPLICABLE": 0,
        "LOW_POSSIBILITY": 0,
        "NOT_APPLICABLE": 0,
        "UNKNOWN": 0,
    }

    for rule in rules:

        relevance = rule.get(
            "target_zone_relevance"
        )

        if relevance in summary:

            summary[
                relevance
            ] += 1

        status = (
            rule
            .get(
                "site_match",
                {}
            )
            .get(
                "status"
            )
        )

        if status in summary:

            summary[
                status
            ] += 1

    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-6 "
        "특례 / 완화 / 강화 규정 조건 분석 테스트 ==="
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
    # C-5 결과 읽기
    # ========================================================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(
            file
        )

    print()
    print(
        "대상 용도지역:",
        TARGET_ZONE
    )

    print()

    # ========================================================
    # 기본값 확인
    # ========================================================

    target_result = data.get(
        "target_result",
        {}
    )

    coverage_base = (
        target_result
        .get(
            "건폐율",
            {}
        )
        .get(
            "selected_value"
        )
    )

    far_base = (
        target_result
        .get(
            "용적률",
            {}
        )
        .get(
            "selected_value"
        )
    )

    print(
        "기본 건폐율:",
        coverage_base,
        "%"
    )

    print(
        "기본 용적률:",
        far_base,
        "%"
    )

    # ========================================================
    # 카테고리 처리
    # ========================================================

    results = {}

    for category in [
        "건폐율",
        "용적률",
    ]:

        print()
        print()
        print("=" * 70)

        print(
            f"[{category}] 특례 후보 조건 분석"
        )

        print("=" * 70)

        rules = process_category(
            data,
            category,
        )

        results[
            category
        ] = rules

        summary = summarize_rules(
            rules
        )

        print(
            "전체 후보:",
            summary[
                "total"
            ]
        )

        print(
            "대상지역 직접 관련:",
            summary[
                "DIRECT"
            ]
        )

        print(
            "일반 관련:",
            summary[
                "GENERAL"
            ]
        )

        print(
            "적용 가능성:",
            summary[
                "POSSIBLE"
            ]
        )

        print(
            "무관:",
            summary[
                "NONE"
            ]
        )

        print(
            "SITE 데이터 필요:",
            summary[
                "NEEDS_SITE_DATA"
            ]
        )

        print()

        print(
            "--- 우선순위 상위 후보 ---"
        )

        # ----------------------------------------------------
        # NONE은 출력 우선순위에서 제외
        # ----------------------------------------------------

        relevant_rules = [
            rule
            for rule in rules
            if rule.get(
                "target_zone_relevance"
            ) != "NONE"
        ]

        for index, rule in enumerate(
            relevant_rules[:10],
            start=1,
        ):

            print_rule(
                index,
                rule,
            )

    # ========================================================
    # 실제 추가로 필요한 SITE 데이터
    # ========================================================

    required_site_conditions = set()

    for rules in results.values():

        for rule in rules:

            if (
                rule.get(
                    "target_zone_relevance"
                )
                == "NONE"
            ):

                continue

            site_match = rule.get(
                "site_match",
                {}
            )

            for condition in (
                site_match.get(
                    "unknown_conditions",
                    []
                )
            ):

                required_site_conditions.add(
                    condition
                )

    print()
    print()
    print("=" * 70)

    print(
        "=== 최종 적용 판정을 위해 "
        "추가 확인이 필요한 SITE 조건 ==="
    )

    print("=" * 70)

    if required_site_conditions:

        for condition in sorted(
            required_site_conditions
        ):

            print(
                "-",
                condition
            )

    else:

        print(
            "추가 SITE 조건 없음"
        )

    # ========================================================
    # 현재 단계 판정
    # ========================================================

    print()
    print()
    print("=" * 70)

    print(
        "=== 현재 SITE 법규 상태 ==="
    )

    print("=" * 70)

    print(
        "용도지역:",
        TARGET_ZONE
    )

    print(
        "기본 건폐율:",
        coverage_base,
        "%"
    )

    print(
        "기본 용적률:",
        far_base,
        "%"
    )

    print()

    print(
        "최종 건폐율: 미확정"
    )

    print(
        "최종 용적률: 미확정"
    )

    print()

    print(
        "사유:"
    )

    print(
        "지구단위계획 / 경관지구 / "
        "공공시설 제공 / 임대주택 등 "
        "SITE별 특례 조건 확인 필요"
    )

    # ========================================================
    # 저장
    # ========================================================

    output_data = {
        "target_zone": (
            TARGET_ZONE
        ),

        "base_values": {
            "building_coverage_ratio": (
                coverage_base
            ),

            "floor_area_ratio": (
                far_base
            ),
        },

        "site_conditions": (
            SITE_CONDITIONS
        ),

        "required_site_conditions": (
            sorted(
                required_site_conditions
            )
        ),

        "rules": (
            results
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
        "STEP 17-21-C-6 완료"
    )

    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-7"
    )

    print(
        "→ SITE / Land 데이터에서 "
        "실제 도시계획 조건 확보"
    )

    print(
        "→ 지구단위계획 / 용도지구 / "
        "용도구역 여부 연결"
    )

    print(
        "→ UNKNOWN 조건을 "
        "True / False로 전환"
    )

    print(
        "→ 최종 적용 규정 판정 준비"
    )


if __name__ == "__main__":
    main()