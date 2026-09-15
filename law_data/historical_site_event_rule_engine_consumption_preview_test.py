from dataclasses import replace
from law_data.historical_site_event_overlay_application_authorization import authorize_historical_site_event_overlay_application
from law_data.historical_site_event_overlay_execution_package import package_historical_site_event_overlay_execution
from law_data.historical_site_event_provenance_preserving_overlay_contract import build_historical_site_event_provenance_preserving_overlay_contract
from law_data.historical_site_event_site_registry_overlay_preview import preview_historical_site_event_site_registry_overlay
from law_data.historical_site_event_site_registry_replacement_policy_authorization import authorize_historical_site_event_site_registry_replacement_policy
from law_data.historical_site_event_site_registry_mutation_transaction import prepare_historical_site_event_site_registry_mutation_transaction
from law_data.historical_site_event_site_registry_mutation_commit_authorization import authorize_historical_site_event_site_registry_mutation_commit
from law_data.historical_site_event_site_registry_mutation_executor import execute_historical_site_event_site_registry_mutation
from law_data.historical_site_event_rule_engine_consumption_preview import preview_historical_site_event_rule_engine_consumption
CLASSIFICATION="STEP52_HISTORICAL_SITE_EVENT_RULE_ENGINE_CONSUMPTION_PREVIEW_BOUNDARY_RECONCILED"
def _execution(state="TRUE"):
 c=build_historical_site_event_provenance_preserving_overlay_contract("역사조건",{"type":"SITE_HISTORY","state":state,"confidence":"HIGH","source":"STEP52_TEST_SOURCE"}); a=authorize_historical_site_event_overlay_application(c); p=package_historical_site_event_overlay_execution("역사조건",a); v=preview_historical_site_event_site_registry_overlay({},p); a48=authorize_historical_site_event_site_registry_replacement_policy(v); t=prepare_historical_site_event_site_registry_mutation_transaction(a48); a50=authorize_historical_site_event_site_registry_mutation_commit(t); return execute_historical_site_event_site_registry_mutation(a50)
def main():
 rules=[{"clause_index":1,"conditions":[{"name":"역사조건","type":"SITE_HISTORY","state":"FALSE","confidence":"LOW","source":"SNAPSHOT"}]},{"clause_index":2,"conditions":[{"name":"다른조건","state":"TRUE"}]},{"clause_index":3,"conditions":[{"name":"역사조건","type":"SITE_HISTORY","state":"TRUE","confidence":"HIGH","source":"RUNTIME_HISTORICAL_SITE_EVENT"}]}]
 before=repr(rules); r=preview_historical_site_event_rule_engine_consumption(_execution("TRUE"),rules)
 assert r.rule_engine_consumption_preview_ready and r.matched_condition_count==2 and r.affected_rule_count==1 and r.expected_refresh_rule_count==1
 assert len(r.repairs)==2 and sum(x["would_change"] for x in r.repairs)==1 and repr(rules)==before
 for state in ("FALSE","UNKNOWN"):
  x=preview_historical_site_event_rule_engine_consumption(_execution(state),rules); assert x.rule_engine_consumption_preview_ready and x.historical_condition_present
 bad=replace(_execution(),mutation_executed=False); assert not preview_historical_site_event_rule_engine_consumption(bad,rules).rule_engine_consumption_preview_ready
 assert not preview_historical_site_event_rule_engine_consumption(None,rules).rule_engine_consumption_preview_ready
 assert not preview_historical_site_event_rule_engine_consumption(_execution(),None).rule_engine_consumption_preview_ready
 d=r.to_dict()
 for k in ("rules_mutated","apply_site_registry_called","refresh_rule_called","rule_engine_state_mutated","rule_evaluation_executed","rule_applicability_recalculated","rule_applicability_changed","site_analysis_builder_modified","production_wiring_applied","runtime_registered","public_api_exposed"): assert d[k] is False
 print("="*72); print("STEP 52 HISTORICAL SITE EVENT RULE ENGINE CONSUMPTION PREVIEW"); print("="*72)
 print("Historical TRUE/FALSE/UNKNOWN consumption preview: PASS"); print("Matching condition / affected rule diagnostics: PASS"); print("Before/after state-confidence-source preview: PASS"); print("Expected refresh target calculation: PASS"); print("Input rules immutability: PASS"); print("Preview ready != Rule Engine consumption: PASS"); print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE"); print("Builder / production wiring / runtime registration / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")
if __name__=="__main__": main()
