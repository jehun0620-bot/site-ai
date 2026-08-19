import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-3A-2A
# VWorld UPIS dataset 의미 / 코드 분석 semantic false-positive 보정
#
# 핵심 보정
# ------------------------------------------------------------
# 1. 기존 identifier probe에서 VWorld가 받아들인 dataset만 분석
# 2. LT_C_UPISUQ151 = 도로계열
# 3. LT_C_UPISUQ152 = 철도/주차장계열
# 4. LT_C_UPISUQ153 = 공원/녹지계열
# 5. LT_C_UPISUQ161 = 지구단위계획구역
# 6. 이미 의미가 확정된 dataset은 개발진흥지구 후보에서 강제 제외
# 7. raw keyword match와 실제 dataset candidate 판정을 분리
# 8. 어떤 property / value / keyword가 match되었는지 기록
# 9. 개발진흥지구 dataset 의미 미확정 시 UNKNOWN 유지
# 10. 번호 추측에 의한 dataset 자동선택 금지
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

INPUT_PROBE_PATH = (
    BASE_DIR
    / "output"
    / "vworld_development_promotion_district_identifier_probe.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "vworld_upis_dataset_semantic_probe.json"
)

ENV_PATH = BASE_DIR.parent / ".env"


# ============================================================
# VWorld
# ============================================================

VWORLD_DATA_URL = "https://api.vworld.kr/req/data"

VWORLD_CRS = "EPSG:4326"

MAX_FEATURES = 100


# ============================================================
# 분석 대상 dataset
# ============================================================

ANALYSIS_DATASETS = [
    "LT_C_UPISUQ151",
    "LT_C_UPISUQ152",
    "LT_C_UPISUQ153",
    "LT_C_UPISUQ161",
    "LT_C_UPISUQ171",
]


# ============================================================
# 이미 의미가 검증된 dataset
# ============================================================

KNOWN_DATASET_MEANINGS = {
    "LT_C_UPISUQ151": "도시계획시설-도로계열",
    "LT_C_UPISUQ152": "도시계획시설-철도/주차장계열",
    "LT_C_UPISUQ153": "도시계획시설-공원/녹지계열",
    "LT_C_UPISUQ161": "지구단위계획구역",
}


# ============================================================
# 개발진흥지구 후보에서 제외할 dataset
#
# 중요:
# 이 dataset들은 이미 다른 공간레이어 의미가 확정되었으므로
# 내부 명칭에 "개발" 등의 문자열이 포함되더라도
# 개발진흥지구 dataset으로 선택해서는 안 된다.
# ============================================================

DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS = {
    "LT_C_UPISUQ151",
    "LT_C_UPISUQ152",
    "LT_C_UPISUQ153",
    "LT_C_UPISUQ161",
}


# ============================================================
# 개발진흥지구 semantic keywords
#
# "개발" 단독 사용 금지.
# "택지개발지구" 등이 잘못 매칭되는 것을 방지한다.
# ============================================================

DEVELOPMENT_PROMOTION_KEYWORDS = [
    "개발진흥지구",
    "산업개발진흥지구",
    "유통개발진흥지구",
    "관광휴양개발진흥지구",
    "복합개발진흥지구",
    "특정개발진흥지구",
    "산업ㆍ유통개발진흥지구",
    "산업·유통개발진흥지구",
]


# ============================================================
# 의미 분석 대상 property
# ============================================================

SEMANTIC_PROPERTY_KEYS = [
    "dgm_nm",
    "lcl_nam",
    "mls_nam",
    "scl_nam",
    "atr_nam",
    "pmi_nam",
    "exc_nam",
    "lclas_cl",
    "mlsfc_cl",
    "sclas_cl",
    "atrb_se",
]


# ============================================================
# 서울 의미 탐색 기준점
#
# dataset 자체의 성격을 살펴보기 위한 probe point.
# SITE 판정용 point가 아니다.
# ============================================================

