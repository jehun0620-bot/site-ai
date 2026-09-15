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


CLASSIFICATION = "STEP47_HISTORICAL_SITE_EVENT_SITE_REGISTRY_OVERLAY_PREVIEW_BOUNDARY_RECONCILED"


def _package(state: str = "TRUE"):
    contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건",
        {
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP47_TEST_HISTORICAL_SOURCE",
            "resolution": "TEST_RESOLUTION",
            "evaluation": {"verified": True},
            "evidence": {"document": "TEST_NOTICE"},
        },
    )
    authorization = authorize_historical_site_event_overlay_application(contract)
    return package_historical_site_event_overlay_execution("테스트 역사조건", authorization)


def main() -> None:
    existing = {
        "기존 공간조건": {
            "type": "SITE_SPATIAL",
            "state": "TRUE",
            "confidence": "HIGH",
            "source": "RUNTIME_SPATIAL_CONDITION",
        }
    }
    existing_snapshot = {name: dict(value) for name, value in existing.items()}

    true_preview = preview_historical_site_event_site_registry_overlay(existing, _package("TRUE"))
    assert true_preview.preview_ready is True
    assert true_preview.condition_name_collision is False
    assert true_preview.preview_registry["기존 공간조건"] == existing["기존 공간조건"]
    assert true_preview.preview_registry["테스트 역사조건"]["type"] == "SITE_HISTORY"
    assert true_preview.preview_registry["테스트 역사조건"]["state"] == "TRUE"
    assert true_preview.preview_registry["테스트 역사조건"]["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
    assert existing == existing_snapshot

    false_preview = preview_historical_site_event_site_registry_overlay(existing, _package("FALSE"))
    assert false_preview.preview_ready is True
    assert false_preview.preview_registry["테스트 역사조건"]["state"] == "FALSE"

    unknown_preview = preview_historical_site_event_site_registry_overlay(existing, _package("UNKNOWN"))
    assert unknown_preview.preview_ready is True
    assert unknown_preview.preview_registry["테스트 역사조건"]["state"] == "UNKNOWN"

    collision_registry = {
        "테스트 역사조건": {
            "type": "SITE",
            "state": "UNKNOWN",
            "confidence": "LOW",
            "source": "BASE_SITE_CONDITION",
        }
    }
    collision_snapshot = {name: dict(value) for name, value in collision_registry.items()}
    collision_preview = preview_historical_site_event_site_registry_overlay(
        collision_registry, _package("TRUE")
    )
    assert collision_preview.preview_ready is True
    assert collision_preview.condition_name_collision is True
    assert collision_preview.existing_condition_before == collision_snapshot["테스트 역사조건"]
    assert collision_preview.historical_condition_after["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
    assert collision_preview.preview_registry["테스트 역사조건"]["type"] == "SITE_HISTORY"
    assert collision_registry == collision_snapshot

    not_ready_package = replace(_package(), execution_ready=False)
    assert preview_historical_site_event_site_registry_overlay(
        existing, not_ready_package
    ).preview_ready is False

    wrong_target = replace(_package(), execution_target="OTHER_TARGET")
    assert preview_historical_site_event_site_registry_overlay(existing, wrong_target).preview_ready is False

    wrong_boundary = replace(_package(), boundary="OTHER_BOUNDARY")
    assert preview_historical_site_event_site_registry_overlay(existing, wrong_boundary).preview_ready is False

    broken_candidate = dict(_package().registry_condition)
    broken_candidate["source"] = "RUNTIME_SPATIAL_CONDITION"
    broken_package = replace(_package(), registry_condition=broken_candidate)
    assert preview_historical_site_event_site_registry_overlay(existing, broken_package).preview_ready is False

    malformed_registry = {"bad": "not-a-mapping"}
    assert preview_historical_site_event_site_registry_overlay(
        malformed_registry, _package()
    ).preview_ready is False

    assert preview_historical_site_event_site_registry_overlay(existing, None).preview_ready is False

    results = (
        true_preview,
        false_preview,
        unknown_preview,
        collision_preview,
        preview_historical_site_event_site_registry_overlay(existing, not_ready_package),
        preview_historical_site_event_site_registry_overlay(existing, wrong_target),
        preview_historical_site_event_site_registry_overlay(existing, wrong_boundary),
        preview_historical_site_event_site_registry_overlay(existing, broken_package),
        preview_historical_site_event_site_registry_overlay(malformed_registry, _package()),
        preview_historical_site_event_site_registry_overlay(existing, None),
    )
    for result in results:
        data = result.to_dict()
        assert data["original_registry_mutated"] is False
        assert data["overlay_application_executed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["apply_site_registry_called"] is False
        assert data["refresh_rule_called"] is False
        assert data["rule_evaluation_pipeline_modified"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["site_condition_context_injected"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["site_state_mutated"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["rule_applicability_recalculated"] is False
        assert data["rule_applicability_changed"] is False
        assert data["builder_wiring_applied"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["historical_producer_auto_run"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 47 HISTORICAL SITE EVENT SITE REGISTRY OVERLAY PREVIEW")
    print("=" * 72)
    print("Historical TRUE overlay preview: PASS")
    print("Historical FALSE overlay preview: PASS")
    print("Historical UNKNOWN overlay preview: PASS")
    print("Existing spatial registry preserved in deep-copy preview: PASS")
    print("Condition-name collision replacement diagnostics: PASS")
    print("Boundary / target / readiness / provenance guards: PASS")
    print("Preview ready != SITE registry mutation: PASS")
    print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
