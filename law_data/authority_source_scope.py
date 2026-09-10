"""Fail-closed authority/source qualification boundary.

This module owns only source qualification metadata. It does not execute a
resolver, verify legal facts by inference, decide SITE applicability, mutate
Rule Engine input, register runtime logic, or expose a public API contract.

A source may carry descriptive metadata (for example an official-looking host,
region name, PRIMARY role, legal scope text, or regulation name) without that
metadata being independently verified. Verification flags therefore never
become True merely because descriptive values are present.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlparse


BOUNDARY_NAME = "AUTHORITY_SOURCE_SCOPE"


_VALID_SOURCE_ROLES = frozenset(
    {
        "PRIMARY",
        "SECONDARY",
        "REFERENCE",
        "DISCOVERY",
        "UNKNOWN",
    }
)


def _clean_optional_text(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    cleaned = value.strip()
    return cleaned or None


def _normalize_source_role(value: object) -> str | None:
    cleaned = _clean_optional_text(value)
    if cleaned is None:
        return None
    normalized = cleaned.upper()
    if normalized not in _VALID_SOURCE_ROLES:
        return None
    return normalized


def _freeze_diagnostics(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    if value is None:
        return MappingProxyType({})
    if not isinstance(value, Mapping):
        raise TypeError("diagnostics must be a mapping")
    return MappingProxyType(dict(value))


@dataclass(frozen=True)
class AuthoritySourceScope:
    """Read-only source qualification metadata with explicit verification.

    Descriptive metadata and verification state are intentionally separate.
    Presence of a URI, host, region, role, authority scope, or regulation name
    never implies that the corresponding authority fact is verified.
    """

    source_uri: str | None = None
    source_host: str | None = None

    official_host_verified: bool = False

    region_binding: str | None = None
    region_binding_verified: bool = False

    source_role: str | None = None
    source_role_verified: bool = False

    legal_authority_scope: str | None = None
    legal_authority_scope_verified: bool = False

    target_regulation: str | None = None
    target_regulation_compatible: bool | None = None
    target_regulation_compatibility_verified: bool = False

    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        source_uri = _clean_optional_text(self.source_uri)
        source_host = _clean_optional_text(self.source_host)
        region_binding = _clean_optional_text(self.region_binding)
        source_role = _normalize_source_role(self.source_role)
        legal_authority_scope = _clean_optional_text(self.legal_authority_scope)
        target_regulation = _clean_optional_text(self.target_regulation)

        if source_uri is not None and source_host is None:
            parsed = urlparse(source_uri)
            source_host = _clean_optional_text(parsed.hostname)

        official_host_verified = self.official_host_verified is True
        region_binding_verified = self.region_binding_verified is True
        source_role_verified = self.source_role_verified is True
        legal_authority_scope_verified = self.legal_authority_scope_verified is True
        compatibility_verified = self.target_regulation_compatibility_verified is True

        if official_host_verified and source_host is None:
            raise ValueError("official_host_verified requires an explicit source_host")
        if region_binding_verified and region_binding is None:
            raise ValueError("region_binding_verified requires an explicit region_binding")
        if source_role_verified and source_role is None:
            raise ValueError("source_role_verified requires an explicit recognized source_role")
        if legal_authority_scope_verified and legal_authority_scope is None:
            raise ValueError(
                "legal_authority_scope_verified requires an explicit legal_authority_scope"
            )
        if compatibility_verified:
            if target_regulation is None:
                raise ValueError(
                    "target_regulation_compatibility_verified requires an explicit target_regulation"
                )
            if self.target_regulation_compatible is not True and self.target_regulation_compatible is not False:
                raise ValueError(
                    "verified target regulation compatibility requires explicit True or False"
                )

        object.__setattr__(self, "source_uri", source_uri)
        object.__setattr__(self, "source_host", source_host)
        object.__setattr__(self, "official_host_verified", official_host_verified)
        object.__setattr__(self, "region_binding", region_binding)
        object.__setattr__(self, "region_binding_verified", region_binding_verified)
        object.__setattr__(self, "source_role", source_role)
        object.__setattr__(self, "source_role_verified", source_role_verified)
        object.__setattr__(self, "legal_authority_scope", legal_authority_scope)
        object.__setattr__(
            self,
            "legal_authority_scope_verified",
            legal_authority_scope_verified,
        )
        object.__setattr__(self, "target_regulation", target_regulation)
        object.__setattr__(
            self,
            "target_regulation_compatible",
            self.target_regulation_compatible
            if self.target_regulation_compatible is True
            or self.target_regulation_compatible is False
            else None,
        )
        object.__setattr__(
            self,
            "target_regulation_compatibility_verified",
            compatibility_verified,
        )
        object.__setattr__(self, "diagnostics", _freeze_diagnostics(self.diagnostics))

    @property
    def authority_chain_verified(self) -> bool:
        """True only when every positive authority qualification gate is verified."""

        return (
            self.official_host_verified
            and self.region_binding_verified
            and self.source_role_verified
            and self.legal_authority_scope_verified
            and self.target_regulation_compatibility_verified
            and self.target_regulation_compatible is True
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "boundary_name": BOUNDARY_NAME,
            "source_uri": self.source_uri,
            "source_host": self.source_host,
            "official_host_verified": self.official_host_verified,
            "region_binding": self.region_binding,
            "region_binding_verified": self.region_binding_verified,
            "source_role": self.source_role,
            "source_role_verified": self.source_role_verified,
            "legal_authority_scope": self.legal_authority_scope,
            "legal_authority_scope_verified": self.legal_authority_scope_verified,
            "target_regulation": self.target_regulation,
            "target_regulation_compatible": self.target_regulation_compatible,
            "target_regulation_compatibility_verified": self.target_regulation_compatibility_verified,
            "authority_chain_verified": self.authority_chain_verified,
            "diagnostics": dict(self.diagnostics),
        }


def normalize_authority_source_scope(
    value: AuthoritySourceScope | Mapping[str, Any] | None,
) -> AuthoritySourceScope:
    """Normalize source metadata without manufacturing verification evidence."""

    if value is None:
        return AuthoritySourceScope()
    if isinstance(value, AuthoritySourceScope):
        return value
    if not isinstance(value, Mapping):
        raise TypeError("authority source scope must be a mapping or AuthoritySourceScope")

    return AuthoritySourceScope(
        source_uri=value.get("source_uri"),
        source_host=value.get("source_host"),
        official_host_verified=value.get("official_host_verified") is True,
        region_binding=value.get("region_binding"),
        region_binding_verified=value.get("region_binding_verified") is True,
        source_role=value.get("source_role"),
        source_role_verified=value.get("source_role_verified") is True,
        legal_authority_scope=value.get("legal_authority_scope"),
        legal_authority_scope_verified=value.get("legal_authority_scope_verified") is True,
        target_regulation=value.get("target_regulation"),
        target_regulation_compatible=(
            value.get("target_regulation_compatible")
            if value.get("target_regulation_compatible") is True
            or value.get("target_regulation_compatible") is False
            else None
        ),
        target_regulation_compatibility_verified=(
            value.get("target_regulation_compatibility_verified") is True
        ),
        diagnostics=value.get("diagnostics") if isinstance(value.get("diagnostics"), Mapping) else {},
    )
