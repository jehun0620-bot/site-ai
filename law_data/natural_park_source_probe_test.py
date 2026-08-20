# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-12A
국토교통부 자연공원/용도지구 공식 SHP source / schema probe

목표
======================================================================
1. 국토교통부 공식 자연공원/용도지구 SHP를 탐색한다.
2. SHP를 정상 로드한다.
3. CRS / Feature 수 / 주요 schema만 간략 출력한다.
4. 상세 schema / 고유값은 JSON에 저장한다.
5. Parcel intersection 전에는 TRUE/FALSE를 확정하지 않는다.

콘솔 출력 원칙
======================================================================
- 핵심 진단값만 출력
- 긴 고유값 목록 출력 금지
- 상세 evidence는 JSON 파일에 저장
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
    "STEP 17-21-C-9-2-12A "
    "자연공원 공식 SHP source/schema probe"
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
    BASE_DIR
    / "law_data"
)

INPUT_DIR = (
    LAW_DATA_DIR
    / "input"
)

SPATIAL_DIR = (
    LAW_DATA_DIR
    / "spatial"
)

OUTPUT_DIR = (
    LAW_DATA_DIR
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "natural_park_source_probe.json"
)

EXPECTED_PREFIX = (
    "LSMD_CONT_UM102"
)


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
            "*자연공원*.zip",
            "*자연공원*.shp",
        ):

            for path in base_dir.rglob(
                pattern
            ):

                if path not in result:

                    result.append(
                        path
                    )

    # 5174 + 서울 파일 우선
    result.sort(
        key=lambda p: (
            0
            if (
                "5174" in p.name
                and "서울" in p.name
            )
            else 1,
            0
            if "서울" in p.name
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

    if not shp_files:
        return None

    for path in shp_files:

        if (
            EXPECTED_PREFIX
            in path.name.upper()
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

    temp_dir = None

    try:

        if (
            path.suffix.lower()
            == ".zip"
        ):

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
                "SHP 로드 실패: "
                + " | ".join(
                    read_errors
                )
            )

        return {
            "gdf": gdf,
            "source_path": str(
                path
            ),
            "shp_path": str(
                shp_path
            ),
            "feature_count": len(
                gdf
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

        if temp_dir is not None:

            temp_dir.cleanup()


# ============================================================
# schema 분석
# ============================================================

def get_unique_values(
    gdf: gpd.GeoDataFrame,
    column: str,
) -> List[str]:

    if (
        column
        not in gdf.columns
    ):

        return []

    return sorted(
        {
            safe_string(
                value
            )
            for value
            in gdf[
                column
            ].tolist()
            if safe_string(
                value
            )
        }
    )


def analyze_schema(
    gdf: gpd.GeoDataFrame,
) -> Dict[str, Any]:

    candidate_columns = [
        "MNUM",
        "ALIAS",
        "REMARK",
        "NTFDATE",
        "DGM_NM",
        "LBL_NM",
        "UQ_CD",
        "UQ_NM",
        "A1",
        "A2",
    ]

    candidate_values = {}

    for column in (
        candidate_columns
    ):

        if (
            column
            in gdf.columns
        ):

            values = (
                get_unique_values(
                    gdf,
                    column,
                )
            )

            candidate_values[
                column
            ] = {
                "count": len(
                    values
                ),
                "values": (
                    values
                ),
                "preview": (
                    values[:5]
                ),
            }

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
        "columns": [
            str(
                column
            )
            for column
            in gdf.columns
        ],
        "candidate_values": (
            candidate_values
        ),
        "geometry_types": (
            geometry_types
        ),
        "feature_count": (
            len(
                gdf
            )
        ),
        "valid_geometry_count": (
            valid_geometry_count
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
        find_files()
    )

    print(
        "found files:",
        len(
            files
        ),
    )

    if files:

        print(
            "selected:",
            files[0].name,
        )

    # ========================================================
    # 파일 없음
    # ========================================================

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
                "자연공원 공식 SHP 없음"
            ),
        }

        result = {
            "step": (
                STEP_NAME
            ),
            "condition": (
                "자연공원"
            ),
            "resolution": (
                resolution
            ),
        }

        save_json(
            result
        )

        print(
            "resolution: UNKNOWN"
        )

        print(
            "reason: 공식 SHP 없음"
        )

        print(
            "OUTPUT:",
            OUTPUT_PATH,
        )

        return 0

    # ========================================================
    # SHP 로드
    # ========================================================

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
                f"SHP 로드 실패: {exc}"
            ),
        }

        save_json(
            {
                "step": (
                    STEP_NAME
                ),
                "condition": (
                    "자연공원"
                ),
                "resolution": (
                    resolution
                ),
            }
        )

        print(
            "resolution: UNKNOWN"
        )

        print(
            "reason: SHP load failed"
        )

        return 0

    gdf = (
        layer[
            "gdf"
        ]
    )

    schema = (
        analyze_schema(
            gdf
        )
    )

    # ========================================================
    # 검증
    # ========================================================

    polygon_ok = (
        bool(
            schema[
                "geometry_types"
            ]
        )
        and all(
            geometry_type
            in (
                "Polygon",
                "MultiPolygon",
            )
            for geometry_type
            in schema[
                "geometry_types"
            ]
        )
    )

    geometry_ok = (
        schema[
            "valid_geometry_count"
        ]
        == schema[
            "feature_count"
        ]
        and schema[
            "feature_count"
        ]
        > 0
    )

    if (
        polygon_ok
        and geometry_ok
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
                "공식 자연공원 Polygon layer 정상. "
                "Parcel intersection 필요"
            ),
        }

        next_step = (
            "STEP 17-21-C-9-2-12B"
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
                "geometry/schema 검증 실패"
            ),
        }

        next_step = (
            "geometry/schema 보정"
        )

    # ========================================================
    # 상세 JSON
    # ========================================================

    result = {
        "step": (
            STEP_NAME
        ),

        "condition": (
            "자연공원"
        ),

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
            "shp_series": (
                "LSMD_CONT_UM102_*"
            ),
        },

        "layer": {
            "source_path": (
                layer[
                    "source_path"
                ]
            ),
            "shp_path": (
                layer[
                    "shp_path"
                ]
            ),
            "feature_count": (
                layer[
                    "feature_count"
                ]
            ),
            "crs": (
                layer[
                    "crs"
                ]
            ),
            "columns": (
                layer[
                    "columns"
                ]
            ),
        },

        "schema": (
            schema
        ),

        "resolution": (
            resolution
        ),

        "next_step": (
            next_step
        ),
    }

    save_json(
        result
    )

    # ========================================================
    # 초간략 콘솔 출력
    # ========================================================

    print(
        "Feature count:",
        layer[
            "feature_count"
        ],
    )

    print(
        "CRS:",
        layer[
            "crs"
        ],
    )

    print(
        "Geometry:",
        schema[
            "geometry_types"
        ],
    )

    print(
        "Geometry valid:",
        (
            f"{schema['valid_geometry_count']}"
            f"/{schema['feature_count']}"
        ),
    )

    # 실제 존재하는 주요 속성 컬럼만 한 줄씩 출력
    for column in (
        "MNUM",
        "ALIAS",
        "DGM_NM",
        "LBL_NM",
        "UQ_CD",
        "UQ_NM",
    ):

        info = (
            schema[
                "candidate_values"
            ].get(
                column
            )
        )

        if not info:
            continue

        print(
            f"{column}: "
            f"count={info['count']}, "
            f"preview={info['preview']}"
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