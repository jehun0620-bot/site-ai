# -*- coding: utf-8 -*-
"""Explicit canonical building-use registry for Annex 1.

This registry is separate from the source-node semantic inventory.
Multiple canonical uses may point to the same official source path.
"""

from __future__ import annotations

from law_data.building_use_annex1_semantic_model import (
    CanonicalBuildingUse,
    SourcePath,
    canonical_uses_for_source_path,
)


CANONICAL_BUILDING_USES: tuple[CanonicalBuildingUse, ...] = (
    CanonicalBuildingUse(
        canonical_name="학원",
        source_path=SourcePath("10", "라"),
        major_use="교육연구시설",
    ),
    CanonicalBuildingUse(
        canonical_name="교습소",
        source_path=SourcePath("10", "라"),
        major_use="교육연구시설",
    ),
    CanonicalBuildingUse(
        canonical_name="사진관",
        source_path=SourcePath("4", "바"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="표구점",
        source_path=SourcePath("4", "바"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="안마시술소",
        source_path=SourcePath("4", "러"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="노래연습장",
        source_path=SourcePath("4", "러"),
        major_use="제2종 근린생활시설",
    ),
)


def canonical_uses_for_path(source_path: SourcePath) -> tuple[CanonicalBuildingUse, ...]:
    """Return registered canonical uses for one official Annex 1 source path."""

    return canonical_uses_for_source_path(CANONICAL_BUILDING_USES, source_path)
