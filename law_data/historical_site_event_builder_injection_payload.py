"""STEP57 historical-only builder injection payload; no builder wiring."""
from __future__ import annotations
import copy
from dataclasses import dataclass
from typing import Any, Mapping
from law_data.historical_site_event_production_integration_authorization import BOUNDARY_NAME as AUTH_BOUNDARY_NAME, HistoricalSiteEventProductionIntegrationAuthorization
BOUNDARY_NAME="HISTORICAL_SITE_EVENT_BUILDER_INJECTION_PAYLOAD"
CHANNEL="HISTORICAL_SITE_EVENT_NON_SPATIAL"
PROVENANCE="RUNTIME_HISTORICAL_SITE_EVENT"
@dataclass(frozen=True)
class HistoricalSiteEventBuilderInjectionPayload:
    boundary:str; authorization_present:bool; authorization_boundary_matched:bool; production_integration_authorized:bool; channel:str; provenance:str; rules_present:bool; repairs_aligned:bool; provenance_preserved:bool; missing_gates:tuple[str,...]; builder_injection_payload_ready:bool; historical_rules:tuple[Mapping[str,Any],...]; historical_repairs:tuple[Mapping[str,Any],...]
    def to_dict(self): return {**self.__dict__,"missing_gates":list(self.missing_gates),"historical_rules":copy.deepcopy(list(self.historical_rules)),"historical_repairs":copy.deepcopy(list(self.historical_repairs)),"site_analysis_builder_modified":False,"site_condition_context_merged":False,"runtime_conditions_merged":False,"evaluate_site_rules_injected":False,"production_wiring_applied":False,"runtime_registered":False,"public_api_exposed":False}
def build_historical_site_event_builder_injection_payload(authorization:HistoricalSiteEventProductionIntegrationAuthorization|None):
    ap=isinstance(authorization,HistoricalSiteEventProductionIntegrationAuthorization); ab=bool(ap and authorization.boundary==AUTH_BOUNDARY_NAME); aa=bool(ap and authorization.production_integration_authorized is True); rules=copy.deepcopy(tuple(authorization.authorized_rules)) if ap else (); repairs=copy.deepcopy(tuple(authorization.authorized_repairs)) if ap else (); rules_present=bool(ap and isinstance(authorization.authorized_rules,tuple)); repair_alignment=bool(ap and len(repairs)==authorization.actual_repair_count)
    provenance=True
    for repair in repairs:
        if not isinstance(repair,Mapping) or repair.get("new_source")!=PROVENANCE: provenance=False; break
    if ap and authorization.execution_mode=="CHANGED_TARGETS" and not repairs: provenance=False
    if ap and authorization.execution_mode=="NO_OP" and repairs: provenance=False
    gates=(("authorization_present",ap),("authorization_boundary_matched",ab),("production_integration_authorized",aa),("rules_present",rules_present),("repairs_aligned",repair_alignment),("provenance_preserved",provenance)); missing=tuple(g for g,p in gates if not p); ready=not missing
    return HistoricalSiteEventBuilderInjectionPayload(BOUNDARY_NAME,ap,ab,aa,CHANNEL,PROVENANCE,rules_present,repair_alignment,provenance,missing,ready,(rules if ready else ()),(repairs if ready else ()))
