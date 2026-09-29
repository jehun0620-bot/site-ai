# -*- coding: utf-8 -*-
"""Fail-closed semantic contracts for Building Act Enforcement Decree Annex 1.

This module does not infer semantic meaning from MAJOR/SUBITEM/DETAIL markers.
Only explicitly supplied, source-bound semantics are represented here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


ACTIVE = "ACTIVE"
DELETED = "DELETED"
UNRESOLVED = "UNRESOLVED"
VALID_STATUSES = frozenset({ACTIVE, DELETED, UNRESOLVED})

USE = "USE"
QUALIFICATION = "QUALIFICATION"
DELETED_ROLE = "DELETED"
UNRESOLVED_ROLE = "UNRESOLVED"
VALID_SEMANTIC_ROLES = frozenset(
    {USE, QUALIFICATION, DELETED_ROLE, UNRESOLVED_ROLE}
)


def _required(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} is required")
    return value.strip()


@dataclass(frozen=True)
class SourcePath:
    major: str
    subitem: str | None = None
    detail: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "major", _required(self.major, "major"))
        if self.subitem is not None:
            object.__setattr__(self, "subitem", _required(self.subitem, "subitem"))
        if self.detail is not None:
            if self.subitem is None:
                raise ValueError("detail requires subitem")
            if not isinstance(self.detail, int) or self.detail < 1:
                raise ValueError("detail must be a positive integer")

    @property
    def key(self) -> str:
        parts = [self.major]
        if self.subitem is not None:
            parts.append(self.subitem)
        if self.detail is not None:
            parts.append(str(self.detail))
        return "/".join(parts)


@dataclass(frozen=True)
class BuildingUseSemanticNode:
    source_path: SourcePath
    status: str = UNRESOLVED
    role: str = UNRESOLVED_ROLE
    canonical_name: str | None = None

    def __post_init__(self) -> None:
        status = _required(self.status, "status").upper()
        role = _required(self.role, "role").upper()
        if status not in VALID_STATUSES:
            raise ValueError(f"unsupported status: {status}")
        if role not in VALID_SEMANTIC_ROLES:
            raise ValueError(f"unsupported semantic role: {role}")
        if status == UNRESOLVED and role != UNRESOLVED_ROLE:
            raise ValueError("unresolved status requires unresolved role")
        if role == UNRESOLVED_ROLE and status != UNRESOLVED:
            raise ValueError("unresolved role requires unresolved status")
        if status == DELETED and role != DELETED_ROLE:
            raise ValueError("deleted status requires deleted role")
        if role == DELETED_ROLE and status != DELETED:
            raise ValueError("deleted role requires deleted status")
        if self.canonical_name is not None:
            object.__setattr__(self, "canonical_name", _required(self.canonical_name, "canonical_name"))
        if role == USE and self.canonical_name is None:
            raise ValueError("use role requires canonical_name")
        if role != USE and self.canonical_name is not None:
            raise ValueError("canonical_name is only valid for use role")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "role", role)


@dataclass(frozen=True)
class BuildingUseQualification:
    source_path: SourcePath
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "text", _required(self.text, "text"))


@dataclass(frozen=True)
class CanonicalBuildingUse:
    canonical_name: str
    source_path: SourcePath
    status: str = ACTIVE
    major_use: str | None = None
    parent_use: str | None = None
    qualifications: tuple[BuildingUseQualification, ...] = field(default_factory=tuple)
    raw_lines: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "canonical_name", _required(self.canonical_name, "canonical_name")
        )
        status = _required(self.status, "status").upper()
        if status not in VALID_STATUSES:
            raise ValueError(f"unsupported status: {status}")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "qualifications", tuple(self.qualifications))
        object.__setattr__(self, "raw_lines", tuple(self.raw_lines))

        if status == DELETED and self.qualifications:
            raise ValueError("deleted use cannot have active qualifications")

        for qualification in self.qualifications:
            if not isinstance(qualification, BuildingUseQualification):
                raise TypeError(
                    "qualifications must contain BuildingUseQualification objects"
                )


def qualification_paths(use: CanonicalBuildingUse) -> tuple[str, ...]:
    return tuple(item.source_path.key for item in use.qualifications)


def unresolved_source_paths(
    known_paths: Iterable[SourcePath],
    resolved_uses: Iterable[CanonicalBuildingUse],
) -> tuple[str, ...]:
    """Return source paths not explicitly represented by supplied semantics."""

    resolved = {item.source_path.key for item in resolved_uses}
    return tuple(path.key for path in known_paths if path.key not in resolved)
