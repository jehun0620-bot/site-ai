from dataclasses import replace
from law_data.historical_site_event_builder_injection_payload import build_historical_site_event_builder_injection_payload, CHANNEL, PROVENANCE
from law_data.historical_site_event_production_integration_authorization import authorize_historical_site_event_production_integration
from law_data.historical_site_event_rule_engine_consumption_executor import execute_historical_site_event_rule_engine_consumption
from law_data.historical_site_event_rule_engine_consumption_executor_test import _package
CLASSIFICATION="STEP57_HISTORICAL_SITE_EVENT_BUILDER_INJECTION_PAYLOAD_BOUNDARY_RECONCILED"
def _authorization(noop=False):
    rules=[] if noop else [{"clause_index":1,"conditions":[{"name":"역사조건","type":"SITE_HISTORY","state":"UNKNOWN","confidence":"LOW","source":"BASE"}]}]
    return authorize_historical_site_event_production_integration(execute_historical_site_event_rule_engine_consumption(_package(noop),rules))
def main():
    p=build_historical_site_event_builder_injection_payload(_authorization()); assert p.builder_injection_payload_ready and p.channel==CHANNEL and p.provenance==PROVENANCE and p.historical_rules and p.historical_repairs
    n=build_historical_site_event_builder_injection_payload(_authorization(True)); assert n.builder_injection_payload_ready and n.historical_rules==() and n.historical_repairs==()
    a=_authorization(); assert not build_historical_site_event_builder_injection_payload(replace(a,production_integration_authorized=False)).builder_injection_payload_ready
    bad=replace(a,authorized_repairs=({**a.authorized_repairs[0],"new_source":"RUNTIME_SPATIAL_CONDITION"},)); assert not build_historical_site_event_builder_injection_payload(bad).builder_injection_payload_ready
    d=p.to_dict()
    for k in ("site_analysis_builder_modified","site_condition_context_merged","runtime_conditions_merged","evaluate_site_rules_injected","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 57 HISTORICAL SITE EVENT BUILDER INJECTION PAYLOAD"); print("="*72); print("Changed-target historical payload: PASS"); print("Zero-op historical payload: PASS"); print("Explicit non-spatial channel: PASS"); print("Historical provenance preservation: PASS"); print("Unauthorized/tampered input fail-closed: PASS"); print("Payload ready != builder/live injection: PASS"); print("Builder / context merge / production wiring / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
