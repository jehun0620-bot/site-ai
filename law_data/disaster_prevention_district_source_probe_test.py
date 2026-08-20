# -*- coding: utf-8 -*-

"""
STEP 17-21-C-10-2B-10A
서울시 방재지구 공식 SHP source / schema probe

목표
======================================================================
1. law_data/input에서 방재지구 관련 공식 SHP ZIP 탐색
2. SHP 로드
3. CRS / geometry / schema 확인
4. 방재지구 명칭 또는 코드체계 검증
5. 아직 SITE TRUE/FALSE 판정은 하지 않음
"""

from __future__ import annotations

import json
import tempfile
import zipfile

from pathlib import Path
from typing import Any, Dict, List

import geopandas as gpd


STEP_NAME = (
    "STEP 17-21-C-10-2B-10A "
    "서울시 방재지구 공식 SHP source/schema probe"
)


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

INPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "input"
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "disaster_prevention_district_source_probe.json"
)


# ============================================================
# 후보 파일명 / 키워드
# ============================================================

FILE_KEYWORDS = [
    "방재",
    "방재지구",
    "UQ",
    "LSMD_CONT",
]


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


def find_candidate_files() -> List[Path]:

    candidates = []

    for path in INPUT_DIR.glob(
        "*.zip"
    ):

        name = path.name

        if (
            "방재" in name
            or (
                "LSMD_CONT" in name
                and "서울" in name
            )
        ):

            candidates.append(
                path
            )

    return sorted(
        candidates
    )


def load_shp_from_zip(
    zip_path: Path,
):

    temp_dir = tempfile.TemporaryDirectory()

    with zipfile.ZipFile(
        zip_path,
        "r",
    ) as zf:

        zf.extractall(
            temp_dir.name
        )

    shp_files = list(
        Path(
            temp_dir.name
        ).rglob(
            "*.shp"
        )
    )

    if not shp_files:

        temp_dir.cleanup()

        raise FileNotFoundError(
            "ZIP 내부 SHP 없음"
        )

    # 보통 1개지만 여러 개면 전부 보여주기 위해 첫 번째 로드
    shp = shp_files[0]

    gdf = gpd.read_file(
        shp
    )

    return (
        temp_dir,
        shp,
        shp_files,
        gdf,
    )


def safe_unique(
    gdf,
    column: str,
    limit: int = 20,
):

    if column not in gdf.columns:
        return []

    values = (
        gdf[
            column
        ]
        .astype(
            str
        )
        .drop_duplicates()
        .tolist()
    )

    return values[:limit]


