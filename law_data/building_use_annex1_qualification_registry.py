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
    expression: dict[str, Any]
    expression_status: str = VERIFIED

    def __post_init__(self) -> None:
        if not self.source_text.strip():
            raise ValueError("source_text is required")
        if self.expression_status != VERIFIED:
            raise ValueError("qualification registry admits VERIFIED expressions only")
        if not isinstance(self.expression, dict) or not self.expression:
            raise ValueError("expression is required")


def numeric(target: str, operator: str, value: float, unit: str) -> dict[str, Any]:
    return {
        "op": "NUMERIC",
        "target": target,
        "operator": operator,
        "value": value,
        "unit": unit,
    }


VERIFIED_QUALIFICATION_RULES: dict[str, BuildingUseQualificationRule] = {
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
}


def qualification_rule_for_path(
    source_path: SourcePath,
) -> BuildingUseQualificationRule | None:
    return VERIFIED_QUALIFICATION_RULES.get(source_path.key)
