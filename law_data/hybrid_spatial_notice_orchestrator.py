from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from hybrid_spatial_notice_resolver import (
    HybridSpatialNoticeGateState,
    resolve_hybrid_spatial_notice,
)


@dataclass(frozen=True)
class HybridSpatialNoticeStageResults:
    authority: Mapping[str, Any] | None = None
    historical_candidate: Mapping[str, Any] | None = None
    designation_identity: Mapping[str, Any] | None = None
    current_validity: Mapping[str, Any] | None = None
    site_spatial_inclusion: Mapping[str, Any] | None = None


def _is_true(mapping: Mapping[str, Any] | None, key: str) -> bool:
    return bool(mapping and mapping.get(key) is True)


def orchestrate_hybrid_spatial_notice(
    stages: HybridSpatialNoticeStageResults,
    *,
    search_hit: bool | None = None,
    http_200: bool | None = None,
    negative_evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Compose stage outputs without independently promoting any positive gate.

    The orchestrator is intentionally passive: it only reads explicit positive-gate
    booleans produced by upstream verification stages and delegates final gate logic
    to the common HYBRID_SPATIAL_NOTICE safety kernel. Diagnostic discovery evidence
    remains non-dispositive.
    """

    identity_verified = _is_true(
        stages.designation_identity,
        "official_designation_identity_verified",
    )
    validity_verified = _is_true(
        stages.current_validity,
        "current_validity_verified",
    )
    spatial_verified = _is_true(
        stages.site_spatial_inclusion,
        "site_spatial_inclusion_verified",
    )

    kernel = resolve_hybrid_spatial_notice(
        HybridSpatialNoticeGateState(
            official_designation_identity_verified=identity_verified,
            current_validity_verified=validity_verified,
            site_spatial_inclusion_verified=spatial_verified,
        ),
        search_hit=search_hit,
        http_200=http_200,
        negative_evidence=negative_evidence,
    )

    return {
        **kernel,
        "stage_results": {
            "authority": dict(stages.authority or {}),
            "historical_candidate": dict(stages.historical_candidate or {}),
            "designation_identity": dict(stages.designation_identity or {}),
            "current_validity": dict(stages.current_validity or {}),
            "site_spatial_inclusion": dict(stages.site_spatial_inclusion or {}),
        },
    }
