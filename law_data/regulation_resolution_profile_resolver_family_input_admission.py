"""Fail-closed input admission for a verified resolver-family dispatch plan.

This boundary checks only that a STEP106 dispatch plan and a family-specific input
object belong together. It never executes a resolver, selects a callable, derives
standard code, decides SITE truth, or grants production/runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .historical_site_event_resolver import HistoricalSiteEventEvidenceState
from .hybrid_spatial_notice_orchestrator import HybridSpatialNoticeStageResults
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    RegulationResolutionProfileResolverFamilyDispatchPlan,
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
) -> RegulationResolutionProfileResolverFamilyInputAdmissionResult:
    """Admit only the exact input class required by the verified family plan."""
    if not isinstance(
        dispatch_plan,
        RegulationResolutionProfileResolverFamilyDispatchPlan,
    ):
        return _reject()

    if not dispatch_plan.planned:
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
