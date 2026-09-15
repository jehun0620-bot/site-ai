"""STEP59 authorization for future builder consumption of dedicated historical input."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_builder_input_adapter import BOUNDARY_NAME as INPUT_BOUNDARY_NAME, HistoricalSiteEventBuilderInput
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_BUILDER_CONSUMPTION_AUTHORIZATION"
@dataclass(frozen=True)
class HistoricalSiteEventBuilderConsumptionAuthorization:
    boundary:str; input_present:bool; input_boundary_matched:bool; builder_input_ready:bool; channel_matched:bool; provenance_matched:bool; rules_valid:bool; repairs_valid:bool; missing_gates:tuple[str,...]; builder_consumption_authorized:bool; authorized_historical_rule_input:Mapping[str,Any]
    def to_dict(self): return {**self.__dict__,"missing_gates":list(self.missing_gates),"authorized_historical_rule_input":copy.deepcopy(dict(self.authorized_historical_rule_input)),"site_analysis_builder_modified":False,"builder_signature_changed":False,"site_condition_context_merged":False,"runtime_conditions_merged":False,"evaluate_site_rules_injected":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def authorize_historical_site_event_builder_consumption(builder_input:HistoricalSiteEventBuilderInput|None):
    ip=isinstance(builder_input,HistoricalSiteEventBuilderInput); ib=bool(ip and builder_input.boundary==INPUT_BOUNDARY_NAME); ready=bool(ip and builder_input.builder_input_ready is True); value=copy.deepcopy(dict(builder_input.historical_rule_input)) if ip else {}; cm=bool(value.get("channel")==CHANNEL); pm=bool(value.get("provenance")==PROVENANCE); rules=value.get("rules"); repairs=value.get("repairs"); rv=isinstance(rules,list) and all(isinstance(r,Mapping) for r in rules); pv=isinstance(repairs,list) and all(isinstance(r,Mapping) for r in repairs) and all(r.get("new_source")==PROVENANCE for r in repairs)
    gates=(("input_present",ip),("input_boundary_matched",ib),("builder_input_ready",ready),("channel_matched",cm),("provenance_matched",pm),("rules_valid",rv),("repairs_valid",pv)); missing=tuple(g for g,p in gates if not p); authorized=not missing
    return HistoricalSiteEventBuilderConsumptionAuthorization(BOUNDARY_NAME,ip,ib,ready,cm,pm,rv,pv,missing,authorized,(value if authorized else {}))
