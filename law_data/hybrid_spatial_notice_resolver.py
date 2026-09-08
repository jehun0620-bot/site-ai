from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"
UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class HybridSpatialNoticeGateState:
    """Positive verification state for HYBRID_SPATIAL_NOTICE runtime registration.

    A False value means "not positively verified". It must never be interpreted as
    legal absence, SITE FALSE, or a negative designation finding.
    """

    official_designation_identity_verified: bool = False
    current_validity_verified: bool = False
    site_spatial_inclusion_verified: bool = False

    @property
    def minimum_registration_gate_satisfied(self) -> bool:
        return (
            self.official_designation_identity_verified
            and self.current_validity_verified
            and self.site_spatial_inclusion_verified
        )

    @property
    def runtime_registration_allowed(self) -> bool:
        return self.minimum_registration_gate_satisfied


def resolve_hybrid_spatial_notice(
    gate_state: HybridSpatialNoticeGateState,
    *,
    search_hit: bool | None = None,
    http_200: bool | None = None,
    negative_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return the common fail-closed HYBRID_SPATIAL_NOTICE safety contract.

    Discovery signals such as search hits, HTTP success, no-hit, non-display, or
    other negative evidence are diagnostic only. They do not satisfy any positive
    registration gate and cannot establish legal absence or SITE FALSE.
    """

    minimum_gate = gate_state.minimum_registration_gate_satisfied

    return {
        "resolution_type": RESOLUTION_TYPE,
        "resolution": UNKNOWN,
        "positive_gates": {
            "official_designation_identity_verified": (
                gate_state.official_designation_identity_verified
            ),
            "current_validity_verified": gate_state.current_validity_verified,
            "site_spatial_inclusion_verified": (
                gate_state.site_spatial_inclusion_verified
            ),
        },
        "minimum_registration_gate_satisfied": minimum_gate,
        "runtime_registration_allowed": minimum_gate,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "diagnostic_discovery": {
            "search_hit": search_hit,
            "http_200": http_200,
            "negative_evidence": dict(negative_evidence or {}),
            "dispositive": False,
        },
    }
