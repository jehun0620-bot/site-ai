"""Provenance-bound execution boundary for admitted resolver-family inputs.

This module is the narrow bridge from STEP108 input admission to the existing
family-specific resolver functions. It does not promote resolver output to SITE
truth and does not grant production or runtime registration authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .historical_site_event_resolver import (
    HistoricalSiteEventEvidenceState,
    resolve_historical_site_event,
)
from .hybrid_spatial_notice_orchestrator import (
    HybridSpatialNoticeStageResults,
    orchestrate_hybrid_spatial_notice,
)
from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    RegulationResolutionProfileResolverFamilyDispatchPlan,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
    admit_resolver_family_input,
)

EXECUTED = "EXECUTED"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class RegulationResolutionProfileResolverFamilyExecutionResult:
    status: str
    resolver_family: str | None
    input_admission_verified: bool
    resolver_executed: bool
    resolver_output: dict[str, Any] | None
    standard_code_used: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def executed(self) -> bool:
        return (
            self.status == EXECUTED
            and self.resolver_family in {
                HISTORICAL_SITE_EVENT,
                HYBRID_SPATIAL_NOTICE,
            }
            and self.input_admission_verified
            and self.resolver_executed
            and isinstance(self.resolver_output, dict)
            and self.standard_code_used is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _reject() -> RegulationResolutionProfileResolverFamilyExecutionResult:
    return RegulationResolutionProfileResolverFamilyExecutionResult(
        status=REJECTED,
        resolver_family=None,
        input_admission_verified=False,
        resolver_executed=False,
        resolver_output=None,
    )


def execute_admitted_resolver_family(
    dispatch_plan: RegulationResolutionProfileResolverFamilyDispatchPlan,
    resolver_input: Any,
    *,
    admitted_profile: RegulationResolutionProfile | None = None,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileResolverFamilyExecutionResult:
    """Execute only after STEP108 reproduces and admits the exact provenance chain."""
    admission = admit_resolver_family_input(
        dispatch_plan,
        resolver_input,
        admitted_profile=admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    if not admission.admitted:
        return _reject()

    if admission.resolver_family == HISTORICAL_SITE_EVENT:
        if type(resolver_input) is not HistoricalSiteEventEvidenceState:
            return _reject()
        output = resolve_historical_site_event(resolver_input)
    elif admission.resolver_family == HYBRID_SPATIAL_NOTICE:
        if type(resolver_input) is not HybridSpatialNoticeStageResults:
            return _reject()
        output = orchestrate_hybrid_spatial_notice(resolver_input)
    else:
        return _reject()

    return RegulationResolutionProfileResolverFamilyExecutionResult(
        status=EXECUTED,
        resolver_family=admission.resolver_family,
        input_admission_verified=True,
        resolver_executed=True,
        resolver_output=output,
        standard_code_used=False,
        site_truth_decision_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
