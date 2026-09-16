# -*- coding: utf-8 -*-
"""SITE Analysis Object Builder."""
from __future__ import annotations
import copy
import json
from pathlib import Path
from typing import Any, Dict, Optional
from law_data.zone_base_numeric_resolver import resolve_zone_base_numeric
from law_data.production_spatial_condition_adapter import adapt_spatial_condition_to_production_contract
from law_data.production_site_condition_shadow_collector import collect_production_site_condition_shadows
from law_data.historical_site_event_rule_engine_registry_adapter import adapt_historical_site_event_rule_engine_registry
from law_data.historical_spatial_registry_collision_policy import evaluate_historical_spatial_registry_collision_policy
from law_data.historical_merged_registry_live_consumption_authorization import authorize_historical_merged_registry_live_consumption
from law_data.historical_verified_rule_input_envelope import HistoricalVerifiedRuleInputEnvelope
try:
    from .rule_evaluation_pipeline import evaluate_site_rules
    from .site_identity_resolver import resolve_site_identity
    from .site_spatial_payload_resolver import resolve_site_spatial_payload
except ImportError:
    from rule_evaluation_pipeline import evaluate_site_rules
    from site_identity_resolver import resolve_site_identity
    from site_spatial_payload_resolver import resolve_site_spatial_payload
try:
    from .spatial_condition_evaluator import get_supported_spatial_conditions, resolve_site_spatial_condition
except ImportError:
    from spatial_condition_evaluator import get_supported_spatial_conditions, resolve_site_spatial_condition

BASE_DIR=Path(__file__).resolve().parent.parent
OUTPUT_DIR=BASE_DIR/"law_data"/"output"
SITE_COMPLETE_PATH=OUTPUT_DIR/"site_rule_evaluation_site_complete.json"
BASE_NUMERIC_PATH=OUTPUT_DIR/"base_numeric_regulation_hierarchy.json"

def load_json(path:Path)->Dict[str,Any]:
    if not path.exists(): raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r",encoding="utf-8") as f:return json.load(f)
def safe_string(value:Any)->str:return "" if value is None else str(value).strip()
def accept_historical_rule_input(value:Any)->Any:return copy.deepcopy(value)
def build_production_condition_contract_shadow(ctx:Any)->Dict[str,Dict[str,Any]]:
    if not isinstance(ctx,dict):return {}
    return {str(n):adapt_spatial_condition_to_production_contract(v,production_eligible=False,runtime_registered=False).to_dict() for n,v in ctx.items() if isinstance(v,dict)}
def build_land_area_result(site_input,site):
    official=site_input.get("land_area"); parcel=site.get("spatial",{}).get("parcel",{}); spatial=parcel.get("area",{}).get("value"); diff=ratio=None
    if official is not None and spatial is not None:
        diff=float(official)-float(spatial)
        if float(official)!=0:ratio=abs(diff)/float(official)*100.0
    return {"official":{"value":official,"unit":"square_meter","source":"VWORLD_LAND_CHARACTERISTICS","role":"LEGAL_OR_ATTRIBUTE_LAND_AREA"},"spatial":{"value":spatial,"unit":"native_crs_square_units","source":"MAPPLAN_PARCEL_GEOMETRY","role":"SPATIAL_GEOMETRY_AREA","crs":parcel.get("crs"),"crs_status":parcel.get("crs_status")},"difference":{"value":diff,"ratio_percent":ratio},"resolution":"KEEP_BOTH_WITH_SOURCE_ROLES","primary":"official"}
def build_regulation_result(e):
    n=e.get("numeric",{}); b=n.get("building_coverage_ratio"); f=n.get("floor_area_ratio")
    return {"building_coverage_ratio":{"value":b,"unit":"percent","status":"CONFIRMED" if b is not None else "PENDING"},"floor_area_ratio":{"value":f,"unit":"percent","status":"CONFIRMED" if f is not None else "PENDING"},"numeric_resolution":n.get("resolution"),"direct_relaxation_count":n.get("direct_relaxation_count",0),"numeric_active_before_guard":n.get("active_before_guard",0),"numeric_excluded_count":n.get("excluded_count",0),"numeric_retained_count":n.get("retained_count",0)}
def build_rule_summary(e):
    s=e.get("rule_summary",{}); a=int(s.get("APPLICABLE",0) or 0); na=int(s.get("NOT_APPLICABLE",0) or 0); c=int(s.get("CONDITIONAL",0) or 0); u=int(s.get("UNKNOWN",0) or 0)
    return {"total":a+na+c+u,"applicable":a,"not_applicable":na,"conditional":c,"unknown":u}
def build_input_requirements(e):
    r=e.get("remaining_inputs",{}); p=copy.deepcopy(r.get("project",[])); q=copy.deepcopy(r.get("procedure",[])); return {"project":p,"procedure":q,"project_count":len(p),"procedure_count":len(q),"requires_additional_input":bool(p or q)}
def build_external_dependencies(e):
    h=copy.deepcopy(e.get("external_dependencies",{})).get("historical",{}); active=[]
    if h:active.append({"category":"SITE_HISTORY","condition":h.get("condition"),"status":h.get("status"),"confidence":h.get("confidence"),"automation_state":h.get("automation_state"),"blocking_analysis":h.get("blocking_site_stage",False)})
    return {"count":len(active),"items":active}
