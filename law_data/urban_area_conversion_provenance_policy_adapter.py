from __future__ import annotations

from typing import Any, Mapping

from law_data.authority_source_scope import normalize_authority_source_scope
from law_data.historical_site_event_provenance_policy import (
    HistoricalSiteEventProvenanceEvidence,
    evaluate_historical_site_event_provenance_policy,
)
from law_data.regulation_authority_requirement import (
    evaluate_regulation_authority_requirement,
)
from law_data.regulation_resolution_profile_registry import (
    get_regulation_resolution_profile,
)
from law_data.regulation_source_policy_requirement import (
    evaluate_regulation_source_policy_requirement,
)


CONDITION_NAME = "도시지역편입해제구역"
ADAPTER_MODE = "READ_ONLY_PRODUCTION_UNWIRED"


def _first_mapping(data: Mapping[str, Any], *keys: str) -> Mapping[str, Any]:
    for key in keys:
        value = data.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def _first_text(data: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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
    """Bind current condition diagnostics to common authority/provenance policies.

    Existing producer/adapter fields preserve useful diagnostic provenance, but they
    do not yet positively verify competent authority, source role, or the remaining
    six production provenance gates. Descriptive source metadata is normalized
    through AuthoritySourceScope without carrying any verification flags from the
    diagnostic payload.

    The regulation profile and authority scope are bound through the common
    RegulationAuthorityRequirement boundary. The profile's declared source-policy
    requirements are separately bound through RegulationSourcePolicyRequirement
    using only explicit verified requirement facts. Profile presence, matching names,
    contract readiness, and descriptive diagnostics remain non-dispositive.

    This adapter does not verify history completeness. Provenance verification is
    taken only from the common provenance policy result. Therefore current source-
    policy requirements remain fail-closed and unsatisfied.

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

    source_uri = _first_text(
        checks,
        "source_uri",
        "source_url",
        "announcement_url",
        "document_url",
    ) or _first_text(
        previous_payload,
        "source_uri",
        "source_url",
        "announcement_url",
        "document_url",
    )
    region_binding = _first_text(
        checks,
        "region_binding",
        "region",
        "jurisdiction",
    ) or _first_text(
        previous_payload,
        "region_binding",
        "region",
        "jurisdiction",
    )
    source_role = _first_text(checks, "source_role") or _first_text(
        previous_payload,
        "source_role",
    )
    legal_authority_scope = _first_text(
        checks,
        "legal_authority_scope",
        "authority_scope",
    ) or _first_text(
        previous_payload,
        "legal_authority_scope",
        "authority_scope",
    )

    authority_scope = normalize_authority_source_scope(
        {
            "source_uri": source_uri,
            "region_binding": region_binding,
            "source_role": source_role,
            "legal_authority_scope": legal_authority_scope,
            "target_regulation": CONDITION_NAME,
            "diagnostics": {
                "candidate_hit": candidate_hit,
                "title_match": title_match,
                "source_url_present": source_url_present,
                "archive_candidate_present": archive_candidate_present,
                "dispositive": False,
            },
        }
    )

    profile = get_regulation_resolution_profile(CONDITION_NAME)
    authority_requirement = evaluate_regulation_authority_requirement(
        profile,
        authority_scope,
    )

    evidence = HistoricalSiteEventProvenanceEvidence(
        source_authority_identity_verified=(
            authority_requirement.authority_requirement_satisfied
        ),
        source_role_explicit=authority_scope.source_role_verified,
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

    source_policy_requirement_facts = {
        "HISTORY COMPLETENESS VERIFIED": False,
        "PROVENANCE VERIFIED": policy.get("provenance_policy_verified") is True,
    }
    source_policy_requirement = evaluate_regulation_source_policy_requirement(
        profile,
        source_policy_requirement_facts,
    )

    return {
        "condition": CONDITION_NAME,
        "adapter_mode": ADAPTER_MODE,
        "resolution_profile": profile.to_dict() if profile is not None else None,
        "authority_source_scope": authority_scope.to_dict(),
        "regulation_authority_requirement": authority_requirement.to_dict(),
        "provenance_policy": policy,
        "regulation_source_policy_requirement": source_policy_requirement.to_dict(),
        "semantic_contract": {
            "diagnostic_provenance_present_does_not_mean_gate_verified": True,
            "descriptive_authority_metadata_does_not_mean_authority_verified": True,
            "official_looking_host_does_not_mean_competent_authority": True,
            "source_role_value_does_not_mean_source_role_verified": True,
            "profile_presence_does_not_mean_authority_requirement_satisfied": True,
            "profile_name_match_does_not_mean_authority_verified": True,
            "authority_scope_binding_does_not_mean_legal_evidence_verified": True,
            "authority_requirement_binding_does_not_mean_legal_evidence_verified": True,
            "source_policy_requirement_declaration_does_not_mean_verified": True,
            "profile_source_policy_verified_does_not_supply_requirement_facts": True,
            "contract_readiness_does_not_supply_requirement_facts": True,
            "history_completeness_not_verified_by_this_adapter": True,
            "provenance_requirement_uses_common_policy_result_only": True,
            "source_policy_requirement_satisfaction_does_not_mean_legal_resolution": True,
            "original_diagnostics_do_not_mean_complete_production_provenance": True,
            "policy_binding_does_not_mean_provenance_policy_verified": True,
            "provenance_policy_verified_does_not_mean_legal_evidence_verified": True,
        },
        "condition_specific_blockers": {
            "profile_missing": profile is None,
            "authority_requirement_unsatisfied": (
                not authority_requirement.authority_requirement_satisfied
            ),
            "source_policy_requirement_unsatisfied": (
                not source_policy_requirement.source_policy_requirement_satisfied
            ),
            "history_completeness_unverified": True,
            "provenance_policy_unverified": (
                policy.get("provenance_policy_verified") is not True
            ),
            "authority_chain_unverified": not authority_scope.authority_chain_verified,
            "source_authority_identity_unverified": (
                not authority_requirement.authority_requirement_satisfied
            ),
            "source_role_unverified": not authority_scope.source_role_verified,
            "document_identity_traceability_unverified": True,
            "original_document_traceability_unverified": True,
            "site_applicability_traceability_unverified": True,
            "temporal_relation_traceability_unverified": True,
        },
        "promotion_guards": {
            "candidate_promoted_to_provenance": False,
            "notice_identity_promoted_to_provenance": False,
            "profile_presence_promoted_to_authority_verification": False,
            "profile_name_match_promoted_to_authority_verification": False,
            "official_host_promoted_to_competent_authority": False,
            "source_role_metadata_promoted_to_verified_role": False,
            "authority_metadata_promoted_to_legal_evidence": False,
            "authority_requirement_promoted_to_legal_resolution": False,
            "source_policy_requirement_promoted_to_verified_evidence": False,
            "source_policy_requirement_promoted_to_legal_resolution": False,
            "contract_readiness_promoted_to_source_policy_verification": False,
            "current_geometry_promoted_to_historical_site_provenance": False,
            "archive_candidate_promoted_to_original_traceability": False,
            "provenance_promoted_to_legal_resolution": False,
        },
        "output_written": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
    }
