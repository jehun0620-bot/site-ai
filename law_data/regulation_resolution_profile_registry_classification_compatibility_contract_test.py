from __future__ import annotations

from dataclasses import replace

from .legal_condition_catalogue_seed import (
    LegalConditionCatalogueSeed,
    LegalConditionSourceProvenance,
)
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    admit_verified_classification_to_profile,
    seed_identity_fingerprint,
    verify_classification_evidence,
)
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry import (
    get_regulation_resolution_profile,
)
from .regulation_resolution_profile_registry_classification_compatibility import (
    COMPATIBLE,
    REJECTED,
    check_registry_classification_compatibility,
)


def _verified_seed(name: str = "개발밀도관리구역") -> LegalConditionCatalogueSeed:
    return LegalConditionCatalogueSeed(
        condition_name=name,
        legal_basis="국토의 계획 및 이용에 관한 법률",
        provenance=LegalConditionSourceProvenance(
            source_family="STATUTE",
            source_uri="https://example.invalid/statute",
            law_id="TEST-LAW",
            law_version_id="TEST-VERSION",
            effective_date="2026-01-01",
            appendix_id="APPENDIX-1",
            row_id="ROW-1",
        ),
        source_verified=True,
        condition_identity_verified=True,
        legal_basis_verified=True,
        provenance_verified=True,
    )


def _admitted_profile(
    *,
    name: str = "개발밀도관리구역",
    condition_type: str = "SITE",
    resolution_type: str = "HYBRID_SPATIAL_NOTICE",
) -> RegulationResolutionProfile:
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
    return admit_verified_classification_to_profile(seed, evidence, verification)


def main() -> None:
    admitted = _admitted_profile()
    expected = get_regulation_resolution_profile(admitted.name)
    assert expected is not None
    assert expected.standard_code == "UQQ700"
    assert expected.standard_code_verified is True
    assert admitted.standard_code is None
    assert admitted.standard_code_verified is False

    result = check_registry_classification_compatibility(admitted)
    assert result.status == COMPATIBLE
    assert result.compatible is True
    assert result.name_matches is True
    assert result.condition_type_matches is True
    assert result.resolution_type_matches is True
    assert result.standard_code_compared is False
    assert result.site_promotion_allowed is False
    assert result.production_registration_allowed is False
    assert result.runtime_registration_allowed is False

    # Exact-name registry lookup: unknown/cross-condition names fail closed.
    unknown = _admitted_profile(name="미등록조건")
    unknown_result = check_registry_classification_compatibility(unknown)
    assert unknown_result.status == REJECTED
    assert unknown_result.expected_profile_found is False
    assert unknown_result.compatible is False

    # A valid STEP101 profile with the wrong classification cannot match baseline.
    wrong_condition_type = _admitted_profile(condition_type="SITE_HISTORY")
    wrong_type_result = check_registry_classification_compatibility(
        wrong_condition_type
    )
    assert wrong_type_result.status == REJECTED
    assert wrong_type_result.condition_type_matches is False

    wrong_resolution = _admitted_profile(resolution_type="SNAPSHOT")
    wrong_resolution_result = check_registry_classification_compatibility(
        wrong_resolution
    )
    assert wrong_resolution_result.status == REJECTED
    assert wrong_resolution_result.resolution_type_matches is False

    # Registry profile itself is not proof of verified classification admission.
    registry_only_result = check_registry_classification_compatibility(expected)
    assert registry_only_result.status == REJECTED
    assert registry_only_result.admitted_profile_verified is False
    assert registry_only_result.compatible is False

    # Forged profile without exact STEP101 diagnostics is rejected.
    forged = RegulationResolutionProfile(
        name=expected.name,
        condition_type=expected.condition_type,
        resolution_type=expected.resolution_type,
        standard_code=None,
        standard_code_verified=False,
        diagnostics={"classification_admission": "VERIFIED"},
    )
    forged_result = check_registry_classification_compatibility(forged)
    assert forged_result.status == REJECTED
    assert forged_result.admitted_profile_verified is False

    # Registry standard code cannot be copied into or used to qualify admission.
    assert admitted.standard_code is None
    assert expected.standard_code == "UQQ700"
    assert result.standard_code_compared is False

    # Permission escalation invalidates the STEP101 admission shape.
    escalated = replace(admitted, runtime_registration_allowed=True)
    escalated_result = check_registry_classification_compatibility(escalated)
    assert escalated_result.status == REJECTED
    assert escalated_result.admitted_profile_verified is False
    assert escalated_result.runtime_registration_allowed is False

    # Non-profile input is rejected without exception or inference.
    invalid_result = check_registry_classification_compatibility(None)  # type: ignore[arg-type]
    assert invalid_result.status == REJECTED
    assert invalid_result.compatible is False

    print("STEP103_VERIFIED_PROFILE_REGISTRY_CLASSIFICATION_COMPATIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
