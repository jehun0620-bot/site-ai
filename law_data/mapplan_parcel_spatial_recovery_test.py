# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-2D
MapPlan Parcel Spatial Recovery

목표
======================================================================
C-9 당시 저장된 MapPlan intersection snapshot에서
현재 SITE Parcel Polygon을 복구한다.

source:
law_data/output/seoul_urban_innovation_zone_mapplan_intersection.json

복구 대상:
- PNU
- GeoJSON geometry
- geometry type
- native MapPlan CRS
- area
- bounds

중요
======================================================================
로컬 SHP 또는 외부 원본을 다시 찾지 않는다.

기존 C-9 evidence snapshot 안에 보존된
MapPlan FeatureCollection을 재사용한다.
"""

from __future__ import annotations

import json
import re

from pathlib import Path
from typing import Any, Dict, List, Optional


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

SOURCE_PATH = (
    OUTPUT_DIR
    / "seoul_urban_innovation_zone_mapplan_intersection.json"
)

OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_parcel_spatial_recovery.json"
)

GEOJSON_OUTPUT_PATH = (
    OUTPUT_DIR
    / "site_parcel_spatial_snapshot.geojson"
)


# ============================================================
# TARGET
# ============================================================

TARGET_PNU = (
    "1168010300100120000"
)

EXPECTED_AREA = (
    120945.65223377591
)

EXPECTED_BOUNDS = [
    962201.02522,
    1943722.58159,
    962711.06096,
    1944220.16506,
]


# ============================================================
# util
# ============================================================

def load_json(
    path: Path,
) -> Dict[str, Any]:

    if not path.exists():

        raise FileNotFoundError(
            f"입력 파일 없음: {path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def save_json(
    path: Path,
    data: Any,
) -> None:

    OUTPUT_DIR.mkdir(
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
# recursive object scan
# ============================================================

def walk(
    obj: Any,
    path: str = "$",
):

    yield (
        path,
        obj,
    )

    if isinstance(
        obj,
        dict,
    ):

        for key, value in obj.items():

            yield from walk(
                value,
                f"{path}.{key}",
            )

    elif isinstance(
        obj,
        list,
    ):

        for index, value in enumerate(
            obj
        ):

            yield from walk(
                value,
                f"{path}[{index}]",
            )


# ============================================================
# direct feature detection
# ============================================================

def find_direct_features(
    data: Any,
) -> List[Dict[str, Any]]:

    features = []

    for path, obj in walk(
        data
    ):

        if not isinstance(
            obj,
            dict,
        ):
            continue

        geometry = (
            obj.get(
                "geometry"
            )
        )

        properties = (
            obj.get(
                "properties"
            )
        )

        if not isinstance(
            geometry,
            dict,
        ):

            continue

        if not isinstance(
            properties,
            dict,
        ):

            continue

        if (
            str(
                properties.get(
                    "pnu",
                    ""
                )
            )
            != TARGET_PNU
        ):

            continue

        features.append(
            {
                "path": (
                    path
                ),

                "feature": (
                    obj
                ),
            }
        )

    return features


# ============================================================
# embedded JSON string recovery
# ============================================================

def try_parse_json_string(
    text: str,
) -> Optional[Any]:

    stripped = (
        text.strip()
    )

    if not stripped:
        return None

    if not (
        stripped.startswith(
            "{"
        )
        or stripped.startswith(
            "["
        )
    ):

        return None

    try:

        return json.loads(
            stripped
        )

    except json.JSONDecodeError:

        return None


def find_embedded_features(
    data: Any,
) -> List[Dict[str, Any]]:

    matches = []

    for path, obj in walk(
        data
    ):

        if not isinstance(
            obj,
            str,
        ):

            continue

        if (
            TARGET_PNU
            not in obj
        ):

            continue

        if (
            "\"geometry\""
            not in obj
            and "'geometry'"
            not in obj
        ):

            continue

        # ----------------------------------------------------
        # 1. 문자열 전체가 JSON인지 먼저 검사
        # ----------------------------------------------------

        parsed = (
            try_parse_json_string(
                obj
            )
        )

        candidates = []

        if parsed is not None:

            candidates.append(
                parsed
            )

        # ----------------------------------------------------
        # 2. 문자열 내부 FeatureCollection 추출 시도
        # ----------------------------------------------------

        else:

            start = (
                obj.find(
                    '{"features"'
                )
            )

            if start < 0:

                start = (
                    obj.find(
                        '{"type":"FeatureCollection"'
                    )
                )

            if start >= 0:

                candidate_text = (
                    obj[
                        start:
                    ]
                )

                parsed_candidate = (
                    try_parse_json_string(
                        candidate_text
                    )
                )

                if (
                    parsed_candidate
                    is not None
                ):

                    candidates.append(
                        parsed_candidate
                    )

        # ----------------------------------------------------
        # candidate scan
        # ----------------------------------------------------

        for candidate in (
            candidates
        ):

            direct = (
                find_direct_features(
                    candidate
                )
            )

            for item in direct:

                matches.append(
                    {
                        "container_path": (
                            path
                        ),

                        "embedded_path": (
                            item[
                                "path"
                            ]
                        ),

                        "feature": (
                            item[
                                "feature"
                            ]
                        ),
                    }
                )

    return matches


# ============================================================
# area / bounds source recovery
# ============================================================

def find_numeric_value(
    data: Any,
    target: float,
    tolerance: float = 1e-6,
) -> List[
    Dict[str, Any]
]:

    hits = []

    for path, obj in walk(
        data
    ):

        if not isinstance(
            obj,
            (
                int,
                float,
            ),
        ):

            continue

        if abs(
            float(
                obj
            )
            - target
        ) <= tolerance:

            hits.append(
                {
                    "path": (
                        path
                    ),

                    "value": (
                        float(
                            obj
                        )
                    ),
                }
            )

    return hits


def find_bounds_array(
    data: Any,
) -> List[
    Dict[str, Any]
]:

    hits = []

    for path, obj in walk(
        data
    ):

        if not isinstance(
            obj,
            list,
        ):

            continue

        if len(
            obj
        ) != 4:

            continue

        if not all(
            isinstance(
                value,
                (
                    int,
                    float,
                ),
            )
            for value
            in obj
        ):

            continue

        if all(
            abs(
                float(
                    obj[index]
                )
                - EXPECTED_BOUNDS[
                    index
                ]
            )
            <= 1e-6

            for index
            in range(
                4
            )
        ):

            hits.append(
                {
                    "path": (
                        path
                    ),

                    "value": [
                        float(
                            value
                        )
                        for value
                        in obj
                    ],
                }
            )

    return hits


# ============================================================
# geometry bounds calculation
# ============================================================

def flatten_coordinates(
    value: Any,
) -> List[
    List[float]
]:

    points = []

    if (
        isinstance(
            value,
            list,
        )
        and len(
            value
        )
        >= 2
        and isinstance(
            value[
                0
            ],
            (
                int,
                float,
            ),
        )
        and isinstance(
            value[
                1
            ],
            (
                int,
                float,
            ),
        )
    ):

        points.append(
            [
                float(
                    value[
                        0
                    ]
                ),
                float(
                    value[
                        1
                    ]
                ),
            ]
        )

        return points

    if isinstance(
        value,
        list,
    ):

        for child in value:

            points.extend(
                flatten_coordinates(
                    child
                )
            )

    return points


def geometry_bounds(
    geometry: Dict[str, Any],
) -> Optional[
    List[float]
]:

    points = flatten_coordinates(
        geometry.get(
            "coordinates",
            [],
        )
    )

    if not points:

        return None

    xs = [
        point[
            0
        ]
        for point
        in points
    ]

    ys = [
        point[
            1
        ]
        for point
        in points
    ]

    return [
        min(
            xs
        ),
        min(
            ys
        ),
        max(
            xs
        ),
        max(
            ys
        ),
    ]


# ============================================================
# main
# ============================================================

def main() -> int:

    source = load_json(
        SOURCE_PATH
    )

    # ========================================================
    # geometry recovery
    # ========================================================

    direct_features = (
        find_direct_features(
            source
        )
    )

    embedded_features = (
        find_embedded_features(
            source
        )
    )

    selected_feature = None

    selected_source = None

    if direct_features:

        selected_feature = (
            direct_features[
                0
            ][
                "feature"
            ]
        )

        selected_source = {
            "mode": (
                "DIRECT_JSON"
            ),

            "path": (
                direct_features[
                    0
                ][
                    "path"
                ]
            ),
        }

    elif embedded_features:

        selected_feature = (
            embedded_features[
                0
            ][
                "feature"
            ]
        )

        selected_source = {
            "mode": (
                "EMBEDDED_JSON_STRING"
            ),

            "container_path": (
                embedded_features[
                    0
                ][
                    "container_path"
                ]
            ),

            "embedded_path": (
                embedded_features[
                    0
                ][
                    "embedded_path"
                ]
            ),
        }

    # ========================================================
    # evidence
    # ========================================================

    area_hits = (
        find_numeric_value(
            source,
            EXPECTED_AREA,
        )
    )

    bounds_hits = (
        find_bounds_array(
            source
        )
    )

    geometry = None
    properties = {}
    calculated_bounds = None

    if selected_feature:

        geometry = (
            selected_feature.get(
                "geometry"
            )
        )

        properties = (
            selected_feature.get(
                "properties",
                {},
            )
        )

        if isinstance(
            geometry,
            dict,
        ):

            calculated_bounds = (
                geometry_bounds(
                    geometry
                )
            )

    # ========================================================
    # source CRS
    #
    # MapPlan geometry bounds are projected coordinates.
    # Historical C-9 result used this native MapPlan coordinate space.
    # Current evidence is consistent with EPSG:5179-like Korean projected
    # coordinates, but this test must not guess a CRS without stored source.
    # ========================================================

    stored_crs = None

    for path, obj in walk(
        source
    ):

        if not isinstance(
            obj,
            dict,
        ):
            continue

        if "crs" not in obj:
            continue

        value = (
            obj.get(
                "crs"
            )
        )

        if value:

            stored_crs = (
                value
            )

            break

    crs_status = (
        "RECOVERED"
        if stored_crs
        else "SOURCE_CRS_NOT_EXPLICIT"
    )

    # ========================================================
    # validation
    # ========================================================

    geometry_type = (
        geometry.get(
            "type"
        )
        if isinstance(
            geometry,
            dict,
        )
        else None
    )

    pnu = (
        str(
            properties.get(
                "pnu",
                ""
            )
        )
    )

    expected_bounds_match = (
        calculated_bounds
        is not None
        and all(
            abs(
                calculated_bounds[
                    index
                ]
                - EXPECTED_BOUNDS[
                    index
                ]
            )
            <= 1e-6

            for index
            in range(
                4
            )
        )
    )

    validations = {

        "feature recovered": (
            selected_feature
            is not None
        ),

        "target PNU": (
            pnu
            == TARGET_PNU
        ),

        "geometry dict": (
            isinstance(
                geometry,
                dict,
            )
        ),

        "geometry Polygon": (
            geometry_type
            == "Polygon"
        ),

        "coordinates exist": (
            isinstance(
                geometry,
                dict,
            )
            and bool(
                geometry.get(
                    "coordinates"
                )
            )
        ),

        "calculated bounds": (
            calculated_bounds
            is not None
        ),

        "expected bounds match": (
            expected_bounds_match
        ),

        "area evidence found": (
            len(
                area_hits
            )
            > 0
        ),

        "bounds evidence found": (
            len(
                bounds_hits
            )
            > 0
        ),
    }

    all_pass = all(
        validations.values()
    )

    # ========================================================
    # spatial metadata snapshot
    # ========================================================

    metadata = {

        "step": (
            "STEP 17-21-C-11-2C-2D "
            "MapPlan parcel spatial recovery"
        ),

        "site": {
            "pnu": (
                TARGET_PNU
            ),
        },

        "source": {
            "snapshot": (
                str(
                    SOURCE_PATH
                )
            ),

            "dataset": (
                "MapPlan"
            ),

            "recovery": (
                selected_source
            ),
        },

        "parcel": {
            "geometry_type": (
                geometry_type
            ),

            "area": (
                area_hits[
                    0
                ][
                    "value"
                ]
                if area_hits
                else None
            ),

            "bounds": (
                calculated_bounds
            ),

            "stored_bounds_evidence": (
                bounds_hits
            ),

            "crs": (
                stored_crs
            ),

            "crs_status": (
                crs_status
            ),

            "geometry_snapshot": (
                str(
                    GEOJSON_OUTPUT_PATH
                )
                if geometry
                else None
            ),
        },

        "validations": (
            validations
        ),

        "all_pass": (
            all_pass
        ),
    }

    save_json(
        OUTPUT_PATH,
        metadata,
    )

    # ========================================================
    # GeoJSON snapshot
    # ========================================================

    if geometry:

        geojson = {
            "type": (
                "FeatureCollection"
            ),

            "features": [
                {
                    "type": (
                        "Feature"
                    ),

                    "properties": {
                        "pnu": (
                            TARGET_PNU
                        ),

                        "source": (
                            "MapPlan C-9 snapshot recovery"
                        ),
                    },

                    "geometry": (
                        geometry
                    ),
                }
            ],
        }

        save_json(
            GEOJSON_OUTPUT_PATH,
            geojson,
        )

    # ========================================================
    # console
    # ========================================================

    print(
        "Source:",
        SOURCE_PATH,
    )

    print()

    print(
        "Recovery mode:",
        (
            selected_source.get(
                "mode"
            )
            if selected_source
            else None
        ),
    )

    print(
        "PNU:",
        pnu,
    )

    print(
        "Geometry:",
        geometry_type,
    )

    print()

    print(
        "Area evidence:",
        (
            area_hits[
                0
            ][
                "value"
            ]
            if area_hits
            else None
        ),
    )

    print(
        "Calculated bounds:",
        calculated_bounds,
    )

    print()

    print(
        "Stored CRS:",
        stored_crs,
    )

    print(
        "CRS status:",
        crs_status,
    )

    print()

    print(
        "GeoJSON:",
        (
            GEOJSON_OUTPUT_PATH
            if geometry
            else None
        ),
    )

    print()

    print(
        "all_pass:",
        all_pass,
    )

    if not all_pass:

        print()
        print(
            "FAILED:"
        )

        for name, passed in (
            validations.items()
        ):

            if not passed:

                print(
                    "-",
                    name,
                )

    print()

    print(
        "OUTPUT:",
        OUTPUT_PATH,
    )

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )