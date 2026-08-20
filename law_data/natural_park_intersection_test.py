# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-12B
국토교통부 자연공원/용도지구 × Parcel Polygon 실제 공간교차

판정 원칙
======================================================================
1. 공식 자연공원/용도지구 전체 Polygon layer 정상 로드
2. 대상 PNU Parcel Polygon 직접 검증
3. 동일 CRS(EPSG:5174)에서 실제 면적교차
4. 면적교차 > 0 -> TRUE / HIGH
5. 전체 layer 정상 + 면적교차 없음 -> FALSE / HIGH
6. 경계 접촉(area=0)은 TRUE로 처리하지 않음
"""

from __future__ import annotations

import json
import math
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
    "STEP 17-21-C-9-2-12B "
    "자연공원 Parcel Polygon 실제 공간교차"
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
    / "natural_park_intersection.json"
)


# ============================================================
# Dataset
# ============================================================

PARCEL_DATASET = "LP_PA_CBND_BUBUN"

EXPECTED_PREFIX = (
    "LSMD_CONT_UM102"
)

EXPECTED_CRS = (
    "EPSG:5174"
)

EXPECTED_FEATURE_COUNT = 48


# ============================================================
# 환경변수
# ============================================================

load_dotenv(
    BASE_DIR / ".env"
)

VWORLD_API_KEY = os.getenv(
    "VWORLD_API_KEY"
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
    print("=" * 72)
    print(f"=== {title} ===")
    print("=" * 72)


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

    try:
        if isinstance(
            value,
            float,
        ) and math.isnan(
            value
        ):
            return ""
    except Exception:
        pass

    text = str(
        value
    ).strip()

    if text.lower() in (
        "nan",
        "none",
        "null",
    ):
        return ""

    return text


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

        payload = response.json()

    except Exception:

        return None

    body = payload.get(
        "response",
        {},
    )

    if body.get(
        "status"
    ) != "OK":

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

        payload = response.json()

    except Exception as exc:

        return {
            "query_status": "QUERY_FAILED",
            "features": [],
            "reason": str(exc),
        }

    body = payload.get(
        "response",
        {},
    )

    if body.get(
        "status"
    ) != "OK":

        return {
            "query_status": "QUERY_FAILED",
            "features": [],
            "reason": (
                "VWorld status="
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

        properties = feature.get(
            "properties",
            {},
        )

        if safe_string(
            properties.get(
                "pnu"
            )
        ) != pnu:

            continue

        geometry_data = feature.get(
            "geometry"
        )

        if not geometry_data:
            continue

        try:

            geom = shape(
                geometry_data
            )

        except Exception:
            continue

        if (
            geom.is_empty
            or geom.geom_type
            not in (
                "Polygon",
                "MultiPolygon",
            )
        ):
            continue

        matched.append(
            {
                "id": feature.get(
                    "id"
                ),
                "geometry": geom,
                "properties": (
                    properties
                ),
            }
        )

    return {
        "query_status": (
            "QUERY_SUCCESS"
        ),
        "features": matched,
    }


# ============================================================
# 자연공원 파일
# ============================================================

def find_files() -> List[Path]:

    result: List[Path] = []

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():
            continue

        for pattern in (
            "*UM102*.zip",
            "*UM102*.shp",
        ):

            for path in base_dir.rglob(
                pattern
            ):

                if path not in result:
                    result.append(
                        path
                    )

    result.sort(
        key=lambda p: (
            0
            if (
                "5174" in p.name
                and "서울" in p.name
            )
            else 1,
            -(
                p.stat().st_mtime
                if p.exists()
                else 0
            ),
        )
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

    for path in shp_files:

        if (
            EXPECTED_PREFIX
            in path.name.upper()
        ):
            return path

    return (
        shp_files[0]
        if shp_files
        else None
    )


def load_layer(
    path: Path,
) -> Dict[str, Any]:

    temp_dir = None

    try:

        if path.suffix.lower() == ".zip":

            temp_dir = (
                tempfile.TemporaryDirectory()
            )

            temp_path = Path(
                temp_dir.name
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

                    gdf = gpd.read_file(
                        shp_path
                    )

                else:

                    gdf = gpd.read_file(
                        shp_path,
                        encoding=encoding,
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

        return {
            "gdf": gdf,
            "source_path": str(
                path
            ),
            "feature_count": (
                len(gdf)
            ),
            "crs": (
                str(gdf.crs)
                if gdf.crs
                else None
            ),
        }

    finally:

        if temp_dir is not None:
            temp_dir.cleanup()


# ============================================================
# Layer 검증
# ============================================================

def validate_layer(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    geometry_types = sorted(
        set(
            gdf.geometry.geom_type.tolist()
        )
    )

    valid_geometry_count = int(
        (
            gdf.geometry.notna()
            & ~gdf.geometry.is_empty
        ).sum()
    )

    alias_values = []

    if "ALIAS" in gdf.columns:

        alias_values = sorted(
            {
                safe_string(
                    value
                )
                for value
                in gdf[
                    "ALIAS"
                ].tolist()
                if safe_string(
                    value
                )
            }
        )

    polygon_ok = all(
        value
        in (
            "Polygon",
            "MultiPolygon",
        )
        for value
        in geometry_types
    )

    verified = (
        len(gdf) > 0
        and valid_geometry_count
        == len(gdf)
        and polygon_ok
        and str(
            gdf.crs
        ) == EXPECTED_CRS
    )

    return {
        "verified": verified,
        "feature_count": len(
            gdf
        ),
        "geometry_types": (
            geometry_types
        ),
        "valid_geometry_count": (
            valid_geometry_count
        ),
        "alias_values": (
            alias_values
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

    features = []

    for index, row in (
        gdf.iterrows()
    ):

        geometry = row.geometry

        if (
            geometry is None
            or geometry.is_empty
        ):
            continue

        bounds = geometry.bounds

        bbox_intersects = not (
            bounds[2] < parcel_bounds[0]
            or bounds[0] > parcel_bounds[2]
            or bounds[3] < parcel_bounds[1]
            or bounds[1] > parcel_bounds[3]
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

        ratio = (
            intersection_area
            / parcel_area
            if parcel_area > 0
            else 0.0
        )

        if intersection_area > 0:

            positive_area_count += 1

        max_ratio = max(
            max_ratio,
            ratio,
        )

        features.append(
            {
                "index": (
                    int(index)
                    if isinstance(
                        index,
                        int,
                    )
                    else str(index)
                ),
                "MNUM": safe_string(
                    row.get(
                        "MNUM"
                    )
                ),
                "ALIAS": safe_string(
                    row.get(
                        "ALIAS"
                    )
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
        "features": features,
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        STEP_NAME
    )

    site = load_site_context()

    if not VWORLD_API_KEY:

        print(
            "ERROR: VWORLD_API_KEY 없음"
        )
        return 1

    # ========================================================
    # 자연공원 layer
    # ========================================================

    files = find_files()

    if not files:

        print(
            "ERROR: 자연공원 SHP 없음"
        )
        return 1

    layer = load_layer(
        files[0]
    )

    gdf = layer[
        "gdf"
    ]

    validation = validate_layer(
        gdf
    )

    print(
        "Natural park layer:",
        (
            "OK"
            if validation[
                "verified"
            ]
            else "FAIL"
        ),
    )

    print(
        "Feature:",
        validation[
            "feature_count"
        ],
    )

    print(
        "CRS:",
        gdf.crs,
    )

    if not validation[
        "verified"
    ]:

        print(
            "resolution: UNKNOWN"
        )
        return 0

    # ========================================================
    # Parcel
    # ========================================================

    point = get_site_point(
        site[
            "address"
        ]
    )

    if point is None:

        print(
            "Parcel point: FAIL"
        )
        return 1

    parcel_result = (
        query_parcel_polygon(
            point[0],
            point[1],
            site[
                "pnu"
            ],
        )
    )

    parcels = parcel_result.get(
        "features",
        [],
    )

    print(
        "Parcel PNU match:",
        len(
            parcels
        ),
    )

    if not parcels:

        print(
            "resolution: UNKNOWN"
        )
        return 0

    parcel_feature = parcels[
        0
    ]

    parcel_4326 = parcel_feature[
        "geometry"
    ]

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
            gdf.crs
        )
    )

    parcel = (
        parcel_target_gdf
        .geometry
        .iloc[
            0
        ]
    )

    # ========================================================
    # 실제 교차
    # ========================================================

    intersection = (
        calculate_intersections(
            parcel,
            gdf,
        )
    )

    positive_count = (
        intersection[
            "positive_area_intersection_count"
        ]
    )

    max_ratio = (
        intersection[
            "max_intersection_ratio"
        ]
    )

    if positive_count > 0:

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
                "국토교통부 공식 자연공원/용도지구 "
                "Polygon과 대상 PNU Parcel Polygon의 "
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
                "국토교통부 공식 서울 자연공원/용도지구 "
                "전체 Polygon layer를 정상 로드하고 "
                "대상 PNU Parcel Polygon과 동일 CRS에서 "
                "공간교차를 수행했으나 실제 면적교차가 "
                "확인되지 않음"
            ),
            "max_intersection_ratio": (
                max_ratio
            ),
        }

    # ========================================================
    # 상세 evidence
    # ========================================================

    result = {
        "step": STEP_NAME,

        "condition": (
            "자연공원"
        ),

        "site": site,

        "official_source": {
            "provider": (
                "국토교통부"
            ),
            "dataset": (
                "(연속주제)_자연공원/용도지구"
            ),
            "vworld_dataset_id": (
                "30395"
            ),
            "source_path": (
                layer[
                    "source_path"
                ]
            ),
            "feature_count": (
                len(gdf)
            ),
            "crs": str(
                gdf.crs
            ),
        },

        "layer_validation": (
            validation
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
            "pnu_direct_match": True,
            "original_crs": (
                "EPSG:4326"
            ),
            "intersection_crs": (
                str(
                    gdf.crs
                )
            ),
            "geometry_type": (
                parcel.geom_type
            ),
            "area": float(
                parcel.area
            ),
            "bounds": [
                float(x)
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
            "PNU 직접 일치 Parcel": (
                bool(
                    parcels
                )
            ),
            "자연공원 Feature 48": (
                len(gdf)
                == EXPECTED_FEATURE_COUNT
            ),
            "CRS EPSG:5174": (
                str(
                    gdf.crs
                )
                == EXPECTED_CRS
            ),
            "전체 geometry 유효": (
                validation[
                    "valid_geometry_count"
                ]
                == len(gdf)
            ),
            "Polygon/MultiPolygon only": (
                all(
                    value
                    in (
                        "Polygon",
                        "MultiPolygon",
                    )
                    for value
                    in validation[
                        "geometry_types"
                    ]
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
            "자연공원 판정 확정 후 "
            "다음 미해결 공간조건 진행"
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 초간략 콘솔
    # ========================================================

    print(
        "BBOX candidates:",
        intersection[
            "bbox_candidate_count"
        ],
    )

    print(
        "Area intersections:",
        positive_count,
    )

    print(
        "Max ratio:",
        max_ratio,
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
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )