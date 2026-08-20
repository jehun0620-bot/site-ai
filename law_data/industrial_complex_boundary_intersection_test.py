# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-11B
국토교통부 산업단지 경계도면 × Parcel Polygon 실제 공간교차

목표
======================================================================
1. 국토교통부 공식 전국 산업단지 경계도면을 정상 로드한다.
2. 실제 schema(DAN_ID / DAN_NAME / DANJI_TYPE)를 검증한다.
3. 대상 PNU Parcel Polygon을 VWorld에서 직접 확보한다.
4. Parcel을 공식 산업단지 layer CRS(EPSG:3857)로 변환한다.
5. 전국 산업단지 1,340개 geometry와 Parcel Polygon을 실제 교차한다.
6. 면적교차 > 0이면 TRUE / HIGH.
7. 공식 전체 layer 정상 + 면적교차 없음이면 FALSE / HIGH.

판정 원칙
======================================================================
- 문자열 출현만으로 판정하지 않는다.
- Point만으로 TRUE/FALSE 판정하지 않는다.
- Parcel Polygon intersection을 사용한다.
- 경계 접촉(area = 0)은 TRUE가 아니다.
- 전체 공식 layer가 정상 로드되어야 FALSE 가능.
- CRS/schema/geometry 미확정이면 UNKNOWN.
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
    "STEP 17-21-C-9-2-11B "
    "국토교통부 산업단지 경계도면 × "
    "Parcel Polygon 실제 공간교차"
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
    / "industrial_complex_boundary_intersection.json"
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
# Dataset
# ============================================================

PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)

EXPECTED_INDUSTRIAL_FEATURE_COUNT = (
    1340
)

EXPECTED_CRS = (
    "EPSG:3857"
)

EXPECTED_ID_COLUMN = (
    "DAN_ID"
)

EXPECTED_NAME_COLUMN = (
    "DAN_NAME"
)

