# -*- coding: utf-8 -*-

"""
STEP 17-21-C-14-2
PNU-aware SITE Spatial Payload Resolver
with Live Parcel Geometry Fallback

목표
======================================================================
현재 분석 SITE의 PNU를 기준으로 Parcel geometry를 안전하게 결정한다.

우선순위:

1. 현재 SITE PNU == 저장된 Parcel snapshot PNU
   -> 기존 검증된 MapPlan snapshot 사용

2. 현재 SITE PNU != snapshot PNU
   -> snapshot 재사용 금지
   -> VWorld live parcel provider 호출
   -> 대상 PNU와 직접 일치하는 Polygon/MultiPolygon만 사용

3. live provider도 실패
   -> geometry_loaded = False

핵심 안전 원칙
======================================================================
다른 SITE에 대표 SITE geometry를 재사용하지 않는다.

잘못된 geometry를 사용하는 것보다
geometry가 없는 상태를 명시적으로 반환하는 것이 우선이다.

Live geometry는 EPSG:4326이므로,
현재 단계에서는 좌표값 자체로 면적을 계산하지 않는다.
"""

from __future__ import annotations

import copy
import json

from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
)


# ============================================================
# local module
# ============================================================

try:
    from .parcel_geometry_provider import (
        resolve_live_parcel_geometry,
    )

except ImportError:
    from parcel_geometry_provider import (
        resolve_live_parcel_geometry,
    )


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

        data = json.load(
            f
        )

    if not isinstance(
        data,
        dict,
    ):

        return {}

    return data


def safe_string(
    value: Any,
) -> str:

    if value is None:

        return ""

    return str(
        value
    ).strip()


