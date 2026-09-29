# -*- coding: utf-8 -*-
"""Verified Annex 1 qualification expressions keyed by legal source path.

This registry starts narrowly. Only source paths whose numeric meaning has
already been reviewed against the official Annex 1 source are admitted here.
It does not infer conditions from source text.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.building_use_annex1_semantic_model import SourcePath


VERIFIED = "VERIFIED"


@dataclass(frozen=True)
class BuildingUseQualificationRule:
    source_path: SourcePath
    source_text: str
    expression: dict[str, Any] | None = None
    excluded_major_uses: tuple[str, ...] = ()
    expression_status: str = VERIFIED

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ValueError("source_text is required")
        if self.expression_status != VERIFIED:
            raise ValueError("qualification registry admits VERIFIED expressions only")
        if self.expression is not None and (
            not isinstance(self.expression, dict) or not self.expression
        ):
            raise ValueError("expression must be a non-empty dict when provided")
        if any(not item.strip() for item in self.excluded_major_uses):
            raise ValueError("excluded_major_uses must contain non-empty names")
        if self.expression is None and not self.excluded_major_uses:
            raise ValueError("at least one qualification condition is required")


def numeric(target: str, operator: str, value: float, unit: str) -> dict[str, Any]:
    return {
        "op": "NUMERIC",
        "target": target,
        "operator": operator,
        "value": value,
        "unit": unit,
    }


VERIFIED_QUALIFICATION_RULES: dict[str, BuildingUseQualificationRule] = {
    "3/가": BuildingUseQualificationRule(
        source_path=SourcePath("3", "가"),
        source_text="소매점으로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 1천제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 1000, "square_meter"),
    ),
    "3/차": BuildingUseQualificationRule(
        source_path=SourcePath("3", "차"),
        source_text="전기자동차 충전소로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 1천제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 1000, "square_meter"),
    ),
    "4/다": BuildingUseQualificationRule(
        source_path=SourcePath("4", "다"),
        source_text="자동차영업소로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 1천제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 1000, "square_meter"),
    ),
    "4/더": BuildingUseQualificationRule(
        source_path=SourcePath("4", "더"),
        source_text="단란주점으로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 150제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 150, "square_meter"),
    ),
    "4/버": BuildingUseQualificationRule(
        source_path=SourcePath("4", "버"),
        source_text="공유보관시설로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 1천제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 1000, "square_meter"),
    ),
    "20/자": BuildingUseQualificationRule(
        source_path=SourcePath("20", "자"),
        source_text="전기자동차 충전소로서 제1종 근린생활시설에 해당하지 않는 것",
        excluded_major_uses=("제1종 근린생활시설",),
    ),
    "25": BuildingUseQualificationRule(
        source_path=SourcePath("25"),
        source_text="발전시설로서 제1종 근린생활시설에 해당하지 아니하는 것",
        excluded_major_uses=("제1종 근린생활시설",),
    ),
    "2/가": BuildingUseQualificationRule(
        source_path=SourcePath("2", "가"),
        source_text="주택으로 쓰는 층수가 5개 층 이상인 주택",
        expression=numeric("residential_floor_count", "GTE", 5, "floor"),
    ),
    "2/나": BuildingUseQualificationRule(
        source_path=SourcePath("2", "나"),
        source_text=(
            "주택으로 쓰는 1개 동의 바닥면적 합계가 660제곱미터를 초과하고, "
            "층수가 4개 층 이하인 주택"
        ),
        expression={
            "op": "AND",
            "children": [
                numeric("residential_floor_area", "GT", 660, "square_meter"),
                numeric("residential_floor_count", "LTE", 4, "floor"),
            ],
        },
    ),
    "2/다": BuildingUseQualificationRule(
        source_path=SourcePath("2", "다"),
        source_text=(
            "주택으로 쓰는 1개 동의 바닥면적 합계가 660제곱미터 이하이고, "
            "층수가 4개 층 이하인 주택"
        ),
        expression={
            "op": "AND",
            "children": [
                numeric("residential_floor_area", "LTE", 660, "square_meter"),
                numeric("residential_floor_count", "LTE", 4, "floor"),
            ],
        },
    ),
    "3/마": BuildingUseQualificationRule(
        source_path=SourcePath("3", "마"),
        source_text=(
            "탁구장, 체육도장으로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 "
            "합계가 500제곱미터 미만인 것"
        ),
        expression=numeric("use_floor_area", "LT", 500, "square_meter"),
    ),
    "4/가": BuildingUseQualificationRule(
        source_path=SourcePath("4", "가"),
        source_text="공연장으로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 500제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 500, "square_meter"),
    ),
    "3/카": BuildingUseQualificationRule(
        source_path=SourcePath("3", "카"),
        source_text="동물병원, 동물미용실, 동물위탁관리업을 위한 시설로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 300제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 300, "square_meter"),
    ),
    "4/차": BuildingUseQualificationRule(
        source_path=SourcePath("4", "차"),
        source_text="장의사, 동물병원, 동물미용실, 동물위탁관리업을 위한 시설로서 제1종 근린생활시설에 해당하는 것은 제외",
        excluded_major_uses=("제1종 근린생활시설",),
    ),
    "3/자": BuildingUseQualificationRule(
        source_path=SourcePath("3", "자"),
        source_text="금융업소, 사무소, 부동산중개사무소, 소개업소, 출판사 등 일반업무시설로서 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 30제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 30, "square_meter"),
    ),
    "4/하": BuildingUseQualificationRule(
        source_path=SourcePath("4", "하"),
        source_text="금융업소, 사무소, 부동산중개사무소, 소개업소, 출판사 등 일반업무시설로서 제1종 근린생활시설에 해당하는 것을 제외하고 같은 건축물에 해당 용도로 쓰는 바닥면적의 합계가 500제곱미터 미만인 것",
        expression=numeric("use_floor_area", "LT", 500, "square_meter"),
        excluded_major_uses=("제1종 근린생활시설",),
    ),
    "14/나/1": BuildingUseQualificationRule(
        source_path=SourcePath("14", "나", 1),
        source_text="금융업소, 사무소, 부동산중개사무소, 소개업소, 출판사 등으로서 제1종 근린생활시설 및 제2종 근린생활시설에 해당하지 않는 것",
        excluded_major_uses=("제1종 근린생활시설", "제2종 근린생활시설"),
    ),
    "13/가": BuildingUseQualificationRule(
        source_path=SourcePath("13", "가"),
        source_text="탁구장, 체육도장, 테니스장 등으로서 제1종 근린생활시설 및 제2종 근린생활시설에 해당하지 아니하는 것",
        excluded_major_uses=("제1종 근린생활시설", "제2종 근린생활시설"),
    ),
    "5/가": BuildingUseQualificationRule(
        source_path=SourcePath("5", "가"),
        source_text=(
            "공연장[극장, 영화관, 연예장, 음악당, 서커스장, 비디오물감상실, "
            "비디오물소극장, 그 밖에 이와 비슷한 것을 말한다]으로서 "
            "제2종 근린생활시설에 해당하지 아니하는 것"
        ),
        excluded_major_uses=("제2종 근린생활시설",),
    ),
}


def qualification_rule_for_path(
    source_path: SourcePath,
) -> BuildingUseQualificationRule | None:
    return VERIFIED_QUALIFICATION_RULES.get(source_path.key)
