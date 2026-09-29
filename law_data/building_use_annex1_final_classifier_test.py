# -*- coding: utf-8 -*-
"""Behavioral regression for limited fail-closed Annex 1 final classification."""

from __future__ import annotations

from dataclasses import replace

from law_data.building_use_annex1_final_classifier import (
    FINAL_CLASSIFICATION_WHITELIST,
    RESOLVED,
    REVIEW_REQUIRED,
    UNRESOLVED,
    classify_building_use,
    classify_candidate_results,
)


def fact(value: float) -> dict:
    return {"state": "TRUE", "value": value, "unit": "square_meter"}


def selected_path(result) -> str | None:
    if result.selected_candidate is None:
        return None
    return result.selected_candidate.entry.source_path.key


def main() -> None:
    assert len(FINAL_CLASSIFICATION_WHITELIST) == 13

    scenarios = (
        ("공연장", 499, "4/가"),
        ("공연장", 500, "5/가"),
        ("단란주점", 149, "4/더"),
        ("단란주점", 150, "16/가"),
        ("동물병원", 299, "3/카"),
        ("동물병원", 300, "4/차"),
        ("동물미용실", 299, "3/카"),
        ("동물미용실", 300, "4/차"),
        ("동물위탁관리업 시설", 299, "3/카"),
        ("동물위탁관리업 시설", 300, "4/차"),
        ("방송국", 999, "3/바"),
        ("방송국", 1000, "24/가"),
        ("전기자동차 충전소", 999, "3/차"),
        ("전기자동차 충전소", 1000, "20/자"),
        ("종교집회장", 499, "4/나"),
        ("종교집회장", 500, "6/가"),
        ("통신용 시설", 999, "3/아"),
        ("통신용 시설", 1000, "24/라"),
        ("금융업소", 29, "3/자"),
        ("금융업소", 30, "4/하"),
        ("금융업소", 500, "14/나/1"),
        ("사무소", 29, "3/자"),
        ("사무소", 30, "4/하"),
        ("사무소", 500, "14/나/1"),
        ("부동산중개사무소", 29, "3/자"),
        ("부동산중개사무소", 30, "4/하"),
        ("부동산중개사무소", 500, "14/나/1"),
        ("출판사", 29, "3/자"),
        ("출판사", 30, "4/하"),
        ("출판사", 500, "14/나/1"),
    )

    for canonical_name, area, expected_path in scenarios:
        result = classify_building_use(
            canonical_name,
            {"use_floor_area": fact(area)},
        )
        assert result.status == RESOLVED
        assert selected_path(result) == expected_path

    missing_fact = classify_building_use("공연장")
    assert missing_fact.status == UNRESOLVED
    assert selected_path(missing_fact) is None

    partial_not_whitelisted = classify_building_use(
        "골프연습장",
        {"use_floor_area": fact(499)},
    )
    assert partial_not_whitelisted.status == UNRESOLVED
    assert selected_path(partial_not_whitelisted) is None

    unknown_name = classify_building_use("등록되지 않은 용도")
    assert unknown_name.status == UNRESOLVED
    assert unknown_name.candidates == ()

    base = classify_building_use(
        "공연장",
        {"use_floor_area": fact(499)},
    )
    assert len(base.candidates) == 2

    multiple_true = tuple(replace(item, state="TRUE") for item in base.candidates)
    multiple_true_result = classify_candidate_results("공연장", multiple_true)
    assert multiple_true_result.status == REVIEW_REQUIRED
    assert selected_path(multiple_true_result) is None

    unknown_candidates = (
        replace(base.candidates[0], state="UNKNOWN"),
        replace(base.candidates[1], state="FALSE"),
    )
    unknown_result = classify_candidate_results("공연장", unknown_candidates)
    assert unknown_result.status == REVIEW_REQUIRED
    assert selected_path(unknown_result) is None

    unset_candidates = (
        replace(base.candidates[0], state="TRUE"),
        replace(base.candidates[1], state="UNSET"),
    )
    unset_result = classify_candidate_results("공연장", unset_candidates)
    assert unset_result.status == UNRESOLVED
    assert selected_path(unset_result) is None

    print("RESULT: PASS")
    print("Final classification whitelist count:", len(FINAL_CLASSIFICATION_WHITELIST))
    print("Verified RESOLVED scenarios:", len(scenarios))
    print("Missing facts -> UNRESOLVED: PASS")
    print("Non-whitelisted partial use -> UNRESOLVED: PASS")
    print("Unknown canonical use -> UNRESOLVED: PASS")
    print("Multiple TRUE -> REVIEW_REQUIRED: PASS")
    print("UNKNOWN candidate -> REVIEW_REQUIRED: PASS")
    print("TRUE + UNSET -> UNRESOLVED: PASS")
    print(
        "Not proven: legal candidate-set completeness, single-candidate "
        "classification, PROJECT mapping, API/frontend integration, or Rule "
        "Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
