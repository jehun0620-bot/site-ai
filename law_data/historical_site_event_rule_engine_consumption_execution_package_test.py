from dataclasses import replace
from law_data.historical_site_event_rule_engine_consumption_preview_authorization_test import _preview
from law_data.historical_site_event_rule_engine_consumption_preview_authorization import authorize_historical_site_event_rule_engine_consumption_preview
from law_data.historical_site_event_rule_engine_consumption_execution_package import package_historical_site_event_rule_engine_consumption_execution
from law_data.historical_site_event_site_registry_mutation_executor import HistoricalSiteEventSiteRegistryMutationExecution
CLASSIFICATION="STEP54_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_EXECUTION_PACKAGE_BOUNDARY_RECONCILED"
def _execution():
    c={"type":"SITE_HISTORY","state":"TRUE","confidence":"HIGH","source":"RUNTIME_HISTORICAL_SITE_EVENT","historical_source":"SRC","runtime_source":"SRC"}; return HistoricalSiteEventSiteRegistryMutationExecution("HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_EXECUTOR","RULE_ENGINE_SITE_REGISTRY_HISTORICAL_OVERLAY",True,True,True,True,True,True,True,True,True,True,True,True,True,(),True,True,{"역사조건":c},"역사조건",c)
def main():
    e=_execution(); a=authorize_historical_site_event_rule_engine_consumption_preview(_preview()); p=package_historical_site_event_rule_engine_consumption_execution(a,e); assert p.rule_engine_consumption_execution_package_ready and p.execution_mode=="CHANGED_TARGETS" and p.affected_rule_indexes==(0,) and p.expected_refresh_rule_count==1
    n=package_historical_site_event_rule_engine_consumption_execution(authorize_historical_site_event_rule_engine_consumption_preview(_preview(0)),e); assert n.rule_engine_consumption_execution_package_ready and n.execution_mode=="NO_OP" and not n.packaged_repairs
    assert not package_historical_site_event_rule_engine_consumption_execution(replace(a,rule_engine_consumption_authorized=False),e).rule_engine_consumption_execution_package_ready
    assert not package_historical_site_event_rule_engine_consumption_execution(a,replace(e,committed_historical_condition_name="OTHER")).rule_engine_consumption_execution_package_ready
    assert not package_historical_site_event_rule_engine_consumption_execution(a,None).rule_engine_consumption_execution_package_ready
    for x in (p,n):
        d=x.to_dict()
        for k in ("apply_site_registry_called","refresh_rule_called","rules_mutated","rule_engine_state_mutated","rule_evaluation_executed","rule_applicability_recalculated","rule_applicability_changed","site_analysis_builder_modified","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 54 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION EXECUTION PACKAGE"); print("="*72); print("Changed-target execution package: PASS"); print("Zero-op execution package: PASS"); print("STEP53 authorization / STEP51 registry identity binding: PASS"); print("Exact affected rule / expected refresh package: PASS"); print("Execution package ready != Rule Engine consumption: PASS"); print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE"); print("Builder / production wiring / runtime registration / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
