# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-10A
서울시 취락지구 UQ128 공식 source / schema probe

목표
======================================================================
1. 서울 열린데이터광장 공식 OpenAPI upisCUq128을 조회한다.
2. UQ128 취락지구 데이터셋의 정상조회 여부와 속성체계를 검증한다.
3. 로컬 UQ128 SHP/ZIP 존재 여부를 확인한다.
4. SHP가 있으면 CRS / 컬럼 / 라벨 값을 점검한다.
5. geometry source 미확보 시 FALSE로 판정하지 않는다.

판정 원칙
======================================================================
- OpenAPI 조회 실패 -> UNKNOWN
- SHP 없음 -> UNKNOWN
- 문자열 출현만으로 SITE 판정 금지
- 실제 Parcel Polygon intersection 전 TRUE/FALSE 금지
"""

from __future__ import annotations

import json
import os
import tempfile
import zipfile

from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd
import requests

from dotenv import load_dotenv


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-10A "
    "서울시 취락지구 UQ128 공식 source / schema probe"
)


# ============================================================
# 경로
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

LAW_DATA_DIR = (
    BASE_DIR / "law_data"
)

INPUT_DIR = (
    LAW_DATA_DIR / "input"
)

SPATIAL_DIR = (
    LAW_DATA_DIR / "spatial"
)

OUTPUT_DIR = (
    LAW_DATA_DIR / "output"
)

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_settlement_district_source_probe.json"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

SEOUL_OPEN_API_KEY = (
    os.getenv(
        "SEOUL_OPEN_API_KEY"
    )
)


# ============================================================
# 공식 데이터
# ============================================================

TARGET_NAME = "취락지구"
TARGET_DATASET_CODE = "UQ128"
SEOUL_SERVICE_NAME = "upisCUq128"

SEOUL_API_BASE = (
    "http://openapi.seoul.go.kr:8088"
)


# ============================================================
# 공통
# ============================================================

def print_section(
    title: str,
) -> None:

    print()

    print(
        "=" * 78
    )

    print(
        f"=== {title} ==="
    )

    print(
        "=" * 78
    )


def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():
        return {}

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    data: Dict[str, Any],
) -> None:

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open(
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


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(
        value
    ).strip()


# ============================================================
# SITE
# ============================================================

def load_site_context() -> Dict[str, str]:

    payload = load_json(
        QUERY_CONTEXT_PATH
    )

    context = payload.get(
        "query_context",
        {},
    )

    return {
        "site_id": safe_string(
            context.get(
                "site_id"
            )
        ),
        "address": safe_string(
            context.get(
                "address"
            )
        ),
        "pnu": safe_string(
            context.get(
                "pnu"
            )
        ),
    }


# ============================================================
# 서울 OpenAPI
# ============================================================

def query_seoul_openapi() -> Dict[str, Any]:

    if not SEOUL_OPEN_API_KEY:

        return {
            "query_status": (
                "NOT_CONNECTED"
            ),
            "http_status": None,
            "payload": None,
            "reason": (
                "SEOUL_OPEN_API_KEY 없음"
            ),
        }

    url = (
        f"{SEOUL_API_BASE}/"
        f"{SEOUL_OPEN_API_KEY}/"
        f"json/"
        f"{SEOUL_SERVICE_NAME}/"
        f"1/1000/"
    )

    try:

        response = requests.get(
            url,
            timeout=30,
        )

        payload = (
            response.json()
        )

    except Exception as exc:

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "http_status": None,
            "payload": None,
            "reason": str(
                exc
            ),
        }

    return {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "http_status": (
            response.status_code
        ),
        "payload": payload,
        "reason": (
            "서울 OpenAPI 응답 수신"
        ),
    }


def parse_seoul_payload(
    payload: Dict[str, Any],
) -> Dict[str, Any]:

    service = payload.get(
        SEOUL_SERVICE_NAME,
        {},
    )

    result = service.get(
        "RESULT",
        {},
    )

    rows = service.get(
        "row",
        [],
    )

    return {
        "result_code": (
            result.get(
                "CODE"
            )
        ),
        "result_message": (
            result.get(
                "MESSAGE"
            )
        ),
        "total_count": (
            service.get(
                "list_total_count"
            )
        ),
        "rows": rows,
    }


# ============================================================
# UQ128 로컬 파일 탐색
# ============================================================

def find_uq128_files() -> List[Path]:

    result: List[
        Path
    ] = []

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():
            continue

        for pattern in (
            "*UQ128*.zip",
            "*UQ128*.shp",
        ):

            for path in (
                base_dir.rglob(
                    pattern
                )
            ):

                if path not in result:

                    result.append(
                        path
                    )

    result.sort(
        key=lambda p: (
            p.stat().st_mtime
            if p.exists()
            else 0
        ),
        reverse=True,
    )

    return result


def find_shp_inside_folder(
    folder: Path,
) -> Optional[Path]:

    shp_files = list(
        folder.rglob(
            "*.shp"
        )
    )

    if not shp_files:
        return None

    for path in shp_files:

        if (
            "UQ128"
            in path.name.upper()
        ):

            return path

    return shp_files[0]


# ============================================================
# UQ128 SHP 로드
# ============================================================

def load_uq128_layer(
    path: Path,
) -> Dict[str, Any]:

    temp_dir_object = None

    try:

        if (
            path.suffix.lower()
            == ".zip"
        ):

            temp_dir_object = (
                tempfile.TemporaryDirectory()
            )

            temp_path = Path(
                temp_dir_object.name
            )

            with zipfile.ZipFile(
                path,
                "r",
            ) as zf:

                zf.extractall(
                    temp_path
                )

            shp_path = (
                find_shp_inside_folder(
                    temp_path
                )
            )

            if shp_path is None:

                raise RuntimeError(
                    "ZIP 내부 SHP 없음"
                )

        else:

            shp_path = path

        gdf = None

        errors = []

        for encoding in (
            "cp949",
            "windows-949",
            "euc-kr",
            "utf-8",
            None,
        ):

            try:

                if encoding is None:

                    gdf = (
                        gpd.read_file(
                            shp_path
                        )
                    )

                else:

                    gdf = (
                        gpd.read_file(
                            shp_path,
                            encoding=encoding,
                        )
                    )

                break

            except Exception as exc:

                errors.append(
                    f"{encoding}: {exc}"
                )

        if gdf is None:

            raise RuntimeError(
                " | ".join(
                    errors
                )
            )

        original_crs = (
            str(
                gdf.crs
            )
            if gdf.crs
            else None
        )

        columns = [
            str(
                column
            )
            for column
            in gdf.columns
        ]

        label_values = []

        if (
            "DGM_NM"
            in gdf.columns
        ):

            label_values = sorted(
                {
                    safe_string(
                        value
                    )
                    for value
                    in gdf[
                        "DGM_NM"
                    ].tolist()
                    if safe_string(
                        value
                    )
                }
            )

        return {
            "load_success": True,
            "source_path": str(
                path
            ),
            "shp_path": str(
                shp_path
            ),
            "feature_count": len(
                gdf
            ),
            "original_crs": (
                original_crs
            ),
            "columns": columns,
            "label_values": (
                label_values
            ),
        }

    finally:

        if (
            temp_dir_object
            is not None
        ):

            temp_dir_object.cleanup()


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        STEP_NAME
    )

    site = (
        load_site_context()
    )

    print(
        "SITE ID:",
        site.get(
            "site_id"
        ),
    )

    print(
        "주소:",
        site.get(
            "address"
        ),
    )

    print(
        "PNU:",
        site.get(
            "pnu"
        ),
    )

    print(
        "SEOUL_OPEN_API_KEY:",
        (
            "FOUND"
            if SEOUL_OPEN_API_KEY
            else "MISSING"
        ),
    )

    # ========================================================
    # 1. 공식 OpenAPI
    # ========================================================

    print_section(
        "1. 서울시 공식 OpenAPI upisCUq128"
    )

    api_result = (
        query_seoul_openapi()
    )

    print(
        "query_status:",
        api_result.get(
            "query_status"
        ),
    )

    print(
        "HTTP:",
        api_result.get(
            "http_status"
        ),
    )

    parsed_api = {
        "result_code": None,
        "result_message": None,
        "total_count": None,
        "rows": [],
    }

    if isinstance(
        api_result.get(
            "payload"
        ),
        dict,
    ):

        parsed_api = (
            parse_seoul_payload(
                api_result[
                    "payload"
                ]
            )
        )

    print(
        "result_code:",
        parsed_api.get(
            "result_code"
        ),
    )

    print(
        "result_message:",
        parsed_api.get(
            "result_message"
        ),
    )

    print(
        "total_count:",
        parsed_api.get(
            "total_count"
        ),
    )

    rows = (
        parsed_api.get(
            "rows",
            [],
        )
    )

    print(
        "received rows:",
        len(
            rows
        ),
    )

    # ========================================================
    # 2. 속성체계
    # ========================================================

    print_section(
        "2. OpenAPI 속성체계 검증"
    )

    sample_columns = []

    if rows:

        sample_columns = sorted(
            rows[
                0
            ].keys()
        )

    print(
        "columns:",
        sample_columns,
    )

    label_values = sorted(
        {
            safe_string(
                row.get(
                    "LBL_NM"
                )
            )
            for row
            in rows
            if safe_string(
                row.get(
                    "LBL_NM"
                )
            )
        }
    )

    lclass_values = sorted(
        {
            safe_string(
                row.get(
                    "FIG_LCLSF_CD"
                )
            )
            for row
            in rows
            if safe_string(
                row.get(
                    "FIG_LCLSF_CD"
                )
            )
        }
    )

    attribute_values = sorted(
        {
            safe_string(
                row.get(
                    "FIG_ATRB_CD"
                )
            )
            for row
            in rows
            if safe_string(
                row.get(
                    "FIG_ATRB_CD"
                )
            )
        }
    )

    print(
        "LBL_NM:",
        label_values,
    )

    print(
        "FIG_LCLSF_CD:",
        lclass_values,
    )

    print(
        "FIG_ATRB_CD:",
        attribute_values,
    )

    # ========================================================
    # 3. 로컬 SHP
    # ========================================================

    print_section(
        "3. UQ128 로컬 공간파일 탐색"
    )

    uq128_files = (
        find_uq128_files()
    )

    print(
        "found files:",
        len(
            uq128_files
        ),
    )

    for path in uq128_files:

        print(
            "-",
            path,
        )

    shp_result = None

    if uq128_files:

        print_section(
            "4. UQ128 SHP schema 확인"
        )

        shp_result = (
            load_uq128_layer(
                uq128_files[
                    0
                ]
            )
        )

        print(
            "load_success:",
            shp_result.get(
                "load_success"
            ),
        )

        print(
            "feature_count:",
            shp_result.get(
                "feature_count"
            ),
        )

        print(
            "original_crs:",
            shp_result.get(
                "original_crs"
            ),
        )

        print(
            "columns:",
            shp_result.get(
                "columns"
            ),
        )

        print(
            "DGM_NM:",
            shp_result.get(
                "label_values"
            ),
        )

    # ========================================================
    # 4. 상태
    # ========================================================

    print_section(
        "5. 현재 판정 상태"
    )

    api_ok = (
        api_result.get(
            "query_status"
        )
        == "QUERY_SUCCESS"
        and parsed_api.get(
            "result_code"
        )
        == "INFO-000"
    )

    shp_ok = (
        isinstance(
            shp_result,
            dict,
        )
        and shp_result.get(
            "load_success"
        )
        is True
    )

    if (
        api_ok
        and shp_ok
    ):

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "서울시 공식 UQ128 OpenAPI와 "
                "공간파일을 정상 확인함. "
                "다음 단계에서 대상 Parcel Polygon과 "
                "실제 공간교차 필요"
            ),
        }

        next_step = (
            "STEP 17-21-C-9-2-10B "
            "UQ128 Parcel Polygon 실제 공간교차"
        )

    elif api_ok:

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "서울시 공식 UQ128 OpenAPI는 정상 확인했으나 "
                "로컬 공식 공간파일을 찾지 못해 "
                "geometry 판정 불가"
            ),
        }

        next_step = (
            "UQ128_용도지구(취락지구)_202602.zip "
            "공식 파일 확보 후 10B 진행"
        )

    else:

        resolution = {
            "query_status": (
                "QUERY_FAILED"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "서울시 공식 UQ128 OpenAPI 정상성을 "
                "확인하지 못함"
            ),
        }

        next_step = (
            "OpenAPI 오류 진단"
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

    result = {
        "step": STEP_NAME,

        "condition": (
            TARGET_NAME
        ),

        "site": site,

        "official_source": {
            "provider": (
                "서울특별시"
            ),
            "dataset": (
                "서울시 용도지구(취락지구) 공간정보"
            ),
            "dataset_code": (
                TARGET_DATASET_CODE
            ),
            "openapi_service": (
                SEOUL_SERVICE_NAME
            ),
            "official_crs": (
                "EPSG:5174"
            ),
            "official_encoding": (
                "windows-949"
            ),
        },

        "openapi": {
            "query_status": (
                api_result.get(
                    "query_status"
                )
            ),
            "http_status": (
                api_result.get(
                    "http_status"
                )
            ),
            "result_code": (
                parsed_api.get(
                    "result_code"
                )
            ),
            "result_message": (
                parsed_api.get(
                    "result_message"
                )
            ),
            "total_count": (
                parsed_api.get(
                    "total_count"
                )
            ),
            "received_rows": (
                len(
                    rows
                )
            ),
            "label_values": (
                label_values
            ),
            "lclass_values": (
                lclass_values
            ),
            "attribute_values": (
                attribute_values
            ),
            "sample_columns": (
                sample_columns
            ),
        },

        "local_spatial_source": {
            "found_files": [
                str(
                    path
                )
                for path
                in uq128_files
            ],
            "selected": (
                shp_result
            ),
        },

        "resolution": (
            resolution
        ),

        "next_step": (
            next_step
        ),

        "validation": {
            "SEOUL_OPEN_API_KEY 존재": (
                bool(
                    SEOUL_OPEN_API_KEY
                )
            ),
            "공식 UQ128 코드 사용": True,
            "공식 upisCUq128 서비스 사용": True,
            "문자열만으로 SITE 판정 금지": True,
            "geometry 전 TRUE 금지": True,
            "geometry 전 FALSE 금지": True,
        },
    }

    save_json(
        result
    )

    print()

    print(
        "NEXT:",
        next_step,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )