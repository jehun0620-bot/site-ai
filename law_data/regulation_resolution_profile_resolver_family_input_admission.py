"""Fail-closed input admission for a provenance-verified resolver-family plan.

This boundary checks that the supplied STEP106 dispatch plan is reproducible from
its exact STEP101 provenance artifacts and that the family-specific input object
belongs to that plan. It never executes a resolver, selects a callable, derives
standard code, decides SITE truth, or grants production/runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .historical_site_event_resolver import HistoricalSiteEventEvidenceState
from .hybrid_spatial_notice_orchestrator import HybridSpatialNoticeStageResults
from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    RegulationResolutionProfileResolverFamilyDispatchPlan,
    build_resolver_family_dispatch_plan,
)

ADMITTED = "ADMITTED"
REJECTED = "REJECTED"

HISTORICAL_SITE_EVENT = "HISTORICAL_SITE_EVENT"
HYBRID_SPATIAL_NOTICE = "HYBRID_SPATIAL_NOTICE"


@dataclass(frozen=True)
class RegulationResolutionProfileResolverFamilyInputAdmissionResult:
    status: str
    resolver_family: str | None
    input_type: str | None
    dispatch_plan_verified: bool
    family_input_matches: bool
    standard_code_used: bool = False
    resolver_callable_selected: bool = False
    resolver_execution_allowed: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def admitted(self) -> bool:
        return (
            self.status == ADMITTED
            and self.resolver_family in {
                HISTORICAL_SITE_EVENT,
                HYBRID_SPATIAL_NOTICE,
            }
            and self.input_type is not None
            and self.dispatch_plan_verified
            and self.family_input_matches
            and self.standard_code_used is False
            and self.resolver_callable_selected is False
            and self.resolver_execution_allowed is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _reject() -> RegulationResolutionProfileResolverFamilyInputAdmissionResult:
    return RegulationResolutionProfileResolverFamilyInputAdmissionResult(
        status=REJECTED,
        resolver_family=None,
        input_type=None,
        dispatch_plan_verified=False,
        family_input_matches=False,
    )


def admit_resolver_family_input(
    dispatch_plan: RegulationResolutionProfileResolverFamilyDispatchPlan,
    resolver_input: Any,
    *,
    admitted_profile: RegulationResolutionProfile | None = None,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileResolverFamilyInputAdmissionResult:
    """Admit exact family input only after reproducing the STEP106 plan.

    A caller-constructed plan, even one whose fields make ``planned`` true, is
    insufficient. The plan must equal the plan rebuilt from the exact admitted
    profile and STEP101 seed/evidence/verification chain.
    """
    if not isinstance(dispatch_plan, RegulationResolutionProfileResolverFamilyDispatchPlan):
        return _reject()
    if not isinstance(admitted_profile, RegulationResolutionProfile):
        return _reject()

    expected_plan = build_resolver_family_dispatch_plan(
        admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    if not expected_plan.planned or dispatch_plan != expected_plan:
        return _reject()

    family = dispatch_plan.resolver_family
    if family == HISTORICAL_SITE_EVENT:
        matches = type(resolver_input) is HistoricalSiteEventEvidenceState
    elif family == HYBRID_SPATIAL_NOTICE:
        matches = type(resolver_input) is HybridSpatialNoticeStageResults
    else:
        return _reject()

    if not matches:
        return RegulationResolutionProfileResolverFamilyInputAdmissionResult(
            status=REJECTED,
            resolver_family=family,
            input_type=type(resolver_input).__name__,
            dispatch_plan_verified=True,
            family_input_matches=False,
        )

    return RegulationResolutionProfileResolverFamilyInputAdmissionResult(
        status=ADMITTED,
        resolver_family=family,
        input_type=type(resolver_input).__name__,
        dispatch_plan_verified=True,
        family_input_matches=True,
        standard_code_used=False,
        resolver_callable_selected=False,
        resolver_execution_allowed=False,
        site_truth_decision_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
