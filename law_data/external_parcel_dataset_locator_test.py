# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-2B
External Parcel Dataset Locator

목표
======================================================================
D:\\site-ai 외부에서 C-9 당시 사용했던 Parcel Polygon 원본을 찾는다.

검색 대상
======================================================================
LP_PA_CBND_BUBUN
PA_CBND_BUBUN
CBND
연속지적
parcel

검색 확장자
======================================================================
.shp
.zip
.gpkg
.geojson

주의
======================================================================
파일 내용을 읽지 않고 파일명 / 경로만 탐색한다.
대용량 공간파일 자체를 Git에 저장하지 않는다.
"""

from __future__ import annotations

import json
import os

from pathlib import Path
from typing import Any, Dict, List


# ============================================================
# PATH
# ============================================================

PROJECT_ROOT = Path(
    r"D:\site-ai"
)

SEARCH_ROOTS = [
    Path(r"D:\\"),
]


OUTPUT_DIR = (
    PROJECT_ROOT
    / "law_data"
    / "output"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "external_parcel_dataset_locator.json"
)


# ============================================================
# search config
# ============================================================

EXACT_KEYWORDS = [
    "LP_PA_CBND_BUBUN",
    "PA_CBND_BUBUN",
]

LOOSE_KEYWORDS = [
    "CBND",
    "BUBUN",
    "PARCEL",
    "연속지적",
    "지적",
]

SUPPORTED_SUFFIXES = {
    ".shp",
    ".zip",
    ".gpkg",
    ".geojson",
}


SKIP_DIR_NAMES = {
    "$RECYCLE.BIN",
    "System Volume Information",
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "WindowsApps",
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


def contains_any(
    text: str,
    keywords: List[str],
) -> bool:

    upper = (
        text.upper()
    )

    return any(
        keyword.upper()
        in upper
        for keyword
        in keywords
    )


def is_inside_project(
    path: Path,
) -> bool:

    try:

        path.resolve().relative_to(
            PROJECT_ROOT.resolve()
        )

        return True

    except ValueError:

        return False


# ============================================================
# scan
# ============================================================

def scan_root(
    root: Path,
) -> Dict[str, Any]:

    exact_hits = []
    loose_hits = []

    scanned_files = 0
    scanned_dirs = 0
    errors = []

    for current_root, dirs, files in os.walk(
        root,
        topdown=True,
    ):

        current_path = Path(
            current_root
        )

        # ----------------------------------------------------
        # skip folders
        # ----------------------------------------------------

        dirs[:] = [
            name
            for name in dirs
            if (
                name
                not in SKIP_DIR_NAMES
            )
        ]

        # 프로젝트 내부는 이미 검색했으므로 제외
        dirs[:] = [
            name
            for name in dirs
            if not is_inside_project(
                current_path
                / name
            )
        ]

        scanned_dirs += 1

        for filename in files:

            path = (
                current_path
                / filename
            )

            suffix = (
                path.suffix.lower()
            )

            if (
                suffix
                not in SUPPORTED_SUFFIXES
            ):
                continue

            scanned_files += 1

            try:

                stat = (
                    path.stat()
                )

                size = (
                    stat.st_size
                )

            except (
                PermissionError,
                OSError,
            ) as exc:

                errors.append(
                    {
                        "path": (
                            str(
                                path
                            )
                        ),

                        "error": (
                            str(
                                exc
                            )
                        ),
                    }
                )

                continue

            item = {
                "path": (
                    str(
                        path
                    )
                ),

                "filename": (
                    filename
                ),

                "suffix": (
                    suffix
                ),

                "size": (
                    size
                ),
            }

            if contains_any(
                filename,
                EXACT_KEYWORDS,
            ):

                exact_hits.append(
                    item
                )

                continue

            if contains_any(
                filename,
                LOOSE_KEYWORDS,
            ):

                loose_hits.append(
                    item
                )

    return {
        "root": (
            str(
                root
            )
        ),

        "scanned_dirs": (
            scanned_dirs
        ),

        "scanned_spatial_files": (
            scanned_files
        ),

        "exact_hits": (
            exact_hits
        ),

        "loose_hits": (
            loose_hits
        ),

        "errors": (
            errors
        ),
    }


# ============================================================
# ranking
# ============================================================

def candidate_score(
    item: Dict[str, Any],
) -> int:

    filename = (
        item[
            "filename"
        ].upper()
    )

    score = 0

    if (
        "LP_PA_CBND_BUBUN"
        in filename
    ):

        score += 100

    elif (
        "PA_CBND_BUBUN"
        in filename
    ):

        score += 90

    if (
        "CBND"
        in filename
    ):

        score += 30

    if (
        "BUBUN"
        in filename
    ):

        score += 20

    if (
        item[
            "suffix"
        ]
        == ".shp"
    ):

        score += 20

    elif (
        item[
            "suffix"
        ]
        == ".zip"
    ):

        score += 10

    return score


# ============================================================
# main
# ============================================================

def main() -> int:

    results = []

    for root in (
        SEARCH_ROOTS
    ):

        if not root.exists():

            results.append(
                {
                    "root": (
                        str(
                            root
                        )
                    ),

                    "exists": (
                        False
                    ),
                }
            )

            continue

        result = scan_root(
            root
        )

        result[
            "exists"
        ] = True

        results.append(
            result
        )

    all_exact = []

    all_loose = []

    for result in results:

        all_exact.extend(
            result.get(
                "exact_hits",
                []
            )
        )

        all_loose.extend(
            result.get(
                "loose_hits",
                []
            )
        )

    candidates = (
        all_exact
        + all_loose
    )

    ranked = sorted(
        candidates,
        key=candidate_score,
        reverse=True,
    )

    ranked = [
        {
            **item,
            "score": (
                candidate_score(
                    item
                )
            ),
        }
        for item
        in ranked
    ]

    resolution = (
        "SOURCE_FOUND"
        if ranked
        else "SOURCE_NOT_FOUND"
    )

    output = {
        "step": (
            "STEP 17-21-C-11-2C-2B "
            "external parcel dataset locator"
        ),

        "project_root": (
            str(
                PROJECT_ROOT
            )
        ),

        "search_roots": [
            str(
                root
            )
            for root
            in SEARCH_ROOTS
        ],

        "scan_results": (
            results
        ),

        "summary": {
            "exact_hit_count": (
                len(
                    all_exact
                )
            ),

            "loose_hit_count": (
                len(
                    all_loose
                )
            ),

            "candidate_count": (
                len(
                    ranked
                )
            ),
        },

        "ranked_candidates": (
            ranked
        ),

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
        "Search roots:",
        [
            str(
                root
            )
            for root
            in SEARCH_ROOTS
        ],
    )

    print()

    print(
        "Exact hits:",
        len(
            all_exact
        ),
    )

    print(
        "Loose hits:",
        len(
            all_loose
        ),
    )

    print()

    print(
        "=== TOP CANDIDATES ==="
    )

    if not ranked:

        print(
            "NONE"
        )

    for index, item in enumerate(
        ranked[
            :30
        ],
        start=1,
    ):

        print(
            f"[{index}] "
            f"score={item['score']} "
            f"| {item['path']}"
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

    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )