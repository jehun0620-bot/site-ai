from __future__ import annotations

from typing import Any, Mapping

from law_data.production_site_condition import (
    ProductionSiteCondition,
    normalize_production_site_condition,
)


ADAPTER_NAME = "PRODUCTION_SPATIAL_CONDITION_ADAPTER"
RUNTIME_SOURCE_MARKER = "RUNTIME_SPATIAL_CONDITION"


def adapt_spatial_condition_to_production_contract(
    raw_condition: Mapping[str, Any] | None,
    *,
    production_eligible: bool = False,
    runtime_registered: bool = False,
) -> ProductionSiteCondition:
    """Normalize an existing spatial evaluator result for production consumption.

    This adapter is deliberately non-dispositive. It preserves the evaluator's
    state/confidence/resolution/provenance and delegates malformed-state fail-closed
    handling to the common production condition normalizer.

    It does not:
    - re-evaluate query or geometry evidence,
    - infer verified-empty semantics,
    - promote UNKNOWN to FALSE/TRUE,
    - infer production eligibility,
    - infer runtime registration,
    - mutate SITE or Rule Engine state.
    """

    raw = dict(raw_condition or {})

    runtime_source = raw.get("source")
    if not isinstance(runtime_source, Mapping):
        runtime_source = {}

    evaluation = raw.get("evaluation")
    if not isinstance(evaluation, Mapping):
        evaluation = {}

    evidence = raw.get("evidence")
    if not isinstance(evidence, Mapping):
        evidence = {}

    provenance = {
        "adapter": ADAPTER_NAME,
        "pnu": raw.get("pnu"),
        "geometry_verified": raw.get("geometry_verified"),
        "resolution": raw.get("resolution"),
        "runtime_source": dict(runtime_source),
    }

    diagnostics = {
        "evaluation": dict(evaluation),
        "evidence": dict(evidence),
    }

    return normalize_production_site_condition(
        name=str(raw.get("name") or "").strip(),
        condition_type="SITE",
        resolution_type="SPATIAL",
        state=raw.get("state"),
        confidence=raw.get("confidence"),
        source=RUNTIME_SOURCE_MARKER,
        provenance=provenance,
        production_eligible=production_eligible,
        runtime_registered=runtime_registered,
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        diagnostics=diagnostics,
    )
