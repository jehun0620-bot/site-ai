import json
import re
from pathlib import Path

import requests


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-6A-7-1 "
    "토지이음 MapPlan HTTP 403 보정 / UQQ905 의미 양성대조 검증"
)


# ============================================================
# PATH
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

LIVE_RESULT_PATH = (
    OUTPUT_DIR / "eum_vertical_mixed_use_zone_mapplan_live.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_mapplan_semantic_validation.json"
)


# ============================================================
# TARGET
# ============================================================

EUM_MAP_URL = (
    "https://www.eum.go.kr/web/mp/mpMapDet.jsp"
)

TARGET_NAME = "도시군계획시설입체복합구역"
TARGET_LAYER = "AC"
TARGET_CODE = "UQQ905"

# A-6의 req=analysis에서 실제 확인된 양성대조
POSITIVE_CONTROL_LAYER = "AC"
POSITIVE_CONTROL_CODE = "UQQ300"


# ============================================================
# HEADER PROFILES
# ============================================================

USER_AGENT = (
    "Mozilla/5.0 "
    "(Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

# 중요:
# eum.ne.kr:9002 MapPlan 서버에 무조건 브라우저 AJAX 헤더를
# 강제하지 않는다.
#
# A-6처럼 최소 요청부터 순차적으로 시험한다.

HEADER_PROFILES = [
    {
        "name": "MINIMAL",
        "headers": {},
    },
    {
        "name": "USER_AGENT_ONLY",
        "headers": {
            "User-Agent": USER_AGENT,
        },
    },
    {
        "name": "UA_ACCEPT",
        "headers": {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,*/*;q=0.8",
        },
    },
    {
        "name": "UA_REFERER",
        "headers": {
            "User-Agent": USER_AGENT,
            "Accept": "application/json,*/*;q=0.8",
            "Referer": EUM_MAP_URL,
        },
    },
]


# ============================================================
# UTIL
# ============================================================

def print_line():
    print("=" * 70)


def print_subline():
    print("-" * 70)


def compact(text):
    return re.sub(
        r"\s+",
        " ",
        text or "",
    ).strip()


def load_json(path):
    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(path, data):
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


def safe_text(value):
    if value is None:
        return ""

    return str(value).strip()


def first_non_empty(*values):
    for value in values:
        text = safe_text(value)

        if text:
            return text

    return ""


def get_nested(data, *paths):
    for path in paths:

        current = data
        valid = True

        for key in path:

            if not isinstance(current, dict):
                valid = False
                break

            if key not in current:
                valid = False
                break

            current = current[key]

        if (
            valid
            and current
            not in (
                None,
                "",
            )
        ):
            return current

    return None


def normalize_site(data):
    return {
        "site_id": first_non_empty(
            data.get("site_id"),
            get_nested(
                data,
                ("site", "site_id"),
                ("query_context", "site_id"),
            ),
        ),

        "address": first_non_empty(
            data.get("address"),
            data.get("lot_address"),
            get_nested(
                data,
                ("site", "address"),
                ("query_context", "address"),
            ),
        ),

        "pnu": first_non_empty(
            data.get("pnu"),
            data.get("PNU"),
            get_nested(
                data,
                ("site", "pnu"),
                ("query_context", "pnu"),
            ),
        ),
    }


# ============================================================
# A-6 RESULT COMPATIBILITY
# ============================================================

def extract_server_candidates(data):
    candidates = []

    direct = data.get(
        "server_candidates"
    )

    if isinstance(
        direct,
        list,
    ):
        candidates.extend(
            direct
        )

    mapplan = data.get(
        "mapplan"
    )

    if isinstance(
        mapplan,
        dict,
    ):
        for key in (
            "raw_server",
            "server",
            "endpoint",
        ):
            value = safe_text(
                mapplan.get(
                    key
                )
            )

            if value:
                candidates.append(
                    value
                )

    for key in (
        "server",
        "gis_server",
        "mapplan_server",
        "mapplan_endpoint",
    ):
        value = safe_text(
            data.get(
                key
            )
        )

        if value:
            candidates.append(
                value
            )

    result = []

    for candidate in candidates:

        candidate = safe_text(
            candidate
        )

        if (
            candidate
            and candidate
            not in result
        ):
            result.append(
                candidate
            )

    return result


def extract_version(data):
    return first_non_empty(
        data.get(
            "selected_version"
        ),
        get_nested(
            data,
            ("mapplan", "version"),
        ),
        data.get(
            "version"
        ),
    )


def extract_bbox(data):

    candidates = []

    parcel_bbox = data.get(
        "parcel_bbox"
    )

    if isinstance(
        parcel_bbox,
        dict,
    ):

        for key in (
            "search_epsg5179",
            "epsg5179",
            "bounds_epsg5179",
        ):
            value = parcel_bbox.get(
                key
            )

            if isinstance(
                value,
                list,
            ):
                candidates.append(
                    value
                )

    mapplan = data.get(
        "mapplan"
    )

    if isinstance(
        mapplan,
        dict,
    ):

        raw_mbr = mapplan.get(
            "mbr"
        )

        if isinstance(
            raw_mbr,
            str,
        ):
            try:
                value = [
                    float(v)
                    for v
                    in raw_mbr.split(",")
                ]

                candidates.append(
                    value
                )

            except Exception:
                pass

    for candidate in candidates:

        if (
            isinstance(
                candidate,
                list,
            )
            and len(
                candidate
            ) == 4
        ):
            return candidate

    return []


# ============================================================
# MAPPLAN URL
# ============================================================

def normalize_mapplan_endpoint(server):

    server = safe_text(
        server
    ).rstrip("/")

    if not server:
        return ""

    if server.lower().endswith(
        "/mapplan"
    ):
        return server

    return (
        server
        + "/MapPlan"
    )


# ============================================================
# REQUEST
# ============================================================

def request_json(
    session,
    url,
    params,
    headers=None,
    timeout=30,
):

    result = {
        "url": url,
        "params": params,
        "headers": headers or {},
        "http_status": None,
        "content_type": None,
        "json": None,
        "text": "",
        "error": None,
    }

    try:

        response = session.get(
            url,
            params=params,
            headers=headers or {},
            timeout=timeout,
        )

        result[
            "http_status"
        ] = response.status_code

        result[
            "content_type"
        ] = response.headers.get(
            "Content-Type"
        )

        result[
            "text"
        ] = response.text

        try:
            result[
                "json"
            ] = response.json()

        except Exception:
            pass

    except Exception as e:

        result[
            "error"
        ] = repr(e)

    return result


# ============================================================
# ACCESS PROFILE PROBE
# ============================================================

def probe_access_profile(
    url,
    version,
    pnu,
):

    results = []

    print_line()
    print(
        "=== MapPlan HTTP 접근 Profile Probe ==="
    )
    print_line()

    for profile in HEADER_PROFILES:

        session = requests.Session()

        result = request_json(
            session=session,
            url=url,
            params={
                "req": "analysis",
                "version": version,
                "pnus": pnu,
            },
            headers=profile[
                "headers"
            ],
        )

        valid_json = isinstance(
            result.get(
                "json"
            ),
            dict,
        )

        print_subline()

        print(
            "profile:",
            profile[
                "name"
            ],
        )

        print(
            "headers:",
            profile[
                "headers"
            ],
        )

        print(
            "HTTP:",
            result[
                "http_status"
            ],
        )

        print(
            "Content-Type:",
            result[
                "content_type"
            ],
        )

        print(
            "JSON object:",
            valid_json,
        )

        print(
            "preview:",
            compact(
                result[
                    "text"
                ]
            )[:500],
        )

        results.append(
            {
                "profile": profile[
                    "name"
                ],
                "headers": profile[
                    "headers"
                ],
                "result": result,
                "valid_json": (
                    valid_json
                ),
            }
        )

        if (
            result[
                "http_status"
            ] == 200
            and valid_json
        ):
            print()

            print(
                "선택 HTTP profile:",
                profile[
                    "name"
                ],
            )

            return (
                profile,
                results,
            )

    return (
        None,
        results,
    )


# ============================================================
# GEOJSON
# ============================================================

def classify_geojson(data):

    result = {
        "is_geojson": False,
        "feature_count": 0,
        "geometry_types": [],
        "features": [],
    }

    if not isinstance(
        data,
        dict,
    ):
        return result

    if (
        data.get(
            "type"
        )
        != "FeatureCollection"
    ):
        return result

    features = data.get(
        "features",
        [],
    )

    if not isinstance(
        features,
        list,
    ):
        return result

    result[
        "is_geojson"
    ] = True

    result[
        "feature_count"
    ] = len(
        features
    )

    result[
        "features"
    ] = features

    geometry_types = []

    for feature in features:

        if not isinstance(
            feature,
            dict,
        ):
            continue

        geometry = (
            feature.get(
                "geometry"
            )
            or {}
        )

        if not isinstance(
            geometry,
            dict,
        ):
            continue

        geometry_type = (
            geometry.get(
                "type"
            )
        )

        if (
            geometry_type
            and geometry_type
            not in geometry_types
        ):
            geometry_types.append(
                geometry_type
            )

    result[
        "geometry_types"
    ] = geometry_types

    return result


# ============================================================
# ANALYSIS PARSER
# ============================================================

def parse_analysis(data):

    records = []

    if not isinstance(
        data,
        dict,
    ):
        return records

    layers = data.get(
        "layer",
        []
    )

    if not isinstance(
        layers,
        list,
    ):
        return records

    for layer in layers:

        if not isinstance(
            layer,
            dict,
        ):
            continue

        layer_name = safe_text(
            layer.get(
                "name"
            )
        ).upper()

        codes = layer.get(
            "codes",
            []
        )

        if not isinstance(
            codes,
            list,
        ):
            continue

        for item in codes:

            if not isinstance(
                item,
                dict,
            ):
                continue

            records.append(
                {
                    "layer": layer_name,
                    "code": safe_text(
                        item.get(
                            "code"
                        )
                    ),
                    "area": item.get(
                        "area"
                    ),
                }
            )

    return records


def find_analysis_code(
    records,
    layer_name,
    code,
):

    layer_name = (
        safe_text(
            layer_name
        ).upper()
    )

    result = []

    for item in records:

        if (
            item[
                "layer"
            ] == layer_name
            and item[
                "code"
            ] == code
        ):
            result.append(
                item
            )

    return result


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        f"=== {STEP_NAME} ==="
    )

    print()

    context = load_json(
        QUERY_CONTEXT_PATH
    )

    live_result = load_json(
        LIVE_RESULT_PATH
    )

    site = normalize_site(
        context
    )

    pnu = site[
        "pnu"
    ]

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print_line()
    print(
        "=== 대상 SITE ==="
    )
    print_line()

    print(
        "SITE ID:",
        site[
            "site_id"
        ] or "-",
    )

    print(
        "주소:",
        site[
            "address"
        ] or "-",
    )

    print(
        "PNU:",
        pnu or "-",
    )

    if (
        len(
            pnu
        ) != 19
        or not pnu.isdigit()
    ):
        raise RuntimeError(
            "PNU 19자리 검증 실패"
        )

    print()

    # --------------------------------------------------------
    # A-6 복원
    # --------------------------------------------------------

    print_line()
    print(
        "=== 1. A-6 MapPlan 정보 복원 ==="
    )
    print_line()

    server_candidates = (
        extract_server_candidates(
            live_result
        )
    )

    selected_version = (
        extract_version(
            live_result
        )
    )

    bbox_5179 = (
        extract_bbox(
            live_result
        )
    )

    if not server_candidates:
        raise RuntimeError(
            "A-6 결과에서 "
            "MapPlan server를 찾지 못했습니다."
        )

    if not selected_version:
        raise RuntimeError(
            "A-6 결과에서 "
            "MapPlan version을 찾지 못했습니다."
        )

    if len(
        bbox_5179
    ) != 4:
        raise RuntimeError(
            "A-6 결과에서 "
            "EPSG:5179 검색 BBOX를 찾지 못했습니다."
        )

    raw_server = (
        server_candidates[0]
    )

    mapplan_url = (
        normalize_mapplan_endpoint(
            raw_server
        )
    )

    mbr = ",".join(
        str(
            value
        )
        for value
        in bbox_5179
    )

    print(
        "A-6 gisServer:",
        raw_server,
    )

    print(
        "MapPlan endpoint:",
        mapplan_url,
    )

    print(
        "version:",
        selected_version,
    )

    print(
        "mbr:",
        mbr,
    )

    print()

    # --------------------------------------------------------
    # HTTP PROFILE PROBE
    # --------------------------------------------------------

    selected_profile, profile_results = (
        probe_access_profile(
            url=mapplan_url,
            version=selected_version,
            pnu=pnu,
        )
    )

    print()

    # --------------------------------------------------------
    # ACCESS FAILURE
    # --------------------------------------------------------

    if selected_profile is None:

        print_line()
        print(
            "=== MapPlan 접근 판정 ==="
        )
        print_line()

        print(
            "source_status:",
            "MAPPLAN_HTTP_ACCESS_BLOCKED",
        )

        print(
            "query_status:",
            "QUERY_FAILED",
        )

        print(
            "resolution:",
            "UNKNOWN",
        )

        print(
            "confidence:",
            "NONE",
        )

        reason = (
            "A-6에서는 동일 MapPlan endpoint에서 HTTP 200 응답을 "
            "확인했으나 현재 실행에서는 최소 헤더를 포함한 모든 "
            "접근 profile이 정상 JSON 응답을 재현하지 못함. "
            "이는 UQQ905 공간조건 음성을 의미하지 않으며 "
            "HTTP 접근 상태 회귀이므로 UNKNOWN 유지"
        )

        print(
            "reason:",
            reason,
        )

        output = {
            "step": STEP_NAME,

            "site": site,

            "mapplan": {
                "endpoint": mapplan_url,
                "version": selected_version,
                "mbr": mbr,
            },

            "http_profile_probe": [
                {
                    "profile": item[
                        "profile"
                    ],
                    "headers": item[
                        "headers"
                    ],
                    "http_status": item[
                        "result"
                    ][
                        "http_status"
                    ],
                    "content_type": item[
                        "result"
                    ][
                        "content_type"
                    ],
                    "valid_json": item[
                        "valid_json"
                    ],
                    "error": item[
                        "result"
                    ][
                        "error"
                    ],
                }
                for item
                in profile_results
            ],

            "site_resolution": {
                "query_status": (
                    "QUERY_FAILED"
                ),
                "resolution": (
                    "UNKNOWN"
                ),
                "confidence": (
                    "NONE"
                ),
                "reason": reason,
            },
        }

        save_json(
            OUTPUT_PATH,
            output,
        )

        print()

        print_line()
        print(
            "결과 저장:"
        )
        print(
            OUTPUT_PATH
        )
        print_line()

        print()

        print(
            "STEP 17-21-C-9-2-6A-7-1 "
            "HTTP 접근 보정 미완료"
        )

        print()

        print(
            "중요:"
        )

        print(
            "HTTP 403을 UQQ905 FALSE로 해석하지 않습니다."
        )

        return

    # --------------------------------------------------------
    # SELECT PROFILE
    # --------------------------------------------------------

    selected_headers = (
        selected_profile[
            "headers"
        ]
    )

    selected_profile_name = (
        selected_profile[
            "name"
        ]
    )

    print_line()
    print(
        "=== 2. 최종 HTTP Profile ==="
    )
    print_line()

    print(
        "profile:",
        selected_profile_name,
    )

    print(
        "headers:",
        selected_headers,
    )

    print()

    # 동일 profile로 새 Session 사용
    session = requests.Session()

    # --------------------------------------------------------
    # ANALYSIS
    # --------------------------------------------------------

    print_line()
    print(
        "=== 3. PNU req=analysis 재검증 ==="
    )
    print_line()

    analysis_result = request_json(
        session=session,
        url=mapplan_url,
        params={
            "req": "analysis",
            "version": (
                selected_version
            ),
            "pnus": pnu,
        },
        headers=selected_headers,
    )

    analysis_success = (
        analysis_result[
            "http_status"
        ] == 200
        and isinstance(
            analysis_result[
                "json"
            ],
            dict,
        )
    )

    records = parse_analysis(
        analysis_result[
            "json"
        ]
    )

    print(
        "HTTP:",
        analysis_result[
            "http_status"
        ],
    )

    print(
        "Content-Type:",
        analysis_result[
            "content_type"
        ],
    )

    print(
        "analysis 정상:",
        analysis_success,
    )

    print(
        "전체 분석 코드 수:",
        len(
            records
        ),
    )

    print()

    print(
        "[AC 계열 분석 결과]"
    )

    ac_records = [
        item
        for item
        in records
        if item[
            "layer"
        ] == "AC"
    ]

    for item in ac_records:

        print(
            "-",
            item[
                "code"
            ],
            "| area:",
            item[
                "area"
            ],
        )

    target_analysis = (
        find_analysis_code(
            records,
            TARGET_LAYER,
            TARGET_CODE,
        )
    )

    control_analysis = (
        find_analysis_code(
            records,
            POSITIVE_CONTROL_LAYER,
            POSITIVE_CONTROL_CODE,
        )
    )

    print()

    print(
        "UQQ905 analysis 존재:",
        bool(
            target_analysis
        ),
    )

    print(
        "UQQ300 analysis 존재:",
        bool(
            control_analysis
        ),
    )

    if control_analysis:

        print(
            "UQQ300 analysis area:",
            control_analysis[
                0
            ][
                "area"
            ],
        )

    print()

    # --------------------------------------------------------
    # POSITIVE CONTROL GEOMETRY
    # --------------------------------------------------------

    print_line()
    print(
        "=== 4. 양성대조 UQQ300 Geometry 조회 ==="
    )
    print_line()

    control_result = request_json(
        session=session,
        url=mapplan_url,
        params={
            "req": "search",
            "version": (
                selected_version
            ),
            "layer": (
                POSITIVE_CONTROL_LAYER
            ),
            "mbr": mbr,
            "code": (
                POSITIVE_CONTROL_CODE
            ),
        },
        headers=selected_headers,
    )

    control_geo = classify_geojson(
        control_result[
            "json"
        ]
    )

    print(
        "HTTP:",
        control_result[
            "http_status"
        ],
    )

    print(
        "GeoJSON:",
        control_geo[
            "is_geojson"
        ],
    )

    print(
        "Feature 수:",
        control_geo[
            "feature_count"
        ],
    )

    print(
        "geometry type:",
        control_geo[
            "geometry_types"
        ],
    )

    print(
        "preview:",
        compact(
            control_result[
                "text"
            ]
        )[:1000],
    )

    print()

    # --------------------------------------------------------
    # TARGET GEOMETRY
    # --------------------------------------------------------

    print_line()
    print(
        "=== 5. 대상 UQQ905 Geometry 조회 ==="
    )
    print_line()

    target_result = request_json(
        session=session,
        url=mapplan_url,
        params={
            "req": "search",
            "version": (
                selected_version
            ),
            "layer": (
                TARGET_LAYER
            ),
            "mbr": mbr,
            "code": (
                TARGET_CODE
            ),
        },
        headers=selected_headers,
    )

    target_geo = classify_geojson(
        target_result[
            "json"
        ]
    )

    print(
        "HTTP:",
        target_result[
            "http_status"
        ],
    )

    print(
        "GeoJSON:",
        target_geo[
            "is_geojson"
        ],
    )

    print(
        "Feature 수:",
        target_geo[
            "feature_count"
        ],
    )

    print(
        "geometry type:",
        target_geo[
            "geometry_types"
        ],
    )

    print(
        "preview:",
        compact(
            target_result[
                "text"
            ]
        )[:1000],
    )

    print()

    # --------------------------------------------------------
    # SEMANTIC CHECK
    # --------------------------------------------------------

    print_line()
    print(
        "=== 6. MapPlan 요청 의미 검증 ==="
    )
    print_line()

    control_analysis_positive = (
        len(
            control_analysis
        ) > 0
    )

    control_geometry_positive = (
        control_result[
            "http_status"
        ] == 200
        and control_geo[
            "is_geojson"
        ]
        and control_geo[
            "feature_count"
        ] > 0
    )

    target_analysis_negative = (
        len(
            target_analysis
        ) == 0
    )

    target_geometry_negative = (
        target_result[
            "http_status"
        ] == 200
        and target_geo[
            "is_geojson"
        ]
        and target_geo[
            "feature_count"
        ] == 0
    )

    search_semantics_verified = (
        analysis_success
        and control_analysis_positive
        and control_geometry_positive
    )

    target_negative_verified = (
        target_analysis_negative
        and target_geometry_negative
    )

    print(
        "analysis endpoint 정상:",
        analysis_success,
    )

    print(
        "양성대조 analysis 검출:",
        control_analysis_positive,
    )

    print(
        "양성대조 geometry 검출:",
        control_geometry_positive,
    )

    print(
        "MapPlan search 의미 검증:",
        search_semantics_verified,
    )

    print(
        "UQQ905 analysis 미검출:",
        target_analysis_negative,
    )

    print(
        "UQQ905 geometry 미검출:",
        target_geometry_negative,
    )

    print(
        "UQQ905 이중 음성:",
        target_negative_verified,
    )

    print()

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    print_line()
    print(
        "=== 7. 입체복합구역 최종 판정 ==="
    )
    print_line()

    if (
        search_semantics_verified
        and target_negative_verified
    ):

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = (
            "FALSE"
        )

        confidence = (
            "HIGH"
        )

        reason = (
            "토지이음 MapPlan에서 대상 PNU req=analysis가 "
            "정상 수행되고 동일 AC layer의 양성대조 UQQ300이 "
            "analysis와 대상 Parcel 주변 geometry 조회에서 모두 "
            "재현되어 MapPlan layer/code/mbr 요청 의미를 검증함. "
            "동일한 조건에서 도시군계획시설입체복합구역 "
            "UQQ905는 PNU analysis에 존재하지 않고 "
            "geometry Feature도 0건이므로 대상 필지는 "
            "입체복합구역에 해당하지 않는 것으로 판정"
        )

    else:

        query_status = (
            "QUERY_SUCCESS"
            if analysis_success
            else "QUERY_FAILED"
        )

        resolution = (
            "UNKNOWN"
        )

        confidence = (
            "NONE"
        )

        if not analysis_success:

            reason = (
                "MapPlan PNU analysis가 정상 재현되지 않아 "
                "UNKNOWN 유지"
            )

        elif not control_analysis_positive:

            reason = (
                "A-6에서 확인했던 양성대조 UQQ300이 "
                "PNU analysis에서 재현되지 않아 UNKNOWN 유지"
            )

        elif not control_geometry_positive:

            reason = (
                "양성대조 UQQ300은 PNU analysis에 존재하지만 "
                "동일 BBOX geometry 검색에서 Feature가 확인되지 않아 "
                "MapPlan search 의미를 아직 검증하지 못함"
            )

        elif not target_analysis_negative:

            reason = (
                "UQQ905가 PNU analysis에 존재하므로 "
                "FALSE로 판정할 수 없으며 실제 Parcel intersection "
                "검증이 필요함"
            )

        elif not target_geometry_negative:

            reason = (
                "UQQ905 geometry Feature가 존재하므로 "
                "실제 Parcel Polygon intersection 검증이 필요함"
            )

        else:

            reason = (
                "입체복합구역 최종 판정 조건이 충분하지 않아 "
                "UNKNOWN 유지"
            )

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

    print()

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    print_line()
    print(
        "=== C-9-2-6A-7-1 검증 ==="
    )
    print_line()

    checks = {
        "SITE 주소 존재": (
            bool(
                site[
                    "address"
                ]
            )
        ),

        "PNU 19자리": (
            len(
                pnu
            ) == 19
            and pnu.isdigit()
        ),

        "MapPlan endpoint 존재": (
            bool(
                mapplan_url
            )
        ),

        "version 존재": (
            bool(
                selected_version
            )
        ),

        "EPSG:5179 BBOX 존재": (
            len(
                bbox_5179
            ) == 4
        ),

        "HTTP profile Probe 실행": (
            len(
                profile_results
            ) > 0
        ),

        "정상 HTTP profile 확보": (
            selected_profile
            is not None
        ),

        "PNU analysis 정상": (
            analysis_success
        ),

        "양성대조 analysis 존재": (
            control_analysis_positive
        ),

        "양성대조 geometry 조회 실행": (
            control_result[
                "http_status"
            ]
            is not None
        ),

        "UQQ905 geometry 조회 실행": (
            target_result[
                "http_status"
            ]
            is not None
        ),

        "FALSE는 MapPlan 의미검증 필요": (
            resolution != "FALSE"
            or search_semantics_verified
        ),

        "FALSE는 UQQ905 analysis 음성 필요": (
            resolution != "FALSE"
            or target_analysis_negative
        ),

        "FALSE는 UQQ905 geometry 음성 필요": (
            resolution != "FALSE"
            or target_geometry_negative
        ),

        "HTTP 실패만으로 FALSE 금지": (
            not (
                resolution == "FALSE"
                and not analysis_success
            )
        ),

        "resolution 허용값": (
            resolution
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            }
        ),

        "query_status 허용값": (
            query_status
            in {
                "QUERY_SUCCESS",
                "QUERY_FAILED",
                "NOT_CONNECTED",
            }
        ),

        "confidence 허용값": (
            confidence
            in {
                "HIGH",
                "MEDIUM",
                "LOW",
                "NONE",
            }
        ),
    }

    for name, passed in (
        checks.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print()

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "target": {
            "name": (
                TARGET_NAME
            ),
            "layer": (
                TARGET_LAYER
            ),
            "code": (
                TARGET_CODE
            ),
        },

        "positive_control": {
            "layer": (
                POSITIVE_CONTROL_LAYER
            ),
            "code": (
                POSITIVE_CONTROL_CODE
            ),
        },

        "mapplan": {
            "raw_server": (
                raw_server
            ),
            "endpoint": (
                mapplan_url
            ),
            "version": (
                selected_version
            ),
            "mbr": mbr,
        },

        "http_profile_probe": [
            {
                "profile": item[
                    "profile"
                ],
                "headers": item[
                    "headers"
                ],
                "http_status": item[
                    "result"
                ][
                    "http_status"
                ],
                "content_type": item[
                    "result"
                ][
                    "content_type"
                ],
                "valid_json": item[
                    "valid_json"
                ],
                "error": item[
                    "result"
                ][
                    "error"
                ],
            }
            for item
            in profile_results
        ],

        "selected_http_profile": {
            "name": (
                selected_profile_name
            ),
            "headers": (
                selected_headers
            ),
        },

        "analysis": {
            "http_status": (
                analysis_result[
                    "http_status"
                ]
            ),
            "records": (
                records
            ),
            "target_matches": (
                target_analysis
            ),
            "control_matches": (
                control_analysis
            ),
        },

        "positive_control_geometry": {
            "http_status": (
                control_result[
                    "http_status"
                ]
            ),
            "is_geojson": (
                control_geo[
                    "is_geojson"
                ]
            ),
            "feature_count": (
                control_geo[
                    "feature_count"
                ]
            ),
            "geometry_types": (
                control_geo[
                    "geometry_types"
                ]
            ),
        },

        "target_geometry": {
            "http_status": (
                target_result[
                    "http_status"
                ]
            ),
            "is_geojson": (
                target_geo[
                    "is_geojson"
                ]
            ),
            "feature_count": (
                target_geo[
                    "feature_count"
                ]
            ),
            "geometry_types": (
                target_geo[
                    "geometry_types"
                ]
            ),
        },

        "semantic_validation": {
            "analysis_success": (
                analysis_success
            ),
            "control_analysis_positive": (
                control_analysis_positive
            ),
            "control_geometry_positive": (
                control_geometry_positive
            ),
            "search_semantics_verified": (
                search_semantics_verified
            ),
            "target_analysis_negative": (
                target_analysis_negative
            ),
            "target_geometry_negative": (
                target_geometry_negative
            ),
            "target_negative_verified": (
                target_negative_verified
            ),
        },

        "site_resolution": {
            "query_status": (
                query_status
            ),
            "resolution": (
                resolution
            ),
            "confidence": (
                confidence
            ),
            "reason": (
                reason
            ),
        },

        "validation": checks,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print_line()

    print(
        "결과 저장:"
    )

    print(
        OUTPUT_PATH
    )

    print_line()

    print()

    if all(
        checks.values()
    ):

        print(
            "STEP 17-21-C-9-2-6A-7-1 완료"
        )

        print()

        print(
            "입체복합구역 최종 판정:"
        )

        print(
            resolution
        )

        if (
            resolution
            == "FALSE"
        ):

            print()

            print(
                "MapPlan HTTP 접근 보정 + "
                "UQQ300 양성대조 + "
                "UQQ905 이중 음성 검증 완료"
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-7"
            )

            print(
                "→ 수산자원보호구역 실제 공간조회"
            )

        else:

            print()

            print(
                "입체복합구역은 아직 UNKNOWN입니다."
            )

    else:

        print(
            "STEP 17-21-C-9-2-6A-7-1 "
            "검증 미완료"
        )


if __name__ == "__main__":
    main()