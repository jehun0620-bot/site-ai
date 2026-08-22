# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-3
PNU-aware SITE Spatial Payload Resolver

목표
======================================================================
현재 분석 SITE의 PNU와 저장된 Parcel snapshot의 PNU가 일치할 때만
해당 Polygon geometry를 사용한다.

중요
======================================================================
기존 C-12 구조에서는 개포동 12번지 snapshot을 모든 SITE에
재사용할 위험이 있었다.

C-13부터는:

requested SITE PNU == snapshot PNU
    -> geometry 사용

requested SITE PNU != snapshot PNU
    -> geometry 사용 금지
    -> geometry_loaded = False
    -> SOURCE_NOT_AVAILABLE_FOR_SITE

잘못된 geometry를 사용하는 것보다 geometry가 없는 상태를
명시적으로 반환하는 것이 원칙이다.
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


def safe_string(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


# ============================================================
# public API
# ============================================================

def resolve_site_spatial_payload(
    site: Dict[str, Any],
) -> Dict[str, Any]:

    """
    현재 SITE의 PNU를 기준으로 Parcel snapshot을 선택적으로 사용한다.

    현재 단계에서는 단일 snapshot만 존재하므로,
    PNU가 일치하지 않으면 snapshot을 절대 재사용하지 않는다.
    """

    # ========================================================
    # requested SITE
    # ========================================================

    requested_pnu = safe_string(
        site.get(
            "pnu"
        )
    )

    # ========================================================
    # snapshot
    # ========================================================

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

    snapshot_geometry = copy.deepcopy(
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

    snapshot_pnu = safe_string(
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

    # ========================================================
    # PNU guard
    # ========================================================

    pnu_match = bool(
        requested_pnu
        and snapshot_pnu
        and (
            requested_pnu
            == snapshot_pnu
        )
    )

    # ========================================================
    # matching SITE
    # ========================================================

    if pnu_match:

        geometry = (
            snapshot_geometry
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

        area_status = (
            "RECOVERED"
            if area is not None
            else "MISSING"
        )

        source_status = (
            "VERIFIED"
            if (
                metadata.get(
                    "all_pass"
                )
                is True
                and geometry_loaded
            )
            else "AVAILABLE_UNVERIFIED"
        )

        verified = (
            metadata.get(
                "all_pass"
            )
            is True
            and geometry_loaded
        )

    # ========================================================
    # different SITE
    # ========================================================

    else:

        geometry = None
        geometry_type = None
        geometry_loaded = False

        area = None
        bounds = None

        crs = None

        crs_status = (
            "SOURCE_NOT_AVAILABLE_FOR_SITE"
        )

        area_status = (
            "SOURCE_NOT_AVAILABLE_FOR_SITE"
        )

        source_status = (
            "SOURCE_NOT_AVAILABLE_FOR_SITE"
        )

        verified = False

    # ========================================================
    # result
    # ========================================================

    return {

        "parcel": {

            # ------------------------------------------------
            # 반드시 현재 SITE PNU를 반환한다.
            #
            # snapshot PNU를 parcel.pnu로 노출하면
            # 다시 SITE identity contamination이 발생한다.
            # ------------------------------------------------

            "pnu": (
                requested_pnu
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
                    area_status
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

                "status": (
                    source_status
                ),

                "requested_pnu": (
                    requested_pnu
                ),

                "snapshot_pnu": (
                    snapshot_pnu
                ),

                "pnu_match": (
                    pnu_match
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