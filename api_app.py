# -*- coding: utf-8 -*-

"""
STEP 17-21-C-12-5
FastAPI Thin HTTP Layer

목표
======================================================================
SITE Analysis Orchestrator를 HTTP API로 노출한다.

중요
======================================================================
이 계층은 법규 / 공간정보 / 건축물 분석 로직을 직접 수행하지 않는다.

HTTP 요청
    ↓
analyze_site_by_parcel()
    ↓
SITE_ANALYSIS_API_V1 response
"""

from __future__ import annotations

from typing import Dict

from fastapi import (
    FastAPI,
    HTTPException,
)

from pydantic import (
    BaseModel,
    Field,
)

from site_data.site_analysis_orchestrator import (
    BuildingAPIError,
    SiteAnalysisError,
    SiteBuildError,
    analyze_site_by_parcel,
)


# ============================================================
# app
# ============================================================

app = FastAPI(
    title="AI 대지분석 API",
    version="0.1.0",
    description=(
        "건축HUB / SITE / 공간정보 / 법규평가를 통합한 "
        "대지분석 API"
    ),
)


# ============================================================
# request schema
# ============================================================

class SiteAnalysisRequest(
    BaseModel
):

    sigungu_cd: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="시군구코드",
    )

    bjdong_cd: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="법정동코드",
    )

    bun: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="본번",
    )

    ji: str = Field(
        ...,
        min_length=4,
        max_length=4,
        description="부번",
    )

    project_profile: Dict[
        str,
        str
    ] = Field(
        default_factory=dict,
    )

    procedure_profile: Dict[
        str,
        str
    ] = Field(
        default_factory=dict,
    )

    include_debug: bool = False


# ============================================================
# health
# ============================================================

@app.get(
    "/health"
)
def health():

    return {
        "status": "ok",
        "service": "site-analysis",
    }


# ============================================================
# analysis
# ============================================================

@app.post(
    "/v1/site-analysis"
)
def site_analysis(
    request: SiteAnalysisRequest,
):

    try:

        return analyze_site_by_parcel(
            sigungu_cd=(
                request.sigungu_cd
            ),

            bjdong_cd=(
                request.bjdong_cd
            ),

            bun=(
                request.bun
            ),

            ji=(
                request.ji
            ),

            project_profile=(
                request.project_profile
            ),

            procedure_profile=(
                request.procedure_profile
            ),

            include_debug=(
                request.include_debug
            ),
        )

    except BuildingAPIError as exc:

        raise HTTPException(
            status_code=502,
            detail=str(
                exc
            ),
        ) from exc

    except SiteBuildError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(
                exc
            ),
        ) from exc

    except SiteAnalysisError as exc:

        raise HTTPException(
            status_code=500,
            detail=str(
                exc
            ),
        ) from exc

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "SITE 분석 중 예상하지 못한 오류가 발생했습니다."
            ),
        ) from exc