"""STEP52 read-only Rule Engine consumption preview for historical registry.

Computes the exact condition repairs that apply_site_registry() would consider,
without mutating rules, calling apply_site_registry/refresh_rule, or evaluating.
"""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping, Sequence
from law_data.historical_site_event_site_registry_mutation_executor import (
    BOUNDARY_NAME as EXECUTOR_BOUNDARY_NAME,
    HistoricalSiteEventSiteRegistryMutationExecution,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import HISTORICAL_CONDITION_TYPE, HISTORICAL_REGISTRY_SOURCE

BOUNDARY_NAME="HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PREVIEW"
VALID_STATES=frozenset({"TRUE","FALSE","UNKNOWN"})

@dataclass(frozen=True)
class HistoricalSiteEventRuleEngineConsumptionPreview:
    boundary: str
    execution_present: bool
    execution_boundary_matched: bool
    mutation_executed: bool
    site_registry_overlaid: bool
    historical_condition_name: str
    historical_condition_present: bool
    historical_type_preserved: bool
    state_valid: bool
    registry_source_matched: bool
    original_historical_source_preserved: bool
    rules_input_valid: bool
    matched_condition_count: int
    affected_rule_count: int
    expected_refresh_rule_count: int
    repairs: tuple[Mapping[str,Any], ...]
    missing_gates: tuple[str,...]
    rule_engine_consumption_preview_ready: bool
    def to_dict(self):
        return {**self.__dict__,"repairs":copy.deepcopy(list(self.repairs)),"missing_gates":list(self.missing_gates),"rules_mutated":False,"apply_site_registry_called":False,"refresh_rule_called":False,"rule_engine_state_mutated":False,"rule_evaluation_executed":False,"rule_applicability_recalculated":False,"rule_applicability_changed":False,"site_analysis_builder_modified":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}

def preview_historical_site_event_rule_engine_consumption(execution: HistoricalSiteEventSiteRegistryMutationExecution|None, rules: Sequence[Mapping[str,Any]]|None):
    present=isinstance(execution,HistoricalSiteEventSiteRegistryMutationExecution)
    boundary=bool(present and execution.boundary==EXECUTOR_BOUNDARY_NAME)
    executed=bool(present and execution.mutation_executed is True)
    overlaid=bool(present and execution.site_registry_overlaid is True)
    name=str(execution.committed_historical_condition_name or "").strip() if present else ""
    historical=copy.deepcopy(dict(execution.committed_historical_condition)) if present else {}
    hp=bool(name and historical)
    ht=str(historical.get("type") or "").strip()==HISTORICAL_CONDITION_TYPE
    sv=str(historical.get("state") or "").strip().upper() in VALID_STATES
    rs=str(historical.get("source") or "").strip()==HISTORICAL_REGISTRY_SOURCE
    hs=historical.get("historical_source"); rts=historical.get("runtime_source")
    provenance=bool(str(hs or "").strip() and hs==rts)
    rules_valid=isinstance(rules,(list,tuple)) and all(isinstance(r,Mapping) for r in rules)
    repairs=[]; affected=set(); matched=0
    if rules_valid and hp:
        for idx,rule in enumerate(rules):
            conditions=rule.get("conditions",[])
            if not isinstance(conditions,list): continue
            for condition in conditions:
                if not isinstance(condition,Mapping) or str(condition.get("name") or "").strip()!=name: continue
                matched+=1
                before={k:condition.get(k) for k in ("state","confidence","source")}
                after={k:historical.get(k) for k in ("state","confidence","source")}
                changed=before!=after
                repairs.append({"rule_index":idx,"clause_index":rule.get("clause_index"),"condition":name,"before":before,"after":after,"would_change":changed})
                if changed: affected.add(idx)
    gates=(("execution_present",present),("execution_boundary_matched",boundary),("mutation_executed",executed),("site_registry_overlaid",overlaid),("historical_condition_present",hp),("historical_type_preserved",ht),("state_valid",sv),("registry_source_matched",rs),("original_historical_source_preserved",provenance),("rules_input_valid",rules_valid))
    missing=tuple(g for g,p in gates if not p)
    ready=not missing
    return HistoricalSiteEventRuleEngineConsumptionPreview(BOUNDARY_NAME,present,boundary,executed,overlaid,name,hp,ht,sv,rs,provenance,rules_valid,matched,len(affected),len(affected),tuple(repairs),missing,ready)
