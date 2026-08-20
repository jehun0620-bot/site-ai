# -*- coding: utf-8 -*-

"""
STEP 17-21-C-9-2-13B
서울시 UQ145 기타용도구역 내 개발밀도관리구역 source probe

목표
======================================================================
1. 서울시 공식 UQ145 기타용도구역 SHP를 로드한다.
2. 실제 schema / 코드 / 명칭 값을 확인한다.
3. '개발밀도관리구역'이 실제 feature 속성에 존재하는지 확인한다.
4. 존재하더라도 Parcel intersection 전에는 TRUE/FALSE를 확정하지 않는다.
5. 콘솔은 핵심값만 출력하고 상세값은 JSON에 저장한다.
"""

from __future__ import annotations

import json
import math
import tempfile
import zipfile

from pathlib import Path
from typing import Any, Dict, List, Optional

import geopandas as gpd


STEP_NAME = (
    "STEP 17-21-C-9-2-13B "
    "서울시 UQ145 기타용도구역 내 개발밀도관리구역 probe"
)

TARGET_NAME = "개발밀도관리구역"

BASE_DIR = Path(__file__).resolve().parent.parent
LAW_DATA_DIR = BASE_DIR / "law_data"

INPUT_DIR = LAW_DATA_DIR / "input"
SPATIAL_DIR = LAW_DATA_DIR / "spatial"
OUTPUT_DIR = LAW_DATA_DIR / "output"

OUTPUT_PATH = (
    OUTPUT_DIR
    / "development_density_uq145_probe.json"
)


def save_json(data: Dict[str, Any]) -> None:

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


def safe_string(value: Any) -> str:

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

    text = str(value).strip()

    if text.lower() in (
        "nan",
        "none",
        "null",
    ):
        return ""

    return text


def find_files() -> List[Path]:

    result = []

    for base_dir in (
        INPUT_DIR,
        SPATIAL_DIR,
    ):

        if not base_dir.exists():
            continue

        for pattern in (
            "*UQ145*.zip",
            "*UQ145*.shp",
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
            if "202602" in p.name
            else 1,
            -(
                p.stat().st_mtime
                if p.exists()
                else 0
            ),
        )
    )

    return result


def find_shp(
    folder: Path,
) -> Optional[Path]:

    files = list(
        folder.rglob(
            "*.shp"
        )
    )

    if not files:
        return None

    for path in files:

        if "UQ145" in path.name.upper():
            return path

    return files[0]


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

            shp_path = find_shp(
                temp_path
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
            "feature_count": len(
                gdf
            ),
            "crs": (
                str(gdf.crs)
                if gdf.crs
                else None
            ),
            "columns": [
                str(column)
                for column
                in gdf.columns
            ],
        }

    finally:

        if temp_dir is not None:
            temp_dir.cleanup()


def unique_values(
    gdf: gpd.GeoDataFrame,
    column: str,
) -> List[str]:

    if column not in gdf.columns:
        return []

    return sorted(
        {
            safe_string(value)
            for value
            in gdf[column].tolist()
            if safe_string(value)
        }
    )


def main() -> int:

    files = find_files()

    print(
        "UQ145 files:",
        len(files),
    )

    if not files:

        print(
            "resolution: UNKNOWN"
        )

        print(
            "reason: UQ145 file not found"
        )

        return 0

    layer = load_layer(
        files[0]
    )

    gdf = layer[
        "gdf"
    ]

    # --------------------------------------------------------
    # 실제 존재하는 주요 UPIS 속성
    # --------------------------------------------------------

    candidate_columns = (
        "DGM_NM",
        "LCLAS_CL",
        "MLSFC_CL",
        "SCLAS_CL",
        "ATRB_SE",
        "PRESENT_SN",
    )

    values = {}

    for column in candidate_columns:

        if column in gdf.columns:

            values[
                column
            ] = unique_values(
                gdf,
                column,
            )

    # --------------------------------------------------------
    # 모든 문자열 컬럼에서 정확/부분 일치 탐색
    # --------------------------------------------------------

    exact_hits = []

    contains_hits = []

    for index, row in gdf.iterrows():

        matched_exact = False
        matched_contains = False

        matched_fields = {}

        for column in gdf.columns:

            if column == "geometry":
                continue

            text = safe_string(
                row.get(
                    column
                )
            )

            if not text:
                continue

            if TARGET_NAME == text:

                matched_exact = True
                matched_fields[
                    column
                ] = text

            elif TARGET_NAME in text:

                matched_contains = True
                matched_fields[
                    column
                ] = text

        if matched_exact:

            exact_hits.append(
                {
                    "index": (
                        int(index)
                        if isinstance(
                            index,
                            int,
                        )
                        else str(index)
                    ),
                    "fields": (
                        matched_fields
                    ),
                }
            )

        elif matched_contains:

            contains_hits.append(
                {
                    "index": (
                        int(index)
                        if isinstance(
                            index,
                            int,
                        )
                        else str(index)
                    ),
                    "fields": (
                        matched_fields
                    ),
                }
            )

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

    target_found = bool(
        exact_hits
        or contains_hits
    )

    if target_found:

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
                "서울시 공식 UQ145 기타용도구역에서 "
                "개발밀도관리구역 속성 Feature를 확인함. "
                "다음 단계에서 해당 Feature를 "
                "Parcel Polygon과 실제 교차해야 함"
            ),
        }

        next_step = (
            "STEP 17-21-C-9-2-13C "
            "개발밀도관리구역 Parcel intersection"
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
                "서울시 공식 UQ145 전체 layer는 "
                "정상 확인됐으나 개발밀도관리구역 "
                "Feature가 확인되지 않음. "
                "UQ145 부재만으로 FALSE 처리하지 않고 "
                "다른 공식 지정 source를 추가 확인해야 함"
            ),
        }

        next_step = (
            "개발밀도관리구역 다른 공식 source 탐색"
        )

    result = {
        "step": STEP_NAME,

        "condition": (
            TARGET_NAME
        ),

        "official_source": {
            "provider": (
                "서울특별시"
            ),
            "dataset": (
                "기타용도구역 공간정보"
            ),
            "dataset_code": (
                "UQ145"
            ),
            "crs": (
                layer[
                    "crs"
                ]
            ),
            "source_path": (
                layer[
                    "source_path"
                ]
            ),
        },

        "layer": {
            "feature_count": (
                len(gdf)
            ),
            "columns": (
                layer[
                    "columns"
                ]
            ),
            "geometry_types": (
                geometry_types
            ),
            "valid_geometry_count": (
                valid_geometry_count
            ),
        },

        "values": values,

        "target_search": {
            "exact_hit_count": (
                len(
                    exact_hits
                )
            ),
            "contains_hit_count": (
                len(
                    contains_hits
                )
            ),
            "exact_hits": (
                exact_hits
            ),
            "contains_hits": (
                contains_hits
            ),
        },

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

    # --------------------------------------------------------
    # 초간략 콘솔
    # --------------------------------------------------------

    print(
        "Feature:",
        len(gdf),
    )

    print(
        "CRS:",
        gdf.crs,
    )

    print(
        "Geometry valid:",
        f"{valid_geometry_count}/{len(gdf)}",
    )

    if "DGM_NM" in values:

        print(
            "DGM_NM:",
            values[
                "DGM_NM"
            ],
        )

    if "ATRB_SE" in values:

        print(
            "ATRB_SE:",
            values[
                "ATRB_SE"
            ],
        )

    print(
        "Target exact hits:",
        len(
            exact_hits
        ),
    )

    print(
        "Target contains hits:",
        len(
            contains_hits
        ),
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