from __future__ import annotations

import inspect

from law_data.historical_site_event_exhaustive_disproof import (
    HistoricalSiteEventExhaustiveDisproofEvidence,
    evaluate_historical_site_event_exhaustive_disproof,
)


CLASSIFICATION = (
    "STEP27_HISTORICAL_SITE_EVENT_EXHAUSTIVE_DISPROOF_BOUNDARY_"
    "TERMINALLY_RECONCILED"
)


def _evaluate(**overrides: object):
    values: dict[str, object] = {
        "official_history_source_verified": False,
        "history_scope_completeness_verified": False,
        "required_original_documents_resolved": False,
        "candidate_universe_exhaustively_enumerated": False,
        "all_candidates_verified_non_target": False,
        "no_unresolved_historical_source": False,
    }
    values.update(overrides)
    evidence = HistoricalSiteEventExhaustiveDisproofEvidence(**values)  # type: ignore[arg-type]
    return evaluate_historical_site_event_exhaustive_disproof(evidence)


def _assert_missing_and_partial_fail_closed() -> None:
    empty = _evaluate()
    assert empty.exhaustive_disproof_verified is False
    assert len(empty.missing_gates) == 6

    partial = _evaluate(
        official_history_source_verified=True,
        history_scope_completeness_verified=True,
        required_original_documents_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_verified_non_target=True,
    )
    assert partial.exhaustive_disproof_verified is False
    assert partial.no_unresolved_historical_source is False
    assert "no_unresolved_historical_source" in partial.missing_gates


def _assert_truthy_non_bool_fails_closed() -> None:
    for truthy in (1, "true", [True], {"verified": True}):
        assessment = _evaluate(
            official_history_source_verified=truthy,
            history_scope_completeness_verified=truthy,
            required_original_documents_resolved=truthy,
            candidate_universe_exhaustively_enumerated=truthy,
            all_candidates_verified_non_target=truthy,
            no_unresolved_historical_source=truthy,
        )
        assert assessment.exhaustive_disproof_verified is False
        assert len(assessment.missing_gates) == 6


def _assert_all_explicit_gates_required_for_positive() -> None:
    positive = _evaluate(
        official_history_source_verified=True,
        history_scope_completeness_verified=True,
        required_original_documents_resolved=True,
        candidate_universe_exhaustively_enumerated=True,
        all_candidates_verified_non_target=True,
        no_unresolved_historical_source=True,
    )
    assert positive.exhaustive_disproof_verified is True
    assert positive.missing_gates == ()

    payload = positive.to_dict()
    assert payload["negative_evidence_inference_allowed"] is False
    assert payload["search_no_hit_promoted_to_disproof"] is False
    assert payload["candidate_zero_promoted_to_disproof"] is False
    assert payload["search_exhaustion_promoted_to_universe_completeness"] is False
    assert payload["legal_absence_inference_allowed"] is False
    assert payload["negative_resolution_generated"] is False
    assert payload["site_state_mutated"] is False
    assert payload["rule_engine_state_mutated"] is False
    assert payload["production_wiring_applied"] is False
    assert payload["runtime_registry_mutated"] is False
    assert payload["public_api_exposed"] is False


def _assert_shortcut_inputs_are_not_part_of_contract() -> None:
    source = inspect.getsource(evaluate_historical_site_event_exhaustive_disproof)
    signature = inspect.signature(evaluate_historical_site_event_exhaustive_disproof)

    assert tuple(signature.parameters) == ("evidence",)

    forbidden_parameter_tokens = (
        "candidate_hit",
        "candidate_count",
        "candidate_zero",
        "title_match",
        "region_match",
        "date_match",
        "http_200",
        "search_completed",
        "search_exhausted",
        "no_hit",
        "current_geometry_verified",
        "contract_ready",
        "provenance_policy_verified",
        "history_completeness_verified=",
    )
    for token in forbidden_parameter_tokens:
        assert token not in str(signature)

    forbidden_side_effect_tokens = (
        "requests.",
        "httpx.",
        "open(",
        "write_text(",
        "write_bytes(",
        "register_runtime",
        "register_production",
        "site_analysis_builder",
        "site_analysis_service",
        "site_analysis_orchestrator",
        "site_analysis_response",
    )
    for token in forbidden_side_effect_tokens:
        assert token not in source


def main() -> None:
    _assert_missing_and_partial_fail_closed()
    _assert_truthy_non_bool_fails_closed()
    _assert_all_explicit_gates_required_for_positive()
    _assert_shortcut_inputs_are_not_part_of_contract()

    print("=" * 60)
    print("STEP 27 HISTORICAL SITE EVENT EXHAUSTIVE DISPROOF BOUNDARY TERMINAL AUDIT")
    print("Missing / partial evidence -> exhaustive disproof: FAIL-CLOSED")
    print("Truthy non-bool evidence -> exhaustive disproof: NONE")
    print("Search no-hit / candidate zero / search exhaustion shortcuts: NONE")
    print("Positive exhaustive disproof: SIX EXPLICIT VERIFIED FACTS ONLY")
    print("Unresolved historical source -> exhaustive disproof: BLOCKED")
    print("Legal absence inference / FALSE resolution generation: NONE")
    print("SITE / Rule Engine / production / runtime mutation: NONE")
    print("Public API exposure: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
