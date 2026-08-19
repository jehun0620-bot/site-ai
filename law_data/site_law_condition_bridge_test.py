import json
from pathlib import Path


# ============================================================
# STEP 17-21-C-7
#
# SITE / PROJECT 법규 적용조건 연결 테스트
#
# 목적
# ------------------------------------------------------------
# 1. C-6 결과 읽기
# 2. 적용조건을 SITE / PROJECT / PROCEDURE로 분류
# 3. 현재 알고 있는 SITE 데이터를 조건값으로 변환
# 4. 용도지역으로 명백히 판정 가능한 조건 자동 처리
# 5. 아직 확보하지 못한 도시계획정보는 UNKNOWN 유지
# 6. 사업계획 조건은 SITE 데이터로 임의 판정하지 않음
# 7. 다음 단계의 실제 특례 적용 판정용 snapshot 생성
# ============================================================


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "law_special_rule_conditions.json"
)

OUTPUT_FILE = (
    BASE_DIR
    / "law_data"
    / "output"
    / "site_law_condition_snapshot.json"
)


# ============================================================
# 현재 테스트 SITE
#
# STEP 16~17에서 확인한 개포동 12번지 SITE 기준
# ============================================================

SITE_DATA = {
    "site_id": "11680-10300-0012-0000",

    "address": (
        "서울특별시 강남구 개포동 12번지"
    ),

    "district": (
        "서울특별시 강남구"
    ),

    "land_area": 121040.4,

    "land_category": "대",

    "zone": "제3종일반주거지역",
}


# ============================================================
# 조건 분류
#
# SITE
#   토지 / 위치 / 도시계획 결정 자체에서 확인
#
# PROJECT
#   앞으로 어떤 건축물 또는 사업을 계획하는지에 따라 결정
#
# PROCEDURE
#   심의 / 허가 등 행정절차 발생 여부
# ============================================================

CONDITION_TYPES = {

    # --------------------------------------------------------
    # SITE CONDITIONS
    # --------------------------------------------------------

    "지구단위계획": "SITE",

    "녹지지역": "SITE",

    "자연경관지구": "SITE",

    "방화지구": "SITE",

    "방재지구": "SITE",

    "기존공장": "SITE",

    "공장": "SITE",

    # --------------------------------------------------------
    # PROJECT CONDITIONS
    # --------------------------------------------------------

    "공공시설제공": "PROJECT",

    "기부채납": "PROJECT",

    "임대주택": "PROJECT",

    "공공주택": "PROJECT",

    "공동주택": "PROJECT",

    "주거복합": "PROJECT",

    "역세권": "PROJECT",

    # --------------------------------------------------------
    # PROCEDURE CONDITIONS
    # --------------------------------------------------------

    "도시계획위원회심의": "PROCEDURE",

    "건축위원회심의": "PROCEDURE",
}


# ============================================================
# 상태값
# ============================================================

TRUE = "TRUE"
FALSE = "FALSE"

UNKNOWN = "UNKNOWN"

PROJECT_REQUIRED = "PROJECT_REQUIRED"

PROCEDURE_REQUIRED = "PROCEDURE_REQUIRED"


# ============================================================
# 용도지역 계열 판정
# ============================================================

def is_residential_zone(zone):

    return (
        zone is not None
        and "주거지역" in zone
    )


def is_green_zone(zone):

    green_zones = {
        "보전녹지지역",
        "생산녹지지역",
        "자연녹지지역",
    }

    return zone in green_zones


def is_commercial_zone(zone):

    commercial_zones = {
        "중심상업지역",
        "일반상업지역",
        "근린상업지역",
        "유통상업지역",
    }

    return zone in commercial_zones


def is_industrial_zone(zone):

    industrial_zones = {
        "전용공업지역",
        "일반공업지역",
        "준공업지역",
    }

    return zone in industrial_zones


# ============================================================
# 현재 SITE만으로 판정 가능한 조건
# ============================================================

