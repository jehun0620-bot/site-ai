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
    CanonicalBuildingUse(
        canonical_name="독서실",
        source_path=SourcePath("4", "타"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="기원",
        source_path=SourcePath("4", "타"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="무도장",
        source_path=SourcePath("16", "마"),
        major_use="위락시설",
    ),
    CanonicalBuildingUse(
        canonical_name="무도학원",
        source_path=SourcePath("16", "마"),
        major_use="위락시설",
    ),
    CanonicalBuildingUse(
        canonical_name="소년원",
        source_path=SourcePath("23", "다"),
        major_use="교정시설",
    ),
    CanonicalBuildingUse(
        canonical_name="소년분류심사원",
        source_path=SourcePath("23", "다"),
        major_use="교정시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물화장시설",
        source_path=SourcePath("26", "라"),
        major_use="묘지 관련 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물건조장시설",
        source_path=SourcePath("26", "라"),
        major_use="묘지 관련 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물 전용의 납골시설",
        source_path=SourcePath("26", "라"),
        major_use="묘지 관련 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="주유소",
        source_path=SourcePath("19", "가"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="석유 판매소",
        source_path=SourcePath("19", "가"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="액화석유가스 충전소",
        source_path=SourcePath("19", "나"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="액화석유가스 판매소",
        source_path=SourcePath("19", "나"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="액화석유가스 저장소",
        source_path=SourcePath("19", "나"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="위험물 제조소",
        source_path=SourcePath("19", "다"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="위험물 저장소",
        source_path=SourcePath("19", "다"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="위험물 취급소",
        source_path=SourcePath("19", "다"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="액화가스 취급소",
        source_path=SourcePath("19", "라"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="액화가스 판매소",
        source_path=SourcePath("19", "라"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="고압가스 충전소",
        source_path=SourcePath("19", "바"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="고압가스 판매소",
        source_path=SourcePath("19", "바"),
        major_use="위험물 저장 및 처리 시설",
    ),
    CanonicalBuildingUse(
        canonical_name="고압가스 저장소",
        source_path=SourcePath("19", "바"),
        major_use="위험물 저장 및 처리 시설",
    ),
)


def canonical_uses_for_path(source_path: SourcePath) -> tuple[CanonicalBuildingUse, ...]:
    """Return registered canonical uses for one official Annex 1 source path."""

    return canonical_uses_for_source_path(CANONICAL_BUILDING_USES, source_path)
