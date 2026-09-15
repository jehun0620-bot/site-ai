"""STEP58 adapter for a dedicated historical builder input; no builder consumption."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_builder_injection_payload import BOUNDARY_NAME as PAYLOAD_BOUNDARY_NAME, CHANNEL, PROVENANCE, HistoricalSiteEventBuilderInjectionPayload
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_BUILDER_INPUT_ADAPTER"
@dataclass(frozen=True)
class HistoricalSiteEventBuilderInput:
    boundary:str; payload_present:bool; payload_boundary_matched:bool; payload_ready:bool; channel_matched:bool; provenance_matched:bool; repairs_aligned:bool; missing_gates:tuple[str,...]; builder_input_ready:bool; historical_rule_input:Mapping[str,Any]
    def to_dict(self): return {**self.__dict__,"missing_gates":list(self.missing_gates),"historical_rule_input":copy.deepcopy(dict(self.historical_rule_input)),"site_analysis_builder_modified":False,"site_condition_context_merged":False,"runtime_conditions_merged":False,"spatial_shadow_merged":False,"evaluate_site_rules_injected":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def adapt_historical_site_event_builder_input(payload:HistoricalSiteEventBuilderInjectionPayload|None):
    pp=isinstance(payload,HistoricalSiteEventBuilderInjectionPayload); pb=bool(pp and payload.boundary==PAYLOAD_BOUNDARY_NAME); pr=bool(pp and payload.builder_injection_payload_ready is True); cm=bool(pp and payload.channel==CHANNEL); pm=bool(pp and payload.provenance==PROVENANCE); ra=bool(pp and len(payload.historical_repairs)==sum(1 for r in payload.historical_repairs if isinstance(r,Mapping)))
    gates=(("payload_present",pp),("payload_boundary_matched",pb),("payload_ready",pr),("channel_matched",cm),("provenance_matched",pm),("repairs_aligned",ra)); missing=tuple(g for g,p in gates if not p); ready=not missing
    value={"channel":CHANNEL,"provenance":PROVENANCE,"rules":copy.deepcopy(list(payload.historical_rules)),"repairs":copy.deepcopy(list(payload.historical_repairs))} if ready else {}
    return HistoricalSiteEventBuilderInput(BOUNDARY_NAME,pp,pb,pr,cm,pm,ra,missing,ready,value)
