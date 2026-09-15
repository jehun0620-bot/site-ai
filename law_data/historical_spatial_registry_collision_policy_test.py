import copy
from law_data.historical_spatial_registry_collision_policy import evaluate_historical_spatial_registry_collision_policy
from law_data.historical_site_event_builder_injection_payload import PROVENANCE
CLASSIFICATION = "STEP63_HISTORICAL_SPATIAL_REGISTRY_COLLISION_POLICY_BOUNDARY_RECONCILED"

def _h(state="TRUE"):
    return {"역사조건": {"state": state, "confidence": "HIGH", "source": PROVENANCE}}

def main():
    spatial = {"공간조건": {"state": "FALSE", "confidence": "HIGH", "source": "RUNTIME_SPATIAL_CONDITION"}}
    s0, h0 = copy.deepcopy(spatial), copy.deepcopy(_h())
    clean = evaluate_historical_spatial_registry_collision_policy(spatial, _h())
    assert clean.merge_candidate_ready and set(clean.merged_registry_candidate) == {"공간조건", "역사조건"}
    same = {"공유조건": {"state": "TRUE", "confidence": "HIGH", "source": PROVENANCE}}
    compatible = evaluate_historical_spatial_registry_collision_policy(same, copy.deepcopy(same))
    assert compatible.merge_candidate_ready and compatible.compatible_duplicate_names == ("공유조건",)
    conflict_spatial = {"공유조건": {"state": "FALSE", "confidence": "HIGH", "source": "RUNTIME_SPATIAL_CONDITION"}}
    conflict_historical = {"공유조건": {"state": "TRUE", "confidence": "HIGH", "source": PROVENANCE}}
    conflict = evaluate_historical_spatial_registry_collision_policy(conflict_spatial, conflict_historical)
    assert not conflict.merge_candidate_ready and conflict.conflicting_collision_names == ("공유조건",) and conflict.merged_registry_candidate == {}
    bad_historical = {"역사조건": {"state": "TRUE", "confidence": "HIGH", "source": "RUNTIME_SPATIAL_CONDITION"}}
    assert not evaluate_historical_spatial_registry_collision_policy(spatial, bad_historical).merge_candidate_ready
    assert spatial == s0 and _h() == h0
    d = clean.to_dict()
    for key in ("implicit_precedence_used", "spatial_overlay_modified", "apply_site_registry_called", "rule_engine_modified", "production_wiring_applied", "runtime_registered", "public_api_exposed"):
        assert d[key] is False
    print("=" * 72); print("STEP 63 HISTORICAL / SPATIAL REGISTRY COLLISION POLICY"); print("=" * 72)
    print("No-collision merge candidate: PASS"); print("Exact compatible duplicate handling: PASS"); print("Conflicting collision fail-closed: PASS"); print("Historical provenance guard: PASS"); print("Caller registry immutability: PASS"); print("Implicit precedence / Rule Engine mutation / runtime / API: NONE"); print(f"CLASSIFICATION: {CLASSIFICATION}")

if __name__ == "__main__": main()
