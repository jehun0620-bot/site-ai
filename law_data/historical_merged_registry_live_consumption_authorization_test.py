from dataclasses import replace
from law_data.historical_spatial_registry_collision_policy import evaluate_historical_spatial_registry_collision_policy
from law_data.historical_merged_registry_live_consumption_authorization import authorize_historical_merged_registry_live_consumption
CLASSIFICATION = "STEP64_HISTORICAL_MERGED_REGISTRY_LIVE_CONSUMPTION_AUTHORIZATION_BOUNDARY_RECONCILED"

def _policy():
    spatial = {"공간조건": {"state": "TRUE", "confidence": "HIGH", "source": "RUNTIME_SPATIAL_CONDITION"}}
    historical = {"역사조건": {"state": "UNKNOWN", "confidence": "MEDIUM", "source": "RUNTIME_HISTORICAL_SITE_EVENT"}}
    return evaluate_historical_spatial_registry_collision_policy(spatial, historical)

def main():
    policy = _policy()
    auth = authorize_historical_merged_registry_live_consumption(policy)
    assert auth.live_consumption_authorized
    assert auth.authorized_merged_registry["역사조건"]["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
    assert authorize_historical_merged_registry_live_consumption(evaluate_historical_spatial_registry_collision_policy({}, {})).live_consumption_authorized
    assert not authorize_historical_merged_registry_live_consumption(replace(policy, merge_candidate_ready=False)).live_consumption_authorized
    assert not authorize_historical_merged_registry_live_consumption(replace(policy, conflicting_collision_names=("충돌",))).live_consumption_authorized
    bad = dict(policy.merged_registry_candidate); bad["역사조건"] = {"state": "UNKNOWN", "confidence": "MEDIUM", "source": "RUNTIME_HISTORICAL_SITE_EVENT_TAMPERED"}
    assert not authorize_historical_merged_registry_live_consumption(replace(policy, merged_registry_candidate=bad)).live_consumption_authorized
    snapshot = policy.to_dict(); authorize_historical_merged_registry_live_consumption(policy); assert policy.to_dict() == snapshot
    d = auth.to_dict()
    for key in ("apply_site_registry_called", "rule_engine_modified", "builder_modified", "production_wiring_applied", "runtime_registered", "public_api_exposed"):
        assert d[key] is False
    print("=" * 72)
    print("STEP 64 HISTORICAL MERGED REGISTRY LIVE CONSUMPTION AUTHORIZATION")
    print("=" * 72)
    print("Valid merge-candidate authorization: PASS")
    print("Zero-op merge-candidate authorization: PASS")
    print("Conflict / readiness fail-closed: PASS")
    print("Historical provenance preservation guard: PASS")
    print("Caller policy immutability: PASS")
    print("apply_site_registry / Rule Engine mutation / runtime / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")

if __name__ == "__main__":
    main()
