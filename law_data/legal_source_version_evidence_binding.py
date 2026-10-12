# -*- coding: utf-8 -*-
"""Read-only, fail-closed identity binding of a source version to an evidence reference.

All fields are caller-supplied descriptions, NOT independently checked source
facts. An exact identity match, plausible URI, or declared SHA-256 value never
proves an official original, content equality, legal effectiveness, competent
authority, parcel applicability, or permission to enter production.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from urllib.parse import urlsplit

from law_data.legal_source_registry import (
    JURISDICTION_LEVELS,
    SOURCE_TYPES,
    LegalSourceRecord,
)

_HEX_SHA256 = re.compile(r"[0-9a-fA-F]{64}\Z")
_ASCII_DIGITS = re.compile(r"[0-9]+\Z")
NOT_EVALUATED = "NOT_EVALUATED"


def _required(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional(name: str, value: object) -> str | None:
    return None if value is None else _required(name, value)


@dataclass(frozen=True, slots=True)
class LegalSourceVersionEvidenceReference:
    """A *claimed* evidence identity; no verification flags are accepted.

    evidence_id must identify an evidence artifact, not merely a law identifier.
    declared_sha256 is caller-provided text and is NEVER computed or confirmed.
    """

    source_system: str
    source_namespace: str
    source_id: str
    version_id: str | None
    source_type: str
    jurisdiction_level: str
    jurisdiction_code: str | None
    evidence_id: str
    evidence_uri: str | None = None
    declared_sha256: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("source_system", "source_namespace", "source_id", "evidence_id"):
            object.__setattr__(self, field_name, _required(field_name, getattr(self, field_name)))
        object.__setattr__(self, "version_id", _optional("version_id", self.version_id))

        if self.source_type not in SOURCE_TYPES:
            raise ValueError("unsupported source_type")
        if self.jurisdiction_level not in JURISDICTION_LEVELS:
            raise ValueError("unsupported jurisdiction_level")
        code = _optional("jurisdiction_code", self.jurisdiction_code)
        if self.jurisdiction_level == "NATIONAL":
            if code is not None or self.source_type == "LOCAL_ORDINANCE":
                raise ValueError("invalid national source scope")
        else:
            width = 2 if self.jurisdiction_level == "SIDO" else 5
            if (
                self.source_type != "LOCAL_ORDINANCE"
                or code is None
                or len(code) != width
                or _ASCII_DIGITS.fullmatch(code) is None
            ):
                raise ValueError("invalid local source scope")
        object.__setattr__(self, "jurisdiction_code", code)

        uri = _optional("evidence_uri", self.evidence_uri)
        if uri is not None:
            parsed = urlsplit(uri)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname:
                raise ValueError("evidence_uri must be an absolute HTTP(S) URL")
        object.__setattr__(self, "evidence_uri", uri)
        digest = _optional("declared_sha256", self.declared_sha256)
        if digest is not None and _HEX_SHA256.fullmatch(digest) is None:
            raise ValueError("declared_sha256 must be 64 ASCII hexadecimal characters")
        object.__setattr__(self, "declared_sha256", digest.lower() if digest is not None else None)

    @property
    def source_key(self) -> tuple[str, str, str]:
        return self.source_system, self.source_namespace, self.source_id

    @property
    def version_key(self) -> tuple[str, str, str, str | None]:
        return (*self.source_key, self.version_id)

    @property
    def evidence_key(self) -> tuple[str, str, str]:
        """Local collision key only; no global evidence uniqueness is claimed."""
        return self.source_system, self.source_namespace, self.evidence_id


@dataclass(frozen=True, slots=True)
class LegalSourceVersionEvidenceBinding:
    """Immutable diagnostic; even an aligned row remains entirely unverified."""

    status: str
    source_key: tuple[str, str, str]
    version_key: tuple[str, str, str, str | None]
    reference_version_key: tuple[str, str, str, str | None]
    evidence_key: tuple[str, str, str]
    source_identity_aligned: bool
    exact_version_aligned: bool
    declared_scope_aligned: bool
    evidence_reference_collision: bool
    missing_reference_fields: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "source_key": list(self.source_key),
            "version_key": list(self.version_key),
            "reference_version_key": list(self.reference_version_key),
            "evidence_key": list(self.evidence_key),
            "source_identity_aligned": self.source_identity_aligned,
            "exact_version_aligned": self.exact_version_aligned,
            "declared_scope_aligned": self.declared_scope_aligned,
            "evidence_reference_collision": self.evidence_reference_collision,
            "missing_reference_fields": list(self.missing_reference_fields),
            "source_identity_basis": "CALLER_SUPPLIED_UNVERIFIED",
            "source_verification_decision": NOT_EVALUATED,
            "original_text_identity_decision": NOT_EVALUATED,
            "current_validity_decision": NOT_EVALUATED,
            "legal_authority_decision": NOT_EVALUATED,
            "legal_applicability_decision": NOT_EVALUATED,
            "production_admission_decision": NOT_EVALUATED,
        }


def bind_legal_source_version_evidence(
    record: LegalSourceRecord,
    reference: LegalSourceVersionEvidenceReference,
    *,
    known_references: tuple[LegalSourceVersionEvidenceReference, ...] = (),
) -> LegalSourceVersionEvidenceBinding:
    """Compare declared identities without verifying provenance or granting access.

    known_references is an optional, caller-provided snapshot for *local*
    evidence-ID collision detection; absence of collisions in it is NOT proof
    that no other references exist. Distinct evidence IDs may still refer to the
    same actual document; only independent inspection could resolve that.
    """
    if not isinstance(record, LegalSourceRecord):
        raise TypeError("record must be LegalSourceRecord")
    if not isinstance(reference, LegalSourceVersionEvidenceReference):
        raise TypeError("reference must be LegalSourceVersionEvidenceReference")
    if not isinstance(known_references, tuple) or any(
        not isinstance(item, LegalSourceVersionEvidenceReference)
        for item in known_references
    ):
        raise TypeError("known_references must be a tuple of evidence references")

    source_aligned = record.source_key == reference.source_key
    version_aligned = bool(
        source_aligned
        and record.version_id is not None
        and reference.version_id is not None
        and record.version_id == reference.version_id
    )
    scope_aligned = (
        record.source_type == reference.source_type
        and record.jurisdiction_level == reference.jurisdiction_level
        and record.jurisdiction_code == reference.jurisdiction_code
    )
    collision = any(
        other.evidence_key == reference.evidence_key
        and other.version_key != reference.version_key
        for other in known_references
    )
    missing = tuple(
        name for name in ("evidence_uri", "declared_sha256")
        if getattr(reference, name) is None
    )

    if not source_aligned:
        status = "SOURCE_IDENTITY_MISMATCH"
    elif record.version_id is None or reference.version_id is None:
        status = "VERSION_UNKNOWN"
    elif not version_aligned:
        status = "VERSION_MISMATCH"
    elif not scope_aligned:
        status = "DECLARED_SCOPE_MISMATCH"
    elif collision:
        status = "EVIDENCE_REFERENCE_COLLISION"
    elif missing:
        status = "EVIDENCE_REFERENCE_INCOMPLETE"
    else:
        status = "IDENTITY_ALIGNED_UNVERIFIED"

    return LegalSourceVersionEvidenceBinding(
        status=status,
        source_key=record.source_key,
        version_key=record.version_key,
        reference_version_key=reference.version_key,
        evidence_key=reference.evidence_key,
        source_identity_aligned=source_aligned,
        exact_version_aligned=version_aligned,
        declared_scope_aligned=scope_aligned,
        evidence_reference_collision=collision,
        missing_reference_fields=missing,
    )
