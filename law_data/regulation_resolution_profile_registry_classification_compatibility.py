"""Fail-closed compatibility boundary for admitted and built-in profiles.

A built-in registry profile is an expected/static classification baseline only.
It is never evidence that classification was verified. Compatibility checks only
name, condition_type, and resolution_type. Standard-code identity, authority or
source verification, SITE truth, and production/runtime permissions are outside
this contract and cannot be supplied or promoted here.
"""

from __future__ import annotations

from dataclasses import dataclass

from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry import (
    get_regulation_resolution_profile,
)

COMPATIBLE = "COMPATIBLE"
REJECTED = "REJECTED"
VERIFIED_CLASSIFICATION_ADMISSION = "VERIFIED"


@dataclass(frozen=True)
class RegulationResolutionProfileRegistryClassificationCompatibilityResult:
    """Read-only result; compatibility is not an authorization token."""

    status: str
    name_matches: bool
    condition_type_matches: bool
    resolution_type_matches: bool
    admitted_profile_verified: bool
    expected_profile_found: bool
    standard_code_compared: bool = False
    site_promotion_allowed: bool = False
    production_registration_allowed: bool = False
    runtime_registration_allowed: bool = False

    @property
    def compatible(self) -> bool:
        return (
            self.status == COMPATIBLE
            and self.admitted_profile_verified
            and self.expected_profile_found
            and self.name_matches
            and self.condition_type_matches
            and self.resolution_type_matches
            and self.standard_code_compared is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _is_step101_admitted_profile(profile: RegulationResolutionProfile) -> bool:
    """Require STEP101 admission diagnostics; registry data alone cannot qualify."""
    if not isinstance(profile, RegulationResolutionProfile):
        return False
    diagnostics = profile.diagnostics
    return (
        diagnostics.get("classification_admission")
        == VERIFIED_CLASSIFICATION_ADMISSION
        and isinstance(diagnostics.get("seed_fingerprint"), str)
        and bool(diagnostics.get("seed_fingerprint"))
        and isinstance(diagnostics.get("classification_evidence_fingerprint"), str)
        and bool(diagnostics.get("classification_evidence_fingerprint"))
        and profile.standard_code is None
        and profile.standard_code_verified is False
        and profile.authority_identity_verified is False
        and profile.source_policy_verified is False
        and profile.negative_evidence_allowed is False
        and profile.legal_absence_inference_allowed is False
        and profile.site_promotion_allowed is False
        and profile.production_registration_allowed is False
        and profile.runtime_registration_allowed is False
    )


def check_registry_classification_compatibility(
    admitted_profile: RegulationResolutionProfile,
) -> RegulationResolutionProfileRegistryClassificationCompatibilityResult:
    """Compare STEP101-admitted classification with the exact-name registry baseline.

    The lookup direction is admitted profile -> expected registry baseline only.
    No registry value is copied into the admitted profile and no missing value is
    inferred from the registry.
    """
    if not isinstance(admitted_profile, RegulationResolutionProfile):
        return RegulationResolutionProfileRegistryClassificationCompatibilityResult(
            status=REJECTED,
            name_matches=False,
            condition_type_matches=False,
            resolution_type_matches=False,
            admitted_profile_verified=False,
            expected_profile_found=False,
        )

    admitted_verified = _is_step101_admitted_profile(admitted_profile)
    expected = get_regulation_resolution_profile(admitted_profile.name)
    expected_found = expected is not None

    name_matches = bool(
        expected_found and expected.name == admitted_profile.name
    )
    condition_type_matches = bool(
        expected_found
        and expected.condition_type == admitted_profile.condition_type
    )
    resolution_type_matches = bool(
        expected_found
        and expected.resolution_type == admitted_profile.resolution_type
    )

    compatible = all((
        admitted_verified,
        expected_found,
        name_matches,
        condition_type_matches,
        resolution_type_matches,
    ))

    return RegulationResolutionProfileRegistryClassificationCompatibilityResult(
        status=COMPATIBLE if compatible else REJECTED,
        name_matches=name_matches,
        condition_type_matches=condition_type_matches,
        resolution_type_matches=resolution_type_matches,
        admitted_profile_verified=admitted_verified,
        expected_profile_found=expected_found,
        standard_code_compared=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )
