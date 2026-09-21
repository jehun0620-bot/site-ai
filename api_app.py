# -*- coding: utf-8 -*-
"""FastAPI thin HTTP layer for SITE analysis."""
from __future__ import annotations
from typing import Dict, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from site_data.address_parcel_candidate_search import search_address_parcel_candidates
from site_data.selected_parcel_candidate_verifier import verify_selected_parcel_candidate
from site_data.site_analysis_orchestrator import BuildingAPIError, SiteAnalysisError, SiteBuildError, analyze_site_by_address, analyze_site_by_parcel, analyze_site_by_selected_candidate

app=FastAPI(title="AI 대지분석 API",version="0.1.0",description="건축HUB / SITE / 공간정보 / 법규평가를 통합한 대지분석 API")


def product_error(code:str,category:str,message:str,retryable:bool=False):
    return {
        "schema_version":"SITE_API_ERROR_V1",
        "code":code,
        "category":category,
        "message":message,
        "retryable":retryable,
    }


def product_http_error(status_code:int,code:str,category:str,message:str,retryable:bool=False):
    return HTTPException(status_code=status_code,detail=product_error(code,category,message,retryable))

class SiteAnalysisRequest(BaseModel):
    sigungu_cd:str=Field(...,min_length=5,max_length=5,description="시군구코드")
    bjdong_cd:str=Field(...,min_length=5,max_length=5,description="법정동코드")
    plat_gb_cd:Literal["0","1"]=Field("0",description="대장구분: 0=일반, 1=산")
    bun:str=Field(...,min_length=4,max_length=4,description="본번")
    ji:str=Field(...,min_length=4,max_length=4,description="부번")
    project_profile:Dict[str,str]=Field(default_factory=dict)
    procedure_profile:Dict[str,str]=Field(default_factory=dict)
    include_debug:bool=False

class AddressSiteAnalysisRequest(BaseModel):
    address:str=Field(...,min_length=1,description="분석할 지번주소")
    project_profile:Dict[str,str]=Field(default_factory=dict)
    procedure_profile:Dict[str,str]=Field(default_factory=dict)
    include_debug:bool=False

class AddressParcelCandidateSearchRequest(BaseModel):
    query:str=Field(...,min_length=1,description="필지 후보를 찾을 지번주소 검색어")
    size:int=Field(10,ge=1,le=100,description="반환할 최대 후보 수")

class SelectedParcelCandidateRequest(BaseModel):
    candidate_pnu:str=Field(...,min_length=19,max_length=19,pattern=r"^\d{19}$",description="사용자가 선택한 후보 PNU")
    x:float=Field(...,ge=-180.0,le=180.0,description="후보 경도(EPSG:4326)")
    y:float=Field(...,ge=-90.0,le=90.0,description="후보 위도(EPSG:4326)")

class SelectedParcelCandidateSiteAnalysisRequest(SelectedParcelCandidateRequest):
    project_profile:Dict[str,str]=Field(default_factory=dict)
    procedure_profile:Dict[str,str]=Field(default_factory=dict)
    include_debug:bool=False

@app.get("/health")
def health(): return {"status":"ok","service":"site-analysis"}

