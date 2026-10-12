# -*- coding: utf-8 -*-
"""Immutable legal-source identity and version inventory, NOT a law resolver.

Entries are caller-supplied *descriptive* metadata. No official API is queried,
no supplied name/URI/date is independently verified, and no SITE applicability,
legal authority, current validity, or production admission is inferred here.

SOURCE_VERIFIED is deliberately unavailable until a separately audited source
qualification/admission path exists. This registry cannot grant that authority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import urlsplit


SOURCE_TYPES = frozenset({"NATIONAL_LAW", "NATIONAL_SUBORDINATE", "LOCAL_ORDINANCE"})
JURISDICTION_LEVELS = frozenset({"NATIONAL", "SIDO", "SIGUNGU"})
SOURCE_STATES = frozenset({"NOT_VERIFIED", "REVIEW_REQUIRED"})
_ASCII_DIGITS = re.compile(r"[0-9]+\Z")
_ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\Z")


class LegalSourceIdentityConflictError(ValueError):
    """A single provider source identity has contradictory kind or scope."""


class LegalSourceVersionConflictError(ValueError):
    """One explicit source version has inconsistent descriptive metadata."""


def _required_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value.strip()


def _optional_text(name: str, value: object) -> str | None:
    if value is None:
        return None
    return _required_text(name, value)


def _optional_iso_date(name: str, value: object) -> str | None:
    value = _optional_text(name, value)
    if value is None:
        return None
    if _ISO_DATE.fullmatch(value) is None:
        raise ValueError(f"{name} must be YYYY-MM-DD, or absent")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be a valid calendar date") from exc
    return value


def _optional_uri(value: object) -> str | None:
    uri = _optional_text("source_uri", value)
    if uri is None:
        return None
    parsed = urlsplit(uri)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("source_uri must be an absolute HTTP(S) URL, or absent")
    return uri  # A plausible URL is NOT evidence of an official source.


@dataclass(frozen=True, slots=True)
class LegalSourceRecord:
    """A versioned inventory row with explicitly unapproved legal decisions.

    Provider source identity is (source_system, source_namespace, source_id).
    source_namespace distinguishes collections like law and ordin; identifiers
    in different namespaces are not assumed to represent the same source.
    version_id=None denotes an *unknown* version, not the latest one.
    """

    source_system: str
    source_namespace: str
    source_id: str
    title: str
    source_type: str
    jurisdiction_level: str
    jurisdiction_code: str | None = None
    version_id: str | None = None
    source_uri: str | None = None
    promulgation_date: str | None = None
    effective_date: str | None = None
    revision_label: str | None = None
    source_state: str = "NOT_VERIFIED"

    def __post_init__(self) -> None:
        for name in ("source_system", "source_namespace", "source_id", "title"):
            object.__setattr__(self, name, _required_text(name, getattr(self, name)))

        if self.source_type not in SOURCE_TYPES:
            raise ValueError(f"unsupported source_type: {self.source_type!r}")
        if self.jurisdiction_level not in JURISDICTION_LEVELS:
            raise ValueError(f"unsupported jurisdiction_level: {self.jurisdiction_level!r}")
        if self.source_state not in SOURCE_STATES:
            raise ValueError("source_state cannot self-promote legal source verification")

        code = _optional_text("jurisdiction_code", self.jurisdiction_code)
        if self.jurisdiction_level == "NATIONAL":
            if code is not None or self.source_type == "LOCAL_ORDINANCE":
                raise ValueError("national sources cannot carry a local jurisdiction")
        else:
            if self.source_type != "LOCAL_ORDINANCE":
                raise ValueError("national-law source types must use NATIONAL jurisdiction")
            width = 2 if self.jurisdiction_level == "SIDO" else 5
            if code is None or len(code) != width or _ASCII_DIGITS.fullmatch(code) is None:
                raise ValueError(f"{self.jurisdiction_level} code must have {width} ASCII digits")

        object.__setattr__(self, "jurisdiction_code", code)
        object.__setattr__(self, "version_id", _optional_text("version_id", self.version_id))
        object.__setattr__(self, "source_uri", _optional_uri(self.source_uri))
        object.__setattr__(self, "promulgation_date", _optional_iso_date("promulgation_date", self.promulgation_date))
        object.__setattr__(self, "effective_date", _optional_iso_date("effective_date", self.effective_date))
        object.__setattr__(self, "revision_label", _optional_text("revision_label", self.revision_label))

    @property
    def source_key(self) -> tuple[str, str, str]:
        return self.source_system, self.source_namespace, self.source_id

    @property
    def version_key(self) -> tuple[str, str, str, str | None]:
        return (*self.source_key, self.version_id)

    def to_dict(self) -> dict[str, str | None]:
        return {
            "source_system": self.source_system,
            "source_namespace": self.source_namespace,
            "source_id": self.source_id,
            "title": self.title,
            "source_type": self.source_type,
            "jurisdiction_level": self.jurisdiction_level,
            "jurisdiction_code": self.jurisdiction_code,
            "version_id": self.version_id,
            "source_uri": self.source_uri,
            "promulgation_date": self.promulgation_date,
            "effective_date": self.effective_date,
            "revision_label": self.revision_label,
            "source_state": self.source_state,
            "source_identity_basis": "CALLER_SUPPLIED_UNVERIFIED",
            "current_validity_decision": "NOT_EVALUATED",
            "legal_authority_decision": "NOT_EVALUATED",
            "legal_applicability_decision": "NOT_EVALUATED",
            "production_admission_decision": "NOT_EVALUATED",
        }


@dataclass(frozen=True, slots=True)
class LegalSourceRegistry:
    """Immutable, deduplicated inventory; no latest-version selection."""

    records: tuple[LegalSourceRecord, ...] = ()

    def __post_init__(self) -> None:
        identities: dict[tuple[str, str, str], tuple[str, str, str | None]] = {}
        versions: dict[tuple[str, str, str, str | None], LegalSourceRecord] = {}
        unique: list[LegalSourceRecord] = []
        if isinstance(self.records, (str, bytes)):
            raise TypeError("records must contain LegalSourceRecord entries")
        for record in self.records:
            if not isinstance(record, LegalSourceRecord):
                raise TypeError("every record must be LegalSourceRecord")
            binding = (record.source_type, record.jurisdiction_level, record.jurisdiction_code)
            previous_binding = identities.get(record.source_key)
            if previous_binding is not None and previous_binding != binding:
                raise LegalSourceIdentityConflictError(
                    f"contradictory source identity/scope: {record.source_key!r}"
                )
            identities[record.source_key] = binding
            previous_version = versions.get(record.version_key)
            if previous_version is not None:
                if previous_version != record:
                    raise LegalSourceVersionConflictError(
                        f"conflicting version metadata: {record.version_key!r}"
                    )
                continue  # Exact duplicates are idempotent, not extra versions.
            versions[record.version_key] = record
            unique.append(record)
        object.__setattr__(self, "records", tuple(unique))

    def versions_for(self, source_system: str, source_namespace: str, source_id: str) -> tuple[LegalSourceRecord, ...]:
        """All candidate versions, including unknown; no presumed current one."""
        source_key = (source_system, source_namespace, source_id)
        return tuple(record for record in self.records if record.source_key == source_key)

    def version_exact(
        self, source_system: str, source_namespace: str, source_id: str,
        version_id: str | None,
    ) -> LegalSourceRecord | None:
        """Exact lookup only. None denotes the unknown-version row, NOT latest."""
        key = (source_system, source_namespace, source_id, version_id)
        return next((record for record in self.records if record.version_key == key), None)


def build_legal_source_registry(records: tuple[LegalSourceRecord, ...] | list[LegalSourceRecord]) -> LegalSourceRegistry:
    """Create a read-only inventory without network, disk, or law decisions."""
    return LegalSourceRegistry(records=records)