def determine_analysis_status(e,r):
    ready=e.get("pipeline",{}).get("ready") is True; b=r.get("building_coverage_ratio",{}).get("status")=="CONFIRMED"; f=r.get("floor_area_ratio",{}).get("status")=="CONFIRMED"
    return "READY" if ready and b and f else ("PARTIAL" if ready else "NOT_READY")

def build_site_analysis(project_profile:Optional[Dict[str,str]]=None,procedure_profile:Optional[Dict[str,str]]=None,site_input:Optional[Dict[str,Any]]=None,production_condition_shadow_sources:Optional[Any]=None,historical_rule_input:Optional[Any]=None)->Dict[str,Any]:
    project_profile=project_profile or {}; procedure_profile=procedure_profile or {}; site_input=site_input or {}
    historical_snapshot=None
    if historical_rule_input is not None:
        if not isinstance(historical_rule_input,HistoricalVerifiedRuleInputEnvelope) or not historical_rule_input.ready: raise ValueError("verified historical rule input envelope required")
        requested_pnu=str(site_input.get("pnu") or "").strip()
        if not requested_pnu or requested_pnu!=historical_rule_input.canonical_pnu: raise ValueError("historical rule input envelope PNU mismatch")
        historical_snapshot=copy.deepcopy(dict(historical_rule_input.historical_rule_input))
    site_complete=load_json(SITE_COMPLETE_PATH); base_numeric=load_json(BASE_NUMERIC_PATH); base_site=copy.deepcopy(site_complete.get("site",{}))
    if not safe_string(base_site.get("zone")):base_site["zone"]=base_numeric.get("site_zone")
    if not safe_string(base_site.get("land_use_zone")):base_site["land_use_zone"]=base_numeric.get("site_zone")
    site=resolve_site_identity(base_site=base_site,site_input=site_input)
    resolved_pnu=str(site.get("pnu") or "").strip()
    if historical_rule_input is not None and resolved_pnu!=historical_rule_input.canonical_pnu: raise ValueError("historical rule input resolved SITE PNU mismatch")
    spatial=resolve_site_spatial_payload(site=site); site["spatial"]=spatial; parcel=spatial.get("parcel",{})
    names=get_supported_spatial_conditions(); ctx={n:resolve_site_spatial_condition(condition_name=n,site=site,parcel=parcel) for n in names}; site["runtime_conditions"]=copy.deepcopy(ctx)
    shadow=build_production_condition_contract_shadow(ctx); site["production_condition_contracts"]=collect_production_site_condition_shadows(shadow,copy.deepcopy(production_condition_shadow_sources))
    ec=site.get("coordinate"); valid=isinstance(ec,dict) and isinstance(ec.get("x"),(int,float)) and isinstance(ec.get("y"),(int,float))
    if not valid:
        lc=spatial.get("parcel",{}).get("source",{}).get("live",{}).get("coordinate",{})
        if isinstance(lc,dict) and lc.get("crs")=="EPSG:4326" and isinstance(lc.get("x"),(int,float)) and isinstance(lc.get("y"),(int,float)):site["coordinate"]={"x":lc.get("x"),"y":lc.get("y"),"crs":"EPSG:4326","source":lc.get("source") or "VWORLD_ADDRESS_SEARCH","status":"CONFIRMED"}
    zone=resolve_zone_base_numeric(site.get("zone")); engine=evaluate_site_rules(project_profile=project_profile,procedure_profile=procedure_profile,base_numeric_context=zone,site_zone_context=site.get("zone"),site_condition_context=ctx)
    if historical_snapshot is not None:
        reg=adapt_historical_site_event_rule_engine_registry(historical_snapshot)
        if not reg.registry_ready:raise ValueError("historical rule input registry adaptation failed")
        collision=evaluate_historical_spatial_registry_collision_policy(engine.get("site_registry"),reg.historical_site_registry)
        if not collision.merge_candidate_ready:raise ValueError("historical/spatial registry collision policy failed")
        auth=authorize_historical_merged_registry_live_consumption(collision)
        if not auth.live_consumption_authorized:raise ValueError("historical merged registry live consumption unauthorized")
        engine=evaluate_site_rules(project_profile=project_profile,procedure_profile=procedure_profile,base_numeric_context=zone,site_zone_context=site.get("zone"),site_condition_context=ctx,historical_registry_authorization=auth)
    land=build_land_area_result(site_input,site); regulation=build_regulation_result(engine); summary=build_rule_summary(engine); req=build_input_requirements(engine); ext=build_external_dependencies(engine); status=determine_analysis_status(engine,regulation)
    inp={"site":copy.deepcopy(site_input),"project":copy.deepcopy(project_profile),"procedure":copy.deepcopy(procedure_profile)}
    if historical_snapshot is not None:inp["historical"]=copy.deepcopy(historical_snapshot)
    return {"analysis":{"status":status,"engine":"RULE_EVALUATION_PIPELINE","engine_version":engine.get("pipeline",{}).get("version")},"site":site,"input":inp,"land_area":land,"regulation":regulation,"rule_evaluation":summary,"input_requirements":req,"external_dependencies":ext,"rule_engine":{"baseline":engine.get("baseline"),"branch_overlay":engine.get("branch_overlay"),"dynamic_injection":engine.get("dynamic_injection"),"site_registry":engine.get("site_registry"),"site_repairs":engine.get("site_repairs"),"numeric":engine.get("numeric")}}
