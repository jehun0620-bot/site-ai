# -*- coding: utf-8 -*-
"""Derived UI catalog for verified Building Act Enforcement Decree Annex 1 uses.

This module does not create new legal semantics. It derives selectable catalog
entries only from the production semantic registry and explicit canonical
registry. Unsupported semantic roles remain fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_data.building_use_annex1_canonical_registry import canonical_uses_for_path
from law_data.building_use_annex1_semantic_model import (
    ACTIVE,
    CATEGORY,
    MULTI_USE,
    USE,
    SourcePath,
)
from law_data.building_use_annex1_semantic_registry import VERIFIED_SEMANTICS


@dataclass(frozen=True)
class BuildingUseCatalogEntry:
    major_use: str
    canonical_name: str
    source_path: SourcePath
    semantic_role: str
    selectable: bool = True


def _major_category_name(source_path: SourcePath) -> str | None:
    major_node = VERIFIED_SEMANTICS.get(source_path.major)
    if (
        major_node is not None
        and major_node.status == ACTIVE
        and major_node.role == CATEGORY
        and major_node.canonical_name is not None
    ):
        return major_node.canonical_name
    return None


def _major_use_name(source_path: SourcePath, canonical_major_use: str | None = None) -> str:
    category_name = _major_category_name(source_path)
    if category_name is not None:
        return category_name
    if canonical_major_use is not None and canonical_major_use.strip():
        return canonical_major_use.strip()

    major_node = VERIFIED_SEMANTICS.get(source_path.major)
    if (
        major_node is not None
        and major_node.status == ACTIVE
        and major_node.role == USE
        and major_node.canonical_name is not None
    ):
        return major_node.canonical_name

    raise ValueError(f"verified major use/category missing for source path: {source_path.key}")


def build_canonical_catalog() -> tuple[BuildingUseCatalogEntry, ...]:
    entries: list[BuildingUseCatalogEntry] = []

    for source_key, semantic in VERIFIED_SEMANTICS.items():
        if semantic.source_path.key != source_key:
            raise ValueError(
                f"semantic registry key mismatch: {source_key} != {semantic.source_path.key}"
            )
        if semantic.status != ACTIVE:
            continue

        if semantic.role == USE:
            if semantic.canonical_name is None:
                raise ValueError(f"USE missing canonical_name: {source_key}")
            entries.append(
                BuildingUseCatalogEntry(
                    major_use=_major_use_name(semantic.source_path),
                    canonical_name=semantic.canonical_name,
                    source_path=semantic.source_path,
                    semantic_role=USE,
                )
            )
            continue

        if semantic.role == MULTI_USE:
            canonical_uses = canonical_uses_for_path(semantic.source_path)
            if not canonical_uses:
                raise ValueError(
                    f"MULTI_USE has no explicit canonical registry entries: {source_key}"
                )
            for canonical_use in canonical_uses:
                entries.append(
                    BuildingUseCatalogEntry(
                        major_use=_major_use_name(
                            semantic.source_path,
                            canonical_use.major_use,
                        ),
                        canonical_name=canonical_use.canonical_name,
                        source_path=semantic.source_path,
                        semantic_role=MULTI_USE,
                    )
                )

    return tuple(entries)


def catalog_entries_for_name(
    canonical_name: str,
) -> tuple[BuildingUseCatalogEntry, ...]:
    name = canonical_name.strip()
    if not name:
        raise ValueError("canonical_name is required")
    return tuple(
        entry
        for entry in build_canonical_catalog()
        if entry.canonical_name == name
    )
