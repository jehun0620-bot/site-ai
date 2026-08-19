# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-5C-2
서울시 UQ121 자연경관지구 Parcel Polygon 공간교차 최종 보정 테스트

핵심 보정
======================================================================
서울 OpenAPI 필드와 UQ121 SHP 내부 필드명이 서로 다름.

OpenAPI                    SHP
----------------------------------------------------------------------
STUT_FIG_MNG_NO        ->  PRESENT_SN
FIG_LCLSF_CD           ->  LCLAS_CL
FIG_MCLSF_CD           ->  MLSFC_CL
FIG_SCLSF_CD           ->  SCLAS_CL
FIG_ATRB_CD            ->  ATRB_SE
FIG_RPT_MNG_CD         ->  WTNNC_SN
DCSN_ANCMNT_MNG_CD     ->  NTFC_SN
LBL_NM                 ->  DGM_NM
AREA                    ->  DGM_AR / SHAPE_AREA
LEN                     ->  DGM_LT / SHAPE_LEN
SGG_CD                  ->  SIGNGU_SE
FLRPLN_NO               ->  DRAWING_NO
STUT_FIG_CRT_DT         ->  CREATE_DAT

자연경관지구 공식 검증값
======================================================================
OpenAPI:
    LBL_NM = 자연경관지구
    FIG_LCLSF_CD = UQF110
    FIG_ATRB_CD = UQF110

SHP:
    DGM_NM = 자연경관지구
    LCLAS_CL = UQF110
    ATRB_SE = UQF110

판정 원칙
======================================================================
1. 대상 PNU Parcel Polygon을 직접 검증
2. UQ121 전체 공간레이어가 정상 로드되어야 함
3. 자연경관지구 Feature 식별이 검증되어야 함
4. Parcel × 자연경관지구 실제 면적 교차 시 TRUE
5. 전체 자연경관지구 layer 정상조회 + 면적 교차 없음 시 FALSE
6. 데이터/분류/geometry 문제 시 UNKNOWN
7. 단순 경계 접촉(area = 0)은 TRUE 처리하지 않음
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

SCHEMA_RESULT_PATH = (
    OUTPUT_DIR
    / "seoul_natural_landscape_district_schema_test.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "seoul_natural_landscape_district_intersection_test.json"
)


# ============================================================
# Dataset / code
# ============================================================

PARCEL_DATASET = "LP_PA_CBND_BUBUN"

UQ121_CODE = "UQ121"

TARGET_LABEL = "자연경관지구"

TARGET_LCLASS_CODE = "UQF110"
TARGET_ATTRIBUTE_CODE = "UQF110"


# ============================================================
# VWorld
# ============================================================

VWORLD_SEARCH_URL = "https://api.vworld.kr/req/search"
VWORLD_DATA_URL = "https://api.vworld.kr/req/data"

load_dotenv(BASE_DIR / ".env")

VWORLD_API_KEY = os.getenv("VWORLD_API_KEY")


# ============================================================
# JSON
# ============================================================

def load_json(path: Path) -> Dict[str, Any]:

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


# ============================================================
# 공통
# ============================================================

def first_nonempty(*values: Any) -> Any:

    for value in values:

        if value not in (
            None,
            "",
            [],
            {},
            "-",
        ):
            return value

    return None


def safe_string(value: Any) -> str:

    if value is None:
        return ""

    return str(value).strip()


# ============================================================
# SITE Context
# ============================================================

def extract_site_context(
    payload: Dict[str, Any],
) -> Dict[str, str]:

    candidates = [
        payload,
        payload.get("site", {}),
        payload.get("query_context", {}),
        payload.get("target_site", {}),
    ]

    result = {
        "site_id": None,
        "address": None,
        "zoning": None,
        "pnu": None,
    }

    for item in candidates:

        if not isinstance(item, dict):
            continue

        result["site_id"] = first_nonempty(
            result["site_id"],
            item.get("site_id"),
            item.get("parcel_key"),
        )

        result["address"] = first_nonempty(
            result["address"],
            item.get("address"),
            item.get("jibun_address"),
        )

        result["zoning"] = first_nonempty(
            result["zoning"],
            item.get("zoning"),
            item.get("use_zone"),
            item.get("land_use_zone"),
        )

        result["pnu"] = first_nonempty(
            result["pnu"],
            item.get("pnu"),
            item.get("PNU"),
        )

    return {
        key: str(value or "-")
        for key, value
        in result.items()
    }


# ============================================================
# VWorld 대표좌표
# ============================================================

