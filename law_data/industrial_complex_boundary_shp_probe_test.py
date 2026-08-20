# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-11A-1
국토교통부 산업단지 경계도면 SHP source / schema probe

목표
======================================================================
1. 국토교통부 공식 산업단지 경계도면 SHP를 탐색한다.
2. SHP를 정상 로드한다.
3. CRS / encoding / feature count / schema를 확인한다.
4. 산업단지명 / 산업단지 유형 필드를 식별한다.
5. 실제 Parcel intersection 전에는 TRUE/FALSE를 판정하지 않는다.
"""

from __future__ import annotations

import json
import tempfile
import zipfile

from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd


# ============================================================
# STEP
# ============================================================

STEP_NAME = (
    "STEP 17-21-C-9-2-11A-1 "
    "국토교통부 산업단지 경계도면 SHP source / schema probe"
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

OUTPUT_PATH = (
    OUTPUT_DIR
    / "industrial_complex_boundary_shp_probe.json"
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
# 파일 탐색
# ============================================================

def find_industrial_boundary_files() -> List[Path]:

    result: List[Path] = []

    keywords = (
        "산업단지",
        "경계",
    )

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():
            continue

        for path in base_dir.rglob("*"):

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

            if all(
                keyword in name
                for keyword
                in keywords
            ):

                result.append(
                    path
                )

        # 영문 파일명인 경우 보조 탐색
        for pattern in (
            "*industrial*.zip",
            "*industrial*.shp",
            "*danji*.zip",
            "*danji*.shp",
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

    # 이름에 산업단지 또는 dan이 포함된 SHP 우선
    for path in shp_files:

        name = (
            path.name
            .lower()
        )

        if (
            "산업"
            in name
            or "dan"
            in name
        ):

            return path

    return shp_files[
        0
    ]


# ============================================================
# SHP 로드
# ============================================================

def load_layer(
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
                    "ZIP 내부 SHP 파일을 찾지 못했습니다."
                )

        else:

            shp_path = (
                path
            )

        gdf = None

        errors = []

        # 공식 과거 설명에서는 UTF-8이라고 명시되어 있으나
        # 실제 파일 encoding을 추정하지 않고 여러 후보로 검증한다.
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

                errors.append(
                    f"{encoding}: {exc}"
                )

        if gdf is None:

            raise RuntimeError(
                "SHP 로드 실패: "
                + " | ".join(
                    errors
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
# schema 분석
# ============================================================

def analyze_schema(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    columns = [
        str(
            column
        )
        for column
        in gdf.columns
    ]

    lower_map = {
        str(
            column
        ).lower(): str(
            column
        )
        for column
        in gdf.columns
    }

    # 공식 과거 schema의 여러 표기 변형 대응
    id_candidates = (
        "dan_id",
        "danid",
        "dan_id_",
    )

    name_candidates = (
        "dan_name",
        "danname",
        "dan_nm",
        "name",
    )

    type_candidates = (
        "dan_type",
        "dantype",
        "dan_ty",
        "type",
    )

    def find_column(
        candidates,
    ):

        for candidate in candidates:

            if (
                candidate
                in lower_map
            ):

                return lower_map[
                    candidate
                ]

        return None

    id_column = (
        find_column(
            id_candidates
        )
    )

    name_column = (
        find_column(
            name_candidates
        )
    )

    type_column = (
        find_column(
            type_candidates
        )
    )

    name_values = []

    if (
        name_column
        and name_column
        in gdf.columns
    ):

        name_values = sorted(
            {
                safe_string(
                    value
                )
                for value
                in gdf[
                    name_column
                ].tolist()
                if safe_string(
                    value
                )
            }
        )

    type_values = []

    if (
        type_column
        and type_column
        in gdf.columns
    ):

        type_values = sorted(
            {
                safe_string(
                    value
                )
                for value
                in gdf[
                    type_column
                ].tolist()
                if safe_string(
                    value
                )
            }
        )

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

    return {
        "columns": (
            columns
        ),
        "id_column": (
            id_column
        ),
        "name_column": (
            name_column
        ),
        "type_column": (
            type_column
        ),
        "name_values_preview": (
            name_values[
                :30
            ]
        ),
        "name_value_count": (
            len(
                name_values
            )
        ),
        "type_values": (
            type_values
        ),
        "geometry_types": (
            geometry_types
        ),
        "valid_geometry_count": (
            valid_geometry_count
        ),
        "feature_count": (
            len(
                gdf
            )
        ),
    }


# ============================================================
# main
# ============================================================

def main() -> int:

    print_section(
        STEP_NAME
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
                "국토교통부 산업단지 경계도면 "
                "공식 SHP 파일을 찾지 못함"
            ),
        }

        result = {
            "step": (
                STEP_NAME
            ),
            "condition": (
                "산업단지"
            ),
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        print(
            resolution[
                "reason"
            ]
        )

        return 0

    # ========================================================
    # SHP 로드
    # ========================================================

    print_section(
        "1. 공식 산업단지 경계 SHP 로드"
    )

    try:

        layer = (
            load_layer(
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
                "산업단지 공식 SHP 로드 실패: "
                f"{exc}"
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

    gdf = (
        layer[
            "gdf"
        ]
    )

    print(
        "source:",
        layer.get(
            "source_path"
        ),
    )

    print(
        "SHP:",
        layer.get(
            "shp_path"
        ),
    )

    print(
        "Feature count:",
        layer.get(
            "feature_count"
        ),
    )

    print(
        "CRS:",
        layer.get(
            "crs"
        ),
    )

    print(
        "columns:",
        layer.get(
            "columns"
        ),
    )

    # ========================================================
    # schema
    # ========================================================

    print_section(
        "2. 공식 schema 분석"
    )

    schema = (
        analyze_schema(
            gdf
        )
    )

    print(
        "ID column:",
        schema.get(
            "id_column"
        ),
    )

    print(
        "Name column:",
        schema.get(
            "name_column"
        ),
    )

    print(
        "Type column:",
        schema.get(
            "type_column"
        ),
    )

    print(
        "Type values:",
        schema.get(
            "type_values"
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
        "Industrial complex names preview:"
    )

    for name in (
        schema.get(
            "name_values_preview",
            [],
        )
    ):

        print(
            "-",
            name,
        )

    # ========================================================
    # 현재 상태
    # ========================================================

    print_section(
        "3. 현재 판정 상태"
    )

    geometry_ok = (
        schema.get(
            "valid_geometry_count"
        )
        == schema.get(
            "feature_count"
        )
        and schema.get(
            "feature_count",
            0
        )
        > 0
    )

    polygon_ok = all(
        geometry_type
        in (
            "Polygon",
            "MultiPolygon",
        )
        for geometry_type
        in schema.get(
            "geometry_types",
            [],
        )
    )

    if (
        geometry_ok
        and polygon_ok
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
                "국토교통부 공식 산업단지 경계 "
                "Polygon SHP를 정상 확보함. "
                "다음 단계에서 대상 PNU Parcel Polygon과 "
                "실제 공간교차 필요"
            ),
        }

        next_step = (
            "STEP 17-21-C-9-2-11B "
            "산업단지 경계 Parcel Polygon 실제 공간교차"
        )

    else:

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
                "산업단지 공식 SHP는 로드됐으나 "
                "유효한 Polygon 전체 layer로 "
                "검증하지 못함"
            ),
        }

        next_step = (
            "산업단지 SHP geometry/schema 보정"
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

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "산업단지"
        ),

        "official_source": {
            "provider": (
                "국토교통부"
            ),
            "dataset": (
                "산업단지 경계도면"
            ),
            "coverage": (
                "전국"
            ),
            "included_types": [
                "국가산업단지",
                "일반산업단지",
                "도시첨단산업단지",
                "농공단지",
            ],
        },

        "layer": {
            "source_path": (
                layer.get(
                    "source_path"
                )
            ),
            "feature_count": (
                layer.get(
                    "feature_count"
                )
            ),
            "crs": (
                layer.get(
                    "crs"
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

        "resolution": (
            resolution
        ),

        "validation": {
            "공식 국토교통부 source": True,
            "전국 산업단지 경계": True,
            "국가산업단지 포함": True,
            "일반산업단지 포함": True,
            "도시첨단산업단지 포함": True,
            "농공단지 포함": True,
            "Polygon geometry 필요": True,
            "Parcel intersection 전 TRUE 금지": True,
            "Parcel intersection 전 FALSE 금지": True,
        },

        "next_step": (
            next_step
        ),
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