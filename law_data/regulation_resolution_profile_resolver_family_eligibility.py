"""Fail-closed resolver-family eligibility for verified classification profiles.

This boundary does not discover, import, select, or execute a resolver callable.
It only exposes the already-verified profile resolution_type as an eligible
family label after STEP103 registry compatibility is recomputed successfully.
Compatibility is recomputed from the supplied profile so no detached or stale
compatibility result can be reused for another profile.

Eligibility is not SITE truth, resolver execution authority, production
readiness, production registration, runtime registration, or SITE mutation.
Standard-code identity is outside this boundary and is never inferred or copied.
"""

from __future__ import annotations

from dataclasses import dataclass

from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry_classification_compatibility import (
    check_registry_classification_compatibility,
)

ELIGIBLE = "ELIGIBLE"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class RegulationResolutionProfileResolverFamilyEligibilityResult:
    """Descriptive family eligibility only; never an execution token."""

    status: str
    resolver_family: str | None
    classification_compatible: bool
    standard_code_used: bool = False
    resolver_execution_allowed: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def eligible(self) -> bool:
        return (
            self.status == ELIGIBLE
            and self.classification_compatible
            and isinstance(self.resolver_family, str)
            and bool(self.resolver_family)
            and self.standard_code_used is False
            and self.resolver_execution_allowed is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def evaluate_resolver_family_eligibility(
    admitted_profile: RegulationResolutionProfile,
) -> RegulationResolutionProfileResolverFamilyEligibilityResult:
    """Return the admitted resolution family only after exact STEP103 compatibility.

    The family label is copied from the admitted profile itself, never from the
    built-in registry and never from standard_code. STEP103 is recomputed here;
    callers cannot supply a detached compatibility result as proof.
    """
    if not isinstance(admitted_profile, RegulationResolutionProfile):
        return RegulationResolutionProfileResolverFamilyEligibilityResult(
            status=REJECTED,
            resolver_family=None,
            classification_compatible=False,
        )

    compatibility = check_registry_classification_compatibility(admitted_profile)
    if not compatibility.compatible:
        return RegulationResolutionProfileResolverFamilyEligibilityResult(
            status=REJECTED,
            resolver_family=None,
            classification_compatible=False,
        )

    return RegulationResolutionProfileResolverFamilyEligibilityResult(
        status=ELIGIBLE,
        resolver_family=admitted_profile.resolution_type,
        classification_compatible=True,
        standard_code_used=False,
        resolver_execution_allowed=False,
        site_truth_decision_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
