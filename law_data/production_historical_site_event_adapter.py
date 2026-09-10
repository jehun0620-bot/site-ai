from __future__ import annotations

from typing import Any, Mapping

from law_data.production_site_condition import (
    FALSE,
    UNKNOWN,
    ProductionSiteCondition,
    normalize_production_site_condition,
)


ADAPTER_NAME = "PRODUCTION_HISTORICAL_SITE_EVENT_ADAPTER"
RESOLUTION_TYPE = "HISTORICAL_SITE_EVENT"
TRUE_CANDIDATE = "TRUE_CANDIDATE"


def adapt_historical_site_event_to_production_contract(
    *,
    name: str,
    resolver_result: Mapping[str, Any] | None,
    confidence: Any = "NONE",
    source: Any = "",
    provenance: Mapping[str, Any] | None = None,
    production_eligible: bool = False,
    runtime_registered: bool = False,
) -> ProductionSiteCondition:
    """Normalize a HISTORICAL_SITE_EVENT result for production consumption.

    Safety rules:
    - TRUE_CANDIDATE is never promoted to production TRUE here.
    - FALSE is preserved only when exhaustive_disproof_verified is explicitly True.
    - UNKNOWN and malformed/missing resolutions fail closed to UNKNOWN.
    - production eligibility and runtime registration are explicit independent gates.
    - no negative-evidence, legal-absence, or SITE-promotion permission is inferred.
    """

    raw = dict(resolver_result or {})
    raw_resolution = str(raw.get("resolution") or "").strip().upper()
    exhaustive_disproof_verified = raw.get("exhaustive_disproof_verified") is True

    if raw_resolution == FALSE and exhaustive_disproof_verified:
        production_state = FALSE
    else:
        production_state = UNKNOWN

    evidence_state = raw.get("evidence_state")
    if not isinstance(evidence_state, Mapping):
        evidence_state = {}

    diagnostic_discovery = raw.get("diagnostic_discovery")
    if not isinstance(diagnostic_discovery, Mapping):
        diagnostic_discovery = {}

    normalized_provenance = dict(provenance or {})
    normalized_provenance.update(
        {
            "adapter": ADAPTER_NAME,
            "resolver_resolution_type": raw.get("resolution_type"),
            "resolver_resolution": raw.get("resolution"),
            "resolution_basis": raw.get("resolution_basis"),
            "exhaustive_disproof_verified": exhaustive_disproof_verified,
        }
    )

    diagnostics = {
        "evidence_state": dict(evidence_state),
        "diagnostic_discovery": dict(diagnostic_discovery),
        "generic_negative_inference_allowed": raw.get(
            "generic_negative_inference_allowed"
        ),
        "legal_absence_inference_from_discovery_allowed": raw.get(
            "legal_absence_inference_from_discovery_allowed"
        ),
        "automatic_true_promotion_allowed": raw.get(
            "automatic_true_promotion_allowed"
        ),
        "production_wiring_applied": raw.get("production_wiring_applied"),
        "runtime_registry_mutated": raw.get("runtime_registry_mutated"),
    }

    return normalize_production_site_condition(
        name=name,
        condition_type="SITE_HISTORY",
        resolution_type=RESOLUTION_TYPE,
        state=production_state,
        confidence=confidence,
        source=source,
        provenance=normalized_provenance,
        production_eligible=production_eligible,
        runtime_registered=runtime_registered,
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        diagnostics=diagnostics,
    )
