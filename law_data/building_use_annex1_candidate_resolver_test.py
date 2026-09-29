# -*- coding: utf-8 -*-
"""Behavioral regression for Annex 1 candidate source-path resolution."""

from __future__ import annotations

from law_data.building_use_annex1_candidate_resolver import (
    candidate_results_for_major_use,
    resolve_candidate_source_paths,
)


def by_path(results):
    return {item.entry.source_path.key: item for item in results}


def numeric_fact(value: float, unit: str) -> dict:
    return {
        "state": "TRUE",
        "value": value,
        "unit": unit,
    }


def main() -> None:
    table_tennis_results = resolve_candidate_source_paths(
        "탁구장",
        {
            "use_floor_area": numeric_fact(499, "square_meter"),
        },
    )
    table_tennis = by_path(table_tennis_results)
    assert set(table_tennis) == {"3/마", "13/가"}
    assert table_tennis["3/마"].state == "TRUE"
    assert table_tennis["3/마"].qualification_status == "VERIFIED"
    assert table_tennis["13/가"].state == "UNSET"
    assert table_tennis["13/가"].qualification_status == "UNREGISTERED"

    table_tennis_neighborhood = candidate_results_for_major_use(
        table_tennis_results,
        "제1종 근린생활시설",
    )
    table_tennis_sports = candidate_results_for_major_use(
        table_tennis_results,
        "운동시설",
    )
    assert tuple(item.entry.source_path.key for item in table_tennis_neighborhood) == (
        "3/마",
    )
    assert tuple(item.entry.source_path.key for item in table_tennis_sports) == (
        "13/가",
    )
    assert table_tennis_neighborhood[0].state == "TRUE"
    assert table_tennis_sports[0].state == "UNSET"

    table_tennis_boundary = by_path(
        resolve_candidate_source_paths(
            "탁구장",
            {
                "use_floor_area": numeric_fact(500, "square_meter"),
            },
        )
    )
    assert table_tennis_boundary["3/마"].state == "FALSE"
    assert table_tennis_boundary["13/가"].state == "UNSET"

    apartment = by_path(
        resolve_candidate_source_paths(
            "아파트",
            {
                "residential_floor_count": numeric_fact(5, "floor"),
            },
        )
    )
    assert set(apartment) == {"2/가"}
    assert apartment["2/가"].state == "TRUE"
    assert apartment["2/가"].qualification_status == "VERIFIED"

    apartment_unset = by_path(
        resolve_candidate_source_paths("아파트")
    )
    assert apartment_unset["2/가"].state == "UNSET"
    assert apartment_unset["2/가"].qualification_status == "VERIFIED"

    performance_hall_results = resolve_candidate_source_paths("공연장")
    performance_hall = by_path(performance_hall_results)
    assert set(performance_hall) == {"4/가", "5/가"}
    assert {item.state for item in performance_hall.values()} == {"UNSET"}
    assert {
        item.qualification_status for item in performance_hall.values()
    } == {"UNREGISTERED"}

    performance_hall_neighborhood = candidate_results_for_major_use(
        performance_hall_results,
        "제2종 근린생활시설",
    )
    performance_hall_culture = candidate_results_for_major_use(
        performance_hall_results,
        "문화 및 집회시설",
    )
    assert tuple(
        item.entry.source_path.key for item in performance_hall_neighborhood
    ) == ("4/가",)
    assert tuple(
        item.entry.source_path.key for item in performance_hall_culture
    ) == ("5/가",)

    office = by_path(
        resolve_candidate_source_paths("사무소")
    )
    assert set(office) == {"3/자", "4/하", "14/나/1"}
    assert {item.state for item in office.values()} == {"UNSET"}

    missing_major_use = candidate_results_for_major_use(
        performance_hall_results,
        "존재하지 않는 대분류",
    )
    assert missing_major_use == ()

    unknown = resolve_candidate_source_paths("등록되지 않은 용도")
    assert unknown == ()

    print("RESULT: PASS")
    print("Table-tennis candidate paths: ('3/마', '13/가')")
    print("3/마 verified numeric evaluation: PASS")
    print("13/가 unregistered qualification remains UNSET: PASS")
    print("Table-tennis major-use lookup: PASS")
    print("Apartment single-path verified qualification: PASS")
    print("Performance-hall candidates remain UNSET without inference: PASS")
    print("Performance-hall major-use lookup: PASS")
    print("Office three-path discovery: PASS")
    print("Unknown major use and canonical name fail-closed: PASS")
    print(
        "Not proven: non-numeric qualification evaluation, automatic exclusion "
        "derivation, final source-path selection, frontend integration, PROJECT "
        "mapping, or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
