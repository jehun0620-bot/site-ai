# -*- coding: utf-8 -*-
"""SITE Analysis Service Orchestrator."""
from __future__ import annotations
import copy, os
from pathlib import Path
from typing import Any, Dict, Optional
import requests
from dotenv import load_dotenv
from site_data.address_parcel_identity_resolver import resolve_address_parcel_identity
from site_data.selected_parcel_candidate_verifier import verify_selected_parcel_candidate
from site_data.site_builder import create_site
from site_data.site_data_model import Site
from site_data.site_analysis_service import analyze_site_object, site_to_analysis_input
from site_data.site_analysis_response import build_site_analysis_response
from site_data.vworld_api import get_land_characteristics
from site_data.land_converter import select_latest_land_record, convert_land_record
from law_data.historical_site_event_admitted_rule_input_adapter import adapt_admitted_historical_site_event_rule_input
from law_data.historical_site_event_candidate_condition_binding_authorization import authorize_historical_site_event_candidate_condition_binding
from law_data.historical_site_event_candidate_repair_consistency_authorization import authorize_historical_site_event_candidate_repair_consistency
from law_data.historical_site_event_site_applicability_admission import HistoricalSiteEventSiteApplicabilityAdmissionResult
from law_data.historical_site_event_site_truth_promotion_rule_input_bridge import HistoricalSiteEventSiteTruthPromotionRuleInputBridge
from law_data.historical_trusted_internal_source_handoff_authorization import HistoricalTrustedInternalSourceHandoffAuthorization
from law_data.historical_verified_rule_input_envelope import seal_verified_historical_rule_input
from law_data.district_unit_plan_verified_registry_candidate_envelope import DistrictUnitPlanVerifiedRegistryCandidateEnvelope
BASE_DIR=Path(__file__).resolve().parent.parent; load_dotenv(BASE_DIR/".env")
BUILDING_API_URL="http://apis.data.go.kr/1613000/BldRgstHubService/getBrTitleInfo"
class SiteAnalysisError(RuntimeError): pass
class BuildingAPIError(SiteAnalysisError): pass
class SiteBuildError(SiteAnalysisError): pass

def fetch_building_items(*,sigungu_cd:str,bjdong_cd:str,bun:str,ji:str,plat_gb_cd:str="0",service_key:Optional[str]=None,timeout:int=30)->Dict[str,Any]:
    key=service_key or os.getenv("DATA_API_KEY")
    if not key: raise BuildingAPIError("DATA_API_KEY를 찾을 수 없습니다.")
    params={"sigunguCd":str(sigungu_cd),"bjdongCd":str(bjdong_cd),"platGbCd":str(plat_gb_cd),"bun":str(bun),"ji":str(ji),"serviceKey":key,"numOfRows":"100","pageNo":"1","_type":"json"}
    try: response=requests.get(BUILDING_API_URL,params=params,timeout=timeout)
    except requests.RequestException as exc: raise BuildingAPIError(f"건축HUB 요청 실패: {exc}") from exc
    if response.status_code!=200: raise BuildingAPIError(f"건축HUB HTTP 오류: {response.status_code}")
    try: data=response.json()
    except ValueError as exc: raise BuildingAPIError("건축HUB 응답 JSON 파싱 실패") from exc
    api_response=data.get("response")
    if not isinstance(api_response,dict): raise BuildingAPIError("건축HUB response 없음")
    header=api_response.get("header",{})
    if header.get("resultCode")!="00": raise BuildingAPIError(f"건축HUB API 오류: {header.get('resultCode')} / {header.get('resultMsg')}")
    body=api_response.get("body",{}); items=(body.get("items") or {}).get("item",[])
    if isinstance(items,dict): items=[items]
    if not isinstance(items,list): items=[]
    return {"items":items,"total_count":body.get("totalCount",0),"result_code":header.get("resultCode"),"result_message":header.get("resultMsg")}

def _actual_site_pnu(site:Any)->str:
    try: pnu=str(site_to_analysis_input(site).get("pnu") or "").strip()
    except (TypeError,ValueError,AttributeError): return ""
    return pnu if len(pnu)==19 and pnu.isdigit() else ""

def _admitted_canonical_pnu(applicability):
    if not isinstance(applicability,HistoricalSiteEventSiteApplicabilityAdmissionResult) or not applicability.admitted or applicability.site_admission is None:return ""
    return str(applicability.site_admission.canonical_pnu or "").strip()

