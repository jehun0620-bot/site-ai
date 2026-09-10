from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from law_data.historical_site_event_evidence_state_assembler import (
    assemble_historical_site_event_evidence_state,
)
from law_data.historical_site_event_resolver import resolve_historical_site_event
from law_data.urban_area_conversion_history_completeness_adapter import (
    adapt_urban_area_conversion_history_completeness,
)
from law_data.urban_area_conversion_positive_evidence_adapter import (
    adapt_urban_area_conversion_positive_evidence,
)


CONDITION_NAME = "도시지역편입해제구역"
SHADOW_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


@dataclass(frozen=True)
class UrbanAreaConversionShadowDiagnostics:
    positive_candidate_present: bool
    official_database_negative: bool
    unresolved_historical_source_present: bool
    current_state_known: bool


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


def build_shadow_diagnostics(
    checks: Mapping[str, Any],
) -> UrbanAreaConversionShadowDiagnostics:
    announcement_ok = bool(checks.get("announcement_query_success", False))
    announcement_rows = _safe_int(checks.get("announcement_total_count"))
    combined_count = _safe_int(checks.get("combined_candidate_count"))
    target_candidates = _safe_int(checks.get("combined_target_candidate_count"))
    unresolved_candidates = _safe_int(checks.get("combined_unresolved_count"))
    all_candidates_classified = bool(
        checks.get("all_combined_candidates_classified_non_target", False)
    )
    direct_target_events = _safe_int(checks.get("direct_target_event_count"))
    direct_not_target = bool(
        checks.get("direct_notice_is_not_target_history", False)
    )

    current_urban = bool(checks.get("current_urban_area_confirmed", False))
    current_greenbelt_absent = bool(
        checks.get("current_greenbelt_absent", False)
    )

    historic_missing = bool(checks.get("historic_chain_has_missing_content", False))
    missing_content_count = _safe_int(
        checks.get("historic_missing_content_notice_count")
    )
    archive_pending = bool(checks.get("national_archive_original_pending", False))
    archive_unverified = _safe_int(
        checks.get("national_archive_original_unverified_count")
    )

    positive_candidate_present = (
        target_candidates > 0 or direct_target_events > 0
    )

    official_database_negative = (
        announcement_ok
        and announcement_rows >= 40000
        and combined_count > 0
        and target_candidates == 0
        and unresolved_candidates == 0
        and all_candidates_classified
        and direct_target_events == 0
        and direct_not_target
    )

    unresolved_historical_source_present = (
        historic_missing
        or missing_content_count > 0
        or archive_pending
        or archive_unverified > 0
    )

    return UrbanAreaConversionShadowDiagnostics(
        positive_candidate_present=positive_candidate_present,
        official_database_negative=official_database_negative,
        unresolved_historical_source_present=unresolved_historical_source_present,
        current_state_known=(current_urban and current_greenbelt_absent),
    )


def adapt_urban_area_conversion_history_shadow(
    previous_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Run the condition through the canonical generalized historical path.

    The shadow adapter owns no direct evidence-state promotions. TRUE-side evidence
    comes through the positive adapter, completeness evidence comes through the
    completeness adapter, and the generalized assembler remains authoritative for
    canonical evidence-state construction. Separate exhaustive-disproof proof is not
    available from the current producer, so the assembler receives no such promotion.
    """

    checks = extract_checks(previous_payload)
    diagnostics = build_shadow_diagnostics(checks)
    candidate_count = _safe_int(checks.get("combined_candidate_count"))

    positive_adapter_result = adapt_urban_area_conversion_positive_evidence(
        previous_payload
    )
    completeness_adapter_result = (
        adapt_urban_area_conversion_history_completeness(previous_payload)
    )

    assembled = assemble_historical_site_event_evidence_state(
        positive_verification=positive_adapter_result["positive_verification"],
        completeness_verification=(
            completeness_adapter_result["completeness_verification"]
        ),
    )

    generalized = resolve_historical_site_event(
        assembled["evidence_state"],
        search_hit=(candidate_count > 0),
        http_200=None,
        candidate_count=candidate_count,
        negative_evidence={
            "official_database_negative": diagnostics.official_database_negative,
        },
    )

    return {
        "condition": CONDITION_NAME,
        "shadow_mode": SHADOW_MODE,
        "generalized_resolution": generalized,
        "canonical_assembly": assembled,
        "positive_adapter_result": positive_adapter_result,
        "completeness_adapter_result": completeness_adapter_result,
        "shadow_diagnostics": {
            "positive_candidate_present": diagnostics.positive_candidate_present,
            "official_database_negative": diagnostics.official_database_negative,
            "unresolved_historical_source_present": (
                diagnostics.unresolved_historical_source_present
            ),
            "current_state_known": diagnostics.current_state_known,
        },
        "promotion_guards": {
            "legacy_positive_candidate_promoted_to_verified_event": False,
            "announcement_query_success_promoted_to_complete_source_set": False,
            "announcement_query_success_promoted_to_official_history_source": False,
            "official_database_negative_promoted_to_global_history_completeness": False,
            "official_database_negative_promoted_to_global_candidate_universe": False,
            "official_database_negative_promoted_to_all_candidates_non_target": False,
            "absence_of_unresolved_diagnostic_promoted_to_verified_absence": False,
            "direct_evidence_state_construction_used": False,
        },
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
