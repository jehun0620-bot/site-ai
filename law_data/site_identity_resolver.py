# -*- coding: utf-8 -*-

"""
STEP 17-21-C-11-2B
SITE Identity Resolver

목표
======================================================================
여러 단계에 흩어진 SITE identity 정보를 하나의 표준 객체로 통합한다.

우선순위
======================================================================
1. SITE Builder / caller가 직접 전달한 값
2. site_spatial_query_context.json
3. vworld_parcel_polygon_identifier_probe.json
4. 기존 rule-engine SITE snapshot

geometry / parcel_area는 별도 spatial payload 단계에서 처리한다.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional


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

QUERY_CONTEXT_PATH = (
    OUTPUT_DIR
    / "site_spatial_query_context.json"
)

PARCEL_PROBE_PATH = (
    OUTPUT_DIR
    / "vworld_parcel_polygon_identifier_probe.json"
)


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


def usable(
    value: Any,
) -> bool:

    if value is None:
        return False

    if isinstance(
        value,
        str,
    ):
        return bool(
            value.strip()
        )

    return True


def first_value(
    *values: Any,
) -> Any:

    for value in values:

        if usable(
            value
        ):
            return value

    return None


def normalize_site_input(
    site: Optional[
        Dict[str, Any]
    ],
) -> Dict[str, Any]:

    if not site:
        return {}

    return copy.deepcopy(
        site
    )


def resolve_site_identity(
    base_site: Optional[
        Dict[str, Any]
    ] = None,
    site_input: Optional[
        Dict[str, Any]
    ] = None,
) -> Dict[str, Any]:

    base_site = normalize_site_input(
        base_site
    )

    site_input = normalize_site_input(
        site_input
    )

    query_data = load_json(
        QUERY_CONTEXT_PATH
    )

    parcel_data = load_json(
        PARCEL_PROBE_PATH
    )

    query = (
        query_data.get(
            "query_context",
            {},
        )
    )

    parcel_site = (
        parcel_data.get(
            "site",
            {},
        )
    )

    point = (
        parcel_site.get(
            "point",
            {},
        )
    )

    # ========================================================
    # canonical identity
    # ========================================================

    site_id = first_value(
        site_input.get(
            "site_id"
        ),
        base_site.get(
            "site_id"
        ),
        query.get(
            "site_id"
        ),
        parcel_site.get(
            "site_id"
        ),
    )

    address = first_value(
        site_input.get(
            "address"
        ),
        base_site.get(
            "address"
        ),
        query.get(
            "address"
        ),
        parcel_site.get(
            "address"
        ),
    )

    road_address = first_value(
        site_input.get(
            "road_address"
        ),
        site_input.get(
            "road_name_address"
        ),
        base_site.get(
            "road_address"
        ),
        query.get(
            "road_address"
        ),
    )

    zone = first_value(
        site_input.get(
            "zone"
        ),
        site_input.get(
            "land_use_zone"
        ),
        base_site.get(
            "zone"
        ),
        base_site.get(
            "land_use_zone"
        ),
        query.get(
            "zone"
        ),
        parcel_site.get(
            "zone"
        ),
    )

    sigungu_code = first_value(
        site_input.get(
            "sigungu_code"
        ),
        site_input.get(
            "sigungu_cd"
        ),
        base_site.get(
            "sigungu_code"
        ),
        base_site.get(
            "sigungu_cd"
        ),
        query.get(
            "sigungu_code"
        ),
    )

    bjdong_code = first_value(
        site_input.get(
            "bjdong_code"
        ),
        site_input.get(
            "bjdong_cd"
        ),
        base_site.get(
            "bjdong_code"
        ),
        base_site.get(
            "bjdong_cd"
        ),
        query.get(
            "bjdong_code"
        ),
    )

    main_no = first_value(
        site_input.get(
            "main_no"
        ),
        site_input.get(
            "bun"
        ),
        base_site.get(
            "main_no"
        ),
        base_site.get(
            "bun"
        ),
        query.get(
            "main_no"
        ),
    )

    sub_no = first_value(
        site_input.get(
            "sub_no"
        ),
        site_input.get(
            "ji"
        ),
        base_site.get(
            "sub_no"
        ),
        base_site.get(
            "ji"
        ),
        query.get(
            "sub_no"
        ),
    )

    pnu = first_value(
        site_input.get(
            "pnu"
        ),
        base_site.get(
            "pnu"
        ),
        query.get(
            "pnu"
        ),
        parcel_site.get(
            "pnu"
        ),
    )

    # ========================================================
    # base coordinate PNU guard
    #
    # base SITE의 representative coordinate는
    # 현재 resolved PNU와 base SITE PNU가 같은 경우에만
    # 재사용할 수 있다.
    #
    # 다른 SITE/PNU에 base coordinate가 상속되는 것을 방지한다.
    # ========================================================

    resolved_pnu_text = (
        str(
            pnu
        ).strip()
        if pnu is not None
        else ""
    )

    # ========================================================
    # coordinate PNU guards
    #
    # 1. base SITE coordinate
    #    -> base SITE PNU와 현재 PNU가 같을 때만 재사용
    #
    # 2. parcel probe point
    #    -> parcel probe SITE PNU와 현재 PNU가 같을 때만 재사용
    #
    # 서로 다른 source의 PNU guard를 분리한다.
    # ========================================================

    resolved_pnu_text = (
        str(
            pnu
        ).strip()
        if pnu is not None
        else ""
    )

    base_pnu = (
        str(
            base_site.get(
                "pnu"
            )
        ).strip()
        if base_site.get(
            "pnu"
        )
        is not None
        else ""
    )

    parcel_probe_pnu = (
        str(
            parcel_site.get(
                "pnu"
            )
        ).strip()
        if parcel_site.get(
            "pnu"
        )
        is not None
        else ""
    )

    same_pnu_as_base = bool(
        resolved_pnu_text
        and base_pnu
        and (
            resolved_pnu_text
            == base_pnu
        )
    )

    same_pnu_as_parcel_probe = bool(
        resolved_pnu_text
        and parcel_probe_pnu
        and (
            resolved_pnu_text
            == parcel_probe_pnu
        )
    )

    # ========================================================
    # base coordinate
    # ========================================================

    base_coordinate = (
        base_site.get(
            "coordinate",
            {},
        )
        if isinstance(
            base_site.get(
                "coordinate"
            ),
            dict,
        )
        else {}
    )

    base_x = (
        first_value(
            base_site.get(
                "x"
            ),
            base_coordinate.get(
                "x"
            ),
        )
        if same_pnu_as_base
        else None
    )

    base_y = (
        first_value(
            base_site.get(
                "y"
            ),
            base_coordinate.get(
                "y"
            ),
        )
        if same_pnu_as_base
        else None
    )

    # ========================================================
    # historical parcel probe coordinate
    #
    # parcel probe에 기록된 PNU와 현재 PNU가 직접 일치하는
    # 경우에만 point를 사용할 수 있다.
    # ========================================================

    fallback_point_x = (
        point.get(
            "x"
        )
        if same_pnu_as_parcel_probe
        else None
    )

    fallback_point_y = (
        point.get(
            "y"
        )
        if same_pnu_as_parcel_probe
        else None
    )

    # ========================================================
    # resolved coordinate
    # ========================================================

    x = first_value(
        site_input.get(
            "x"
        ),
        site_input.get(
            "longitude"
        ),
        base_x,
        fallback_point_x,
    )

    y = first_value(
        site_input.get(
            "y"
        ),
        site_input.get(
            "latitude"
        ),
        base_y,
        fallback_point_y,
    )

    base_coordinate_crs = (
        base_coordinate.get(
            "crs"
        )
        if same_pnu_as_base
        else None
    )

    parcel_probe_crs = (
        point.get(
            "crs"
        )
        if same_pnu_as_parcel_probe
        else None
    )

    coordinate_crs = first_value(
        site_input.get(
            "coordinate_crs"
        ),
        base_coordinate_crs,
        parcel_probe_crs,
    )

    # ========================================================
    # source tracking
    # ========================================================

    identity = {
        "site_id": site_id,
        "address": address,
        "road_address": road_address,

        "pnu": pnu,

        "sigungu_code": sigungu_code,
        "bjdong_code": bjdong_code,

        "main_no": main_no,
        "sub_no": sub_no,

        "zone": zone,
        "land_use_zone": zone,

        "coordinate": {
            "x": x,
            "y": y,
            "crs": coordinate_crs,
        },

        # compatibility aliases
        "x": x,
        "y": y,
    }

    # ========================================================
    # completeness
    # ========================================================

    required_identity = [
        "site_id",
        "address",
        "pnu",
        "sigungu_code",
        "bjdong_code",
        "main_no",
        "sub_no",
        "zone",
    ]

    missing_identity = [
        key
        for key
        in required_identity
        if not usable(
            identity.get(
                key
            )
        )
    ]

    coordinate_complete = (
        usable(
            x
        )
        and usable(
            y
        )
    )

    identity[
        "identity_status"
    ] = (
        "COMPLETE"
        if not missing_identity
        else "PARTIAL"
    )

    identity[
        "coordinate_status"
    ] = (
        "CONFIRMED"
        if coordinate_complete
        else "MISSING"
    )

    identity[
        "missing_identity_fields"
    ] = (
        missing_identity
    )

    # ========================================================
    # parcel source metadata
    # ========================================================

    selected_parcel = (
        parcel_data.get(
            "selected",
            {},
        )
    )

    identity[
        "parcel_reference"
    ] = {
        "dataset": (
            selected_parcel.get(
                "dataset"
            )
        ),

        "status": (
            selected_parcel.get(
                "status"
            )
        ),

        "strict_pnu_verified": (
            selected_parcel.get(
                "strict_pnu_verified"
            )
        ),

        "geometry_loaded": (
            False
        ),

        "note": (
            "Parcel dataset은 검증되었으나 geometry 자체는 "
            "이번 identity object에 아직 포함하지 않음"
        ),
    }

    return identity