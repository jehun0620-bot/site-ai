from __future__ import annotations

from pathlib import Path

from law_data.historical_history_completeness import (
    HistoricalHistoryCompletenessEvidence,
    evaluate_historical_history_completeness,
)


CLASSIFICATION = "STEP24_HISTORICAL_HISTORY_COMPLETENESS_BOUNDARY_TERMINALLY_RECONCILED"
BASE_DIR = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _read_source(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def test_missing_or_empty_evidence_fails_closed() -> None:
    missing = evaluate_historical_history_completeness(None).to_dict()
    require(missing["target_identity_verified"] is False, "missing target inferred")
    require(missing["coverage_scope_defined"] is False, "missing scope inferred")
    require(
        missing["coverage_requirements_declared"] is False,
        "missing requirements unexpectedly declared",
    )
    require(
        missing["history_completeness_verified"] is False,
        "missing evidence unexpectedly verified history completeness",
    )

    empty = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
        )
    ).to_dict()
    require(
        empty["history_completeness_verified"] is False,
        "empty coverage declaration was vacuously verified",
    )


def test_truthy_or_partial_facts_do_not_verify_completeness() -> None:
    required = ("SOURCE_FAMILY_A", "INTERVAL_1980_1989", "EVENT_CLASS_CHANGE")

    truthy = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=1,
            coverage_scope_defined="true",
            required_coverage_items=required,
            verified_coverage_facts={item: True for item in required},
        )
    ).to_dict()
    require(
        truthy["history_completeness_verified"] is False,
        "truthy non-bool identity/scope unexpectedly verified completeness",
    )

    partial = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
            required_coverage_items=required,
            verified_coverage_facts={
                "SOURCE_FAMILY_A": True,
                "INTERVAL_1980_1989": True,
                "EVENT_CLASS_CHANGE": False,
            },
        )
    ).to_dict()
    require(
        partial["missing_coverage_items"] == ["EVENT_CLASS_CHANGE"],
        "partial missing coverage changed",
    )
    require(
        partial["history_completeness_verified"] is False,
        "partial coverage unexpectedly verified completeness",
    )

    fact_truthy = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
            required_coverage_items=("SOURCE_FAMILY_A",),
            verified_coverage_facts={"SOURCE_FAMILY_A": 1},
        )
    ).to_dict()
    require(
        fact_truthy["history_completeness_verified"] is False,
        "truthy non-bool coverage fact unexpectedly verified completeness",
    )


def test_unresolved_gap_blocks_otherwise_complete_coverage() -> None:
    assessment = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
            required_coverage_items=("SOURCE_FAMILY_A", "INTERVAL_1990_1999"),
            verified_coverage_facts={
                "SOURCE_FAMILY_A": True,
                "INTERVAL_1990_1999": True,
            },
            unresolved_gaps=("ORIGINAL_NOTICE_UNRESOLVED",),
        )
    ).to_dict()

    require(assessment["missing_coverage_items"] == [], "verified coverage lost")
    require(assessment["unresolved_gap_present"] is True, "gap disappeared")
    require(
        assessment["history_completeness_verified"] is False,
        "unresolved gap unexpectedly allowed completeness",
    )


def test_positive_verification_requires_complete_explicit_coverage() -> None:
    required = (
        "SOURCE_FAMILY_A",
        "SOURCE_FAMILY_B",
        "INTERVAL_1980_1989",
        "INTERVAL_1990_1999",
        "EVENT_CLASS_DESIGNATION",
        "EVENT_CLASS_CHANGE",
        "EVENT_CLASS_RELEASE",
    )
    assessment = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
            required_coverage_items=required,
            verified_coverage_facts={
                **{item: True for item in required},
                "UNRELATED_DIAGNOSTIC": True,
            },
            unresolved_gaps=(),
        )
    ).to_dict()

    require(
        assessment["verified_coverage_items"] == list(required),
        "complete verified coverage set changed",
    )
    require(assessment["missing_coverage_items"] == [], "complete coverage missing")
    require(
        assessment["unexpected_verified_items"] == ["UNRELATED_DIAGNOSTIC"],
        "unrelated fact was not isolated diagnostically",
    )
    require(
        assessment["history_completeness_verified"] is True,
        "complete explicit coverage did not verify history completeness",
    )
    require(
        "state" not in assessment and "site_state" not in assessment,
        "history completeness manufactured SITE state",
    )
    require(
        "production_registration_allowed" not in assessment,
        "history completeness manufactured production permission",
    )
    require(
        "runtime_registration_allowed" not in assessment,
        "history completeness manufactured runtime permission",
    )