def evaluate_known_site_condition(
    condition_name,
    site_data,
):

    zone = site_data.get(
        "zone"
    )

    # --------------------------------------------------------
    # 녹지지역
    # --------------------------------------------------------

    if condition_name == "녹지지역":

        if is_green_zone(zone):

            return {
                "value": TRUE,
                "source": "SITE.zone",
                "reason": (
                    f"용도지역이 {zone}이므로 "
                    "녹지지역에 해당"
                ),
            }

        return {
            "value": FALSE,
            "source": "SITE.zone",
            "reason": (
                f"용도지역이 {zone}이므로 "
                "녹지지역이 아님"
            ),
        }

    # --------------------------------------------------------
    # 기존 공장
    #
    # 현재 SITE 데이터만으로 확정 불가.
    # 용도지역이 주거지역이라는 이유만으로
    # 기존 공장 존재 여부를 False 처리하면 안 됨.
    # --------------------------------------------------------

    if condition_name == "기존공장":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "기존 건축물의 사용승인 / 용도 / "
                "용도지역 변경 시점 데이터 필요"
            ),
        }

    if condition_name == "공장":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "현재 건축물 용도 데이터 또는 "
                "사업계획 데이터 필요"
            ),
        }

    # --------------------------------------------------------
    # 지구단위계획
    # --------------------------------------------------------

    if condition_name == "지구단위계획":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "해당 필지가 지구단위계획구역에 "
                "포함되는지 도시계획 공간정보 확인 필요"
            ),
        }

    # --------------------------------------------------------
    # 각종 용도지구
    # --------------------------------------------------------

    if condition_name == "자연경관지구":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "용도지구 공간정보 확인 필요"
            ),
        }

    if condition_name == "방화지구":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "방화지구 지정 여부 확인 필요"
            ),
        }

    if condition_name == "방재지구":

        return {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "방재지구 지정 여부 확인 필요"
            ),
        }

    return {
        "value": UNKNOWN,
        "source": None,
        "reason": (
            "현재 SITE 데이터만으로 "
            "자동 판정할 수 없음"
        ),
    }


# ============================================================
# PROJECT 조건
# ============================================================

def evaluate_project_condition(
    condition_name,
):

    return {
        "value": PROJECT_REQUIRED,

        "source": None,

        "reason": (
            "토지 고유조건이 아니라 "
            "향후 건축 / 사업계획에 따라 결정되는 조건"
        ),
    }


# ============================================================
# PROCEDURE 조건
# ============================================================

def evaluate_procedure_condition(
    condition_name,
):

    return {
        "value": PROCEDURE_REQUIRED,

        "source": None,

        "reason": (
            "법규 적용결과에 따라 "
            "심의 / 허가 절차 발생 여부를 판정해야 함"
        ),
    }


# ============================================================
# 조건 하나 판정
# ============================================================

def evaluate_condition(
    condition_name,
    site_data,
):

    condition_type = (
        CONDITION_TYPES.get(
            condition_name,
            "UNKNOWN",
        )
    )

    if condition_type == "SITE":

        result = (
            evaluate_known_site_condition(
                condition_name,
                site_data,
            )
        )

    elif condition_type == "PROJECT":

        result = (
            evaluate_project_condition(
                condition_name
            )
        )

    elif condition_type == "PROCEDURE":

        result = (
            evaluate_procedure_condition(
                condition_name
            )
        )

    else:

        result = {
            "value": UNKNOWN,
            "source": None,
            "reason": (
                "조건 유형이 아직 정의되지 않음"
            ),
        }

    result[
        "condition_type"
    ] = condition_type

    return result


# ============================================================
# 규정별 SITE 조건 재판정
# ============================================================

def evaluate_rule_conditions(
    rule,
    condition_snapshot,
):

    conditions = (
        rule.get(
            "conditions",
            []
        )
    )

    evaluations = []

    for condition_item in conditions:

        condition_name = (
            condition_item.get(
                "condition"
            )
        )

        if not condition_name:
            continue

        condition_result = (
            condition_snapshot.get(
                condition_name,
                {}
            )
        )

        evaluations.append(
            {
                "condition": (
                    condition_name
                ),

                "condition_type": (
                    condition_result.get(
                        "condition_type"
                    )
                ),

                "value": (
                    condition_result.get(
                        "value"
                    )
                ),

                "reason": (
                    condition_result.get(
                        "reason"
                    )
                ),
            }
        )

    return evaluations


# ============================================================
# 규정 상태 요약
#
# 주의:
#
# 여기서는 법률 문장의 AND / OR 관계를 아직
# 파싱하지 않았기 때문에 FALSE 조건 하나만 보고
# 규정 전체를 NOT_APPLICABLE 처리하지 않는다.
#
# 예:
# 제51조 하나 안에
# 임대주택 / 지구단위계획 / 녹지지역 등의
# 서로 다른 여러 항ㆍ호가 존재할 수 있음.
#
# 따라서 C-7에서는 "데이터 확보상태"까지만 판정.
# 실제 조항별 적용 여부는 C-8에서 처리.
# ============================================================

def summarize_rule_status(
    evaluations,
):

    if not evaluations:

        return {
            "status": "NO_CONDITION",
            "reason": (
                "추출된 적용조건 없음"
            ),
        }

    values = [
        item.get(
            "value"
        )
        for item in evaluations
    ]

    if (
        UNKNOWN in values
        or PROJECT_REQUIRED in values
        or PROCEDURE_REQUIRED in values
    ):

        return {
            "status": "NEEDS_MORE_DATA",

            "reason": (
                "SITE / PROJECT / PROCEDURE "
                "추가 조건 확인 필요"
            ),
        }

    return {
        "status": "SITE_DATA_READY",

        "reason": (
            "현재 추출된 조건에 대한 "
            "SITE 데이터 확보 완료"
        ),
    }


# ============================================================
# 출력
# ============================================================

def print_condition_snapshot(
    condition_snapshot,
):

    print()
    print("=" * 70)

    print(
        "=== SITE / PROJECT / PROCEDURE 조건 스냅샷 ==="
    )

    print("=" * 70)

    for (
        condition_name,
        info
    ) in condition_snapshot.items():

        print()

        print(
            condition_name
        )

        print(
            "  유형:",
            info.get(
                "condition_type"
            )
        )

        print(
            "  값:",
            info.get(
                "value"
            )
        )

        print(
            "  근거:",
            info.get(
                "reason"
            )
        )


# ============================================================
# 추가 확보 대상
# ============================================================

def build_required_data_list(
    condition_snapshot,
):

    required = {
        "SITE": [],
        "PROJECT": [],
        "PROCEDURE": [],
    }

    for (
        condition_name,
        info
    ) in condition_snapshot.items():

        condition_type = (
            info.get(
                "condition_type"
            )
        )

        value = info.get(
            "value"
        )

        if (
            condition_type == "SITE"
            and value == UNKNOWN
        ):

            required[
                "SITE"
            ].append(
                condition_name
            )

        elif (
            condition_type == "PROJECT"
        ):

            required[
                "PROJECT"
            ].append(
                condition_name
            )

        elif (
            condition_type == "PROCEDURE"
        ):

            required[
                "PROCEDURE"
            ].append(
                condition_name
            )

    return required


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-7 "
        "SITE / PROJECT 법규조건 연결 테스트 ==="
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
    # C-6 결과
    # ========================================================

    with open(
        INPUT_FILE,
        "r",
        encoding="utf-8",
    ) as file:

        law_data = json.load(
            file
        )

    # ========================================================
    # 기본 SITE
    # ========================================================

    print()
    print("=" * 70)

    print(
        "=== 대상 SITE ==="
    )

    print("=" * 70)

    print(
        "SITE ID:",
        SITE_DATA.get(
            "site_id"
        )
    )

    print(
        "주소:",
        SITE_DATA.get(
            "address"
        )
    )

    print(
        "용도지역:",
        SITE_DATA.get(
            "zone"
        )
    )

    print(
        "대지면적:",
        SITE_DATA.get(
            "land_area"
        ),
        "㎡"
    )

    print(
        "지목:",
        SITE_DATA.get(
            "land_category"
        )
    )

    # ========================================================
    # C-6에서 실제 요구된 조건 가져오기
    # ========================================================

    requested_conditions = (
        law_data.get(
            "required_site_conditions",
            []
        )
    )

    # --------------------------------------------------------
    # required_site_conditions는 C-6 명칭상 SITE지만
    # 실제로 PROJECT / PROCEDURE 조건도 포함되어 있으므로
    # 여기서 다시 분리한다.
    # --------------------------------------------------------

    condition_snapshot = {}

    for condition_name in requested_conditions:

        condition_snapshot[
            condition_name
        ] = evaluate_condition(
            condition_name,
            SITE_DATA,
        )

    # ========================================================
    # 출력
    # ========================================================

    print_condition_snapshot(
        condition_snapshot
    )

    # ========================================================
    # 필요한 추가 데이터
    # ========================================================

    required_data = (
        build_required_data_list(
            condition_snapshot
        )
    )

    print()
    print()
    print("=" * 70)

    print(
        "=== 추가 확보가 필요한 SITE 데이터 ==="
    )

    print("=" * 70)

    if required_data["SITE"]:

        for item in required_data[
            "SITE"
        ]:

            print(
                "-",
                item
            )

    else:

        print(
            "없음"
        )

    print()
    print("=" * 70)

    print(
        "=== 향후 PROJECT 입력으로 결정할 조건 ==="
    )

    print("=" * 70)

    if required_data["PROJECT"]:

        for item in required_data[
            "PROJECT"
        ]:

            print(
                "-",
                item
            )

    else:

        print(
            "없음"
        )

    print()
    print("=" * 70)

    print(
        "=== 법규 판정 후 PROCEDURE에서 결정할 조건 ==="
    )

    print("=" * 70)

    if required_data[
        "PROCEDURE"
    ]:

        for item in required_data[
            "PROCEDURE"
        ]:

            print(
                "-",
                item
            )

    else:

        print(
            "없음"
        )

    # ========================================================
    # 규정별 데이터 준비상태
    # ========================================================

    rule_results = {}

    rules_by_category = (
        law_data.get(
            "rules",
            {}
        )
    )

    for (
        category,
        rules
    ) in rules_by_category.items():

        normalized_rules = []

        for rule in rules:

            evaluations = (
                evaluate_rule_conditions(
                    rule,
                    condition_snapshot,
                )
            )

            status = (
                summarize_rule_status(
                    evaluations
                )
            )

            normalized_rule = {
                "category": category,

                "law_name": (
                    rule.get(
                        "law_name"
                    )
                ),

                "level": (
                    rule.get(
                        "level"
                    )
                ),

                "rule_name": (
                    rule.get(
                        "rule_name"
                    )
                ),

                "effect_type": (
                    rule.get(
                        "effect_type"
                    )
                ),

                "target_zone_relevance": (
                    rule.get(
                        "target_zone_relevance"
                    )
                ),

                "condition_evaluations": (
                    evaluations
                ),

                "data_status": (
                    status
                ),
            }

            normalized_rules.append(
                normalized_rule
            )

        rule_results[
            category
        ] = normalized_rules

    # ========================================================
    # 현재 기본 법규값
    # ========================================================

    base_values = (
        law_data.get(
            "base_values",
            {}
        )
    )

    print()
    print()
    print("=" * 70)

    print(
        "=== 현재 SITE 기본 법규값 ==="
    )

    print("=" * 70)

    print(
        "용도지역:",
        SITE_DATA.get(
            "zone"
        )
    )

    print(
        "기본 건폐율:",
        base_values.get(
            "building_coverage_ratio"
        ),
        "%"
    )

    print(
        "기본 용적률:",
        base_values.get(
            "floor_area_ratio"
        ),
        "%"
    )

    print()

    print(
        "최종 건폐율: 미확정"
    )

    print(
        "최종 용적률: 미확정"
    )

    # ========================================================
    # 저장
    # ========================================================

    output = {
        "site": SITE_DATA,

        "base_values": (
            base_values
        ),

        "condition_snapshot": (
            condition_snapshot
        ),

        "required_data": (
            required_data
        ),

        "rule_data_status": (
            rule_results
        ),
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            output,
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
        "STEP 17-21-C-7 완료"
    )

    print()

    print(
        "다음 단계:"
    )

    print(
        "STEP 17-21-C-8"
    )

    print(
        "→ 실제 SITE 도시계획 공간정보 연결"
    )

    print(
        "→ 지구단위계획 / 용도지구 / "
        "용도구역 지정 여부 자동 확인"
    )

    print(
        "→ 법규 조문을 항ㆍ호 단위로 분해"
    )

    print(
        "→ 한 조문 안에 섞여 있는 "
        "서로 다른 특례조건 분리"
    )

    print(
        "→ SITE별 실제 적용 가능한 "
        "특례 규정만 남기기"
    )


if __name__ == "__main__":
    main()