"""Minimal fail-closed pre-profile legal condition catalogue seed contract.

This module preserves only legal enumeration identity, legal basis, and
reproducible source provenance. It does not classify a condition, infer a
standard code, admit a RegulationResolutionProfile, decide SITE applicability,
or authorize production/runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


BOUNDARY_NAME = "LEGAL_CONDITION_CATALOGUE_SEED"

STATUTE_APPENDIX = "STATUTE_APPENDIX"
DECREE_APPENDIX = "DECREE_APPENDIX"
STATUTE_ARTICLE = "STATUTE_ARTICLE"
DECREE_ARTICLE = "DECREE_ARTICLE"
OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE"

VALID_SOURCE_FAMILIES = frozenset(
    {
        STATUTE_APPENDIX,
        DECREE_APPENDIX,
        STATUTE_ARTICLE,
        DECREE_ARTICLE,
        OFFICIAL_GAZETTE,
    }
)


def _clean_required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _clean_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _freeze_metadata(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class LegalEnumerationProvenance:
    """Reproducible source-family-specific identity for one legal enumeration.

    Verification is explicit and fail-closed. Descriptive identifiers never
    manufacture verification. A verified provenance must contain one complete
    identity family and may not mix article, appendix, or official-gazette
    identifiers.
    """

    source_family: str

    source_uri: str | None = None

    law_id: str | None = None
    law_version_id: str | None = None
    effective_date: str | None = None
    article_id: str | None = None
    paragraph_id: str | None = None
    item_id: str | None = None
    appendix_id: str | None = None
    row_id: str | None = None

    gazette_issue_id: str | None = None
    publication_date: str | None = None
    gazette_document_id: str | None = None
    issuing_authority: str | None = None

    source_identity_verified: bool = False
    row_binding_verified: bool = False

    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        source_family = _clean_required_text(
            self.source_family, "source_family"
        ).upper()
        if source_family not in VALID_SOURCE_FAMILIES:
            raise ValueError(f"unsupported source_family: {source_family!r}")

        fields = {
            "source_uri": _clean_optional_text(self.source_uri),
            "law_id": _clean_optional_text(self.law_id),
            "law_version_id": _clean_optional_text(self.law_version_id),
            "effective_date": _clean_optional_text(self.effective_date),
            "article_id": _clean_optional_text(self.article_id),
            "paragraph_id": _clean_optional_text(self.paragraph_id),
            "item_id": _clean_optional_text(self.item_id),
            "appendix_id": _clean_optional_text(self.appendix_id),
            "row_id": _clean_optional_text(self.row_id),
            "gazette_issue_id": _clean_optional_text(self.gazette_issue_id),
            "publication_date": _clean_optional_text(self.publication_date),
            "gazette_document_id": _clean_optional_text(self.gazette_document_id),
            "issuing_authority": _clean_optional_text(self.issuing_authority),
        }

        law_core_fields = (
            fields["law_id"],
            fields["law_version_id"],
            fields["effective_date"],
        )
        article_locator_fields = (
            fields["article_id"],
            fields["paragraph_id"],
            fields["item_id"],
        )
        appendix_locator_fields = (
            fields["appendix_id"],
            fields["row_id"],
        )
        gazette_fields = (
            fields["gazette_issue_id"],
            fields["publication_date"],
            fields["gazette_document_id"],
            fields["issuing_authority"],
        )

        if source_family in {STATUTE_APPENDIX, DECREE_APPENDIX}:
            if any(article_locator_fields) or any(gazette_fields):
                raise ValueError(
                    "appendix provenance cannot contain article or official-gazette identity fields"
                )
            required = law_core_fields + appendix_locator_fields
        elif source_family in {STATUTE_ARTICLE, DECREE_ARTICLE}:
            if any(appendix_locator_fields) or any(gazette_fields):
                raise ValueError(
                    "article provenance cannot contain appendix or official-gazette identity fields"
                )
            required = law_core_fields + (fields["article_id"],)
            if fields["item_id"] and not fields["paragraph_id"]:
                raise ValueError("item_id requires paragraph_id for article provenance")
        else:
            if any(law_core_fields) or any(article_locator_fields) or any(
                appendix_locator_fields
            ):
                raise ValueError(
                    "official-gazette provenance cannot contain statute/decree identity fields"
                )
            required = gazette_fields

        source_identity_verified = self.source_identity_verified is True
        row_binding_verified = self.row_binding_verified is True

        if source_identity_verified and not all(required):
            raise ValueError(
                "source_identity_verified requires a complete source-family identity"
            )
        if row_binding_verified and not source_identity_verified:
            raise ValueError(
                "row_binding_verified requires verified source identity"
            )

        object.__setattr__(self, "source_family", source_family)
        for field_name, value in fields.items():
            object.__setattr__(self, field_name, value)
        object.__setattr__(
            self, "source_identity_verified", source_identity_verified
        )
        object.__setattr__(self, "row_binding_verified", row_binding_verified)
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def provenance_verified(self) -> bool:
        return self.source_identity_verified and self.row_binding_verified

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_family": self.source_family,
            "source_uri": self.source_uri,
            "law_id": self.law_id,
            "law_version_id": self.law_version_id,
            "effective_date": self.effective_date,
            "article_id": self.article_id,
            "paragraph_id": self.paragraph_id,
            "item_id": self.item_id,
            "appendix_id": self.appendix_id,
            "row_id": self.row_id,
            "gazette_issue_id": self.gazette_issue_id,
            "publication_date": self.publication_date,
            "gazette_document_id": self.gazette_document_id,
            "issuing_authority": self.issuing_authority,
            "source_identity_verified": self.source_identity_verified,
            "row_binding_verified": self.row_binding_verified,
            "provenance_verified": self.provenance_verified,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class LegalConditionCatalogueSeed:
    """Immutable pre-profile record for one legally enumerated condition."""

    condition_name: str
    legal_basis: str
    provenance: LegalEnumerationProvenance

    def __post_init__(self) -> None:
        condition_name = _clean_required_text(self.condition_name, "condition_name")
        legal_basis = _clean_required_text(self.legal_basis, "legal_basis")
        if not isinstance(self.provenance, LegalEnumerationProvenance):
            raise TypeError(
                "provenance must be an exact LegalEnumerationProvenance contract"
            )
        object.__setattr__(self, "condition_name", condition_name)
        object.__setattr__(self, "legal_basis", legal_basis)

    @property
    def seed_verified(self) -> bool:
        return self.provenance.provenance_verified

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_name": BOUNDARY_NAME,
            "condition_name": self.condition_name,
            "legal_basis": self.legal_basis,
            "provenance": self.provenance.to_dict(),
            "seed_verified": self.seed_verified,
        }
