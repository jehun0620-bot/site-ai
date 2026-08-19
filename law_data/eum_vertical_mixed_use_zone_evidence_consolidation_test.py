from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional


# ============================================================
# 기본 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
OUTPUT_DIR = LAW_DATA_DIR / "output"

A6_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_mapplan_live.json"
)

A7_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_mapplan_semantic_validation.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "eum_vertical_mixed_use_zone_evidence_consolidation.json"
)


STEP_NAME = (
    "STEP 17-21-C-9-2-6A-8-1 "
    "토지이음 UQQ905 기존 정상응답 Evidence "
    "Consolidation 보정 / 최종 판정 검증"
)

TARGET_NAME = "도시군계획시설입체복합구역"
TARGET_LAYER = "AC"
TARGET_CODE = "UQQ905"

POSITIVE_CONTROL_LAYER = "AC"
POSITIVE_CONTROL_CODE = "UQQ300"


# ============================================================
# 유틸
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


def normalize_text(value: Any) -> str:
    if value is None:
        return ""

    return str(value).strip()


def normalize_layer(value: Any) -> str:
    return normalize_text(value).upper()


def normalize_code(value: Any) -> str:
    return normalize_text(value).upper()


def valid_pnu(value: Any) -> bool:
    text = normalize_text(value)

    return (
        len(text) == 19
        and text.isdigit()
    )


def to_float(
    value: Any,
    default: float = 0.0,
) -> float:

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def to_int(
    value: Any,
    default: int = 0,
) -> int:

    try:
        return int(value)

    except (
        TypeError,
        ValueError,
    ):
        return default


def print_section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ============================================================
# SITE 복원
# ============================================================

def restore_site(
    a6: dict,
) -> dict:

    site = a6.get("site")

    if not isinstance(site, dict):
        site = {}

    site_id = normalize_text(
        site.get("site_id")
    )

    address = normalize_text(
        site.get("address")
    )

    pnu = normalize_text(
        site.get("pnu")
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": pnu,
    }


# ============================================================
# A-6 Analysis preview JSON 복원
# ============================================================

def clean_json_text(
    text: str,
) -> str:

    text = text.strip()

    # Markdown code fence가 혹시 저장되어 있을 경우 제거
    if text.startswith("```"):
        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

    return text.strip()


def parse_json_string(
    value: Any,
) -> Optional[Any]:

    if isinstance(
        value,
        (dict, list),
    ):
        return value

    if not isinstance(
        value,
        str,
    ):
        return None

    text = clean_json_text(value)

    if not text:
        return None

    try:
        return json.loads(text)

    except json.JSONDecodeError:
        return None


def restore_analysis_payload(
    a6: dict,
) -> dict:

    result = {
        "found": False,
        "source": None,
        "http_status": None,
        "content_type": None,
        "payload": None,
        "parse_success": False,
        "reason": None,
    }

    analysis_list = a6.get(
        "mapplan_analysis"
    )

    if not isinstance(
        analysis_list,
        list,
    ):
        result["reason"] = (
            "A-6 mapplan_analysis가 list가 아님"
        )

        return result

    if not analysis_list:
        result["reason"] = (
            "A-6 mapplan_analysis가 비어 있음"
        )

        return result

    # 정상응답 우선
    candidates = sorted(
        analysis_list,
        key=lambda item: (
            0
            if isinstance(item, dict)
            and item.get("http_status") == 200
            else 1
        ),
    )

    for index, item in enumerate(
        candidates,
        start=1,
    ):

        if not isinstance(
            item,
            dict,
        ):
            continue

        http_status = item.get(
            "http_status"
        )

        content_type = normalize_text(
            item.get(
                "content_type"
            )
        )

        # ----------------------------------------
        # 1. 혹시 구조화 response가 있다면 우선
        # ----------------------------------------

        for key in [
            "response",
            "json",
            "payload",
            "data",
        ]:

            parsed = parse_json_string(
                item.get(key)
            )

            if isinstance(
                parsed,
                dict,
            ):

                if isinstance(
                    parsed.get("layer"),
                    list,
                ):

                    result.update(
                        {
                            "found": True,
                            "source": (
                                f"mapplan_analysis"
                                f"[{index - 1}].{key}"
                            ),
                            "http_status": http_status,
                            "content_type": content_type,
                            "payload": parsed,
                            "parse_success": True,
                            "reason": (
                                "구조화된 analysis "
                                "response에서 layer 복원"
                            ),
                        }
                    )

                    return result

        # ----------------------------------------
        # 2. A-6 실제 구조:
        #    preview 문자열을 JSON parse
        # ----------------------------------------

        preview = item.get(
            "preview"
        )

        parsed_preview = (
            parse_json_string(
                preview
            )
        )

        if isinstance(
            parsed_preview,
            dict,
        ):

            if isinstance(
                parsed_preview.get(
                    "layer"
                ),
                list,
            ):

                result.update(
                    {
                        "found": True,
                        "source": (
                            "mapplan_analysis"
                            f"[{index - 1}].preview"
                        ),
                        "http_status": http_status,
                        "content_type": content_type,
                        "payload": parsed_preview,
                        "parse_success": True,
                        "reason": (
                            "A-6 preview 문자열을 "
                            "json.loads()하여 "
                            "analysis layer 복원"
                        ),
                    }
                )

                return result

    result["reason"] = (
        "mapplan_analysis에서 "
        "layer payload를 복원하지 못함"
    )

    return result


# ============================================================
# Analysis Layer / Code 추출
# ============================================================

def extract_analysis_codes(
    payload: Optional[dict],
) -> list[dict]:

    results = []

    if not isinstance(
        payload,
        dict,
    ):
        return results

    layers = payload.get("layer")

    if not isinstance(
        layers,
        list,
    ):
        return results

    for layer_item in layers:

        if not isinstance(
            layer_item,
            dict,
        ):
            continue

        layer_name_raw = (
            layer_item.get("name")
        )

        layer_name = (
            normalize_layer(
                layer_name_raw
            )
        )

        codes = layer_item.get(
            "codes"
        )

        if not isinstance(
            codes,
            list,
        ):
            continue

        for code_item in codes:

            if not isinstance(
                code_item,
                dict,
            ):
                continue

            code = normalize_code(
                code_item.get(
                    "code"
                )
            )

            area = to_float(
                code_item.get(
                    "area"
                ),
                0.0,
            )

            results.append(
                {
                    "layer": layer_name,
                    "layer_raw": layer_name_raw,
                    "code": code,
                    "area": area,
                }
            )

    return results


def find_analysis_code(
    codes: list[dict],
    layer: str,
    code: str,
) -> dict:

    wanted_layer = (
        normalize_layer(layer)
    )

    wanted_code = (
        normalize_code(code)
    )

    matches = []

    for item in codes:

        if (
            normalize_layer(
                item.get("layer")
            )
            == wanted_layer
            and normalize_code(
                item.get("code")
            )
            == wanted_code
        ):

            matches.append(item)

    area = sum(
        to_float(
            item.get("area"),
            0.0,
        )
        for item in matches
    )

    return {
        "found": bool(matches),
        "count": len(matches),
        "area": area,
        "matches": matches,
    }


# ============================================================
# A-6 UQQ905 Geometry Evidence
# ============================================================

def extract_geometry_evidence(
    a6: dict,
) -> dict:

    search_list = a6.get(
        "mapplan_search"
    )

    if not isinstance(
        search_list,
        list,
    ):
        search_list = []

    matched_requests = []

    for item in search_list:

        if not isinstance(
            item,
            dict,
        ):
            continue

        params = item.get(
            "params"
        )

        if not isinstance(
            params,
            dict,
        ):
            params = {}

        req = normalize_text(
            params.get("req")
        ).lower()

        layer = normalize_layer(
            params.get("layer")
        )

        code = normalize_code(
            params.get("code")
        )

        if (
            req == "search"
            and layer == TARGET_LAYER
            and code == TARGET_CODE
        ):

            geojson = item.get(
                "geojson"
            )

            if not isinstance(
                geojson,
                dict,
            ):
                geojson = {}

            matched_requests.append(
                {
                    "server": item.get(
                        "server"
                    ),
                    "url": item.get(
                        "url"
                    ),
                    "http_status": item.get(
                        "http_status"
                    ),
                    "content_type": item.get(
                        "content_type"
                    ),
                    "is_geojson": bool(
                        geojson.get(
                            "is_geojson",
                            False,
                        )
                    ),
                    "feature_count": (
                        to_int(
                            geojson.get(
                                "feature_count"
                            ),
                            0,
                        )
                    ),
                    "geometry_types": (
                        geojson.get(
                            "geometry_types"
                        )
                        if isinstance(
                            geojson.get(
                                "geometry_types"
                            ),
                            list,
                        )
                        else []
                    ),
                    "preview": item.get(
                        "preview"
                    ),
                    "params": params,
                }
            )

    http_200 = any(
        item["http_status"] == 200
        for item in matched_requests
    )

    valid_geojson = any(
        item["http_status"] == 200
        and item["is_geojson"]
        for item in matched_requests
    )

    total_features = sum(
        item["feature_count"]
        for item in matched_requests
        if (
            item["http_status"] == 200
            and item["is_geojson"]
        )
    )

    geometry_negative = (
        bool(matched_requests)
        and http_200
        and valid_geojson
        and total_features == 0
    )

    geometry_positive = (
        valid_geojson
        and total_features > 0
    )

    return {
        "request_count": (
            len(matched_requests)
        ),
        "requests": matched_requests,
        "http_200": http_200,
        "valid_geojson": valid_geojson,
        "feature_count": total_features,
        "geometry_negative": (
            geometry_negative
        ),
        "geometry_positive": (
            geometry_positive
        ),
    }


