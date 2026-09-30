# -*- coding: utf-8 -*-
"""Fail-closed final classification for a limited verified Annex 1 scope."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from law_data.building_use_annex1_candidate_resolver import (
    BuildingUseCandidateResult,
    aggregate_candidate_state,
    resolve_candidate_source_paths,
)
from law_data.building_use_annex1_canonical_catalog import catalog_entries_for_name
from law_data.building_use_annex1_cross_classification import (
    evaluate_cross_classifications,
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


def _cross_classification_final(
    canonical_name: str,
    candidates: tuple[BuildingUseCandidateResult, ...],
    fact_context: dict[str, Any] | None,
) -> BuildingUseFinalClassification | None:
    """Promote only a verified, non-conflicting cross-classification branch."""

    cross_results = evaluate_cross_classifications(canonical_name, fact_context)
    if not cross_results:
        return None

    cross_states = tuple(result.state for result in cross_results)
    if "UNKNOWN" in cross_states:
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=REVIEW_REQUIRED,
            selected_candidate=None,
            candidates=candidates,
        )

    true_cross = tuple(result for result in cross_results if result.state == "TRUE")
    if len(true_cross) > 1:
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=REVIEW_REQUIRED,
            selected_candidate=None,
            candidates=candidates,
        )

    if len(true_cross) != 1:
        return None

    same_name_state = aggregate_candidate_state(candidates)
    if same_name_state == "TRUE":
        return BuildingUseFinalClassification(
            canonical_name=canonical_name,
            status=REVIEW_REQUIRED,
            selected_candidate=None,
            candidates=candidates,
        )
    if same_name_state in {"UNKNOWN", "UNSET"}:
        return None

    relation = true_cross[0].relation
    target_entries = tuple(
        entry
        for entry in catalog_entries_for_name(relation.resolved_canonical_name)
        if entry.source_path == relation.target_source_path
    )
    if len(target_entries) != 1:
        return None

    promoted = BuildingUseCandidateResult(
        entry=target_entries[0],
        state="TRUE",
        qualification_status="VERIFIED",
    )
    return BuildingUseFinalClassification(
        canonical_name=relation.resolved_canonical_name,
        status=RESOLVED,
        selected_candidate=promoted,
        candidates=(promoted,),
    )


def classify_building_use(
    canonical_name: str,
    fact_context: dict[str, Any] | None = None,
) -> BuildingUseFinalClassification:
    """Resolve same-name candidates, then apply verified cross branches narrowly."""

    candidates = resolve_candidate_source_paths(canonical_name, fact_context)

    cross_final = _cross_classification_final(
        canonical_name,
        candidates,
        fact_context,
    )
    if cross_final is not None:
        return cross_final

    return classify_candidate_results(canonical_name, candidates)
