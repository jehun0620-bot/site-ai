from copy import deepcopy
from law_data.historical_site_event_rule_engine_registry_adapter import adapt_historical_site_event_rule_engine_registry
from law_data.historical_site_event_builder_input_adapter import adapt_historical_site_event_builder_input
from law_data.historical_site_event_builder_injection_payload import build_historical_site_event_builder_injection_payload, PROVENANCE
from law_data.historical_site_event_builder_injection_payload_test import _authorization
CLASSIFICATION = "STEP62_HISTORICAL_SITE_EVENT_RULE_ENGINE_REGISTRY_ADAPTER_BOUNDARY_RECONCILED"

def _input(noop=False):
    return adapt_historical_site_event_builder_input(
        build_historical_site_event_builder_injection_payload(_authorization(noop))
    ).historical_rule_input

def main():
    source = _input()
    before = deepcopy(source)
    result = adapt_historical_site_event_rule_engine_registry(source)
    assert result.registry_ready and result.historical_site_registry
    assert all(item["source"] == PROVENANCE for item in result.historical_site_registry.values())
    assert source == before
    noop = adapt_historical_site_event_rule_engine_registry(_input(True))
    assert noop.registry_ready and noop.historical_site_registry == {}
    bad = deepcopy(source); bad["channel"] = "SPATIAL"
    assert not adapt_historical_site_event_rule_engine_registry(bad).registry_ready
    bad = deepcopy(source); bad["repairs"][0]["new_source"] = "RUNTIME_SPATIAL_CONDITION"
    assert not adapt_historical_site_event_rule_engine_registry(bad).registry_ready
    bad = deepcopy(source); bad["repairs"].append({**bad["repairs"][0], "after": "FALSE"})
    assert not adapt_historical_site_event_rule_engine_registry(bad).registry_ready
    d = result.to_dict()
    for key in ("spatial_overlay_used", "site_condition_context_merged", "runtime_conditions_merged", "rule_engine_modified", "apply_site_registry_called", "production_wiring_applied", "runtime_registered", "public_api_exposed"):
        assert d[key] is False
    print("=" * 72); print("STEP 62 HISTORICAL SITE EVENT RULE ENGINE REGISTRY ADAPTER"); print("=" * 72)
    print("Changed-target historical registry adaptation: PASS"); print("Zero-op historical registry adaptation: PASS")
    print("Historical provenance preservation: PASS"); print("Conflicting duplicate condition fail-closed: PASS")
    print("Caller input immutability: PASS"); print("Spatial overlay / Rule Engine injection / runtime / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")

if __name__ == "__main__": main()
