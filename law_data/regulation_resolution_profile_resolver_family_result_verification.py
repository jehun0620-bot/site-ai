"""Fail-closed verification for provenance-bound resolver-family execution results.

STEP112 verifies that a supplied STEP110 result is exactly reproducible from the
same dispatch plan, family input, admitted profile, and STEP101 provenance chain.
It validates family/result identity only. It does not convert resolver output into
SITE truth or propagate resolver-local production/runtime flags as authority.
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
    execute_admitted_resolver_family,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)

VERIFIED = "VERIFIED"
REJECTED = "REJECTED"

_HISTORICAL_RESOLUTIONS = frozenset({"TRUE_CANDIDATE", "FALSE", "UNKNOWN"})
_HYBRID_RESOLUTIONS = frozenset({"UNKNOWN"})


@dataclass(frozen=True)
class RegulationResolutionProfileResolverFamilyResultVerification:
    status: str
    resolver_family: str | None
    execution_reproduced: bool
    family_result_identity_verified: bool
    resolution: str | None
    standard_code_used: bool = False
    site_truth_decision_allowed: bool = False
    site_promotion_allowed: bool = False
    production_readiness_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.resolver_family in {
                HISTORICAL_SITE_EVENT,
                HYBRID_SPATIAL_NOTICE,
            }
            and self.execution_reproduced
            and self.family_result_identity_verified
            and self.resolution is not None
            and self.standard_code_used is False
            and self.site_truth_decision_allowed is False
            and self.site_promotion_allowed is False
            and self.production_readiness_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _reject() -> RegulationResolutionProfileResolverFamilyResultVerification:
    return RegulationResolutionProfileResolverFamilyResultVerification(
        status=REJECTED,
        resolver_family=None,
        execution_reproduced=False,
        family_result_identity_verified=False,
        resolution=None,
    )


def _family_output_is_valid(family: str, output: dict[str, Any]) -> bool:
    if output.get("resolution_type") != family:
        return False
    resolution = output.get("resolution")
    if not isinstance(resolution, str):
        return False

    if family == HISTORICAL_SITE_EVENT:
        return (
            resolution in _HISTORICAL_RESOLUTIONS
            and output.get("automatic_true_promotion_allowed") is False
            and output.get("production_wiring_applied") is False
            and output.get("runtime_registry_mutated") is False
        )

    if family == HYBRID_SPATIAL_NOTICE:
        return (
            resolution in _HYBRID_RESOLUTIONS
            and output.get("site_promotion_allowed") is False
            and output.get("negative_evidence_allowed") is False
            and output.get("legal_absence_inference_allowed") is False
            and output.get("site_false_inference_allowed") is False
        )

    return False


def verify_resolver_family_result(
    execution_result: RegulationResolutionProfileResolverFamilyExecutionResult,
    dispatch_plan: RegulationResolutionProfileResolverFamilyDispatchPlan,
    resolver_input: Any,
    *,
    admitted_profile: RegulationResolutionProfile | None = None,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileResolverFamilyResultVerification:
    """Verify an exact STEP110 result without granting downstream authority."""
    if not isinstance(
        execution_result,
        RegulationResolutionProfileResolverFamilyExecutionResult,
    ):
        return _reject()

    expected_execution = execute_admitted_resolver_family(
        dispatch_plan,
        resolver_input,
        admitted_profile=admitted_profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    if not expected_execution.executed or execution_result != expected_execution:
        return _reject()

    family = execution_result.resolver_family
    output = execution_result.resolver_output
    if family not in {HISTORICAL_SITE_EVENT, HYBRID_SPATIAL_NOTICE}:
        return _reject()
    if not isinstance(output, dict) or not _family_output_is_valid(family, output):
        return _reject()

    return RegulationResolutionProfileResolverFamilyResultVerification(
        status=VERIFIED,
        resolver_family=family,
        execution_reproduced=True,
        family_result_identity_verified=True,
        resolution=output["resolution"],
        standard_code_used=False,
        site_truth_decision_allowed=False,
        site_promotion_allowed=False,
        production_readiness_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
