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
    authorize_historical_site_event_site_registry_replacement_policy,
)
from law_data.historical_site_event_site_registry_mutation_transaction import (
    MUTATION_TARGET,
    prepare_historical_site_event_site_registry_mutation_transaction,
)


CLASSIFICATION = "STEP49_HISTORICAL_SITE_EVENT_SITE_REGISTRY_MUTATION_TRANSACTION_BOUNDARY_RECONCILED"


def _authorization(state: str = "TRUE"):
    contract = build_historical_site_event_provenance_preserving_overlay_contract(
        "테스트 역사조건",
        {
            "type": "SITE_HISTORY",
            "state": state,
            "confidence": "HIGH",
            "source": "STEP49_TEST_HISTORICAL_SOURCE",
            "resolution": "TEST_RESOLUTION",
            "evaluation": {"verified": True},
            "evidence": {"document": "TEST_NOTICE"},
        },
    )
    overlay_auth = authorize_historical_site_event_overlay_application(contract)
    package = package_historical_site_event_overlay_execution("테스트 역사조건", overlay_auth)
    preview = preview_historical_site_event_site_registry_overlay(
        {
            "기존 공간조건": {
                "type": "SITE_SPATIAL",
                "state": "TRUE",
                "confidence": "HIGH",
                "source": "RUNTIME_SPATIAL_CONDITION",
            }
        },
        package,
    )
    return authorize_historical_site_event_site_registry_replacement_policy(preview)


def main() -> None:
    true_tx = prepare_historical_site_event_site_registry_mutation_transaction(_authorization("TRUE"))
    assert true_tx.mutation_transaction_ready is True
    assert true_tx.mutation_target == MUTATION_TARGET
    assert true_tx.historical_condition_count == 1
    assert true_tx.historical_condition_name == "테스트 역사조건"
    assert true_tx.transaction_historical_condition["state"] == "TRUE"
    assert true_tx.transaction_historical_condition["source"] == "RUNTIME_HISTORICAL_SITE_EVENT"
    assert "기존 공간조건" in true_tx.transaction_registry_snapshot

    false_tx = prepare_historical_site_event_site_registry_mutation_transaction(_authorization("FALSE"))
    assert false_tx.mutation_transaction_ready is True
    assert false_tx.transaction_historical_condition["state"] == "FALSE"

    unknown_tx = prepare_historical_site_event_site_registry_mutation_transaction(_authorization("UNKNOWN"))
    assert unknown_tx.mutation_transaction_ready is True
    assert unknown_tx.transaction_historical_condition["state"] == "UNKNOWN"

    unauthorized = replace(
        _authorization(),
        replacement_policy_authorized=False,
        authorized_preview_registry={},
    )
    assert prepare_historical_site_event_site_registry_mutation_transaction(
        unauthorized
    ).mutation_transaction_ready is False

    wrong_boundary = replace(_authorization(), boundary="OTHER_BOUNDARY")
    assert prepare_historical_site_event_site_registry_mutation_transaction(
        wrong_boundary
    ).mutation_transaction_ready is False

    wrong_policy = replace(_authorization(), policy="ALLOW_COLLISION_REPLACEMENT")
    assert prepare_historical_site_event_site_registry_mutation_transaction(
        wrong_policy
    ).mutation_transaction_ready is False

    collision_tamper = replace(
        _authorization(),
        condition_name_collision=True,
        no_collision_policy_satisfied=False,
    )
    assert prepare_historical_site_event_site_registry_mutation_transaction(
        collision_tamper
    ).mutation_transaction_ready is False

    multiple_registry = dict(_authorization().authorized_preview_registry)
    multiple_registry["추가 역사조건"] = dict(multiple_registry["테스트 역사조건"])
    multiple_history = replace(_authorization(), authorized_preview_registry=multiple_registry)
    multiple_tx = prepare_historical_site_event_site_registry_mutation_transaction(multiple_history)
    assert multiple_tx.mutation_transaction_ready is False
    assert multiple_tx.historical_condition_count == 2

    assert prepare_historical_site_event_site_registry_mutation_transaction(
        None
    ).mutation_transaction_ready is False

    results = (
        true_tx,
        false_tx,
        unknown_tx,
        prepare_historical_site_event_site_registry_mutation_transaction(unauthorized),
        prepare_historical_site_event_site_registry_mutation_transaction(wrong_boundary),
        prepare_historical_site_event_site_registry_mutation_transaction(wrong_policy),
        prepare_historical_site_event_site_registry_mutation_transaction(collision_tamper),
        multiple_tx,
        prepare_historical_site_event_site_registry_mutation_transaction(None),
    )
    for result in results:
        data = result.to_dict()
        assert data["mutation_executed"] is False
        assert data["original_registry_mutated"] is False
        assert data["overlay_application_executed"] is False
        assert data["site_registry_overlaid"] is False
        assert data["apply_site_registry_called"] is False
        assert data["refresh_rule_called"] is False
        assert data["rule_evaluation_pipeline_modified"] is False
        assert data["site_analysis_builder_modified"] is False
        assert data["rule_engine_input_consumed"] is False
        assert data["rule_engine_state_mutated"] is False
        assert data["rule_evaluation_executed"] is False
        assert data["rule_applicability_recalculated"] is False
        assert data["rule_applicability_changed"] is False
        assert data["production_wiring_applied"] is False
        assert data["runtime_registered"] is False
        assert data["runtime_registry_mutated"] is False
        assert data["public_api_exposed"] is False

    print("=" * 72)
    print("STEP 49 HISTORICAL SITE EVENT SITE REGISTRY MUTATION TRANSACTION")
    print("=" * 72)
    print("Historical TRUE mutation transaction: PASS")
    print("Historical FALSE mutation transaction: PASS")
    print("Historical UNKNOWN mutation transaction: PASS")
    print("No-collision policy / exact authorization binding: PASS")
    print("Exactly-one historical condition guard: PASS")
    print("Historical provenance preservation guards: PASS")
    print("Transaction ready != registry mutation: PASS")
    print("apply_site_registry / refresh_rule / Rule Engine evaluation: NONE")
    print("Builder / production wiring / runtime registration / API: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
