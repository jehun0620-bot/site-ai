from __future__ import annotations

from typing import Any, Mapping

from law_data.historical_site_event_positive_evidence_verifier import (
    HistoricalSiteEventPositiveEvidence,
    verify_historical_site_event_positive_evidence,
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


def adapt_urban_area_conversion_positive_evidence(
    previous_payload: Mapping[str, Any],
) -> dict[str, Any]:
    """Adapt current condition evidence into the positive verifier conservatively.

    Current producer fields establish candidates, document/chain discovery, archive
    candidates, and current parcel state. None positively verifies the three
    HISTORICAL_SITE_EVENT TRUE-side gates, so all gates remain false.
    """

    checks = extract_checks(previous_payload)

    combined_candidates = _safe_int(checks.get("combined_candidate_count"))
    target_candidates = _safe_int(checks.get("combined_target_candidate_count"))
    direct_hits = _safe_int(checks.get("direct_notice_hit_count"))
    direct_target_events = _safe_int(checks.get("direct_target_event_count"))
    archive_candidates = _safe_int(checks.get("national_archive_candidate_count"))

    candidate_hit = (
        combined_candidates > 0
        or target_candidates > 0
        or direct_hits > 0
        or direct_target_events > 0
        or archive_candidates > 0
    )

    title_match = bool(
        checks.get("notice_123_identified", False)
        or checks.get("notice_534_found", False)
        or checks.get("historic_daechi_notice_chain_confirmed", False)
    )

    current_geometry_match = bool(
        checks.get("current_urban_area_confirmed", False)
        or checks.get("current_greenbelt_absent", False)
    )

    archive_candidate_present = bool(
        checks.get("national_archive_candidates_confirmed", False)
        or archive_candidates > 0
    )

    positive_evidence = HistoricalSiteEventPositiveEvidence(
        verified_event_identity=False,
        historical_site_applicability=False,
        temporal_relation_verified=False,
    )

    verified = verify_historical_site_event_positive_evidence(
        positive_evidence,
        candidate_hit=candidate_hit,
        title_match=title_match,
        http_200=None,
        current_geometry_match=current_geometry_match,
        official_archive_candidate_present=archive_candidate_present,
        diagnostic_evidence={
            "combined_candidate_count": combined_candidates,
            "combined_target_candidate_count": target_candidates,
            "direct_notice_hit_count": direct_hits,
            "direct_target_event_count": direct_target_events,
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
            "national_archive_candidate_count": archive_candidates,
            "national_archive_candidates_confirmed": bool(
                checks.get("national_archive_candidates_confirmed", False)
            ),
        },
    )

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "positive_verification": verified,
        "promotion_guards": {
            "candidate_count_promoted_to_verified_event_identity": False,
            "notice_identity_promoted_to_verified_event_identity": False,
            "historical_chain_promoted_to_verified_event_identity": False,
            "current_geometry_promoted_to_historical_site_applicability": False,
            "archive_candidate_promoted_to_verified_event_identity": False,
            "document_date_promoted_to_temporal_relation": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
