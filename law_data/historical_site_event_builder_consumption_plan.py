"""STEP60 non-executing plan for future builder consumption of historical input."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_builder_consumption_authorization import BOUNDARY_NAME as AUTH_BOUNDARY_NAME, HistoricalSiteEventBuilderConsumptionAuthorization
from law_data.historical_site_event_builder_injection_payload import CHANNEL, PROVENANCE
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_BUILDER_CONSUMPTION_PLAN"
TARGET_FUNCTION="build_site_analysis"
TARGET_ARGUMENT="historical_rule_input"
@dataclass(frozen=True)
class HistoricalSiteEventBuilderConsumptionPlan:
    boundary:str; authorization_present:bool; authorization_boundary_matched:bool; builder_consumption_authorized:bool; channel_matched:bool; provenance_matched:bool; target_function:str; target_argument:str; missing_gates:tuple[str,...]; builder_consumption_planned:bool; planned_historical_rule_input:Mapping[str,Any]
    def to_dict(self): return {**self.__dict__,"missing_gates":list(self.missing_gates),"planned_historical_rule_input":copy.deepcopy(dict(self.planned_historical_rule_input)),"site_analysis_builder_modified":False,"builder_signature_changed":False,"site_condition_context_merged":False,"runtime_conditions_merged":False,"spatial_shadow_merged":False,"evaluate_site_rules_injected":False,"plan_executed":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def plan_historical_site_event_builder_consumption(authorization:HistoricalSiteEventBuilderConsumptionAuthorization|None):
    ap=isinstance(authorization,HistoricalSiteEventBuilderConsumptionAuthorization); ab=bool(ap and authorization.boundary==AUTH_BOUNDARY_NAME); aa=bool(ap and authorization.builder_consumption_authorized is True); value=copy.deepcopy(dict(authorization.authorized_historical_rule_input)) if ap else {}; cm=bool(value.get("channel")==CHANNEL); pm=bool(value.get("provenance")==PROVENANCE)
    gates=(("authorization_present",ap),("authorization_boundary_matched",ab),("builder_consumption_authorized",aa),("channel_matched",cm),("provenance_matched",pm)); missing=tuple(g for g,p in gates if not p); planned=not missing
    return HistoricalSiteEventBuilderConsumptionPlan(BOUNDARY_NAME,ap,ab,aa,cm,pm,TARGET_FUNCTION,TARGET_ARGUMENT,missing,planned,(value if planned else {}))
