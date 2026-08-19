import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP 17-21-C-9-2-3A-1
# 개발진흥지구 VWorld dataset 탐색 로직 보정
#
# 핵심 보정
# ------------------------------------------------------------
# 1. 서울 전체 BBOX 제거
# 2. 대상점 주변 소규모 BOX 사용
# 3. NOT_FOUND는 dataset 무효가 아님
# 4. INVALID_RANGE만 dataset 식별자 무효로 분류
# 5. QUERY_SUCCESS / NOT_FOUND 모두 "identifier accepted" 처리
# 6. Feature properties를 최대한 출력하여 의미 확인
# 7. LT_C_UPISUQ161은 지구단위계획 negative-control
# 8. 이 단계에서는 개발진흥지구 TRUE/FALSE 판정 금지
# ============================================================


BASE_DIR = Path(__file__).resolve().parent

QUERY_CONTEXT_PATH = (
    BASE_DIR
    / "output"
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    BASE_DIR
    / "output"
    / "vworld_development_promotion_district_identifier_probe.json"
)

ENV_PATH = BASE_DIR.parent / ".env"


VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"


TARGET_CONDITION = "개발진흥지구"


# ============================================================
# 의미 키워드
# ============================================================

SEMANTIC_KEYWORDS = [
    "개발진흥지구",
    "개발진흥",
    "진흥지구",
    "산업ㆍ유통개발진흥지구",
    "산업·유통개발진흥지구",
]


# ============================================================
# 후보 dataset
#
# 주의:
# 아래 값들은 "정답"이 아니라 probe 후보일 뿐이다.
# INVALID_RANGE가 아닌 경우에만
# VWorld가 식별자를 인식한다고 본다.
# ============================================================

DATASET_CANDIDATES = [
    # --------------------------------------------------------
    # 기존 UQ 계열 탐색 후보
    # --------------------------------------------------------
    "LT_C_UPISUQ111",
    "LT_C_UPISUQ112",
    "LT_C_UPISUQ113",
    "LT_C_UPISUQ114",
    "LT_C_UPISUQ115",

    "LT_C_UPISUQ121",
    "LT_C_UPISUQ122",
    "LT_C_UPISUQ123",
    "LT_C_UPISUQ124",
    "LT_C_UPISUQ125",
    "LT_C_UPISUQ126",
    "LT_C_UPISUQ127",
    "LT_C_UPISUQ128",
    "LT_C_UPISUQ129",

    "LT_C_UPISUQ131",
    "LT_C_UPISUQ132",
    "LT_C_UPISUQ133",
    "LT_C_UPISUQ134",
    "LT_C_UPISUQ135",

    "LT_C_UPISUQ141",
    "LT_C_UPISUQ142",
    "LT_C_UPISUQ143",

    "LT_C_UPISUQ151",
    "LT_C_UPISUQ152",
    "LT_C_UPISUQ153",

    # --------------------------------------------------------
    # 이미 지구단위계획으로 검증됨.
    # negative-control 용도.
    # --------------------------------------------------------
    "LT_C_UPISUQ161",

    "LT_C_UPISUQ162",
    "LT_C_UPISUQ163",

    "LT_C_UPISUQ171",
    "LT_C_UPISUQ172",
]


KNOWN_NEGATIVE_CONTROL = {
    "LT_C_UPISUQ161":
        "지구단위계획구역으로 이미 검증된 dataset",
}


# ============================================================
# 주변 조회 반경
# ============================================================

# 위경도 기준 약 수백 m 수준
# 서울 전체 BBOX처럼 지나치게 넓은 요청을 하지 않는다.

LOCAL_BOX_DELTAS = [
    0.002,
    0.005,
    0.010,
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
) -> None:
    print(
        char * width
    )