def _parcel_address_from_land_record(record:Any,pnu:str)->str:
    if not isinstance(record,dict) or str(record.get("pnu") or "").strip()!=pnu: return ""
    locality=str(record.get("ldCodeNm") or "").strip(); lot=str(record.get("mnnmSlno") or "").strip()
    if not locality or not lot: return ""
    register_code=str(record.get("regstrSeCode") or "").strip()
    if register_code=="2": return f"{locality} 산 {lot}"
    if register_code=="1": return f"{locality} {lot}"
    return ""

def _parcel_only_site(*,sigungu_cd:str,bjdong_cd:str,plat_gb_cd:str,bun:str,ji:str)->Site:
    site=Site(site_id=f"{sigungu_cd}-{bjdong_cd}-{bun}-{ji}",sigungu_cd=str(sigungu_cd).strip(),bjdong_cd=str(bjdong_cd).strip(),plat_gb_cd=str(plat_gb_cd).strip(),bun=str(bun).strip(),ji=str(ji).strip())
    pnu=_actual_site_pnu(site)
    if not pnu: raise SiteBuildError("유효한 필지 identity로 Site 객체를 생성할 수 없습니다.")
    try:
        records=get_land_characteristics(pnu); record=select_latest_land_record(records)
        if record is not None:
            site.land=convert_land_record(record)
            site.address=_parcel_address_from_land_record(record,pnu)
    except (RuntimeError,ValueError,TypeError): pass
    return site

def analyze_site_by_parcel(*,sigungu_cd:str,bjdong_cd:str,bun:str,ji:str,plat_gb_cd:str="0",project_profile:Optional[Dict[str,str]]=None,procedure_profile:Optional[Dict[str,str]]=None,production_condition_shadow_sources:Optional[Any]=None,historical_handoff_authorization:Optional[HistoricalTrustedInternalSourceHandoffAuthorization]=None,historical_site_applicability_admission:Optional[HistoricalSiteEventSiteApplicabilityAdmissionResult]=None,historical_promotion_rule_input_bridge:Optional[HistoricalSiteEventSiteTruthPromotionRuleInputBridge]=None,district_unit_plan_registry_candidate:Optional[Any]=None,include_debug:bool=False,service_key:Optional[str]=None)->Dict[str,Any]:
    building_result=fetch_building_items(sigungu_cd=sigungu_cd,bjdong_cd=bjdong_cd,plat_gb_cd=plat_gb_cd,bun=bun,ji=ji,service_key=service_key); items=building_result["items"]
    if items:
        site=create_site(items)
        if site is None: raise SiteBuildError("Site 객체 생성 실패")
        if str(site.plat_gb_cd).strip()!=str(plat_gb_cd).strip(): raise SiteBuildError("건축HUB 대장구분과 요청 필지 identity가 일치하지 않습니다.")
    else: site=_parcel_only_site(sigungu_cd=sigungu_cd,bjdong_cd=bjdong_cd,plat_gb_cd=plat_gb_cd,bun=bun,ji=ji)
    raw_historical_rule_input=None; verified_historical_input=None; verified_district_unit_plan_input=None; actual_site_pnu=""
    legacy_requested=bool(historical_handoff_authorization is not None or historical_site_applicability_admission is not None); promotion_requested=historical_promotion_rule_input_bridge is not None; historical_requested=legacy_requested or promotion_requested; district_requested=district_unit_plan_registry_candidate is not None
    if legacy_requested and promotion_requested: raise SiteAnalysisError("Historical SITE input is ambiguous: legacy and promotion paths cannot be used together")
    if historical_requested and district_requested: raise SiteAnalysisError("Historical and district-unit verified SITE inputs cannot be combined")
    if district_requested:
        envelope=district_unit_plan_registry_candidate
        if not isinstance(envelope,DistrictUnitPlanVerifiedRegistryCandidateEnvelope) or not envelope.ready: raise SiteAnalysisError("District-unit verified registry candidate envelope is not ready")
        actual_site_pnu=_actual_site_pnu(site)
        if not actual_site_pnu or actual_site_pnu!=envelope.canonical_pnu: raise SiteAnalysisError("District-unit verified registry candidate PNU rebinding failed")
        verified_district_unit_plan_input=envelope
    if promotion_requested:
        bridge=historical_promotion_rule_input_bridge
        if not isinstance(bridge,HistoricalSiteEventSiteTruthPromotionRuleInputBridge) or not bridge.ready: raise SiteAnalysisError("Historical SITE promotion rule-input bridge is not ready")
        actual_site_pnu=_actual_site_pnu(site); repairs=bridge.historical_rule_input.get("repairs"); repair_pnus={str(r.get("pnu") or "").strip() for r in repairs or [] if isinstance(r,dict)}
        if not actual_site_pnu or len(repair_pnus)!=1 or actual_site_pnu not in repair_pnus: raise SiteAnalysisError("Historical SITE promotion PNU rebinding failed")
        raw_historical_rule_input=copy.deepcopy(dict(bridge.historical_rule_input))
    elif legacy_requested:
        actual_site_pnu=_actual_site_pnu(site); admitted_pnu=_admitted_canonical_pnu(historical_site_applicability_admission)
        if not actual_site_pnu or not admitted_pnu or actual_site_pnu!=admitted_pnu: raise SiteAnalysisError("Historical SITE applicability PNU rebinding failed")
        consistency=authorize_historical_site_event_candidate_repair_consistency(historical_site_applicability_admission,historical_handoff_authorization)
        if not consistency.authorized: raise SiteAnalysisError(f"Historical SITE candidate/repair consistency failed: {consistency.status} / {','.join(consistency.missing_gates)}")
        binding=authorize_historical_site_event_candidate_condition_binding(historical_site_applicability_admission,historical_handoff_authorization)
        if not binding.authorized: raise SiteAnalysisError(f"Historical SITE candidate/condition binding failed: {binding.status} / {','.join(binding.missing_gates)}")
        adapter=adapt_admitted_historical_site_event_rule_input(historical_site_applicability_admission,historical_handoff_authorization)
        if not adapter.ready: raise SiteAnalysisError(f"Historical SITE applicability/handoff admission failed: {adapter.status} / {','.join(adapter.missing_gates)}")
        raw_historical_rule_input=copy.deepcopy(dict(adapter.historical_rule_input))
    if raw_historical_rule_input is not None:
        verified_historical_input=seal_verified_historical_rule_input(canonical_pnu=actual_site_pnu,historical_rule_input=raw_historical_rule_input)
        if not verified_historical_input.ready: raise SiteAnalysisError("Historical verified rule-input envelope is not ready")
    analysis=analyze_site_object(site=site,project_profile=project_profile or {},procedure_profile=procedure_profile or {},production_condition_shadow_sources=production_condition_shadow_sources,historical_rule_input=verified_historical_input,district_unit_plan_registry_candidate=verified_district_unit_plan_input)
    response=build_site_analysis_response(analysis,include_debug=include_debug); response["service"]={"building_count":len(items),"building_total_count":building_result.get("total_count"),"building_api_status":building_result.get("result_code")}; return response


