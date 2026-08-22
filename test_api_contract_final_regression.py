# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-7
API Contract Final Regression / Schema Freeze

목표
======================================================================
SITE_ANALYSIS_API_V1의 공개 API 계약을 최종 고정한다.

검증
======================================================================
1. 정상 response schema
2. 핵심 SITE 필드
3. land_area 구조
4. spatial parcel 구조
5. regulation 구조
6. rule summary 구조
7. requirements 구조
8. external dependency 구조
9. service metadata
10. debug 기본 제외
11. HTTP error contract
12. JSON round-trip

이번 테스트 통과 후:
SITE_ANALYSIS_API_V1 = FROZEN
"""

from __future__ import annotations

import json

from unittest.mock import patch

from fastapi.testclient import TestClient

from api_app import app

from site_data.site_analysis_orchestrator import (
    BuildingAPIError,
    SiteAnalysisError,
    SiteBuildError,
)


# ============================================================
# client
# ============================================================

client = TestClient(
    app
)


# ============================================================
# request
# ============================================================

VALID_PAYLOAD = {

    "sigungu_cd": "11680",

    "bjdong_cd": "10300",

    "bun": "0012",

    "ji": "0000",

    "project_profile": {
        "공동주택": "TRUE",
    },

    "procedure_profile": {
        "도시계획위원회심의": "TRUE",
    },

    "include_debug": False,
}


# ============================================================
# frozen success response
# ============================================================

SUCCESS_RESPONSE = {

    "schema_version": (
        "SITE_ANALYSIS_API_V1"
    ),

    "status": (
        "READY"
    ),

    "site": {
        "site_id": (
            "11680-10300-0012-0000"
        ),

        "address": (
            "서울특별시 강남구 개포동 12번지"
        ),

        "road_address": (
            "서울특별시 강남구 개포로109길 21 (개포동)"
        ),

        "pnu": (
            "1168010300100120000"
        ),

        "sigungu_code": (
            "11680"
        ),

        "bjdong_code": (
            "10300"
        ),

        "main_no": (
            "0012"
        ),

        "sub_no": (
            "0000"
        ),

        "zone": (
            "제3종일반주거지역"
        ),

        "coordinate": {
            "x": (
                127.07539280356858
            ),

            "y": (
                37.494197498186885
            ),

            "crs": (
                "EPSG:4326"
            ),
        },

        "identity_status": (
            "COMPLETE"
        ),
    },

    "land_area": {

        "official": {
            "value": (
                121040.4
            ),

            "unit": (
                "square_meter"
            ),

            "source": (
                "VWORLD_LAND_CHARACTERISTICS"
            ),

            "role": (
                "LEGAL_OR_ATTRIBUTE_LAND_AREA"
            ),
        },

        "spatial": {
            "value": (
                120945.65223377591
            ),

            "unit": (
                "native_crs_square_units"
            ),

            "source": (
                "MAPPLAN_PARCEL_GEOMETRY"
            ),

            "role": (
                "SPATIAL_GEOMETRY_AREA"
            ),

            "crs": None,

            "crs_status": (
                "SOURCE_CRS_NOT_EXPLICIT"
            ),
        },

        "difference": {
            "value": (
                94.74776622408535
            ),

            "ratio_percent": (
                0.07827780329880384
            ),
        },

        "resolution": (
            "KEEP_BOTH_WITH_SOURCE_ROLES"
        ),

        "primary": (
            "official"
        ),
    },

    "spatial": {

        "parcel": {

            "pnu": (
                "1168010300100120000"
            ),

            "geometry": {
                "type": (
                    "Polygon"
                ),

                "coordinates": [
                    [
                        [
                            962201.02522,
                            1943841.80188,
                        ],

                        [
                            962210.40147,
                            1943851.19867,
                        ],

                        [
                            962201.02522,
                            1943841.80188,
                        ],
                    ]
                ],
            },

            "geometry_type": (
                "Polygon"
            ),

            "geometry_loaded": True,

            "area": {
                "value": (
                    120945.65223377591
                ),

                "unit": (
                    "native_crs_square_units"
                ),

                "status": (
                    "RECOVERED"
                ),
            },

            "bounds": [
                962201.02522,
                1943722.58159,
                962711.06096,
                1944220.16506,
            ],

            "crs": None,

            "crs_status": (
                "SOURCE_CRS_NOT_EXPLICIT"
            ),

            "source": {
                "provider": (
                    "MapPlan"
                ),

                "verified": True,
            },
        },
    },

    "regulation": {

        "building_coverage_ratio": {
            "value": (
                50.0
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
            ),
        },

        "floor_area_ratio": {
            "value": (
                250.0
            ),

            "unit": (
                "percent"
            ),

            "status": (
                "CONFIRMED"
            ),
        },

        "numeric_resolution": (
            "BASE_VALUES_RETAINED"
        ),

        "direct_relaxation_count": (
            0
        ),
    },

    "rule_evaluation": {
        "total": (
            314
        ),

        "applicable": (
            63
        ),

        "not_applicable": (
            213
        ),

        "conditional": (
            36
        ),

        "unknown": (
            2
        ),
    },

    "requirements": {

        "project": [],

        "procedure": [],

        "project_count": (
            14
        ),

        "procedure_count": (
            1
        ),

        "requires_additional_input": True,
    },

    "external_dependencies": {

        "count": (
            1
        ),

        "items": [
            {
                "category": (
                    "SITE_HISTORY"
                ),

                "condition": (
                    "도시지역편입해제구역"
                ),

                "status": (
                    "UNKNOWN"
                ),

                "automation_state": (
                    "HISTORICAL_SOURCE_PENDING"
                ),

                "blocking_analysis": False,
            }
        ],
    },

    "service": {

        "building_count": (
            34
        ),

        "building_total_count": (
            34
        ),

        "building_api_status": (
            "00"
        ),
    },
}


# ============================================================
# util
# ============================================================

def require_keys(
    container,
    expected,
) -> bool:

    if not isinstance(
        container,
        dict,
    ):

        return False

    return all(
        key in container
        for key
        in expected
    )


def post_with_side_effect(
    side_effect,
):

    with patch(
        "api_app.analyze_site_by_parcel",
        side_effect=(
            side_effect
        ),
    ):

        return client.post(
            "/v1/site-analysis",
            json=(
                VALID_PAYLOAD
            ),
        )


# ============================================================
# main
# ============================================================

def main() -> int:

    validations = {}

    # ========================================================
    # 1. SUCCESS CONTRACT
    # ========================================================

    with patch(
        "api_app.analyze_site_by_parcel",
        return_value=(
            SUCCESS_RESPONSE
        ),
    ):

        response = client.post(
            "/v1/site-analysis",
            json=(
                VALID_PAYLOAD
            ),
        )

    result = (
        response.json()
    )

    print(
        "=== SUCCESS CONTRACT ==="
    )

    print(
        "HTTP:",
        response.status_code,
    )

    print(
        "Schema:",
        result.get(
            "schema_version"
        ),
    )

    print(
        "Status:",
        result.get(
            "status"
        ),
    )

    # --------------------------------------------------------
    # top-level freeze
    # --------------------------------------------------------

    required_top_keys = {
        "schema_version",
        "status",
        "site",
        "land_area",
        "spatial",
        "regulation",
        "rule_evaluation",
        "requirements",
        "external_dependencies",
        "service",
    }

    top_keys = set(
        result.keys()
    )

    missing_top = sorted(
        required_top_keys
        - top_keys
    )

    validations[
        "success 200"
    ] = (
        response.status_code
        == 200
    )

    validations[
        "schema version"
    ] = (
        result.get(
            "schema_version"
        )
        == "SITE_ANALYSIS_API_V1"
    )

    validations[
        "status ready"
    ] = (
        result.get(
            "status"
        )
        == "READY"
    )

    validations[
        "top schema complete"
    ] = (
        not missing_top
    )

    validations[
        "debug excluded"
    ] = (
        "debug"
        not in result
    )

    # ========================================================
    # 2. SITE CONTRACT
    # ========================================================

    site = (
        result.get(
            "site",
            {},
        )
    )

    validations[
        "site keys"
    ] = require_keys(
        site,
        {
            "site_id",
            "address",
            "road_address",
            "pnu",
            "sigungu_code",
            "bjdong_code",
            "main_no",
            "sub_no",
            "zone",
            "coordinate",
            "identity_status",
        },
    )

    validations[
        "site id"
    ] = (
        site.get(
            "site_id"
        )
        == "11680-10300-0012-0000"
    )

    validations[
        "pnu"
    ] = (
        site.get(
            "pnu"
        )
        == "1168010300100120000"
    )

    validations[
        "zone"
    ] = (
        site.get(
            "zone"
        )
        == "제3종일반주거지역"
    )

    validations[
        "identity complete"
    ] = (
        site.get(
            "identity_status"
        )
        == "COMPLETE"
    )

    coordinate = (
        site.get(
            "coordinate",
            {},
        )
    )

    validations[
        "coordinate schema"
    ] = require_keys(
        coordinate,
        {
            "x",
            "y",
            "crs",
        },
    )

    validations[
        "coordinate crs"
    ] = (
        coordinate.get(
            "crs"
        )
        == "EPSG:4326"
    )

    # ========================================================
    # 3. LAND AREA CONTRACT
    # ========================================================

    land_area = (
        result.get(
            "land_area",
            {},
        )
    )

    validations[
        "land area keys"
    ] = require_keys(
        land_area,
        {
            "official",
            "spatial",
            "difference",
            "resolution",
            "primary",
        },
    )

    validations[
        "official primary"
    ] = (
        land_area.get(
            "primary"
        )
        == "official"
    )

    validations[
        "area resolution"
    ] = (
        land_area.get(
            "resolution"
        )
        == "KEEP_BOTH_WITH_SOURCE_ROLES"
    )

    validations[
        "official area"
    ] = (
        land_area.get(
            "official",
            {},
        ).get(
            "value"
        )
        == 121040.4
    )

    # ========================================================
    # 4. SPATIAL CONTRACT
    # ========================================================

    parcel = (
        result.get(
            "spatial",
            {},
        ).get(
            "parcel",
            {},
        )
    )

    validations[
        "parcel keys"
    ] = require_keys(
        parcel,
        {
            "pnu",
            "geometry",
            "geometry_type",
            "geometry_loaded",
            "area",
            "bounds",
            "crs",
            "crs_status",
            "source",
        },
    )

    validations[
        "parcel polygon"
    ] = (
        parcel.get(
            "geometry_type"
        )
        == "Polygon"
    )

    validations[
        "parcel loaded"
    ] = (
        parcel.get(
            "geometry_loaded"
        )
        is True
    )

    validations[
        "parcel crs unresolved"
    ] = (
        parcel.get(
            "crs"
        )
        is None
        and parcel.get(
            "crs_status"
        )
        == "SOURCE_CRS_NOT_EXPLICIT"
    )

    # ========================================================
    # 5. REGULATION CONTRACT
    # ========================================================

    regulation = (
        result.get(
            "regulation",
            {},
        )
    )

    validations[
        "regulation keys"
    ] = require_keys(
        regulation,
        {
            "building_coverage_ratio",
            "floor_area_ratio",
            "numeric_resolution",
            "direct_relaxation_count",
        },
    )

    validations[
        "BCR 50"
    ] = (
        regulation.get(
            "building_coverage_ratio",
            {},
        ).get(
            "value"
        )
        == 50.0
    )

    validations[
        "FAR 250"
    ] = (
        regulation.get(
            "floor_area_ratio",
            {},
        ).get(
            "value"
        )
        == 250.0
    )

    validations[
        "base retained"
    ] = (
        regulation.get(
            "numeric_resolution"
        )
        == "BASE_VALUES_RETAINED"
    )

    # ========================================================
    # 6. RULE CONTRACT
    # ========================================================

    rules = (
        result.get(
            "rule_evaluation",
            {},
        )
    )

    validations[
        "rule keys"
    ] = require_keys(
        rules,
        {
            "total",
            "applicable",
            "not_applicable",
            "conditional",
            "unknown",
        },
    )

    validations[
        "rules total"
    ] = (
        rules.get(
            "total"
        )
        == 314
    )

    validations[
        "rules sum"
    ] = (
        rules.get(
            "applicable",
            0,
        )
        + rules.get(
            "not_applicable",
            0,
        )
        + rules.get(
            "conditional",
            0,
        )
        + rules.get(
            "unknown",
            0,
        )
        == 314
    )

    # ========================================================
    # 7. REQUIREMENTS CONTRACT
    # ========================================================

    requirements = (
        result.get(
            "requirements",
            {},
        )
    )

    validations[
        "requirements keys"
    ] = require_keys(
        requirements,
        {
            "project",
            "procedure",
            "project_count",
            "procedure_count",
            "requires_additional_input",
        },
    )

    validations[
        "requirements counts"
    ] = (
        requirements.get(
            "project_count"
        )
        == 14
        and requirements.get(
            "procedure_count"
        )
        == 1
    )

    # ========================================================
    # 8. EXTERNAL DEPENDENCY CONTRACT
    # ========================================================

    external = (
        result.get(
            "external_dependencies",
            {},
        )
    )

    validations[
        "external keys"
    ] = require_keys(
        external,
        {
            "count",
            "items",
        },
    )

    validations[
        "external count"
    ] = (
        external.get(
            "count"
        )
        == 1
    )

    validations[
        "historical pending"
    ] = (
        bool(
            external.get(
                "items"
            )
        )
        and external[
            "items"
        ][
            0
        ].get(
            "automation_state"
        )
        == "HISTORICAL_SOURCE_PENDING"
    )

    # ========================================================
    # 9. SERVICE CONTRACT
    # ========================================================

    service = (
        result.get(
            "service",
            {},
        )
    )

    validations[
        "service keys"
    ] = require_keys(
        service,
        {
            "building_count",
            "building_total_count",
            "building_api_status",
        },
    )

    validations[
        "building count"
    ] = (
        service.get(
            "building_count"
        )
        == 34
    )

    validations[
        "building status"
    ] = (
        service.get(
            "building_api_status"
        )
        == "00"
    )

    # ========================================================
    # 10. JSON ROUND TRIP
    # ========================================================

    encoded = json.dumps(
        result,
        ensure_ascii=False,
    )

    decoded = json.loads(
        encoded
    )

    validations[
        "JSON round trip"
    ] = (
        decoded
        == result
    )

    # ========================================================
    # 11. ERROR CONTRACT
    # ========================================================

    invalid_payload = {
        **VALID_PAYLOAD,
        "sigungu_cd": (
            "1168"
        ),
    }

    response_422 = client.post(
        "/v1/site-analysis",
        json=(
            invalid_payload
        ),
    )

    validations[
        "422 contract"
    ] = (
        response_422.status_code
        == 422
    )

    response_404 = post_with_side_effect(
        SiteBuildError(
            "not found"
        )
    )

    validations[
        "404 contract"
    ] = (
        response_404.status_code
        == 404
    )

    response_502 = post_with_side_effect(
        BuildingAPIError(
            "upstream failure"
        )
    )

    validations[
        "502 contract"
    ] = (
        response_502.status_code
        == 502
    )

    response_500 = post_with_side_effect(
        SiteAnalysisError(
            "analysis failure"
        )
    )

    validations[
        "500 analysis contract"
    ] = (
        response_500.status_code
        == 500
    )

    response_unexpected = post_with_side_effect(
        RuntimeError(
            "SECRET_INTERNAL_VALUE"
        )
    )

    unexpected_body = (
        response_unexpected.json()
    )

    validations[
        "500 unexpected contract"
    ] = (
        response_unexpected.status_code
        == 500
    )

    validations[
        "500 no leak"
    ] = (
        "SECRET_INTERNAL_VALUE"
        not in str(
            unexpected_body
        )
    )

    # ========================================================
    # FINAL
    # ========================================================

    all_pass = all(
        validations.values()
    )

    print()

    print(
        "========================================"
    )

    print(
        "SITE_ANALYSIS_API_V1 FINAL CONTRACT"
    )

    print(
        "========================================"
    )

    print(
        "Missing top keys:",
        missing_top,
    )

    print()

    print(
        "HTTP success:",
        200,
    )

    print(
        "HTTP validation:",
        422,
    )

    print(
        "HTTP not found:",
        404,
    )

    print(
        "HTTP upstream:",
        502,
    )

    print(
        "HTTP internal:",
        500,
    )

    print()

    print(
        "Schema freeze:",
        (
            "READY"
            if all_pass
            else "FAILED"
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

    return (
        0
        if all_pass
        else 1
    )


if __name__ == "__main__":

    raise SystemExit(
        main()
    )