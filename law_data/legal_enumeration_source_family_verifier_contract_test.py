"""Focused contract tests for STEP96 evidence identity binding."""

from dataclasses import FrozenInstanceError

from .legal_condition_catalogue_seed import DECREE_APPENDIX, STATUTE_APPENDIX
from .legal_enumeration_source_family_verifier import (
    UNVERIFIED,
    VERIFIED,
    LawAppendixEnumerationEvidence,
    OfficialGazetteEnumerationEvidence,
    evidence_matches_verification,
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
        condition_name="테스트구역",
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


def main() -> None:
    statute = _law()
    statute_result = verify_law_appendix_enumeration(statute)
    assert statute_result.status == VERIFIED and statute_result.verified
    assert statute_result.source_family == STATUTE_APPENDIX
    assert statute_result.evidence_fingerprint == statute.identity_fingerprint()
    assert evidence_matches_verification(statute, statute_result)

    decree = _law(source_family=DECREE_APPENDIX)
    decree_result = verify_law_appendix_enumeration(decree)
    assert decree_result.status == VERIFIED and decree_result.source_family == DECREE_APPENDIX
    assert evidence_matches_verification(decree, decree_result)
    assert decree.identity_fingerprint() != statute.identity_fingerprint()
    assert not evidence_matches_verification(statute, decree_result)
    assert not evidence_matches_verification(decree, statute_result)

    gazette = _gazette()
    gazette_result = verify_official_gazette_enumeration(gazette)
    assert gazette_result.status == VERIFIED and gazette_result.verified
    assert gazette_result.evidence_fingerprint == gazette.identity_fingerprint()
    assert evidence_matches_verification(gazette, gazette_result)
    assert not evidence_matches_verification(statute, gazette_result)
    assert not evidence_matches_verification(gazette, statute_result)

    # Any seed-relevant identity change must break the evidence/result pair.
    for changed in (
        _law(condition_name="다른구역"),
        _law(legal_basis="다른 법적 근거"),
        _law(law_id="LAW-2"),
        _law(law_version_id="MST-2"),
        _law(effective_date="2026-02-01"),
        _law(appendix_id="APP-2"),
        _law(row_id="ROW-2"),
        _law(source_uri="https://www.law.go.kr/other"),
    ):
        assert not evidence_matches_verification(changed, statute_result)

    for changed in (
        _gazette(condition_name="다른구역"),
        _gazette(legal_basis="다른 법적 근거"),
        _gazette(gazette_issue_id="ISSUE-2"),
        _gazette(publication_date="2026-02-02"),
        _gazette(gazette_document_id="DOC-2"),
        _gazette(issuing_authority="다른기관"),
        _gazette(source_uri="https://gwanbo.go.kr/other"),
    ):
        assert not evidence_matches_verification(changed, gazette_result)

    # Metadata and verification gate flags are deliberately outside the identity hash.
    assert _law(metadata={"note": "A"}).identity_fingerprint() == statute.identity_fingerprint()
    assert _law(metadata={"note": "B"}).identity_fingerprint() == statute.identity_fingerprint()
    assert _law(official_source_qualified=False).identity_fingerprint() == statute.identity_fingerprint()

    for field, value in (
        ("official_source_qualified", False),
        ("law_identity_bound", False),
        ("version_identity_bound", False),
        ("effective_date_bound", False),
        ("appendix_identity_bound", False),
        ("row_identity_bound", False),
        ("condition_name_bound", False),
        ("legal_basis_bound", False),
        ("same_row_binding", False),
    ):
        result = verify_law_appendix_enumeration(_law(**{field: value}))
        assert result.status == UNVERIFIED and not result.verified
        assert result.evidence_fingerprint is None
        assert not evidence_matches_verification(_law(**{field: value}), result)

    for field in (
        "official_source_qualified", "issue_identity_bound",
        "publication_date_bound", "document_identity_bound",
        "issuing_authority_bound", "entry_identity_bound",
        "condition_name_bound", "legal_basis_bound", "same_entry_binding",
    ):
        evidence = _gazette(**{field: False})
        result = verify_official_gazette_enumeration(evidence)
        assert result.status == UNVERIFIED and not result.verified
        assert result.evidence_fingerprint is None
        assert not evidence_matches_verification(evidence, result)

    try:
        _law(source_family="OFFICIAL_GAZETTE")
        raise AssertionError("source-family mismatch must fail")
    except ValueError:
        pass

    try:
        _law(row_id=" ")
        raise AssertionError("incomplete row identity must fail")
    except ValueError:
        pass

    metadata_only = _law(
        official_source_qualified=False,
        law_identity_bound=False,
        version_identity_bound=False,
        effective_date_bound=False,
        appendix_identity_bound=False,
        row_identity_bound=False,
        condition_name_bound=False,
        legal_basis_bound=False,
        same_row_binding=False,
        metadata={"claimed_verified": True, "condition_name": "테스트구역"},
    )
    result = verify_law_appendix_enumeration(metadata_only)
    assert result.status == UNVERIFIED
    assert not result.source_identity_verified
    assert not result.row_binding_verified
    assert result.evidence_fingerprint is None
    assert not result.metadata_reconstruction_performed

    assert not statute_result.cross_document_reconstruction_performed
    assert not statute_result.cross_version_reconstruction_performed
    assert not statute_result.metadata_reconstruction_performed

    try:
        statute.condition_name = "변경"
        raise AssertionError("evidence must be frozen")
    except FrozenInstanceError:
        pass

    try:
        statute.metadata["x"] = 1
        raise AssertionError("metadata must be immutable")
    except TypeError:
        pass

    forbidden = {
        "standard_code", "condition_type", "resolution_type", "seed",
        "site_applicable", "runtime_registration_allowed",
    }
    assert forbidden.isdisjoint(statute_result.__dataclass_fields__)

    print("STEP96_VERIFIED_EVIDENCE_IDENTITY_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