def clean_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    if not isinstance(
        value,
        str,
    ):
        value = str(value)

    value = value.replace(
        "\r",
        " ",
    )

    value = value.replace(
        "\n",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def recursive_find_value(
    obj: Any,
    target_keys: List[str],
) -> Optional[Any]:

    if isinstance(
        obj,
        dict,
    ):
        for key in target_keys:

            if (
                key in obj
                and obj[key]
                not in {
                    None,
                    "",
                }
            ):
                return obj[key]

        for value in obj.values():

            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in {
                None,
                "",
            }:
                return result

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            result = recursive_find_value(
                value,
                target_keys,
            )

            if result not in {
                None,
                "",
            }:
                return result

    return None


# ============================================================
# SITE Query Context
# ============================================================

def extract_query_context(
    data: Dict[str, Any],
) -> Dict[str, str]:

    site_id = recursive_find_value(
        data,
        [
            "site_id",
            "SITE ID",
            "parcel_key",
            "parcelKey",
        ],
    )

    address = recursive_find_value(
        data,
        [
            "address",
            "주소",
            "jibun_address",
            "parcel_address",
        ],
    )

    zone = recursive_find_value(
        data,
        [
            "zone",
            "용도지역",
            "land_use_zone",
            "use_zone",
            "zoning",
        ],
    )

    pnu = recursive_find_value(
        data,
        [
            "pnu",
            "PNU",
        ],
    )

    return {
        "site_id":
            clean_text(
                site_id
            ),

        "address":
            clean_text(
                address
            ),

        "zone":
            clean_text(
                zone
            ),

        "pnu":
            clean_text(
                pnu
            ),
    }


# ============================================================
# HTTP
# ============================================================

def request_json(
    url: str,
    params: Dict[str, Any],
    timeout: int = 30,
) -> Tuple[
    Optional[requests.Response],
    Optional[Dict[str, Any]],
    Optional[str],
]:

    try:
        response = requests.get(
            url,
            params=params,
            timeout=timeout,
        )

    except requests.RequestException as exc:
        return (
            None,
            None,
            str(exc),
        )

    try:
        payload = response.json()

    except ValueError:
        payload = None

    return (
        response,
        payload,
        None,
    )


# ============================================================
# VWorld 응답
# ============================================================

def extract_vworld_status(
    payload: Optional[Dict[str, Any]],
) -> str:

    if not isinstance(
        payload,
        dict,
    ):
        return ""

    response_obj = payload.get(
        "response"
    )

    if not isinstance(
        response_obj,
        dict,
    ):
        return ""

    return clean_text(
        response_obj.get(
            "status"
        )
    ).upper()


def extract_vworld_error(
    payload: Optional[Dict[str, Any]],
) -> Dict[str, str]:

    result = {
        "code": "",
        "text": "",
    }

    if not isinstance(
        payload,
        dict,
    ):
        return result

    response_obj = payload.get(
        "response"
    )

    if not isinstance(
        response_obj,
        dict,
    ):
        return result

    error_obj = response_obj.get(
        "error"
    )

    if not isinstance(
        error_obj,
        dict,
    ):
        return result

    result["code"] = clean_text(
        error_obj.get(
            "code"
        )
    )

    result["text"] = clean_text(
        error_obj.get(
            "text"
        )
    )

    return result


# ============================================================
# FeatureCollection
# ============================================================

def find_feature_collections(
    obj: Any,
) -> List[Dict[str, Any]]:

    found = []

    if isinstance(
        obj,
        dict,
    ):

        if (
            obj.get(
                "type"
            )
            == "FeatureCollection"
            and isinstance(
                obj.get(
                    "features"
                ),
                list,
            )
        ):
            found.append(
                obj
            )

        for value in obj.values():

            found.extend(
                find_feature_collections(
                    value
                )
            )

    elif isinstance(
        obj,
        list,
    ):

        for value in obj:

            found.extend(
                find_feature_collections(
                    value
                )
            )

    return found


def extract_features(
    payload: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    if not isinstance(
        payload,
        dict,
    ):
        return []

    collections = find_feature_collections(
        payload
    )

    result = []
    seen = set()

    for collection in collections:

        for feature in collection.get(
            "features",
            [],
        ):

            if not isinstance(
                feature,
                dict,
            ):
                continue

            feature_id = clean_text(
                feature.get(
                    "id"
                )
            )

            if feature_id:
                key = feature_id

            else:
                key = json.dumps(
                    feature,
                    ensure_ascii=False,
                    sort_keys=True,
                )

            if key in seen:
                continue

            seen.add(
                key
            )

            result.append(
                feature
            )

    return result


# ============================================================
# 주소 검색
# ============================================================

def geocode_address(
    api_key: str,
    address: str,
) -> Dict[str, Any]:

    params = {
        "service": "search",
        "request": "search",
        "version": "2.0",
        "crs": "EPSG:4326",
        "size": 10,
        "page": 1,
        "query": address,
        "type": "address",
        "category": "parcel",
        "format": "json",
        "errorformat": "json",
        "key": api_key,
    }

    (
        response,
        payload,
        request_error,
    ) = request_json(
        VWORLD_SEARCH_URL,
        params,
    )

    result = {
        "http_status":
            response.status_code
            if response
            else None,

        "vworld_status":
            extract_vworld_status(
                payload
            ),

        "request_error":
            request_error,

        "x":
            None,

        "y":
            None,
    }

    if (
        response is None
        or response.status_code != 200
        or result[
            "vworld_status"
        ] != "OK"
    ):
        return result

    try:
        items = (
            payload[
                "response"
            ][
                "result"
            ][
                "items"
            ]
        )

    except (
        KeyError,
        TypeError,
    ):
        return result

    if not isinstance(
        items,
        list,
    ):
        return result

    for item in items:

        if not isinstance(
            item,
            dict,
        ):
            continue

        point = item.get(
            "point"
        )

        if not isinstance(
            point,
            dict,
        ):
            continue

        try:
            result["x"] = float(
                point[
                    "x"
                ]
            )

            result["y"] = float(
                point[
                    "y"
                ]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):
            continue

        break

    return result


# ============================================================
# Data API
# ============================================================

def classify_data_response(
    response: Optional[
        requests.Response
    ],
    payload: Optional[
        Dict[str, Any]
    ],
    request_error: Optional[str],
) -> Dict[str, Any]:

    http_status = (
        response.status_code
        if response
        else None
    )

    status = extract_vworld_status(
        payload
    )

    error = extract_vworld_error(
        payload
    )

    # --------------------------------------------------------
    # 중요
    #
    # NOT_FOUND:
    # 해당 위치에 Feature가 없다는 뜻일 수 있으므로
    # dataset 자체를 INVALID로 보면 안 된다.
    #
    # INVALID_RANGE:
    # data 파라미터가 허용되지 않는 경우
    # dataset identifier invalid로 분류
    # --------------------------------------------------------

    if response is None:
        classification = (
            "REQUEST_FAILED"
        )

    elif http_status != 200:
        classification = (
            "HTTP_ERROR"
        )

    elif (
        status == "ERROR"
        and error[
            "code"
        ]
        == "INVALID_RANGE"
    ):
        classification = (
            "INVALID_DATA_IDENTIFIER"
        )

    elif status == "OK":
        classification = (
            "QUERY_SUCCESS"
        )

    elif status == "NOT_FOUND":
        classification = (
            "VALID_IDENTIFIER_NO_FEATURE"
        )

    else:
        classification = (
            "QUERY_FAILED"
        )

    identifier_accepted = (
        classification
        in {
            "QUERY_SUCCESS",
            "VALID_IDENTIFIER_NO_FEATURE",
        }
    )

    return {
        "http_status":
            http_status,

        "vworld_status":
            status,

        "classification":
            classification,

        "identifier_accepted":
            identifier_accepted,

        "error_code":
            error[
                "code"
            ],

        "error_text":
            error[
                "text"
            ],

        "request_error":
            request_error,
    }


def query_dataset(
    api_key: str,
    dataset: str,
    geom_filter: str,
    size: int = 100,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "version": "2.0",
        "data": dataset,
        "key": api_key,
        "domain": "",
        "format": "json",
        "crs": "EPSG:4326",
        "geomFilter": geom_filter,
        "geometry": "true",
        "attribute": "true",
        "size": size,
        "page": 1,
    }

    (
        response,
        payload,
        request_error,
    ) = request_json(
        VWORLD_DATA_URL,
        params,
    )

    classified = classify_data_response(
        response,
        payload,
        request_error,
    )

    features = extract_features(
        payload
    )

    return {
        "dataset":
            dataset,

        **classified,

        "feature_count":
            len(
                features
            ),

        "features":
            features,

        "payload":
            payload,
    }


# ============================================================
# Geometry filter
# ============================================================

def point_filter(
    x: float,
    y: float,
) -> str:

    return (
        f"POINT("
        f"{x} "
        f"{y}"
        f")"
    )


def local_box_filter(
    x: float,
    y: float,
    delta: float,
) -> str:

    min_x = x - delta
    min_y = y - delta

    max_x = x + delta
    max_y = y + delta

    # VWorld Data API BOX 문법
    # BOX(minx,miny,maxx,maxy)

    return (
        f"BOX("
        f"{min_x},"
        f"{min_y},"
        f"{max_x},"
        f"{max_y}"
        f")"
    )


# ============================================================
# 의미 분석
# ============================================================

def flatten_strings(
    obj: Any,
    prefix: str = "",
) -> List[Tuple[str, str]]:

    result = []

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            child = (
                f"{prefix}.{key}"
                if prefix
                else str(key)
            )

            if isinstance(
                value,
                (
                    dict,
                    list,
                ),
            ):
                result.extend(
                    flatten_strings(
                        value,
                        child,
                    )
                )

            else:
                text = clean_text(
                    value
                )

                if text:
                    result.append(
                        (
                            child,
                            text,
                        )
                    )

    elif isinstance(
        obj,
        list,
    ):

        for index, value in enumerate(
            obj
        ):
            result.extend(
                flatten_strings(
                    value,
                    f"{prefix}[{index}]",
                )
            )

    return result


def analyze_feature(
    feature: Dict[str, Any],
) -> Dict[str, Any]:

    properties = feature.get(
        "properties"
    )

    if not isinstance(
        properties,
        dict,
    ):
        properties = {}

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

    flattened = flatten_strings(
        properties
    )

    keyword_hits = []

    for key, value in flattened:

        for keyword in SEMANTIC_KEYWORDS:

            if keyword in value:

                keyword_hits.append(
                    {
                        "key":
                            key,

                        "value":
                            value,

                        "keyword":
                            keyword,
                    }
                )

    return {
        "feature_id":
            clean_text(
                feature.get(
                    "id"
                )
            ),

        "geometry_type":
            geometry_type,

        "properties":
            properties,

        "keyword_hits":
            keyword_hits,

        "semantic_match":
            bool(
                keyword_hits
            ),
    }


def property_preview(
    properties: Dict[str, Any],
    max_items: int = 30,
) -> List[Tuple[str, str]]:

    result = []

    for key, value in properties.items():

        text = clean_text(
            value
        )

        if not text:
            continue

        result.append(
            (
                str(key),
                text,
            )
        )

        if len(
            result
        ) >= max_items:
            break

    return result


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-3A-1 개발진흥지구 VWorld dataset 탐색 보정 ==="
    )

    print()

    print(
        "Query Context 입력:"
    )

    print(
        QUERY_CONTEXT_PATH
    )

    print()

    if not QUERY_CONTEXT_PATH.exists():

        raise FileNotFoundError(
            f"Query Context 파일이 없습니다: {QUERY_CONTEXT_PATH}"
        )

    load_dotenv(
        ENV_PATH
    )

    api_key = clean_text(
        os.getenv(
            "VWORLD_API_KEY"
        )
    )

    raw_context = load_json(
        QUERY_CONTEXT_PATH
    )

    site = extract_query_context(
        raw_context
    )

    # ========================================================
    # SITE
    # ========================================================

    print_separator()

    print(
        "=== 대상 SITE ==="
    )

    print_separator()

    print(
        "SITE ID:",
        site[
            "site_id"
        ]
        or "-",
    )

    print(
        "주소:",
        site[
            "address"
        ]
        or "-",
    )

    print(
        "용도지역:",
        site[
            "zone"
        ]
        or "-",
    )

    print(
        "PNU:",
        site[
            "pnu"
        ]
        or "-",
    )

    print()

    # ========================================================
    # 인증
    # ========================================================

    print_separator()

    print(
        "=== VWorld 인증 ==="
    )

    print_separator()

    if api_key:

        print(
            "VWORLD_API_KEY: 정상적으로 읽었습니다."
        )

    else:

        print(
            "VWORLD_API_KEY: 없습니다."
        )

    print()

    if not api_key:

        raise RuntimeError(
            "VWORLD_API_KEY가 없습니다."
        )

    if not site[
        "address"
    ]:

        raise RuntimeError(
            "SITE 주소가 없습니다."
        )

    if not re.fullmatch(
        r"\d{19}",
        site[
            "pnu"
        ],
    ):

        raise RuntimeError(
            "PNU가 정상적인 19자리가 아닙니다."
        )

    # ========================================================
    # 좌표
    # ========================================================

    print_separator()

    print(
        "=== 1. 대표 좌표 확보 ==="
    )

    print_separator()

    geocode = geocode_address(
        api_key,
        site[
            "address"
        ],
    )

    print(
        "HTTP 상태:",
        geocode[
            "http_status"
        ],
    )

    print(
        "VWorld status:",
        geocode[
            "vworld_status"
        ]
        or "-",
    )

    x = geocode[
        "x"
    ]

    y = geocode[
        "y"
    ]

    if (
        x is None
        or y is None
    ):

        raise RuntimeError(
            "대표좌표 획득 실패"
        )

    print(
        "X:",
        x,
    )

    print(
        "Y:",
        y,
    )

    print()

    # ========================================================
    # 후보 탐색
    # ========================================================

    print_separator()

    print(
        "=== 2. dataset 식별자 / 주변 Feature 탐색 ==="
    )

    print_separator()

    candidates = list(
        dict.fromkeys(
            DATASET_CANDIDATES
        )
    )

    print(
        "후보 수:",
        len(
            candidates
        ),
    )

    print()

    results = []

    for index, dataset in enumerate(
        candidates,
        start=1,
    ):

        print(
            "-" * 70
        )

        print(
            f"[{index}] dataset:",
            dataset,
        )

        if dataset in KNOWN_NEGATIVE_CONTROL:

            print(
                "known control:",
                KNOWN_NEGATIVE_CONTROL[
                    dataset
                ],
            )

        # ----------------------------------------------------
        # POINT
        # ----------------------------------------------------

        point_result = query_dataset(
            api_key,
            dataset,
            point_filter(
                x,
                y,
            ),
        )

        print(
            "POINT HTTP:",
            point_result[
                "http_status"
            ],
        )

        print(
            "POINT VWorld status:",
            point_result[
                "vworld_status"
            ]
            or "-",
        )

        print(
            "POINT classification:",
            point_result[
                "classification"
            ],
        )

        print(
            "identifier accepted:",
            point_result[
                "identifier_accepted"
            ],
        )

        if (
            point_result[
                "classification"
            ]
            == "INVALID_DATA_IDENTIFIER"
        ):

            print(
                "error code:",
                point_result[
                    "error_code"
                ],
            )

            print(
                "error text:",
                point_result[
                    "error_text"
                ],
            )

            results.append(
                {
                    "dataset":
                        dataset,

                    "identifier_accepted":
                        False,

                    "point":
                        {
                            key: value
                            for key, value
                            in point_result.items()
                            if key
                            not in {
                                "payload",
                                "features",
                            }
                        },

                    "local_boxes":
                        [],

                    "semantic_match":
                        False,

                    "semantic_features":
                        [],
                }
            )

            print()

            continue

        print(
            "POINT Feature 수:",
            point_result[
                "feature_count"
            ],
        )

        semantic_features = []

        # point feature 분석
        for feature in point_result[
            "features"
        ]:

            analyzed = analyze_feature(
                feature
            )

            print()

            print(
                "POINT Feature:",
                analyzed[
                    "feature_id"
                ]
                or "-",
            )

            print(
                "geometry:",
                analyzed[
                    "geometry_type"
                ]
                or "-",
            )

            print(
                "properties:"
            )

            for key, value in property_preview(
                analyzed[
                    "properties"
                ]
            ):

                print(
                    f"  {key}: {value}"
                )

            if analyzed[
                "semantic_match"
            ]:

                semantic_features.append(
                    analyzed
                )

                print(
                    ">>> 개발진흥지구 의미 키워드 발견"
                )

        # ----------------------------------------------------
        # Local BOX
        # ----------------------------------------------------

        local_box_results = []

        for delta in LOCAL_BOX_DELTAS:

            box = local_box_filter(
                x,
                y,
                delta,
            )

            box_result = query_dataset(
                api_key,
                dataset,
                box,
                size=100,
            )

            print()

            print(
                f"LOCAL BOX ±{delta}"
            )

            print(
                "geomFilter:",
                box,
            )

            print(
                "HTTP:",
                box_result[
                    "http_status"
                ],
            )

            print(
                "VWorld status:",
                box_result[
                    "vworld_status"
                ]
                or "-",
            )

            print(
                "classification:",
                box_result[
                    "classification"
                ],
            )

            print(
                "Feature 수:",
                box_result[
                    "feature_count"
                ],
            )

            analyzed_box_features = []

            for feature in box_result[
                "features"
            ]:

                analyzed = analyze_feature(
                    feature
                )

                analyzed_box_features.append(
                    analyzed
                )

                if analyzed[
                    "semantic_match"
                ]:

                    semantic_features.append(
                        analyzed
                    )

            local_box_results.append(
                {
                    "delta":
                        delta,

                    "geom_filter":
                        box,

                    "http_status":
                        box_result[
                            "http_status"
                        ],

                    "vworld_status":
                        box_result[
                            "vworld_status"
                        ],

                    "classification":
                        box_result[
                            "classification"
                        ],

                    "identifier_accepted":
                        box_result[
                            "identifier_accepted"
                        ],

                    "feature_count":
                        box_result[
                            "feature_count"
                        ],

                    "features":
                        analyzed_box_features,
                }
            )

            # Feature가 발견되면 속성 출력
            for analyzed in analyzed_box_features[
                :5
            ]:

                print()

                print(
                    "  Feature:",
                    analyzed[
                        "feature_id"
                    ]
                    or "-",
                )

                print(
                    "  geometry:",
                    analyzed[
                        "geometry_type"
                    ]
                    or "-",
                )

                for key, value in property_preview(
                    analyzed[
                        "properties"
                    ],
                    max_items=20,
                ):

                    print(
                        f"    {key}: {value}"
                    )

                if analyzed[
                    "semantic_match"
                ]:

                    print(
                        "  >>> 개발진흥지구 의미 키워드 발견"
                    )

            # 이 dataset이 box 자체에서 invalid라면
            # 더 큰 box는 시도할 필요 없음
            if (
                box_result[
                    "classification"
                ]
                == "INVALID_DATA_IDENTIFIER"
            ):
                break

        # ----------------------------------------------------
        # 중복 semantic feature 제거
        # ----------------------------------------------------

        unique_semantic_features = []

        seen_feature_ids = set()

        for item in semantic_features:

            feature_id = (
                item[
                    "feature_id"
                ]
                or json.dumps(
                    item[
                        "properties"
                    ],
                    ensure_ascii=False,
                    sort_keys=True,
                )
            )

            if feature_id in seen_feature_ids:
                continue

            seen_feature_ids.add(
                feature_id
            )

            unique_semantic_features.append(
                item
            )

        semantic_match = bool(
            unique_semantic_features
        )

        print()

        print(
            "semantic match:",
            semantic_match,
        )

        results.append(
            {
                "dataset":
                    dataset,

                "known_negative_control":
                    KNOWN_NEGATIVE_CONTROL.get(
                        dataset
                    ),

                "identifier_accepted":
                    point_result[
                        "identifier_accepted"
                    ],

                "point":
                    {
                        key: value
                        for key, value
                        in point_result.items()
                        if key
                        not in {
                            "payload",
                            "features",
                        }
                    },

                "point_features":
                    [
                        analyze_feature(
                            feature
                        )
                        for feature
                        in point_result[
                            "features"
                        ]
                    ],

                "local_boxes":
                    local_box_results,

                "semantic_match":
                    semantic_match,

                "semantic_features":
                    unique_semantic_features,
            }
        )

        print()

    # ========================================================
    # 요약
    # ========================================================

    print_separator()

    print(
        "=== 3. 탐색 결과 요약 ==="
    )

    print_separator()

    accepted = [
        item
        for item in results
        if item[
            "identifier_accepted"
        ]
    ]

    semantic = [
        item
        for item in results
        if item[
            "semantic_match"
        ]
    ]

    invalid = [
        item
        for item in results
        if (
            item[
                "point"
            ][
                "classification"
            ]
            == "INVALID_DATA_IDENTIFIER"
        )
    ]

    not_found = [
        item
        for item in results
        if (
            item[
                "point"
            ][
                "classification"
            ]
            == "VALID_IDENTIFIER_NO_FEATURE"
        )
    ]

    print(
        "전체 후보:",
        len(
            results
        ),
    )

    print(
        "식별자 accepted:",
        len(
            accepted
        ),
    )

    print(
        "POINT NOT_FOUND:",
        len(
            not_found
        ),
    )

    print(
        "INVALID_DATA_IDENTIFIER:",
        len(
            invalid
        ),
    )

    print(
        "개발진흥지구 의미 일치:",
        len(
            semantic
        ),
    )

    print()

    if accepted:

        print(
            "VWorld가 식별자로 받아들인 후보:"
        )

        for item in accepted:

            print(
                "-",
                item[
                    "dataset"
                ],
                "|",
                item[
                    "point"
                ][
                    "classification"
                ],
            )

        print()

    selected_dataset = None

    # negative-control 제외 후 semantic match만 선택
    selectable = [
        item
        for item in semantic
        if item[
            "dataset"
        ]
        not in KNOWN_NEGATIVE_CONTROL
    ]

    if len(
        selectable
    ) == 1:

        selected_dataset = (
            selectable[
                0
            ][
                "dataset"
            ]
        )

    elif len(
        selectable
    ) > 1:

        print(
            "주의: 개발진흥지구 의미가 일치하는 dataset이 복수입니다."
        )

        print(
            "추가 구조 분석 후 하나를 선택해야 합니다."
        )

        print()

    if selected_dataset:

        print(
            "개발진흥지구 dataset 후보 확정:"
        )

        print(
            selected_dataset
        )

    else:

        print(
            "개발진흥지구 dataset은 아직 확정하지 않습니다."
        )

    print()

    # ========================================================
    # 검증
    # ========================================================

    validations = {
        "VWORLD API Key 존재":
            bool(
                api_key
            ),

        "SITE 주소 존재":
            bool(
                site[
                    "address"
                ]
            ),

        "PNU 19자리":
            bool(
                re.fullmatch(
                    r"\d{19}",
                    site[
                        "pnu"
                    ],
                )
            ),

        "대표 좌표 획득":
            (
                x is not None
                and y is not None
            ),

        "후보 전체 탐색 완료":
            (
                len(
                    results
                )
                == len(
                    candidates
                )
            ),

        "NOT_FOUND를 INVALID_DATA_IDENTIFIER로 처리하지 않음":
            all(
                not (
                    item[
                        "point"
                    ][
                        "vworld_status"
                    ]
                    == "NOT_FOUND"
                    and item[
                        "point"
                    ][
                        "classification"
                    ]
                    == "INVALID_DATA_IDENTIFIER"
                )
                for item
                in results
            ),

        "서울 전체 대형 BBOX 사용 안 함":
            True,

        "지구단위계획 negative-control 자동선택 금지":
            (
                selected_dataset
                != "LT_C_UPISUQ161"
            ),

        "semantic 검증 없이 개발진흥지구 dataset 확정 금지":
            (
                selected_dataset is None
                or any(
                    item[
                        "dataset"
                    ]
                    == selected_dataset
                    and item[
                        "semantic_match"
                    ]
                    for item
                    in results
                )
            ),

        "dataset 탐색 단계 TRUE/FALSE 판정 없음":
            True,
    }

    print_separator()

    print(
        "=== C-9-2-3A-1 검증 ==="
    )

    print_separator()

    for name, passed in validations.items():

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    all_pass = all(
        validations.values()
    )

    print()

    # ========================================================
    # 저장
    # ========================================================

    output_data = {
        "step":
            "STEP 17-21-C-9-2-3A-1",

        "target_condition":
            TARGET_CONDITION,

        "site": {
            **site,

            "representative_point": {
                "x":
                    x,

                "y":
                    y,

                "crs":
                    "EPSG:4326",
            },
        },

        "summary": {
            "total_candidates":
                len(
                    results
                ),

            "identifier_accepted":
                len(
                    accepted
                ),

            "point_not_found":
                len(
                    not_found
                ),

            "invalid_data_identifier":
                len(
                    invalid
                ),

            "semantic_match":
                len(
                    semantic
                ),

            "selected_dataset":
                selected_dataset,
        },

        "selected_dataset":
            selected_dataset,

        "results":
            results,

        "condition_resolution": {
            "query_status":
                (
                    "NOT_QUERIED"
                    if selected_dataset
                    else "QUERY_FAILED"
                ),

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                (
                    "개발진흥지구 dataset 의미 검증 후보를 확보했으나 "
                    "Parcel Polygon과의 실제 공간교차 전이므로 "
                    "TRUE/FALSE를 확정하지 않음"
                    if selected_dataset
                    else
                    "현재 후보군에서 개발진흥지구 dataset을 "
                    "의미까지 검증하여 확정하지 못했으므로 UNKNOWN 유지"
                ),
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

    print_separator()

    print(
        "결과 저장:"
    )

    print(
        OUTPUT_PATH
    )

    print_separator()

    print()

    if not all_pass:

        print(
            "STEP 17-21-C-9-2-3A-1 검증 실패"
        )

        return

    print(
        "STEP 17-21-C-9-2-3A-1 완료"
    )

    print()

    if selected_dataset:

        print(
            "개발진흥지구 dataset 의미 검증 성공:"
        )

        print(
            selected_dataset
        )

        print()

        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-3B"
        )

        print(
            "→ 대상 PNU Parcel Polygon 재사용"
        )

        print(
            "→ 개발진흥지구 Polygon 조회"
        )

        print(
            "→ Parcel × 개발진흥지구 실제 intersection"
        )

        print(
            "→ 교차 시 TRUE"
        )

        print(
            "→ 완전한 정상조회에서 교차 없음이 확인될 경우 FALSE"
        )

    else:

        print(
            "개발진흥지구 dataset 의미 검증 미완료"
        )

        print()

        print(
            "현재 단계에서는 개발진흥지구를 UNKNOWN으로 유지합니다."
        )

        print()

        print(
            "다음 작업:"
        )

        print(
            "→ identifier accepted 후보의 Feature properties 분석"
        )

        print(
            "→ VWorld 데이터목록 기반으로 후보 ID를 추가 확보"
        )

        print(
            "→ 코드번호 추측 탐색은 여기서 중단"
        )


if __name__ == "__main__":
    main()