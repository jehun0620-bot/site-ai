# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-5B
서울시 UQ121 경관지구 OpenAPI / SHP schema 분석
자연경관지구 분류 코드 확정 테스트

목표
------------------------------------------------------------
1. 공식 경관지구 코드 UQ121 확인
2. 서울 OpenAPI service 후보를 실제 호출하여 검증
3. 경관지구 전체 row의 속성값 분석
4. '자연경관지구'를 나타내는 명시적 LBL_NM / 코드 확인
5. 로컬 UQ121 ZIP/SHP가 있으면 schema도 병행 분석
6. 자연경관지구 Feature 식별 규칙 확정
7. Parcel 공간교차 전에는 SITE TRUE/FALSE 판정하지 않음
"""

from __future__ import annotations

import json
import os
import re
import sys
import zipfile
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from dotenv import load_dotenv


# ============================================================
# 선택적 geopandas
# ============================================================

try:
    import geopandas as gpd
except Exception:
    gpd = None


# ============================================================
# 경로
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"
INPUT_DIR = LAW_DATA_DIR / "input"
SPATIAL_DIR = LAW_DATA_DIR / "spatial"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

SOURCE_PROBE_PATH = (
    OUTPUT_DIR
    / "seoul_natural_landscape_district_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_natural_landscape_district_schema_test.json"
)


# ============================================================
# 공식 Dataset
# ============================================================

TARGET_CONDITION = "자연경관지구"

OFFICIAL_DATASET_CODE = "UQ121"

OFFICIAL_DATASET_NAME = (
    "서울시 용도지구(경관지구) 공간정보"
)

OFFICIAL_CRS = "EPSG:5174"

OFFICIAL_ENCODING = "cp949"


# 서울 OpenAPI 서비스명은
# 실제 호출 성공 여부로 검증한다.
SERVICE_CANDIDATES = [
    "upiSCUq121",
    "upisCUq121",
    "upiSCUQ121",
]


SEOUL_API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)

REQUEST_TIMEOUT = 30


# ============================================================
# 환경변수
# ============================================================

load_dotenv(BASE_DIR / ".env")

SEOUL_OPEN_API_KEY = os.getenv(
    "SEOUL_OPEN_API_KEY"
)


# ============================================================
# 공통
# ============================================================

def load_json(path: Path) -> Dict[str, Any]:

    if not path.exists():
        raise FileNotFoundError(
            f"입력 파일이 없습니다:\n{path}"
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
            default=str,
        )


def normalize_text(value: Any) -> str:

    if value is None:
        return ""

    text = str(value)

    text = (
        text
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\t", " ")
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


def first_nonempty(
    *values: Any,
) -> Any:

    for value in values:

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return None


# ============================================================
# SITE
# ============================================================

def extract_site_context(
    context: Dict[str, Any],
) -> Dict[str, str]:

    candidates = [
        context,
        context.get("site", {}),
        context.get("query_context", {}),
        context.get("target_site", {}),
    ]

    site_id = None
    address = None
    zoning = None
    pnu = None
    sigungu_code = None

    for item in candidates:

        if not isinstance(
            item,
            dict,
        ):
            continue

        site_id = first_nonempty(
            site_id,
            item.get("site_id"),
            item.get("SITE_ID"),
            item.get("parcel_key"),
        )

        address = first_nonempty(
            address,
            item.get("address"),
            item.get("jibun_address"),
        )

        zoning = first_nonempty(
            zoning,
            item.get("zoning"),
            item.get("use_zone"),
            item.get("land_use_zone"),
        )

        pnu = first_nonempty(
            pnu,
            item.get("pnu"),
            item.get("PNU"),
        )

        sigungu_code = first_nonempty(
            sigungu_code,
            item.get("sigungu_code"),
            item.get("sgg_code"),
        )

    if (
        not sigungu_code
        and isinstance(pnu, str)
        and len(pnu) >= 5
    ):
        sigungu_code = pnu[:5]

    return {
        "site_id": str(site_id or "-"),
        "address": str(address or "-"),
        "zoning": str(zoning or "-"),
        "pnu": str(pnu or "-"),
        "sigungu_code":
            str(sigungu_code or "-"),
    }


# ============================================================
# 서울 OpenAPI
# ============================================================

def call_seoul_api(
    service: str,
    start_index: int = 1,
    end_index: int = 1000,
) -> Dict[str, Any]:

    if not SEOUL_OPEN_API_KEY:

        raise RuntimeError(
            "SEOUL_OPEN_API_KEY를 찾을 수 없습니다."
        )

    url = (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{service}/"
        f"{start_index}/"
        f"{end_index}/"
    )

    try:

        response = requests.get(
            url,
            timeout=REQUEST_TIMEOUT,
        )

        try:
            payload = response.json()
        except Exception:
            payload = {}

        return {
            "url": url,
            "http_status":
                response.status_code,
            "content_type":
                response.headers.get(
                    "Content-Type",
                    "",
                ),
            "payload":
                payload,
            "text_preview":
                response.text[:1000],
            "error":
                None,
        }

    except requests.RequestException as exc:

        return {
            "url": url,
            "http_status":
                None,
            "content_type":
                None,
            "payload":
                {},
            "text_preview":
                "",
            "error":
                str(exc),
        }


def extract_service_object(
    payload: Dict[str, Any],
    service: str,
) -> Optional[Dict[str, Any]]:

    obj = payload.get(service)

    if isinstance(obj, dict):
        return obj

    for key, value in payload.items():

        if (
            str(key).lower()
            == service.lower()
            and isinstance(
                value,
                dict,
            )
        ):
            return value

    return None


def probe_service() -> Dict[str, Any]:

    results = []

    selected = None

    for service in SERVICE_CANDIDATES:

        api = call_seoul_api(
            service,
            1,
            1000,
        )

        obj = extract_service_object(
            api["payload"],
            service,
        )

        code = None
        message = None
        total_count = 0
        rows = []

        if obj:

            result = obj.get(
                "RESULT",
                {},
            )

            code = result.get(
                "CODE"
            )

            message = result.get(
                "MESSAGE"
            )

            total_count = int(
                obj.get(
                    "list_total_count",
                    0,
                )
                or 0
            )

            raw_rows = obj.get(
                "row",
                [],
            )

            if isinstance(
                raw_rows,
                list,
            ):
                rows = raw_rows

        success = (
            api["http_status"] == 200
            and obj is not None
            and code == "INFO-000"
        )

        item = {
            "service":
                service,

            "http_status":
                api["http_status"],

            "service_object_found":
                obj is not None,

            "result_code":
                code,

            "result_message":
                message,

            "total_count":
                total_count,

            "row_count":
                len(rows),

            "success":
                success,

            "rows":
                rows,
        }

        results.append(
            item
        )

        if (
            success
            and selected is None
        ):
            selected = item

    return {
        "results":
            results,

        "selected":
            selected,
    }


# ============================================================
# OpenAPI schema
# ============================================================

def analyze_api_rows(
    rows: List[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    fields = set()

    for row in rows:

        if isinstance(
            row,
            dict,
        ):
            fields.update(
                row.keys()
            )

    key_fields = [
        "OBJT_ID",
        "STUT_FIG_MNG_NO",
        "FIG_LCLSF_CD",
        "FIG_MCLSF_CD",
        "FIG_SCLSF_CD",
        "FIG_ATRB_CD",
        "FIG_RPT_MNG_CD",
        "DCSN_ANCMNT_MNG_CD",
        "LBL_NM",
        "SGG_CD",
        "FLRPLN_NO",
        "STUT_FIG_CRT_DT",
        "AREA",
        "LEN",
    ]

    value_summary = {}

    for field in [
        "FIG_LCLSF_CD",
        "FIG_MCLSF_CD",
        "FIG_SCLSF_CD",
        "FIG_ATRB_CD",
        "LBL_NM",
        "SGG_CD",
    ]:

        values = []

        for row in rows:

            value = normalize_text(
                row.get(
                    field
                )
            )

            if (
                value
                and value not in values
            ):
                values.append(
                    value
                )

        value_summary[field] = (
            sorted(values)
        )

    natural_rows = []

    for row in rows:

        texts = []

        for key, value in row.items():

            if isinstance(
                value,
                (
                    str,
                    int,
                    float,
                ),
            ):

                texts.append(
                    normalize_text(
                        value
                    )
                )

        joined = " ".join(
            texts
        )

        if "자연경관지구" in joined:

            natural_rows.append(
                row
            )

    return {
        "fields":
            sorted(fields),

        "expected_fields_present":
            {
                key:
                    key in fields
                for key in key_fields
            },

        "value_summary":
            value_summary,

        "natural_landscape_rows":
            natural_rows,

        "natural_landscape_row_count":
            len(
                natural_rows
            ),
    }


# ============================================================
# SHP 탐색
# ============================================================

def find_uq121_files() -> List[Path]:

    result: List[Path] = []

    patterns = [
        "UQ121*.zip",
        "*UQ121*.zip",
        "UQ121*.shp",
        "*UQ121*.shp",
    ]

    for base in [
        INPUT_DIR,
        SPATIAL_DIR,
    ]:

        if not base.exists():
            continue

        for pattern in patterns:

            for path in base.rglob(
                pattern
            ):

                if (
                    path not in result
                ):
                    result.append(
                        path
                    )

    result.sort(
        key=lambda p:
            p.stat().st_mtime
            if p.exists()
            else 0,
        reverse=True,
    )

    return result


def find_shp_in_folder(
    folder: Path,
) -> Optional[Path]:

    shp_files = list(
        folder.rglob(
            "*.shp"
        )
    )

    if not shp_files:
        return None

    # UQ121 문자열 포함 파일 우선
    for shp in shp_files:

        if (
            "UQ121"
            in shp.name.upper()
        ):
            return shp

    return shp_files[0]


def load_spatial_file(
    source_path: Path,
) -> Dict[str, Any]:

    if gpd is None:

        return {
            "success":
                False,

            "reason":
                "geopandas를 import할 수 없음",

            "source_path":
                str(source_path),
        }

    temp_dir_obj = None

    try:

        if (
            source_path.suffix.lower()
            == ".zip"
        ):

            temp_dir_obj = (
                tempfile.TemporaryDirectory()
            )

            temp_dir = Path(
                temp_dir_obj.name
            )

            with zipfile.ZipFile(
                source_path,
                "r",
            ) as zf:

                zf.extractall(
                    temp_dir
                )

            shp_path = find_shp_in_folder(
                temp_dir
            )

            if shp_path is None:

                return {
                    "success":
                        False,

                    "reason":
                        "ZIP 내부 SHP 없음",

                    "source_path":
                        str(source_path),
                }

        else:

            shp_path = source_path

        # encoding windows-949
        try:

            gdf = gpd.read_file(
                shp_path,
                encoding=OFFICIAL_ENCODING,
            )

        except Exception:

            # 일부 GDAL 환경은 euc-kr로 읽어야 할 수 있음
            gdf = gpd.read_file(
                shp_path,
                encoding="euc-kr",
            )

        original_crs = (
            str(gdf.crs)
            if gdf.crs
            else None
        )

        columns = [
            str(c)
            for c in
            gdf.columns
        ]

        geom_types = []

        if (
            "geometry"
            in gdf.columns
        ):

            geom_types = sorted(
                {
                    str(v)
                    for v in
                    gdf.geometry.geom_type
                    .dropna()
                    .tolist()
                }
            )

        return {
            "success":
                True,

            "source_path":
                str(source_path),

            "shp_path":
                str(shp_path),

            "feature_count":
                len(gdf),

            "crs":
                original_crs,

            "columns":
                columns,

            "geometry_types":
                geom_types,

            "gdf":
                gdf,
        }

    finally:

        # gdf 분석 전 temp 제거 방지를 위해
        # 반환 직전에는 실제 데이터를 메모리에 이미 로드함
        if temp_dir_obj is not None:
            temp_dir_obj.cleanup()


# ============================================================
# SHP 속성 분석
# ============================================================

def analyze_gdf(
    gdf,
) -> Dict[str, Any]:

    columns = [
        str(c)
        for c in
        gdf.columns
    ]

    string_columns = []

    for column in columns:

        if column == "geometry":
            continue

        try:

            dtype = str(
                gdf[column].dtype
            )

            if (
                "object"
                in dtype.lower()
                or "string"
                in dtype.lower()
            ):
                string_columns.append(
                    column
                )

        except Exception:
            pass

    natural_indexes = []

    natural_rows_preview = []

    for index, row in (
        gdf.iterrows()
    ):

        found = False

        for column in columns:

            if column == "geometry":
                continue

            value = normalize_text(
                row.get(
                    column
                )
            )

            if (
                "자연경관지구"
                in value
            ):

                found = True
                break

        if found:

            natural_indexes.append(
                index
            )

            preview = {}

            for column in columns:

                if column == "geometry":
                    continue

                value = row.get(
                    column
                )

                if (
                    value is not None
                    and normalize_text(
                        value
                    )
                ):

                    preview[column] = (
                        normalize_text(
                            value
                        )
                    )

            natural_rows_preview.append(
                preview
            )

    unique_values = {}

    for column in string_columns:

        values = []

        try:

            raw = (
                gdf[column]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            for value in raw:

                norm = normalize_text(
                    value
                )

                if (
                    norm
                    and norm not in values
                ):
                    values.append(
                        norm
                    )

            unique_values[
                column
            ] = sorted(
                values
            )[:200]

        except Exception:
            pass

    return {
        "columns":
            columns,

        "string_columns":
            string_columns,

        "unique_values":
            unique_values,

        "natural_landscape_feature_count":
            len(
                natural_indexes
            ),

        "natural_landscape_feature_indexes":
            [
                str(v)
                for v in
                natural_indexes
            ],

        "natural_landscape_preview":
            natural_rows_preview[
                :20
            ],
    }


# ============================================================
# 식별 규칙
# ============================================================

def derive_filter_rule(
    api_analysis: Dict[
        str,
        Any,
    ],
    shp_analysis: Optional[
        Dict[
            str,
            Any,
        ]
    ],
) -> Dict[str, Any]:

    candidates = []

    # OpenAPI에서 직접 자연경관지구 row 발견
    for row in api_analysis.get(
        "natural_landscape_rows",
        [],
    ):

        for field in [
            "LBL_NM",
            "FIG_LCLSF_CD",
            "FIG_MCLSF_CD",
            "FIG_SCLSF_CD",
            "FIG_ATRB_CD",
        ]:

            value = normalize_text(
                row.get(
                    field
                )
            )

            if value:

                candidates.append(
                    {
                        "source":
                            "OPEN_API",

                        "field":
                            field,

                        "value":
                            value,

                        "explicit_text":
                            (
                                "자연경관지구"
                                in value
                            ),
                    }
                )

    # SHP에서 자연경관지구 행 발견
    if shp_analysis:

        for row in shp_analysis.get(
            "natural_landscape_preview",
            [],
        ):

            for field, value in (
                row.items()
            ):

                text = normalize_text(
                    value
                )

                if text:

                    candidates.append(
                        {
                            "source":
                                "SHP",

                            "field":
                                field,

                            "value":
                                text,

                            "explicit_text":
                                (
                                    "자연경관지구"
                                    in text
                                ),
                        }
                    )

    # 중복 제거
    unique = []

    seen = set()

    for item in candidates:

        key = (
            item["source"],
            item["field"],
            item["value"],
        )

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    explicit = [
        item
        for item in unique
        if item[
            "explicit_text"
        ]
    ]

    if explicit:

        # 가장 안전한 규칙:
        # 자연경관지구 문자열 직접 일치
        return {
            "status":
                "VERIFIED",

            "rule_type":
                "EXPLICIT_TEXT",

            "rules":
                explicit,

            "reason":
                "공식 UQ121 데이터의 실제 Feature 속성에서 "
                "'자연경관지구' 문자열을 직접 확인함",
        }

    return {
        "status":
            "UNRESOLVED",

        "rule_type":
            None,

        "rules":
            unique,

        "reason":
            "UQ121 source는 확인했으나 자연경관지구를 "
            "직접 식별할 수 있는 명시적 속성값을 아직 "
            "확정하지 못함",
    }


# ============================================================
# validation
# ============================================================

def build_validation(
    site: Dict[str, str],
    service_probe: Dict[
        str,
        Any,
    ],
    api_analysis: Optional[
        Dict[
            str,
            Any,
        ]
    ],
    spatial_files: List[Path],
    spatial_result: Optional[
        Dict[
            str,
            Any,
        ]
    ],
    filter_rule: Dict[
        str,
        Any,
    ],
) -> Dict[str, bool]:

    selected = (
        service_probe.get(
            "selected"
        )
    )

    pnu = site[
        "pnu"
    ]

    return {
        "서울 OpenAPI Key 존재":
            bool(
                SEOUL_OPEN_API_KEY
            ),

        "SITE 주소 존재":
            site[
                "address"
            ]
            not in (
                "",
                "-",
            ),

        "PNU 19자리":
            (
                len(pnu) == 19
                and pnu.isdigit()
            ),

        "공식 경관지구 코드 UQ121":
            OFFICIAL_DATASET_CODE
            == "UQ121",

        "OpenAPI service 후보 조회 실행":
            len(
                service_probe[
                    "results"
                ]
            ) > 0,

        "OpenAPI service 성공 시 schema 분석":
            (
                selected is None
                or api_analysis
                is not None
            ),

        "SHP 미확보만으로 FALSE 판정 없음":
            True,

        "자연경관지구 분류 미확정 시 SITE UNKNOWN":
            True,

        "경관지구 전체를 자연경관지구로 자동 간주하지 않음":
            True,

        "필터 규칙은 실제 Feature 속성 기반":
            (
                filter_rule[
                    "status"
                ]
                in (
                    "VERIFIED",
                    "UNRESOLVED",
                )
            ),
    }


# ============================================================
# main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-5B "
        "서울시 UQ121 경관지구 Schema / "
        "자연경관지구 분류값 검증 ==="
    )

    print()

    print(
        "Query Context 입력:"
    )
    print(
        QUERY_CONTEXT_PATH
    )

    print()

    print(
        "Source Probe 입력:"
    )
    print(
        SOURCE_PROBE_PATH
    )

    context = load_json(
        QUERY_CONTEXT_PATH
    )

    source_probe = load_json(
        SOURCE_PROBE_PATH
    )

    site = extract_site_context(
        context
    )

    # --------------------------------------------------------
    # SITE
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 대상 SITE ==="
    )
    print(
        "=" * 70
    )

    print(
        "SITE ID:",
        site["site_id"],
    )

    print(
        "주소:",
        site["address"],
    )

    print(
        "용도지역:",
        site["zoning"],
    )

    print(
        "PNU:",
        site["pnu"],
    )

    # --------------------------------------------------------
    # 공식 dataset
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 1. 공식 경관지구 Dataset ==="
    )
    print(
        "=" * 70
    )

    print(
        "dataset:",
        OFFICIAL_DATASET_NAME,
    )

    print(
        "공간정보 코드:",
        OFFICIAL_DATASET_CODE,
    )

    print(
        "공간파일 CRS:",
        OFFICIAL_CRS,
    )

    print(
        "공간파일 인코딩:",
        "windows-949",
    )

    # --------------------------------------------------------
    # OpenAPI
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 2. 경관지구 OpenAPI "
        "service 검증 ==="
    )
    print(
        "=" * 70
    )

    service_probe = (
        probe_service()
    )

    for item in (
        service_probe[
            "results"
        ]
    ):

        print()
        print(
            "-" * 70
        )

        print(
            "service:",
            item[
                "service"
            ],
        )

        print(
            "HTTP:",
            item[
                "http_status"
            ],
        )

        print(
            "service 객체:",
            item[
                "service_object_found"
            ],
        )

        print(
            "RESULT.CODE:",
            item[
                "result_code"
            ],
        )

        print(
            "RESULT.MESSAGE:",
            item[
                "result_message"
            ],
        )

        print(
            "전체 데이터 수:",
            item[
                "total_count"
            ],
        )

        print(
            "row 수:",
            item[
                "row_count"
            ],
        )

        print(
            "success:",
            item[
                "success"
            ],
        )

    selected = (
        service_probe[
            "selected"
        ]
    )

    api_analysis = None

    if selected:

        print()
        print(
            "검증된 OpenAPI service:"
        )

        print(
            selected[
                "service"
            ]
        )

        api_analysis = (
            analyze_api_rows(
                selected[
                    "rows"
                ]
            )
        )

        # ----------------------------------------------------
        # API schema
        # ----------------------------------------------------

        print()
        print(
            "=" * 70
        )
        print(
            "=== 3. OpenAPI Schema / "
            "분류값 분석 ==="
        )
        print(
            "=" * 70
        )

        print(
            "필드 수:",
            len(
                api_analysis[
                    "fields"
                ]
            ),
        )

        for field in (
            api_analysis[
                "fields"
            ]
        ):

            print(
                "-",
                field,
            )

        print()

        print(
            "주요 속성 고유값:"
        )

        for field, values in (
            api_analysis[
                "value_summary"
            ].items()
        ):

            print()
            print(
                f"[{field}]"
            )

            for value in values:

                print(
                    "-",
                    value,
                )

        print()
        print(
            "자연경관지구 명시 Row:",
            api_analysis[
                "natural_landscape_row_count"
            ],
        )

        for index, row in enumerate(
            api_analysis[
                "natural_landscape_rows"
            ],
            start=1,
        ):

            print()
            print(
                "-" * 70
            )

            print(
                f"자연경관지구 Row {index}"
            )

            for key, value in (
                row.items()
            ):

                print(
                    f"{key}: "
                    f"{value}"
                )

    else:

        print()
        print(
            "OpenAPI service를 "
            "확정하지 못했습니다."
        )

    # --------------------------------------------------------
    # 공간파일
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 4. UQ121 공간파일 탐색 ==="
    )
    print(
        "=" * 70
    )

    spatial_files = (
        find_uq121_files()
    )

    print(
        "공간파일 후보 수:",
        len(
            spatial_files
        ),
    )

    for index, path in enumerate(
        spatial_files,
        start=1,
    ):

        print(
            f"{index}. {path}"
        )

    spatial_result = None
    shp_analysis = None

    if spatial_files:

        selected_file = (
            spatial_files[0]
        )

        print()
        print(
            "선택 공간파일:"
        )
        print(
            selected_file
        )

        spatial_result = (
            load_spatial_file(
                selected_file
            )
        )

        print()

        print(
            "공간레이어 로드:",
            spatial_result[
                "success"
            ],
        )

        print(
            "reason:",
            spatial_result.get(
                "reason",
                "-",
            ),
        )

        if spatial_result[
            "success"
        ]:

            print(
                "Feature 수:",
                spatial_result[
                    "feature_count"
                ],
            )

            print(
                "CRS:",
                spatial_result[
                    "crs"
                ],
            )

            print(
                "Geometry type:",
                ", ".join(
                    spatial_result[
                        "geometry_types"
                    ]
                ),
            )

            print(
                "컬럼:"
            )

            for column in (
                spatial_result[
                    "columns"
                ]
            ):

                print(
                    "-",
                    column,
                )

            shp_analysis = (
                analyze_gdf(
                    spatial_result[
                        "gdf"
                    ]
                )
            )

            print()
            print(
                "=" * 70
            )
            print(
                "=== 5. SHP 자연경관지구 "
                "속성 분석 ==="
            )
            print(
                "=" * 70
            )

            print(
                "자연경관지구 Feature:",
                shp_analysis[
                    "natural_landscape_feature_count"
                ],
            )

            print()

            print(
                "문자형 컬럼별 고유값:"
            )

            for column, values in (
                shp_analysis[
                    "unique_values"
                ].items()
            ):

                print()
                print(
                    f"[{column}]"
                )

                for value in values:

                    print(
                        "-",
                        value,
                    )

            if (
                shp_analysis[
                    "natural_landscape_preview"
                ]
            ):

                print()

                print(
                    "자연경관지구 Feature 예시:"
                )

                for index, row in enumerate(
                    shp_analysis[
                        "natural_landscape_preview"
                    ],
                    start=1,
                ):

                    print()
                    print(
                        "-" * 70
                    )

                    print(
                        f"Feature {index}"
                    )

                    for key, value in (
                        row.items()
                    ):

                        print(
                            f"{key}: "
                            f"{value}"
                        )

    else:

        print()
        print(
            "UQ121 ZIP/SHP가 로컬에 없습니다."
        )

        print(
            "예상 파일명:"
        )

        print(
            "UQ121_용도지구(경관지구)_202602.zip"
        )

        print()
        print(
            "law_data/input 또는 "
            "law_data/spatial에 저장하면 "
            "SHP schema 분석도 함께 수행합니다."
        )

    # --------------------------------------------------------
    # Filter rule
    # --------------------------------------------------------

    if api_analysis is None:

        api_analysis = {
            "natural_landscape_rows":
                [],
        }

    filter_rule = (
        derive_filter_rule(
            api_analysis,
            shp_analysis,
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== 6. 자연경관지구 "
        "Feature 식별 규칙 ==="
    )
    print(
        "=" * 70
    )

    print(
        "status:",
        filter_rule[
            "status"
        ],
    )

    print(
        "rule_type:",
        filter_rule[
            "rule_type"
        ]
        or "-",
    )

    print(
        "reason:",
        filter_rule[
            "reason"
        ],
    )

    if filter_rule[
        "rules"
    ]:

        print()

        for rule in (
            filter_rule[
                "rules"
            ]
        ):

            print(
                "- "
                f"{rule['source']} / "
                f"{rule['field']} = "
                f"{rule['value']}"
            )

    # --------------------------------------------------------
    # SITE 판정
    # --------------------------------------------------------

    print()
    print(
        "=" * 70
    )
    print(
        "=== 7. 현재 자연경관지구 "
        "SITE 판정 ==="
    )
    print(
        "=" * 70
    )

    print(
        "query_status: NOT_QUERIED"
    )

    print(
        "resolution: UNKNOWN"
    )

    print(
        "confidence: NONE"
    )

    print(
        "reason: 자연경관지구 Feature 식별 규칙 "
        "분석 단계이며 대상 Parcel Polygon과 "
        "공간교차를 아직 수행하지 않았으므로 "
        "TRUE/FALSE를 판정하지 않음"
    )

    # --------------------------------------------------------
    # validation
    # --------------------------------------------------------

    validation = (
        build_validation(
            site,
            service_probe,
            api_analysis,
            spatial_files,
            spatial_result,
            filter_rule,
        )
    )

    print()
    print(
        "=" * 70
    )
    print(
        "=== C-9-2-5B 검증 ==="
    )
    print(
        "=" * 70
    )

    for key, value in (
        validation.items()
    ):

        print(
            f"{key}: "
            f"{'PASS' if value else 'FAIL'}"
        )

    # --------------------------------------------------------
    # 저장용 spatial result 정리
    # --------------------------------------------------------

    serializable_spatial = None

    if spatial_result:

        serializable_spatial = {
            key:
                value
            for key, value
            in spatial_result.items()
            if key != "gdf"
        }

    output = {
        "step":
            "STEP 17-21-C-9-2-5B",

        "condition":
            TARGET_CONDITION,

        "official_source": {
            "dataset_name":
                OFFICIAL_DATASET_NAME,

            "dataset_code":
                OFFICIAL_DATASET_CODE,

            "crs":
                OFFICIAL_CRS,

            "encoding":
                "windows-949",
        },

        "site":
            site,

        "source_probe_input":
            source_probe,

        "openapi_probe":
            service_probe,

        "api_analysis":
            api_analysis,

        "spatial_files":
            [
                str(v)
                for v in
                spatial_files
            ],

        "spatial_result":
            serializable_spatial,

        "shp_analysis":
            shp_analysis,

        "filter_rule":
            filter_rule,

        "site_resolution": {
            "query_status":
                "NOT_QUERIED",

            "resolution":
                "UNKNOWN",

            "confidence":
                "NONE",

            "reason":
                "자연경관지구 Feature 식별 규칙 "
                "검증 단계로 Parcel Polygon과의 "
                "실제 공간교차는 아직 수행하지 않음",
        },

        "validation":
            validation,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print(
        "=" * 70
    )
    print(
        "결과 저장:"
    )
    print(
        OUTPUT_PATH
    )
    print(
        "=" * 70
    )

    if all(
        validation.values()
    ):

        print()
        print(
            "STEP 17-21-C-9-2-5B 완료"
        )

        if (
            filter_rule[
                "status"
            ]
            == "VERIFIED"
        ):

            print()

            print(
                "자연경관지구 Feature "
                "식별 규칙 검증 성공"
            )

            print()

            print(
                "다음 단계:"
            )

            print(
                "STEP 17-21-C-9-2-5C"
            )

            print(
                "→ UQ121 경관지구 Polygon 로드"
            )

            print(
                "→ 자연경관지구 Feature만 필터"
            )

            print(
                "→ 기존 PNU Parcel Polygon 재조회"
            )

            print(
                "→ Parcel × 자연경관지구 "
                "Polygon intersection"
            )

            print(
                "→ 실제 교차 시 TRUE"
            )

            print(
                "→ 전체 자연경관지구 layer "
                "정상조회 + 교차 없음 시 FALSE"
            )

        else:

            print()

            print(
                "자연경관지구 Feature "
                "분류 규칙이 아직 미확정입니다."
            )

            print(
                "SITE resolution: UNKNOWN"
            )

            print()

            print(
                "OpenAPI row 또는 UQ121 SHP "
                "속성값을 추가 분석해야 합니다."
            )

    else:

        print()
        print(
            "STEP 17-21-C-9-2-5B "
            "검증 미완료"
        )


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        print()
        print(
            "사용자에 의해 중단되었습니다."
        )

        sys.exit(130)

    except Exception as exc:

        print()
        print(
            "=" * 70
        )
        print(
            "ERROR"
        )
        print(
            "=" * 70
        )

        print(
            f"{type(exc).__name__}: "
            f"{exc}"
        )

        raise