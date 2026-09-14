from __future__ import annotations

from dataclasses import dataclass
from typing import Any


BOUNDARY_NAME = "HISTORICAL_SITE_EVENT_QUALIFICATION"


def _is_explicit_true(value: Any) -> bool:
    """Accept only the literal boolean True as positive verification."""

    return value is True


@dataclass(frozen=True)
class HistoricalSiteEventQualificationEvidence:
    """Positive-proof-only evidence for qualifying a historical SITE event.

    This boundary evaluates three substantive facts that must already have been
    independently verified:

    1. historical event identity,
    2. historical SITE applicability, and
    3. temporal relation to the SITE/regulation question.

    It does not discover sources, infer legal absence from no-hit results,
    evaluate provenance or history completeness, resolve the final regulation
    state, mutate SITE state, or register anything into production/runtime.
    """

    historical_event_identity_verified: Any = False
    historical_site_applicability_verified: Any = False
    temporal_relation_verified: Any = False


@dataclass(frozen=True)
class HistoricalSiteEventQualificationAssessment:
    boundary: str
    historical_event_identity_verified: bool
    historical_site_applicability_verified: bool
    temporal_relation_verified: bool
    verified_gate_count: int
    required_gate_count: int
    missing_gates: tuple[str, ...]
    qualifying_historical_event_verified: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary": self.boundary,
            "historical_event_identity_verified": (
                self.historical_event_identity_verified
            ),
            "historical_site_applicability_verified": (
                self.historical_site_applicability_verified
            ),
            "temporal_relation_verified": self.temporal_relation_verified,
            "verified_gate_count": self.verified_gate_count,
            "required_gate_count": self.required_gate_count,
            "missing_gates": list(self.missing_gates),
            "qualifying_historical_event_verified": (
                self.qualifying_historical_event_verified
            ),
            "negative_evidence_inference_allowed": False,
            "legal_absence_inference_allowed": False,
            "final_regulation_resolution_applied": False,
            "site_state_mutated": False,
            "production_wiring_applied": False,
            "runtime_registry_mutated": False,
        }


def evaluate_historical_site_event_qualification(
    evidence: HistoricalSiteEventQualificationEvidence | None,
) -> HistoricalSiteEventQualificationAssessment:
    """Evaluate the substantive historical-event qualification boundary.

    Verification is fail-closed. Only exact boolean ``True`` values satisfy a
    gate. Candidate discovery, title/region/date matches, provenance readiness,
    history completeness, current geometry, contract readiness, or other
    diagnostic signals are not accepted as substitutes for these three facts.
    """

    evidence = evidence or HistoricalSiteEventQualificationEvidence()

    gates = {
        "historical_event_identity_verified": _is_explicit_true(
            evidence.historical_event_identity_verified
        ),
        "historical_site_applicability_verified": _is_explicit_true(
            evidence.historical_site_applicability_verified
        ),
        "temporal_relation_verified": _is_explicit_true(
            evidence.temporal_relation_verified
        ),
    }

    missing_gates = tuple(name for name, passed in gates.items() if not passed)
    qualifying_historical_event_verified = not missing_gates

    return HistoricalSiteEventQualificationAssessment(
        boundary=BOUNDARY_NAME,
        historical_event_identity_verified=gates[
            "historical_event_identity_verified"
        ],
        historical_site_applicability_verified=gates[
            "historical_site_applicability_verified"
        ],
        temporal_relation_verified=gates["temporal_relation_verified"],
        verified_gate_count=sum(1 for passed in gates.values() if passed),
        required_gate_count=len(gates),
        missing_gates=missing_gates,
        qualifying_historical_event_verified=qualifying_historical_event_verified,
    )
