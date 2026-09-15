from dataclasses import replace
from law_data.historical_site_event_overlay_application_authorization import authorize_historical_site_event_overlay_application
from law_data.historical_site_event_overlay_execution_package import package_historical_site_event_overlay_execution
from law_data.historical_site_event_provenance_preserving_overlay_contract import build_historical_site_event_provenance_preserving_overlay_contract
from law_data.historical_site_event_site_registry_overlay_preview import preview_historical_site_event_site_registry_overlay
from law_data.historical_site_event_site_registry_replacement_policy_authorization import authorize_historical_site_event_site_registry_replacement_policy
from law_data.historical_site_event_site_registry_mutation_transaction import prepare_historical_site_event_site_registry_mutation_transaction
from law_data.historical_site_event_site_registry_mutation_commit_authorization import authorize_historical_site_event_site_registry_mutation_commit
from law_data.historical_site_event_site_registry_mutation_executor import execute_historical_site_event_site_registry_mutation

CLASSIFICATION="STEP51_HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_EXECUTOR_BOUNDARY_RECONCILED"

def _auth(state="TRUE"):
    c=build_historical_site_event_provenance_preserving_overlay_contract("테스트 역사조건",{"type":"SITE_HISTORY","state":state,"confidence":"HIGH","source":"STEP51_TEST_HISTORICAL_SOURCE"})
    a45=authorize_historical_site_event_overlay_application(c)
    p46=package_historical_site_event_overlay_execution("테스트 역사조건",a45)
    p47=preview_historical_site_event_site_registry_overlay({"기존 공간조건":{"type":"SITE_SPATIAL","state":"TRUE","confidence":"HIGH","source":"RUNTIME_SPATIAL_CONDITION"}},p46)
    a48=authorize_historical_site_event_site_registry_replacement_policy(p47)
    t49=prepare_historical_site_event_site_registry_mutation_transaction(a48)
    return authorize_historical_site_event_site_registry_mutation_commit(t49)

def main():
    executions=[]
    for state in ("TRUE","FALSE","UNKNOWN"):
        auth=_auth(state); before=auth.to_dict()
        result=execute_historical_site_event_site_registry_mutation(auth)
        assert result.mutation_executed is True and result.site_registry_overlaid is True
        assert result.committed_historical_condition["state"]==state
        assert result.committed_historical_condition["source"]=="RUNTIME_HISTORICAL_SITE_EVENT"
        assert auth.to_dict()==before
        executions.append(result)
    auth=_auth()
    assert execute_historical_site_event_site_registry_mutation(replace(auth,mutation_commit_authorized=False)).mutation_executed is False
    assert execute_historical_site_event_site_registry_mutation(replace(auth,mutation_target="OTHER_TARGET")).mutation_executed is False
    assert execute_historical_site_event_site_registry_mutation(replace(auth,boundary="OTHER_BOUNDARY")).mutation_executed is False
    bad=dict(auth.authorized_registry_snapshot); bad[auth.authorized_historical_condition_name]=dict(auth.authorized_historical_condition); bad[auth.authorized_historical_condition_name]["source"]="RUNTIME_SPATIAL_CONDITION"
    assert execute_historical_site_event_site_registry_mutation(replace(auth,authorized_registry_snapshot=bad)).mutation_executed is False
    assert execute_historical_site_event_site_registry_mutation(None).mutation_executed is False
    for result in executions+[execute_historical_site_event_site_registry_mutation(None)]:
        d=result.to_dict()
        for key in ("input_authorization_mutated","apply_site_registry_called","refresh_rule_called","rule_evaluation_pipeline_modified","site_analysis_builder_modified","rule_engine_input_consumed","rule_engine_state_mutated","rule_evaluation_executed","rule_applicability_recalculated","rule_applicability_changed","production_wiring_applied","runtime_registered","runtime_registry_mutated","public_api_exposed"):
            assert d[key] is False
    print("="*72)
    print("STEP 51 HISTORICAL SITE EVENT SITE REGISTRY MUTATION EXECUTOR")
    print("="*72)
    print("Historical TRUE registry mutation execution: PASS")
    print("Historical FALSE registry mutation execution: PASS")
    print("Historical UNKNOWN registry mutation execution: PASS")
    print("STEP50-only authorization / exact target guards: PASS")
    print("Historical provenance / snapshot alignment guards: PASS")
    print("Input authorization immutability: PASS")
    print("Registry mutation executed != Rule Engine consumption: PASS")
    print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")

if __name__=="__main__": main()
