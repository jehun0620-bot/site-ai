import json
import os
import sys
import zipfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-6A-1 "
    "입체복합구역 서울시 기타용도구역 UQ145 Schema 탐색"
)

TARGET_NAMES = [
    "입체복합구역",
    "도시군계획시설입체복합구역",
    "도시ㆍ군계획시설입체복합구역",
    "도시·군계획시설입체복합구역",
]


# ============================================================
# 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
INPUT_DIR = LAW_DATA_DIR / "input"
SPATIAL_DIR = LAW_DATA_DIR / "spatial"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR / "site_spatial_query_context.json"
)

PREVIOUS_PROBE_PATH = (
    OUTPUT_DIR / "seoul_vertical_mixed_use_zone_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR / "seoul_vertical_mixed_use_zone_uq145_schema_probe.json"
)

ENV_PATH = BASE_DIR / ".env"


# ============================================================
# 환경
# ============================================================

load_dotenv(ENV_PATH)

SEOUL_OPEN_API_KEY = os.getenv("SEOUL_OPEN_API_KEY")


# ============================================================
# 설정
# ============================================================

SEOUL_API_BASE = "http://openapi.seoul.go.kr:8088"

DATASET_CODE = "UQ145"
DATASET_NAME = "서울시 기타용도구역 공간정보"

EXPECTED_CRS = "EPSG:5174"

SERVICE_CANDIDATES = [
    "upisCUq145",
    "upiSCUq145",
    "upisCUQ145",
    "upiSCUQ145",
]


# ============================================================
# 공통
# ============================================================

def print_separator(char: str = "=") -> None:
    print(char * 70)


def print_title(title: str) -> None:
    print()
    print_separator("=")
    print(f"=== {title} ===")
    print_separator("=")


def load_json(path: Path) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:
        return json.load(f)


