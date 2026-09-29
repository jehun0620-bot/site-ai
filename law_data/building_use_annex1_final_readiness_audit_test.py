# -*- coding: utf-8 -*-
"""Behavioral readiness audit for fully registered multi-candidate Annex 1 uses.

Only fact values already exercised by the verified qualification/resolver
regressions are used here. This audit does not infer missing legal conditions
and does not implement final classification.
"""

from __future__ import annotations

from collections import defaultdict

from law_data.building_use_annex1_candidate_resolver import (
    resolve_candidate_source_paths,
)
from law_data.building_use_annex1_canonical_catalog import build_canonical_catalog
from law_data.building_use_annex1_qualification_registry import (
    qualification_rules_for_candidate,
)


def numeric_fact(value: float, unit: str = "square_meter") -> dict:
    return {"state": "TRUE", "value": value, "unit": unit}


def states(canonical_name: str, area: float) -> tuple[tuple[str, str], ...]:
    results = resolve_candidate_source_paths(
        canonical_name,
        {"use_floor_area": numeric_fact(area)},
    )
    return tuple((item.entry.source_path.key, item.state) for item in results)


def classify_pattern(result_states: tuple[tuple[str, str], ...]) -> str:
    values = tuple(state for _, state in result_states)
    true_count = values.count("TRUE")
    if true_count == 1 and all(state in {"TRUE", "FALSE"} for state in values):
        return "ONE_TRUE_REST_FALSE"
    if "UNKNOWN" in values:
        return "UNKNOWN_PRESENT"
    if "UNSET" in values:
        return "UNSET_PRESENT"
    if true_count > 1:
        return "MULTIPLE_TRUE"
    if all(state == "FALSE" for state in values):
        return "ALL_FALSE"
    return "OTHER"


def main() -> None:
    catalog = build_canonical_catalog()
    by_name = defaultdict(list)
    for entry in catalog:
        by_name[entry.canonical_name].append(entry)

    fully_registered_multi = tuple(
        name
        for name in sorted(by_name)
        if len(by_name[name]) > 1
        and all(
            qualification_rules_for_candidate(entry.source_path, entry.canonical_name)
            for entry in by_name[name]
        )
    )
    assert len(fully_registered_multi) == 23

    # Boundary scenarios below reuse values already covered by existing
    # qualification/resolver regressions. No new legal threshold is invented.
    scenarios = {
        "종교집회장": (499, 500),
        "단란주점": (149, 150),
        "방송국": (999, 1000),
        "통신용 시설": (999, 1000),
        "공연장": (499, 500),
        "전기자동차 충전소": (999, 1000),
        "탁구장": (499, 500),
        "체육도장": (499, 500),
        "골프연습장": (499, 500),
        "테니스장": (499, 500),
        "체력단련장": (499, 500),
        "에어로빅장": (499, 500),
        "당구장": (499, 500),
        "실내낚시터": (499, 500),
        "볼링장": (499, 500),
        "놀이형시설": (499, 500),
        "동물병원": (299, 300),
        "동물미용실": (299, 300),
        "동물위탁관리업 시설": (299, 300),
        "금융업소": (29, 30, 499, 500),
        "사무소": (29, 30, 499, 500),
        "부동산중개사무소": (29, 30, 499, 500),
        "출판사": (29, 30, 499, 500),
    }
    assert set(scenarios) == set(fully_registered_multi)

    summaries = {}
    for name in fully_registered_multi:
        rows = []
        for area in scenarios[name]:
            result_states = states(name, area)
            rows.append((area, result_states, classify_pattern(result_states)))
        summaries[name] = tuple(rows)

    expected_bidirectional = {
        "종교집회장",
        "단란주점",
        "방송국",
        "통신용 시설",
        "공연장",
        "전기자동차 충전소",
        "동물병원",
        "동물미용실",
        "동물위탁관리업 시설",
    }
    expected_partial = {
        "탁구장",
        "체육도장",
        "골프연습장",
        "테니스장",
        "체력단련장",
        "에어로빅장",
        "당구장",
        "실내낚시터",
        "볼링장",
        "놀이형시설",
    }
    expected_three_stage = {
        "금융업소",
        "사무소",
        "부동산중개사무소",
        "출판사",
    }

    assert (
        expected_bidirectional | expected_partial | expected_three_stage
        == set(fully_registered_multi)
    )

    for name in expected_bidirectional:
        patterns = tuple(row[2] for row in summaries[name])
        assert patterns == ("ONE_TRUE_REST_FALSE", "ONE_TRUE_REST_FALSE")

    for name in expected_partial:
        patterns = tuple(row[2] for row in summaries[name])
        assert patterns[0] == "ONE_TRUE_REST_FALSE"
        assert patterns[1] == "UNSET_PRESENT"

    for name in expected_three_stage:
        patterns = tuple(row[2] for row in summaries[name])
        assert patterns == (
            "ONE_TRUE_REST_FALSE",
            "ONE_TRUE_REST_FALSE",
            "ONE_TRUE_REST_FALSE",
            "ONE_TRUE_REST_FALSE",
        )

    print("RESULT: PASS")
    print("Fully registered multi-candidate count:", len(fully_registered_multi))
    print("Bidirectional boundary-ready count:", len(expected_bidirectional))
    print("Three-stage boundary-ready count:", len(expected_three_stage))
    print("Partial/fail-closed count:", len(expected_partial))

    print("\nFINAL-READINESS AUDIT")
    for name in fully_registered_multi:
        print(f"- {name}")
        for area, result_states, pattern in summaries[name]:
            print(f"  area={area} -> {result_states} -> {pattern}")

    print("\nBIDIRECTIONAL BOUNDARY-READY")
    print(tuple(sorted(expected_bidirectional)))
    print("\nTHREE-STAGE BOUNDARY-READY")
    print(tuple(sorted(expected_three_stage)))
    print("\nPARTIAL / FAIL-CLOSED")
    print(tuple(sorted(expected_partial)))
    print(
        "\nNot proven: candidate-set legal completeness, automatic final "
        "classification, single-candidate final resolution, missing qualification "
        "coverage, frontend integration, PROJECT mapping, or Rule Engine "
        "end-to-end integration."
    )


if __name__ == "__main__":
    main()
