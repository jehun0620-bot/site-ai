# -*- coding: utf-8 -*-
"""Fail-closed final classification for a limited verified Annex 1 scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.building_use_annex1_candidate_resolver import (
    BuildingUseCandidateResult,
    resolve_candidate_source_paths,
)


RESOLVED = "RESOLVED"
UNRESOLVED = "UNRESOLVED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
VALID_FINAL_STATUSES = {RESOLVED, UNRESOLVED, REVIEW_REQUIRED}

FINAL_CLASSIFICATION_WHITELIST = frozenset(
    {
        "공연장",
        "단란주점",
        "동물미용실",
        "동물병원",
        "동물위탁관리업 시설",
        "방송국",
        "전기자동차 충전소",
        "종교집회장",
        "통신용 시설",
        "금융업소",
        "부동산중개사무소",
        "사무소",
        "출판사",
    }
)


@dataclass(frozen=True)
class BuildingUseFinalClassification:
    canonical_name: str
    status: str
    selected_candidate: BuildingUseCandidateResult | None
    candidates: tuple[BuildingUseCandidateResult, ...]

    def __post_init__(self) -> None:
        if self.status not in VALID_FINAL_STATUSES:
            raise ValueError(f"invalid final classification status: {self.status}")
        if self.status == RESOLVED and self.selected_candidate is None:
            raise ValueError("RESOLVED requires selected_candidate")
        if self.status != RESOLVED and self.selected_candidate is not None:
            raise ValueError("non-RESOLVED result cannot select a candidate")


def classify_candidate_results(
    canonical_name: str,
    candidates: tuple[BuildingUseCandidateResult, ...],
) -> BuildingUseFinalClassification:
    """Classify already-evaluated candidates without inferring missing facts."""

    if canonical_name not in FINAL_CLASSIFICATION_WHITELIST:
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=UNRESOLVED,
            selected_candidate=None,
            candidates=candidates,
        )

    if not candidates:
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=UNRESOLVED,
            selected_candidate=None,
            candidates=candidates,
        )

    true_candidates = tuple(item for item in candidates if item.state == "TRUE")
    states = tuple(item.state for item in candidates)

    if len(true_candidates) > 1 or "UNKNOWN" in states:
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=REVIEW_REQUIRED,
            selected_candidate=None,
            candidates=candidates,
        )

    if (
        len(true_candidates) == 1
        and all(item.state in {"TRUE", "FALSE"} for item in candidates)
    ):
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=RESOLVED,
            selected_candidate=true_candidates[0],
            candidates=candidates,
        )

    return BuildingUseFinalClassification(
        canonical_name=canonical_name,
        status=UNRESOLVED,
        selected_candidate=None,
        candidates=candidates,
    )


def classify_building_use(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> BuildingUseFinalClassification:
    """Resolve candidates, then apply the limited fail-closed final contract."""

    candidates = resolve_candidate_source_paths(canonical_name, fact_context)
    return classify_candidate_results(canonical_name, candidates)
