# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-10B
서울시 UQ128 취락지구 Parcel Polygon 실제 공간교차 검증

목표
======================================================================
1. 서울시 공식 UQ128 취락지구 SHP를 정상 로드한다.
2. OpenAPI에서 검증한 UQM120 코드체계를 SHP에서도 확인한다.
3. 대상 PNU Parcel Polygon을 VWorld에서 직접 확보한다.
4. Parcel과 UQ128을 동일 CRS로 정규화한다.
5. 실제 Polygon 면적교차를 계산한다.
6. 실제 면적교차 > 0 이면 TRUE / HIGH.
7. 공식 전체 공간레이어 정상 + 실제 면적교차 없음이면 FALSE / HIGH.

판정 원칙
======================================================================
- 문자열 출현만으로 SITE 조건 판정 금지
- Point 포함만으로 TRUE 금지
- Parcel Polygon intersection 우선
- 경계 접촉(area = 0)은 TRUE가 아님
- UQ128 layer 또는 Parcel geometry 로드 실패 -> UNKNOWN
- 코드/schema 검증 실패 -> UNKNOWN
- 전체 공식 layer 정상조회 + 유효한 공간비교 + 교차 없음 -> FALSE
"""

from __future__ import annotations

import json
import os
import tempfile
import zipfile

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import geopandas as gpd
import requests

from dotenv import load_dotenv

from shapely.geometry import shape
from shapely.geometry.base import BaseGeometry


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-10B "
    "서울시 UQ128 취락지구 Parcel Polygon 실제 공간교차"
)


# ============================================================
# 프로젝트 경로
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

SOURCE_PROBE_PATH = (
    OUTPUT_DIR
    / "seoul_settlement_district_source_probe.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_settlement_district_intersection.json"
)


# ============================================================
# Dataset
# ============================================================

PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)

TARGET_CONDITION = (
    "취락지구"
)

UQ128_CODE = (
    "UQ128"
)

EXPECTED_CLASS_CODE = (
    "UQM120"
)

EXPECTED_CRS = (
    "EPSG:5174"
)


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

VWORLD_API_KEY = (
    os.getenv(
        "VWORLD_API_KEY"
    )
)


# ============================================================
# VWorld
# ============================================================

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

REQUEST_TIMEOUT = 30


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
# SITE Context
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
# VWorld 대표좌표
# ============================================================

def get_site_point(
    address: str,
) -> Optional[
    Tuple[
        float,
        float,
    ]
]:

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
        "key": VWORLD_API_KEY,
    }

    try:

        response = requests.get(
            VWORLD_SEARCH_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        payload = (
            response.json()
        )

    except Exception:

        return None

    body = payload.get(
        "response",
        {},
    )

    if (
        body.get(
            "status"
        )
        != "OK"
    ):

        return None

    items = (
        body
        .get(
            "result",
            {},
        )
        .get(
            "items",
            [],
        )
    )

    if not items:

        return None

    point = items[
        0
    ].get(
        "point",
        {},
    )

    try:

        return (
            float(
                point["x"]
            ),
            float(
                point["y"]
            ),
        )

    except Exception:

        return None


# ============================================================
# VWorld Parcel Polygon
# ============================================================

def query_parcel_polygon(
    x: float,
    y: float,
    pnu: str,
) -> Dict[str, Any]:

    params = {
        "service": "data",
        "request": "GetFeature",
        "data": PARCEL_DATASET,
        "key": VWORLD_API_KEY,
        "domain": "localhost",
        "format": "json",
        "geometry": "true",
        "attribute": "true",
        "crs": "EPSG:4326",
        "geomFilter": (
            f"POINT({x} {y})"
        ),
        "size": 100,
    }

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        payload = (
            response.json()
        )

    except Exception as exc:

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "raw_feature_count": 0,
            "features": [],
            "reason": (
                "VWorld Parcel API 호출 실패: "
                f"{exc}"
            ),
        }

    body = payload.get(
        "response",
        {},
    )

    if (
        body.get(
            "status"
        )
        != "OK"
    ):

        return {
            "query_status": (
                "QUERY_FAILED"
            ),
            "raw_feature_count": 0,
            "features": [],
            "reason": (
                "VWorld Parcel API status="
                f"{body.get('status')}"
            ),
        }

    features = (
        body
        .get(
            "result",
            {},
        )
        .get(
            "featureCollection",
            {},
        )
        .get(
            "features",
            [],
        )
    )

    matched = []

    for feature in features:

        properties = (
            feature.get(
                "properties",
                {},
            )
        )

        feature_pnu = (
            safe_string(
                properties.get(
                    "pnu"
                )
            )
        )

        if (
            feature_pnu
            != pnu
        ):

            continue

        geometry = (
            feature.get(
                "geometry"
            )
        )

        if not geometry:

            continue

        try:

            geom = shape(
                geometry
            )

        except Exception:

            continue

        if geom.is_empty:

            continue

        if (
            geom.geom_type
            not in (
                "Polygon",
                "MultiPolygon",
            )
        ):

            continue

        matched.append(
            {
                "id": (
                    feature.get(
                        "id"
                    )
                ),
                "properties": (
                    properties
                ),
                "geometry": (
                    geom
                ),
            }
        )

    return {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "raw_feature_count": (
            len(
                features
            )
        ),
        "features": (
            matched
        ),
        "reason": (
            "대상 PNU Parcel Polygon 조회 완료"
        ),
    }


# ============================================================
# UQ128 파일 탐색
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

                if (
                    path
                    not in result
                ):

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

    return shp_files[
        0
    ]


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
                    "UQ128 ZIP 내부 SHP 파일을 찾지 못함"
                )

        else:

            shp_path = path

        gdf = None

        read_errors = []

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

                read_errors.append(
                    f"{encoding}: {exc}"
                )

        if gdf is None:

            raise RuntimeError(
                "UQ128 SHP 로드 실패: "
                + " | ".join(
                    read_errors
                )
            )

        original_crs = (
            str(
                gdf.crs
            )
            if gdf.crs
            else None
        )

        crs_source = (
            "FILE_METADATA"
        )

        if gdf.crs is None:

            gdf = gdf.set_crs(
                EXPECTED_CRS,
                allow_override=True,
            )

            crs_source = (
                "OFFICIAL_DEFAULT_EPSG5174"
            )

        gdf = (
            gdf.copy()
        )

        return {
            "gdf": gdf,
            "source_path": str(
                path
            ),
            "shp_path": str(
                shp_path
            ),
            "feature_count": (
                len(
                    gdf
                )
            ),
            "original_crs": (
                original_crs
            ),
            "effective_crs": str(
                gdf.crs
            ),
            "crs_source": (
                crs_source
            ),
            "columns": [
                str(
                    column
                )
                for column
                in gdf.columns
            ],
        }

    finally:

        if (
            temp_dir_object
            is not None
        ):

            temp_dir_object.cleanup()


# ============================================================
# UQ128 schema / code 검증
# ============================================================

def validate_uq128_schema(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    required_columns = [
        "LCLAS_CL",
        "ATRB_SE",
        "DGM_NM",
        "geometry",
    ]

    missing_columns = [
        column
        for column
        in required_columns
        if column
        not in gdf.columns
    ]

    if missing_columns:

        return {
            "verified": False,
            "missing_columns": (
                missing_columns
            ),
            "reason": (
                "필수 컬럼 누락"
            ),
        }

    lclass_values = sorted(
        {
            safe_string(
                value
            )
            for value
            in gdf[
                "LCLAS_CL"
            ].tolist()
            if safe_string(
                value
            )
        }
    )

    attribute_values = sorted(
        {
            safe_string(
                value
            )
            for value
            in gdf[
                "ATRB_SE"
            ].tolist()
            if safe_string(
                value
            )
        }
    )

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

    lclass_all_expected = (
        bool(
            lclass_values
        )
        and all(
            value
            == EXPECTED_CLASS_CODE
            for value
            in lclass_values
        )
    )

    attribute_all_expected = (
        bool(
            attribute_values
        )
        and all(
            value
            == EXPECTED_CLASS_CODE
            for value
            in attribute_values
        )
    )

    geometry_valid_count = int(
        (
            gdf.geometry.notna()
            & ~gdf.geometry.is_empty
        ).sum()
    )

    verified = (
        lclass_all_expected
        and attribute_all_expected
        and geometry_valid_count
        == len(
            gdf
        )
    )

    return {
        "verified": (
            verified
        ),
        "feature_count": (
            len(
                gdf
            )
        ),
        "LCLAS_CL_values": (
            lclass_values
        ),
        "ATRB_SE_values": (
            attribute_values
        ),
        "DGM_NM_values": (
            label_values
        ),
        "LCLAS_CL_all_UQM120": (
            lclass_all_expected
        ),
        "ATRB_SE_all_UQM120": (
            attribute_all_expected
        ),
        "geometry_valid_count": (
            geometry_valid_count
        ),
        "reason": (
            "UQ128 SHP 코드/schema 정상"
            if verified
            else "UQ128 SHP 코드/schema 검증 실패"
        ),
    }


# ============================================================
# 공간교차
# ============================================================

def calculate_intersections(
    parcel: BaseGeometry,
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    parcel_area = float(
        parcel.area
    )

    parcel_bounds = (
        parcel.bounds
    )

    bbox_candidate_count = 0

    intersection_count = 0

    positive_area_count = 0

    max_ratio = 0.0

    feature_results = []

    for index, row in (
        gdf.iterrows()
    ):

        geometry = (
            row.geometry
        )

        if geometry is None:

            continue

        if geometry.is_empty:

            continue

        geometry_bounds = (
            geometry.bounds
        )

        # ----------------------------------------------------
        # cheap bbox pre-filter
        # ----------------------------------------------------

        bbox_intersects = not (
            geometry_bounds[2]
            < parcel_bounds[0]
            or geometry_bounds[0]
            > parcel_bounds[2]
            or geometry_bounds[3]
            < parcel_bounds[1]
            or geometry_bounds[1]
            > parcel_bounds[3]
        )

        if not bbox_intersects:

            continue

        bbox_candidate_count += 1

        if not parcel.intersects(
            geometry
        ):

            continue

        intersection_count += 1

        intersection = (
            parcel.intersection(
                geometry
            )
        )

        intersection_area = float(
            intersection.area
        )

        if (
            parcel_area
            > 0
        ):

            ratio = (
                intersection_area
                / parcel_area
            )

        else:

            ratio = 0.0

        if (
            intersection_area
            > 0
        ):

            positive_area_count += 1

        if (
            ratio
            > max_ratio
        ):

            max_ratio = ratio

        feature_results.append(
            {
                "index": (
                    int(index)
                    if isinstance(
                        index,
                        int,
                    )
                    else str(
                        index
                    )
                ),
                "DGM_NM": safe_string(
                    row.get(
                        "DGM_NM"
                    )
                ),
                "LCLAS_CL": safe_string(
                    row.get(
                        "LCLAS_CL"
                    )
                ),
                "ATRB_SE": safe_string(
                    row.get(
                        "ATRB_SE"
                    )
                ),
                "geometry_type": (
                    geometry.geom_type
                ),
                "intersects": True,
                "intersection_area": (
                    intersection_area
                ),
                "parcel_intersection_ratio": (
                    ratio
                ),
                "boundary_only": (
                    intersection_area
                    <= 0
                ),
            }
        )

    return {
        "bbox_candidate_count": (
            bbox_candidate_count
        ),
        "intersection_count": (
            intersection_count
        ),
        "positive_area_intersection_count": (
            positive_area_count
        ),
        "max_intersection_ratio": (
            max_ratio
        ),
        "features": (
            feature_results
        ),
    }


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
        "VWORLD_API_KEY:",
        (
            "FOUND"
            if VWORLD_API_KEY
            else "MISSING"
        ),
    )

    # ========================================================
    # 1. 기본 검증
    # ========================================================

    if not VWORLD_API_KEY:

        print(
            "ERROR: VWORLD_API_KEY 없음"
        )

        return 1

    if (
        len(
            site.get(
                "pnu",
                "",
            )
        )
        != 19
    ):

        print(
            "ERROR: PNU 19자리 검증 실패"
        )

        return 1

    # ========================================================
    # 2. UQ128 파일
    # ========================================================

    print_section(
        "1. UQ128 공식 공간레이어 로드"
    )

    files = (
        find_uq128_files()
    )

    print(
        "found files:",
        len(
            files
        ),
    )

    for path in files:

        print(
            "-",
            path,
        )

    if not files:

        resolution = {
            "query_status": (
                "NOT_QUERIED"
            ),
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "NONE"
            ),
            "reason": (
                "UQ128 공식 공간파일을 찾지 못함"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "resolution": (
                    resolution
                ),
            }
        )

        return 0

    try:

        layer_result = (
            load_uq128_layer(
                files[
                    0
                ]
            )
        )

    except Exception as exc:

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
                "UQ128 공식 공간레이어 로드 실패: "
                f"{exc}"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "resolution": (
                    resolution
                ),
            }
        )

        print(
            resolution[
                "reason"
            ]
        )

        return 0

    uq128_gdf = (
        layer_result[
            "gdf"
        ]
    )

    print(
        "Feature count:",
        len(
            uq128_gdf
        ),
    )

    print(
        "original CRS:",
        layer_result.get(
            "original_crs"
        ),
    )

    print(
        "effective CRS:",
        layer_result.get(
            "effective_crs"
        ),
    )

    # ========================================================
    # 3. 코드/schema
    # ========================================================

    print_section(
        "2. UQ128 코드 / schema 검증"
    )

    schema = (
        validate_uq128_schema(
            uq128_gdf
        )
    )

    print(
        "verified:",
        schema.get(
            "verified"
        ),
    )

    print(
        "LCLAS_CL:",
        schema.get(
            "LCLAS_CL_values"
        ),
    )

    print(
        "ATRB_SE:",
        schema.get(
            "ATRB_SE_values"
        ),
    )

    print(
        "DGM_NM:",
        schema.get(
            "DGM_NM_values"
        ),
    )

    print(
        "geometry valid:",
        (
            f"{schema.get('geometry_valid_count')}"
            f"/{schema.get('feature_count')}"
        ),
    )

    if not schema.get(
        "verified"
    ):

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
                "UQ128 공간레이어의 UQM120 "
                "코드/schema 검증에 실패함"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "schema": (
                    schema
                ),
                "resolution": (
                    resolution
                ),
            }
        )

        return 0

    # ========================================================
    # 4. Parcel
    # ========================================================

    print_section(
        "3. SITE Parcel Polygon 조회"
    )

    point = (
        get_site_point(
            site[
                "address"
            ]
        )
    )

    print(
        "대표좌표 EPSG:4326:",
        point,
    )

    if point is None:

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
                "SITE 대표좌표 조회 실패"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "resolution": (
                    resolution
                ),
            }
        )

        return 0

    parcel_result = (
        query_parcel_polygon(
            point[
                0
            ],
            point[
                1
            ],
            site[
                "pnu"
            ],
        )
    )

    matched_parcels = (
        parcel_result.get(
            "features",
            [],
        )
    )

    print(
        "Parcel query_status:",
        parcel_result.get(
            "query_status"
        ),
    )

    print(
        "PNU matched parcel count:",
        len(
            matched_parcels
        ),
    )

    if (
        parcel_result.get(
            "query_status"
        )
        != "QUERY_SUCCESS"
        or not matched_parcels
    ):

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
                "대상 PNU Parcel Polygon을 "
                "정상 확보하지 못함"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "resolution": (
                    resolution
                ),
            }
        )

        return 0

    parcel_feature = (
        matched_parcels[
            0
        ]
    )

    parcel_4326 = (
        parcel_feature[
            "geometry"
        ]
    )

    print(
        "Parcel geometry:",
        parcel_4326.geom_type,
    )

    print(
        "Parcel bounds EPSG:4326:",
        list(
            parcel_4326.bounds
        ),
    )

    # ========================================================
    # 5. 동일 CRS 정규화
    # ========================================================

    print_section(
        "4. CRS 정규화"
    )

    try:

        parcel_gdf = (
            gpd.GeoDataFrame(
                [
                    {
                        "pnu": (
                            site[
                                "pnu"
                            ]
                        )
                    }
                ],
                geometry=[
                    parcel_4326
                ],
                crs=(
                    "EPSG:4326"
                ),
            )
        )

        parcel_target_gdf = (
            parcel_gdf.to_crs(
                uq128_gdf.crs
            )
        )

        parcel_target = (
            parcel_target_gdf
            .geometry
            .iloc[
                0
            ]
        )

    except Exception as exc:

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
                "Parcel CRS 변환 실패: "
                f"{exc}"
            ),
        }

        save_json(
            {
                "step": STEP_NAME,
                "condition": (
                    TARGET_CONDITION
                ),
                "site": site,
                "resolution": (
                    resolution
                ),
            }
        )

        return 0

    print(
        "intersection CRS:",
        uq128_gdf.crs,
    )

    print(
        "Parcel geometry:",
        parcel_target.geom_type,
    )

    print(
        "Parcel area:",
        float(
            parcel_target.area
        ),
    )

    print(
        "Parcel bounds:",
        [
            float(
                x
            )
            for x
            in parcel_target.bounds
        ],
    )

    # ========================================================
    # 6. 실제 교차
    # ========================================================

    print_section(
        "5. UQ128 × Parcel 실제 공간교차"
    )

    intersection = (
        calculate_intersections(
            parcel_target,
            uq128_gdf,
        )
    )

    print(
        "전체 UQ128 Feature:",
        len(
            uq128_gdf
        ),
    )

    print(
        "bbox candidate count:",
        intersection.get(
            "bbox_candidate_count"
        ),
    )

    print(
        "intersection count:",
        intersection.get(
            "intersection_count"
        ),
    )

    print(
        "positive area intersection count:",
        intersection.get(
            "positive_area_intersection_count"
        ),
    )

    print(
        "max parcel intersection ratio:",
        intersection.get(
            "max_intersection_ratio"
        ),
    )

    if intersection.get(
        "features"
    ):

        print()

        print(
            "교차 Feature:"
        )

        for feature in (
            intersection[
                "features"
            ]
        ):

            print(
                "-",
                feature,
            )

    # ========================================================
    # 7. 최종 판정
    # ========================================================

    print_section(
        "6. 최종 판정"
    )

    positive_area_count = (
        intersection.get(
            "positive_area_intersection_count",
            0,
        )
    )

    max_ratio = (
        intersection.get(
            "max_intersection_ratio",
            0.0,
        )
    )

    if (
        positive_area_count
        > 0
    ):

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "TRUE"
            ),
            "confidence": (
                "HIGH"
            ),
            "reason": (
                "서울시 공식 UQ128 취락지구 "
                "공간레이어를 정상 로드하고 "
                "UQM120 코드체계를 검증한 뒤 "
                "대상 PNU Parcel Polygon과 실제 "
                "면적교차가 확인됨"
            ),
            "max_intersection_ratio": (
                max_ratio
            ),
        }

    else:

        resolution = {
            "query_status": (
                "QUERY_SUCCESS"
            ),
            "resolution": (
                "FALSE"
            ),
            "confidence": (
                "HIGH"
            ),
            "reason": (
                "서울시 공식 UQ128 취락지구 "
                "전체 공간레이어를 정상 로드하고 "
                "UQM120 코드체계를 검증한 뒤 "
                "대상 PNU Parcel Polygon과 공간교차를 "
                "수행했으나 실제 면적교차가 확인되지 않음"
            ),
            "max_intersection_ratio": (
                max_ratio
            ),
        }

    print(
        "query_status:",
        resolution.get(
            "query_status"
        ),
    )

    print(
        "resolution:",
        resolution.get(
            "resolution"
        ),
    )

    print(
        "confidence:",
        resolution.get(
            "confidence"
        ),
    )

    print(
        "reason:",
        resolution.get(
            "reason"
        ),
    )

    # ========================================================
    # 8. evidence 저장
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            TARGET_CONDITION
        ),

        "site": (
            site
        ),

        "parcel": {
            "provider": (
                "VWorld"
            ),
            "dataset": (
                PARCEL_DATASET
            ),
            "feature_id": (
                parcel_feature.get(
                    "id"
                )
            ),
            "pnu_direct_match": (
                True
            ),
            "original_crs": (
                "EPSG:4326"
            ),
            "intersection_crs": (
                str(
                    uq128_gdf.crs
                )
            ),
            "geometry_type": (
                parcel_target.geom_type
            ),
            "area": float(
                parcel_target.area
            ),
            "bounds": [
                float(
                    value
                )
                for value
                in parcel_target.bounds
            ],
        },

        "uq128_source": {
            "provider": (
                "서울특별시"
            ),
            "dataset": (
                "서울시 용도지구(취락지구) 공간정보"
            ),
            "dataset_code": (
                UQ128_CODE
            ),
            "openapi": (
                "upisCUq128"
            ),
            "class_code": (
                EXPECTED_CLASS_CODE
            ),
            "source_path": (
                layer_result.get(
                    "source_path"
                )
            ),
            "feature_count": (
                layer_result.get(
                    "feature_count"
                )
            ),
            "original_crs": (
                layer_result.get(
                    "original_crs"
                )
            ),
            "effective_crs": (
                layer_result.get(
                    "effective_crs"
                )
            ),
            "crs_source": (
                layer_result.get(
                    "crs_source"
                )
            ),
            "columns": (
                layer_result.get(
                    "columns"
                )
            ),
        },

        "schema": (
            schema
        ),

        "intersection": (
            intersection
        ),

        "resolution": (
            resolution
        ),

        "validation": {
            "VWORLD API Key 존재": (
                bool(
                    VWORLD_API_KEY
                )
            ),
            "SITE PNU 19자리": (
                len(
                    site.get(
                        "pnu",
                        "",
                    )
                )
                == 19
            ),
            "Parcel query 성공": (
                parcel_result.get(
                    "query_status"
                )
                == "QUERY_SUCCESS"
            ),
            "Parcel PNU 직접 검증": (
                bool(
                    matched_parcels
                )
            ),
            "Parcel Polygon geometry": (
                parcel_target.geom_type
                in (
                    "Polygon",
                    "MultiPolygon",
                )
            ),
            "UQ128 공식 공간파일 존재": (
                bool(
                    files
                )
            ),
            "UQ128 Feature 38건": (
                len(
                    uq128_gdf
                )
                == 38
            ),
            "LCLAS_CL UQM120 검증": (
                schema.get(
                    "LCLAS_CL_all_UQM120"
                )
                is True
            ),
            "ATRB_SE UQM120 검증": (
                schema.get(
                    "ATRB_SE_all_UQM120"
                )
                is True
            ),
            "UQ128 geometry 전체 유효": (
                schema.get(
                    "geometry_valid_count"
                )
                == len(
                    uq128_gdf
                )
            ),
            "동일 CRS 교차": (
                str(
                    uq128_gdf.crs
                )
                == str(
                    parcel_target_gdf.crs
                )
            ),
            "TRUE는 실제 면적교차 필요": (
                True
            ),
            "경계접촉만으로 TRUE 금지": (
                True
            ),
            "FALSE는 전체 공식 layer 정상 필요": (
                True
            ),
        },

        "next_step": (
            "취락지구 판정 확정 후 "
            "다음 미해결 공간조건으로 진행"
        ),
    }

    save_json(
        result
    )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )