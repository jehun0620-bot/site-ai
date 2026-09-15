"""Focused contract tests for fingerprint-bound evidence-to-seed admission."""

from .legal_condition_catalogue_seed import DECREE_APPENDIX, OFFICIAL_GAZETTE, STATUTE_APPENDIX
from .legal_enumeration_evidence_to_seed_admission import (
    LegalEnumerationSeedAdmissionError,
    admit_verified_evidence_to_seed,
)
from .legal_enumeration_source_family_verifier import (
    LawAppendixEnumerationEvidence,
    OfficialGazetteEnumerationEvidence,
    verify_law_appendix_enumeration,
    verify_official_gazette_enumeration,
)


def _law(**overrides):
    values = dict(
        source_family=STATUTE_APPENDIX,
        condition_name="테스트구역",
        legal_basis="법률 별표 제1호",
        law_id="LAW-1",
        law_version_id="MST-1",
        effective_date="2026-01-01",
        appendix_id="APP-1",
        row_id="ROW-1",
        source_uri="https://www.law.go.kr/example",
        official_source_qualified=True,
        law_identity_bound=True,
        version_identity_bound=True,
        effective_date_bound=True,
        appendix_identity_bound=True,
        row_identity_bound=True,
        condition_name_bound=True,
        legal_basis_bound=True,
        same_row_binding=True,
    )
    values.update(overrides)
    return LawAppendixEnumerationEvidence(**values)


def _gazette(**overrides):
    values = dict(
        condition_name="관보테스트구역",
        legal_basis="관보 게재 법적 근거",
        gazette_issue_id="ISSUE-1",
        publication_date="2026-01-02",
        gazette_document_id="DOC-1",
        issuing_authority="국토교통부",
        source_uri="https://gwanbo.go.kr/example",
        official_source_qualified=True,
        issue_identity_bound=True,
        publication_date_bound=True,
        document_identity_bound=True,
        issuing_authority_bound=True,
        entry_identity_bound=True,
        condition_name_bound=True,
        legal_basis_bound=True,
        same_entry_binding=True,
    )
    values.update(overrides)
    return OfficialGazetteEnumerationEvidence(**values)


def _must_reject(evidence, verification) -> None:
    try:
        admit_verified_evidence_to_seed(evidence, verification)
        raise AssertionError("unsafe admission must fail closed")
    except LegalEnumerationSeedAdmissionError:
        pass


def main() -> None:
    statute = _law()
    statute_verification = verify_law_appendix_enumeration(statute)
    statute_seed = admit_verified_evidence_to_seed(statute, statute_verification)
    assert statute_seed.seed_verified
    assert statute_seed.condition_name == statute.condition_name
    assert statute_seed.legal_basis == statute.legal_basis
    assert statute_seed.provenance.source_family == STATUTE_APPENDIX
    assert statute_seed.provenance.law_id == statute.law_id
    assert statute_seed.provenance.law_version_id == statute.law_version_id
    assert statute_seed.provenance.effective_date == statute.effective_date
    assert statute_seed.provenance.appendix_id == statute.appendix_id
    assert statute_seed.provenance.row_id == statute.row_id
    assert statute_seed.provenance.source_uri == statute.source_uri
    assert not statute_seed.provenance.metadata

    decree = _law(source_family=DECREE_APPENDIX)
    decree_seed = admit_verified_evidence_to_seed(
        decree, verify_law_appendix_enumeration(decree)
    )
    assert decree_seed.seed_verified
    assert decree_seed.provenance.source_family == DECREE_APPENDIX

    gazette = _gazette()
    gazette_seed = admit_verified_evidence_to_seed(
        gazette, verify_official_gazette_enumeration(gazette)
    )
    assert gazette_seed.seed_verified
    assert gazette_seed.provenance.source_family == OFFICIAL_GAZETTE
    assert gazette_seed.provenance.gazette_issue_id == gazette.gazette_issue_id
    assert gazette_seed.provenance.publication_date == gazette.publication_date
    assert gazette_seed.provenance.gazette_document_id == gazette.gazette_document_id
    assert gazette_seed.provenance.issuing_authority == gazette.issuing_authority
    assert gazette_seed.provenance.source_uri == gazette.source_uri
    assert not gazette_seed.provenance.metadata

    _must_reject(_law(row_id="ROW-2"), statute_verification)
    _must_reject(_law(condition_name="다른구역"), statute_verification)
    _must_reject(_law(legal_basis="다른 근거"), statute_verification)
    _must_reject(_law(source_family=DECREE_APPENDIX), statute_verification)
    _must_reject(_gazette(), statute_verification)

    unverified_law = _law(same_row_binding=False)
    _must_reject(
        unverified_law, verify_law_appendix_enumeration(unverified_law)
    )
    unverified_gazette = _gazette(document_identity_bound=False)
    _must_reject(
        unverified_gazette,
        verify_official_gazette_enumeration(unverified_gazette),
    )

    metadata_variant = _law(metadata={"condition_name": "가짜구역", "verified": True})
    metadata_seed = admit_verified_evidence_to_seed(
        metadata_variant, verify_law_appendix_enumeration(metadata_variant)
    )
    assert metadata_seed.condition_name == metadata_variant.condition_name
    assert not metadata_seed.provenance.metadata

    forbidden = {
        "standard_code", "condition_type", "resolution_type",
        "site_applicable", "production_resolution", "runtime_registration_allowed",
    }
    assert forbidden.isdisjoint(statute_seed.__dataclass_fields__)
    assert forbidden.isdisjoint(statute_seed.provenance.__dataclass_fields__)

    print("STEP98_FINGERPRINT_BOUND_EVIDENCE_TO_SEED_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