def analyze_site_by_address(*,address:str,project_profile:Optional[Dict[str,str]]=None,procedure_profile:Optional[Dict[str,str]]=None,include_debug:bool=False,service_key:Optional[str]=None,vworld_api_key:Optional[str]=None)->Dict[str,Any]:
    """Resolve a parcel address to verified canonical identity, then reuse parcel analysis."""
    identity=resolve_address_parcel_identity(address,api_key=vworld_api_key)
    if not identity.verified:
        raise SiteBuildError(f"주소에서 검증된 필지를 확정할 수 없습니다: {identity.resolution}")
    return analyze_site_by_parcel(
        sigungu_cd=identity.sigungu_cd,
        bjdong_cd=identity.bjdong_cd,
        plat_gb_cd=identity.plat_gb_cd,
        bun=identity.bun,
        ji=identity.ji,
        project_profile=project_profile,
        procedure_profile=procedure_profile,
        include_debug=include_debug,
        service_key=service_key,
    )


def analyze_site_by_selected_candidate(*,candidate_pnu:str,x:float,y:float,project_profile:Optional[Dict[str,str]]=None,procedure_profile:Optional[Dict[str,str]]=None,include_debug:bool=False,service_key:Optional[str]=None,vworld_api_key:Optional[str]=None)->Dict[str,Any]:
    """Re-verify a user-selected discovery candidate, then reuse parcel analysis."""
    identity=verify_selected_parcel_candidate(candidate_pnu,x,y,api_key=vworld_api_key)
    if not identity.verified:
        raise SiteBuildError(f"선택한 필지를 다시 검증할 수 없습니다: {identity.resolution}")
    return analyze_site_by_parcel(
        sigungu_cd=identity.sigungu_cd,
        bjdong_cd=identity.bjdong_cd,
        plat_gb_cd=identity.plat_gb_cd,
        bun=identity.bun,
        ji=identity.ji,
        project_profile=project_profile,
        procedure_profile=procedure_profile,
        include_debug=include_debug,
        service_key=service_key,
    )
