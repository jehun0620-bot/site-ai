# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-1
Parcel Spatial Source Probe

목표
======================================================================
기존 law_data/output 안에서 현재 SITE의 Parcel Polygon과 관련된
geometry / area / bounds / CRS / dataset 정보를 찾아
실제 저장 구조를 확인한다.

이번 단계에서는 SITE Analysis 객체를 수정하지 않는다.

확인 대상
======================================================================
- geometry
- geometry type
- parcel area
- bounds
- CRS
- source dataset
- PNU
- strict PNU verification
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict, List


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
    / "site_parcel_spatial_source_probe.json"
)


# ============================================================
# candidate source files
# ============================================================

CANDIDATE_FILES = [

    "vworld_parcel_polygon_identifier_probe.json",

    "site_spatial_query_context.json",

    "mapplan_parcel_geometry_probe.json",

    "parcel_polygon_probe.json",

    "site_parcel_polygon.json",

    "site_spatial_condition_final_snapshot.json",
]


# ============================================================
# SEARCH KEYS
# ============================================================

GEOMETRY_KEYS = {
    "geometry",
    "geom",
    "parcel_geometry",
    "geojson",
}

AREA_KEYS = {
    "area",
    "parcel_area",
    "land_area",
    "geometry_area",
}

BOUNDS_KEYS = {
    "bounds",
    "bbox",
    "bounding_box",
}

CRS_KEYS = {
    "crs",
    "epsg",
    "srid",
}

DATASET_KEYS = {
    "dataset",
    "source_dataset",
    "layer",
    "table",
}

PNU_KEYS = {
    "pnu",
    "PNU",
}


# ============================================================
# util
# ============================================================

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


def short_value(
    value: Any,
    max_length: int = 500,
) -> Any:

    if isinstance(
        value,
        (
            dict,
            list,
        ),
    ):

        text = json.dumps(
            value,
            ensure_ascii=False,
            default=str,
        )

    else:

        text = str(
            value
        )

    if len(
        text
    ) <= max_length:

        return value

    return (
        text[
            :max_length
        ]
        + "..."
    )


# ============================================================
# recursive scan
# ============================================================

def scan_object(
    obj: Any,
    path: str = "$",
) -> List[
    Dict[str, Any]
]:

    hits = []

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            current_path = (
                f"{path}.{key}"
            )

            key_lower = str(
                key
            ).strip()

            categories = []

            if key_lower in GEOMETRY_KEYS:

                categories.append(
                    "GEOMETRY"
                )

            if key_lower in AREA_KEYS:

                categories.append(
                    "AREA"
                )

            if key_lower in BOUNDS_KEYS:

                categories.append(
                    "BOUNDS"
                )

            if key_lower in CRS_KEYS:

                categories.append(
                    "CRS"
                )

            if key_lower in DATASET_KEYS:

                categories.append(
                    "DATASET"
                )

            if key_lower in PNU_KEYS:

                categories.append(
                    "PNU"
                )

            if categories:

                hits.append(
                    {
                        "path": (
                            current_path
                        ),

                        "key": (
                            key
                        ),

                        "categories": (
                            categories
                        ),

                        "value_type": (
                            type(
                                value
                            ).__name__
                        ),

                        "value_preview": (
                            short_value(
                                value
                            )
                        ),
                    }
                )

            hits.extend(
                scan_object(
                    value,
                    current_path,
                )
            )

    elif isinstance(
        obj,
        list,
    ):

        for index, item in enumerate(
            obj
        ):

            hits.extend(
                scan_object(
                    item,
                    f"{path}[{index}]",
                )
            )

    return hits


# ============================================================
# geometry inspection
# ============================================================

def inspect_geometry(
    value: Any,
) -> Dict[str, Any]:

    result = {
        "recognized": False,
        "geometry_type": None,
        "coordinate_container": None,
    }

    if not isinstance(
        value,
        dict,
    ):

        return result

    geometry_type = (
        value.get(
            "type"
        )
    )

    coordinates = (
        value.get(
            "coordinates"
        )
    )

    if geometry_type in {
        "Polygon",
        "MultiPolygon",
    }:

        result[
            "recognized"
        ] = True

        result[
            "geometry_type"
        ] = (
            geometry_type
        )

        result[
            "coordinate_container"
        ] = (
            type(
                coordinates
            ).__name__
        )

    return result


