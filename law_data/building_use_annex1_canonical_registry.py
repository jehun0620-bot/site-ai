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
    canonical_uses_for_name,
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
    CanonicalBuildingUse(
        canonical_name="일반숙박시설",
        source_path=SourcePath("15", "가"),
        major_use="숙박시설",
    ),
    CanonicalBuildingUse(
        canonical_name="생활숙박시설",
        source_path=SourcePath("15", "가"),
        major_use="숙박시설",
    ),
    CanonicalBuildingUse(
        canonical_name="탁구장",
        source_path=SourcePath("3", "마"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="탁구장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물병원",
        source_path=SourcePath("3", "카"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물병원",
        source_path=SourcePath("4", "차"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물미용실",
        source_path=SourcePath("3", "카"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물미용실",
        source_path=SourcePath("4", "차"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물위탁관리업 시설",
        source_path=SourcePath("3", "카"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="동물위탁관리업 시설",
        source_path=SourcePath("4", "차"),
        major_use="제2종 근린생활시설",
    ),    CanonicalBuildingUse(
        canonical_name="체육도장",
        source_path=SourcePath("3", "마"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="체육도장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="테니스장",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="테니스장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="체력단련장",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="체력단련장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="에어로빅장",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="에어로빅장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="당구장",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="당구장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="실내낚시터",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="실내낚시터",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="골프연습장",
        source_path=SourcePath("4", "파"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="골프연습장",
        source_path=SourcePath("13", "가"),
        major_use="운동시설",
    ),
    CanonicalBuildingUse(
        canonical_name="휴게음식점",
        source_path=SourcePath("3", "나"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="제과점",
        source_path=SourcePath("3", "나"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="휴게음식점",
        source_path=SourcePath("4", "아"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="제과점",
        source_path=SourcePath("4", "아"),
        major_use="제2종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="이용원",
        source_path=SourcePath("3", "다"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="미용원",
        source_path=SourcePath("3", "다"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="목욕장",
        source_path=SourcePath("3", "다"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="세탁소",
        source_path=SourcePath("3", "다"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="의원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="치과의원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="한의원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="침술원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="접골원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="조산원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="안마원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
    CanonicalBuildingUse(
        canonical_name="산후조리원",
        source_path=SourcePath("3", "라"),
        major_use="제1종 근린생활시설",
    ),
)


def canonical_uses_for_path(source_path: SourcePath) -> tuple[CanonicalBuildingUse, ...]:
    """Return registered canonical uses for one official Annex 1 source path."""

    return canonical_uses_for_source_path(CANONICAL_BUILDING_USES, source_path)


def canonical_uses_for_canonical_name(
    canonical_name: str,
) -> tuple[CanonicalBuildingUse, ...]:
    """Return registered canonical uses matching one canonical name."""

    return canonical_uses_for_name(CANONICAL_BUILDING_USES, canonical_name)
