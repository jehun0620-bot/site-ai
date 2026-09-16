from __future__ import annotations

from dataclasses import replace

from .legal_condition_catalogue_seed import (
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)
from .legal_condition_classification_profile_admission import (
    VERIFIED,
    LegalConditionClassificationEvidence,
    admit_verified_classification_to_profile,
    seed_identity_fingerprint,
    verify_classification_evidence,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry import get_regulation_resolution_profile
from .regulation_resolution_profile_registry_classification_compatibility import (
    COMPATIBLE,
    REJECTED,
    check_registry_classification_compatibility,
)


def _verified_seed(name: str = "개발밀도관리구역") -> LegalConditionCatalogueSeed:
    return LegalConditionCatalogueSeed(
        condition_name=name,
        legal_basis="국토의 계획 및 이용에 관한 법률",
        provenance=LegalEnumerationProvenance(
            source_family="STATUTE_APPENDIX",
            source_uri="https://example.invalid/statute",
            law_id="TEST-LAW",
            law_version_id="TEST-VERSION",
            effective_date="2026-01-01",
            appendix_id="APPENDIX-1",
            row_id="ROW-1",
            source_identity_verified=True,
            row_binding_verified=True,
        ),
    )


def _admission(
    *,
    name: str = "개발밀도관리구역",
    condition_type: str = "SITE",
    resolution_type: str = "HYBRID_SPATIAL_NOTICE",
):
    seed = _verified_seed(name)
    evidence = LegalConditionClassificationEvidence(
        condition_name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=seed_identity_fingerprint(seed),
        condition_type=condition_type,
        resolution_type=resolution_type,
        official_source_qualified=True,
        condition_identity_bound=True,
        legal_basis_bound=True,
        classification_statement_bound=True,
        same_source_binding=True,
    )
    verification = verify_classification_evidence(seed, evidence)
    assert verification.verified
    profile = admit_verified_classification_to_profile(seed, evidence, verification)
    return seed, evidence, verification, profile


def _check(admission):
    seed, evidence, verification, profile = admission
    return check_registry_classification_compatibility(
        profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    admission = _admission()
    seed, evidence, verification, admitted = admission
    expected = get_regulation_resolution_profile(admitted.name)
    assert expected is not None
    assert expected.standard_code == "UQQ700"
    assert expected.standard_code_verified is True
    assert admitted.standard_code is None

    result = _check(admission)
    assert result.status == COMPATIBLE
    assert result.compatible is True
    assert result.admitted_profile_verified is True
    assert result.standard_code_compared is False

    unknown = _admission(name="미등록조건")
    unknown_result = _check(unknown)
    assert unknown_result.status == REJECTED
    assert unknown_result.expected_profile_found is False

    wrong_type = _admission(condition_type="SITE_HISTORY")
    assert _check(wrong_type).status == REJECTED
    wrong_resolution = _admission(resolution_type="SNAPSHOT")
    assert _check(wrong_resolution).status == REJECTED

    # Registry profile alone is never STEP101 provenance.
    registry_only_result = check_registry_classification_compatibility(expected)
    assert registry_only_result.status == REJECTED
    assert registry_only_result.admitted_profile_verified is False

    # Even a complete-looking set of caller-controlled diagnostics is not proof.
    forged = RegulationResolutionProfile(
        name=admitted.name,
        condition_type=admitted.condition_type,
        resolution_type=admitted.resolution_type,
        standard_code=None,
        standard_code_verified=False,
        diagnostics={
            "classification_admission": VERIFIED,
            "classification_admission_proof_version": admitted.diagnostics["classification_admission_proof_version"],
            "seed_fingerprint": "f" * 64,
            "classification_evidence_fingerprint": "e" * 64,
            "classification_admission_proof": "a" * 64,
        },
    )
    forged_result = check_registry_classification_compatibility(forged)
    assert forged_result.status == REJECTED
    assert forged_result.admitted_profile_verified is False

    # Copying the genuine diagnostics still cannot authenticate without exact artifacts.
    copied = replace(admitted, diagnostics=dict(admitted.diagnostics))
    copied_without_artifacts = check_registry_classification_compatibility(copied)
    assert copied_without_artifacts.status == REJECTED
    assert copied_without_artifacts.admitted_profile_verified is False

    # Cross-seed/evidence/verification binding must fail closed.
    other_seed, other_evidence, other_verification, _ = _admission(name="도시지역편입해제구역", condition_type="SITE_HISTORY", resolution_type="HISTORICAL_SITE_EVENT")
    cross = check_registry_classification_compatibility(
        admitted,
        seed=other_seed,
        evidence=other_evidence,
        verification=other_verification,
    )
    assert cross.status == REJECTED
    assert cross.admitted_profile_verified is False

    escalated = replace(admitted, runtime_registration_allowed=True)
    escalated_result = check_registry_classification_compatibility(
        escalated,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    assert escalated_result.status == REJECTED
    assert escalated_result.runtime_registration_allowed is False

    invalid_result = check_registry_classification_compatibility(None)  # type: ignore[arg-type]
    assert invalid_result.status == REJECTED

    print("STEP103_VERIFIED_PROFILE_REGISTRY_CLASSIFICATION_COMPATIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
