from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class HistoricalSiteEventPositiveEvidence:
    verified_event_identity: bool = False
    historical_site_applicability: bool = False
    temporal_relation_verified: bool = False

    @property
    def verified_qualifying_event_present(self) -> bool:
        return (
            self.verified_event_identity
            and self.historical_site_applicability
            and self.temporal_relation_verified
        )


def verify_historical_site_event_positive_evidence(
    evidence: HistoricalSiteEventPositiveEvidence,
    *,
    candidate_hit: bool | None = None,
    title_match: bool | None = None,
    http_200: bool | None = None,
    current_geometry_match: bool | None = None,
    official_archive_candidate_present: bool | None = None,
    diagnostic_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify the positive side of a historical SITE event contract.

    The three positive gates are conjunctive and must be established explicitly.
    Discovery and weak-match signals are diagnostics only and cannot manufacture a
    verified qualifying historical event.
    """

    return {
        "positive_evidence": {
            "verified_event_identity": evidence.verified_event_identity,
            "historical_site_applicability": evidence.historical_site_applicability,
            "temporal_relation_verified": evidence.temporal_relation_verified,
        },
        "positive_gate_count": sum(
            (
                evidence.verified_event_identity,
                evidence.historical_site_applicability,
                evidence.temporal_relation_verified,
            )
        ),
        "verified_qualifying_event_present": (
            evidence.verified_qualifying_event_present
        ),
        "candidate_discovery_promoted_to_verified_event": False,
        "title_match_promoted_to_verified_event": False,
        "http_200_promoted_to_verified_event": False,
        "current_geometry_promoted_to_historical_site_applicability": False,
        "archive_candidate_promoted_to_verified_event": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
        "diagnostics": {
            "candidate_hit": candidate_hit,
            "title_match": title_match,
            "http_200": http_200,
            "current_geometry_match": current_geometry_match,
            "official_archive_candidate_present": official_archive_candidate_present,
            "diagnostic_evidence": dict(diagnostic_evidence or {}),
            "dispositive": False,
        },
    }
