from dataclasses import replace
from law_data.historical_site_event_builder_consumption_authorization import authorize_historical_site_event_builder_consumption
from law_data.historical_site_event_builder_input_adapter import adapt_historical_site_event_builder_input
from law_data.historical_site_event_builder_injection_payload_test import _authorization
from law_data.historical_site_event_builder_injection_payload import build_historical_site_event_builder_injection_payload
CLASSIFICATION="STEP59_HISTORICAL_SITE_EVENT_BUILDER_CONSUMPTION_AUTHORIZATION_BOUNDARY_RECONCILED"
def _input(noop=False): return adapt_historical_site_event_builder_input(build_historical_site_event_builder_injection_payload(_authorization(noop)))
def main():
    a=authorize_historical_site_event_builder_consumption(_input()); assert a.builder_consumption_authorized and a.rules_valid and a.repairs_valid
    n=authorize_historical_site_event_builder_consumption(_input(True)); assert n.builder_consumption_authorized and n.authorized_historical_rule_input["rules"]==[] and n.authorized_historical_rule_input["repairs"]==[]
    i=_input(); assert not authorize_historical_site_event_builder_consumption(replace(i,builder_input_ready=False)).builder_consumption_authorized
    bad=dict(i.historical_rule_input); bad["channel"]="SPATIAL"; assert not authorize_historical_site_event_builder_consumption(replace(i,historical_rule_input=bad)).builder_consumption_authorized
    bad=dict(i.historical_rule_input); bad["repairs"]=[{**bad["repairs"][0],"new_source":"RUNTIME_SPATIAL_CONDITION"}]; assert not authorize_historical_site_event_builder_consumption(replace(i,historical_rule_input=bad)).builder_consumption_authorized
    d=a.to_dict()
    for k in ("site_analysis_builder_modified","builder_signature_changed","site_condition_context_merged","runtime_conditions_merged","evaluate_site_rules_injected","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 59 HISTORICAL SITE EVENT BUILDER CONSUMPTION AUTHORIZATION"); print("="*72); print("Changed-target builder consumption authorization: PASS"); print("Zero-op builder consumption authorization: PASS"); print("Non-spatial channel / historical provenance guards: PASS"); print("Rules / repairs structural integrity: PASS"); print("Tampered input fail-closed: PASS"); print("Authorization != builder consumption: PASS"); print("Builder signature / live injection / production wiring / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
