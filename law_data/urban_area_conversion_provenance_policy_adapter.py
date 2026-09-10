from __future__ import annotations

from typing import Any, Mapping

from law_data.historical_site_event_provenance_policy import (
    HistoricalSiteEventProvenanceEvidence,
    evaluate_historical_site_event_provenance_policy,
)


CONDITION_NAME = "도시지역편입해제구역"
ADAPTER_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


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


def adapt_urban_area_conversion_provenance_policy(
    previous_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Bind current condition diagnostics to the common provenance policy.

    Existing producer/adapter fields preserve useful diagnostic provenance, but they
    do not yet positively verify the six production provenance gates. Therefore all
    provenance gates remain false and the condition-specific provenance policy stays
    blocked.

    This adapter is read-only. It does not promote diagnostics into legal evidence,
    write output, apply production wiring, mutate SITE overlay, or mutate a runtime
    registry.
    """

    checks = extract_checks(previous_payload)

    candidate_hit = bool(
        checks.get("combined_candidate_count", 0)
        or checks.get("combined_target_candidate_count", 0)
        or checks.get("direct_notice_hit_count", 0)
        or checks.get("direct_target_event_count", 0)
    )
    title_match = bool(
        checks.get("notice_123_identified", False)
        or checks.get("notice_534_found", False)
        or checks.get("historic_daechi_notice_chain_confirmed", False)
    )
    source_url_present = bool(
        checks.get("announcement_query_success", False)
        or checks.get("national_archive_candidates_confirmed", False)
    )
    archive_candidate_present = bool(
        checks.get("national_archive_candidates_confirmed", False)
        or checks.get("national_archive_candidate_count", 0)
    )

    evidence = HistoricalSiteEventProvenanceEvidence(
        source_authority_identity_verified=False,
        source_role_explicit=False,
        document_identity_traceable=False,
        original_document_traceable=False,
        site_applicability_traceable=False,
        temporal_relation_traceable=False,
    )

    policy = evaluate_historical_site_event_provenance_policy(
        evidence,
        candidate_hit=candidate_hit,
        title_match=title_match,
        http_200=None,
        source_url_present=source_url_present,
        archive_candidate_present=archive_candidate_present,
        diagnostic_evidence={
            "announcement_query_success": bool(
                checks.get("announcement_query_success", False)
            ),
            "historic_daechi_notice_chain_confirmed": bool(
                checks.get("historic_daechi_notice_chain_confirmed", False)
            ),
            "notice_123_identified": bool(
                checks.get("notice_123_identified", False)
            ),
            "notice_534_found": bool(checks.get("notice_534_found", False)),
            "current_urban_area_confirmed": bool(
                checks.get("current_urban_area_confirmed", False)
            ),
            "current_greenbelt_absent": bool(
                checks.get("current_greenbelt_absent", False)
            ),
            "national_archive_candidates_confirmed": bool(
                checks.get("national_archive_candidates_confirmed", False)
            ),
            "national_archive_original_pending": bool(
                checks.get("national_archive_original_pending", False)
            ),
        },
    )

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "provenance_policy": policy,
        "semantic_contract": {
            "diagnostic_provenance_present_does_not_mean_gate_verified": True,
            "original_diagnostics_do_not_mean_complete_production_provenance": True,
            "policy_binding_does_not_mean_provenance_policy_verified": True,
            "provenance_policy_verified_does_not_mean_legal_evidence_verified": True,
        },
        "condition_specific_blockers": {
            "source_authority_identity_unverified": True,
            "source_role_unverified": True,
            "document_identity_traceability_unverified": True,
            "original_document_traceability_unverified": True,
            "site_applicability_traceability_unverified": True,
            "temporal_relation_traceability_unverified": True,
        },
        "promotion_guards": {
            "candidate_promoted_to_provenance": False,
            "notice_identity_promoted_to_provenance": False,
            "current_geometry_promoted_to_historical_site_provenance": False,
            "archive_candidate_promoted_to_original_traceability": False,
            "provenance_promoted_to_legal_resolution": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
