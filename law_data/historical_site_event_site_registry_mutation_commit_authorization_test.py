from dataclasses import replace
from law_data.historical_site_event_overlay_application_authorization import authorize_historical_site_event_overlay_application
from law_data.historical_site_event_overlay_execution_package import package_historical_site_event_overlay_execution
from law_data.historical_site_event_provenance_preserving_overlay_contract import build_historical_site_event_provenance_preserving_overlay_contract
from law_data.historical_site_event_site_registry_overlay_preview import preview_historical_site_event_site_registry_overlay
from law_data.historical_site_event_site_registry_replacement_policy_authorization import authorize_historical_site_event_site_registry_replacement_policy
from law_data.historical_site_event_site_registry_mutation_transaction import prepare_historical_site_event_site_registry_mutation_transaction
from law_data.historical_site_event_site_registry_mutation_commit_authorization import authorize_historical_site_event_site_registry_mutation_commit

CLASSIFICATION = "STEP50_HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_COMMIT_AUTHORIZATION_BOUNDARY_RECONCILED"

def _transaction(state="TRUE"):
    contract = build_historical_site_event_provenance_preserving_overlay_contract("테스트 역사조건", {"type":"SITE_HISTORY","state":state,"confidence":"HIGH","source":"STEP50_TEST_HISTORICAL_SOURCE"})
    a45 = authorize_historical_site_event_overlay_application(contract)
    package = package_historical_site_event_overlay_execution("테스트 역사조건", a45)
    preview = preview_historical_site_event_site_registry_overlay({"기존 공간조건":{"type":"SITE_SPATIAL","state":"TRUE","confidence":"HIGH","source":"RUNTIME_SPATIAL_CONDITION"}}, package)
    a48 = authorize_historical_site_event_site_registry_replacement_policy(preview)
    return prepare_historical_site_event_site_registry_mutation_transaction(a48)

def main():
    results=[]
    for state in ("TRUE","FALSE","UNKNOWN"):
        auth=authorize_historical_site_event_site_registry_mutation_commit(_transaction(state))
        assert auth.mutation_commit_authorized is True
        assert auth.authorized_historical_condition["state"] == state
        assert auth.transaction_snapshot_aligned is True
        results.append(auth)

    tx=_transaction()
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, mutation_transaction_ready=False)).mutation_commit_authorized is False
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, mutation_target="OTHER_TARGET")).mutation_commit_authorized is False
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, boundary="OTHER_BOUNDARY")).mutation_commit_authorized is False
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, historical_condition_count=2)).mutation_commit_authorized is False
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, no_collision_policy_satisfied=False)).mutation_commit_authorized is False
    bad_snapshot=dict(tx.transaction_registry_snapshot); bad_snapshot[tx.historical_condition_name]=dict(tx.transaction_historical_condition); bad_snapshot[tx.historical_condition_name]["state"]="FALSE"
    assert authorize_historical_site_event_site_registry_mutation_commit(replace(tx, transaction_registry_snapshot=bad_snapshot)).mutation_commit_authorized is False
    assert authorize_historical_site_event_site_registry_mutation_commit(None).mutation_commit_authorized is False

    cases=results+[authorize_historical_site_event_site_registry_mutation_commit(None)]
    for result in cases:
        d=result.to_dict()
        for key in ("mutation_executed","original_registry_mutated","site_registry_overlaid","apply_site_registry_called","refresh_rule_called","rule_engine_state_mutated","rule_evaluation_executed","rule_applicability_recalculated","rule_applicability_changed","site_analysis_builder_modified","production_wiring_applied","runtime_registered","runtime_registry_mutated","public_api_exposed"):
            assert d[key] is False

    print("="*72)
    print("STEP 50 HISTORICAL SITE EVENT SITE REGISTRY MUTATION COMMIT AUTHORIZATION")
    print("="*72)
    print("Historical TRUE mutation commit authorization: PASS")
    print("Historical FALSE mutation commit authorization: PASS")
    print("Historical UNKNOWN mutation commit authorization: PASS")
    print("Exact transaction / target / no-collision binding: PASS")
    print("Snapshot / historical provenance alignment guards: PASS")
    print("Commit authorized != registry mutation: PASS")
    print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")

if __name__ == "__main__": main()
