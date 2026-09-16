"""Fail-closed resolver-family eligibility for verified classification profiles.

This boundary does not discover, import, select, or execute a resolver callable.
It only exposes the already-verified profile resolution_type as an eligible
family label after STEP103 registry compatibility is recomputed successfully
from the exact STEP101 provenance artifacts.

Eligibility is not SITE truth, resolver execution authority, production
readiness, production registration, runtime registration, or SITE mutation.
Standard-code identity is outside this boundary and is never inferred or copied.
"""

from __future__ import annotations

from dataclasses import dataclass

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
)
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
    *,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileResolverFamilyEligibilityResult:
    """Return the family only after exact STEP103 provenance compatibility.

    STEP103 is recomputed from the profile plus the exact STEP101 seed,
    classification evidence, and verification result. Profile-only calls and
    cross-artifact reuse therefore fail closed. The family label is copied from
    the admitted profile itself, never from registry data or standard_code.
    """
    if not isinstance(admitted_profile, RegulationResolutionProfile):
        return RegulationResolutionProfileResolverFamilyEligibilityResult(
            status=REJECTED,
            resolver_family=None,
            classification_compatible=False,
        )

    compatibility = check_registry_classification_compatibility(
        admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
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
