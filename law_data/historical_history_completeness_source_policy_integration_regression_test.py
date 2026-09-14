from __future__ import annotations

from pathlib import Path

from law_data.historical_history_completeness import (
    HistoricalHistoryCompletenessEvidence,
)
from law_data.regulation_resolution_profile_registry import (
    URBAN_AREA_CONVERSION_CONDITION_NAME,
)
from law_data.urban_area_conversion_provenance_policy_adapter import (
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = "STEP24_HISTORICAL_HISTORY_COMPLETENESS_SOURCE_POLICY_INTEGRATION_PASS"
BASE_DIR = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _read_source(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def _diagnostic_payload() -> dict[str, object]:
    return {
        "checks": {
            "combined_candidate_count": 4,
            "direct_notice_hit_count": 2,
            "notice_123_identified": True,
            "notice_534_found": True,
            "historic_daechi_notice_chain_confirmed": True,
            "announcement_query_success": True,
            "national_archive_candidates_confirmed": True,
            "national_archive_candidate_count": 3,
            "current_urban_area_confirmed": True,
            "current_greenbelt_absent": True,
            "history_completeness_verified": True,
            "search_completed": True,
            "search_exhausted": True,
            "all_discovered_records_processed": True,
            "source_policy_verified": True,
            "provenance_verified": True,
        }
    }


def _complete_evidence() -> HistoricalHistoryCompletenessEvidence:
    required = (
        "SOURCE_FAMILY_A",
        "SOURCE_FAMILY_B",
        "INTERVAL_1980_1989",
        "INTERVAL_1990_1999",
        "EVENT_CLASS_DESIGNATION",
        "EVENT_CLASS_CHANGE",
        "EVENT_CLASS_RELEASE",
    )
    return HistoricalHistoryCompletenessEvidence(
        target_identity_verified=True,
        coverage_scope_defined=True,
        required_coverage_items=required,
        verified_coverage_facts={item: True for item in required},
        unresolved_gaps=(),
    )


def test_missing_explicit_evidence_preserves_fail_closed_state() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    history = result["history_completeness"]
    source_policy = result["regulation_source_policy_requirement"]
    blockers = result["condition_specific_blockers"]

    require(result["condition"] == URBAN_AREA_CONVERSION_CONDITION_NAME, "condition changed")
    require(
        history["history_completeness_verified"] is False,
        "diagnostics manufactured history completeness",
    )
    require(
        "HISTORY COMPLETENESS VERIFIED" not in source_policy["verified_requirements"],
        "missing explicit evidence manufactured source-policy fact",
    )
    require(
        blockers["history_completeness_unverified"] is True,
        "missing evidence cleared history completeness blocker",
    )
    require(
        source_policy["source_policy_requirement_satisfied"] is False,
        "missing evidence satisfied source policy",
    )


def test_partial_or_unresolved_explicit_evidence_remains_false() -> None:
    partial = HistoricalHistoryCompletenessEvidence(
        target_identity_verified=True,
        coverage_scope_defined=True,
        required_coverage_items=("SOURCE_FAMILY_A", "INTERVAL_1980_1989"),
        verified_coverage_facts={"SOURCE_FAMILY_A": True},
    )
    partial_result = adapt_urban_area_conversion_provenance_policy(
        _diagnostic_payload(),
        history_completeness_evidence=partial,
    )
    require(
        partial_result["history_completeness"]["history_completeness_verified"] is False,
        "partial explicit evidence verified completeness",
    )

    unresolved = HistoricalHistoryCompletenessEvidence(
        target_identity_verified=True,
        coverage_scope_defined=True,
        required_coverage_items=("SOURCE_FAMILY_A",),
        verified_coverage_facts={"SOURCE_FAMILY_A": True},
        unresolved_gaps=("ORIGINAL_NOTICE_UNRESOLVED",),
    )
    unresolved_result = adapt_urban_area_conversion_provenance_policy(
        _diagnostic_payload(),
        history_completeness_evidence=unresolved,
    )
    require(
        unresolved_result["history_completeness"]["history_completeness_verified"] is False,
        "unresolved explicit evidence verified completeness",
    )
    require(
        unresolved_result["condition_specific_blockers"]["history_completeness_unverified"]
        is True,
        "unresolved gap cleared blocker",
    )


def test_complete_explicit_evidence_supplies_only_history_requirement_fact() -> None:
    result = adapt_urban_area_conversion_provenance_policy(
        _diagnostic_payload(),
        history_completeness_evidence=_complete_evidence(),
    )
    history = result["history_completeness"]
    policy = result["provenance_policy"]
    source_policy = result["regulation_source_policy_requirement"]
    blockers = result["condition_specific_blockers"]
    guards = result["promotion_guards"]

    require(
        history["history_completeness_verified"] is True,
        "complete explicit coverage did not verify history completeness",
    )
    require(
        source_policy["verified_requirements"] == ["HISTORY COMPLETENESS VERIFIED"],
        "history completeness supplied facts beyond its own requirement",
    )
    require(
        policy["provenance_policy_verified"] is False,
        "history completeness promoted provenance",
    )
    require(
        "PROVENANCE VERIFIED" in source_policy["missing_requirements"],
        "history completeness manufactured provenance requirement",
    )
    require(
        source_policy["source_policy_requirement_satisfied"] is False,
        "history completeness alone satisfied all source-policy requirements",
    )
    require(
        blockers["history_completeness_unverified"] is False,
        "verified history completeness blocker remained set",
    )
    require(
        blockers["source_policy_requirement_unsatisfied"] is True,
        "remaining provenance blocker was lost",
    )
    require(
        guards["diagnostics_promoted_to_history_completeness_evidence"] is False,
        "diagnostics promoted into history completeness evidence",
    )
    require(
        guards["history_completeness_promoted_to_legal_resolution"] is False,
        "history completeness promoted to legal resolution",
    )
    require(result["output_written"] is False, "adapter wrote output")
    require(result["production_wiring_applied"] is False, "production wiring applied")
    require(result["overlay_mutated"] is False, "SITE overlay mutated")
    require(result["runtime_registry_mutated"] is False, "runtime registry mutated")


def test_integration_does_not_auto_wire_runtime_rule_engine_or_public_api() -> None:
    isolated_paths = (
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )
    forbidden_tokens = (
        "historical_history_completeness",
        "HistoricalHistoryCompletenessEvidence",
        "evaluate_historical_history_completeness",
    )

    for relative_path in isolated_paths:
        source = _read_source(relative_path)
        for token in forbidden_tokens:
            require(
                token not in source,
                f"STEP24 integration unexpectedly auto-wired into {relative_path}: {token}",
            )


def run_regression() -> None:
    test_missing_explicit_evidence_preserves_fail_closed_state()
    test_partial_or_unresolved_explicit_evidence_remains_false()
    test_complete_explicit_evidence_supplies_only_history_requirement_fact()
    test_integration_does_not_auto_wire_runtime_rule_engine_or_public_api()

    print("=" * 92)
    print("STEP 24 HISTORICAL HISTORY COMPLETENESS -> SOURCE POLICY INTEGRATION REGRESSION")
    print("=" * 92)
    print("Diagnostic payload -> history completeness evidence: NONE")
    print("Missing / partial / unresolved explicit evidence -> completeness: FALSE")
    print("Complete explicit coverage -> HISTORY COMPLETENESS VERIFIED fact: TRUE")
    print("History completeness -> provenance verification: NONE")
    print("History completeness alone -> source-policy satisfaction: NONE")
    print("Legal resolution / SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_regression()