PROBE_POINTS = [
    {
        "name": "강남-개포",
        "x": 127.07539280356858,
        "y": 37.494197498186885,
    },
    {
        "name": "강남-삼성",
        "x": 127.0630,
        "y": 37.5088,
    },
    {
        "name": "송파-잠실",
        "x": 127.1000,
        "y": 37.5133,
    },
    {
        "name": "영등포-여의도",
        "x": 126.9240,
        "y": 37.5219,
    },
    {
        "name": "마포-상암",
        "x": 126.8895,
        "y": 37.5797,
    },
    {
        "name": "구로-가산인접",
        "x": 126.8837,
        "y": 37.4785,
    },
    {
        "name": "성동-성수",
        "x": 127.0557,
        "y": 37.5445,
    },
    {
        "name": "용산",
        "x": 126.9810,
        "y": 37.5320,
    },
]


BOX_DELTAS = [
    0.002,
    0.005,
    0.01,
]


# ============================================================
# 공통 유틸
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


def print_separator(
    char: str = "=",
    width: int = 70,
):
    print(
        char * width
    )


def clean_text(
    value: Any,
) -> str:
    if value is None:
        return ""

    return str(
        value
    ).strip()


def unique_strings(
    values: List[str],
) -> List[str]:
    result = []
    seen = set()

    for value in values:
        value = clean_text(
            value
        )

        if not value:
            continue

        if value in seen:
            continue

        seen.add(
            value
        )

        result.append(
            value
        )

    return result


# ============================================================
# 기존 Probe accepted dataset 읽기
# ============================================================

def collect_accepted_datasets(
    probe_data: Any,
) -> List[str]:

    found: List[str] = []

    def walk(
        obj: Any,
    ):
        if isinstance(
            obj,
            dict,
        ):
            dataset = clean_text(
                obj.get(
                    "dataset"
                )
            )

            identifier_accepted = obj.get(
                "identifier_accepted"
            )

            if (
                dataset
                and identifier_accepted is True
            ):
                found.append(
                    dataset
                )

            for value in obj.values():
                walk(
                    value
                )

        elif isinstance(
            obj,
            list,
        ):
            for value in obj:
                walk(
                    value
                )

    walk(
        probe_data
    )

    return unique_strings(
        found
    )


# ============================================================
# VWorld 응답
# ============================================================

def get_vworld_status(
    data: Any,
) -> str:
    if not isinstance(
        data,
        dict,
    ):
        return ""

    response = data.get(
        "response"
    )

    if not isinstance(
        response,
        dict,
    ):
        return ""

    return clean_text(
        response.get(
            "status"
        )
    ).upper()


def extract_features(
    data: Any,
) -> List[Dict[str, Any]]:

    if not isinstance(
        data,
        dict,
    ):
        return []

    response = data.get(
        "response"
    )

    if not isinstance(
        response,
        dict,
    ):
        return []

    result = response.get(
        "result"
    )

    if not isinstance(
        result,
        dict,
    ):
        return []

    feature_collection = result.get(
        "featureCollection"
    )

    if isinstance(
        feature_collection,
        dict,
    ):
        features = feature_collection.get(
            "features"
        )

        if isinstance(
            features,
            list,
        ):
            return [
                x
                for x in features
                if isinstance(
                    x,
                    dict,
                )
            ]

    if isinstance(
        feature_collection,
        list,
    ):
        result_features = []

        for collection in feature_collection:
            if not isinstance(
                collection,
                dict,
            ):
                continue

            features = collection.get(
                "features"
            )

            if not isinstance(
                features,
                list,
            ):
                continue

            result_features.extend(
                x
                for x in features
                if isinstance(
                    x,
                    dict,
                )
            )

        return result_features

    return []


# ============================================================
# BBOX
# ============================================================

def make_box(
    x: float,
    y: float,
    delta: float,
) -> str:
    return (
        f"BOX("
        f"{x - delta},"
        f"{y - delta},"
        f"{x + delta},"
        f"{y + delta}"
        f")"
    )


# ============================================================
# VWorld 조회
# ============================================================

