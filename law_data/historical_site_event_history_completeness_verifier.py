from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HistoricalHistoryCompletenessEvidence:
    official_historical_source_set_verified: bool = False
    authority_time_scope_completeness_verified: bool = False
    required_original_documents_resolved: bool = False
    candidate_universe_exhaustively_enumerated: bool = False

    @property
    def history_scope_complete_verified(self) -> bool:
        return (
            self.official_historical_source_set_verified
            and self.authority_time_scope_completeness_verified
            and self.required_original_documents_resolved
            and self.candidate_universe_exhaustively_enumerated
        )


def verify_history_completeness(
    evidence: HistoricalHistoryCompletenessEvidence,
    *,
    search_no_hit: bool | None = None,
    http_200: bool | None = None,
    fetched_row_count: int | None = None,
    negative_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify global historical completeness using positive evidence only.

    Discovery success, no-hit, row counts, candidate exhaustion within one source,
    and other negative evidence are diagnostic only. They cannot manufacture any
    positive completeness gate.
    """

    return {
        "official_historical_source_set_verified": (
            evidence.official_historical_source_set_verified
        ),
        "authority_time_scope_completeness_verified": (
            evidence.authority_time_scope_completeness_verified
        ),
        "required_original_documents_resolved": (
            evidence.required_original_documents_resolved
        ),
        "candidate_universe_exhaustively_enumerated": (
            evidence.candidate_universe_exhaustively_enumerated
        ),
        "history_scope_complete_verified": (
            evidence.history_scope_complete_verified
        ),
        "positive_gate_count": sum(
            1
            for value in (
                evidence.official_historical_source_set_verified,
                evidence.authority_time_scope_completeness_verified,
                evidence.required_original_documents_resolved,
                evidence.candidate_universe_exhaustively_enumerated,
            )
            if value
        ),
        "generic_negative_inference_allowed": False,
        "legal_absence_inference_from_discovery_allowed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "diagnostic_discovery": {
            "search_no_hit": search_no_hit,
            "http_200": http_200,
            "fetched_row_count": fetched_row_count,
            "negative_evidence": dict(negative_evidence or {}),
            "dispositive": False,
        },
    }
