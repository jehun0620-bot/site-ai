# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-2A
Local Parcel Dataset Locator

목표
======================================================================
로컬 프로젝트 안에서 LP_PA_CBND_BUBUN Parcel dataset의 실제
파일 위치를 찾는다.

지원 탐색
======================================================================
- .shp
- .zip 내부 shapefile
- .gpkg
- .geojson
- .json

주의
======================================================================
이번 단계에서는 geometry를 읽거나 SITE 객체를 수정하지 않는다.
실제 원본 dataset 위치만 찾는다.
"""

from __future__ import annotations

import json
import zipfile

from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# PATH
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

OUTPUT_DIR = (
    BASE_DIR
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "local_parcel_dataset_locator.json"
)


# ============================================================
# TARGET
# ============================================================

TARGET_NAMES = (
    "LP_PA_CBND_BUBUN",
    "PA_CBND_BUBUN",
)

SUPPORTED_SUFFIXES = {
    ".shp",
    ".zip",
    ".gpkg",
    ".geojson",
    ".json",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
}


# ============================================================
# util
# ============================================================

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


def contains_target(
    value: str,
) -> bool:

    upper = value.upper()

    return any(
        target.upper()
        in upper
        for target
        in TARGET_NAMES
    )


def should_skip(
    path: Path,
) -> bool:

    return any(
        part
        in SKIP_DIRS
        for part
        in path.parts
    )


# ============================================================
# direct file scan
# ============================================================

def scan_files() -> List[Dict[str, Any]]:

    hits = []

    for path in BASE_DIR.rglob(
        "*"
    ):

        if not path.is_file():
            continue

        if should_skip(
            path
        ):
            continue

        if (
            path.suffix.lower()
            not in SUPPORTED_SUFFIXES
        ):
            continue

        if contains_target(
            path.name
        ):

            hits.append(
                {
                    "kind": (
                        "DIRECT_FILE"
                    ),

                    "path": (
                        str(
                            path
                        )
                    ),

                    "relative_path": (
                        str(
                            path.relative_to(
                                BASE_DIR
                            )
                        )
                    ),

                    "suffix": (
                        path.suffix.lower()
                    ),

                    "size": (
                        path.stat().st_size
                    ),
                }
            )

    return hits


# ============================================================
# ZIP inspection
# ============================================================

def scan_zip_contents() -> List[Dict[str, Any]]:

    hits = []

    for zip_path in BASE_DIR.rglob(
        "*.zip"
    ):

        if should_skip(
            zip_path
        ):
            continue

        try:

            with zipfile.ZipFile(
                zip_path,
                "r",
            ) as zf:

                names = (
                    zf.namelist()
                )

                matched = [
                    name
                    for name
                    in names
                    if contains_target(
                        name
                    )
                ]

                if not matched:
                    continue

                shp_members = [
                    name
                    for name
                    in matched
                    if name.lower().endswith(
                        ".shp"
                    )
                ]

                hits.append(
                    {
                        "kind": (
                            "ZIP_CONTENT"
                        ),

                        "path": (
                            str(
                                zip_path
                            )
                        ),

                        "relative_path": (
                            str(
                                zip_path.relative_to(
                                    BASE_DIR
                                )
                            )
                        ),

                        "size": (
                            zip_path.stat().st_size
                        ),

                        "matched_members": (
                            matched
                        ),

                        "shp_members": (
                            shp_members
                        ),
                    }
                )

        except (
            zipfile.BadZipFile,
            PermissionError,
            OSError,
        ) as exc:

            hits.append(
                {
                    "kind": (
                        "ZIP_ERROR"
                    ),

                    "path": (
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

    return hits


# ============================================================
# looser spatial candidate search
#
# exact dataset 이름이 변경되었을 가능성을 대비한다.
# ============================================================

def scan_loose_candidates() -> List[Dict[str, Any]]:

    keywords = (
        "CBND",
        "PARCEL",
        "BUBUN",
        "연속지적",
        "지적",
    )

    hits = []

    for path in BASE_DIR.rglob(
        "*"
    ):

        if not path.is_file():
            continue

        if should_skip(
            path
        ):
            continue

        if (
            path.suffix.lower()
            not in {
                ".shp",
                ".zip",
                ".gpkg",
                ".geojson",
            }
        ):

            continue

        name_upper = (
            path.name.upper()
        )

        if not any(
            keyword.upper()
            in name_upper
            for keyword
            in keywords
        ):

            continue

        # exact hits와 구분
        if contains_target(
            path.name
        ):
            continue

        hits.append(
            {
                "path": (
                    str(
                        path
                    )
                ),

                "relative_path": (
                    str(
                        path.relative_to(
                            BASE_DIR
                        )
                    )
                ),

                "suffix": (
                    path.suffix.lower()
                ),

                "size": (
                    path.stat().st_size
                ),
            }
        )

    return hits


# ============================================================
# main
# ============================================================

def main() -> int:

    direct_hits = (
        scan_files()
    )

    zip_hits = (
        scan_zip_contents()
    )

    loose_hits = (
        scan_loose_candidates()
    )

    usable_zip_hits = [
        item
        for item
        in zip_hits
        if item.get(
            "kind"
        )
        == "ZIP_CONTENT"
    ]

    candidate_count = (
        len(
            direct_hits
        )
        + len(
            usable_zip_hits
        )
    )

    resolution = (
        "SOURCE_FOUND"
        if candidate_count
        > 0
        else "SOURCE_NOT_FOUND"
    )

    output = {
        "step": (
            "STEP 17-21-C-11-2C-2A "
            "local parcel dataset locator"
        ),

        "target_dataset": (
            "LP_PA_CBND_BUBUN"
        ),

        "project_root": (
            str(
                BASE_DIR
            )
        ),

        "direct_hits": (
            direct_hits
        ),

        "zip_hits": (
            zip_hits
        ),

        "loose_candidates": (
            loose_hits
        ),

        "summary": {
            "direct_hit_count": (
                len(
                    direct_hits
                )
            ),

            "zip_hit_count": (
                len(
                    usable_zip_hits
                )
            ),

            "loose_candidate_count": (
                len(
                    loose_hits
                )
            ),

            "candidate_count": (
                candidate_count
            ),
        },

        "resolution": (
            resolution
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Project root:",
        BASE_DIR,
    )

    print()

    print(
        "Target:",
        "LP_PA_CBND_BUBUN",
    )

    print()

    print(
        "Direct hits:",
        len(
            direct_hits
        ),
    )

    for item in direct_hits:

        print(
            "-",
            item[
                "relative_path"
            ],
            f"({item['suffix']})",
        )

    print()

    print(
        "ZIP hits:",
        len(
            usable_zip_hits
        ),
    )

    for item in usable_zip_hits:

        print(
            "-",
            item[
                "relative_path"
            ],
        )

        for member in item.get(
            "shp_members",
            [],
        ):

            print(
                "   SHP:",
                member,
            )

    print()

    print(
        "Loose spatial candidates:",
        len(
            loose_hits
        ),
    )

    for item in loose_hits[:20]:

        print(
            "-",
            item[
                "relative_path"
            ],
        )

    print()

    print(
        "resolution:",
        resolution,
    )

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    # locator이므로 SOURCE_NOT_FOUND도
    # script error로 처리하지 않는다.
    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )