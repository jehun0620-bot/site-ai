"""Fail-closed dispatch planning for verified resolver-family eligibility.

A dispatch plan is descriptive only. It says which already-verified resolver
family may be considered by a later, separately authorized execution boundary.
This module never imports or executes a resolver, builds resolver input, decides
SITE truth, or grants production/runtime authority.
"""

from __future__ import annotations

from dataclasses import dataclass

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_resolver_family_eligibility import (
    evaluate_resolver_family_eligibility,
)

PLANNED = "PLANNED"
REJECTED = "REJECTED"

SUPPORTED_RESOLVER_FAMILIES = frozenset(
    {
        "HYBRID_SPATIAL_NOTICE",
        "HISTORICAL_SITE_EVENT",
    }
)


@dataclass(frozen=True)
class RegulationResolutionProfileResolverFamilyDispatchPlan:
    """Descriptive family plan only; never an execution or authorization token."""

    status: str
    resolver_family: str | None
    classification_compatible: bool
    standard_code_used: bool = False
    resolver_callable_selected: bool = False
    resolver_input_built: bool = False
    resolver_execution_allowed: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def planned(self) -> bool:
        return (
            self.status == PLANNED
            and self.classification_compatible
            and self.resolver_family in SUPPORTED_RESOLVER_FAMILIES
            and self.standard_code_used is False
            and self.resolver_callable_selected is False
            and self.resolver_input_built is False
            and self.resolver_execution_allowed is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def build_resolver_family_dispatch_plan(
    admitted_profile: RegulationResolutionProfile,
    *,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileResolverFamilyDispatchPlan:
    """Build a non-executable plan only after STEP104 provenance is rechecked.

    The exact STEP101 seed/evidence/verification artifacts are propagated into
    STEP104 and therefore STEP103. Profile-only or cross-artifact calls fail
    closed. The family never comes from standard_code, registry inference, or
    caller metadata.
    """
    eligibility = evaluate_resolver_family_eligibility(
        admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    if not eligibility.eligible:
        return RegulationResolutionProfileResolverFamilyDispatchPlan(
            status=REJECTED,
            resolver_family=None,
            classification_compatible=False,
        )

    if eligibility.resolver_family not in SUPPORTED_RESOLVER_FAMILIES:
        return RegulationResolutionProfileResolverFamilyDispatchPlan(
            status=REJECTED,
            resolver_family=None,
            classification_compatible=eligibility.classification_compatible,
        )

    return RegulationResolutionProfileResolverFamilyDispatchPlan(
        status=PLANNED,
        resolver_family=eligibility.resolver_family,
        classification_compatible=True,
        standard_code_used=False,
        resolver_callable_selected=False,
        resolver_input_built=False,
        resolver_execution_allowed=False,
        site_truth_decision_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
