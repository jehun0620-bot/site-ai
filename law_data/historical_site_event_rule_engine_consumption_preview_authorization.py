"""STEP53 non-executing authorization of a STEP52 Rule Engine consumption preview."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_rule_engine_consumption_preview import BOUNDARY_NAME as PREVIEW_BOUNDARY_NAME, HistoricalSiteEventRuleEngineConsumptionPreview
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PREVIEW_AUTHORIZATION"
@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineConsumptionPreviewAuthorization:
    boundary:str; preview_present:bool; preview_boundary_matched:bool; preview_ready:bool; historical_condition_name:str; historical_condition_name_present:bool; repair_count:int; matched_condition_count:int; affected_rule_count:int; expected_refresh_rule_count:int; repair_count_matched:bool; affected_refresh_counts_aligned:bool; repair_contract_aligned:bool; no_op_consumption:bool; missing_gates:tuple[str,...]; rule_engine_consumption_authorized:bool; authorized_repairs:tuple[Mapping[str,Any],...]
    def to_dict(self):
        return {**self.__dict__,"missing_gates":list(self.missing_gates),"authorized_repairs":copy.deepcopy(list(self.authorized_repairs)),"rules_mutated":False,"apply_site_registry_called":False,"refresh_rule_called":False,"rule_engine_state_mutated":False,"rule_evaluation_executed":False,"rule_applicability_recalculated":False,"rule_applicability_changed":False,"site_analysis_builder_modified":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def authorize_historical_site_event_rule_engine_consumption_preview(preview:HistoricalSiteEventRuleEngineConsumptionPreview|None):
    present=isinstance(preview,HistoricalSiteEventRuleEngineConsumptionPreview); boundary=bool(present and preview.boundary==PREVIEW_BOUNDARY_NAME); ready=bool(present and preview.rule_engine_consumption_preview_ready is True); name=str(preview.historical_condition_name or "").strip() if present else ""; repairs=copy.deepcopy(tuple(preview.repairs)) if present else (); repair_count=len(repairs); matched=preview.matched_condition_count if present else 0; affected=preview.affected_rule_count if present else 0; refresh=preview.expected_refresh_rule_count if present else 0; count_match=repair_count==matched; affected_match=affected==refresh; valid=True; changed=set()
    for r in repairs:
        if not isinstance(r,Mapping) or r.get("condition")!=name or not isinstance(r.get("rule_index"),int) or not isinstance(r.get("before"),Mapping) or not isinstance(r.get("after"),Mapping) or not isinstance(r.get("would_change"),bool): valid=False; break
        if set(r["before"].keys())!={"state","confidence","source"} or set(r["after"].keys())!={"state","confidence","source"}: valid=False; break
        if r["would_change"]!=(dict(r["before"])!=dict(r["after"])): valid=False; break
        if r["would_change"]: changed.add(r["rule_index"])
    contract=valid and len(changed)==affected; noop=bool(ready and matched==0 and affected==0 and refresh==0 and repair_count==0); gates=(("preview_present",present),("preview_boundary_matched",boundary),("preview_ready",ready),("historical_condition_name_present",bool(name)),("repair_count_matched",count_match),("affected_refresh_counts_aligned",affected_match),("repair_contract_aligned",contract)); missing=tuple(g for g,p in gates if not p); authorized=not missing
    return HistoricalSiteEventRuleEngineConsumptionPreviewAuthorization(BOUNDARY_NAME,present,boundary,ready,name,bool(name),repair_count,matched,affected,refresh,count_match,affected_match,contract,noop,missing,authorized,(repairs if authorized else ()))