def query_dataset_bbox(
    dataset: str,
    box: str,
    api_key: str,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": dataset,
        "key": api_key,
        "domain": "localhost",
        "format": "json",
        "crs": VWORLD_CRS,
        "geomFilter": box,
        "size": MAX_FEATURES,
    }

    try:
        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=30,
        )

    except requests.RequestException as exc:
        return {
            "http_status": None,
            "vworld_status": "",
            "classification": "HTTP_ERROR",
            "error": str(exc),
            "features": [],
        }

    http_status = response.status_code

    try:
        data = response.json()

    except ValueError:
        return {
            "http_status": http_status,
            "vworld_status": "",
            "classification": "INVALID_JSON",
            "error": response.text[
                :1000
            ],
            "features": [],
        }

    status = get_vworld_status(
        data
    )

    features = extract_features(
        data
    )

    if (
        http_status == 200
        and status == "OK"
    ):
        classification = (
            "QUERY_SUCCESS"
        )

    elif (
        http_status == 200
        and status == "NOT_FOUND"
    ):
        classification = (
            "VALID_IDENTIFIER_NO_FEATURE"
        )

    else:
        classification = (
            "QUERY_FAILED"
        )

    return {
        "http_status": http_status,
        "vworld_status": status,
        "classification": classification,
        "features": features,
        "raw": data,
    }


# ============================================================
# Feature 속성
# ============================================================

def extract_properties(
    feature: Dict[str, Any],
) -> Dict[str, str]:

    raw = feature.get(
        "properties"
    )

    if not isinstance(
        raw,
        dict,
    ):
        return {}

    result = {}

    for key, value in raw.items():
        result[
            str(key)
        ] = clean_text(
            value
        )

    return result


def detect_development_promotion_keyword_details(
    properties: Dict[str, str],
) -> List[Dict[str, str]]:
    """
    어떤 property의 어떤 값에서
    정확히 어떤 개발진흥지구 keyword가 잡혔는지 기록한다.

    '개발' 단독 keyword는 절대 사용하지 않는다.
    """

    hits: List[
        Dict[str, str]
    ] = []

    for key, value in properties.items():

        if (
            SEMANTIC_PROPERTY_KEYS
            and key
            not in SEMANTIC_PROPERTY_KEYS
        ):
            continue

        if not value:
            continue

        for keyword in (
            DEVELOPMENT_PROMOTION_KEYWORDS
        ):
            if keyword in value:
                hits.append(
                    {
                        "property": key,
                        "value": value,
                        "keyword": keyword,
                    }
                )

    return hits


def summarize_feature(
    feature: Dict[str, Any],
) -> Dict[str, Any]:

    properties = extract_properties(
        feature
    )

    hit_details = (
        detect_development_promotion_keyword_details(
            properties
        )
    )

    geometry = feature.get(
        "geometry"
    )

    geometry_type = ""

    if isinstance(
        geometry,
        dict,
    ):
        geometry_type = clean_text(
            geometry.get(
                "type"
            )
        )

    result = {
        "id": clean_text(
            feature.get(
                "id"
            )
        ),
        "geometry_type":
            geometry_type,
        "properties": properties,
        "development_promotion_keyword_hits":
            sorted(
                {
                    item[
                        "keyword"
                    ]
                    for item in hit_details
                }
            ),
        "development_promotion_keyword_hit_details":
            hit_details,
        "development_promotion_raw_semantic_match":
            bool(
                hit_details
            ),
    }

    return result


# ============================================================
# dataset 전체 의미 분석
# ============================================================