def calculate_geometry_bounds(
    geometry: Dict[str, Any],
) -> Optional[List[float]]:

    """
    GeoJSON Polygon / MultiPolygon coordinates에서
    [min_x, min_y, max_x, max_y]를 계산한다.

    CRS 변환은 하지 않는다.
    geometry가 EPSG:4326이면 bounds 역시 EPSG:4326이다.
    """

    if not isinstance(
        geometry,
        dict,
    ):

        return None

    coordinates = (
        geometry.get(
            "coordinates"
        )
    )

    if not coordinates:

        return None

    points: List[
        tuple[
            float,
            float,
        ]
    ] = []

    def collect_points(
        value: Any,
    ) -> None:

        if not isinstance(
            value,
            list,
        ):

            return

        # ----------------------------------------------------
        # coordinate pair
        # ----------------------------------------------------

        if (
            len(
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
                (
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
                )
            )

            return

        # ----------------------------------------------------
        # recursive nested coordinates
        # ----------------------------------------------------

        for child in value:

            collect_points(
                child
            )

    collect_points(
        coordinates
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
# public API
# ============================================================

def resolve_site_spatial_payload(
    site: Dict[str, Any],
) -> Dict[str, Any]:

    """
    현재 SITE PNU 기준 Parcel geometry resolver.

    Resolution order:

    1. verified local MapPlan snapshot
    2. VWorld live PNU-verified parcel geometry
    3. unavailable
    """

    # ========================================================
    # requested SITE
    # ========================================================

    requested_pnu = safe_string(
        site.get(
            "pnu"
        )
    )

    requested_address = safe_string(
        site.get(
            "address"
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

    if not isinstance(
        parcel_meta,
        dict,
    ):

        parcel_meta = {}

    source_meta = (
        metadata.get(
            "source",
            {},
        )
    )

    if not isinstance(
        source_meta,
        dict,
    ):

        source_meta = {}

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

    if not isinstance(
        features,
        list,
    ):

        features = []

    feature = (
        features[
            0
        ]
        if (
            features
            and isinstance(
                features[
                    0
                ],
                dict,
            )
        )
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

    if not isinstance(
        properties,
        dict,
    ):

        properties = {}

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

    # live metadata default
    live_result: Dict[
        str,
        Any
    ] = {}

    live_resolution = None
    live_query = None
    live_coordinate = None
    live_dataset = None
    live_feature_pnu = None
    live_feature_id = None
    live_pnu_property_key = None

    # ========================================================
    # 1. matching snapshot SITE
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

        source_provider = (
            "MapPlan"
        )

        source_dataset = (
            parcel_meta.get(
                "dataset"
            )
            or "LP_PA_CBND_BUBUN"
        )

        verified = (
            metadata.get(
                "all_pass"
            )
            is True
            and geometry_loaded
        )

        resolution = (
            "SNAPSHOT_PNU_MATCH"
        )

    # ========================================================
    # 2. different SITE -> live VWorld fallback
    # ========================================================

    else:

        live_result = (
            resolve_live_parcel_geometry(
                pnu=(
                    requested_pnu
                ),

                address=(
                    requested_address
                ),
            )
        )

        live_loaded = (
            live_result.get(
                "geometry_loaded"
            )
            is True
        )

        live_resolution = (
            live_result.get(
                "resolution"
            )
        )

        live_query = copy.deepcopy(
            live_result.get(
                "query"
            )
        )

        live_coordinate = copy.deepcopy(
            live_result.get(
                "coordinate"
            )
        )

        live_dataset = (
            live_result.get(
                "dataset"
            )
        )

        live_feature_pnu = (
            live_result.get(
                "feature_pnu"
            )
        )

        live_feature_id = (
            live_result.get(
                "feature_id"
            )
        )

        live_pnu_property_key = (
            live_result.get(
                "pnu_property_key"
            )
        )

        # ====================================================
        # live success
        # ====================================================

        if live_loaded:

            geometry = copy.deepcopy(
                live_result.get(
                    "geometry"
                )
            )

            geometry_type = (
                live_result.get(
                    "geometry_type"
                )
            )

            geometry_loaded = True

            # ------------------------------------------------
            # EPSG:4326 geometry에서 degree²를 parcel area로
            # 해석하면 안 되므로 현재는 계산하지 않는다.
            # ------------------------------------------------

            area = None

            bounds = (
                calculate_geometry_bounds(
                    geometry
                )
            )

            crs = (
                live_result.get(
                    "source",
                    {},
                ).get(
                    "crs"
                )
                or "EPSG:4326"
            )

            crs_status = (
                "CONFIRMED"
            )

            area_status = (
                "NOT_CALCULATED_FOR_LIVE_GEOMETRY"
            )

            source_status = (
                "VERIFIED"
            )

            source_provider = (
                "VWorld"
            )

            source_dataset = (
                live_dataset
                or "LP_PA_CBND_BUBUN"
            )

            verified = (
                live_result.get(
                    "strict_pnu_verified"
                )
                is True
            )

            resolution = (
                live_resolution
                or "LIVE_PNU_POLYGON_VERIFIED"
            )

        # ====================================================
        # live failure
        # ====================================================

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
                live_resolution
                or "SOURCE_NOT_AVAILABLE_FOR_SITE"
            )

            source_provider = (
                "VWorld"
            )

            source_dataset = (
                live_dataset
                or "LP_PA_CBND_BUBUN"
            )

            verified = False

            resolution = (
                live_resolution
                or "LIVE_SOURCE_UNAVAILABLE"
            )

    # ========================================================
    # result
    # ========================================================

    return {

        "parcel": {

            # ------------------------------------------------
            # 반드시 현재 SITE PNU 반환
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

                # --------------------------------------------
                # active source
                # --------------------------------------------

                "provider": (
                    source_provider
                ),

                "dataset": (
                    source_dataset
                ),

                "status": (
                    source_status
                ),

                "resolution": (
                    resolution
                ),

                "verified": (
                    verified
                ),

                # --------------------------------------------
                # current SITE
                # --------------------------------------------

                "requested_pnu": (
                    requested_pnu
                ),

                "requested_address": (
                    requested_address
                ),

                # --------------------------------------------
                # snapshot context
                # --------------------------------------------

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

                # --------------------------------------------
                # live source context
                #
                # snapshot 경로에서는 None.
                # live VWorld 경로에서만 값 존재.
                # --------------------------------------------

                "live": {

                    "resolution": (
                        live_resolution
                    ),

                    "dataset": (
                        live_dataset
                    ),

                    "feature_id": (
                        live_feature_id
                    ),

                    "feature_pnu": (
                        live_feature_pnu
                    ),

                    "pnu_property_key": (
                        live_pnu_property_key
                    ),

                    "coordinate": (
                        live_coordinate
                    ),

                    "query": (
                        live_query
                    ),
                },
            },
        },
    }