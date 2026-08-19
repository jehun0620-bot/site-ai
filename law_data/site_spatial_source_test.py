import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional


# ============================================================
# STEP 17-21-C-9-2-1
# SITE 공간조건 Source Registry / 조회 결과 Schema 구축
#
# 목적
# ------------------------------------------------------------
# 1. C-9-1A에서 생성된 10개 SITE 공간조건을 입력으로 사용
# 2. 각 공간조건별 실제 조회 source registry 정의
# 3. 아직 연결되지 않은 source는 NOT_CONNECTED 유지
# 4. NOT_CONNECTED를 FALSE로 절대 변환하지 않음
# 5. 추후 실제 API / 공간데이터 연결을 위한 공통 결과 schema 생성
# 6. HISTORY 조건은 현재 공간상태 조건과 분리
#
# 중요
# ------------------------------------------------------------
# NOT_CONNECTED:
#   조회 source 자체가 아직 코드에 연결되지 않음
#
# NOT_QUERIED:
#   source는 연결되어 있으나 이번 실행에서는 조회하지 않음
#
# QUERY_SUCCESS:
#   실제 조회가 성공함
#
# QUERY_FAILED:
#   실제 조회를 시도했으나 실패함
#
# resolved_status:
#   TRUE / FALSE / UNKNOWN 중 하나
#
# API 미연결/조회 실패 상태는 반드시 UNKNOWN
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_SPATIAL_SNAPSHOT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_condition_snapshot.json"
)

INPUT_SITE_PATH = (
    BASE_DIR
    / "output"
    / "site_law_condition_snapshot.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_source_snapshot.json"
)


# ============================================================
# 허용 상태값
# ============================================================

QUERY_STATUSES = {
    "NOT_CONNECTED",
    "NOT_QUERIED",
    "QUERY_SUCCESS",
    "QUERY_FAILED",
}

RESOLVED_STATUSES = {
    "TRUE",
    "FALSE",
    "UNKNOWN",
}

CONFIDENCE_VALUES = {
    "HIGH",
    "MEDIUM",
    "LOW",
    "NONE",
}


# ============================================================
# 공간조건 Source Registry
# ============================================================
#
# source_candidates:
#   앞으로 실제 데이터 연결 시 검토해야 할 source 종류
#
# preferred_method:
#   이상적인 조회 방식
#
# query_key:
#   내부 프로그램에서 사용할 고정 식별자
#
# 현재 단계에서는 실제 endpoint를 넣지 않는다.
# API URL/서비스키 연결은 C-9-2-2부터 진행한다.
# ============================================================