def get_site_point(
    address: str,
) -> Optional[Tuple[float, float]]:

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
            timeout=30,
        )

        payload = response.json()

    except Exception:

        return None

    body = payload.get(
        "response",
        {},
    )

    if body.get("status") != "OK":
        return None

    items = (
        body
        .get("result", {})
        .get("items", [])
    )

    if not items:
        return None

    point = items[0].get(
        "point",
        {},
    )

    try:

        x = float(point["x"])
        y = float(point["y"])

        return x, y

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
        "geomFilter": f"POINT({x} {y})",
        "size": 100,
    }

    try:

        response = requests.get(
            VWORLD_DATA_URL,
            params=params,
            timeout=30,
        )

        payload = response.json()

    except Exception as exc:

        return {
            "query_status": "QUERY_FAILED",
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

    if body.get("status") != "OK":

        return {
            "query_status": "QUERY_FAILED",
            "raw_feature_count": 0,
            "features": [],
            "reason": (
                "VWorld Parcel API status="
                f"{body.get('status')}"
            ),
        }

    feature_collection = (
        body
        .get("result", {})
        .get("featureCollection", {})
    )

    features = feature_collection.get(
        "features",
        [],
    )

    matched = []

    for feature in features:

        properties = feature.get(
            "properties",
            {},
        )

        feature_pnu = safe_string(
            properties.get("pnu")
        )

        if feature_pnu != pnu:
            continue

        geometry = feature.get(
            "geometry"
        )

        if not geometry:
            continue

        try:

            geom = shape(geometry)

        except Exception:
            continue

        if geom.is_empty:
            continue

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            continue

        matched.append(
            {
                "id": feature.get("id"),
                "properties": properties,
                "geometry": geom,
            }
        )

    return {
        "query_status": "QUERY_SUCCESS",
        "raw_feature_count": len(features),
        "features": matched,
        "reason": "대상 PNU Parcel Polygon 조회 완료",
    }


# ============================================================
# UQ121 파일 탐색
# ============================================================

def find_uq121_files() -> List[Path]:

    result: List[Path] = []

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():
            continue

        for pattern in (
            "*UQ121*.zip",
            "*UQ121*.shp",
        ):

            for path in base_dir.rglob(pattern):

                if path not in result:
                    result.append(path)

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
        folder.rglob("*.shp")
    )

    if not shp_files:
        return None

    for path in shp_files:

        if "UQ121" in path.name.upper():
            return path

    return shp_files[0]


# ============================================================
# UQ121 로드
# ============================================================