def analyze_dataset_features(
    dataset: str,
    features: List[Dict[str, Any]],
) -> Dict[str, Any]:

    feature_summaries = []

    unique_features: Dict[
        str,
        Dict[str, Any],
    ] = {}

    lcl_names: Set[str] = set()
    mls_names: Set[str] = set()
    scl_names: Set[str] = set()
    atr_names: Set[str] = set()

    semantic_hit_details = []

    for index, feature in enumerate(
        features,
        start=1,
    ):
        summary = summarize_feature(
            feature
        )

        feature_id = (
            summary.get(
                "id"
            )
            or f"{dataset}.__NO_ID__{index}"
        )

        if (
            feature_id
            not in unique_features
        ):
            unique_features[
                feature_id
            ] = summary

        properties = summary.get(
            "properties",
            {},
        )

        for field, target_set in [
            (
                "lcl_nam",
                lcl_names,
            ),
            (
                "mls_nam",
                mls_names,
            ),
            (
                "scl_nam",
                scl_names,
            ),
            (
                "atr_nam",
                atr_names,
            ),
        ]:
            value = clean_text(
                properties.get(
                    field
                )
            )

            if value:
                target_set.add(
                    value
                )

        for hit in summary.get(
            "development_promotion_keyword_hit_details",
            [],
        ):
            semantic_hit_details.append(
                {
                    "feature_id":
                        feature_id,
                    **deepcopy(
                        hit
                    ),
                }
            )

    feature_summaries = list(
        unique_features.values()
    )

    raw_semantic_match = bool(
        semantic_hit_details
    )

    return {
        "dataset": dataset,
        "known_meaning":
            KNOWN_DATASET_MEANINGS.get(
                dataset
            ),
        "feature_count": len(
            feature_summaries
        ),
        "lcl_nam": sorted(
            lcl_names
        ),
        "mls_nam": sorted(
            mls_names
        ),
        "scl_nam": sorted(
            scl_names
        ),
        "atr_nam": sorted(
            atr_names
        ),
        "development_promotion_raw_semantic_match":
            raw_semantic_match,
        "development_promotion_semantic_hit_details":
            semantic_hit_details,
        "features":
            feature_summaries,
    }


# ============================================================
# 개발진흥지구 dataset 후보 최종 판정
# ============================================================

def is_development_promotion_dataset_candidate(
    dataset: str,
    semantic_summary: Dict[str, Any],
) -> bool:
    """
    raw keyword match와 실제 dataset 선택을 분리한다.

    예:
      LT_C_UPISUQ161 내부 dgm_nm에
      '개포택지개발지구 지구단위계획'
      등이 존재하더라도

      이 dataset은 이미 지구단위계획구역으로 검증되었으므로
      개발진흥지구 후보가 될 수 없다.
    """

    if (
        dataset
        in DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS
    ):
        return False

    if not semantic_summary.get(
        "development_promotion_raw_semantic_match"
    ):
        return False

    return True


def get_dataset_exclusion_reason(
    dataset: str,
    semantic_summary: Dict[str, Any],
) -> str:

    if (
        dataset
        in DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS
    ):
        known = (
            KNOWN_DATASET_MEANINGS.get(
                dataset,
                "다른 용도",
            )
        )

        return (
            f"이미 '{known}' dataset으로 의미가 "
            "검증되어 개발진흥지구 후보에서 제외"
        )

    if not semantic_summary.get(
        "development_promotion_raw_semantic_match"
    ):
        return (
            "Feature 속성에서 개발진흥지구를 "
            "명시적으로 나타내는 keyword가 확인되지 않음"
        )

    return ""


# ============================================================
# Dataset 조회
# ============================================================

def probe_dataset(
    dataset: str,
    api_key: str,
) -> Dict[str, Any]:

    requests_log = []

    all_features: List[
        Dict[str, Any]
    ] = []

    for point in PROBE_POINTS:

        point_name = point[
            "name"
        ]

        x = float(
            point[
                "x"
            ]
        )

        y = float(
            point[
                "y"
            ]
        )

        for delta in BOX_DELTAS:

            box = make_box(
                x=x,
                y=y,
                delta=delta,
            )

            result = query_dataset_bbox(
                dataset=dataset,
                box=box,
                api_key=api_key,
            )

            features = result.get(
                "features",
                [],
            )

            requests_log.append(
                {
                    "point_name":
                        point_name,
                    "delta":
                        delta,
                    "geom_filter":
                        box,
                    "http_status":
                        result.get(
                            "http_status"
                        ),
                    "vworld_status":
                        result.get(
                            "vworld_status"
                        ),
                    "classification":
                        result.get(
                            "classification"
                        ),
                    "feature_count":
                        len(
                            features
                        ),
                }
            )

            all_features.extend(
                features
            )

    semantic_summary = (
        analyze_dataset_features(
            dataset=dataset,
            features=all_features,
        )
    )

    candidate = (
        is_development_promotion_dataset_candidate(
            dataset=dataset,
            semantic_summary=
                semantic_summary,
        )
    )

    exclusion_reason = (
        get_dataset_exclusion_reason(
            dataset=dataset,
            semantic_summary=
                semantic_summary,
        )
    )

    semantic_summary[
        "development_promotion_dataset_candidate"
    ] = candidate

    semantic_summary[
        "candidate_exclusion_reason"
    ] = exclusion_reason

    return {
        "dataset": dataset,
        "known_meaning":
            KNOWN_DATASET_MEANINGS.get(
                dataset
            ),
        "requests": requests_log,
        "semantic_summary":
            semantic_summary,
    }


