"""STEP56 non-wiring authorization for future historical production integration."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_rule_engine_consumption_executor import BOUNDARY_NAME as EXECUTION_BOUNDARY_NAME, HistoricalSiteEventRuleEngineConsumptionExecution
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_PRODUCTION_INTEGRATION_AUTHORIZATION"
@dataclass(frozen=True)
class HistoricalSiteEventProductionIntegrationAuthorization:
    boundary:str; execution_present:bool; execution_boundary_matched:bool; execution_succeeded:bool; actual_repairs_aligned:bool; original_rules_immutable:bool; historical_provenance_preserved:bool; execution_mode:str; actual_repair_count:int; expected_refresh_rule_count:int; changed_rule_indexes_aligned:bool; missing_gates:tuple[str,...]; production_integration_authorized:bool; authorized_rules:tuple[Mapping[str,Any],...]; authorized_repairs:tuple[Mapping[str,Any],...]
    def to_dict(self): return {**self.__dict__,"missing_gates":list(self.missing_gates),"authorized_rules":copy.deepcopy(list(self.authorized_rules)),"authorized_repairs":copy.deepcopy(list(self.authorized_repairs)),"site_analysis_builder_modified":False,"production_wiring_applied":False,"rule_engine_live_state_mutated":False,"runtime_registered":False,"public_api_exposed":False}
def authorize_historical_site_event_production_integration(execution:HistoricalSiteEventRuleEngineConsumptionExecution|None):
    ep=isinstance(execution,HistoricalSiteEventRuleEngineConsumptionExecution); eb=bool(ep and execution.boundary==EXECUTION_BOUNDARY_NAME); success=bool(ep and execution.execution_succeeded is True); repairs_ok=bool(ep and execution.actual_repairs_aligned is True); immutable=bool(ep and execution.to_dict().get("input_rules_mutated") is False); indexes_ok=bool(ep and execution.actual_changed_rule_indexes==execution.authorized_changed_rule_indexes and len(execution.actual_changed_rule_indexes)==execution.expected_refresh_rule_count)
    provenance=True
    if ep:
        for repair in execution.actual_repairs:
            if not isinstance(repair,Mapping) or repair.get("new_source")!="RUNTIME_HISTORICAL_SITE_EVENT": provenance=False; break
        if execution.execution_mode=="CHANGED_TARGETS" and not execution.actual_repairs: provenance=False
        if execution.execution_mode=="NO_OP" and execution.actual_repairs: provenance=False
    gates=(("execution_present",ep),("execution_boundary_matched",eb),("execution_succeeded",success),("actual_repairs_aligned",repairs_ok),("original_rules_immutable",immutable),("historical_provenance_preserved",provenance),("changed_rule_indexes_aligned",indexes_ok)); missing=tuple(g for g,p in gates if not p); authorized=not missing
    return HistoricalSiteEventProductionIntegrationAuthorization(BOUNDARY_NAME,ep,eb,success,repairs_ok,immutable,provenance,(execution.execution_mode if ep else ""),(execution.actual_repair_count if ep else 0),(execution.expected_refresh_rule_count if ep else 0),indexes_ok,missing,authorized,(copy.deepcopy(execution.executed_rules) if authorized else ()),(copy.deepcopy(execution.actual_repairs) if authorized else ()))
