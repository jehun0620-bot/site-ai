from dataclasses import replace
from law_data.historical_site_event_builder_input_adapter import adapt_historical_site_event_builder_input
from law_data.historical_site_event_builder_injection_payload import build_historical_site_event_builder_injection_payload, CHANNEL, PROVENANCE
from law_data.historical_site_event_builder_injection_payload_test import _authorization
CLASSIFICATION="STEP58_HISTORICAL_SITE_EVENT_BUILDER_INPUT_ADAPTER_BOUNDARY_RECONCILED"
def main():
    payload=build_historical_site_event_builder_injection_payload(_authorization()); a=adapt_historical_site_event_builder_input(payload); assert a.builder_input_ready and a.historical_rule_input["channel"]==CHANNEL and a.historical_rule_input["provenance"]==PROVENANCE and a.historical_rule_input["rules"] and a.historical_rule_input["repairs"]
    noop=adapt_historical_site_event_builder_input(build_historical_site_event_builder_injection_payload(_authorization(True))); assert noop.builder_input_ready and noop.historical_rule_input["rules"]==[] and noop.historical_rule_input["repairs"]==[]
    assert not adapt_historical_site_event_builder_input(replace(payload,builder_injection_payload_ready=False)).builder_input_ready
    assert not adapt_historical_site_event_builder_input(replace(payload,channel="SPATIAL")).builder_input_ready
    assert not adapt_historical_site_event_builder_input(replace(payload,provenance="RUNTIME_SPATIAL_CONDITION")).builder_input_ready
    d=a.to_dict()
    for k in ("site_analysis_builder_modified","site_condition_context_merged","runtime_conditions_merged","spatial_shadow_merged","evaluate_site_rules_injected","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 58 HISTORICAL SITE EVENT BUILDER INPUT ADAPTER"); print("="*72); print("Changed-target dedicated historical input: PASS"); print("Zero-op dedicated historical input: PASS"); print("Non-spatial channel / historical provenance guards: PASS"); print("Tampered payload fail-closed: PASS"); print("Builder input ready != builder consumption: PASS"); print("Spatial context / runtime_conditions / shadow merge: NONE"); print("Builder / Rule Engine injection / production wiring / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
