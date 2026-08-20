# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-14D
도시지역편입해제구역 현행 공간상태 교차검증

검증
======================================================================
1. 서울시 공식 UQ111 도시지역 전체 layer
2. 서울시 공식 UQ141 개발제한구역 전체 layer
3. VWorld PNU Parcel 직접 일치
4. 모두 EPSG:5174로 통일
5. Parcel Polygon 실제 면적교차
6. 현행 상태는 history 최종판정의 보조 evidence로만 사용
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


STEP_NAME = (
    "STEP 17-21-C-9-2-14D "
    "도시지역편입해제구역 현행 공간상태 교차검증"
)

BASE_DIR = Path(__file__).resolve().parent.parent

LAW_DATA_DIR = BASE_DIR / "law_data"
INPUT_DIR = LAW_DATA_DIR / "input"
OUTPUT_DIR = LAW_DATA_DIR / "output"

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "urban_area_conversion_current_state.json"
)

load_dotenv(
    BASE_DIR / ".env"
)

VWORLD_API_KEY = os.getenv(
    "VWORLD_API_KEY"
)

VWORLD_SEARCH_URL = (
    "https://api.vworld.kr/req/search"
)

VWORLD_DATA_URL = (
    "https://api.vworld.kr/req/data"
)

PARCEL_DATASET = (
    "LP_PA_CBND_BUBUN"
)

TARGET_CRS = (
    "EPSG:5174"
)

TIMEOUT = 30


def safe_string(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip()


def load_json(
    path: Path,
) -> Dict[str, Any]:

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


def load_site() -> Dict[str, str]:

    data = load_json(
        QUERY_CONTEXT_PATH
    )

    context = data.get(
        "query_context",
        {},
    )

    return {
        "site_id": safe_string(
            context.get("site_id")
        ),
        "address": safe_string(
            context.get("address")
        ),
        "pnu": safe_string(
            context.get("pnu")
        ),
    }


def find_file(
    code: str,
) -> Optional[Path]:

    files = list(
        INPUT_DIR.rglob(
            f"*{code}*.zip"
        )
    )

    if not files:
        return None

    files.sort(
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )

    return files[0]


def find_shp(
    folder: Path,
    code: str,
) -> Optional[Path]:

    shp_files = list(
        folder.rglob("*.shp")
    )

    for path in shp_files:

        if code.upper() in path.name.upper():
            return path

    return (
        shp_files[0]
        if shp_files
        else None
    )


def load_layer(
    zip_path: Path,
    code: str,
) -> Dict[str, Any]:

    temp = tempfile.TemporaryDirectory()

    try:

        temp_path = Path(
            temp.name
        )

        with zipfile.ZipFile(
            zip_path,
            "r",
        ) as zf:

            zf.extractall(
                temp_path
            )

        shp_path = find_shp(
            temp_path,
            code,
        )

        if shp_path is None:

            raise RuntimeError(
                f"{code} SHP 없음"
            )

        gdf = None

        for encoding in (
            "cp949",
            "windows-949",
            "euc-kr",
            "utf-8",
            None,
        ):

            try:

                if encoding:

                    gdf = gpd.read_file(
                        shp_path,
                        encoding=encoding,
                    )

                else:

                    gdf = gpd.read_file(
                        shp_path
                    )

                break

            except Exception:
                pass

        if gdf is None:

            raise RuntimeError(
                f"{code} SHP 로드 실패"
            )

        return {
            "gdf": gdf.copy(),
            "source_path": str(
                zip_path
            ),
            "feature_count": len(
                gdf
            ),
            "crs": str(
                gdf.crs
            ),
            "columns": [
                str(c)
                for c
                in gdf.columns
            ],
        }

    finally:

        temp.cleanup()


def get_site_point(
    address: str,
) -> Optional[
    Tuple[float, float]
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
        "key": VWORLD_API_KEY,
    }

    response = requests.get(
        VWORLD_SEARCH_URL,
        params=params,
        timeout=TIMEOUT,
    )

    payload = response.json()

    items = (
        payload
        .get("response", {})
        .get("result", {})
        .get("items", [])
    )

    if not items:
        return None

    point = items[0].get(
        "point",
        {},
    )

    return (
        float(point["x"]),
        float(point["y"]),
    )


def get_parcel(
    point: Tuple[float, float],
    pnu: str,
):

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
            f"POINT({point[0]} {point[1]})"
        ),
        "size": 100,
    }

    response = requests.get(
        VWORLD_DATA_URL,
        params=params,
        timeout=TIMEOUT,
    )

    payload = response.json()

    features = (
        payload
        .get("response", {})
        .get("result", {})
        .get("featureCollection", {})
        .get("features", [])
    )

    for feature in features:

        props = feature.get(
            "properties",
            {},
        )

        if safe_string(
            props.get("pnu")
        ) != pnu:

            continue

        geom = shape(
            feature["geometry"]
        )

        return geom

    return None


