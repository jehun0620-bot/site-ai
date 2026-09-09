from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_orchestrator import (
    HybridSpatialNoticeStageResults,
    orchestrate_hybrid_spatial_notice,
)


TARGET_NAME = "개발밀도관리구역"
STANDARD_CODE = "UQQ700"


@dataclass(frozen=True)
class Uqq700ProductionAdapterInput:
    """Explicit verified stage outputs for the UQQ700 production boundary.

    This adapter does not discover evidence and does not infer legal facts. It only
    forwards explicit generalized stage results to the common orchestrator/kernel.
    Missing or non-True gate values remain unverified.
    """

    authority: Mapping[str, Any] | None = None
    historical_candidate: Mapping[str, Any] | None = None
    designation_identity: Mapping[str, Any] | None = None
    current_validity: Mapping[str, Any] | None = None
    site_spatial_inclusion: Mapping[str, Any] | None = None


def adapt_uqq700_production_state(
    adapter_input: Uqq700ProductionAdapterInput,
    *,
    search_hit: bool | None = None,
    http_200: bool | None = None,
    negative_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed UQQ700 compatibility view without production mutation.

    The generalized orchestrator owns the three positive gate semantics. Discovery
    diagnostics are forwarded only so the safety kernel can preserve them as
    non-dispositive context. Even when all three gates are positively verified,
    this adapter only exposes runtime registration eligibility; it never promotes
    SITE TRUE/FALSE and never infers legal absence.
    """

    orchestrated = orchestrate_hybrid_spatial_notice(
        HybridSpatialNoticeStageResults(
            authority=adapter_input.authority,
            historical_candidate=adapter_input.historical_candidate,
            designation_identity=adapter_input.designation_identity,
            current_validity=adapter_input.current_validity,
            site_spatial_inclusion=adapter_input.site_spatial_inclusion,
        ),
        search_hit=search_hit,
        http_200=http_200,
        negative_evidence=negative_evidence,
    )

    return {
        "target": TARGET_NAME,
        "standard_code": STANDARD_CODE,
        **orchestrated,
        "site_true_inference_allowed": False,
        "production_wiring_applied": False,
        "runtime_registry_mutated": False,
    }