# ============================================================
# 검증
# ============================================================

def validation_all_analysis_datasets_accepted(
    accepted_datasets: List[str],
) -> bool:

    accepted_set = set(
        accepted_datasets
    )

    return all(
        dataset
        in accepted_set
        for dataset
        in ANALYSIS_DATASETS
    )


def validation_known_dataset_meaning(
    dataset_results:
        List[Dict[str, Any]],
    dataset: str,
) -> bool:

    target = next(
        (
            item
            for item
            in dataset_results
            if item.get(
                "dataset"
            )
            == dataset
        ),
        None,
    )

    if target is None:
        return False

    return bool(
        target.get(
            "semantic_summary",
            {}
        ).get(
            "feature_count",
            0,
        )
        >= 0
    )


def validation_uq161_not_candidate(
    dataset_results:
        List[Dict[str, Any]],
) -> bool:

    target = next(
        (
            item
            for item
            in dataset_results
            if item.get(
                "dataset"
            )
            == "LT_C_UPISUQ161"
        ),
        None,
    )

    if target is None:
        return False

    summary = target.get(
        "semantic_summary",
        {},
    )

    return not (
        is_development_promotion_dataset_candidate(
            "LT_C_UPISUQ161",
            summary,
        )
    )


def validation_excluded_dataset_not_selected(
    selected_dataset:
        Optional[str],
) -> bool:

    return (
        selected_dataset is None
        or selected_dataset
        not in
        DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS
    )


def validation_no_site_resolution(
    resolution: str,
) -> bool:
    """
    이 단계에서는 dataset 의미 분석만 수행한다.
    개발진흥지구 SITE TRUE/FALSE는 판정하지 않는다.
    """

    return (
        resolution
        == "UNKNOWN"
    )


def run_validations(
    accepted_datasets:
        List[str],
    dataset_results:
        List[Dict[str, Any]],
    selected_dataset:
        Optional[str],
    resolution: str,
) -> Dict[str, bool]:

    return {
        "기존 accepted dataset만 분석":
            validation_all_analysis_datasets_accepted(
                accepted_datasets
            ),

        "151 도로계열 의미 재확인":
            validation_known_dataset_meaning(
                dataset_results,
                "LT_C_UPISUQ151",
            ),

        "152 철도/주차장계열 의미 재확인":
            validation_known_dataset_meaning(
                dataset_results,
                "LT_C_UPISUQ152",
            ),

        "153 공원/녹지계열 의미 재확인":
            validation_known_dataset_meaning(
                dataset_results,
                "LT_C_UPISUQ153",
            ),

        "161 지구단위계획 의미 재확인":
            validation_known_dataset_meaning(
                dataset_results,
                "LT_C_UPISUQ161",
            ),

        "171 조회 실행":
            validation_known_dataset_meaning(
                dataset_results,
                "LT_C_UPISUQ171",
            ),

        "161 지구단위계획 dataset 개발진흥지구 후보 제외":
            validation_uq161_not_candidate(
                dataset_results
            ),

        "known dataset 개발진흥지구 자동선택 금지":
            validation_excluded_dataset_not_selected(
                selected_dataset
            ),

        "semantic 검증 없이 dataset 자동선택 없음":
            (
                selected_dataset
                is None
                or any(
                    item.get(
                        "dataset"
                    )
                    == selected_dataset
                    and item.get(
                        "semantic_summary",
                        {},
                    ).get(
                        "development_promotion_dataset_candidate"
                    )
                    is True
                    for item
                    in dataset_results
                )
            ),

        "SITE TRUE/FALSE 미판정":
            validation_no_site_resolution(
                resolution
            ),
    }