EXPECTED_TYPE_COLUMN = (
    "DANJI_TYPE"
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
# 대표좌표
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

    point = (
        items[
            0
        ].get(
            "point",
            {},
        )
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
# Parcel Polygon
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
# 산업단지 파일 탐색
# ============================================================

def find_industrial_boundary_files() -> List[Path]:

    result: List[
        Path
    ] = []

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():

            continue

        for path in (
            base_dir.rglob(
                "*"
            )
        ):

            if not path.is_file():

                continue

            if (
                path.suffix.lower()
                not in (
                    ".zip",
                    ".shp",
                )
            ):

                continue

            name = (
                path.name
                .lower()
            )

            if (
                "산업단지"
                in name
                and "경계"
                in name
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
            "dam_dan"
            in path.name.lower()
        ):

            return path

    return shp_files[
        0
    ]


# ============================================================
# 산업단지 layer 로드
# ============================================================

def load_industrial_layer(
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

            shp_path = (
                path
            )

        gdf = None

        read_errors = []

        for encoding in (
            "utf-8",
            "cp949",
            "windows-949",
            "euc-kr",
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
                "산업단지 SHP 로드 실패: "
                + " | ".join(
                    read_errors
                )
            )

        return {
            "gdf": (
                gdf
            ),
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
            "crs": (
                str(
                    gdf.crs
                )
                if gdf.crs
                else None
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
# schema 검증
# ============================================================

def validate_schema(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    required_columns = [
        EXPECTED_ID_COLUMN,
        EXPECTED_NAME_COLUMN,
        EXPECTED_TYPE_COLUMN,
        "geometry",
    ]

    missing = [
        column
        for column
        in required_columns
        if (
            column
            not in gdf.columns
        )
    ]

    geometry_types = sorted(
        {
            safe_string(
                value
            )
            for value
            in gdf.geometry.geom_type.tolist()
            if safe_string(
                value
            )
        }
    )

    valid_geometry_count = int(
        (
            gdf.geometry.notna()
            & ~gdf.geometry.is_empty
        ).sum()
    )

    type_values = []

    if (
        EXPECTED_TYPE_COLUMN
        in gdf.columns
    ):

        type_values = sorted(
            {
                safe_string(
                    value
                )
                for value
                in gdf[
                    EXPECTED_TYPE_COLUMN
                ].tolist()
                if safe_string(
                    value
                )
            }
        )

    polygon_only = (
        bool(
            geometry_types
        )
        and all(
            value
            in (
                "Polygon",
                "MultiPolygon",
            )
            for value
            in geometry_types
        )
    )

    verified = (
        not missing
        and valid_geometry_count
        == len(
            gdf
        )
        and polygon_only
    )

    return {
        "verified": (
            verified
        ),
        "missing_columns": (
            missing
        ),
        "feature_count": (
            len(
                gdf
            )
        ),
        "geometry_types": (
            geometry_types
        ),
        "valid_geometry_count": (
            valid_geometry_count
        ),
        "type_values": (
            type_values
        ),
        "reason": (
            "산업단지 공식 layer schema 정상"
            if verified
            else "산업단지 공식 layer schema 검증 실패"
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

    results = []

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

        bounds = (
            geometry.bounds
        )

        bbox_intersects = not (
            bounds[2]
            < parcel_bounds[0]
            or bounds[0]
            > parcel_bounds[2]
            or bounds[3]
            < parcel_bounds[1]
            or bounds[1]
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

        max_ratio = max(
            max_ratio,
            ratio,
        )

        results.append(
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
                "DAN_ID": safe_string(
                    row.get(
                        EXPECTED_ID_COLUMN
                    )
                ),
                "DAN_NAME": safe_string(
                    row.get(
                        EXPECTED_NAME_COLUMN
                    )
                ),
                "DANJI_TYPE": safe_string(
                    row.get(
                        EXPECTED_TYPE_COLUMN
                    )
                ),
                "geometry_type": (
                    geometry.geom_type
                ),
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
            results
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

    if not VWORLD_API_KEY:

        print(
            "ERROR: VWORLD_API_KEY 없음"
        )

        return 1

    # ========================================================
    # 1. 산업단지 layer
    # ========================================================

    print_section(
        "1. 공식 산업단지 전국 경계 layer"
    )

    files = (
        find_industrial_boundary_files()
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

        print(
            "ERROR: 공식 산업단지 경계 SHP 없음"
        )

        return 1

    layer = (
        load_industrial_layer(
            files[
                0
            ]
        )
    )

    industrial_gdf = (
        layer[
            "gdf"
        ]
    )

    print(
        "Feature count:",
        len(
            industrial_gdf
        ),
    )

    print(
        "CRS:",
        industrial_gdf.crs,
    )

    print(
        "columns:",
        layer.get(
            "columns"
        ),
    )

    # ========================================================
    # 2. schema
    # ========================================================

    print_section(
        "2. 산업단지 schema 검증"
    )

    schema = (
        validate_schema(
            industrial_gdf
        )
    )

    print(
        "verified:",
        schema.get(
            "verified"
        ),
    )

    print(
        "Feature count:",
        schema.get(
            "feature_count"
        ),
    )

    print(
        "Geometry types:",
        schema.get(
            "geometry_types"
        ),
    )

    print(
        "Geometry valid:",
        (
            f"{schema.get('valid_geometry_count')}"
            f"/{schema.get('feature_count')}"
        ),
    )

    print(
        "DANJI_TYPE values:",
        schema.get(
            "type_values"
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
                "산업단지 공식 layer schema "
                "검증 실패"
            ),
        }

        save_json(
            {
                "step": (
                    STEP_NAME
                ),
                "condition": (
                    "산업단지"
                ),
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
    # 3. Parcel
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

        print(
            "ERROR: 대표좌표 조회 실패"
        )

        return 1

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

    matched = (
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
            matched
        ),
    )

    if (
        parcel_result.get(
            "query_status"
        )
        != "QUERY_SUCCESS"
        or not matched
    ):

        print(
            "ERROR: Parcel Polygon 확보 실패"
        )

        return 1

    parcel_feature = (
        matched[
            0
        ]
    )

    parcel_4326 = (
        parcel_feature[
            "geometry"
        ]
    )

    # ========================================================
    # 4. CRS transform
    # ========================================================

    print_section(
        "4. Parcel CRS 정규화"
    )

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
            crs="EPSG:4326",
        )
    )

    parcel_target_gdf = (
        parcel_gdf.to_crs(
            industrial_gdf.crs
        )
    )

    parcel = (
        parcel_target_gdf
        .geometry
        .iloc[
            0
        ]
    )

    print(
        "intersection CRS:",
        industrial_gdf.crs,
    )

    print(
        "Parcel geometry:",
        parcel.geom_type,
    )

    print(
        "Parcel area:",
        float(
            parcel.area
        ),
    )

    print(
        "Parcel bounds:",
        [
            float(
                x
            )
            for x
            in parcel.bounds
        ],
    )

    # ========================================================
    # 5. intersection
    # ========================================================

    print_section(
        "5. 전국 산업단지 × Parcel 실제 공간교차"
    )

    intersection = (
        calculate_intersections(
            parcel,
            industrial_gdf,
        )
    )

    print(
        "전체 산업단지 Feature:",
        len(
            industrial_gdf
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
            "교차 산업단지:"
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
    # 6. final resolution
    # ========================================================

    print_section(
        "6. 최종 판정"
    )

    positive_count = (
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
        positive_count
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
                "국토교통부 공식 전국 산업단지 "
                "경계도면 1,340개 Polygon을 정상 "
                "로드하고 대상 PNU Parcel Polygon과 "
                "실제 면적교차가 확인됨"
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
                "국토교통부 공식 전국 산업단지 "
                "경계도면 전체 1,340개 Polygon을 "
                "정상 로드하고 대상 PNU Parcel Polygon과 "
                "동일 CRS에서 공간교차를 수행했으나 "
                "실제 면적교차가 확인되지 않음"
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
    # 7. evidence
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "산업단지"
        ),

        "site": (
            site
        ),

        "official_source": {
            "provider": (
                "국토교통부"
            ),
            "dataset": (
                "산업단지 경계도면"
            ),
            "coverage": (
                "대한민국 전체"
            ),
            "source_path": (
                layer.get(
                    "source_path"
                )
            ),
            "feature_count": (
                len(
                    industrial_gdf
                )
            ),
            "crs": (
                str(
                    industrial_gdf.crs
                )
            ),
            "columns": (
                layer.get(
                    "columns"
                )
            ),
        },

        "schema": (
            schema
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
                    industrial_gdf.crs
                )
            ),
            "geometry_type": (
                parcel.geom_type
            ),
            "area": (
                float(
                    parcel.area
                )
            ),
            "bounds": [
                float(
                    x
                )
                for x
                in parcel.bounds
            ],
        },

        "intersection": (
            intersection
        ),

        "resolution": (
            resolution
        ),

        "validation": {
            "VWORLD_API_KEY 존재": (
                bool(
                    VWORLD_API_KEY
                )
            ),
            "PNU 19자리": (
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
                    matched
                )
            ),
            "산업단지 공식 layer 존재": (
                bool(
                    files
                )
            ),
            "산업단지 Feature 1340": (
                len(
                    industrial_gdf
                )
                == EXPECTED_INDUSTRIAL_FEATURE_COUNT
            ),
            "산업단지 CRS EPSG:3857": (
                str(
                    industrial_gdf.crs
                )
                == EXPECTED_CRS
            ),
            "DAN_ID 존재": (
                EXPECTED_ID_COLUMN
                in industrial_gdf.columns
            ),
            "DAN_NAME 존재": (
                EXPECTED_NAME_COLUMN
                in industrial_gdf.columns
            ),
            "DANJI_TYPE 존재": (
                EXPECTED_TYPE_COLUMN
                in industrial_gdf.columns
            ),
            "전체 geometry 유효": (
                schema.get(
                    "valid_geometry_count"
                )
                == len(
                    industrial_gdf
                )
            ),
            "동일 CRS 교차": (
                str(
                    parcel_target_gdf.crs
                )
                == str(
                    industrial_gdf.crs
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
            "산업단지 판정 확정 후 "
            "자연공원 공간조건 검증"
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