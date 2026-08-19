import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


# ============================================================
# STEP 17-21-C-9-1A
# SITE 공간조건 판정 프레임 의미 보정
#
# 핵심 원칙
# ------------------------------------------------------------
# 1. 법규명 / 조문명 / 검토필요 문구의 문자열 출현은
#    SITE 공간조건 TRUE 근거가 아니다.
#
# 2. TRUE / FALSE는 반드시
#    - 실제 공간조회 결과
#    - 명시적인 SITE fact
#    에서만 생성한다.
#
# 3. 조회하지 않은 조건은 UNKNOWN 유지
#
# 4. UNKNOWN을 자동 FALSE 처리하지 않는다.
#
# 5. C-8에서 추출된 SITE 조건 10개를 그대로 판정 대상으로 사용
#
# 6. 향후 C-9-2에서 실제 공간조회 source를 연결할 수 있도록
#    source_type / source_name / confidence / evidence 구조를 유지한다.
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_CLAUSES_PATH = (
    BASE_DIR
    / "output"
    / "law_special_rule_clauses.json"
)

INPUT_SITE_PATH = (
    BASE_DIR
    / "output"
    / "site_law_condition_snapshot.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_condition_snapshot.json"
)


# ============================================================
# 기본 조건 정의
# ============================================================

