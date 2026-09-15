from dataclasses import replace
from law_data.historical_site_event_rule_engine_consumption_preview import HistoricalSiteEventRuleEngineConsumptionPreview
from law_data.historical_site_event_rule_engine_consumption_preview_authorization import authorize_historical_site_event_rule_engine_consumption_preview
CLASSIFICATION="STEP53_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PREVIEW_AUTHORIZATION_BOUNDARY_RECONCILED"
def _preview(matched=1,changed=True):
    repairs=() if matched==0 else ({"rule_index":0,"clause_index":1,"condition":"역사조건","before":{"state":"UNKNOWN","confidence":"LOW","source":"BASE"},"after":{"state":"TRUE","confidence":"HIGH","source":"RUNTIME_HISTORICAL_SITE_EVENT"},"would_change":changed},)
    affected=1 if matched and changed else 0
    return HistoricalSiteEventRuleEngineConsumptionPreview("HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PREVIEW",True,True,True,True,"역사조건",True,True,True,True,True,True,matched,affected,affected,repairs,(),True)
def main():
    a=authorize_historical_site_event_rule_engine_consumption_preview(_preview()); assert a.rule_engine_consumption_authorized and a.affected_rule_count==1 and len(a.authorized_repairs)==1
    n=authorize_historical_site_event_rule_engine_consumption_preview(_preview(0)); assert n.rule_engine_consumption_authorized and n.no_op_consumption
    p=_preview(); assert not authorize_historical_site_event_rule_engine_consumption_preview(replace(p,rule_engine_consumption_preview_ready=False)).rule_engine_consumption_authorized
    assert not authorize_historical_site_event_rule_engine_consumption_preview(replace(p,expected_refresh_rule_count=2)).rule_engine_consumption_authorized
    bad=replace(p,repairs=({**p.repairs[0],"would_change":False},)); assert not authorize_historical_site_event_rule_engine_consumption_preview(bad).rule_engine_consumption_authorized
    assert not authorize_historical_site_event_rule_engine_consumption_preview(None).rule_engine_consumption_authorized
    for x in (a,n):
        d=x.to_dict()
        for k in ("rules_mutated","apply_site_registry_called","refresh_rule_called","rule_engine_state_mutated","rule_evaluation_executed","rule_applicability_recalculated","rule_applicability_changed","site_analysis_builder_modified","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 53 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION PREVIEW AUTHORIZATION"); print("="*72); print("Changed-target consumption authorization: PASS"); print("Zero-match explicit no-op authorization: PASS"); print("Repair / affected / refresh alignment guards: PASS"); print("Tampered preview fail-closed: PASS"); print("Authorization != Rule Engine consumption: PASS"); print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE"); print("Builder / production wiring / runtime registration / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
