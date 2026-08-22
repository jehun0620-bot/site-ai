# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-6
API Contract / Error Handling Regression

목표
======================================================================
FastAPI HTTP 계층의 error contract를 고정한다.

검증
======================================================================
정상 요청                         -> 200
잘못된 request schema             -> 422
필수값 누락                       -> 422
SiteBuildError                    -> 404
BuildingAPIError                  -> 502
SiteAnalysisError                 -> 500
예상하지 못한 Exception           -> 500

중요
======================================================================
외부 Building HUB API는 호출하지 않는다.

api_app.analyze_site_by_parcel()을 mock하여
HTTP error mapping만 독립적으로 검증한다.
"""

from __future__ import annotations

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
# representative request
# ============================================================

VALID_PAYLOAD = {

    "sigungu_cd": (
        "11680"
    ),

    "bjdong_cd": (
        "10300"
    ),

    "bun": (
        "0012"
    ),

    "ji": (
        "0000"
    ),

    "project_profile": {
        "공동주택": (
            "TRUE"
        ),
    },

    "procedure_profile": {
        "도시계획위원회심의": (
            "TRUE"
        ),
    },

    "include_debug": (
        False
    ),
}


# ============================================================
# mocked success response
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
    },

    "regulation": {
        "building_coverage_ratio": {
            "value": (
                50.0
            ),
        },

        "floor_area_ratio": {
            "value": (
                250.0
            ),
        },
    },

    "rule_evaluation": {
        "total": (
            314
        ),
    },

    "service": {
        "building_count": (
            34
        ),
    },
}


# ============================================================
# helper
# ============================================================

def print_case(
    name: str,
    status_code: int,
    body,
) -> None:

    print(
        f"[{name}]"
    )

    print(
        "HTTP:",
        status_code,
    )

    print(
        "Body:",
        body,
    )

    print()


# ============================================================
# main
# ============================================================

def main() -> int:

    validations = {}

    # ========================================================
    # CASE 1
    # Normal request -> 200
    # ========================================================

    with patch(
        "api_app.analyze_site_by_parcel",
        return_value=(
            SUCCESS_RESPONSE
        ),
    ) as mocked:

        response = client.post(
            "/v1/site-analysis",
            json=VALID_PAYLOAD,
        )

    body = response.json()

    print_case(
        "NORMAL_200",
        response.status_code,
        body,
    )

    validations[
        "normal 200"
    ] = (
        response.status_code
        == 200
    )

    validations[
        "normal schema"
    ] = (
        body.get(
            "schema_version"
        )
        == "SITE_ANALYSIS_API_V1"
    )

    validations[
        "normal orchestrator called"
    ] = (
        mocked.call_count
        == 1
    )

    # ========================================================
    # CASE 2
    # Invalid sigungu length -> 422
    # ========================================================

    invalid_length_payload = {
        **VALID_PAYLOAD,
        "sigungu_cd": (
            "1168"
        ),
    }

    with patch(
        "api_app.analyze_site_by_parcel"
    ) as mocked:

        response = client.post(
            "/v1/site-analysis",
            json=(
                invalid_length_payload
            ),
        )

    body = response.json()

    print_case(
        "INVALID_LENGTH_422",
        response.status_code,
        body,
    )

    validations[
        "invalid length 422"
    ] = (
        response.status_code
        == 422
    )

    # Pydantic validation 단계에서 막혀야 하므로
    # orchestrator 자체가 호출되면 안 된다.
    validations[
        "invalid length no orchestrator"
    ] = (
        mocked.call_count
        == 0
    )

    # ========================================================
    # CASE 3
    # Missing required field -> 422
    # ========================================================

    missing_payload = dict(
        VALID_PAYLOAD
    )

    missing_payload.pop(
        "bjdong_cd"
    )

    with patch(
        "api_app.analyze_site_by_parcel"
    ) as mocked:

        response = client.post(
            "/v1/site-analysis",
            json=(
                missing_payload
            ),
        )

    body = response.json()

    print_case(
        "MISSING_FIELD_422",
        response.status_code,
        body,
    )

    validations[
        "missing field 422"
    ] = (
        response.status_code
        == 422
    )

    validations[
        "missing field no orchestrator"
    ] = (
        mocked.call_count
        == 0
    )

    # ========================================================
    # CASE 4
    # SiteBuildError -> 404
    # ========================================================

    with patch(
        "api_app.analyze_site_by_parcel",
        side_effect=(
            SiteBuildError(
                "건축HUB에서 건축물 데이터를 찾지 못했습니다."
            )
        ),
    ):

        response = client.post(
            "/v1/site-analysis",
            json=VALID_PAYLOAD,
        )

    body = response.json()

    print_case(
        "SITE_BUILD_404",
        response.status_code,
        body,
    )

    validations[
        "site build 404"
    ] = (
        response.status_code
        == 404
    )

    validations[
        "site build detail"
    ] = (
        body.get(
            "detail"
        )
        == (
            "건축HUB에서 건축물 데이터를 찾지 못했습니다."
        )
    )

    # ========================================================
    # CASE 5
    # BuildingAPIError -> 502
    # ========================================================

    with patch(
        "api_app.analyze_site_by_parcel",
        side_effect=(
            BuildingAPIError(
                "건축HUB HTTP 오류: 503"
            )
        ),
    ):

        response = client.post(
            "/v1/site-analysis",
            json=VALID_PAYLOAD,
        )

    body = response.json()

    print_case(
        "BUILDING_API_502",
        response.status_code,
        body,
    )

    validations[
        "building api 502"
    ] = (
        response.status_code
        == 502
    )

    validations[
        "building api detail"
    ] = (
        body.get(
            "detail"
        )
        == (
            "건축HUB HTTP 오류: 503"
        )
    )

    # ========================================================
    # CASE 6
    # SiteAnalysisError -> 500
    # ========================================================

    with patch(
        "api_app.analyze_site_by_parcel",
        side_effect=(
            SiteAnalysisError(
                "Rule Engine evaluation failed"
            )
        ),
    ):

        response = client.post(
            "/v1/site-analysis",
            json=VALID_PAYLOAD,
        )

    body = response.json()

    print_case(
        "SITE_ANALYSIS_500",
        response.status_code,
        body,
    )

    validations[
        "site analysis 500"
    ] = (
        response.status_code
        == 500
    )

    validations[
        "site analysis detail"
    ] = (
        body.get(
            "detail"
        )
        == (
            "Rule Engine evaluation failed"
        )
    )

    # ========================================================
    # CASE 7
    # Unexpected exception -> 500
    # ========================================================

    secret_internal_message = (
        "internal database password=SECRET"
    )

    with patch(
        "api_app.analyze_site_by_parcel",
        side_effect=(
            RuntimeError(
                secret_internal_message
            )
        ),
    ):

        response = client.post(
            "/v1/site-analysis",
            json=VALID_PAYLOAD,
        )

    body = response.json()

    print_case(
        "UNEXPECTED_500",
        response.status_code,
        body,
    )

    validations[
        "unexpected 500"
    ] = (
        response.status_code
        == 500
    )

    validations[
        "unexpected generic detail"
    ] = (
        body.get(
            "detail"
        )
        == (
            "SITE 분석 중 예상하지 못한 오류가 발생했습니다."
        )
    )

    # 내부 exception 내용은 HTTP response에 노출하지 않는다.
    validations[
        "unexpected no internal leak"
    ] = (
        secret_internal_message
        not in str(
            body
        )
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    all_pass = all(
        validations.values()
    )

    print(
        "========================================"
    )

    print(
        "API CONTRACT SUMMARY"
    )

    print(
        "========================================"
    )

    print(
        "Normal request:",
        "200",
    )

    print(
        "Invalid schema:",
        "422",
    )

    print(
        "Missing field:",
        "422",
    )

    print(
        "Site not found:",
        "404",
    )

    print(
        "Building API error:",
        "502",
    )

    print(
        "Analysis error:",
        "500",
    )

    print(
        "Unexpected error:",
        "500",
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