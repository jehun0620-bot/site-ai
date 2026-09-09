from __future__ import annotations

from typing import Any, Mapping

from law_data.historical_site_event_history_completeness_verifier import (
    HistoricalHistoryCompletenessEvidence,
    verify_history_completeness,
)


CONDITION_NAME = "도시지역편입해제구역"
ADAPTER_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_mapping(data: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def extract_checks(previous_payload: Mapping[str, Any]) -> Mapping[str, Any]:
    checks = _first_mapping(
        previous_payload,
        "checks",
        "evidence_checks",
        "verification",
    )
    if checks:
        return checks

    summary = previous_payload.get("summary")
    if isinstance(summary, Mapping):
        return _first_mapping(summary, "checks", "evidence_checks")
    return {}


def adapt_urban_area_conversion_history_completeness(
    previous_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Map condition evidence into the generalized completeness verifier.

    This adapter intentionally refuses these promotions:
    - announcement query success -> complete official historical source set
    - official database negative -> global candidate-universe completeness
    - row count / no-hit -> authority/time-scope completeness

    Only unresolved-original state is directly mappable from the current producer.
    The adapter is read-only and production-unwired.
    """

    checks = extract_checks(previous_payload)

    announcement_ok = bool(checks.get("announcement_query_success", False))
    announcement_rows = _safe_int(checks.get("announcement_total_count"))
    target_candidates = _safe_int(checks.get("combined_target_candidate_count"))
    unresolved_candidates = _safe_int(checks.get("combined_unresolved_count"))
    all_candidates_classified = bool(
        checks.get("all_combined_candidates_classified_non_target", False)
    )
    direct_target_events = _safe_int(checks.get("direct_target_event_count"))
    direct_not_target = bool(
        checks.get("direct_notice_is_not_target_history", False)
    )

    historic_missing = bool(checks.get("historic_chain_has_missing_content", False))
    missing_content_count = _safe_int(
        checks.get("historic_missing_content_notice_count")
    )
    archive_pending = bool(checks.get("national_archive_original_pending", False))
    archive_unverified = _safe_int(
        checks.get("national_archive_original_unverified_count")
    )

    unresolved_historical_source_present = (
        historic_missing
        or missing_content_count > 0
        or archive_pending
        or archive_unverified > 0
    )

    official_database_negative = (
        announcement_ok
        and announcement_rows >= 40000
        and target_candidates == 0
        and unresolved_candidates == 0
        and all_candidates_classified
        and direct_target_events == 0
        and direct_not_target
    )

    required_original_documents_resolved = (
        not unresolved_historical_source_present
    )

    evidence = HistoricalHistoryCompletenessEvidence(
        official_historical_source_set_verified=False,
        authority_time_scope_completeness_verified=False,
        required_original_documents_resolved=required_original_documents_resolved,
        candidate_universe_exhaustively_enumerated=False,
    )

    verified = verify_history_completeness(
        evidence,
        search_no_hit=(target_candidates == 0),
        http_200=None,
        fetched_row_count=announcement_rows,
        negative_evidence={
            "announcement_query_success": announcement_ok,
            "official_database_negative": official_database_negative,
            "all_combined_candidates_classified_non_target": (
                all_candidates_classified
            ),
        },
    )

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "completeness_verification": verified,
        "condition_diagnostics": {
            "announcement_query_success": announcement_ok,
            "announcement_total_count": announcement_rows,
            "official_database_negative": official_database_negative,
            "unresolved_historical_source_present": (
                unresolved_historical_source_present
            ),
            "required_original_documents_resolved": (
                required_original_documents_resolved
            ),
        },
        "promotion_guards": {
            "announcement_query_success_promoted_to_official_source_set": False,
            "official_database_negative_promoted_to_global_candidate_universe": False,
            "row_count_promoted_to_authority_time_scope_completeness": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
