"""Focused contract tests for verified classification-to-profile admission."""

from .legal_condition_catalogue_seed import (
    STATUTE_APPENDIX,
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    LegalConditionClassificationProfileAdmissionError,
    admit_verified_classification_to_profile,
    seed_identity_fingerprint,
    verify_classification_evidence,
)


def _seed(**overrides):
    values = dict(
        condition_name="테스트구역",
        legal_basis="법률 별표 제1호",
        provenance=LegalEnumerationProvenance(
            source_family=STATUTE_APPENDIX,
            source_uri="https://www.law.go.kr/example",
            law_id="LAW-1",
            law_version_id="MST-1",
            effective_date="2026-01-01",
            appendix_id="APP-1",
            row_id="ROW-1",
            source_identity_verified=True,
            row_binding_verified=True,
        ),
    )
    values.update(overrides)
    return LegalConditionCatalogueSeed(**values)


def _evidence(seed, **overrides):
    values = dict(
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
    values.update(overrides)
    return LegalConditionClassificationEvidence(**values)


def _must_reject(seed, evidence, verification) -> None:
    try:
        admit_verified_classification_to_profile(seed, evidence, verification)
        raise AssertionError("unsafe classification admission must fail closed")
    except LegalConditionClassificationProfileAdmissionError:
        pass


def main() -> None:
    seed = _seed()
    evidence = _evidence(seed)
    verification = verify_classification_evidence(seed, evidence)
    profile = admit_verified_classification_to_profile(seed, evidence, verification)

    assert profile.name == seed.condition_name
    assert profile.condition_type == "SITE"
    assert profile.resolution_type == "HYBRID_SPATIAL_NOTICE"
    assert profile.standard_code is None
    assert profile.standard_code_verified is False
    assert profile.authority_identity_verified is False
    assert profile.source_policy_verified is False
    assert profile.negative_evidence_allowed is False
    assert profile.legal_absence_inference_allowed is False
    assert profile.site_promotion_allowed is False
    assert profile.production_registration_allowed is False
    assert profile.runtime_registration_allowed is False

    changed_classification = _evidence(seed, resolution_type="SNAPSHOT")
    _must_reject(seed, changed_classification, verification)

    changed_condition = _evidence(seed, condition_name="다른구역")
    _must_reject(seed, changed_condition, verification)

    changed_basis = _evidence(seed, legal_basis="다른 법적 근거")
    _must_reject(seed, changed_basis, verification)

    other_seed = _seed(
        provenance=LegalEnumerationProvenance(
            source_family=STATUTE_APPENDIX,
            source_uri="https://www.law.go.kr/example",
            law_id="LAW-1",
            law_version_id="MST-2",
            effective_date="2026-02-01",
            appendix_id="APP-1",
            row_id="ROW-1",
            source_identity_verified=True,
            row_binding_verified=True,
        )
    )
    _must_reject(other_seed, evidence, verification)

    unverified = _evidence(seed, classification_statement_bound=False)
    _must_reject(seed, unverified, verify_classification_evidence(seed, unverified))

    metadata_variant = _evidence(
        seed,
        metadata={
            "condition_type": "SITE_HISTORY",
            "resolution_type": "HISTORICAL_SITE_EVENT",
            "standard_code": "FAKE",
            "runtime_registration_allowed": True,
        },
    )
    metadata_profile = admit_verified_classification_to_profile(
        seed,
        metadata_variant,
        verify_classification_evidence(seed, metadata_variant),
    )
    assert metadata_profile.condition_type == "SITE"
    assert metadata_profile.resolution_type == "HYBRID_SPATIAL_NOTICE"
    assert metadata_profile.standard_code is None
    assert metadata_profile.standard_code_verified is False
    assert metadata_profile.runtime_registration_allowed is False

    history_seed = _seed(condition_name="과거사건구역")
    history_evidence = _evidence(
        history_seed,
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    history_profile = admit_verified_classification_to_profile(
        history_seed,
        history_evidence,
        verify_classification_evidence(history_seed, history_evidence),
    )
    assert history_profile.condition_type == "SITE_HISTORY"
    assert history_profile.resolution_type == "HISTORICAL_SITE_EVENT"
    assert history_profile.standard_code is None
    assert history_profile.standard_code_verified is False
    assert history_profile.site_promotion_allowed is False
    assert history_profile.production_registration_allowed is False
    assert history_profile.runtime_registration_allowed is False

    forbidden_evidence_fields = {
        "standard_code", "standard_code_verified", "site_applicable",
        "site_promotion_allowed", "production_registration_allowed",
        "runtime_registration_allowed", "negative_evidence_allowed",
        "legal_absence_inference_allowed",
    }
    assert forbidden_evidence_fields.isdisjoint(evidence.__dataclass_fields__)

    print("STEP101_VERIFIED_CLASSIFICATION_TO_PROFILE_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
