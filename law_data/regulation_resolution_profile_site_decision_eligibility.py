"""Fail-closed SITE-decision eligibility after STEP112 result verification.

This boundary decides only whether a verified resolver result is sufficiently
conclusive to be considered by a later SITE-decision admission layer. It does not
mutate SITE state, promote a value, or authorize production/runtime registration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    RegulationResolutionProfileResolverFamilyDispatchPlan,
)
from .regulation_resolution_profile_resolver_family_execution import (
    RegulationResolutionProfileResolverFamilyExecutionResult,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_resolver_family_result_verification import (
    verify_resolver_family_result,
)

ELIGIBLE = "ELIGIBLE"
INELIGIBLE = "INELIGIBLE"
REJECTED = "REJECTED"


@dataclass(frozen=True)
class RegulationResolutionProfileSiteDecisionEligibility:
    status: str
    resolver_family: str | None
    resolver_result_verified: bool
    resolution: str | None
    candidate_site_decision: bool | None
    conclusive_for_site_decision: bool
    standard_code_used: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def eligible(self) -> bool:
        return (
            self.status == ELIGIBLE
            and self.resolver_family == HISTORICAL_SITE_EVENT
            and self.resolver_result_verified
            and self.resolution == "FALSE"
            and self.candidate_site_decision is False
            and self.conclusive_for_site_decision
            and self.standard_code_used is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _result(
    *,
    status: str,
    family: str | None = None,
    verified: bool = False,
    resolution: str | None = None,
    candidate: bool | None = None,
    conclusive: bool = False,
) -> RegulationResolutionProfileSiteDecisionEligibility:
    return RegulationResolutionProfileSiteDecisionEligibility(
        status=status,
        resolver_family=family,
        resolver_result_verified=verified,
        resolution=resolution,
        candidate_site_decision=candidate,
        conclusive_for_site_decision=conclusive,
    )


def evaluate_site_decision_eligibility(
    execution_result: RegulationResolutionProfileResolverFamilyExecutionResult,
    dispatch_plan: RegulationResolutionProfileResolverFamilyDispatchPlan,
    resolver_input: Any,
    *,
    admitted_profile: RegulationResolutionProfile | None = None,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileSiteDecisionEligibility:
    """Reproduce STEP112 and expose only a non-authoritative decision candidate."""
    result_verification = verify_resolver_family_result(
        execution_result,
        dispatch_plan,
        resolver_input,
        admitted_profile=admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    if not result_verification.verified:
        return _result(status=REJECTED)

    family = result_verification.resolver_family
    resolution = result_verification.resolution

    # Historical FALSE is based on the resolver's positively verified exhaustive
    # disproof contract. It is therefore conclusive enough to become a candidate
    # for a later SITE-decision admission boundary, but is not applied here.
    if family == HISTORICAL_SITE_EVENT and resolution == "FALSE":
        return _result(
            status=ELIGIBLE,
            family=family,
            verified=True,
            resolution=resolution,
            candidate=False,
            conclusive=True,
        )

    # TRUE_CANDIDATE is intentionally not SITE TRUE. UNKNOWN is never conclusive.
    # HYBRID_SPATIAL_NOTICE currently resolves UNKNOWN even when its local positive
    # gates are satisfied, so its resolver-local registration flag is not promoted.
    if family in {HISTORICAL_SITE_EVENT, HYBRID_SPATIAL_NOTICE}:
        return _result(
            status=INELIGIBLE,
            family=family,
            verified=True,
            resolution=resolution,
        )

    return _result(status=REJECTED)