# ============================================================
# main
# ============================================================

def main() -> int:

    files = []

    total_hits = []

    geometry_candidates = []

    for filename in (
        CANDIDATE_FILES
    ):

        path = (
            OUTPUT_DIR
            / filename
        )

        exists = (
            path.exists()
        )

        if not exists:

            files.append(
                {
                    "filename": (
                        filename
                    ),

                    "exists": (
                        False
                    ),

                    "hit_count": (
                        0
                    ),
                }
            )

            continue

        data = load_json(
            path
        )

        hits = scan_object(
            data
        )

        files.append(
            {
                "filename": (
                    filename
                ),

                "exists": (
                    True
                ),

                "hit_count": (
                    len(
                        hits
                    )
                ),

                "top_level_keys": (
                    sorted(
                        data.keys()
                    )
                    if isinstance(
                        data,
                        dict,
                    )
                    else []
                ),
            }
        )

        for hit in hits:

            item = {
                "filename": (
                    filename
                ),

                **hit,
            }

            total_hits.append(
                item
            )

            if (
                "GEOMETRY"
                in hit[
                    "categories"
                ]
            ):

                geometry_candidates.append(
                    item
                )

    # ========================================================
    # summary by category
    # ========================================================

    category_counts = {
        "GEOMETRY": 0,
        "AREA": 0,
        "BOUNDS": 0,
        "CRS": 0,
        "DATASET": 0,
        "PNU": 0,
    }

    for hit in total_hits:

        for category in hit[
            "categories"
        ]:

            if category in (
                category_counts
            ):

                category_counts[
                    category
                ] += 1

    # ========================================================
    # output
    # ========================================================

    output = {
        "step": (
            "STEP 17-21-C-11-2C-1 "
            "Parcel spatial source probe"
        ),

        "files": (
            files
        ),

        "summary": {
            "files_checked": (
                len(
                    CANDIDATE_FILES
                )
            ),

            "files_existing": (
                sum(
                    1
                    for item
                    in files
                    if item[
                        "exists"
                    ]
                )
            ),

            "total_hits": (
                len(
                    total_hits
                )
            ),

            "category_counts": (
                category_counts
            ),

            "geometry_candidate_count": (
                len(
                    geometry_candidates
                )
            ),
        },

        "geometry_candidates": (
            geometry_candidates
        ),

        "hits": (
            total_hits
        ),
    }

    save_json(
        output
    )

    # ========================================================
    # console
    # ========================================================

    print(
        "Files checked:",
        len(
            CANDIDATE_FILES
        ),
    )

    print(
        "Files existing:",
        output[
            "summary"
        ][
            "files_existing"
        ],
    )

    print()

    print(
        "Category counts:",
        category_counts,
    )

    print()

    print(
        "=== EXISTING FILES ==="
    )

    for item in files:

        if not item[
            "exists"
        ]:

            continue

        print(
            f"- {item['filename']} "
            f"| hits={item['hit_count']}"
        )

        print(
            "  top keys:",
            item.get(
                "top_level_keys"
            ),
        )

    print()

    print(
        "=== GEOMETRY CANDIDATES ==="
    )

    if not geometry_candidates:

        print(
            "NONE"
        )

    for item in (
        geometry_candidates
    ):

        print(
            "- file:",
            item[
                "filename"
            ],
        )

        print(
            "  path:",
            item[
                "path"
            ],
        )

        print(
            "  type:",
            item[
                "value_type"
            ],
        )

        print(
            "  preview:",
            item[
                "value_preview"
            ],
        )

    print()

    print(
        "=== AREA / BOUNDS / CRS ==="
    )

    for item in total_hits:

        categories = (
            item[
                "categories"
            ]
        )

        if not any(
            category
            in {
                "AREA",
                "BOUNDS",
                "CRS",
            }
            for category
            in categories
        ):

            continue

        print(
            f"- {item['filename']} "
            f"| {item['path']} "
            f"| {categories}"
        )

        print(
            "  value:",
            item[
                "value_preview"
            ],
        )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    # probe이므로 geometry가 없어도 failure로 처리하지 않는다.
    return 0


if __name__ == "__main__":

    raise SystemExit(
        main()
    )