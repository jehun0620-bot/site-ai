from __future__ import annotations

from dataclasses import dataclass

from .legal_condition_catalogue_seed import LegalConditionCatalogueSeed
from .legal_condition_classification_profile_admission import (
    CLASSIFICATION_ADMISSION_PROOF_VERSION,
    VERIFIED,
    LegalConditionClassificationEvidence,
    LegalConditionClassificationVerificationResult,
    classification_admission_proof_fingerprint,
    evidence_matches_classification_verification,
    seed_identity_fingerprint,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry import get_regulation_resolution_profile


COMPATIBLE = "COMPATIBLE"
REJECTED = "REJECTED"
VERIFIED_CLASSIFICATION_ADMISSION = VERIFIED


@dataclass(frozen=True)
class RegulationResolutionProfileRegistryClassificationCompatibilityResult:
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
            and self.admitted_profile_verified is True
            and self.expected_profile_found is True
            and self.name_matches is True
            and self.condition_type_matches is True
            and self.resolution_type_matches is True
            and self.standard_code_compared is False
            and self.site_promotion_allowed is False
            and self.production_registration_allowed is False
            and self.runtime_registration_allowed is False
        )


def _has_step101_fail_closed_shape(profile: RegulationResolutionProfile) -> bool:
    return (
        profile.standard_code is None
        and profile.standard_code_verified is False
        and profile.authority_identity_verified is False
        and profile.source_policy_verified is False
        and profile.negative_evidence_allowed is False
        and profile.legal_absence_inference_allowed is False
        and profile.site_promotion_allowed is False
        and profile.production_registration_allowed is False
        and profile.runtime_registration_allowed is False
    )


def _is_step101_admitted_profile(
    profile: RegulationResolutionProfile,
    *,
    seed: LegalConditionCatalogueSeed | None,
    evidence: LegalConditionClassificationEvidence | None,
    verification: LegalConditionClassificationVerificationResult | None,
) -> bool:
    if not isinstance(profile, RegulationResolutionProfile):
        return False
    if not isinstance(seed, LegalConditionCatalogueSeed):
        return False
    if not isinstance(evidence, LegalConditionClassificationEvidence):
        return False
    if not isinstance(verification, LegalConditionClassificationVerificationResult):
        return False
    if seed.seed_verified is not True:
        return False
    if not evidence_matches_classification_verification(evidence, verification):
        return False

    expected_seed_fingerprint = seed_identity_fingerprint(seed)
    expected_evidence_fingerprint = evidence.identity_fingerprint()
    diagnostics = profile.diagnostics

    if evidence.condition_name != seed.condition_name:
        return False
    if evidence.legal_basis != seed.legal_basis:
        return False
    if evidence.seed_fingerprint != expected_seed_fingerprint:
        return False
    if profile.name != seed.condition_name:
        return False
    if profile.condition_type != evidence.condition_type:
        return False
    if profile.resolution_type != evidence.resolution_type:
        return False
    if not _has_step101_fail_closed_shape(profile):
        return False

    expected_proof = classification_admission_proof_fingerprint(
        name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=expected_seed_fingerprint,
        classification_evidence_fingerprint=expected_evidence_fingerprint,
        condition_type=evidence.condition_type,
        resolution_type=evidence.resolution_type,
    )
    return (
        diagnostics.get("classification_admission") == VERIFIED_CLASSIFICATION_ADMISSION
        and diagnostics.get("classification_admission_proof_version")
        == CLASSIFICATION_ADMISSION_PROOF_VERSION
        and diagnostics.get("seed_fingerprint") == expected_seed_fingerprint
        and diagnostics.get("classification_evidence_fingerprint")
        == expected_evidence_fingerprint
        and diagnostics.get("classification_admission_proof") == expected_proof
    )


def check_registry_classification_compatibility(
    admitted_profile: RegulationResolutionProfile,
    *,
    seed: LegalConditionCatalogueSeed | None = None,
    evidence: LegalConditionClassificationEvidence | None = None,
    verification: LegalConditionClassificationVerificationResult | None = None,
) -> RegulationResolutionProfileRegistryClassificationCompatibilityResult:
    expected = (
        get_regulation_resolution_profile(admitted_profile.name)
        if isinstance(admitted_profile, RegulationResolutionProfile)
        else None
    )
    admitted_profile_verified = (
        _is_step101_admitted_profile(
            admitted_profile,
            seed=seed,
            evidence=evidence,
            verification=verification,
        )
        if isinstance(admitted_profile, RegulationResolutionProfile)
        else False
    )
    expected_profile_found = expected is not None
    name_matches = bool(expected and admitted_profile.name == expected.name)
    condition_type_matches = bool(
        expected and admitted_profile.condition_type == expected.condition_type
    )
    resolution_type_matches = bool(
        expected and admitted_profile.resolution_type == expected.resolution_type
    )
    compatible = (
        admitted_profile_verified
        and expected_profile_found
        and name_matches
        and condition_type_matches
        and resolution_type_matches
    )

    return RegulationResolutionProfileRegistryClassificationCompatibilityResult(
        status=COMPATIBLE if compatible else REJECTED,
        name_matches=name_matches,
        condition_type_matches=condition_type_matches,
        resolution_type_matches=resolution_type_matches,
        admitted_profile_verified=admitted_profile_verified,
        expected_profile_found=expected_profile_found,
    )
