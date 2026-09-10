from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


CONTRACT_NAME = "PRODUCTION_SITE_CONDITION"

TRUE = "TRUE"
FALSE = "FALSE"
UNKNOWN = "UNKNOWN"

VALID_STATES = frozenset({TRUE, FALSE, UNKNOWN})
VALID_CONDITION_TYPES = frozenset({"SITE", "SITE_HISTORY"})
VALID_RESOLUTION_TYPES = frozenset(
    {
        "SNAPSHOT",
        "SPATIAL",
        "HYBRID_SPATIAL_NOTICE",
        "HISTORICAL_SITE_EVENT",
    }
)


@dataclass(frozen=True)
class ProductionSiteCondition:
    """Production-facing SITE condition contract.

    This object is a normalization boundary only. It does not register a runtime
    resolver, mutate SITE state, apply an overlay, or promote UNKNOWN to TRUE/FALSE.

    `state` is the dispositive Rule Engine input. The remaining fields preserve
    production eligibility, provenance, and safety metadata so that richer
    resolver/runtime semantics are not discarded before Rule Engine evaluation.
    """

    name: str
    condition_type: str
    resolution_type: str
    state: str = UNKNOWN
    confidence: str = "NONE"
    source: str = ""
    provenance: Mapping[str, Any] = field(default_factory=dict)
    production_eligible: bool = False
    runtime_registered: bool = False
    negative_evidence_allowed: bool = False
    legal_absence_inference_allowed: bool = False
    site_promotion_allowed: bool = False
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.name).strip():
            raise ValueError("condition name is required")

        if self.condition_type not in VALID_CONDITION_TYPES:
            raise ValueError(
                f"unsupported condition_type: {self.condition_type!r}"
            )

        if self.resolution_type not in VALID_RESOLUTION_TYPES:
            raise ValueError(
                f"unsupported resolution_type: {self.resolution_type!r}"
            )

        if self.state not in VALID_STATES:
            raise ValueError(f"unsupported state: {self.state!r}")

        if self.condition_type == "SITE_HISTORY" and self.resolution_type == "SPATIAL":
            raise ValueError(
                "SITE_HISTORY cannot use SPATIAL resolution_type; historical semantics "
                "must not be registered through the spatial runtime contract"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": CONTRACT_NAME,
            "name": self.name,
            "condition_type": self.condition_type,
            "resolution_type": self.resolution_type,
            "state": self.state,
            "confidence": self.confidence,
            "source": self.source,
            "provenance": dict(self.provenance),
            "production_eligible": self.production_eligible,
            "runtime_registered": self.runtime_registered,
            "negative_evidence_allowed": self.negative_evidence_allowed,
            "legal_absence_inference_allowed": self.legal_absence_inference_allowed,
            "site_promotion_allowed": self.site_promotion_allowed,
            "diagnostics": dict(self.diagnostics),
        }


def normalize_production_site_condition(
    *,
    name: str,
    condition_type: str,
    resolution_type: str,
    state: Any = UNKNOWN,
    confidence: Any = "NONE",
    source: Any = "",
    provenance: Mapping[str, Any] | None = None,
    production_eligible: bool = False,
    runtime_registered: bool = False,
    negative_evidence_allowed: bool = False,
    legal_absence_inference_allowed: bool = False,
    site_promotion_allowed: bool = False,
    diagnostics: Mapping[str, Any] | None = None,
) -> ProductionSiteCondition:
    """Normalize a condition without manufacturing positive/negative legal state.

    Unknown, missing, malformed, or unsupported runtime/resolver states fail closed
    to UNKNOWN. Production eligibility and runtime registration are never inferred
    from state, confidence, source, diagnostics, or resolver implementation.
    """

    normalized_state = str(state or "").strip().upper()
    if normalized_state not in VALID_STATES:
        normalized_state = UNKNOWN

    normalized_confidence = str(confidence or "").strip().upper() or "NONE"
    normalized_source = str(source or "").strip()

    return ProductionSiteCondition(
        name=str(name).strip(),
        condition_type=str(condition_type).strip().upper(),
        resolution_type=str(resolution_type).strip().upper(),
        state=normalized_state,
        confidence=normalized_confidence,
        source=normalized_source,
        provenance=dict(provenance or {}),
        production_eligible=production_eligible is True,
        runtime_registered=runtime_registered is True,
        negative_evidence_allowed=negative_evidence_allowed is True,
        legal_absence_inference_allowed=legal_absence_inference_allowed is True,
        site_promotion_allowed=site_promotion_allowed is True,
        diagnostics=dict(diagnostics or {}),
    )


def rule_engine_condition_view(
    condition: ProductionSiteCondition,
) -> dict[str, Any]:
    """Return the minimal Rule Engine-facing condition view.

    Safety/provenance fields remain available on the production contract itself;
    this view deliberately exposes no implicit eligibility or registration logic.
    """

    return {
        "name": condition.name,
        "type": condition.condition_type,
        "state": condition.state,
        "confidence": condition.confidence,
        "source": condition.source,
    }