def test_diagnostic_shortcuts_are_non_dispositive() -> None:
    shortcuts = (
        "SEARCH_COMPLETED",
        "SEARCH_EXHAUSTED",
        "NO_HIT",
        "ALL_DISCOVERED_RECORDS_PROCESSED",
        "SOURCE_FAMILY_ENUMERATION_COMPLETE",
        "PROVENANCE_VERIFIED",
        "CONTRACT_READY",
        "CURRENT_GEOMETRY_VERIFIED",
    )

    assessment = evaluate_historical_history_completeness(
        HistoricalHistoryCompletenessEvidence(
            target_identity_verified=True,
            coverage_scope_defined=True,
            required_coverage_items=("REQUIRED_HISTORICAL_COVERAGE",),
            verified_coverage_facts={shortcut: True for shortcut in shortcuts},
        )
    ).to_dict()

    require(
        assessment["missing_coverage_items"] == ["REQUIRED_HISTORICAL_COVERAGE"],
        "diagnostic shortcut satisfied required historical coverage",
    )
    require(
        assessment["history_completeness_verified"] is False,
        "diagnostic shortcuts unexpectedly verified completeness",
    )


def test_boundary_has_no_search_registry_mutation_or_integration_surface() -> None:
    source = _read_source("law_data/historical_history_completeness.py")

    forbidden_tokens = (
        "requests.",
        "httpx.",
        "open(",
        "write_text(",
        "write_bytes(",
        "HISTORY_COMPLETENESS_REGISTRY",
        "def register_",
        "def register_runtime",
        "def resolve_",
        "def promote_",
        "evaluate_regulation_source_policy_requirement",
        "adapt_urban_area_conversion_provenance_policy",
    )
    for token in forbidden_tokens:
        require(
            token not in source,
            f"STEP24 boundary unexpectedly contains integration/mutation surface: {token}",
        )

    isolated_paths = (
        "law_data/regulation_source_policy_requirement.py",
        "law_data/urban_area_conversion_provenance_policy_adapter.py",
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )
    forbidden_integration_tokens = (
        "historical_history_completeness",
        "HistoricalHistoryCompletenessAssessment",
        "evaluate_historical_history_completeness",
    )
    for relative_path in isolated_paths:
        existing = _read_source(relative_path)
        for token in forbidden_integration_tokens:
            require(
                token not in existing,
                f"STEP24 boundary unexpectedly auto-wired into {relative_path}: {token}",
            )


def run_terminal_audit() -> None:
    test_missing_or_empty_evidence_fails_closed()
    test_truthy_or_partial_facts_do_not_verify_completeness()
    test_unresolved_gap_blocks_otherwise_complete_coverage()
    test_positive_verification_requires_complete_explicit_coverage()
    test_diagnostic_shortcuts_are_non_dispositive()
    test_boundary_has_no_search_registry_mutation_or_integration_surface()

    print("=" * 88)
    print("STEP 24 HISTORICAL HISTORY COMPLETENESS BOUNDARY TERMINAL AUDIT")
    print("=" * 88)
    print("Missing / empty coverage evidence: FAIL-CLOSED PASS")
    print("Truthy non-bool / partial coverage -> completeness: NONE")
    print("Unresolved coverage gap -> completeness: BLOCKED")
    print("Search completed/exhausted/no-hit -> completeness: NONE")
    print("Discovered records processed -> completeness: NONE")
    print("Provenance / contract readiness / current geometry -> completeness: NONE")
    print("Positive completeness: EXPLICIT COMPLETE VERIFIED COVERAGE ONLY")
    print("Source discovery/search: NONE")
    print("Legal absence / SITE state inference: NONE")
    print("Production/runtime mutation: NONE")
    print("STEP23 adapter/source-policy integration: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_terminal_audit()