# ============================================================
# A-7 / A-7-1 HTTP 회귀 Evidence
# ============================================================

def extract_followup_access_state(
    a7: Optional[dict],
) -> dict:

    result = {
        "file_exists": (
            a7 is not None
        ),
        "http_403_observed": False,
        "access_blocked": False,
        "query_status": None,
        "resolution": None,
        "source_status": None,
    }

    if not isinstance(
        a7,
        dict,
    ):
        return result

    # 최신 보정 결과에서 흔히 사용하는 위치들
    for key in [
        "source_status",
        "status",
    ]:

        value = normalize_text(
            a7.get(key)
        )

        if value:
            result["source_status"] = value
            break

    site_resolution = a7.get(
        "site_resolution"
    )

    if isinstance(
        site_resolution,
        dict,
    ):

        result["query_status"] = (
            site_resolution.get(
                "query_status"
            )
        )

        result["resolution"] = (
            site_resolution.get(
                "resolution"
            )
        )

    else:

        result["query_status"] = (
            a7.get(
                "query_status"
            )
        )

        result["resolution"] = (
            a7.get(
                "resolution"
            )
        )

    serialized = json.dumps(
        a7,
        ensure_ascii=False,
    )

    if (
        '"http_status": 403'
        in serialized
        or "HTTP 403"
        in serialized
        or "MAPPLAN_HTTP_ACCESS_BLOCKED"
        in serialized
    ):

        result[
            "http_403_observed"
        ] = True

    source_status = normalize_text(
        result.get(
            "source_status"
        )
    ).upper()

    if (
        "ACCESS_BLOCKED"
        in source_status
        or result[
            "http_403_observed"
        ]
    ):

        result[
            "access_blocked"
        ] = True

    return result


# ============================================================
# 메인
# ============================================================

