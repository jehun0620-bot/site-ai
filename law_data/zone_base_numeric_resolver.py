# -*- coding: utf-8 -*-

"""
STEP 17-21-C-13-4F
Dynamic Zone Base Numeric Resolver

목표
======================================================================
현재 SITE의 용도지역(zone)을 기준으로
서울특별시 도시계획 조례의 기본 건폐율 / 용적률을 반환한다.

source
======================================================================
law_data/output/zone_ratio_map_layer_resolution.json

원칙
======================================================================
- 서울시 조례값을 실제 baseline으로 사용
- 국가 시행령값은 ceiling/reference로 보존
- zone 미지원 시 임의 fallback 금지
"""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any, Dict


BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

SOURCE_PATH = (
    BASE_DIR
    / "law_data"
    / "output"
    / "zone_ratio_map_layer_resolution.json"
)


class ZoneBaseNumericError(
    RuntimeError
):
    pass


def load_source() -> Dict[str, Any]:

    if not SOURCE_PATH.exists():

        raise ZoneBaseNumericError(
            f"Zone numeric source 없음: {SOURCE_PATH}"
        )

    with SOURCE_PATH.open(
        "r",
        encoding="utf-8",
    ) as f:

        return json.load(f)


def resolve_zone_base_numeric(
    zone: str,
) -> Dict[str, Any]:

    zone = str(
        zone
        or ""
    ).strip()

    if not zone:

        raise ZoneBaseNumericError(
            "SITE 용도지역이 없습니다."
        )

    data = load_source()

    resolved_map = (
        data.get(
            "resolved_map",
            {},
        )
    )

    zone_values = (
        resolved_map.get(
            zone
        )
    )

    if not isinstance(
        zone_values,
        dict,
    ):

        raise ZoneBaseNumericError(
            f"지원되지 않는 용도지역: {zone}"
        )

    result_by_zone = (
        data.get(
            "result_by_zone",
            {},
        )
    )

    detail = (
        result_by_zone.get(
            zone,
            {},
        )
    )

    bcr_detail = (
        detail.get(
            "건폐율",
            {},
        )
    )

    far_detail = (
        detail.get(
            "용적률",
            {},
        )
    )

    bcr = (
        zone_values.get(
            "building_coverage_ratio"
        )
    )

    far = (
        zone_values.get(
            "floor_area_ratio"
        )
    )

    if (
        bcr is None
        or far is None
    ):

        raise ZoneBaseNumericError(
            f"용도지역 numeric 값 불완전: {zone}"
        )

    national_bcr_values = (
        bcr_detail.get(
            "national_values",
            [],
        )
    )

    national_far_values = (
        far_detail.get(
            "national_values",
            [],
        )
    )

    return {

        "zone": (
            zone
        ),

        "building_coverage_ratio": {
            "value": (
                float(
                    bcr
                )
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
            ),

            "source": (
                "SEOUL_METROPOLITAN_ORDINANCE"
            ),

            "source_law": (
                "서울특별시 도시계획 조례"
            ),

            "national_ceiling": (
                max(
                    national_bcr_values
                )
                if national_bcr_values
                else None
            ),
        },

        "floor_area_ratio": {
            "value": (
                float(
                    far
                )
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
            ),

            "source": (
                "SEOUL_METROPOLITAN_ORDINANCE"
            ),

            "source_law": (
                "서울특별시 도시계획 조례"
            ),

            "national_ceiling": (
                max(
                    national_far_values
                )
                if national_far_values
                else None
            ),
        },

        "resolution": (
            "ZONE_BASE_NUMERIC_RESOLVED"
        ),
    }