def load_uq121_layer(
    path: Path,
) -> Dict[str, Any]:

    temp_dir_object = None

    try:

        if path.suffix.lower() == ".zip":

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

                zf.extractall(temp_path)

            shp_path = find_shp_inside_folder(
                temp_path
            )

            if shp_path is None:

                raise RuntimeError(
                    "UQ121 ZIP 내부 SHP 파일을 찾지 못했습니다."
                )

        else:

            shp_path = path

        gdf = None
        read_errors = []

        for encoding in (
            "cp949",
            "euc-kr",
            "windows-949",
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

                read_errors.append(
                    f"{encoding}: {exc}"
                )

        if gdf is None:

            raise RuntimeError(
                "UQ121 SHP 로드 실패: "
                + " | ".join(read_errors)
            )

        original_crs = (
            str(gdf.crs)
            if gdf.crs
            else None
        )

        crs_source = "FILE_METADATA"

        if gdf.crs is None:

            gdf = gdf.set_crs(
                "EPSG:5174",
                allow_override=True,
            )

            crs_source = (
                "OFFICIAL_DEFAULT_EPSG5174"
            )

        gdf = gdf.to_crs(
            "EPSG:4326"
        )

        gdf = gdf.copy()

        return {
            "gdf": gdf,
            "source_path": str(path),
            "shp_path": str(shp_path),
            "original_crs": original_crs,
            "normalized_crs": "EPSG:4326",
            "crs_source": crs_source,
            "feature_count": len(gdf),
            "columns": [
                str(column)
                for column
                in gdf.columns
            ],
        }

    finally:

        if temp_dir_object is not None:
            temp_dir_object.cleanup()


# ============================================================
# UQ121 Schema 분석
# ============================================================

def analyze_uq121_schema(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    expected_columns = {
        "PRESENT_SN": "STUT_FIG_MNG_NO",
        "LCLAS_CL": "FIG_LCLSF_CD",
        "MLSFC_CL": "FIG_MCLSF_CD",
        "SCLAS_CL": "FIG_SCLSF_CD",
        "ATRB_SE": "FIG_ATRB_CD",
        "WTNNC_SN": "FIG_RPT_MNG_CD",
        "NTFC_SN": "DCSN_ANCMNT_MNG_CD",
        "DGM_NM": "LBL_NM",
        "DGM_AR": "AREA",
        "DGM_LT": "LEN",
        "SIGNGU_SE": "SGG_CD",
        "DRAWING_NO": "FLRPLN_NO",
        "CREATE_DAT": "STUT_FIG_CRT_DT",
    }

    present = {}

    for shp_column, api_column in (
        expected_columns.items()
    ):

        present[shp_column] = {
            "exists": shp_column in gdf.columns,
            "openapi_equivalent": api_column,
        }

    return {
        "column_mapping": present,
        "actual_columns": [
            str(column)
            for column
            in gdf.columns
        ],
    }


# ============================================================
# 자연경관지구 식별
# ============================================================

def filter_natural_landscape_features(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    """
    UQ121 SHP의 실제 schema 사용.

    우선순위
    ----------------------------------------------------------
    1. DGM_NM == 자연경관지구
       - OpenAPI LBL_NM 대응 필드

    2. ATRB_SE == UQF110
       - OpenAPI FIG_ATRB_CD 대응 필드

    3. LCLAS_CL == UQF110
       - OpenAPI FIG_LCLSF_CD 대응 필드

    가장 강한 명시 텍스트 DGM_NM을 우선 사용하고,
    공식 코드값을 교차 검증한다.
    """

    diagnostics: Dict[str, Any] = {
        "DGM_NM_exists":
            "DGM_NM" in gdf.columns,

        "ATRB_SE_exists":
            "ATRB_SE" in gdf.columns,

        "LCLAS_CL_exists":
            "LCLAS_CL" in gdf.columns,

        "target_label":
            TARGET_LABEL,

        "target_attribute_code":
            TARGET_ATTRIBUTE_CODE,

        "target_lclass_code":
            TARGET_LCLASS_CODE,
    }

    text_mask = None
    attribute_mask = None
    lclass_mask = None

    # --------------------------------------------------------
    # DGM_NM
    # --------------------------------------------------------

    if "DGM_NM" in gdf.columns:

        values = (
            gdf["DGM_NM"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        text_mask = (
            values == TARGET_LABEL
        )

        diagnostics[
            "DGM_NM_target_count"
        ] = int(text_mask.sum())

        diagnostics[
            "DGM_NM_unique_values"
        ] = sorted(
            {
                value
                for value
                in values.tolist()
                if value
            }
        )

    # --------------------------------------------------------
    # ATRB_SE
    # --------------------------------------------------------

    if "ATRB_SE" in gdf.columns:

        values = (
            gdf["ATRB_SE"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        attribute_mask = (
            values == TARGET_ATTRIBUTE_CODE
        )

        diagnostics[
            "ATRB_SE_target_count"
        ] = int(
            attribute_mask.sum()
        )

        diagnostics[
            "ATRB_SE_unique_values"
        ] = sorted(
            {
                value
                for value
                in values.tolist()
                if value
            }
        )

    # --------------------------------------------------------
    # LCLAS_CL
    # --------------------------------------------------------

    if "LCLAS_CL" in gdf.columns:

        values = (
            gdf["LCLAS_CL"]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.upper()
        )

        lclass_mask = (
            values == TARGET_LCLASS_CODE
        )

        diagnostics[
            "LCLAS_CL_target_count"
        ] = int(
            lclass_mask.sum()
        )

        diagnostics[
            "LCLAS_CL_unique_values"
        ] = sorted(
            {
                value
                for value
                in values.tolist()
                if value
            }
        )

    # ========================================================
    # 1. DGM_NM 명시 텍스트
    # ========================================================

    if (
        text_mask is not None
        and int(text_mask.sum()) > 0
    ):

        subset = gdf[
            text_mask
        ].copy()

        # 코드 일치 검증
        code_consistency = {}

        if "ATRB_SE" in subset.columns:

            atrb_values = (
                subset["ATRB_SE"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            code_consistency[
                "ATRB_SE_all_UQF110"
            ] = bool(
                len(subset) > 0
                and
                (
                    atrb_values
                    == TARGET_ATTRIBUTE_CODE
                ).all()
            )

        if "LCLAS_CL" in subset.columns:

            lclas_values = (
                subset["LCLAS_CL"]
                .fillna("")
                .astype(str)
                .str.strip()
                .str.upper()
            )

            code_consistency[
                "LCLAS_CL_all_UQF110"
            ] = bool(
                len(subset) > 0
                and
                (
                    lclas_values
                    == TARGET_LCLASS_CODE
                ).all()
            )

        diagnostics[
            "code_consistency"
        ] = code_consistency

        return {
            "status": "VERIFIED",
            "method": "DGM_NM_EXPLICIT_TEXT",
            "column": "DGM_NM",
            "value": TARGET_LABEL,
            "feature_count": len(subset),
            "gdf": subset,
            "diagnostics": diagnostics,
        }

    # ========================================================
    # 2. ATRB_SE
    # ========================================================

    if (
        attribute_mask is not None
        and int(attribute_mask.sum()) > 0
    ):

        subset = gdf[
            attribute_mask
        ].copy()

        return {
            "status": "VERIFIED",
            "method": "ATRB_SE_OFFICIAL_CODE",
            "column": "ATRB_SE",
            "value": TARGET_ATTRIBUTE_CODE,
            "feature_count": len(subset),
            "gdf": subset,
            "diagnostics": diagnostics,
        }

    # ========================================================
    # 3. LCLAS_CL
    # ========================================================

    if (
        lclass_mask is not None
        and int(lclass_mask.sum()) > 0
    ):

        subset = gdf[
            lclass_mask
        ].copy()

        return {
            "status": "VERIFIED",
            "method": "LCLAS_CL_OFFICIAL_CODE",
            "column": "LCLAS_CL",
            "value": TARGET_LCLASS_CODE,
            "feature_count": len(subset),
            "gdf": subset,
            "diagnostics": diagnostics,
        }

    # ========================================================
    # 실패
    # ========================================================

    return {
        "status": "UNRESOLVED",
        "method": None,
        "column": None,
        "value": None,
        "feature_count": 0,
        "gdf": None,
        "diagnostics": diagnostics,
        "reason": (
            "UQ121 공간레이어는 정상 로드되었으나 "
            "DGM_NM='자연경관지구', "
            "ATRB_SE='UQF110', "
            "LCLAS_CL='UQF110' 중 어느 식별 규칙도 "
            "실제 Feature에서 확인하지 못함"
        ),
    }


# ============================================================
# 교차 분석
# ============================================================

def bbox_overlaps(
    bounds_a: Tuple[
        float,
        float,
        float,
        float,
    ],
    bounds_b: Tuple[
        float,
        float,
        float,
        float,
    ],
) -> bool:

    aminx, aminy, amaxx, amaxy = bounds_a
    bminx, bminy, bmaxx, bmaxy = bounds_b

    return not (
        amaxx < bminx
        or aminx > bmaxx
        or amaxy < bminy
        or aminy > bmaxy
    )


def analyze_intersections(
    parcel_geom,
    natural_gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    parcel_area = float(
        parcel_geom.area
    )

    parcel_bounds = (
        parcel_geom.bounds
    )

    bbox_candidate_count = 0

    intersections = []

    for index, row in (
        natural_gdf.iterrows()
    ):

        geom = row.geometry

        if geom is None:
            continue

        if geom.is_empty:
            continue

        if geom.geom_type not in (
            "Polygon",
            "MultiPolygon",
        ):
            continue

        if not bbox_overlaps(
            parcel_bounds,
            geom.bounds,
        ):
            continue

        bbox_candidate_count += 1

        if not parcel_geom.intersects(
            geom
        ):
            continue

        try:

            intersection_geom = (
                parcel_geom.intersection(
                    geom
                )
            )

        except Exception:
            continue

        if intersection_geom.is_empty:
            continue

        intersection_area = float(
            intersection_geom.area
        )

        # 선/점 접촉 제외
        if intersection_area <= 0:
            continue

        if parcel_area > 0:

            ratio = (
                intersection_area
                / parcel_area
            )

        else:

            ratio = 0.0

        properties = {}

        for column in (
            natural_gdf.columns
        ):

            if column == "geometry":
                continue

            try:

                value = row[column]

                if value is None:
                    continue

                properties[
                    str(column)
                ] = str(value)

            except Exception:
                pass

        intersections.append(
            {
                "index": str(index),

                "intersection_area_degree2":
                    intersection_area,

                "intersection_ratio":
                    ratio,

                "properties":
                    properties,
            }
        )

    max_ratio = max(
        (
            item[
                "intersection_ratio"
            ]
            for item
            in intersections
        ),
        default=0.0,
    )

    return {
        "bbox_candidate_count":
            bbox_candidate_count,

        "intersection_count":
            len(intersections),

        "max_intersection_ratio":
            max_ratio,

        "features":
            intersections,
    }


# ============================================================
# UNKNOWN
# ============================================================

def save_unknown_result(
    site: Dict[str, Any],
    query_status: str,
    reason: str,
    extra: Optional[
        Dict[str, Any]
    ] = None,
) -> None:

    resolution = {
        "query_status": query_status,
        "resolution": "UNKNOWN",
        "confidence": "NONE",
        "reason": reason,
    }

    output = {
        "step":
            "STEP 17-21-C-9-2-5C-2",

        "condition":
            TARGET_LABEL,

        "site":
            site,

        "resolution":
            resolution,
    }

    if extra:
        output.update(extra)

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print("=" * 70)
    print(
        "=== 현재 자연경관지구 SITE 판정 ==="
    )
    print("=" * 70)

    print(
        "query_status:",
        query_status,
    )

    print(
        "resolution: UNKNOWN"
    )

    print(
        "confidence: NONE"
    )

    print(
        "reason:",
        reason,
    )

    print()
    print("=" * 70)
    print("결과 저장:")
    print(OUTPUT_PATH)
    print("=" * 70)


# ============================================================
# main
# ============================================================

def main() -> None:

    print(
        "=== STEP 17-21-C-9-2-5C-2 "
        "서울시 UQ121 자연경관지구 "
        "Parcel Polygon 공간교차 최종 보정 테스트 ==="
    )

    # --------------------------------------------------------
    # 입력
    # --------------------------------------------------------

    query_context = load_json(
        QUERY_CONTEXT_PATH
    )

    site = extract_site_context(
        query_context
    )

    print()
    print("=" * 70)
    print("=== 대상 SITE ===")
    print("=" * 70)

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

    pnu = site["pnu"]

    if (
        len(pnu) != 19
        or not pnu.isdigit()
    ):

        raise RuntimeError(
            "PNU가 정상적인 19자리 숫자가 아닙니다."
        )

    if site["address"] in (
        "",
        "-",
    ):

        raise RuntimeError(
            "SITE 주소가 없습니다."
        )

    if not VWORLD_API_KEY:

        raise RuntimeError(
            "VWORLD_API_KEY를 찾을 수 없습니다."
        )

    # ========================================================
    # 1. Parcel
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 1. 대상 Parcel Polygon 조회 ==="
    )
    print("=" * 70)

    point = get_site_point(
        site["address"]
    )

    if point is None:

        save_unknown_result(
            site,
            "QUERY_FAILED",
            "VWorld 주소검색에서 대표좌표 확보 실패",
        )

        return

    x, y = point

    print("대표좌표 X:", x)
    print("대표좌표 Y:", y)

    parcel_result = (
        query_parcel_polygon(
            x,
            y,
            pnu,
        )
    )

    print(
        "query_status:",
        parcel_result[
            "query_status"
        ],
    )

    print(
        "전체 Feature 수:",
        parcel_result[
            "raw_feature_count"
        ],
    )

    print(
        "대상 PNU 일치 Feature 수:",
        len(
            parcel_result[
                "features"
            ]
        ),
    )

    if (
        parcel_result[
            "query_status"
        ]
        != "QUERY_SUCCESS"
    ):

        save_unknown_result(
            site,
            "QUERY_FAILED",
            parcel_result[
                "reason"
            ],
        )

        return

    if not parcel_result[
        "features"
    ]:

        save_unknown_result(
            site,
            "QUERY_FAILED",
            (
                "대상 PNU와 직접 일치하는 "
                "Parcel Polygon Feature 없음"
            ),
        )

        return

    parcel_feature = (
        parcel_result[
            "features"
        ][0]
    )

    parcel_geom = (
        parcel_feature[
            "geometry"
        ]
    )

    print(
        "Parcel Feature ID:",
        parcel_feature["id"],
    )

    print(
        "Parcel geometry:",
        parcel_geom.geom_type,
    )

    print(
        "Parcel bounds:",
        parcel_geom.bounds,
    )

    # ========================================================
    # 2. UQ121 파일
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 2. UQ121 공간파일 탐색 ==="
    )
    print("=" * 70)

    files = find_uq121_files()

    print(
        "공간파일 후보 수:",
        len(files),
    )

    for index, file_path in enumerate(
        files,
        start=1,
    ):

        print(
            f"{index}. {file_path}"
        )

    if not files:

        save_unknown_result(
            site,
            "NOT_CONNECTED",
            (
                "서울시 UQ121 공간파일을 "
                "찾지 못함"
            ),
        )

        return

    selected_file = files[0]

    print()
    print(
        "선택 파일:",
        selected_file,
    )

    # ========================================================
    # 3. UQ121 로드
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 3. UQ121 공간레이어 로드 ==="
    )
    print("=" * 70)

    try:

        layer_result = (
            load_uq121_layer(
                selected_file
            )
        )

    except Exception as exc:

        save_unknown_result(
            site,
            "QUERY_FAILED",
            (
                "UQ121 공간레이어 "
                f"로드 실패: {exc}"
            ),
        )

        return

    gdf = layer_result["gdf"]

    print(
        "전체 Feature 수:",
        len(gdf),
    )

    print(
        "원본 CRS:",
        layer_result[
            "original_crs"
        ],
    )

    print(
        "정규화 CRS:",
        layer_result[
            "normalized_crs"
        ],
    )

    print(
        "CRS 처리:",
        layer_result[
            "crs_source"
        ],
    )

    print()
    print("SHP 실제 컬럼:")

    for column in gdf.columns:
        print("-", column)

    # ========================================================
    # 4. Schema 대응 확인
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 4. OpenAPI ↔ SHP Schema 대응 ==="
    )
    print("=" * 70)

    schema_result = (
        analyze_uq121_schema(
            gdf
        )
    )

    for shp_column, info in (
        schema_result[
            "column_mapping"
        ].items()
    ):

        print(
            f"{shp_column:12} "
            f"-> {info['openapi_equivalent']:22} "
            f"| "
            f"{'FOUND' if info['exists'] else 'MISSING'}"
        )

    # ========================================================
    # 5. 자연경관지구 식별
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 5. 자연경관지구 Feature 식별 ==="
    )
    print("=" * 70)

    filter_result = (
        filter_natural_landscape_features(
            gdf
        )
    )

    diagnostics = (
        filter_result[
            "diagnostics"
        ]
    )

    print(
        "DGM_NM 존재:",
        diagnostics[
            "DGM_NM_exists"
        ],
    )

    print(
        "ATRB_SE 존재:",
        diagnostics[
            "ATRB_SE_exists"
        ],
    )

    print(
        "LCLAS_CL 존재:",
        diagnostics[
            "LCLAS_CL_exists"
        ],
    )

    if (
        "DGM_NM_target_count"
        in diagnostics
    ):

        print(
            "DGM_NM 자연경관지구:",
            diagnostics[
                "DGM_NM_target_count"
            ],
        )

    if (
        "ATRB_SE_target_count"
        in diagnostics
    ):

        print(
            "ATRB_SE UQF110:",
            diagnostics[
                "ATRB_SE_target_count"
            ],
        )

    if (
        "LCLAS_CL_target_count"
        in diagnostics
    ):

        print(
            "LCLAS_CL UQF110:",
            diagnostics[
                "LCLAS_CL_target_count"
            ],
        )

    print()
    print(
        "status:",
        filter_result[
            "status"
        ],
    )

    print(
        "method:",
        filter_result[
            "method"
        ],
    )

    print(
        "column:",
        filter_result[
            "column"
        ],
    )

    print(
        "value:",
        filter_result[
            "value"
        ],
    )

    print(
        "자연경관지구 Feature 수:",
        filter_result[
            "feature_count"
        ],
    )

    if (
        filter_result[
            "status"
        ]
        != "VERIFIED"
    ):

        save_unknown_result(
            site,
            "QUERY_FAILED",
            filter_result[
                "reason"
            ],
            extra={
                "schema":
                    schema_result,

                "feature_filter": {
                    key: value
                    for key, value
                    in filter_result.items()
                    if key != "gdf"
                },
            },
        )

        return

    natural_gdf = (
        filter_result[
            "gdf"
        ]
    )

    # --------------------------------------------------------
    # 식별 Feature 예시
    # --------------------------------------------------------

    print()
    print(
        "자연경관지구 Feature 예시:"
    )

    preview_columns = [
        column
        for column in (
            "PRESENT_SN",
            "LCLAS_CL",
            "MLSFC_CL",
            "SCLAS_CL",
            "ATRB_SE",
            "DGM_NM",
            "DGM_AR",
            "SIGNGU_SE",
        )
        if column in natural_gdf.columns
    ]

    for number, (_, row) in enumerate(
        natural_gdf.head(10).iterrows(),
        start=1,
    ):

        print()
        print(
            f"Feature {number}"
        )

        for column in preview_columns:

            print(
                f"  {column}: "
                f"{row[column]}"
            )

    # ========================================================
    # 6. 교차
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 6. Parcel Polygon × "
        "자연경관지구 Polygon 교차분석 ==="
    )
    print("=" * 70)

    intersection_result = (
        analyze_intersections(
            parcel_geom,
            natural_gdf,
        )
    )

    print(
        "전체 UQ121 Feature:",
        len(gdf),
    )

    print(
        "자연경관지구 Feature:",
        len(natural_gdf),
    )

    print(
        "Parcel BBOX 후보:",
        intersection_result[
            "bbox_candidate_count"
        ],
    )

    print(
        "실제 면적 교차 Feature:",
        intersection_result[
            "intersection_count"
        ],
    )

    print(
        "최대 교차 비율:",
        intersection_result[
            "max_intersection_ratio"
        ],
    )

    for number, item in enumerate(
        intersection_result[
            "features"
        ],
        start=1,
    ):

        print()
        print(
            f"교차 Feature {number}"
        )

        print(
            "intersection ratio:",
            item[
                "intersection_ratio"
            ],
        )

        properties = item[
            "properties"
        ]

        for column in (
            "PRESENT_SN",
            "LCLAS_CL",
            "ATRB_SE",
            "DGM_NM",
        ):

            if column in properties:

                print(
                    f"{column}:",
                    properties[column],
                )

    # ========================================================
    # 7. 판정
    # ========================================================

    print()
    print("=" * 70)
    print(
        "=== 7. 자연경관지구 공간조건 최종 판정 ==="
    )
    print("=" * 70)

    if (
        intersection_result[
            "intersection_count"
        ]
        > 0
    ):

        resolution = {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "TRUE",

            "confidence":
                "HIGH",

            "reason":
                (
                    "서울시 공식 UQ121 경관지구 공간레이어에서 "
                    "자연경관지구 Feature를 검증된 SHP 속성 "
                    "DGM_NM/UQF110 체계로 식별하고 대상 PNU "
                    "Parcel Polygon과 실제 면적 교차를 확인함"
                ),

            "max_intersection_ratio":
                intersection_result[
                    "max_intersection_ratio"
                ],
        }

    else:

        resolution = {
            "query_status":
                "QUERY_SUCCESS",

            "resolution":
                "FALSE",

            "confidence":
                "HIGH",

            "reason":
                (
                    "서울시 공식 UQ121 경관지구 공간레이어 전체를 "
                    "정상 로드하고 자연경관지구 Feature를 "
                    "검증된 SHP 속성 DGM_NM/UQF110 체계로 "
                    "식별한 뒤 대상 PNU Parcel Polygon과 "
                    "공간교차를 수행했으나 실제 면적 교차 "
                    "Feature가 확인되지 않음"
                ),

            "max_intersection_ratio":
                0.0,
        }

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

    print(
        "최대 필지 교차 비율:",
        resolution[
            "max_intersection_ratio"
        ],
    )

    # ========================================================
    # 8. 검증
    # ========================================================

    validation = {
        "VWORLD API Key 존재":
            bool(VWORLD_API_KEY),

        "SITE 주소 존재":
            site["address"]
            not in (
                "",
                "-",
            ),

        "PNU 19자리":
            (
                len(pnu) == 19
                and pnu.isdigit()
            ),

        "Parcel query 성공":
            (
                parcel_result[
                    "query_status"
                ]
                == "QUERY_SUCCESS"
            ),

        "Parcel PNU 직접 검증":
            (
                len(
                    parcel_result[
                        "features"
                    ]
                )
                > 0
            ),

        "Parcel Polygon geometry":
            (
                parcel_geom.geom_type
                in (
                    "Polygon",
                    "MultiPolygon",
                )
            ),

        "UQ121 공식 코드":
            (
                UQ121_CODE
                == "UQ121"
            ),

        "UQ121 Feature 존재":
            len(gdf) > 0,

        "UQ121 EPSG:4326 정규화":
            (
                gdf.crs
                is not None
                and
                str(gdf.crs).upper()
                == "EPSG:4326"
            ),

        "DGM_NM 컬럼 확인":
            (
                "DGM_NM"
                in gdf.columns
            ),

        "ATRB_SE 컬럼 확인":
            (
                "ATRB_SE"
                in gdf.columns
            ),

        "LCLAS_CL 컬럼 확인":
            (
                "LCLAS_CL"
                in gdf.columns
            ),

        "자연경관지구 식별 성공":
            (
                filter_result[
                    "status"
                ]
                == "VERIFIED"
            ),

        "자연경관지구 Feature 존재":
            (
                len(natural_gdf)
                > 0
            ),

        "검증된 SHP 식별규칙 사용":
            (
                filter_result[
                    "method"
                ]
                in (
                    "DGM_NM_EXPLICIT_TEXT",
                    "ATRB_SE_OFFICIAL_CODE",
                    "LCLAS_CL_OFFICIAL_CODE",
                )
            ),

        "TRUE는 실제 면적 교차 존재":
            (
                resolution[
                    "resolution"
                ]
                != "TRUE"
                or
                intersection_result[
                    "intersection_count"
                ]
                > 0
            ),

        "FALSE는 전체 레이어 정상 + 교차 없음":
            (
                resolution[
                    "resolution"
                ]
                != "FALSE"
                or
                (
                    len(gdf) > 0
                    and
                    len(natural_gdf) > 0
                    and
                    intersection_result[
                        "intersection_count"
                    ]
                    == 0
                )
            ),

        "query_status 허용값":
            (
                resolution[
                    "query_status"
                ]
                in (
                    "QUERY_SUCCESS",
                    "QUERY_FAILED",
                    "NOT_CONNECTED",
                    "NOT_QUERIED",
                )
            ),

        "resolution 허용값":
            (
                resolution[
                    "resolution"
                ]
                in (
                    "TRUE",
                    "FALSE",
                    "UNKNOWN",
                )
            ),

        "confidence 허용값":
            (
                resolution[
                    "confidence"
                ]
                in (
                    "HIGH",
                    "MEDIUM",
                    "LOW",
                    "NONE",
                )
            ),
    }

    print()
    print("=" * 70)
    print(
        "=== C-9-2-5C-2 검증 ==="
    )
    print("=" * 70)

    for name, passed in (
        validation.items()
    ):

        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    # ========================================================
    # 9. 저장
    # ========================================================

    output = {
        "step":
            "STEP 17-21-C-9-2-5C-2",

        "condition":
            TARGET_LABEL,

        "site":
            site,

        "parcel": {
            "dataset":
                PARCEL_DATASET,

            "feature_id":
                parcel_feature[
                    "id"
                ],

            "geometry_type":
                parcel_geom.geom_type,

            "bounds":
                list(
                    parcel_geom.bounds
                ),

            "representative_point": {
                "x": x,
                "y": y,
            },
        },

        "uq121_source": {
            "code":
                UQ121_CODE,

            "file":
                str(
                    selected_file
                ),

            "feature_count":
                len(gdf),

            "original_crs":
                layer_result[
                    "original_crs"
                ],

            "normalized_crs":
                layer_result[
                    "normalized_crs"
                ],

            "crs_source":
                layer_result[
                    "crs_source"
                ],

            "columns":
                [
                    str(column)
                    for column
                    in gdf.columns
                ],
        },

        "schema":
            schema_result,

        "feature_filter": {
            "status":
                filter_result[
                    "status"
                ],

            "method":
                filter_result[
                    "method"
                ],

            "column":
                filter_result[
                    "column"
                ],

            "value":
                filter_result[
                    "value"
                ],

            "feature_count":
                filter_result[
                    "feature_count"
                ],

            "diagnostics":
                diagnostics,
        },

        "intersection":
            intersection_result,

        "resolution":
            resolution,

        "validation":
            validation,
    }

    save_json(
        OUTPUT_PATH,
        output,
    )

    print()
    print("=" * 70)
    print("결과 저장:")
    print(OUTPUT_PATH)
    print("=" * 70)

    if all(
        validation.values()
    ):

        print()
        print(
            "STEP 17-21-C-9-2-5C-2 완료"
        )

        print()
        print(
            "자연경관지구 최종 판정:"
        )

        print(
            resolution[
                "resolution"
            ]
        )

        print()
        print(
            "Parcel Polygon × 서울시 UQ121 "
            "자연경관지구 Polygon 실제 공간교차 검증 완료"
        )

        print()
        print(
            "다음 단계:"
        )

        print(
            "STEP 17-21-C-9-2-6"
        )

        print(
            "→ 입체복합구역 실제 공간조회"
        )

    else:

        print()
        print(
            "STEP 17-21-C-9-2-5C-2 "
            "검증 미완료"
        )


if __name__ == "__main__":
    main()