@app.post("/v1/site-analysis")
def site_analysis(request:SiteAnalysisRequest):
    try:
        return analyze_site_by_parcel(sigungu_cd=request.sigungu_cd,bjdong_cd=request.bjdong_cd,plat_gb_cd=request.plat_gb_cd,bun=request.bun,ji=request.ji,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise product_http_error(502,"BUILDING_PROVIDER_FAILED","PROVIDER","건축물 정보를 조회하지 못했습니다.") from exc
    except SiteBuildError as exc: raise product_http_error(404,"PARCEL_BUILD_FAILED","PARCEL","분석할 필지 정보를 구성하지 못했습니다.") from exc
    except SiteAnalysisError as exc: raise product_http_error(500,"SITE_ANALYSIS_FAILED","ANALYSIS","SITE 분석을 완료하지 못했습니다.") from exc
    except Exception as exc: raise product_http_error(500,"UNEXPECTED_ERROR","INTERNAL","SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

@app.post("/v1/site-analysis/address")
def site_analysis_by_address(request:AddressSiteAnalysisRequest):
    try:
        return analyze_site_by_address(address=request.address,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise product_http_error(502,"BUILDING_PROVIDER_FAILED","PROVIDER","건축물 정보를 조회하지 못했습니다.") from exc
    except SiteBuildError as exc: raise product_http_error(404,"PARCEL_BUILD_FAILED","PARCEL","분석할 필지 정보를 구성하지 못했습니다.") from exc
    except SiteAnalysisError as exc: raise product_http_error(500,"SITE_ANALYSIS_FAILED","ANALYSIS","SITE 분석을 완료하지 못했습니다.") from exc
    except Exception as exc: raise HTTPException(status_code=500,detail="SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

@app.post("/v1/site-analysis/selected-candidate")
def site_analysis_by_selected_candidate(request:SelectedParcelCandidateSiteAnalysisRequest):
    try:
        return analyze_site_by_selected_candidate(candidate_pnu=request.candidate_pnu,x=request.x,y=request.y,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise product_http_error(502,"BUILDING_PROVIDER_FAILED","PROVIDER","건축물 정보를 조회하지 못했습니다.") from exc
    except SiteBuildError as exc: raise product_http_error(404,"PARCEL_BUILD_FAILED","PARCEL","분석할 필지 정보를 구성하지 못했습니다.") from exc
    except SiteAnalysisError as exc: raise product_http_error(500,"SITE_ANALYSIS_FAILED","ANALYSIS","SITE 분석을 완료하지 못했습니다.") from exc
    except Exception as exc: raise product_http_error(500,"UNEXPECTED_ERROR","INTERNAL","선택 필지 SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

@app.post("/v1/parcel-candidates/address")
def parcel_candidates_by_address(request:AddressParcelCandidateSearchRequest):
    try:
        candidates=search_address_parcel_candidates(request.query,size=request.size)
        return {
            "schema_version":"PARCEL_CANDIDATE_SEARCH_V1",
            "status":"READY",
            "query":request.query,
            "count":len(candidates),
            "candidates":[candidate.to_dict() for candidate in candidates],
        }
    except Exception as exc:
        raise product_http_error(500,"CANDIDATE_SEARCH_FAILED","PROVIDER","필지 후보 검색을 완료하지 못했습니다.") from exc

@app.post("/v1/parcel-candidates/confirm")
def confirm_selected_parcel_candidate(request:SelectedParcelCandidateRequest):
    try:
        verification=verify_selected_parcel_candidate(candidate_pnu=request.candidate_pnu,x=request.x,y=request.y)
        if not verification.verified:
            raise product_http_error(404,"PARCEL_VERIFICATION_FAILED","PARCEL","선택한 필지를 검증할 수 없습니다.")
        if not isinstance(verification.geometry,dict):
            raise product_http_error(404,"PARCEL_GEOMETRY_UNRESOLVED","PARCEL","선택한 필지의 검증된 경계를 확인할 수 없습니다.")
        return {
            "schema_version":"PARCEL_CONFIRMATION_V1",
            "status":"READY",
            "parcel":{
                "pnu":verification.pnu,
                "sigungu_cd":verification.sigungu_cd,
                "bjdong_cd":verification.bjdong_cd,
                "plat_gb_cd":verification.plat_gb_cd,
                "bun":verification.bun,
                "ji":verification.ji,
                "x":verification.x,
                "y":verification.y,
                "crs":verification.crs,
            },
            "verification":{
                "status":verification.status,
                "resolution":verification.resolution,
            },
            "geometry":verification.geometry,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise product_http_error(500,"UNEXPECTED_ERROR","INTERNAL","선택 필지 확인 중 예상하지 못한 오류가 발생했습니다.") from exc
