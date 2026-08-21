# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2C-3
SITE Spatial Payload Resolver

목표
======================================================================
C-11에서 복구한 Parcel spatial snapshot을 읽어
최종 SITE 객체에 사용할 표준 spatial payload를 생성한다.

중요
======================================================================
Parcel CRS는 source에서 명시적으로 확인되지 않았으므로
절대 추측하지 않는다.

crs = None
crs_status = SOURCE_CRS_NOT_EXPLICIT

상태를 그대로 보존한다.
"""

from __future__ import annotations

import copy
import json

from pathlib import Path
from typing import Any, Dict


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

PARCEL_METADATA_PATH = (
    OUTPUT_DIR
    / "site_parcel_spatial_recovery.json"
)

PARCEL_GEOJSON_PATH = (
    OUTPUT_DIR
    / "site_parcel_spatial_snapshot.geojson"
)


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


# ============================================================
# public API
# ============================================================

def resolve_site_spatial_payload() -> Dict[str, Any]:

    metadata = load_json(
        PARCEL_METADATA_PATH
    )

    geojson = load_json(
        PARCEL_GEOJSON_PATH
    )

    parcel_meta = (
        metadata.get(
            "parcel",
            {},
        )
    )

    source_meta = (
        metadata.get(
            "source",
            {},
        )
    )

    features = (
        geojson.get(
            "features",
            [],
        )
        if isinstance(
            geojson,
            dict,
        )
        else []
    )

    feature = (
        features[
            0
        ]
        if features
        else {}
    )

    geometry = copy.deepcopy(
        feature.get(
            "geometry"
        )
    )

    properties = copy.deepcopy(
        feature.get(
            "properties",
            {},
        )
    )

    pnu = (
        properties.get(
            "pnu"
        )
        or metadata.get(
            "site",
            {},
        ).get(
            "pnu"
        )
    )

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

    geometry_loaded = (
        isinstance(
            geometry,
            dict,
        )
        and bool(
            geometry.get(
                "coordinates"
            )
        )
    )

    area = (
        parcel_meta.get(
            "area"
        )
    )

    bounds = copy.deepcopy(
        parcel_meta.get(
            "bounds"
        )
    )

    crs = (
        parcel_meta.get(
            "crs"
        )
    )

    crs_status = (
        parcel_meta.get(
            "crs_status"
        )
    )

    verified = (
        metadata.get(
            "all_pass"
        )
        is True
        and geometry_loaded
        and pnu is not None
    )

    return {

        "parcel": {
            "pnu": (
                pnu
            ),

            "geometry": (
                geometry
            ),

            "geometry_type": (
                geometry_type
            ),

            "geometry_loaded": (
                geometry_loaded
            ),

            "area": {
                "value": (
                    area
                ),

                "unit": (
                    "native_crs_square_units"
                ),

                "status": (
                    "RECOVERED"
                    if area
                    is not None
                    else "MISSING"
                ),
            },

            "bounds": (
                bounds
            ),

            "crs": (
                crs
            ),

            "crs_status": (
                crs_status
            ),

            "source": {
                "provider": (
                    "MapPlan"
                ),

                "snapshot": (
                    source_meta.get(
                        "snapshot"
                    )
                ),

                "recovery": (
                    copy.deepcopy(
                        source_meta.get(
                            "recovery"
                        )
                    )
                ),

                "geojson_snapshot": (
                    str(
                        PARCEL_GEOJSON_PATH
                    )
                ),

                "verified": (
                    verified
                ),
            },
        },
    }