SUPPORTED_SITE_CONDITIONS = {
    "개발밀도관리구역": {
        "positive_keywords": [
            "개발밀도관리구역",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "개발진흥지구": {
        "positive_keywords": [
            "개발진흥지구",
            "산업ㆍ유통개발진흥지구",
            "산업·유통개발진흥지구",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "도시지역편입해제구역": {
        "positive_keywords": [
            "개발제한구역",
            "시가화조정구역",
            "공원에서 해제",
            "녹지지역에서 해제",
            "도시지역으로 편입",
            "새로이 도시지역으로 편입",
        ],
        "query_group": "HISTORY",
    },

    "산업단지": {
        "positive_keywords": [
            "산업단지",
            "국가산업단지",
            "일반산업단지",
            "도시첨단산업단지",
            "준산업단지",
        ],
        "query_group": "THEMATIC_LAYER",
    },

    "수산자원보호구역": {
        "positive_keywords": [
            "수산자원보호구역",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "입체복합구역": {
        "positive_keywords": [
            "입체복합구역",
            "도시ㆍ군계획시설입체복합구역",
            "도시·군계획시설입체복합구역",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "자연경관지구": {
        "positive_keywords": [
            "자연경관지구",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "자연공원": {
        "positive_keywords": [
            "자연공원",
        ],
        "query_group": "THEMATIC_LAYER",
    },

    "지구단위계획": {
        "positive_keywords": [
            "지구단위계획구역",
            "지구단위계획",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },

    "취락지구": {
        "positive_keywords": [
            "취락지구",
        ],
        "query_group": "URBAN_PLANNING_ZONE",
    },
}


# ============================================================
# JSON
# ============================================================

def load_json(
    path: Path,
) -> Any:

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            data,
            f,
            ensure_ascii=False,
            indent=2,
        )


# ============================================================
# 공통 유틸
# ============================================================

def clean_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    text = str(value)

    text = text.replace(
        "\r",
        " ",
    )

    text = text.replace(
        "\n",
        " ",
    )

    return " ".join(
        text.split()
    )


def recursive_find_value(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(
        obj,
        dict,
    ):

        for key in keys:

            if (
                key in obj
                and obj[key]
                not in (
                    None,
                    "",
                )
            ):
                return obj[key]

        for value in obj.values():

            result = recursive_find_value(
                value,
                keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            result = recursive_find_value(
                value,
                keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    return None


# ============================================================
# SITE 기본 정보
# ============================================================

def extract_site_info(
    site_data: Any,
) -> Dict[str, str]:

    site_id = recursive_find_value(
        site_data,
        [
            "site_id",
            "SITE_ID",
            "siteId",
            "필지ID",
        ],
    )

    address = recursive_find_value(
        site_data,
        [
            "address",
            "주소",
            "jibun_address",
            "parcel_address",
        ],
    )

    road_address = recursive_find_value(
        site_data,
        [
            "road_address",
            "도로명주소",
            "roadAddress",
        ],
    )

    zone = recursive_find_value(
        site_data,
        [
            "zone",
            "용도지역",
            "land_use_zone",
            "use_zone",
            "zoning",
        ],
    )

    return {
        "site_id": str(
            site_id
            or ""
        ),
        "address": str(
            address
            or ""
        ),
        "road_address": str(
            road_address
            or ""
        ),
        "zone": str(
            zone
            or ""
        ),
    }


# ============================================================
# C-8 required SITE conditions 읽기
# ============================================================

def extract_required_site_conditions(
    clauses_data: Any,
) -> List[str]:

    if not isinstance(
        clauses_data,
        dict,
    ):
        return []

    required = clauses_data.get(
        "required_conditions",
        {},
    )

    if isinstance(
        required,
        dict,
    ):

        site_conditions = required.get(
            "SITE",
            [],
        )

        if isinstance(
            site_conditions,
            list,
        ):

            return sorted(
                {
                    str(x).strip()
                    for x in site_conditions
                    if str(x).strip()
                }
            )

    return []


# ============================================================
# 판정 객체 생성
# ============================================================

def make_unknown_condition(
    condition_name: str,
    reason: str,
) -> Dict[str, Any]:

    config = SUPPORTED_SITE_CONDITIONS.get(
        condition_name,
        {},
    )

    return {
        "name": condition_name,

        "status": "UNKNOWN",

        "confidence": "NONE",

        "source_type": None,

        "source_name": None,

        "reason": reason,

        "evidence": [],

        "reference_mentions": [],

        "query_group": config.get(
            "query_group",
            "UNKNOWN",
        ),
    }


def make_true_condition(
    condition_name: str,
    source_type: str,
    source_name: str,
    evidence: Optional[List[str]] = None,
    reason: str = "",
    confidence: str = "HIGH",
) -> Dict[str, Any]:

    config = SUPPORTED_SITE_CONDITIONS.get(
        condition_name,
        {},
    )

    return {
        "name": condition_name,

        "status": "TRUE",

        "confidence": confidence,

        "source_type": source_type,

        "source_name": source_name,

        "reason": reason,

        "evidence": evidence or [],

        "reference_mentions": [],

        "query_group": config.get(
            "query_group",
            "UNKNOWN",
        ),
    }


def make_false_condition(
    condition_name: str,
    source_type: str,
    source_name: str,
    evidence: Optional[List[str]] = None,
    reason: str = "",
    confidence: str = "HIGH",
) -> Dict[str, Any]:

    config = SUPPORTED_SITE_CONDITIONS.get(
        condition_name,
        {},
    )

    return {
        "name": condition_name,

        "status": "FALSE",

        "confidence": confidence,

        "source_type": source_type,

        "source_name": source_name,

        "reason": reason,

        "evidence": evidence or [],

        "reference_mentions": [],

        "query_group": config.get(
            "query_group",
            "UNKNOWN",
        ),
    }


# ============================================================
# 문자열 참고 evidence
#
# 중요:
# 문자열 존재는 TRUE/FALSE 판정에 사용하지 않는다.
# 단지 debugging / 향후 source 연결 참고용이다.
# ============================================================

SKIP_EVIDENCE_KEYS = {
    "required_conditions",
    "conditions",
}


def find_keyword_evidence(
    obj: Any,
    keywords: List[str],
    path: str = "",
) -> List[str]:

    evidence: List[str] = []

    if not keywords:
        return evidence

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            child_path = (
                f"{path}.{key}"
                if path
                else str(key)
            )

            if isinstance(
                value,
                (dict, list),
            ):

                evidence.extend(
                    find_keyword_evidence(
                        value,
                        keywords,
                        child_path,
                    )
                )

                continue

            text = clean_text(
                value
            )

            if not text:
                continue

            if any(
                keyword in text
                for keyword in keywords
            ):

                evidence.append(
                    text
                )

    elif isinstance(
        obj,
        list,
    ):

        for index, item in enumerate(
            obj
        ):

            child_path = (
                f"{path}[{index}]"
                if path
                else f"[{index}]"
            )

            evidence.extend(
                find_keyword_evidence(
                    item,
                    keywords,
                    child_path,
                )
            )

    else:

        text = clean_text(
            obj
        )

        if any(
            keyword in text
            for keyword in keywords
        ):
            evidence.append(
                text
            )

    # 중복 제거
    unique: List[str] = []

    seen: Set[str] = set()

    for item in evidence:

        if item in seen:
            continue

        seen.add(
            item
        )

        unique.append(
            item
        )

    return unique


# ============================================================
# 명시적 status 변환
# ============================================================

def normalize_explicit_status(
    value: Any,
) -> Optional[str]:

    if isinstance(
        value,
        bool,
    ):
        return (
            "TRUE"
            if value
            else "FALSE"
        )

    if value is None:
        return None

    if isinstance(
        value,
        int,
    ):

        if value == 1:
            return "TRUE"

        if value == 0:
            return "FALSE"

    text = clean_text(
        value
    ).upper()

    true_values = {
        "TRUE",
        "YES",
        "Y",
        "1",
        "해당",
        "포함",
        "포함됨",
    }

    false_values = {
        "FALSE",
        "NO",
        "N",
        "0",
        "비해당",
        "미포함",
        "포함안됨",
        "포함되지않음",
    }

    unknown_values = {
        "UNKNOWN",
        "NONE",
        "NULL",
        "미확인",
        "확인필요",
        "조회필요",
        "판정필요",
    }

    if text in true_values:
        return "TRUE"

    if text in false_values:
        return "FALSE"

    if text in unknown_values:
        return "UNKNOWN"

    return None


# ============================================================
# 명시적 공간조건 찾기
#
# 허용:
#
# "site_spatial_conditions": {
#     "지구단위계획": true
# }
#
# "spatial_conditions": {
#     "지구단위계획": {
#         "status": "TRUE",
#         "source": "...",
#         "evidence": [...]
#     }
# }
#
# "site_facts": {
#     "자연경관지구": false
# }
#
# 일반 법규 text의 문자열 출현은 절대 판정하지 않는다.
# ============================================================

EXPLICIT_SPATIAL_CONTAINER_KEYS = {
    "spatial_conditions",
    "site_spatial_conditions",
    "site_conditions",
    "site_facts",
    "spatial_facts",
    "resolved_spatial_conditions",
}


def find_explicit_spatial_condition(
    obj: Any,
    condition_name: str,
) -> Optional[Dict[str, Any]]:

    if isinstance(
        obj,
        dict,
    ):

        # ----------------------------------------------------
        # 현재 dict 내부의 명시적 container 검사
        # ----------------------------------------------------

        for container_key in (
            EXPLICIT_SPATIAL_CONTAINER_KEYS
        ):

            container = obj.get(
                container_key
            )

            if not isinstance(
                container,
                dict,
            ):
                continue

            if condition_name not in container:
                continue

            raw_value = container[
                condition_name
            ]

            # ------------------------------------------------
            # 단순 bool / status 문자열
            # ------------------------------------------------

            if not isinstance(
                raw_value,
                dict,
            ):

                status = normalize_explicit_status(
                    raw_value
                )

                if status == "TRUE":

                    return make_true_condition(
                        condition_name=condition_name,
                        source_type="EXPLICIT_SITE_FACT",
                        source_name=container_key,
                        evidence=[
                            (
                                f"{condition_name}"
                                f"={raw_value}"
                            )
                        ],
                        reason=(
                            "SITE snapshot의 "
                            "명시적 공간조건 값"
                        ),
                        confidence="HIGH",
                    )

                if status == "FALSE":

                    return make_false_condition(
                        condition_name=condition_name,
                        source_type="EXPLICIT_SITE_FACT",
                        source_name=container_key,
                        evidence=[
                            (
                                f"{condition_name}"
                                f"={raw_value}"
                            )
                        ],
                        reason=(
                            "SITE snapshot의 "
                            "명시적 공간조건 값"
                        ),
                        confidence="HIGH",
                    )

                if status == "UNKNOWN":

                    result = make_unknown_condition(
                        condition_name,
                        (
                            "SITE snapshot에 "
                            "명시적으로 UNKNOWN으로 저장됨"
                        ),
                    )

                    result[
                        "source_type"
                    ] = "EXPLICIT_SITE_FACT"

                    result[
                        "source_name"
                    ] = container_key

                    return result

                continue

            # ------------------------------------------------
            # dict 형식
            # ------------------------------------------------

            status_value = (
                raw_value.get(
                    "status"
                )
                if "status" in raw_value
                else raw_value.get(
                    "value"
                )
            )

            if status_value is None:

                status_value = raw_value.get(
                    "boolean"
                )

            if status_value is None:

                status_value = raw_value.get(
                    "result"
                )

            status = normalize_explicit_status(
                status_value
            )

            raw_evidence = raw_value.get(
                "evidence",
                [],
            )

            if isinstance(
                raw_evidence,
                list,
            ):

                evidence = [
                    clean_text(x)
                    for x in raw_evidence
                    if clean_text(x)
                ]

            elif raw_evidence not in (
                None,
                "",
            ):

                evidence = [
                    clean_text(
                        raw_evidence
                    )
                ]

            else:

                evidence = []

            source_name = (
                raw_value.get(
                    "source"
                )
                or raw_value.get(
                    "source_name"
                )
                or container_key
            )

            confidence = (
                raw_value.get(
                    "confidence"
                )
                or "HIGH"
            )

            reason = (
                raw_value.get(
                    "reason"
                )
                or (
                    "SITE snapshot의 "
                    "명시적 공간조건 판정"
                )
            )

            if status == "TRUE":

                return make_true_condition(
                    condition_name=condition_name,
                    source_type="EXPLICIT_SITE_FACT",
                    source_name=str(
                        source_name
                    ),
                    evidence=(
                        evidence
                        or [
                            (
                                f"{condition_name}"
                                "=TRUE"
                            )
                        ]
                    ),
                    reason=str(
                        reason
                    ),
                    confidence=str(
                        confidence
                    ),
                )

            if status == "FALSE":

                return make_false_condition(
                    condition_name=condition_name,
                    source_type="EXPLICIT_SITE_FACT",
                    source_name=str(
                        source_name
                    ),
                    evidence=(
                        evidence
                        or [
                            (
                                f"{condition_name}"
                                "=FALSE"
                            )
                        ]
                    ),
                    reason=str(
                        reason
                    ),
                    confidence=str(
                        confidence
                    ),
                )

            if status == "UNKNOWN":

                result = make_unknown_condition(
                    condition_name,
                    str(
                        reason
                    ),
                )

                result[
                    "source_type"
                ] = "EXPLICIT_SITE_FACT"

                result[
                    "source_name"
                ] = str(
                    source_name
                )

                result[
                    "evidence"
                ] = evidence

                return result

        # ----------------------------------------------------
        # 다른 하위 구조 재귀 탐색
        # ----------------------------------------------------

        for value in obj.values():

            if not isinstance(
                value,
                (dict, list),
            ):
                continue

            result = (
                find_explicit_spatial_condition(
                    value,
                    condition_name,
                )
            )

            if result is not None:
                return result

    elif isinstance(
        obj,
        list,
    ):

        for item in obj:

            if not isinstance(
                item,
                (dict, list),
            ):
                continue

            result = (
                find_explicit_spatial_condition(
                    item,
                    condition_name,
                )
            )

            if result is not None:
                return result

    return None


# ============================================================
# 기존 snapshot에서 판정
# ============================================================

def resolve_from_existing_snapshot(
    condition_name: str,
    site_data: Any,
) -> Dict[str, Any]:
    """
    중요:

    site_law_condition_snapshot.json에는
    법규 분석 결과, 조문명, 조회 필요 문구가 포함될 수 있다.

    따라서 해당 조건명이 문자열로 존재한다고 해서
    SITE가 실제 해당 공간구역에 포함된다고 볼 수 없다.

    실제 명시적인 spatial fact가 있을 때만 TRUE/FALSE.
    그 외에는 UNKNOWN.
    """

    explicit_result = (
        find_explicit_spatial_condition(
            site_data,
            condition_name,
        )
    )

    if explicit_result is not None:
        return explicit_result

    config = SUPPORTED_SITE_CONDITIONS.get(
        condition_name,
        {},
    )

    keywords = config.get(
        "positive_keywords",
        [],
    )

    reference_evidence = (
        find_keyword_evidence(
            site_data,
            keywords,
        )
    )

    result = make_unknown_condition(
        condition_name,
        (
            "기존 SITE snapshot에는 실제 필지 공간교차 "
            "판정값이 없음. 법규명ㆍ조문명ㆍ검토 필요 문구의 "
            "문자열 출현은 SITE 해당 여부의 근거로 사용하지 않음"
        ),
    )

    result[
        "reference_mentions"
    ] = reference_evidence[:10]

    return result


# ============================================================
# 전체 판정
# ============================================================

def resolve_site_conditions(
    required_conditions: List[str],
    site_data: Any,
) -> List[Dict[str, Any]]:

    results: List[Dict[str, Any]] = []

    for condition_name in required_conditions:

        result = resolve_from_existing_snapshot(
            condition_name,
            site_data,
        )

        results.append(
            result
        )

    return results


# ============================================================
# 통계
# ============================================================

def summarize_conditions(
    conditions: List[Dict[str, Any]],
) -> Dict[str, int]:

    summary = {
        "total": len(
            conditions
        ),
        "TRUE": 0,
        "FALSE": 0,
        "UNKNOWN": 0,
    }

    for condition in conditions:

        status = condition.get(
            "status"
        )

        if status in {
            "TRUE",
            "FALSE",
            "UNKNOWN",
        }:

            summary[
                status
            ] += 1

    return summary


# ============================================================
# 검증
# ============================================================

def validation_all_required_generated(
    required_conditions: List[str],
    conditions: List[Dict[str, Any]],
) -> bool:

    required_set = set(
        required_conditions
    )

    generated_set = {
        condition.get(
            "name"
        )
        for condition in conditions
        if condition.get(
            "name"
        )
    }

    return (
        required_set
        == generated_set
    )


def validation_status_values(
    conditions: List[Dict[str, Any]],
) -> bool:

    valid = {
        "TRUE",
        "FALSE",
        "UNKNOWN",
    }

    return all(
        condition.get(
            "status"
        )
        in valid
        for condition in conditions
    )


def validation_no_unsupported_false(
    conditions: List[Dict[str, Any]],
) -> bool:
    """
    FALSE에는 반드시 명시적 source와 근거가 있어야 한다.
    """

    for condition in conditions:

        if condition.get(
            "status"
        ) != "FALSE":
            continue

        if not condition.get(
            "source_type"
        ):
            return False

        if not condition.get(
            "source_name"
        ):
            return False

        if not condition.get(
            "reason"
        ):
            return False

    return True


def validation_no_unsupported_true(
    conditions: List[Dict[str, Any]],
) -> bool:
    """
    TRUE에는 반드시 명시적 source가 있어야 한다.
    """

    for condition in conditions:

        if condition.get(
            "status"
        ) != "TRUE":
            continue

        if not condition.get(
            "source_type"
        ):
            return False

        if not condition.get(
            "source_name"
        ):
            return False

        if not condition.get(
            "reason"
        ):
            return False

    return True


def validation_unknown_not_false(
    conditions: List[Dict[str, Any]],
) -> bool:
    """
    현재 실제 공간조회가 없는 조건은
    UNKNOWN이어야 한다.

    문자열 미발견만으로 FALSE 생성되면 실패.
    """

    for condition in conditions:

        if condition.get(
            "status"
        ) != "FALSE":
            continue

        source_type = condition.get(
            "source_type"
        )

        if source_type in {
            None,
            "",
            "KEYWORD_SEARCH",
            "EXISTING_SITE_SNAPSHOT",
        }:
            return False

    return True


def validation_no_keyword_only_true(
    conditions: List[Dict[str, Any]],
) -> bool:
    """
    법규/일반 snapshot 문자열 검색만으로
    TRUE 생성되는 것을 금지한다.
    """

    forbidden_sources = {
        "KEYWORD_SEARCH",
        "EXISTING_SITE_SNAPSHOT",
        "TEXT_MATCH",
        "STRING_MATCH",
    }

    for condition in conditions:

        if condition.get(
            "status"
        ) != "TRUE":
            continue

        if condition.get(
            "source_type"
        ) in forbidden_sources:
            return False

    return True


def validation_reference_mentions_not_decisive(
    conditions: List[Dict[str, Any]],
) -> bool:
    """
    reference_mentions가 존재하더라도
    그 자체만으로 TRUE/FALSE가 되면 안 된다.
    """

    for condition in conditions:

        mentions = condition.get(
            "reference_mentions",
            [],
        )

        if not mentions:
            continue

        if (
            condition.get(
                "status"
            )
            in {
                "TRUE",
                "FALSE",
            }
            and condition.get(
                "source_type"
            )
            in {
                None,
                "",
                "KEYWORD_SEARCH",
                "EXISTING_SITE_SNAPSHOT",
                "TEXT_MATCH",
            }
        ):
            return False

    return True


def run_validations(
    required_conditions: List[str],
    conditions: List[Dict[str, Any]],
) -> Dict[str, bool]:

    return {
        "C-8 SITE 조건 전부 생성":
            validation_all_required_generated(
                required_conditions,
                conditions,
            ),

        "상태값 TRUE/FALSE/UNKNOWN 한정":
            validation_status_values(
                conditions
            ),

        "근거 없는 FALSE 없음":
            validation_no_unsupported_false(
                conditions
            ),

        "근거 없는 TRUE 없음":
            validation_no_unsupported_true(
                conditions
            ),

        "UNKNOWN을 FALSE로 자동 변환하지 않음":
            validation_unknown_not_false(
                conditions
            ),

        "법규 문자열만으로 TRUE 판정 없음":
            validation_no_keyword_only_true(
                conditions
            ),

        "참고 문자열은 판정 근거로 사용하지 않음":
            validation_reference_mentions_not_decisive(
                conditions
            ),
    }


# ============================================================
# 출력
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:

    print(
        char * width
    )


def print_site_condition(
    condition: Dict[str, Any],
) -> None:

    status = condition.get(
        "status",
        "UNKNOWN",
    )

    name = condition.get(
        "name",
        "",
    )

    print(
        f"[{status}] {name}"
    )

    print(
        "  confidence:",
        condition.get(
            "confidence",
            "NONE",
        ),
    )

    source_name = condition.get(
        "source_name"
    )

    print(
        "  source:",
        source_name
        if source_name
        else "-",
    )

    source_type = condition.get(
        "source_type"
    )

    if source_type:
        print(
            "  source_type:",
            source_type,
        )

    query_group = condition.get(
        "query_group"
    )

    if query_group:
        print(
            "  query_group:",
            query_group,
        )

    print(
        "  reason:",
        condition.get(
            "reason",
            "",
        ),
    )

    evidence = condition.get(
        "evidence",
        [],
    )

    if evidence:

        print(
            "  evidence:"
        )

        for item in evidence[:10]:

            print(
                "   -",
                item,
            )

    mentions = condition.get(
        "reference_mentions",
        [],
    )

    if mentions:

        print(
            "  reference mentions "
            "(판정 근거 아님):"
        )

        for item in mentions[:5]:

            text = clean_text(
                item
            )

            if len(
                text
            ) > 180:

                text = (
                    text[:180]
                    + "..."
                )

            print(
                "   -",
                text,
            )

    print()


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-1A "
        "SITE 공간조건 판정 프레임 의미 보정 테스트 ==="
    )
    print()

    print(
        "Clause 입력:"
    )
    print(
        INPUT_CLAUSES_PATH
    )
    print()

    print(
        "SITE 입력:"
    )
    print(
        INPUT_SITE_PATH
    )
    print()

    if not INPUT_CLAUSES_PATH.exists():

        raise FileNotFoundError(
            (
                "Clause 입력 파일이 없습니다: "
                f"{INPUT_CLAUSES_PATH}"
            )
        )

    if not INPUT_SITE_PATH.exists():

        raise FileNotFoundError(
            (
                "SITE 입력 파일이 없습니다: "
                f"{INPUT_SITE_PATH}"
            )
        )

    clauses_data = load_json(
        INPUT_CLAUSES_PATH
    )

    site_data = load_json(
        INPUT_SITE_PATH
    )

    site = extract_site_info(
        site_data
    )

    required_conditions = (
        extract_required_site_conditions(
            clauses_data
        )
    )

    # --------------------------------------------------------
    # 대상 SITE
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 대상 SITE ==="
    )
    print_separator()

    print(
        "SITE ID:",
        site.get(
            "site_id"
        )
        or "-",
    )

    print(
        "주소:",
        site.get(
            "address"
        )
        or "-",
    )

    print(
        "도로명주소:",
        site.get(
            "road_address"
        )
        or "-",
    )

    print(
        "용도지역:",
        site.get(
            "zone"
        )
        or "-",
    )

    print()

    # --------------------------------------------------------
    # required condition
    # --------------------------------------------------------

    print_separator()
    print(
        "=== C-8에서 요구된 SITE 조건 ==="
    )
    print_separator()

    print(
        "조건 수:",
        len(
            required_conditions
        ),
    )

    for condition_name in required_conditions:

        print(
            "-",
            condition_name,
        )

    print()

    # --------------------------------------------------------
    # 판정
    # --------------------------------------------------------

    conditions = resolve_site_conditions(
        required_conditions,
        site_data,
    )

    print_separator()
    print(
        "=== C-9-1A SITE 조건 의미 보정 판정 ==="
    )
    print_separator()

    for condition in conditions:

        print_site_condition(
            condition
        )

    # --------------------------------------------------------
    # 요약
    # --------------------------------------------------------

    summary = summarize_conditions(
        conditions
    )

    print_separator()
    print(
        "=== 판정 요약 ==="
    )
    print_separator()

    print(
        "전체:",
        summary[
            "total"
        ],
    )

    print(
        "TRUE:",
        summary[
            "TRUE"
        ],
    )

    print(
        "FALSE:",
        summary[
            "FALSE"
        ],
    )

    print(
        "UNKNOWN:",
        summary[
            "UNKNOWN"
        ],
    )

    print()

    # --------------------------------------------------------
    # C-9-2 조회그룹
    # --------------------------------------------------------

    query_groups: Dict[
        str,
        List[str],
    ] = {}

    for condition in conditions:

        if condition.get(
            "status"
        ) != "UNKNOWN":
            continue

        group = condition.get(
            "query_group",
            "UNKNOWN",
        )

        query_groups.setdefault(
            group,
            [],
        ).append(
            condition.get(
                "name",
                "",
            )
        )

    print_separator()
    print(
        "=== C-9-2 실제 조회 필요 그룹 ==="
    )
    print_separator()

    group_labels = {
        "URBAN_PLANNING_ZONE":
            "용도지역ㆍ용도지구ㆍ구역 공간조회",

        "THEMATIC_LAYER":
            "별도 주제도 공간조회",

        "HISTORY":
            "공간변경 이력 조회",

        "UNKNOWN":
            "조회원 추가 설계 필요",
    }

    if not query_groups:

        print(
            "- 없음"
        )

    else:

        for group_name in [
            "URBAN_PLANNING_ZONE",
            "THEMATIC_LAYER",
            "HISTORY",
            "UNKNOWN",
        ]:

            items = query_groups.get(
                group_name,
                [],
            )

            if not items:
                continue

            print(
                (
                    f"[{group_name}] "
                    f"{group_labels.get(group_name, '')}"
                )
            )

            for item in sorted(
                items
            ):

                print(
                    f"  - {item}"
                )

    print()

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = run_validations(
        required_conditions,
        conditions,
    )

    print_separator()
    print(
        "=== C-9-1A 검증 ==="
    )
    print_separator()

    for name, passed in validations.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # 결과 JSON
    # --------------------------------------------------------

    output_data = {
        "step": "STEP 17-21-C-9-1A",

        "site": deepcopy(
            site
        ),

        "required_site_conditions":
            required_conditions,

        "summary": {
            "total":
                summary["total"],

            "true":
                summary["TRUE"],

            "false":
                summary["FALSE"],

            "unknown":
                summary["UNKNOWN"],
        },

        "query_groups":
            query_groups,

        "validations":
            validations,

        "all_pass":
            all_pass,

        "conditions":
            conditions,
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print_separator()
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print_separator()

    print()

    # --------------------------------------------------------
    # 종료
    # --------------------------------------------------------

    if all_pass:

        print(
            "STEP 17-21-C-9-1A 완료"
        )

        print()

        print(
            "SITE 공간조건 판정 프레임 의미 검증: ALL PASS"
        )

        print()

        if (
            summary["TRUE"] == 0
            and summary["FALSE"] == 0
            and summary["UNKNOWN"]
            == summary["total"]
        ):

            print(
                "현재 snapshot에는 "
                "실제 공간교차 판정값이 없습니다."
            )

            print(
                "따라서 모든 공간조건을 "
                "안전하게 UNKNOWN으로 유지했습니다."
            )

            print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2"
        )

        print(
            "→ 실제 공간정보 조회 source 연결"
        )

        print(
            "→ 지구단위계획 / 개발진흥지구 / "
            "개발밀도관리구역 등 필지 교차 조회"
        )

        print(
            "→ 산업단지 / 자연공원 별도 주제도 조회"
        )

        print(
            "→ 도시지역편입해제구역은 "
            "현재 상태가 아닌 변경 이력 별도 판정"
        )

        print(
            "→ 조회 완료 항목만 TRUE / FALSE 확정"
        )

    else:

        print(
            "STEP 17-21-C-9-1A 검증 실패"
        )

        print()

        print(
            "FAIL 항목이 남아 있으므로 "
            "C-9-2로 진행하지 않습니다."
        )


if __name__ == "__main__":
    main()