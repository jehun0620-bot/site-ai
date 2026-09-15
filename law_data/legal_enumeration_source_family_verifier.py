"""Fail-closed source-family verification for legal enumeration evidence.

This boundary verifies already-acquired legal enumeration evidence only. It does
not acquire sources, create catalogue seeds, infer standard codes or resolution
types, decide SITE applicability, or authorize production/runtime behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from types import MappingProxyType
from typing import Any, Mapping

from .legal_condition_catalogue_seed import (
    DECREE_APPENDIX,
    OFFICIAL_GAZETTE,
    STATUTE_APPENDIX,
)

VERIFIED = "VERIFIED"
UNVERIFIED = "UNVERIFIED"


def _clean_required(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} is required")
    return value.strip()


def _freeze(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping")
    return MappingProxyType(dict(value))


def _fingerprint(fields: tuple[str, ...]) -> str:
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LawAppendixEnumerationEvidence:
    source_family: str
    condition_name: str
    legal_basis: str
    law_id: str
    law_version_id: str
    effective_date: str
    appendix_id: str
    row_id: str
    source_uri: str
    official_source_qualified: bool = False
    law_identity_bound: bool = False
    version_identity_bound: bool = False
    effective_date_bound: bool = False
    appendix_identity_bound: bool = False
    row_identity_bound: bool = False
    condition_name_bound: bool = False
    legal_basis_bound: bool = False
    same_row_binding: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        family = _clean_required(self.source_family, "source_family").upper()
        if family not in {STATUTE_APPENDIX, DECREE_APPENDIX}:
            raise ValueError("law appendix evidence requires statute/decree source family")
        object.__setattr__(self, "source_family", family)
        for name in (
            "condition_name", "legal_basis", "law_id", "law_version_id",
            "effective_date", "appendix_id", "row_id", "source_uri",
        ):
            object.__setattr__(self, name, _clean_required(getattr(self, name), name))
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def identity_fingerprint(self) -> str:
        return _fingerprint((
            self.source_family,
            self.condition_name,
            self.legal_basis,
            self.law_id,
            self.law_version_id,
            self.effective_date,
            self.appendix_id,
            self.row_id,
            self.source_uri,
        ))


@dataclass(frozen=True)
class OfficialGazetteEnumerationEvidence:
    condition_name: str
    legal_basis: str
    gazette_issue_id: str
    publication_date: str
    gazette_document_id: str
    issuing_authority: str
    source_uri: str
    official_source_qualified: bool = False
    issue_identity_bound: bool = False
    publication_date_bound: bool = False
    document_identity_bound: bool = False
    issuing_authority_bound: bool = False
    entry_identity_bound: bool = False
    condition_name_bound: bool = False
    legal_basis_bound: bool = False
    same_entry_binding: bool = False
    metadata: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        for name in (
            "condition_name", "legal_basis", "gazette_issue_id",
            "publication_date", "gazette_document_id", "issuing_authority",
            "source_uri",
        ):
            object.__setattr__(self, name, _clean_required(getattr(self, name), name))
        object.__setattr__(self, "metadata", _freeze(self.metadata))

    def identity_fingerprint(self) -> str:
        return _fingerprint((
            OFFICIAL_GAZETTE,
            self.condition_name,
            self.legal_basis,
            self.gazette_issue_id,
            self.publication_date,
            self.gazette_document_id,
            self.issuing_authority,
            self.source_uri,
        ))


@dataclass(frozen=True)
class LegalEnumerationVerificationResult:
    source_family: str
    status: str
    source_identity_verified: bool
    row_binding_verified: bool
    exact_source_family_bound: bool
    source_document_identity_bound: bool
    row_or_entry_identity_bound: bool
    condition_name_bound: bool
    legal_basis_bound: bool
    evidence_fingerprint: str | None = None
    cross_document_reconstruction_performed: bool = False
    cross_version_reconstruction_performed: bool = False
    metadata_reconstruction_performed: bool = False

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.source_identity_verified
            and self.row_binding_verified
            and isinstance(self.evidence_fingerprint, str)
            and bool(self.evidence_fingerprint)
        )


def evidence_matches_verification(
    evidence: LawAppendixEnumerationEvidence | OfficialGazetteEnumerationEvidence,
    verification: LegalEnumerationVerificationResult,
) -> bool:
    """Return True only when a verified result is bound to this exact evidence."""
    if not isinstance(verification, LegalEnumerationVerificationResult):
        return False
    if not verification.verified:
        return False
    if isinstance(evidence, LawAppendixEnumerationEvidence):
        if verification.source_family != evidence.source_family:
            return False
    elif isinstance(evidence, OfficialGazetteEnumerationEvidence):
        if verification.source_family != OFFICIAL_GAZETTE:
            return False
    else:
        return False
    return verification.evidence_fingerprint == evidence.identity_fingerprint()


def verify_law_appendix_enumeration(
    evidence: LawAppendixEnumerationEvidence,
) -> LegalEnumerationVerificationResult:
    if not isinstance(evidence, LawAppendixEnumerationEvidence):
        raise TypeError("evidence must be LawAppendixEnumerationEvidence")

    exact_family = evidence.source_family in {STATUTE_APPENDIX, DECREE_APPENDIX}
    source_identity = all((
        exact_family,
        evidence.official_source_qualified is True,
        evidence.law_identity_bound is True,
        evidence.version_identity_bound is True,
        evidence.effective_date_bound is True,
        evidence.appendix_identity_bound is True,
    ))
    row_identity = evidence.row_identity_bound is True
    condition_bound = evidence.condition_name_bound is True
    basis_bound = evidence.legal_basis_bound is True
    row_binding = all((
        source_identity,
        row_identity,
        condition_bound,
        basis_bound,
        evidence.same_row_binding is True,
    ))

    return LegalEnumerationVerificationResult(
        source_family=evidence.source_family,
        status=VERIFIED if row_binding else UNVERIFIED,
        source_identity_verified=source_identity,
        row_binding_verified=row_binding,
        exact_source_family_bound=exact_family,
        source_document_identity_bound=source_identity,
        row_or_entry_identity_bound=row_identity,
        condition_name_bound=condition_bound,
        legal_basis_bound=basis_bound,
        evidence_fingerprint=evidence.identity_fingerprint() if row_binding else None,
    )


def verify_official_gazette_enumeration(
    evidence: OfficialGazetteEnumerationEvidence,
) -> LegalEnumerationVerificationResult:
    if not isinstance(evidence, OfficialGazetteEnumerationEvidence):
        raise TypeError("evidence must be OfficialGazetteEnumerationEvidence")

    source_identity = all((
        evidence.official_source_qualified is True,
        evidence.issue_identity_bound is True,
        evidence.publication_date_bound is True,
        evidence.document_identity_bound is True,
        evidence.issuing_authority_bound is True,
    ))
    entry_identity = evidence.entry_identity_bound is True
    condition_bound = evidence.condition_name_bound is True
    basis_bound = evidence.legal_basis_bound is True
    row_binding = all((
        source_identity,
        entry_identity,
        condition_bound,
        basis_bound,
        evidence.same_entry_binding is True,
    ))

    return LegalEnumerationVerificationResult(
        source_family=OFFICIAL_GAZETTE,
        status=VERIFIED if row_binding else UNVERIFIED,
        source_identity_verified=source_identity,
        row_binding_verified=row_binding,
        exact_source_family_bound=True,
        source_document_identity_bound=source_identity,
        row_or_entry_identity_bound=entry_identity,
        condition_name_bound=condition_bound,
        legal_basis_bound=basis_bound,
        evidence_fingerprint=evidence.identity_fingerprint() if row_binding else None,
    )