def intersect_layer(
    parcel,
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    parcel_area = float(
        parcel.area
    )

    results = []

    positive = 0

    for index, row in gdf.iterrows():

        geom = row.geometry

        if (
            geom is None
            or geom.is_empty
        ):
            continue

        if not parcel.intersects(
            geom
        ):
            continue

        intersection = (
            parcel.intersection(
                geom
            )
        )

        area = float(
            intersection.area
        )

        if area > 0:
            positive += 1

        properties = {}

        for column in gdf.columns:

            if column == "geometry":
                continue

            value = row.get(
                column
            )

            text = safe_string(
                value
            )

            if text:

                properties[
                    column
                ] = text

        results.append(
            {
                "index": int(index),
                "intersection_area": area,
                "ratio": (
                    area / parcel_area
                    if parcel_area > 0
                    else 0
                ),
                "properties": properties,
            }
        )

    return {
        "intersection_count": len(
            results
        ),
        "positive_area_count": (
            positive
        ),
        "features": results,
    }


def main() -> int:

    site = load_site()

    uq111_path = find_file(
        "UQ111"
    )

    uq141_path = find_file(
        "UQ141"
    )

    if not uq111_path:

        print(
            "UQ111: MISSING"
        )
        return 1

    if not uq141_path:

        print(
            "UQ141: MISSING"
        )
        return 1

    uq111 = load_layer(
        uq111_path,
        "UQ111",
    )

    uq141 = load_layer(
        uq141_path,
        "UQ141",
    )

    point = get_site_point(
        site["address"]
    )

    if point is None:

        print(
            "Parcel point: FAIL"
        )
        return 1

    parcel_4326 = get_parcel(
        point,
        site["pnu"],
    )

    if parcel_4326 is None:

        print(
            "Parcel: FAIL"
        )
        return 1

    parcel_gdf = (
        gpd.GeoDataFrame(
            [{"pnu": site["pnu"]}],
            geometry=[
                parcel_4326
            ],
            crs="EPSG:4326",
        )
    )

    parcel_5174 = (
        parcel_gdf
        .to_crs(
            TARGET_CRS
        )
        .geometry
        .iloc[0]
    )

    # 공식 layer를 동일 CRS로 정규화
    uq111_gdf = (
        uq111["gdf"]
        .to_crs(
            TARGET_CRS
        )
    )

    uq141_gdf = (
        uq141["gdf"]
        .to_crs(
            TARGET_CRS
        )
    )

    urban = intersect_layer(
        parcel_5174,
        uq111_gdf,
    )

    greenbelt = intersect_layer(
        parcel_5174,
        uq141_gdf,
    )

    result = {
        "step": STEP_NAME,

        "condition": (
            "도시지역편입해제구역"
        ),

        "site": site,

        "parcel": {
            "pnu_direct_match": True,
            "crs": TARGET_CRS,
            "area": float(
                parcel_5174.area
            ),
        },

        "current_state": {
            "UQ111_urban_area": (
                urban
            ),
            "UQ141_greenbelt": (
                greenbelt
            ),
        },

        "resolution": {
            "resolution": (
                "UNKNOWN"
            ),
            "confidence": (
                "MEDIUM"
            ),
            "reason": (
                "현행 공간상태를 확인한 단계. "
                "과거 결정고시 전수검색 evidence와 "
                "결합하여 다음 단계에서 history "
                "최종 판정"
            ),
        },
    }

    save_json(
        result
    )

    print(
        "UQ111:",
        uq111["feature_count"],
        "/",
        uq111["crs"],
    )

    print(
        "UQ141:",
        uq141["feature_count"],
        "/",
        uq141["crs"],
    )

    print(
        "Parcel:",
        "OK",
    )

    print(
        "Urban area intersections:",
        urban[
            "positive_area_count"
        ],
    )

    print(
        "Greenbelt intersections:",
        greenbelt[
            "positive_area_count"
        ],
    )

    if urban[
        "features"
    ]:

        feature = urban[
            "features"
        ][0]

        # 속성은 너무 길지 않게 첫 feature만 출력
        print(
            "Urban properties:",
            feature[
                "properties"
            ],
        )

    print(
        "resolution: UNKNOWN"
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