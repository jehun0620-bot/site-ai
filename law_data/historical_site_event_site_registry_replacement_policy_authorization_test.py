from dataclasses import replace

from law_data.historical_site_event_overlay_application_authorization import (
    authorize_historical_site_event_overlay_application,
)
from law_data.historical_site_event_overlay_execution_package import (
    package_historical_site_event_overlay_execution,
)
from law_data.historical_site_event_provenance_preserving_overlay_contract import (
    build_historical_site_event_provenance_preserving_overlay_contract,
)
from law_data.historical_site_event_site_registry_overlay_preview import (
    preview_historical_site_event_site_registry_overlay,
)
from law_data.historical_site_event_site_registry_replacement_policy_authorization import (
    POLICY,
    authorize_historical_site_event_site_registry_replacement_policy,
)


CLASSIFICATION = "STEP48_HISTORICAL_SITE_EVENT_SITE_REGISTRY_REPLACEMENT_POLICY_AUTHORIZATION_BOUNDARY_RECONCILED"


def _preview(state: str = "TRUE", collision: bool = False):
    contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건",
        {
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP48_TEST_HISTORICAL_SOURCE",
            "resolution": "TEST_RESOLUTION",
            "evaluation": {"verified": True},
            "evidence": {"document": "TEST_NOTICE"},
        },
    )
    authorization = authorize_historical_site_event_overlay_application(contract)
    package = package_historical_site_event_overlay_execution("테스트 역사조건", authorization)
    registry = {
        "기존 공간조건": {
            "type": "SITE_SPATIAL",
            "state": "TRUE",
            "confidence": "HIGH",
            "source": "RUNTIME_SPATIAL_CONDITION",
        }
    }
    if collision:
        registry["테스트 역사조건"] = {
            "type": "SITE",
            "state": "UNKNOWN",
            "confidence": "LOW",
            "source": "BASE_SITE_CONDITION",
        }
    return preview_historical_site_event_site_registry_overlay(registry, package)


def main() -> None:
    true_auth = authorize_historical_site_event_site_registry_replacement_policy(_preview("TRUE"))
    assert true_auth.policy == POLICY
    assert true_auth.replacement_policy_authorized is True
    assert true_auth.condition_name_collision is False
    assert true_auth.authorized_preview_registry["테스트 역사조건"]["state"] == "TRUE"

    false_auth = authorize_historical_site_event_site_registry_replacement_policy(_preview("FALSE"))
    assert false_auth.replacement_policy_authorized is True
    assert false_auth.authorized_preview_registry["테스트 역사조건"]["state"] == "FALSE"

    unknown_auth = authorize_historical_site_event_site_registry_replacement_policy(_preview("UNKNOWN"))
    assert unknown_auth.replacement_policy_authorized is True
    assert unknown_auth.authorized_preview_registry["테스트 역사조건"]["state"] == "UNKNOWN"

    collision_auth = authorize_historical_site_event_site_registry_replacement_policy(
        _preview("TRUE", collision=True)
    )
    assert collision_auth.condition_name_collision is True
    assert collision_auth.no_collision_policy_satisfied is False
    assert collision_auth.replacement_policy_authorized is False
    assert collision_auth.authorized_preview_registry == {}
    assert "no_collision_policy_satisfied" in collision_auth.missing_gates

    not_ready = replace(_preview(), preview_ready=False)
    assert authorize_historical_site_event_site_registry_replacement_policy(
        not_ready
    ).replacement_policy_authorized is False

    wrong_boundary = replace(_preview(), boundary="OTHER_BOUNDARY")
    assert authorize_historical_site_event_site_registry_replacement_policy(
        wrong_boundary
    ).replacement_policy_authorized is False

    broken_historical = dict(_preview().historical_condition_after)
    broken_historical["source"] = "RUNTIME_SPATIAL_CONDITION"
    broken_preview = replace(_preview(), historical_condition_after=broken_historical)
    assert authorize_historical_site_event_site_registry_replacement_policy(
        broken_preview
    ).replacement_policy_authorized is False

    assert authorize_historical_site_event_site_registry_replacement_policy(
        None
    ).replacement_policy_authorized is False

    results = (
        true_auth,
        false_auth,
        unknown_auth,
        collision_auth,
        authorize_historical_site_event_site_registry_replacement_policy(not_ready),
        authorize_historical_site_event_site_registry_replacement_policy(wrong_boundary),
        authorize_historical_site_event_site_registry_replacement_policy(broken_preview),
        authorize_historical_site_event_site_registry_replacement_policy(None),
    )
    for result in results:
        data = result.to_dict()
        assert data["collision_replacement_authorized"] is False
        assert data["original_registry_mutated"] is False
        assert data["overlay_application_executed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["apply_site_registry_called"] is False
        assert data["refresh_rule_called"] is False
        assert data["rule_evaluation_pipeline_modified"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["rule_applicability_recalculated"] is False
        assert data["rule_applicability_changed"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 48 HISTORICAL SITE EVENT SITE REGISTRY REPLACEMENT POLICY AUTHORIZATION")
    print("=" * 72)
    print("Historical TRUE no-collision authorization: PASS")
    print("Historical FALSE no-collision authorization: PASS")
    print("Historical UNKNOWN no-collision authorization: PASS")
    print("Condition-name collision fail-closed: PASS")
    print("Boundary / readiness / provenance guards: PASS")
    print("Replacement policy authorized != registry mutation: PASS")
    print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
