from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


POLICY_NAME = "HISTORICAL_SITE_EVENT_PROVENANCE_POLICY"


@dataclass(frozen=True)
class HistoricalSiteEventProvenanceEvidence:
    """Positive-proof-only provenance contract for HISTORICAL_SITE_EVENT.

    Provenance verification describes whether already-verified historical evidence
    can be traced back through authoritative sources and its legal/SITE/temporal
    roles. It does not itself verify a qualifying event, prove historical absence,
    resolve SITE applicability, or mutate production state.
    """

    source_authority_identity_verified: bool = False
    source_role_explicit: bool = False
    document_identity_traceable: bool = False
    original_document_traceable: bool = False
    site_applicability_traceable: bool = False
    temporal_relation_traceable: bool = False

    @property
    def provenance_policy_verified(self) -> bool:
        return (
            self.source_authority_identity_verified
            and self.source_role_explicit
            and self.document_identity_traceable
            and self.original_document_traceable
            and self.site_applicability_traceable
            and self.temporal_relation_traceable
        )


def evaluate_historical_site_event_provenance_policy(
    evidence: HistoricalSiteEventProvenanceEvidence,
    *,
    candidate_hit: bool | None = None,
    title_match: bool | None = None,
    http_200: bool | None = None,
    source_url_present: bool | None = None,
    archive_candidate_present: bool | None = None,
    diagnostic_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate provenance readiness without manufacturing legal evidence.

    Discovery and transport signals are diagnostic only. In particular, the
    presence of a candidate, matching title, HTTP success, URL, or archive candidate
    cannot promote any provenance gate to verified status.
    """

    gates = {
        "source_authority_identity_verified": (
            evidence.source_authority_identity_verified
        ),
        "source_role_explicit": evidence.source_role_explicit,
        "document_identity_traceable": evidence.document_identity_traceable,
        "original_document_traceable": evidence.original_document_traceable,
        "site_applicability_traceable": evidence.site_applicability_traceable,
        "temporal_relation_traceable": evidence.temporal_relation_traceable,
    }

    verified = evidence.provenance_policy_verified

    return {
        "policy": POLICY_NAME,
        "gates": gates,
        "verified_gate_count": sum(1 for value in gates.values() if value),
        "required_gate_count": len(gates),
        "missing_gates": [name for name, passed in gates.items() if not passed],
        "provenance_policy_verified": verified,
        "provenance_state": "VERIFIED" if verified else "BLOCKED",
        "promotion_guards": {
            "candidate_promoted_to_authority_identity": False,
            "title_promoted_to_document_identity": False,
            "http_200_promoted_to_authority_identity": False,
            "source_url_promoted_to_source_role": False,
            "archive_candidate_promoted_to_original_traceability": False,
            "provenance_promoted_to_verified_event_identity": False,
            "provenance_promoted_to_site_applicability": False,
            "provenance_promoted_to_temporal_relation": False,
            "provenance_promoted_to_history_completeness": False,
        },
        "negative_evidence_inference_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_promotion_applied": False,
        "production_wiring_applied": False,
        "overlay_mutated": False,
        "runtime_registry_mutated": False,
        "diagnostics": {
            "candidate_hit": candidate_hit,
            "title_match": title_match,
            "http_200": http_200,
            "source_url_present": source_url_present,
            "archive_candidate_present": archive_candidate_present,
            "diagnostic_evidence": dict(diagnostic_evidence or {}),
            "dispositive": False,
        },
    }