def save_json(
    path: Path,
    data: Dict[str, Any],
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


def recursive_find(
    obj: Any,
    keys: List[str],
) -> Optional[Any]:

    if isinstance(obj, dict):

        for key in keys:

            if key in obj:

                value = obj[key]

                if value not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return value

        for value in obj.values():

            found = recursive_find(
                value,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    elif isinstance(obj, list):

        for item in obj:

            found = recursive_find(
                item,
                keys,
            )

            if found not in (
                None,
                "",
                [],
                {},
            ):
                return found

    return None


# ============================================================
# SITE
# ============================================================

def extract_site(
    context: Dict[str, Any],
) -> Dict[str, Any]:

    site_id = recursive_find(
        context,
        [
            "site_id",
            "SITE_ID",
        ],
    )

    address = recursive_find(
        context,
        [
            "address",
            "jibun_address",
            "site_address",
        ],
    )

    pnu = recursive_find(
        context,
        [
            "pnu",
            "PNU",
        ],
    )

    sigungu_code = recursive_find(
        context,
        [
            "sigungu_code",
            "sgg_cd",
        ],
    )

    zoning = recursive_find(
        context,
        [
            "zoning",
            "zone_name",
            "land_use_zone",
            "용도지역",
        ],
    )

    return {
        "site_id": site_id,
        "address": address,
        "pnu": (
            str(pnu)
            if pnu
            else None
        ),
        "sigungu_code": (
            str(sigungu_code)
            if sigungu_code
            else None
        ),
        "zoning": zoning,
    }


# ============================================================
# 서울 OpenAPI
# ============================================================

def request_service(
    service: str,
) -> Dict[str, Any]:

    url = (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{service}/"
        f"1/1000/"
    )

    result = {
        "service": service,
        "http_status": None,
        "service_found": False,
        "success": False,
        "result_code": None,
        "result_message": None,
        "total_count": 0,
        "rows": [],
        "error": None,
    }

    try:

        response = requests.get(
            url,
            timeout=30,
        )

        result["http_status"] = (
            response.status_code
        )

        if response.status_code != 200:
            return result

        payload = response.json()

    except Exception as exc:

        result["error"] = str(exc)

        return result

    service_obj = payload.get(
        service
    )

    if not isinstance(
        service_obj,
        dict,
    ):
        return result

    result["service_found"] = True

    result_info = service_obj.get(
        "RESULT",
        {},
    )

    if isinstance(
        result_info,
        dict,
    ):

        result["result_code"] = (
            result_info.get("CODE")
        )

        result["result_message"] = (
            result_info.get("MESSAGE")
        )

    rows = service_obj.get(
        "row",
        [],
    )

    if not isinstance(
        rows,
        list,
    ):
        rows = []

    result["rows"] = rows

    result["total_count"] = (
        service_obj.get(
            "list_total_count",
            0,
        )
        or 0
    )

    result["success"] = (
        result["result_code"]
        == "INFO-000"
    )

    return result


def probe_services() -> Tuple[
    Optional[str],
    List[Dict[str, Any]],
]:

    results = []

    selected = None

    for service in SERVICE_CANDIDATES:

        result = request_service(
            service
        )

        results.append(result)

        if (
            selected is None
            and result["success"]
        ):
            selected = service

    return selected, results


# ============================================================
# OpenAPI 분석
# ============================================================

def collect_fields(
    rows: List[Dict[str, Any]],
) -> List[str]:

    fields = set()

    for row in rows:

        if isinstance(row, dict):
            fields.update(
                row.keys()
            )

    return sorted(fields)


def normalize_text(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def find_target_rows(
    rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    matches = []

    for row in rows:

        texts = []

        for key, value in row.items():

            text = normalize_text(
                value
            )

            if text:
                texts.append(
                    (
                        key,
                        text,
                    )
                )

        hits = []

        for key, text in texts:

            for target in TARGET_NAMES:

                if target in text:

                    hits.append(
                        {
                            "column": key,
                            "target": target,
                            "value": text,
                        }
                    )

        if hits:

            matches.append(
                {
                    "row": row,
                    "hits": hits,
                }
            )

    return matches


def collect_unique_values(
    rows: List[Dict[str, Any]],
    field: str,
) -> List[str]:

    values = set()

    for row in rows:

        value = normalize_text(
            row.get(field)
        )

        if value:
            values.add(value)

    return sorted(values)


# ============================================================
# 공간파일 탐색
# ============================================================

def find_uq145_files() -> List[Path]:

    patterns = [
        "*UQ145*.zip",
        "*UQ145*.shp",
        "*기타용도구역*.zip",
        "*기타용도구역*.shp",
    ]

    found = []

    for directory in [
        INPUT_DIR,
        SPATIAL_DIR,
    ]:

        if not directory.exists():
            continue

        for pattern in patterns:

            for path in directory.glob(
                pattern
            ):

                if path not in found:
                    found.append(path)

    return sorted(found)


# ============================================================
# SHP 분석
# ============================================================

def inspect_shapefile(
    source_path: Path,
) -> Dict[str, Any]:

    result: Dict[str, Any] = {
        "loaded": False,
        "source": str(source_path),
        "feature_count": 0,
        "columns": [],
        "crs": None,
        "target_matches": [],
        "unique_values": {},
        "error": None,
    }

    try:

        import geopandas as gpd

    except Exception as exc:

        result["error"] = (
            f"geopandas import 실패: {exc}"
        )

        return result

    temp_dir = None

    try:

        shp_path = None

        if source_path.suffix.lower() == ".zip":

            temp_dir = tempfile.TemporaryDirectory()

            with zipfile.ZipFile(
                source_path,
                "r",
            ) as zf:

                zf.extractall(
                    temp_dir.name
                )

            shp_candidates = list(
                Path(
                    temp_dir.name
                ).rglob("*.shp")
            )

            if not shp_candidates:

                result["error"] = (
                    "ZIP 내부 SHP 없음"
                )

                return result

            shp_path = shp_candidates[0]

        elif (
            source_path.suffix.lower()
            == ".shp"
        ):

            shp_path = source_path

        else:

            result["error"] = (
                "지원하지 않는 파일 형식"
            )

            return result

        gdf = gpd.read_file(
            shp_path,
            encoding="cp949",
        )

        result["loaded"] = True
        result["feature_count"] = len(gdf)
        result["columns"] = list(
            gdf.columns
        )

        if gdf.crs is not None:

            result["crs"] = (
                gdf.crs.to_string()
            )

        text_columns = [
            col
            for col in gdf.columns
            if col != "geometry"
        ]

        target_matches = []

        for index, row in gdf.iterrows():

            row_hits = []

            for col in text_columns:

                value = normalize_text(
                    row.get(col)
                )

                if not value:
                    continue

                for target in TARGET_NAMES:

                    if target in value:

                        row_hits.append(
                            {
                                "column": col,
                                "target": target,
                                "value": value,
                            }
                        )

            if row_hits:

                target_matches.append(
                    {
                        "index": int(index),
                        "hits": row_hits,
                        "properties": {
                            col: (
                                None
                                if str(
                                    row.get(col)
                                )
                                == "nan"
                                else str(
                                    row.get(col)
                                )
                            )
                            for col
                            in text_columns
                        },
                    }
                )

        result["target_matches"] = (
            target_matches
        )

        # UPIS 계열 주요 컬럼의 고유값 분석
        candidate_fields = [
            "DGM_NM",
            "LCLAS_CL",
            "MLSFC_CL",
            "SCLAS_CL",
            "ATRB_SE",
            "PRESENT_SN",
            "SIGNGU_SE",
        ]

        unique_values = {}

        for field in candidate_fields:

            if field not in gdf.columns:
                continue

            values = set()

            for value in gdf[
                field
            ].tolist():

                text = normalize_text(
                    value
                )

                if (
                    text
                    and text.lower()
                    != "nan"
                ):
                    values.add(text)

            unique_values[field] = (
                sorted(values)
            )

        result["unique_values"] = (
            unique_values
        )

        return result

    except Exception as exc:

        result["error"] = str(exc)

        return result

    finally:

        if temp_dir is not None:
            temp_dir.cleanup()


# ============================================================
# Source 판정
# ============================================================

def classify_source(
    api_success: bool,
    api_target_rows: List[Dict[str, Any]],
    shp_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:

    shp_hits = []

    if shp_result:

        shp_hits = shp_result.get(
            "target_matches",
            [],
        )

    # 실제 Feature 문자열에서 직접 확인
    if api_target_rows or shp_hits:

        return {
            "source_status":
                "FEATURE_SEMANTIC_CONFIRMED",

            "source_role":
                "PARENT_LAYER_WITH_TARGET_FEATURE",

            "dataset_code":
                DATASET_CODE,

            "reason": (
                "서울시 기타용도구역 UQ145 "
                "실제 Feature 속성에서 "
                "입체복합구역 명칭을 직접 확인함. "
                "다음 단계에서 해당 Feature만 "
                "필터링하여 Parcel Polygon과 "
                "공간교차 가능"
            ),
        }

    # API나 SHP는 읽었지만 target 없음.
    #
    # 중요:
    # 이것만으로 SITE FALSE 아님.
    if api_success or (
        shp_result
        and shp_result.get("loaded")
    ):

        return {
            "source_status":
                "PARENT_LAYER_VERIFIED_TARGET_NOT_FOUND",

            "source_role":
                "PARENT_LAYER",

            "dataset_code":
                DATASET_CODE,

            "reason": (
                "서울시 공식 기타용도구역 "
                "UQ145 source 자체는 확인했으나 "
                "현재 조회한 Feature 속성에서 "
                "입체복합구역을 명시적으로 "
                "확인하지 못함. "
                "UQ145 미포함 가능성과 "
                "별도 신규 layer 가능성을 "
                "구분해야 하므로 SITE는 "
                "UNKNOWN 유지"
            ),
        }

    return {
        "source_status":
            "UQ145_NOT_VERIFIED",

        "source_role":
            None,

        "dataset_code":
            DATASET_CODE,

        "reason": (
            "UQ145 OpenAPI 또는 공간파일의 "
            "실제 Feature를 검증하지 못했으므로 "
            "입체복합구역 source를 확정하지 않음"
        ),
    }


# ============================================================
# SITE 판정
# ============================================================

def build_site_resolution(
    source_result: Dict[str, Any],
) -> Dict[str, Any]:

    return {
        "query_status":
            "NOT_QUERIED",

        "resolution":
            "UNKNOWN",

        "confidence":
            "NONE",

        "reason": (
            "현재 단계는 입체복합구역 "
            "source 및 Feature 의미 검증 단계이며 "
            "대상 PNU Parcel Polygon과 "
            "입체복합구역 Polygon 사이의 "
            "실제 공간교차를 수행하지 않았으므로 "
            "TRUE/FALSE를 판정하지 않음"
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    print(
        f"=== {STEP_NAME} ==="
    )

    print()
    print("Query Context 입력:")
    print(QUERY_CONTEXT_PATH)

    print()
    print("이전 Probe 입력:")
    print(PREVIOUS_PROBE_PATH)

    # --------------------------------------------------------
    # 입력
    # --------------------------------------------------------

    context = load_json(
        QUERY_CONTEXT_PATH
    )

    previous = None

    if PREVIOUS_PROBE_PATH.exists():

        previous = load_json(
            PREVIOUS_PROBE_PATH
        )

    site = extract_site(
        context
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print_title("대상 SITE")

    print(
        "SITE ID:",
        site.get("site_id") or "-",
    )

    print(
        "주소:",
        site.get("address") or "-",
    )

    print(
        "용도지역:",
        site.get("zoning") or "-",
    )

    print(
        "PNU:",
        site.get("pnu") or "-",
    )

    # --------------------------------------------------------
    # 공식 Dataset
    # --------------------------------------------------------

    print_title(
        "1. 서울시 기타용도구역 공식 Dataset"
    )

    print(
        "dataset:",
        DATASET_NAME,
    )

    print(
        "공간정보 코드:",
        DATASET_CODE,
    )

    print(
        "CRS:",
        EXPECTED_CRS,
    )

    print(
        "예상 공간파일:"
    )

    print(
        "UQ145_기타용도구역_202602.zip"
    )

    # --------------------------------------------------------
    # OpenAPI
    # --------------------------------------------------------

    print_title(
        "2. UQ145 OpenAPI service 탐색"
    )

    if not SEOUL_OPEN_API_KEY:

        print(
            "SEOUL_OPEN_API_KEY 없음"
        )

        return 1

    selected_service, api_results = (
        probe_services()
    )

    for result in api_results:

        print()
        print_separator("-")

        print(
            "service:",
            result["service"],
        )

        print(
            "HTTP:",
            result["http_status"],
        )

        print(
            "service 객체:",
            result["service_found"],
        )

        print(
            "RESULT.CODE:",
            result["result_code"],
        )

        print(
            "RESULT.MESSAGE:",
            result[
                "result_message"
            ],
        )

        print(
            "전체 데이터 수:",
            result["total_count"],
        )

        print(
            "row 수:",
            len(
                result["rows"]
            ),
        )

        print(
            "success:",
            result["success"],
        )

    print()

    print(
        "검증된 OpenAPI service:",
        selected_service or "미확정",
    )

    # --------------------------------------------------------
    # API Schema
    # --------------------------------------------------------

    api_rows: List[
        Dict[str, Any]
    ] = []

    api_success = False

    api_fields: List[str] = []

    api_matches: List[
        Dict[str, Any]
    ] = []

    if selected_service:

        selected_result = next(
            item
            for item in api_results
            if item["service"]
            == selected_service
        )

        api_rows = selected_result[
            "rows"
        ]

        api_success = (
            selected_result[
                "success"
            ]
        )

        api_fields = collect_fields(
            api_rows
        )

        api_matches = find_target_rows(
            api_rows
        )

        print_title(
            "3. UQ145 OpenAPI Schema / 의미 분석"
        )

        print(
            "필드 수:",
            len(api_fields),
        )

        for field in api_fields:
            print(
                f"- {field}"
            )

        print()

        print(
            "입체복합구역 명시 Row:",
            len(api_matches),
        )

        for index, item in enumerate(
            api_matches,
            start=1,
        ):

            print()
            print_separator("-")

            print(
                f"Match Row {index}"
            )

            print("hits:")

            for hit in item[
                "hits"
            ]:

                print(
                    "  "
                    f"{hit['column']}: "
                    f"{hit['value']}"
                )

            print("row:")

            for key, value in (
                item["row"].items()
            ):

                print(
                    f"  {key}: {value}"
                )

        # 주요 필드 unique
        important_fields = [
            "LBL_NM",
            "FIG_LCLSF_CD",
            "FIG_MCLSF_CD",
            "FIG_SCLSF_CD",
            "FIG_ATRB_CD",
        ]

        print()
        print("주요 속성 고유값:")

        for field in important_fields:

            if field not in api_fields:
                continue

            values = collect_unique_values(
                api_rows,
                field,
            )

            print()
            print(f"[{field}]")

            for value in values:
                print(
                    f"- {value}"
                )

    else:

        print_title(
            "3. UQ145 OpenAPI Schema / 의미 분석"
        )

        print(
            "OpenAPI service 미확정"
        )

    # --------------------------------------------------------
    # SHP
    # --------------------------------------------------------

    print_title(
        "4. UQ145 공간파일 탐색"
    )

    spatial_files = (
        find_uq145_files()
    )

    print(
        "공간파일 후보 수:",
        len(spatial_files),
    )

    for index, path in enumerate(
        spatial_files,
        start=1,
    ):

        print(
            f"{index}. {path}"
        )

    shp_result = None

    if spatial_files:

        selected_file = (
            spatial_files[0]
        )

        print()
        print(
            "선택 파일:",
            selected_file,
        )

        shp_result = inspect_shapefile(
            selected_file
        )

        print_title(
            "5. UQ145 SHP Schema / 의미 분석"
        )

        print(
            "로드 성공:",
            shp_result.get(
                "loaded"
            ),
        )

        print(
            "Feature 수:",
            shp_result.get(
                "feature_count"
            ),
        )

        print(
            "CRS:",
            shp_result.get(
                "crs"
            ),
        )

        print()
        print("컬럼:")

        for col in shp_result.get(
            "columns",
            [],
        ):
            print(
                f"- {col}"
            )

        print()

        matches = shp_result.get(
            "target_matches",
            [],
        )

        print(
            "입체복합구역 명시 Feature:",
            len(matches),
        )

        for index, item in enumerate(
            matches,
            start=1,
        ):

            print()
            print_separator("-")

            print(
                f"Feature {index}"
            )

            for hit in item[
                "hits"
            ]:

                print(
                    f"{hit['column']}: "
                    f"{hit['value']}"
                )

        print()
        print(
            "주요 SHP 속성 고유값:"
        )

        for field, values in (
            shp_result.get(
                "unique_values",
                {},
            ).items()
        ):

            print()
            print(
                f"[{field}]"
            )

            for value in values:
                print(
                    f"- {value}"
                )

        if shp_result.get(
            "error"
        ):

            print()
            print(
                "SHP error:",
                shp_result[
                    "error"
                ],
            )

    else:

        print()
        print(
            "UQ145 ZIP/SHP가 "
            "로컬에 없습니다."
        )

        print()
        print(
            "예상 파일명:"
        )

        print(
            "UQ145_기타용도구역_202602.zip"
        )

        print()
        print(
            "law_data/input 또는 "
            "law_data/spatial에 저장하면 "
            "실제 SHP Feature까지 분석합니다."
        )

    # --------------------------------------------------------
    # Source 의미 판정
    # --------------------------------------------------------

    print_title(
        "6. 입체복합구역 Source 의미 판정"
    )

    source_result = classify_source(
        api_success=api_success,
        api_target_rows=api_matches,
        shp_result=shp_result,
    )

    print(
        "source_status:",
        source_result[
            "source_status"
        ],
    )

    print(
        "source_role:",
        source_result[
            "source_role"
        ],
    )

    print(
        "dataset:",
        source_result[
            "dataset_code"
        ],
    )

    print(
        "reason:",
        source_result[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # SITE 상태
    # --------------------------------------------------------

    print_title(
        "7. 현재 입체복합구역 SITE 판정"
    )

    resolution = (
        build_site_resolution(
            source_result
        )
    )

    print(
        "query_status:",
        resolution[
            "query_status"
        ],
    )

    print(
        "resolution:",
        resolution[
            "resolution"
        ],
    )

    print(
        "confidence:",
        resolution[
            "confidence"
        ],
    )

    print(
        "reason:",
        resolution[
            "reason"
        ],
    )

    # --------------------------------------------------------
    # 검증
    # --------------------------------------------------------

    print_title(
        "C-9-2-6A-1 검증"
    )

    pnu = site.get("pnu")

    checks = {
        "서울 OpenAPI Key 존재":
            bool(
                SEOUL_OPEN_API_KEY
            ),

        "SITE 주소 존재":
            bool(
                site.get("address")
            ),

        "PNU 19자리":
            bool(
                pnu
                and len(pnu) == 19
                and pnu.isdigit()
            ),

        "서울 기타용도구역 코드 UQ145":
            DATASET_CODE
            == "UQ145",

        "OpenAPI 후보 조회 실행":
            len(
                api_results
            )
            == len(
                SERVICE_CANDIDATES
            ),

        "UQ145 source만으로 SITE TRUE 금지":
            resolution[
                "resolution"
            ]
            != "TRUE",

        "UQ145 source만으로 SITE FALSE 금지":
            resolution[
                "resolution"
            ]
            != "FALSE",

        "공간교차 전 UNKNOWN 유지":
            resolution[
                "resolution"
            ]
            == "UNKNOWN",

        "query_status 허용값":
            resolution[
                "query_status"
            ]
            in {
                "NOT_CONNECTED",
                "NOT_QUERIED",
                "QUERY_FAILED",
                "QUERY_SUCCESS",
            },

        "resolution 허용값":
            resolution[
                "resolution"
            ]
            in {
                "TRUE",
                "FALSE",
                "UNKNOWN",
            },

        "confidence 허용값":
            resolution[
                "confidence"
            ]
            in {
                "NONE",
                "MEDIUM",
                "HIGH",
            },
    }

    all_pass = True

    for name, passed in (
        checks.items()
    ):

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{name}: {status}"
        )

        if not passed:
            all_pass = False

    # --------------------------------------------------------
    # 저장
    # --------------------------------------------------------

    output = {
        "step": STEP_NAME,

        "site": site,

        "previous_probe_loaded":
            previous is not None,

        "dataset": {
            "provider":
                "서울특별시",

            "name":
                DATASET_NAME,

            "code":
                DATASET_CODE,

            "crs":
                EXPECTED_CRS,

            "expected_file":
                "UQ145_기타용도구역_202602.zip",
        },

        "openapi": {
            "selected_service":
                selected_service,

            "probe_results":
                api_results,

            "fields":
                api_fields,

            "target_match_count":
                len(api_matches),

            "target_matches":
                api_matches,
        },

        "spatial_files": [
            str(path)
            for path in spatial_files
        ],

        "shapefile":
            shp_result,

        "source_result":
            source_result,

        "site_resolution":
            resolution,

        "checks":
            checks,

        "all_pass":
            all_pass,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print_separator("=")

    print("결과 저장:")
    print(OUTPUT_PATH)

    print_separator("=")

    print()

    if all_pass:

        print(
            "STEP 17-21-C-9-2-6A-1 완료"
        )

        print()

        status = source_result[
            "source_status"
        ]

        if (
            status
            == "FEATURE_SEMANTIC_CONFIRMED"
        ):

            print(
                "UQ145 실제 Feature에서 "
                "입체복합구역을 확인했습니다."
            )

            print()
            print("다음 단계:")
            print(
                "STEP 17-21-C-9-2-6B"
            )

            print(
                "→ 입체복합구역 Feature 필터"
            )

            print(
                "→ Parcel Polygon 재조회"
            )

            print(
                "→ Parcel × 입체복합구역 "
                "Polygon intersection"
            )

        else:

            print(
                "UQ145에서 입체복합구역 "
                "Feature 의미 검증은 "
                "아직 완료되지 않았습니다."
            )

            print()

            print(
                "현재 입체복합구역:"
            )

            print(
                "UNKNOWN"
            )

            print()
            print("다음 단계:")

            print(
                "STEP 17-21-C-9-2-6A-2"
            )

            print(
                "→ 토지이음 공식 "
                "입체복합구역 명칭/관리체계 확인"
            )

            print(
                "→ 서울 도시계획 결정고시 "
                "입체복합구역 지정 사례 탐색"
            )

            print(
                "→ 신규 공간정보 layer "
                "존재 여부 추가 확인"
            )

        return 0

    print(
        "STEP 17-21-C-9-2-6A-1 "
        "검증 미완료"
    )

    return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )