from dataclasses import replace
from law_data.historical_site_event_builder_consumption_plan import plan_historical_site_event_builder_consumption, TARGET_FUNCTION, TARGET_ARGUMENT
from law_data.historical_site_event_builder_consumption_authorization import authorize_historical_site_event_builder_consumption
from law_data.historical_site_event_builder_consumption_authorization_test import _input
CLASSIFICATION="STEP60_HISTORICAL_SITE_EVENT_BUILDER_CONSUMPTION_PLAN_BOUNDARY_RECONCILED"
def _auth(noop=False): return authorize_historical_site_event_builder_consumption(_input(noop))
def main():
    p=plan_historical_site_event_builder_consumption(_auth()); assert p.builder_consumption_planned and p.target_function==TARGET_FUNCTION and p.target_argument==TARGET_ARGUMENT and p.planned_historical_rule_input
    n=plan_historical_site_event_builder_consumption(_auth(True)); assert n.builder_consumption_planned and n.planned_historical_rule_input["rules"]==[] and n.planned_historical_rule_input["repairs"]==[]
    a=_auth(); assert not plan_historical_site_event_builder_consumption(replace(a,builder_consumption_authorized=False)).builder_consumption_planned
    bad=dict(a.authorized_historical_rule_input); bad["provenance"]="RUNTIME_SPATIAL_CONDITION"; assert not plan_historical_site_event_builder_consumption(replace(a,authorized_historical_rule_input=bad)).builder_consumption_planned
    d=p.to_dict()
    for k in ("site_analysis_builder_modified","builder_signature_changed","site_condition_context_merged","runtime_conditions_merged","spatial_shadow_merged","evaluate_site_rules_injected","plan_executed","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
    print("="*72); print("STEP 60 HISTORICAL SITE EVENT BUILDER CONSUMPTION PLAN"); print("="*72); print("Changed-target builder consumption plan: PASS"); print("Zero-op builder consumption plan: PASS"); print("Target function / dedicated argument plan: PASS"); print("Non-spatial channel / historical provenance guards: PASS"); print("Unauthorized/tampered input fail-closed: PASS"); print("Plan != builder signature/live consumption: PASS"); print("Builder / Rule Engine injection / production wiring / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