def main() -> int:

    candidates = (
        find_candidate_files()
    )

    print(
        "Candidate files:",
        len(
            candidates
        ),
    )

    for path in candidates[:20]:

        print(
            "-",
            path.name,
        )

    # ========================================================
    # 후보 없음
    # ========================================================

    if not candidates:

        output = {
            "step": STEP_NAME,

            "found_files": 0,

            "resolution": (
                "SOURCE_REQUIRED"
            ),

            "confidence": (
                "NONE"
            ),

            "reason": (
                "law_data/input에서 방재지구 공식 "
                "공간파일 후보를 찾지 못함"
            ),
        }

        save_json(
            output
        )

        print()
        print(
            "resolution: SOURCE_REQUIRED"
        )

        print(
            "OUTPUT:",
            OUTPUT_PATH,
        )

        return 0

    # ========================================================
    # 후보마다 probe
    # ========================================================

    probed = []

    for zip_path in candidates:

        try:

            (
                temp_dir,
                shp,
                shp_files,
                gdf,
            ) = load_shp_from_zip(
                zip_path
            )

            columns = list(
                gdf.columns
            )

            geometry_types = sorted(
                gdf.geometry
                .geom_type
                .dropna()
                .unique()
                .tolist()
            )

            valid_count = int(
                gdf.geometry
                .is_valid
                .sum()
            )

            feature_count = len(
                gdf
            )

            # -----------------------------------------------
            # 흔한 도시계획 SHP 필드 탐색
            # -----------------------------------------------

            candidate_name_columns = [
                column
                for column in columns
                if column.upper()
                in {
                    "DGM_NM",
                    "ALIAS",
                    "LBL_NM",
                    "NAME",
                    "UQ_NM",
                    "ZON_NM",
                }
            ]

            candidate_code_columns = [
                column
                for column in columns
                if (
                    "CL" in column.upper()
                    or "ATR" in column.upper()
                    or "CODE" in column.upper()
                    or column.upper()
                    in {
                        "MNUM",
                        "UQ_CD",
                    }
                )
            ]

            name_values = {}

            for column in (
                candidate_name_columns
            ):

                name_values[
                    column
                ] = safe_unique(
                    gdf,
                    column,
                )

            code_values = {}

            for column in (
                candidate_code_columns[:10]
            ):

                code_values[
                    column
                ] = safe_unique(
                    gdf,
                    column,
                )

            # -----------------------------------------------
            # 내용 중 방재 문자열 확인
            # -----------------------------------------------

            disaster_hits = {}

            for column in columns:

                if column == (
                    gdf.geometry.name
                ):
                    continue

                try:

                    series = (
                        gdf[
                            column
                        ]
                        .astype(
                            str
                        )
                    )

                    mask = (
                        series
                        .str
                        .contains(
                            "방재",
                            na=False,
                        )
                    )

                    hit_count = int(
                        mask.sum()
                    )

                    if hit_count:

                        disaster_hits[
                            column
                        ] = {
                            "count": (
                                hit_count
                            ),

                            "preview": (
                                series[
                                    mask
                                ]
                                .drop_duplicates()
                                .tolist()[
                                    :10
                                ]
                            ),
                        }

                except Exception:
                    pass

            probed.append(
                {
                    "file": (
                        str(
                            zip_path
                        )
                    ),

                    "shp": (
                        shp.name
                    ),

                    "shp_count": (
                        len(
                            shp_files
                        )
                    ),

                    "feature_count": (
                        feature_count
                    ),

                    "crs": (
                        str(
                            gdf.crs
                        )
                    ),

                    "columns": (
                        columns
                    ),

                    "geometry_types": (
                        geometry_types
                    ),

                    "geometry_valid": (
                        f"{valid_count}/{feature_count}"
                    ),

                    "name_values": (
                        name_values
                    ),

                    "code_values": (
                        code_values
                    ),

                    "disaster_hits": (
                        disaster_hits
                    ),
                }
            )

            temp_dir.cleanup()

        except Exception as exc:

            probed.append(
                {
                    "file": (
                        str(
                            zip_path
                        )
                    ),

                    "error": (
                        str(
                            exc
                        )
                    ),
                }
            )

    # ========================================================
    # 방재 데이터 여부
    # ========================================================

    matched = [
        item
        for item in probed
        if item.get(
            "disaster_hits"
        )
    ]

    if matched:

        resolution = (
            "SOURCE_FOUND"
        )

        confidence = (
            "MEDIUM"
        )

        reason = (
            "방재 문자열을 포함한 공식 공간파일 후보 확인. "
            "다음 단계에서 Parcel Polygon 실제 공간교차 필요"
        )

    else:

        resolution = (
            "SOURCE_UNVERIFIED"
        )

        confidence = (
            "NONE"
        )

        reason = (
            "공간파일은 확인했으나 방재지구 "
            "레이어라는 직접 evidence를 찾지 못함"
        )

    output = {
        "step": STEP_NAME,

        "found_files": (
            len(
                candidates
            )
        ),

        "probed": (
            probed
        ),

        "matched_source_count": (
            len(
                matched
            )
        ),

        "resolution": (
            resolution
        ),

        "confidence": (
            confidence
        ),

        "reason": (
            reason
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # concise output
    # ========================================================

    print()

    for index, item in enumerate(
        probed,
        start=1,
    ):

        print(
            f"[{index}]",
            Path(
                item[
                    "file"
                ]
            ).name,
        )

        if item.get(
            "error"
        ):

            print(
                "  ERROR:",
                item[
                    "error"
                ],
            )

            continue

        print(
            "  Feature:",
            item[
                "feature_count"
            ],
        )

        print(
            "  CRS:",
            item[
                "crs"
            ],
        )

        print(
            "  Geometry:",
            item[
                "geometry_types"
            ],
        )

        print(
            "  valid:",
            item[
                "geometry_valid"
            ],
        )

        print(
            "  disaster hits:",
            item[
                "disaster_hits"
            ],
        )

    print()

    print(
        "resolution:",
        resolution,
    )

    print(
        "confidence:",
        confidence,
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