# -*- coding: utf-8 -*-

"""Fail-closed BUILDING_USE fact boundary for final Annex 1 classification."""

from __future__ import annotations

from dataclasses import dataclass

from law_data.building_use_annex1_final_classifier import (
    BuildingUseFinalClassification,
    RESOLVED,
)


@dataclass(frozen=True)
class BuildingUseFact:
    """A confirmed Annex 1 building-use fact safe for downstream consumption."""

    canonical_name: str
    major_use: str
    source_path: str
    classification_status: str = RESOLVED


def _source_path_text(result: BuildingUseFinalClassification) -> str:
    selected = result.selected_candidate
    if selected is None:
        raise ValueError("RESOLVED building use requires selected candidate")

    path = selected.entry.source_path
    value = path.major

    if path.subitem is not None:
        value += f"/{path.subitem}"

    if path.detail is not None:
        value += f"/{path.detail}"

    return value


def building_use_fact_from_final(
    result: BuildingUseFinalClassification,
) -> BuildingUseFact | None:
    """Return a confirmed fact only for a RESOLVED final classification."""

    if result.status != RESOLVED:
        return None

    selected = result.selected_candidate
    if selected is None:
        raise ValueError("RESOLVED building use requires selected candidate")

    entry = selected.entry

    return BuildingUseFact(
        canonical_name=result.canonical_name,
        major_use=entry.major_use,
        source_path=_source_path_text(result),
    )