def main() -> None:

    print(
        f"=== {STEP_NAME} ==="
    )

    if not A6_PATH.exists():
        raise FileNotFoundError(
            f"A-6 Evidence 파일 없음: "
            f"{A6_PATH}"
        )

    a6 = load_json(
        A6_PATH
    )

    if not isinstance(
        a6,
        dict,
    ):
        raise RuntimeError(
            "A-6 JSON root가 dict가 아닙니다."
        )

    a7 = None

    if A7_PATH.exists():

        loaded_a7 = load_json(
            A7_PATH
        )

        if isinstance(
            loaded_a7,
            dict,
        ):
            a7 = loaded_a7

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    site = restore_site(a6)

    print_section(
        "=== 대상 SITE ==="
    )

    print(
        "SITE ID:",
        site["site_id"]
        or "-",
    )

    print(
        "주소:",
        site["address"]
        or "-",
    )

    print(
        "PNU:",
        site["pnu"]
        or "-",
    )

    if not valid_pnu(
        site["pnu"]
    ):

        raise RuntimeError(
            "PNU 19자리 검증 실패"
        )

    # --------------------------------------------------------
    # A-6 Analysis 복원
    # --------------------------------------------------------

    print_section(
        "=== 1. A-6 기존 정상 MapPlan Evidence 복원 ==="
    )

    analysis_restore = (
        restore_analysis_payload(a6)
    )

    print(
        "A-6 파일 존재:",
        True,
    )

    print(
        "analysis payload 복원:",
        analysis_restore[
            "found"
        ],
    )

    print(
        "analysis source:",
        analysis_restore[
            "source"
        ],
    )

    print(
        "analysis HTTP:",
        analysis_restore[
            "http_status"
        ],
    )

    print(
        "analysis parse success:",
        analysis_restore[
            "parse_success"
        ],
    )

    analysis_payload = (
        analysis_restore[
            "payload"
        ]
    )

    analysis_codes = (
        extract_analysis_codes(
            analysis_payload
        )
    )

    layer_names = sorted(
        {
            item["layer"]
            for item in analysis_codes
            if item["layer"]
        }
    )

    print(
        "analysis layer 종류 수:",
        len(layer_names),
    )

    print(
        "analysis code 수:",
        len(analysis_codes),
    )

    print()
    print(
        "[복원된 Layer]"
    )

    for name in layer_names:
        print(
            "-",
            name,
        )

    # --------------------------------------------------------
    # 양성 대조 UQQ300
    # --------------------------------------------------------

    positive = find_analysis_code(
        analysis_codes,
        POSITIVE_CONTROL_LAYER,
        POSITIVE_CONTROL_CODE,
    )

    print()
    print(
        "[양성대조 UQQ300]"
    )

    print(
        "layer:",
        POSITIVE_CONTROL_LAYER,
    )

    print(
        "found:",
        positive["found"],
    )

    print(
        "count:",
        positive["count"],
    )

    print(
        "area:",
        positive["area"],
    )

    # --------------------------------------------------------
    # 대상 UQQ905 analysis
    # --------------------------------------------------------

    target_analysis = (
        find_analysis_code(
            analysis_codes,
            TARGET_LAYER,
            TARGET_CODE,
        )
    )

    print()
    print(
        "[대상 UQQ905 Analysis]"
    )

    print(
        "layer:",
        TARGET_LAYER,
    )

    print(
        "found:",
        target_analysis[
            "found"
        ],
    )

    print(
        "count:",
        target_analysis[
            "count"
        ],
    )

    print(
        "area:",
        target_analysis[
            "area"
        ],
    )

    # --------------------------------------------------------
    # Geometry
    # --------------------------------------------------------

    geometry = (
        extract_geometry_evidence(
            a6
        )
    )

    print()
    print(
        "[대상 UQQ905 Geometry]"
    )

    print(
        "정상 요청 수:",
        geometry[
            "request_count"
        ],
    )

    print(
        "HTTP 200:",
        geometry[
            "http_200"
        ],
    )

    print(
        "GeoJSON 정상:",
        geometry[
            "valid_geojson"
        ],
    )

    print(
        "Feature 수:",
        geometry[
            "feature_count"
        ],
    )

    print(
        "geometry 음성:",
        geometry[
            "geometry_negative"
        ],
    )

    # --------------------------------------------------------
    # A-7 후속 403 상태
    # --------------------------------------------------------

    print_section(
        "=== 2. A-7 / A-7-1 후속 접근상태 Evidence ==="
    )

    followup = (
        extract_followup_access_state(
            a7
        )
    )

    print(
        "A-7 파일 존재:",
        followup[
            "file_exists"
        ],
    )

    print(
        "HTTP 403 관측:",
        followup[
            "http_403_observed"
        ],
    )

    print(
        "접근 차단 상태:",
        followup[
            "access_blocked"
        ],
    )

    print(
        "query_status:",
        followup[
            "query_status"
        ],
    )

    print(
        "기존 resolution:",
        followup[
            "resolution"
        ],
    )

    print()
    print(
        "해석:"
    )

    print(
        "후속 HTTP 403은 MapPlan 접근 상태 "
        "회귀로만 처리합니다."
    )

    print(
        "A-6에서 확보된 HTTP 200 정상응답 "
        "Evidence는 폐기하지 않습니다."
    )

    print(
        "403 자체는 UQQ905 TRUE/FALSE "
        "근거로 사용하지 않습니다."
    )

    # --------------------------------------------------------
    # Evidence Consolidation
    # --------------------------------------------------------

    print_section(
        "=== 3. UQQ905 Evidence Consolidation ==="
    )

    a6_http_200_analysis = (
        analysis_restore[
            "http_status"
        ]
        == 200
    )

    positive_control_valid = (
        a6_http_200_analysis
        and analysis_restore[
            "parse_success"
        ]
        and positive[
            "found"
        ]
        and positive[
            "area"
        ] > 0
    )

    target_analysis_negative = (
        a6_http_200_analysis
        and analysis_restore[
            "parse_success"
        ]
        and not target_analysis[
            "found"
        ]
    )

    target_geometry_negative = (
        geometry[
            "geometry_negative"
        ]
    )

    double_negative = (
        target_analysis_negative
        and target_geometry_negative
    )

    positive_plus_double_negative = (
        positive_control_valid
        and double_negative
    )

    print(
        "A-6 analysis HTTP 200:",
        a6_http_200_analysis,
    )

    print(
        "UQQ300 양성대조 유효:",
        positive_control_valid,
    )

    print(
        "UQQ905 PNU analysis 음성:",
        target_analysis_negative,
    )

    print(
        "UQQ905 geometry 음성:",
        target_geometry_negative,
    )

    print(
        "UQQ905 이중 음성:",
        double_negative,
    )

    print(
        "양성대조 + 이중 음성:",
        positive_plus_double_negative,
    )

    # --------------------------------------------------------
    # TRUE 조건
    # --------------------------------------------------------

    true_evidence = (
        geometry[
            "geometry_positive"
        ]
        or target_analysis[
            "found"
        ]
        and target_analysis[
            "area"
        ] > 0
    )

    # --------------------------------------------------------
    # 최종 판정
    # --------------------------------------------------------

    print_section(
        "=== 4. 입체복합구역 최종 판정 ==="
    )

    if true_evidence:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = "TRUE"
        confidence = "HIGH"

        evidence_state = (
            "TARGET_POSITIVE_EVIDENCE"
        )

        reason = (
            "UQQ905 대상 코드에 대한 "
            "양성 공간/analysis evidence가 "
            "확인되어 입체복합구역으로 판정함"
        )

    elif positive_plus_double_negative:

        query_status = (
            "QUERY_SUCCESS"
        )

        resolution = "FALSE"
        confidence = "HIGH"

        evidence_state = (
            "POSITIVE_CONTROL_VALID_"
            "TARGET_DOUBLE_NEGATIVE"
        )

        reason = (
            "A-6에서 동일 MapPlan 요청 체계의 "
            "양성대조 UQQ300이 PNU analysis에서 "
            "정상 검출되었고, 동일 대상 PNU에 대해 "
            "UQQ905가 analysis에서 검출되지 않았으며 "
            "대상 Parcel 주변 UQQ905 geometry 조회도 "
            "정상 HTTP 200 GeoJSON 응답에서 0건으로 "
            "확인되어 입체복합구역이 아닌 것으로 판정함"
        )

    else:

        query_status = (
            "QUERY_SUCCESS"
            if (
                a6_http_200_analysis
                or geometry[
                    "http_200"
                ]
            )
            else "QUERY_FAILED"
        )

        resolution = "UNKNOWN"

        if (
            target_geometry_negative
            or target_analysis_negative
        ):

            confidence = "LOW"

        else:
            confidence = "NONE"

        evidence_state = (
            "EVIDENCE_INCOMPLETE"
        )

        missing = []

        if not positive_control_valid:

            missing.append(
                "UQQ300 양성대조"
            )

        if not target_analysis_negative:

            missing.append(
                "UQQ905 analysis 음성"
            )

        if not target_geometry_negative:

            missing.append(
                "UQQ905 geometry 음성"
            )

        reason = (
            "FALSE 판정에 필요한 Evidence가 "
            "완전히 충족되지 않음"
        )

        if missing:

            reason += (
                ": "
                + ", ".join(missing)
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
        "evidence_state:",
        evidence_state,
    )

    print(
        "reason:",
        reason,
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    validation = {
        "SITE ID 복원": bool(
            site["site_id"]
        ),

        "SITE 주소 존재": bool(
            site["address"]
        ),

        "PNU 19자리": valid_pnu(
            site["pnu"]
        ),

        "A-6 evidence 파일 존재": (
            A6_PATH.exists()
        ),

        "A-6 analysis preview JSON 복원": (
            analysis_restore[
                "parse_success"
            ]
        ),

        "A-6 analysis HTTP 200": (
            a6_http_200_analysis
        ),

        "A-6 analysis layer 구조 복원": (
            bool(layer_names)
        ),

        "AC 양성대조 UQQ300 확인": (
            positive_control_valid
        ),

        "UQQ905 PNU analysis 음성 검증": (
            target_analysis_negative
        ),

        "UQQ905 geometry evidence 해석": (
            geometry[
                "http_200"
            ]
            and geometry[
                "valid_geojson"
            ]
        ),

        "UQQ905 geometry 음성 검증": (
            target_geometry_negative
        ),

        "HTTP 403을 FALSE 근거로 사용 안 함": (
            True
        ),

        "후속 403으로 기존 HTTP 200 evidence 폐기 안 함": (
            True
        ),

        "TRUE는 실제 양성 evidence 필요": (
            resolution != "TRUE"
            or true_evidence
        ),

        "FALSE는 양성대조 필요": (
            resolution != "FALSE"
            or positive_control_valid
        ),

        "FALSE는 UQQ905 analysis 음성 필요": (
            resolution != "FALSE"
            or target_analysis_negative
        ),

        "FALSE는 UQQ905 geometry 음성 필요": (
            resolution != "FALSE"
            or target_geometry_negative
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
                "NOT_QUERIED",
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

    print_section(
        "=== C-9-2-6A-8-1 검증 ==="
    )

    all_pass = True

    for name, passed in (
        validation.items()
    ):

        print(
            f"{name}:",
            "PASS"
            if passed
            else "FAIL",
        )

        if not passed:
            all_pass = False

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "target": {
            "name": TARGET_NAME,
            "layer": TARGET_LAYER,
            "code": TARGET_CODE,
        },

        "a6_analysis_evidence": {
            "source": (
                analysis_restore[
                    "source"
                ]
            ),
            "http_status": (
                analysis_restore[
                    "http_status"
                ]
            ),
            "content_type": (
                analysis_restore[
                    "content_type"
                ]
            ),
            "parse_success": (
                analysis_restore[
                    "parse_success"
                ]
            ),
            "layer_count": len(
                layer_names
            ),
            "code_count": len(
                analysis_codes
            ),
        },

        "positive_control": {
            "layer": (
                POSITIVE_CONTROL_LAYER
            ),
            "code": (
                POSITIVE_CONTROL_CODE
            ),
            "found": (
                positive[
                    "found"
                ]
            ),
            "count": (
                positive[
                    "count"
                ]
            ),
            "area": (
                positive[
                    "area"
                ]
            ),
            "valid": (
                positive_control_valid
            ),
        },

        "target_analysis": {
            "layer": TARGET_LAYER,
            "code": TARGET_CODE,
            "found": (
                target_analysis[
                    "found"
                ]
            ),
            "count": (
                target_analysis[
                    "count"
                ]
            ),
            "area": (
                target_analysis[
                    "area"
                ]
            ),
            "negative": (
                target_analysis_negative
            ),
        },

        "target_geometry": geometry,

        "followup_access_state": (
            followup
        ),

        "evidence_consolidation": {
            "positive_control_valid": (
                positive_control_valid
            ),
            "target_analysis_negative": (
                target_analysis_negative
            ),
            "target_geometry_negative": (
                target_geometry_negative
            ),
            "double_negative": (
                double_negative
            ),
            "positive_control_plus_double_negative": (
                positive_plus_double_negative
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
            "evidence_state": (
                evidence_state
            ),
            "reason": reason,
        },

        "validation": validation,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print_section(
        "결과 저장:"
    )

    print(
        OUTPUT_PATH
    )

    print("=" * 70)

    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-6A-8-1 완료"
        )

        print()

        print(
            "입체복합구역 최종 판정:"
        )

        print(
            resolution
        )

        if resolution == "FALSE":

            print()
            print(
                "A-6 HTTP 200 정상응답에서 "
                "UQQ300 양성대조와 "
                "UQQ905 analysis/geometry "
                "이중 음성을 모두 검증했습니다."
            )

            print()
            print(
                "후속 HTTP 403은 판정 근거에서 "
                "배제했습니다."
            )

    else:

        print(
            "STEP 17-21-C-9-2-6A-8-1 "
            "검증 미완료"
        )

        print()
        print(
            "입체복합구역 최종 판정:"
        )

        print(
            resolution
        )


if __name__ == "__main__":
    main()