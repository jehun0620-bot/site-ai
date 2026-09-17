# -*- coding: utf-8 -*-
"""FastAPI thin HTTP layer for SITE analysis."""
from __future__ import annotations
from typing import Dict, Literal
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from site_data.address_parcel_candidate_search import search_address_parcel_candidates
from site_data.site_analysis_orchestrator import BuildingAPIError, SiteAnalysisError, SiteBuildError, analyze_site_by_address, analyze_site_by_parcel, analyze_site_by_selected_candidate

app=FastAPI(title="AI 대지분석 API",version="0.1.0",description="건축HUB / SITE / 공간정보 / 법규평가를 통합한 대지분석 API")

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

class SelectedParcelCandidateSiteAnalysisRequest(BaseModel):
    candidate_pnu:str=Field(...,min_length=19,max_length=19,pattern=r"^\d{19}$",description="사용자가 선택한 후보 PNU")
    x:float=Field(...,ge=-180.0,le=180.0,description="후보 경도(EPSG:4326)")
    y:float=Field(...,ge=-90.0,le=90.0,description="후보 위도(EPSG:4326)")
    project_profile:Dict[str,str]=Field(default_factory=dict)
    procedure_profile:Dict[str,str]=Field(default_factory=dict)
    include_debug:bool=False

@app.get("/health")
def health(): return {"status":"ok","service":"site-analysis"}

@app.post("/v1/site-analysis")
def site_analysis(request:SiteAnalysisRequest):
    try:
        return analyze_site_by_parcel(sigungu_cd=request.sigungu_cd,bjdong_cd=request.bjdong_cd,plat_gb_cd=request.plat_gb_cd,bun=request.bun,ji=request.ji,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise HTTPException(status_code=502,detail=str(exc)) from exc
    except SiteBuildError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except SiteAnalysisError as exc: raise HTTPException(status_code=500,detail=str(exc)) from exc
    except Exception as exc: raise HTTPException(status_code=500,detail="SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

@app.post("/v1/site-analysis/address")
def site_analysis_by_address(request:AddressSiteAnalysisRequest):
    try:
        return analyze_site_by_address(address=request.address,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise HTTPException(status_code=502,detail=str(exc)) from exc
    except SiteBuildError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except SiteAnalysisError as exc: raise HTTPException(status_code=500,detail=str(exc)) from exc
    except Exception as exc: raise HTTPException(status_code=500,detail="SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

@app.post("/v1/site-analysis/selected-candidate")
def site_analysis_by_selected_candidate(request:SelectedParcelCandidateSiteAnalysisRequest):
    try:
        return analyze_site_by_selected_candidate(candidate_pnu=request.candidate_pnu,x=request.x,y=request.y,project_profile=request.project_profile,procedure_profile=request.procedure_profile,include_debug=request.include_debug)
    except BuildingAPIError as exc: raise HTTPException(status_code=502,detail=str(exc)) from exc
    except SiteBuildError as exc: raise HTTPException(status_code=404,detail=str(exc)) from exc
    except SiteAnalysisError as exc: raise HTTPException(status_code=500,detail=str(exc)) from exc
    except Exception as exc: raise HTTPException(status_code=500,detail="선택 필지 SITE 분석 중 예상하지 못한 오류가 발생했습니다.") from exc

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
        raise HTTPException(status_code=500,detail="필지 후보 검색 중 예상하지 못한 오류가 발생했습니다.") from exc
