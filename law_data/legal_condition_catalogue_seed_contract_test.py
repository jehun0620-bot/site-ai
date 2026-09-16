from __future__ import annotations

from dataclasses import FrozenInstanceError, fields

from law_data.legal_condition_catalogue_seed import (
    DECREE_APPENDIX,
    OFFICIAL_GAZETTE,
    STATUTE_APPENDIX,
    STATUTE_ARTICLE,
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)


def _expect_raises(exc_type, fn) -> None:
    try:
        fn()
    except exc_type:
        return
    raise AssertionError(f"expected {exc_type.__name__}")


def _verified_statute_provenance() -> LegalEnumerationProvenance:
    return LegalEnumerationProvenance(
        source_family=STATUTE_APPENDIX,
        source_uri="https://example.invalid/statute",
        law_id="LAW-ID",
        law_version_id="MST-1",
        effective_date="2026-01-01",
        appendix_id="APPENDIX-1",
        row_id="ROW-1",
        source_identity_verified=True,
        row_binding_verified=True,
    )


def test_verified_statute_seed_is_immutable_and_minimal() -> None:
    provenance = _verified_statute_provenance()
    seed = LegalConditionCatalogueSeed(
        condition_name="개발제한구역",
        legal_basis="국토의 계획 및 이용에 관한 법률",
        provenance=provenance,
    )

    assert provenance.provenance_verified is True
    assert seed.seed_verified is True
    assert seed.condition_name == "개발제한구역"

    seed_fields = {field.name for field in fields(LegalConditionCatalogueSeed)}
    assert seed_fields == {"condition_name", "legal_basis", "provenance"}
    for forbidden in (
        "standard_code",
        "condition_type",
        "resolution_type",
        "site_applicable",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert forbidden not in seed_fields
        assert not hasattr(seed, forbidden)

    _expect_raises(
        FrozenInstanceError,
        lambda: setattr(seed, "condition_name", "변조"),
    )


def test_verified_statute_article_seed_is_supported_and_minimal() -> None:
    provenance = LegalEnumerationProvenance(
        source_family=STATUTE_ARTICLE,
        source_uri="https://example.invalid/statute/article",
        law_id="LAW-ID",
        law_version_id="MST-3",
        effective_date="2026-04-01",
        article_id="ARTICLE-50",
        source_identity_verified=True,
        row_binding_verified=True,
    )
    seed = LegalConditionCatalogueSeed(
        condition_name="지구단위계획",
        legal_basis="국토의 계획 및 이용에 관한 법률 제50조",
        provenance=provenance,
    )

    assert provenance.provenance_verified is True
    assert seed.seed_verified is True
    assert provenance.article_id == "ARTICLE-50"
    assert provenance.appendix_id is None
    assert provenance.row_id is None
    assert {field.name for field in fields(LegalConditionCatalogueSeed)} == {
        "condition_name",
        "legal_basis",
        "provenance",
    }


def test_descriptive_identity_does_not_manufacture_verification() -> None:
    provenance = LegalEnumerationProvenance(
        source_family=DECREE_APPENDIX,
        law_id="DECREE-ID",
        law_version_id="MST-2",
        effective_date="2026-02-01",
        appendix_id="APPENDIX-1",
        row_id="ROW-2",
    )
    seed = LegalConditionCatalogueSeed(
        condition_name="테스트구역",
        legal_basis="테스트법",
        provenance=provenance,
    )

    assert provenance.source_identity_verified is False
    assert provenance.row_binding_verified is False
    assert provenance.provenance_verified is False
    assert seed.seed_verified is False


def test_verified_appendix_identity_requires_complete_identity() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_APPENDIX,
            law_id="LAW-ID",
            law_version_id="MST-1",
            effective_date="2026-01-01",
            appendix_id="APPENDIX-1",
            source_identity_verified=True,
        ),
    )


def test_verified_article_identity_requires_complete_identity() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_ARTICLE,
            law_id="LAW-ID",
            law_version_id="MST-3",
            effective_date="2026-04-01",
            source_identity_verified=True,
        ),
    )


def test_article_identity_rejects_appendix_or_gazette_synthesis() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_ARTICLE,
            law_id="LAW-ID",
            law_version_id="MST-3",
            effective_date="2026-04-01",
            article_id="ARTICLE-50",
            appendix_id="APPENDIX-1",
        ),
    )
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_ARTICLE,
            law_id="LAW-ID",
            law_version_id="MST-3",
            effective_date="2026-04-01",
            article_id="ARTICLE-50",
            gazette_issue_id="ISSUE-1",
        ),
    )


def test_article_item_requires_paragraph_identity() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_ARTICLE,
            law_id="LAW-ID",
            law_version_id="MST-3",
            effective_date="2026-04-01",
            article_id="ARTICLE-50",
            item_id="ITEM-1",
        ),
    )


def test_verified_gazette_identity_requires_complete_identity() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=OFFICIAL_GAZETTE,
            gazette_issue_id="ISSUE-1",
            publication_date="2026-03-01",
            issuing_authority="국토교통부",
            source_identity_verified=True,
        ),
    )


def test_cross_source_identity_synthesis_is_rejected() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=STATUTE_APPENDIX,
            law_id="LAW-ID",
            law_version_id="MST-1",
            effective_date="2026-01-01",
            appendix_id="APPENDIX-1",
            row_id="ROW-1",
            gazette_issue_id="ISSUE-1",
        ),
    )
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=OFFICIAL_GAZETTE,
            gazette_issue_id="ISSUE-1",
            publication_date="2026-03-01",
            gazette_document_id="DOC-1",
            issuing_authority="국토교통부",
            law_id="LAW-ID",
        ),
    )


def test_row_binding_cannot_be_verified_without_source_identity() -> None:
    _expect_raises(
        ValueError,
        lambda: LegalEnumerationProvenance(
            source_family=DECREE_APPENDIX,
            law_id="DECREE-ID",
            law_version_id="MST-2",
            effective_date="2026-02-01",
            appendix_id="APPENDIX-1",
            row_id="ROW-2",
            row_binding_verified=True,
        ),
    )


def test_seed_requires_explicit_identity_basis_and_typed_provenance() -> None:
    provenance = _verified_statute_provenance()
    _expect_raises(
        ValueError,
        lambda: LegalConditionCatalogueSeed("", "법률", provenance),
    )
    _expect_raises(
        ValueError,
        lambda: LegalConditionCatalogueSeed("구역", "", provenance),
    )
    _expect_raises(
        TypeError,
        lambda: LegalConditionCatalogueSeed("구역", "법률", {}),
    )


def run_contract_tests() -> None:
    test_verified_statute_seed_is_immutable_and_minimal()
    test_verified_statute_article_seed_is_supported_and_minimal()
    test_descriptive_identity_does_not_manufacture_verification()
    test_verified_appendix_identity_requires_complete_identity()
    test_verified_article_identity_requires_complete_identity()
    test_article_identity_rejects_appendix_or_gazette_synthesis()
    test_article_item_requires_paragraph_identity()
    test_verified_gazette_identity_requires_complete_identity()
    test_cross_source_identity_synthesis_is_rejected()
    test_row_binding_cannot_be_verified_without_source_identity()
    test_seed_requires_explicit_identity_basis_and_typed_provenance()
    print("STEP88_MINIMAL_LEGAL_CATALOGUE_SEED_CONTRACT_PASS")


if __name__ == "__main__":
    run_contract_tests()
