from __future__ import annotations

from pathlib import Path

from law_data.historical_site_event_qualification import (
    BOUNDARY_NAME,
    HistoricalSiteEventQualificationEvidence,
    evaluate_historical_site_event_qualification,
)


CLASSIFICATION = (
    "STEP25_HISTORICAL_SITE_EVENT_QUALIFICATION_BOUNDARY_TERMINALLY_RECONCILED"
)

ROOT = Path(__file__).resolve().parent.parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def _read_source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_missing_and_partial_evidence_fail_closed() -> None:
    missing = evaluate_historical_site_event_qualification(None)
    require(missing.boundary == BOUNDARY_NAME, "unexpected boundary name")
    require(
        missing.qualifying_historical_event_verified is False,
        "missing evidence must fail closed",
    )
    require(missing.verified_gate_count == 0, "missing evidence verified a gate")

    partial = evaluate_historical_site_event_qualification(
        HistoricalSiteEventQualificationEvidence(
            historical_event_identity_verified=True,
            historical_site_applicability_verified=True,
            temporal_relation_verified=False,
        )
    )
    require(
        partial.qualifying_historical_event_verified is False,
        "partial evidence must not qualify a historical event",
    )
    require(
        partial.missing_gates == ("temporal_relation_verified",),
        "partial evidence missing-gate diagnostics changed",
    )


def test_truthy_non_bool_values_do_not_verify_gates() -> None:
    assessment = evaluate_historical_site_event_qualification(
        HistoricalSiteEventQualificationEvidence(
            historical_event_identity_verified=1,
            historical_site_applicability_verified="true",
            temporal_relation_verified=[True],
        )
    )
    require(
        assessment.verified_gate_count == 0,
        "truthy non-bool values must not verify qualification gates",
    )
    require(
        assessment.qualifying_historical_event_verified is False,
        "truthy non-bool evidence must fail closed",
    )


def test_all_three_explicit_positive_facts_are_required() -> None:
    assessment = evaluate_historical_site_event_qualification(
        HistoricalSiteEventQualificationEvidence(
            historical_event_identity_verified=True,
            historical_site_applicability_verified=True,
            temporal_relation_verified=True,
        )
    )
    require(
        assessment.qualifying_historical_event_verified is True,
        "all three explicit verified facts should qualify the event",
    )
    require(assessment.verified_gate_count == 3, "positive gate count changed")
    require(assessment.required_gate_count == 3, "required gate count changed")
    require(not assessment.missing_gates, "positive assessment has missing gates")

    payload = assessment.to_dict()
    require(
        payload["negative_evidence_inference_allowed"] is False,
        "qualification enabled negative evidence inference",
    )
    require(
        payload["legal_absence_inference_allowed"] is False,
        "qualification enabled legal absence inference",
    )
    require(
        payload["final_regulation_resolution_applied"] is False,
        "qualification promoted itself to final regulation resolution",
    )
    require(payload["site_state_mutated"] is False, "qualification mutated SITE")
    require(
        payload["production_wiring_applied"] is False,
        "qualification manufactured production wiring",
    )
    require(
        payload["runtime_registry_mutated"] is False,
        "qualification mutated runtime registry",
    )


def test_shortcut_signals_are_not_part_of_the_boundary_contract() -> None:
    source = _read_source("law_data/historical_site_event_qualification.py")

    shortcut_parameter_tokens = (
        "candidate_hit:",
        "title_match:",
        "region_match:",
        "date_match:",
        "http_200:",
        "search_completed:",
        "search_exhausted:",
        "no_hit:",
        "current_geometry_verified:",
        "contract_ready:",
        "provenance_policy_verified:",
        "history_completeness_verified:",
    )
    for token in shortcut_parameter_tokens:
        require(
            token not in source,
            f"diagnostic shortcut unexpectedly became qualification input: {token}",
        )


def test_boundary_has_no_search_registry_mutation_or_auto_wiring_surface() -> None:
    source = _read_source("law_data/historical_site_event_qualification.py")
    forbidden_tokens = (
        "requests.",
        "httpx.",
        "open(",
        "write_text(",
        "write_bytes(",
        "HISTORICAL_SITE_EVENT_QUALIFICATION_REGISTRY",
        "def register_",
        "def register_runtime",
        "def resolve_",
        "def promote_",
        "evaluate_regulation_source_policy_requirement",
        "evaluate_historical_history_completeness",
        "adapt_urban_area_conversion_provenance_policy",
    )
    for token in forbidden_tokens:
        require(token not in source, f"forbidden STEP25 boundary surface: {token}")

    isolated_paths = (
        "law_data/regulation_source_policy_requirement.py",
        "law_data/historical_history_completeness.py",
        "law_data/urban_area_conversion_provenance_policy_adapter.py",
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )
    integration_tokens = (
        "historical_site_event_qualification",
        "HistoricalSiteEventQualificationAssessment",
        "evaluate_historical_site_event_qualification",
    )
    for relative_path in isolated_paths:
        target_source = _read_source(relative_path)
        for token in integration_tokens:
            require(
                token not in target_source,
                f"STEP25 boundary unexpectedly auto-wired into {relative_path}: {token}",
            )


def main() -> None:
    test_missing_and_partial_evidence_fail_closed()
    test_truthy_non_bool_values_do_not_verify_gates()
    test_all_three_explicit_positive_facts_are_required()
    test_shortcut_signals_are_not_part_of_the_boundary_contract()
    test_boundary_has_no_search_registry_mutation_or_auto_wiring_surface()

    print("=" * 72)
    print("STEP 25 HISTORICAL SITE EVENT QUALIFICATION BOUNDARY TERMINAL AUDIT")
    print("=" * 72)
    print("Missing / partial evidence -> qualification: FAIL-CLOSED")
    print("Truthy non-bool evidence -> qualification: NONE")
    print("Candidate/title/region/date/search shortcuts -> qualification: NONE")
    print("Provenance / history completeness / current geometry -> shortcut: NONE")
    print("Positive qualification: THREE EXPLICIT VERIFIED FACTS ONLY")
    print("Legal absence / negative evidence inference: NONE")
    print("Final legal resolution / SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("STEP23/24 adapter/source-policy integration: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