SPATIAL_SOURCE_REGISTRY: Dict[str, Dict[str, Any]] = {

    # --------------------------------------------------------
    # URBAN_PLANNING_ZONE
    # --------------------------------------------------------

    "지구단위계획": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "district_unit_plan",
        "description": (
            "대상 필지가 지구단위계획구역에 포함되는지 판정"
        ),
        "source_candidates": [
            "국가공간정보/토지이용계획 공간정보",
            "서울시 도시계획 공간정보",
            "지자체 도시관리계획 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 1,
        "connection_status": "NOT_CONNECTED",
    },

    "개발진흥지구": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "development_promotion_district",
        "description": (
            "대상 필지가 개발진흥지구에 포함되는지 판정"
        ),
        "source_candidates": [
            "국가공간정보 용도지구 공간정보",
            "서울시 도시계획 용도지구 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 2,
        "connection_status": "NOT_CONNECTED",
    },

    "개발밀도관리구역": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "development_density_control_area",
        "description": (
            "대상 필지가 개발밀도관리구역에 포함되는지 판정"
        ),
        "source_candidates": [
            "도시관리계획 구역 공간정보",
            "지자체 도시계획 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 3,
        "connection_status": "NOT_CONNECTED",
    },

    "자연경관지구": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "natural_landscape_district",
        "description": (
            "대상 필지가 자연경관지구에 포함되는지 판정"
        ),
        "source_candidates": [
            "국가공간정보 용도지구 공간정보",
            "서울시 도시계획 용도지구 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 4,
        "connection_status": "NOT_CONNECTED",
    },

    "입체복합구역": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "three_dimensional_complex_zone",
        "description": (
            "대상 필지가 도시ㆍ군계획시설입체복합구역에 "
            "포함되는지 판정"
        ),
        "source_candidates": [
            "도시ㆍ군관리계획 공간정보",
            "지자체 도시계획 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 5,
        "connection_status": "NOT_CONNECTED",
    },

    "수산자원보호구역": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "fishery_resource_protection_zone",
        "description": (
            "대상 필지가 수산자원보호구역에 포함되는지 판정"
        ),
        "source_candidates": [
            "국토계획 용도구역 공간정보",
            "해양ㆍ수산 관련 공간정보",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 6,
        "connection_status": "NOT_CONNECTED",
    },

    "취락지구": {
        "query_group": "URBAN_PLANNING_ZONE",
        "query_key": "settlement_district",
        "description": (
            "대상 필지가 취락지구에 포함되는지 판정"
        ),
        "source_candidates": [
            "국가공간정보 용도지구 공간정보",
            "지자체 도시계획 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 7,
        "connection_status": "NOT_CONNECTED",
    },

    # --------------------------------------------------------
    # THEMATIC_LAYER
    # --------------------------------------------------------

    "산업단지": {
        "query_group": "THEMATIC_LAYER",
        "query_key": "industrial_complex",
        "description": (
            "대상 필지가 산업단지 경계 안에 포함되는지 판정"
        ),
        "source_candidates": [
            "산업입지 공간정보",
            "산업단지 경계 GIS",
            "국가공간정보 산업단지 주제도",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 8,
        "connection_status": "NOT_CONNECTED",
    },

    "자연공원": {
        "query_group": "THEMATIC_LAYER",
        "query_key": "natural_park",
        "description": (
            "대상 필지가 자연공원 구역에 포함되는지 판정"
        ),
        "source_candidates": [
            "자연공원 공간정보",
            "국립공원/도립공원/군립공원 경계 GIS",
        ],
        "preferred_method": "PARCEL_POLYGON_INTERSECTION",
        "priority": 9,
        "connection_status": "NOT_CONNECTED",
    },

    # --------------------------------------------------------
    # HISTORY
    # --------------------------------------------------------

    "도시지역편입해제구역": {
        "query_group": "HISTORY",
        "query_key": "urban_area_conversion_history",
        "description": (
            "개발제한구역ㆍ시가화조정구역ㆍ녹지지역ㆍ공원 해제 "
            "또는 도시지역 신규 편입 이력 판정"
        ),
        "source_candidates": [
            "도시관리계획 결정ㆍ변경 이력",
            "용도지역ㆍ구역 변경 이력",
            "도시계획 고시 이력",
        ],
        "preferred_method": "PARCEL_HISTORY_LOOKUP",
        "priority": 10,
        "connection_status": "NOT_CONNECTED",
    },
}


# ============================================================
# JSON
# ============================================================

def load_json(path: Path) -> Any:
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
# 공통 탐색
# ============================================================

def recursive_find_value(
    obj: Any,
    target_keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in target_keys:
            if (
                key in obj
                and obj[key] not in (
                    None,
                    "",
                )
            ):
                return obj[key]

        for value in obj.values():
            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    elif isinstance(obj, list):

        for value in obj:
            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in (
                None,
                "",
            ):
                return result

    return None


# ============================================================
# SITE 정보
# ============================================================

def extract_site_info(
    site_data: Any,
) -> Dict[str, str]:

    return {

        "site_id": str(
            recursive_find_value(
                site_data,
                [
                    "site_id",
                    "SITE ID",
                    "id",
                ],
            )
            or ""
        ),

        "address": str(
            recursive_find_value(
                site_data,
                [
                    "address",
                    "주소",
                    "jibun_address",
                    "parcel_address",
                ],
            )
            or ""
        ),

        "road_address": str(
            recursive_find_value(
                site_data,
                [
                    "road_address",
                    "도로명주소",
                    "roadAddress",
                ],
            )
            or ""
        ),

        "sigungu_code": str(
            recursive_find_value(
                site_data,
                [
                    "sigungu_code",
                    "시군구코드",
                    "sigunguCd",
                ],
            )
            or ""
        ),

        "bjdong_code": str(
            recursive_find_value(
                site_data,
                [
                    "bjdong_code",
                    "법정동코드",
                    "bjdongCd",
                ],
            )
            or ""
        ),

        "main_no": str(
            recursive_find_value(
                site_data,
                [
                    "main_no",
                    "본번",
                    "bun",
                ],
            )
            or ""
        ),

        "sub_no": str(
            recursive_find_value(
                site_data,
                [
                    "sub_no",
                    "부번",
                    "ji",
                ],
            )
            or ""
        ),

        "zone": str(
            recursive_find_value(
                site_data,
                [
                    "zone",
                    "용도지역",
                    "land_use_zone",
                    "use_zone",
                    "zoning",
                ],
            )
            or ""
        ),
    }


# ============================================================
# C-9-1A 결과에서 조건 읽기
# ============================================================

def extract_existing_conditions(
    spatial_snapshot: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    C-9-1A 출력 구조가 조금 달라도
    조건 객체들을 최대한 유연하게 추출한다.
    """

    candidates: List[Dict[str, Any]] = []

    possible_keys = [
        "conditions",
        "spatial_conditions",
        "site_conditions",
        "results",
    ]

    for key in possible_keys:
        value = spatial_snapshot.get(key)

        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    candidates.append(
                        deepcopy(item)
                    )

    if candidates:
        return candidates

    # dict 형태 지원
    for key in possible_keys:
        value = spatial_snapshot.get(key)

        if not isinstance(value, dict):
            continue

        for name, item in value.items():

            if isinstance(item, dict):
                copied = deepcopy(item)

                if not copied.get("name"):
                    copied["name"] = name

                candidates.append(
                    copied
                )

    if candidates:
        return candidates

    # required_conditions 내부 대응
    required = spatial_snapshot.get(
        "required_conditions"
    )

    if isinstance(required, dict):

        site_items = required.get(
            "SITE"
        )

        if isinstance(
            site_items,
            list,
        ):
            for name in site_items:
                candidates.append(
                    {
                        "name": str(name),
                        "status": "UNKNOWN",
                    }
                )

    return candidates


def extract_condition_name(
    item: Dict[str, Any],
) -> str:

    for key in [
        "name",
        "condition",
        "condition_name",
        "조건",
    ]:
        value = item.get(key)

        if value:
            return str(value)

    return ""


# ============================================================
# Query context
# ============================================================

def build_query_context(
    site: Dict[str, str],
) -> Dict[str, Any]:
    """
    추후 실제 공간 API가 공통적으로 사용할
    필지 식별정보 구조.
    """

    pnu_like = ""

    if (
        site.get("sigungu_code")
        and site.get("bjdong_code")
        and site.get("main_no")
    ):
        pnu_like = (
            f"{site.get('sigungu_code')}"
            f"-{site.get('bjdong_code')}"
            f"-{site.get('main_no')}"
            f"-{site.get('sub_no') or '0000'}"
        )

    return {
        "site_id": site.get(
            "site_id",
            "",
        ),
        "address": site.get(
            "address",
            "",
        ),
        "road_address": site.get(
            "road_address",
            "",
        ),
        "sigungu_code": site.get(
            "sigungu_code",
            "",
        ),
        "bjdong_code": site.get(
            "bjdong_code",
            "",
        ),
        "main_no": site.get(
            "main_no",
            "",
        ),
        "sub_no": site.get(
            "sub_no",
            "",
        ),
        "parcel_key": pnu_like,
    }


# ============================================================
# 기본 source 결과
# ============================================================

def build_not_connected_result(
    condition_name: str,
    registry: Dict[str, Any],
    query_context: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "condition": condition_name,

        "query_group": registry.get(
            "query_group",
        ),

        "query_key": registry.get(
            "query_key",
        ),

        "priority": registry.get(
            "priority",
        ),

        "description": registry.get(
            "description",
            "",
        ),

        "source": {
            "source_name": None,
            "source_type": None,
            "endpoint": None,
            "dataset": None,
            "connected": False,
            "candidates": deepcopy(
                registry.get(
                    "source_candidates",
                    [],
                )
            ),
        },

        "query": {
            "method": registry.get(
                "preferred_method",
            ),
            "status": "NOT_CONNECTED",
            "context": deepcopy(
                query_context
            ),
            "request": None,
            "response": None,
            "error": None,
        },

        "resolution": {
            "status": "UNKNOWN",
            "confidence": "NONE",
            "reason": (
                "실제 공간정보 조회 source가 아직 연결되지 않았으므로 "
                "TRUE 또는 FALSE로 판정하지 않음"
            ),
            "evidence": [],
        },
    }


# ============================================================
# Registry 처리
# ============================================================

def build_source_results(
    conditions: List[Dict[str, Any]],
    site: Dict[str, str],
) -> List[Dict[str, Any]]:

    query_context = build_query_context(
        site
    )

    results = []

    seen = set()

    for condition in conditions:

        name = extract_condition_name(
            condition
        )

        if not name:
            continue

        if name in seen:
            continue

        seen.add(name)

        registry = SPATIAL_SOURCE_REGISTRY.get(
            name
        )

        # C-8/C-9에서 새 조건이 추가되었지만
        # source registry가 아직 없는 경우도 안전하게 처리
        if registry is None:

            results.append(
                {
                    "condition": name,

                    "query_group": "UNREGISTERED",

                    "query_key": None,

                    "priority": 999,

                    "description": (
                        "Source registry에 등록되지 않은 공간조건"
                    ),

                    "source": {
                        "source_name": None,
                        "source_type": None,
                        "endpoint": None,
                        "dataset": None,
                        "connected": False,
                        "candidates": [],
                    },

                    "query": {
                        "method": None,
                        "status": "NOT_CONNECTED",
                        "context": deepcopy(
                            query_context
                        ),
                        "request": None,
                        "response": None,
                        "error": None,
                    },

                    "resolution": {
                        "status": "UNKNOWN",
                        "confidence": "NONE",
                        "reason": (
                            "Source registry에 등록되지 않아 "
                            "공간조회 방법을 결정할 수 없음"
                        ),
                        "evidence": [],
                    },
                }
            )

            continue

        results.append(
            build_not_connected_result(
                condition_name=name,
                registry=registry,
                query_context=query_context,
            )
        )

    results.sort(
        key=lambda x: (
            x.get(
                "priority",
                999,
            ),
            x.get(
                "condition",
                "",
            ),
        )
    )

    return results


# ============================================================
# 검증
# ============================================================

def validation_all_conditions_registered(
    results: List[Dict[str, Any]],
) -> bool:

    return all(
        result.get(
            "query_group"
        )
        != "UNREGISTERED"
        for result in results
    )


def validation_query_status_values(
    results: List[Dict[str, Any]],
) -> bool:

    for result in results:

        status = (
            result
            .get(
                "query",
                {},
            )
            .get(
                "status"
            )
        )

        if status not in QUERY_STATUSES:
            return False

    return True


def validation_resolution_status_values(
    results: List[Dict[str, Any]],
) -> bool:

    for result in results:

        status = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "status"
            )
        )

        if status not in RESOLVED_STATUSES:
            return False

    return True


def validation_confidence_values(
    results: List[Dict[str, Any]],
) -> bool:

    for result in results:

        confidence = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "confidence"
            )
        )

        if confidence not in CONFIDENCE_VALUES:
            return False

    return True


def validation_not_connected_unknown(
    results: List[Dict[str, Any]],
) -> bool:
    """
    NOT_CONNECTED는 반드시 UNKNOWN.
    """

    for result in results:

        query_status = (
            result
            .get(
                "query",
                {},
            )
            .get(
                "status"
            )
        )

        resolved_status = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "status"
            )
        )

        if (
            query_status
            == "NOT_CONNECTED"
            and resolved_status
            != "UNKNOWN"
        ):
            return False

    return True


def validation_no_false_without_query(
    results: List[Dict[str, Any]],
) -> bool:
    """
    QUERY_SUCCESS가 아닌데 FALSE이면 오류.
    """

    for result in results:

        query_status = (
            result
            .get(
                "query",
                {},
            )
            .get(
                "status"
            )
        )

        resolved_status = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "status"
            )
        )

        if (
            resolved_status == "FALSE"
            and query_status
            != "QUERY_SUCCESS"
        ):
            return False

    return True


def validation_no_true_without_query(
    results: List[Dict[str, Any]],
) -> bool:
    """
    QUERY_SUCCESS가 아닌데 TRUE이면 오류.
    """

    for result in results:

        query_status = (
            result
            .get(
                "query",
                {},
            )
            .get(
                "status"
            )
        )

        resolved_status = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "status"
            )
        )

        if (
            resolved_status == "TRUE"
            and query_status
            != "QUERY_SUCCESS"
        ):
            return False

    return True


def validation_history_separated(
    results: List[Dict[str, Any]],
) -> bool:

    history_items = [
        result
        for result in results
        if result.get(
            "condition"
        )
        == "도시지역편입해제구역"
    ]

    if not history_items:
        return False

    return all(
        item.get(
            "query_group"
        )
        == "HISTORY"
        and (
            item
            .get(
                "query",
                {},
            )
            .get(
                "method"
            )
            == "PARCEL_HISTORY_LOOKUP"
        )
        for item in history_items
    )


def validation_expected_count(
    results: List[Dict[str, Any]],
) -> bool:
    """
    현재 C-8 최종 요구조건은 10개.
    """

    return len(
        results
    ) == 10


def run_validations(
    results: List[Dict[str, Any]],
) -> Dict[str, bool]:

    return {
        "C-9-1A 공간조건 10개 유지":
            validation_expected_count(
                results
            ),

        "모든 조건 Source Registry 등록":
            validation_all_conditions_registered(
                results
            ),

        "query status 허용값 준수":
            validation_query_status_values(
                results
            ),

        "resolution status TRUE/FALSE/UNKNOWN 한정":
            validation_resolution_status_values(
                results
            ),

        "confidence 허용값 준수":
            validation_confidence_values(
                results
            ),

        "NOT_CONNECTED는 UNKNOWN 유지":
            validation_not_connected_unknown(
                results
            ),

        "실제 조회 없이 FALSE 판정 없음":
            validation_no_false_without_query(
                results
            ),

        "실제 조회 없이 TRUE 판정 없음":
            validation_no_true_without_query(
                results
            ),

        "HISTORY 조건 별도 조회 구조":
            validation_history_separated(
                results
            ),
    }


# ============================================================
# 로그
# ============================================================

def print_separator(
    char: str = "=",
    width: int = 70,
) -> None:

    print(
        char * width
    )


def print_site(
    site: Dict[str, str],
) -> None:

    print_separator()
    print(
        "=== 대상 SITE ==="
    )
    print_separator()

    print(
        "SITE ID:",
        site.get(
            "site_id",
            "",
        )
        or "-",
    )

    print(
        "주소:",
        site.get(
            "address",
            "",
        )
        or "-",
    )

    print(
        "도로명주소:",
        site.get(
            "road_address",
            "",
        )
        or "-",
    )

    print(
        "시군구코드:",
        site.get(
            "sigungu_code",
            "",
        )
        or "-",
    )

    print(
        "법정동코드:",
        site.get(
            "bjdong_code",
            "",
        )
        or "-",
    )

    print(
        "본번:",
        site.get(
            "main_no",
            "",
        )
        or "-",
    )

    print(
        "부번:",
        site.get(
            "sub_no",
            "",
        )
        or "-",
    )

    print(
        "용도지역:",
        site.get(
            "zone",
            "",
        )
        or "-",
    )

    print()


def print_source_result(
    result: Dict[str, Any],
) -> None:

    condition = result.get(
        "condition"
    )

    query_group = result.get(
        "query_group"
    )

    query_key = result.get(
        "query_key"
    )

    priority = result.get(
        "priority"
    )

    source = result.get(
        "source",
        {},
    )

    query = result.get(
        "query",
        {},
    )

    resolution = result.get(
        "resolution",
        {},
    )

    print(
        f"[{resolution.get('status')}] "
        f"{condition}"
    )

    print(
        "  group:",
        query_group,
    )

    print(
        "  query_key:",
        query_key,
    )

    print(
        "  priority:",
        priority,
    )

    print(
        "  method:",
        query.get(
            "method"
        ),
    )

    print(
        "  query_status:",
        query.get(
            "status"
        ),
    )

    print(
        "  connected:",
        source.get(
            "connected"
        ),
    )

    print(
        "  confidence:",
        resolution.get(
            "confidence"
        ),
    )

    print(
        "  reason:",
        resolution.get(
            "reason"
        ),
    )

    candidates = source.get(
        "candidates",
        [],
    )

    if candidates:

        print(
            "  source candidates:"
        )

        for candidate in candidates:
            print(
                f"   - {candidate}"
            )

    print()


# ============================================================
# 요약
# ============================================================

def build_summary(
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:

    query_status_counts = {
        status: 0
        for status in sorted(
            QUERY_STATUSES
        )
    }

    resolution_counts = {
        status: 0
        for status in sorted(
            RESOLVED_STATUSES
        )
    }

    group_counts: Dict[str, int] = {}

    for result in results:

        query_status = (
            result
            .get(
                "query",
                {},
            )
            .get(
                "status"
            )
        )

        if query_status in query_status_counts:
            query_status_counts[
                query_status
            ] += 1

        resolved_status = (
            result
            .get(
                "resolution",
                {},
            )
            .get(
                "status"
            )
        )

        if resolved_status in resolution_counts:
            resolution_counts[
                resolved_status
            ] += 1

        group = result.get(
            "query_group",
            "UNKNOWN",
        )

        group_counts[group] = (
            group_counts.get(
                group,
                0,
            )
            + 1
        )

    return {
        "total": len(
            results
        ),
        "query_status": query_status_counts,
        "resolution_status": resolution_counts,
        "query_groups": group_counts,
    }


# ============================================================
# Main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-1 "
        "공간조회 Source Registry / 결과 Schema 테스트 ==="
    )

    print()

    print(
        "공간조건 입력:"
    )

    print(
        INPUT_SPATIAL_SNAPSHOT_PATH
    )

    print()

    print(
        "SITE 입력:"
    )

    print(
        INPUT_SITE_PATH
    )

    print()

    if not INPUT_SPATIAL_SNAPSHOT_PATH.exists():
        raise FileNotFoundError(
            "C-9-1A 공간조건 파일이 없습니다: "
            f"{INPUT_SPATIAL_SNAPSHOT_PATH}"
        )

    if not INPUT_SITE_PATH.exists():
        raise FileNotFoundError(
            "SITE 입력 파일이 없습니다: "
            f"{INPUT_SITE_PATH}"
        )

    spatial_snapshot = load_json(
        INPUT_SPATIAL_SNAPSHOT_PATH
    )

    site_data = load_json(
        INPUT_SITE_PATH
    )

    site = extract_site_info(
        site_data
    )

    conditions = extract_existing_conditions(
        spatial_snapshot
    )

    print_site(
        site
    )

    print_separator()
    print(
        "=== C-9-1A 입력 공간조건 ==="
    )
    print_separator()

    print(
        "조건 수:",
        len(
            conditions
        ),
    )

    for item in conditions:

        name = extract_condition_name(
            item
        )

        if name:
            print(
                f"- {name}"
            )

    print()

    results = build_source_results(
        conditions=conditions,
        site=site,
    )

    print_separator()
    print(
        "=== C-9-2-1 Source Registry ==="
    )
    print_separator()

    print()

    for result in results:
        print_source_result(
            result
        )

    summary = build_summary(
        results
    )

    print_separator()
    print(
        "=== 조회 Source 상태 요약 ==="
    )
    print_separator()

    print(
        "전체:",
        summary[
            "total"
        ],
    )

    print()

    print(
        "[Query Status]"
    )

    for status, count in (
        summary[
            "query_status"
        ].items()
    ):
        print(
            f"{status}: {count}"
        )

    print()

    print(
        "[Resolved Status]"
    )

    for status, count in (
        summary[
            "resolution_status"
        ].items()
    ):
        print(
            f"{status}: {count}"
        )

    print()

    print(
        "[Query Group]"
    )

    for group, count in (
        summary[
            "query_groups"
        ].items()
    ):
        print(
            f"{group}: {count}"
        )

    print()

    validations = run_validations(
        results
    )

    print_separator()
    print(
        "=== C-9-2-1 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    all_pass = all(
        validations.values()
    )

    output_data = {

        "step":
            "STEP 17-21-C-9-2-1",

        "site": deepcopy(
            site
        ),

        "summary": summary,

        "validations":
            validations,

        "all_pass":
            all_pass,

        "source_registry": deepcopy(
            SPATIAL_SOURCE_REGISTRY
        ),

        "results":
            results,
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

    if all_pass:

        print(
            "STEP 17-21-C-9-2-1 완료"
        )

        print()

        print(
            "공간조회 Source Registry / 결과 Schema 검증: ALL PASS"
        )

        print()

        print(
            "현재 상태:"
        )

        print(
            "- 실제 공간정보 source 연결: 0"
        )

        print(
            "- 공간조건 TRUE 확정: 0"
        )

        print(
            "- 공간조건 FALSE 확정: 0"
        )

        print(
            "- 공간조건 UNKNOWN 유지: "
            f"{len(results)}"
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-2"
        )

        print(
            "→ 지구단위계획 실제 공간조회 source 탐색 / 연결"
        )

        print(
            "→ 대상 필지와 지구단위계획구역 공간교차 판정"
        )

        print(
            "→ 조회 성공 시에만 TRUE / FALSE 확정"
        )

        print(
            "→ API 실패 / 데이터 미확보는 UNKNOWN 유지"
        )

    else:

        print(
            "STEP 17-21-C-9-2-1 검증 실패"
        )

        print()

        print(
            "FAIL 항목이 남아 있으므로 "
            "C-9-2-2로 진행하지 않습니다."
        )


if __name__ == "__main__":
    main()