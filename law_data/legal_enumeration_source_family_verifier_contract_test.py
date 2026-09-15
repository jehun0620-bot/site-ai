"""Focused contract tests for STEP93 source-family legal enumeration verifier."""

from dataclasses import FrozenInstanceError

from .legal_condition_catalogue_seed import DECREE_APPENDIX, STATUTE_APPENDIX
from .legal_enumeration_source_family_verifier import (
    UNVERIFIED,
    VERIFIED,
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
    result = verify_law_appendix_enumeration(statute)
    assert result.status == VERIFIED and result.verified
    assert result.source_family == STATUTE_APPENDIX

    decree = _law(source_family=DECREE_APPENDIX)
    result = verify_law_appendix_enumeration(decree)
    assert result.status == VERIFIED and result.source_family == DECREE_APPENDIX

    gazette = _gazette()
    result = verify_official_gazette_enumeration(gazette)
    assert result.status == VERIFIED and result.verified

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

    for field in (
        "official_source_qualified", "issue_identity_bound",
        "publication_date_bound", "document_identity_bound",
        "issuing_authority_bound", "entry_identity_bound",
        "condition_name_bound", "legal_basis_bound", "same_entry_binding",
    ):
        result = verify_official_gazette_enumeration(_gazette(**{field: False}))
        assert result.status == UNVERIFIED and not result.verified

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
    assert not result.metadata_reconstruction_performed

    result = verify_law_appendix_enumeration(_law(same_row_binding=False))
    assert not result.row_binding_verified
    result = verify_law_appendix_enumeration(_law(version_identity_bound=False))
    assert not result.source_identity_verified
    assert not result.row_binding_verified
    result = verify_official_gazette_enumeration(_gazette(same_entry_binding=False))
    assert not result.row_binding_verified
    result = verify_official_gazette_enumeration(_gazette(document_identity_bound=False))
    assert not result.source_identity_verified

    assert not result.cross_document_reconstruction_performed
    assert not result.cross_version_reconstruction_performed
    assert not result.metadata_reconstruction_performed

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
    assert forbidden.isdisjoint(result.__dataclass_fields__)

    print("STEP93_SOURCE_FAMILY_LEGAL_ENUMERATION_VERIFIER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