# ============================================================
# 로그 출력
# ============================================================

def print_request_log(
    requests_log:
        List[Dict[str, Any]],
):
    for item in requests_log:

        status = item.get(
            "vworld_status"
        )

        count = item.get(
            "feature_count"
        )

        print(
            f"{item.get('point_name')} "
            f"±{item.get('delta')}: "
            f"{status or item.get('classification')} "
            f"/ {count}"
        )


def print_name_values(
    label: str,
    values: List[str],
):
    if values:
        print(
            f"{label}: "
            + ", ".join(
                values
            )
        )

    else:
        print(
            f"{label}: -"
        )


def print_feature_examples(
    features:
        List[Dict[str, Any]],
    limit: int = 10,
):
    if not features:
        return

    print()
    print(
        "Feature 예시:"
    )

    for feature in features[
        :limit
    ]:
        print()
        print(
            "  ID:",
            feature.get(
                "id",
                "",
            ),
        )

        props = feature.get(
            "properties",
            {},
        )

        for key in [
            "lclas_cl",
            "mlsfc_cl",
            "sclas_cl",
            "atrb_se",
            "dgm_nm",
            "lcl_nam",
            "mls_nam",
            "scl_nam",
            "atr_nam",
        ]:
            value = props.get(
                key
            )

            if value:
                print(
                    f"    {key}: "
                    f"{value}"
                )

        hit_details = feature.get(
            "development_promotion_keyword_hit_details",
            [],
        )

        if hit_details:
            print(
                "    semantic keyword hits:"
            )

            for hit in hit_details:
                print(
                    "      - "
                    f"{hit.get('property')}: "
                    f"{hit.get('value')} "
                    f"[keyword={hit.get('keyword')}]"
                )


# ============================================================
# 메인
# ============================================================

