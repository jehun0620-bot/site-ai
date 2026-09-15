"""STEP55 historical-only Rule Engine consumption executor on a deep-copy ruleset."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from law_data.historical_site_event_rule_engine_consumption_execution_package import BOUNDARY_NAME as PACKAGE_BOUNDARY_NAME, HistoricalSiteEventRuleEngineConsumptionExecutionPackage
from law_data.rule_evaluation_pipeline import apply_site_registry
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_EXECUTOR"
@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineConsumptionExecution:
    boundary:str; package_present:bool; package_boundary_matched:bool; package_ready:bool; rules_input_valid:bool; current_rules_aligned:bool; execution_mode:str; apply_site_registry_called:bool; actual_repair_count:int; expected_refresh_rule_count:int; actual_changed_rule_indexes:tuple[int,...]; authorized_changed_rule_indexes:tuple[int,...]; actual_repairs_aligned:bool; execution_succeeded:bool; missing_gates:tuple[str,...]; executed_rules:tuple[Mapping[str,Any],...]; actual_repairs:tuple[Mapping[str,Any],...]
    def to_dict(self): return {**self.__dict__,"actual_changed_rule_indexes":list(self.actual_changed_rule_indexes),"authorized_changed_rule_indexes":list(self.authorized_changed_rule_indexes),"missing_gates":list(self.missing_gates),"executed_rules":copy.deepcopy(list(self.executed_rules)),"actual_repairs":copy.deepcopy(list(self.actual_repairs)),"input_rules_mutated":False,"site_analysis_builder_modified":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def execute_historical_site_event_rule_engine_consumption(package:HistoricalSiteEventRuleEngineConsumptionExecutionPackage|None,rules:Sequence[Mapping[str,Any]]|None):
    pp=isinstance(package,HistoricalSiteEventRuleEngineConsumptionExecutionPackage); pb=bool(pp and package.boundary==PACKAGE_BOUNDARY_NAME); pr=bool(pp and package.rule_engine_consumption_execution_package_ready is True); rv=isinstance(rules,(list,tuple)) and all(isinstance(r,Mapping) for r in rules); working=copy.deepcopy(list(rules)) if rv else []; repairs=tuple(package.packaged_repairs) if pp else (); name=str(package.packaged_historical_condition.get("name") or "") if pp else ""
    # Reconstruct the STEP52 before/after view against current rules to prevent drift.
    current=[]
    if rv and pp:
        target_name=next(iter(package.packaged_registry.keys()),"") if len(package.packaged_registry)==1 else ""
        # packaged registry may contain unrelated entries; exact historical condition is identified by repair condition or registry equality.
        target_name=repairs[0].get("condition","") if repairs else next((k for k,v in package.packaged_registry.items() if dict(v)==dict(package.packaged_historical_condition)),"")
        hist=package.packaged_historical_condition
        for i,r in enumerate(working):
            for c in r.get("conditions",[]) if isinstance(r.get("conditions",[]),list) else []:
                if isinstance(c,dict) and str(c.get("name") or "").strip()==target_name:
                    before={k:c.get(k) for k in ("state","confidence","source")}; after={k:hist.get(k) for k in ("state","confidence","source")}; current.append({"rule_index":i,"clause_index":r.get("clause_index"),"condition":target_name,"before":before,"after":after,"would_change":before!=after})
    aligned=bool(pp and tuple(current)==repairs)
    gates=(("package_present",pp),("package_boundary_matched",pb),("package_ready",pr),("rules_input_valid",rv),("current_rules_aligned",aligned)); missing=tuple(g for g,p in gates if not p)
    if missing: return HistoricalSiteEventRuleEngineConsumptionExecution(BOUNDARY_NAME,pp,pb,pr,rv,aligned,(package.execution_mode if pp else ""),False,0,(package.expected_refresh_rule_count if pp else 0),(),(package.affected_rule_indexes if pp else ()),False,False,missing,(),())
    if package.execution_mode=="NO_OP": return HistoricalSiteEventRuleEngineConsumptionExecution(BOUNDARY_NAME,pp,pb,pr,rv,aligned,"NO_OP",False,0,0,(),(),True,True,(),tuple(working),())
    actual=apply_site_registry(working,copy.deepcopy(dict(package.packaged_registry))); actual=tuple(copy.deepcopy(actual)); changed=tuple(sorted({i for i,r in enumerate(current) if r["would_change"]})); ok=len(actual)==len(repairs) and changed==package.affected_rule_indexes and len(changed)==package.expected_refresh_rule_count
    return HistoricalSiteEventRuleEngineConsumptionExecution(BOUNDARY_NAME,pp,pb,pr,rv,aligned,"CHANGED_TARGETS",True,len(actual),package.expected_refresh_rule_count,changed,package.affected_rule_indexes,ok,ok,(() if ok else ("actual_repairs_aligned",)),(tuple(working) if ok else ()),(actual if ok else ()))
