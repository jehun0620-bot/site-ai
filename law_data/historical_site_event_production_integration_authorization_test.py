from dataclasses import replace
from law_data.historical_site_event_production_integration_authorization import authorize_historical_site_event_production_integration
from law_data.historical_site_event_rule_engine_consumption_executor import execute_historical_site_event_rule_engine_consumption
from law_data.historical_site_event_rule_engine_consumption_executor_test import _package
CLASSIFICATION="STEP56_HISTORICAL_SITE_EVENT_PRODUCTION_INTEGRATION_AUTHORIZATION_BOUNDARY_RECONCILED"
def main():
    rules=[{"clause_index":1,"conditions":[{"name":"역사조건","type":"SITE_HISTORY","state":"UNKNOWN","confidence":"LOW","source":"BASE"}]}]
    execution=execute_historical_site_event_rule_engine_consumption(_package(False),rules); auth=authorize_historical_site_event_production_integration(execution); assert auth.production_integration_authorized and auth.historical_provenance_preserved and auth.changed_rule_indexes_aligned
    noop=authorize_historical_site_event_production_integration(execute_historical_site_event_rule_engine_consumption(_package(True),[])); assert noop.production_integration_authorized and not noop.authorized_repairs
    assert not authorize_historical_site_event_production_integration(replace(execution,execution_succeeded=False)).production_integration_authorized
    assert not authorize_historical_site_event_production_integration(replace(execution,actual_repairs_aligned=False)).production_integration_authorized
    bad=replace(execution,actual_repairs=({**execution.actual_repairs[0],"new_source":"RUNTIME_SPATIAL_CONDITION"},)); assert not authorize_historical_site_event_production_integration(bad).production_integration_authorized
    d=auth.to_dict(); assert d["site_analysis_builder_modified"] is False and d["production_wiring_applied"] is False and d["rule_engine_live_state_mutated"] is False and d["runtime_registered"] is False and d["public_api_exposed"] is False
    print("="*72); print("STEP 56 HISTORICAL SITE EVENT PRODUCTION INTEGRATION AUTHORIZATION"); print("="*72); print("Changed-target integration authorization: PASS"); print("Zero-op integration authorization: PASS"); print("Historical provenance preservation guard: PASS"); print("Repair / refresh target alignment guard: PASS"); print("Failed/tampered execution fail-closed: PASS"); print("Authorization != production/live integration: PASS"); print("Builder / production wiring / live Rule Engine / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