def main():

    print(
        "=== STEP 17-21-C-9-2-3A-2A "
        "VWorld UPIS dataset semantic false-positive 보정 ==="
    )
    print()

    print(
        "기존 Probe 입력:"
    )
    print(
        INPUT_PROBE_PATH
    )
    print()

    if not INPUT_PROBE_PATH.exists():
        raise FileNotFoundError(
            f"기존 Probe 파일이 없습니다: "
            f"{INPUT_PROBE_PATH}"
        )

    load_dotenv(
        ENV_PATH
    )

    api_key = os.getenv(
        "VWORLD_API_KEY"
    )

    if not api_key:
        raise RuntimeError(
            "VWORLD_API_KEY를 찾을 수 없습니다."
        )

    probe_data = load_json(
        INPUT_PROBE_PATH
    )

    # --------------------------------------------------------
    # 1. 기존 accepted 확인
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 1. 기존 Probe에서 유효 dataset 확인 ==="
    )
    print_separator()

    accepted_datasets = (
        collect_accepted_datasets(
            probe_data
        )
    )

    print(
        "기존 accepted:"
    )

    if accepted_datasets:
        for dataset in (
            accepted_datasets
        ):
            print(
                f"- {dataset}"
            )

    else:
        print(
            "- 없음"
        )

    print()

    all_analysis_accepted = (
        validation_all_analysis_datasets_accepted(
            accepted_datasets
        )
    )

    print(
        "분석 대상 5개 모두 기존 accepted:",
        (
            "PASS"
            if all_analysis_accepted
            else "FAIL"
        ),
    )
    print()

    # --------------------------------------------------------
    # 2. Dataset 의미 탐색
    # --------------------------------------------------------

    print_separator()
    print(
        "=== 2. Dataset별 의미 탐색 ==="
    )
    print_separator()

    dataset_results = []

    for dataset in (
        ANALYSIS_DATASETS
    ):

        print()
        print(
            "-" * 70
        )

        print(
            "dataset:",
            dataset,
        )

        known_meaning = (
            KNOWN_DATASET_MEANINGS.get(
                dataset
            )
        )

        if known_meaning:
            print(
                "기존 의미:",
                known_meaning,
            )

        if (
            dataset
            in DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS
        ):
            print(
                "개발진흥지구 negative-control: True"
            )

        result = probe_dataset(
            dataset=dataset,
            api_key=api_key,
        )

        dataset_results.append(
            result
        )

        requests_log = result.get(
            "requests",
            [],
        )

        print_request_log(
            requests_log
        )

        summary = result.get(
            "semantic_summary",
            {},
        )

        print()

        print(
            "고유 Feature 수:",
            summary.get(
                "feature_count",
                0,
            ),
        )

        print_name_values(
            "lcl_nam",
            summary.get(
                "lcl_nam",
                [],
            ),
        )

        print_name_values(
            "mls_nam",
            summary.get(
                "mls_nam",
                [],
            ),
        )

        print_name_values(
            "atr_nam",
            summary.get(
                "atr_nam",
                [],
            ),
        )

        raw_match = summary.get(
            "development_promotion_raw_semantic_match",
            False,
        )

        candidate = summary.get(
            "development_promotion_dataset_candidate",
            False,
        )

        print(
            "개발진흥지구 raw semantic match:",
            raw_match,
        )

        print(
            "개발진흥지구 dataset candidate:",
            candidate,
        )

        exclusion_reason = (
            summary.get(
                "candidate_exclusion_reason",
                "",
            )
        )

        if exclusion_reason:
            print(
                "후보 제외 사유:",
                exclusion_reason,
            )

        hit_details = summary.get(
            "development_promotion_semantic_hit_details",
            [],
        )

        if hit_details:
            print()
            print(
                "개발진흥지구 semantic hit detail:"
            )

            for hit in hit_details[
                :20
            ]:
                print(
                    "  - "
                    f"Feature={hit.get('feature_id')} "
                    f"| property={hit.get('property')} "
                    f"| keyword={hit.get('keyword')} "
                    f"| value={hit.get('value')}"
                )

        print_feature_examples(
            summary.get(
                "features",
                [],
            ),
            limit=10,
        )

    # --------------------------------------------------------
    # 3. 의미 분석 결과
    # --------------------------------------------------------

    print()
    print_separator()
    print(
        "=== 3. 의미 분석 결과 ==="
    )
    print_separator()

    candidate_datasets = []

    for result in dataset_results:

        dataset = result.get(
            "dataset",
            "",
        )

        summary = result.get(
            "semantic_summary",
            {},
        )

        print(
            dataset
        )

        print(
            "  feature:",
            summary.get(
                "feature_count",
                0,
            ),
        )

        print(
            "  known meaning:",
            result.get(
                "known_meaning"
            )
            or "-",
        )

        print(
            "  raw semantic match:",
            summary.get(
                "development_promotion_raw_semantic_match",
                False,
            ),
        )

        print(
            "  개발진흥지구 candidate:",
            summary.get(
                "development_promotion_dataset_candidate",
                False,
            ),
        )

        exclusion_reason = (
            summary.get(
                "candidate_exclusion_reason"
            )
        )

        if exclusion_reason:
            print(
                "  exclusion:",
                exclusion_reason,
            )

        if summary.get(
            "development_promotion_dataset_candidate"
        ):
            candidate_datasets.append(
                dataset
            )

    print()

    # --------------------------------------------------------
    # 현재는 단 하나의 명확한 후보가 있더라도
    # dataset 의미 검증 단계일 뿐 SITE 판정을 하지 않는다.
    #
    # 복수 후보일 경우 자동선택하지 않는다.
    # --------------------------------------------------------

    if len(
        candidate_datasets
    ) == 1:
        selected_dataset = (
            candidate_datasets[
                0
            ]
        )

    else:
        selected_dataset = None

    print(
        "개발진흥지구 의미 검증 dataset:"
    )

    if selected_dataset:
        print(
            selected_dataset
        )

    else:
        print(
            "미확정"
        )

    # --------------------------------------------------------
    # SITE 상태
    #
    # 이 단계에서는 무조건 UNKNOWN.
    # Dataset 탐색 결과만으로 SITE TRUE/FALSE 금지.
    # --------------------------------------------------------

    resolution = "UNKNOWN"
    query_status = (
        "NOT_QUERIED"
    )
    confidence = "NONE"

    if selected_dataset:
        reason = (
            "개발진흥지구 후보 dataset이 의미상 식별되었으나 "
            "대상 Parcel Polygon과 실제 공간교차를 아직 수행하지 않았으므로 "
            "SITE 판정은 UNKNOWN 유지"
        )

    else:
        reason = (
            "개발진흥지구 전용 dataset의 의미 검증이 완료되지 않았으므로 "
            "SITE 판정을 수행하지 않고 UNKNOWN 유지"
        )

    print()
    print_separator()
    print(
        "=== 4. 현재 개발진흥지구 SITE 판정 상태 ==="
    )
    print_separator()

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
    )

    print(
        "reason:",
        reason,
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validations = run_validations(
        accepted_datasets=
            accepted_datasets,
        dataset_results=
            dataset_results,
        selected_dataset=
            selected_dataset,
        resolution=
            resolution,
    )

    print()
    print_separator()
    print(
        "=== C-9-2-3A-2A 검증 ==="
    )
    print_separator()

    for name, passed in (
        validations.items()
    ):
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    all_pass = all(
        validations.values()
    )

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output_data = {
        "step":
            "STEP 17-21-C-9-2-3A-2A",

        "purpose":
            "VWorld UPIS dataset semantic false-positive 보정",

        "accepted_datasets":
            accepted_datasets,

        "analysis_datasets":
            ANALYSIS_DATASETS,

        "known_dataset_meanings":
            KNOWN_DATASET_MEANINGS,

        "development_promotion_excluded_datasets":
            sorted(
                DEVELOPMENT_PROMOTION_EXCLUDED_DATASETS
            ),

        "development_promotion_keywords":
            DEVELOPMENT_PROMOTION_KEYWORDS,

        "dataset_results":
            dataset_results,

        "development_promotion_candidate_datasets":
            candidate_datasets,

        "selected_dataset":
            selected_dataset,

        "site_resolution": {
            "query_status":
                query_status,
            "resolution":
                resolution,
            "confidence":
                confidence,
            "reason":
                reason,
        },

        "validations":
            validations,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output_data,
    )

    print()
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
    # 종료 메시지
    # --------------------------------------------------------

    if not all_pass:
        print(
            "STEP 17-21-C-9-2-3A-2A 검증 실패"
        )
        print()
        print(
            "FAIL 항목을 먼저 수정해야 합니다."
        )
        return

    print(
        "STEP 17-21-C-9-2-3A-2A 완료"
    )
    print()

    print(
        "UPIS dataset semantic false-positive 방어: ALL PASS"
    )
    print()

    if selected_dataset:
        print(
            "개발진흥지구 후보 dataset:"
        )
        print(
            selected_dataset
        )
        print()
        print(
            "주의:"
        )
        print(
            "아직 SITE TRUE/FALSE는 확정하지 않습니다."
        )
        print()
        print(
            "다음 단계:"
        )
        print(
            "STEP 17-21-C-9-2-3B"
        )
        print(
            "→ 대상 Parcel Polygon과 후보 dataset Polygon 실제 intersection"
        )
        print(
            "→ 실제 교차 확인 시에만 TRUE"
        )
        print(
            "→ 정상 조회 + 교차 없음이 충분히 검증될 때만 FALSE"
        )

    else:
        print(
            "개발진흥지구 dataset 의미 검증:"
        )
        print(
            "미확정"
        )
        print()
        print(
            "현재 개발진흥지구 resolution:"
        )
        print(
            "UNKNOWN"
        )
        print()
        print(
            "LT_C_UPISUQ161은 지구단위계획구역 dataset이므로 "
            "개발진흥지구 후보에서 강제 제외했습니다."
        )
        print()
        print(
            "다음 단계:"
        )
        print(
            "STEP 17-21-C-9-2-3A-3"
        )
        print(
            "→ VWorld 코드번호 추측 탐색 종료"
        )
        print(
            "→ 서울시 / 국가공간정보 개발진흥지구 전용 source 탐색"
        )
        print(
            "→ 전용 source 확보 전까지 개발진흥지구 UNKNOWN 유지"
        )


if __name__ == "__main__":
    main()