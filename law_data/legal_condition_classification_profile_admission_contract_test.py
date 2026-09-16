from __future__ import annotations

from dataclasses import replace

from .legal_condition_catalogue_seed import (
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)
from .legal_condition_classification_profile_admission import (
    CLASSIFICATION_ADMISSION_PROOF_VERSION,
    VERIFIED,
    LegalConditionClassificationEvidence,
    admit_verified_classification_to_profile,
    classification_admission_proof_fingerprint,
    seed_identity_fingerprint,
    verify_classification_evidence,
)


def _verified_seed() -> LegalConditionCatalogueSeed:
    return LegalConditionCatalogueSeed(
        condition_name="개발밀도관리구역",
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


def _evidence(seed: LegalConditionCatalogueSeed) -> LegalConditionClassificationEvidence:
    return LegalConditionClassificationEvidence(
        condition_name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=seed_identity_fingerprint(seed),
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        official_source_qualified=True,
        condition_identity_bound=True,
        legal_basis_bound=True,
        classification_statement_bound=True,
        same_source_binding=True,
    )


def main() -> None:
    seed = _verified_seed()
    evidence = _evidence(seed)
    verification = verify_classification_evidence(seed, evidence)
    assert verification.verified
    assert verification.status == VERIFIED

    profile = admit_verified_classification_to_profile(seed, evidence, verification)
    diagnostics = profile.diagnostics
    assert profile.standard_code is None
    assert profile.standard_code_verified is False
    assert diagnostics["classification_admission"] == VERIFIED
    assert diagnostics["classification_admission_proof_version"] == CLASSIFICATION_ADMISSION_PROOF_VERSION
    assert diagnostics["seed_fingerprint"] == seed_identity_fingerprint(seed)
    assert diagnostics["classification_evidence_fingerprint"] == evidence.identity_fingerprint()
    assert diagnostics["classification_admission_proof"] == classification_admission_proof_fingerprint(
        name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=seed_identity_fingerprint(seed),
        classification_evidence_fingerprint=evidence.identity_fingerprint(),
        condition_type=evidence.condition_type,
        resolution_type=evidence.resolution_type,
    )

    assert profile.authority_identity_verified is False
    assert profile.source_policy_verified is False
    assert profile.negative_evidence_allowed is False
    assert profile.legal_absence_inference_allowed is False
    assert profile.site_promotion_allowed is False
    assert profile.production_registration_allowed is False
    assert profile.runtime_registration_allowed is False

    tampered_evidence = replace(evidence, resolution_type="SNAPSHOT")
    try:
        admit_verified_classification_to_profile(seed, tampered_evidence, verification)
    except ValueError:
        pass
    else:
        raise AssertionError("cross-evidence verification reuse must fail closed")

    unverified = replace(verification, status="UNVERIFIED")
    try:
        admit_verified_classification_to_profile(seed, evidence, unverified)
    except ValueError:
        pass
    else:
        raise AssertionError("unverified classification must fail closed")

    print("STEP101_VERIFIED_CLASSIFICATION_TO_PROFILE_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
