# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-4
SITE Analysis Service Orchestrator

목표
======================================================================
실제 외부 입력부터 최종 API Response까지의 전체 흐름을
하나의 재사용 가능한 서비스 함수로 묶는다.

흐름
======================================================================
parcel identifiers
    ↓
건축HUB API
    ↓
create_site()
    ↓
Site
    ↓
analyze_site_object()
    ↓
Final SITE Analysis
    ↓
build_site_analysis_response()
    ↓
SITE_ANALYSIS_API_V1

중요
======================================================================
HTTP/FastAPI/Flask와 독립적이다.

즉 향후 웹 API 계층에서는 이 모듈의 함수만 호출하면 된다.
"""

from __future__ import annotations

import os

from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv


from site_data.site_builder import (
    create_site,
)

from site_data.site_analysis_service import (
    analyze_site_object,
)

from site_data.site_analysis_response import (
    build_site_analysis_response,
)


# ============================================================
# PATH / ENV
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
)

load_dotenv(
    BASE_DIR
    / ".env"
)


BUILDING_API_URL = (
    "http://apis.data.go.kr/"
    "1613000/BldRgstHubService/"
    "getBrTitleInfo"
)


# ============================================================
# errors
# ============================================================

class SiteAnalysisError(
    RuntimeError
):
    pass


class BuildingAPIError(
    SiteAnalysisError
):
    pass


class SiteBuildError(
    SiteAnalysisError
):
    pass


# ============================================================
# Building HUB
# ============================================================

def fetch_building_items(
    *,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    service_key: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:

    key = (
        service_key
        or os.getenv(
            "DATA_API_KEY"
        )
    )

    if not key:

        raise BuildingAPIError(
            "DATA_API_KEY를 찾을 수 없습니다."
        )

    params = {
        "sigunguCd": (
            str(
                sigungu_cd
            )
        ),

        "bjdongCd": (
            str(
                bjdong_cd
            )
        ),

        "bun": (
            str(
                bun
            )
        ),

        "ji": (
            str(
                ji
            )
        ),

        "serviceKey": (
            key
        ),

        "numOfRows": (
            "100"
        ),

        "pageNo": (
            "1"
        ),

        "_type": (
            "json"
        ),
    }

    try:

        response = requests.get(
            BUILDING_API_URL,
            params=params,
            timeout=timeout,
        )

    except requests.RequestException as exc:

        raise BuildingAPIError(
            f"건축HUB 요청 실패: {exc}"
        ) from exc

    if (
        response.status_code
        != 200
    ):

        raise BuildingAPIError(
            "건축HUB HTTP 오류: "
            f"{response.status_code}"
        )

    try:

        data = (
            response.json()
        )

    except ValueError as exc:

        content_type = (
            response.headers.get(
                "Content-Type",
                "",
            )
        )

        response_text = (
            response.text
            or ""
        )

        response_preview = (
            response_text[
                :500
            ]
            .replace(
                "\r",
                " ",
            )
            .replace(
                "\n",
                " ",
            )
        )

        raise BuildingAPIError(
            "건축HUB 응답 JSON 파싱 실패"
            f" | HTTP={response.status_code}"
            f" | Content-Type={content_type}"
            f" | Length={len(response_text)}"
            f" | Preview={response_preview!r}"
        ) from exc

    api_response = (
        data.get(
            "response"
        )
    )

    if not isinstance(
        api_response,
        dict,
    ):

        raise BuildingAPIError(
            "건축HUB response 없음"
        )

    header = (
        api_response.get(
            "header",
            {},
        )
    )

    if (
        header.get(
            "resultCode"
        )
        != "00"
    ):

        raise BuildingAPIError(
            "건축HUB API 오류: "
            f"{header.get('resultCode')} / "
            f"{header.get('resultMsg')}"
        )

    body = (
        api_response.get(
            "body",
            {},
        )
    )

    items_container = (
        body.get(
            "items"
        )
        or {}
    )

    items = (
        items_container.get(
            "item",
            [],
        )
    )

    if isinstance(
        items,
        dict,
    ):

        items = [
            items
        ]

    if not isinstance(
        items,
        list,
    ):

        items = []

    return {
        "items": (
            items
        ),

        "total_count": (
            body.get(
                "totalCount",
                0,
            )
        ),

        "result_code": (
            header.get(
                "resultCode"
            )
        ),

        "result_message": (
            header.get(
                "resultMsg"
            )
        ),
    }


# ============================================================
# orchestrator
# ============================================================

def analyze_site_by_parcel(
    *,
    sigungu_cd: str,
    bjdong_cd: str,
    bun: str,
    ji: str,
    project_profile: Optional[
        Dict[str, str]
    ] = None,
    procedure_profile: Optional[
        Dict[str, str]
    ] = None,
    include_debug: bool = False,
    service_key: Optional[str] = None,
) -> Dict[str, Any]:

    # ========================================================
    # 1. Building HUB
    # ========================================================

    building_result = (
        fetch_building_items(
            sigungu_cd=(
                sigungu_cd
            ),

            bjdong_cd=(
                bjdong_cd
            ),

            bun=(
                bun
            ),

            ji=(
                ji
            ),

            service_key=(
                service_key
            ),
        )
    )

    items = (
        building_result[
            "items"
        ]
    )

    if not items:

        raise SiteBuildError(
            "건축HUB에서 건축물 데이터를 찾지 못했습니다."
        )

    # ========================================================
    # 2. Site Builder
    # ========================================================

    site = (
        create_site(
            items
        )
    )

    if site is None:

        raise SiteBuildError(
            "Site 객체 생성 실패"
        )

    # ========================================================
    # 3. Rule / Spatial Analysis
    # ========================================================

    analysis = (
        analyze_site_object(
            site=(
                site
            ),

            project_profile=(
                project_profile
                or {}
            ),

            procedure_profile=(
                procedure_profile
                or {}
            ),
        )
    )

    # ========================================================
    # 4. Public response
    # ========================================================

    response = (
        build_site_analysis_response(
            analysis,
            include_debug=(
                include_debug
            ),
        )
    )

    # ========================================================
    # 5. service metadata
    # ========================================================

    response[
        "service"
    ] = {
        "building_count": (
            len(
                items
            )
        ),

        "building_total_count": (
            building_result.get(
                "total_count"
            )
        ),

        "building_api_status": (
            building_result.get(
                "result_code"
            )
        ),
    }

    return response