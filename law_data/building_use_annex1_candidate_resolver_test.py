# -*- coding: utf-8 -*-
"""Behavioral regression for Annex 1 candidate source-path resolution."""

from __future__ import annotations

from law_data.building_use_annex1_candidate_resolver import (
    aggregate_candidate_state,
    candidate_results_for_major_use,
    excluded_major_use_state,
    major_use_classification_state,
    negate_candidate_state,
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
    assert table_tennis["13/가"].state == "FALSE"
    assert table_tennis["13/가"].qualification_status == "VERIFIED"

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
    assert table_tennis_sports[0].state == "FALSE"

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

    general_dormitory_facts = {
        "dormitory_building_standard_compliant": {"state": "TRUE"},
        "has_individually_owned_room": {"state": "FALSE"},
        "general_dormitory_eligible_occupancy": {"state": "TRUE"},
        "common_cooking_household_ratio": numeric_fact(50, "percent"),
    }
    general_dormitory = by_path(
        resolve_candidate_source_paths("일반기숙사", general_dormitory_facts)
    )
    assert set(general_dormitory) == {"2/라/1"}
    assert general_dormitory["2/라/1"].state == "TRUE"
    assert general_dormitory["2/라/1"].qualification_status == "VERIFIED"
    general_dormitory_below = by_path(
        resolve_candidate_source_paths(
            "일반기숙사",
            {**general_dormitory_facts, "common_cooking_household_ratio": numeric_fact(49, "percent")},
        )
    )
    assert general_dormitory_below["2/라/1"].state == "FALSE"
    assert by_path(resolve_candidate_source_paths("일반기숙사"))["2/라/1"].state == "UNSET"

    rental_dormitory_facts = {
        "dormitory_building_standard_compliant": {"state": "TRUE"},
        "has_individually_owned_room": {"state": "FALSE"},
        "qualified_dormitory_rental_operator": {"state": "TRUE"},
        "rental_room_count": numeric_fact(20, "room"),
        "common_cooking_household_ratio": numeric_fact(50, "percent"),
    }
    rental_dormitory = by_path(
        resolve_candidate_source_paths("임대형기숙사", rental_dormitory_facts)
    )
    assert set(rental_dormitory) == {"2/라/2"}
    assert rental_dormitory["2/라/2"].state == "TRUE"
    assert rental_dormitory["2/라/2"].qualification_status == "VERIFIED"
    rental_dormitory_below = by_path(
        resolve_candidate_source_paths(
            "임대형기숙사",
            {**rental_dormitory_facts, "rental_room_count": numeric_fact(19, "room")},
        )
    )
    assert rental_dormitory_below["2/라/2"].state == "FALSE"
    assert by_path(resolve_candidate_source_paths("임대형기숙사"))["2/라/2"].state == "UNSET"

    religious_499 = by_path(
        resolve_candidate_source_paths(
            "종교집회장", {"use_floor_area": numeric_fact(499, "square_meter")}
        )
    )
    assert set(religious_499) == {"4/나", "6/가"}
    assert religious_499["4/나"].state == "TRUE"
    assert religious_499["6/가"].state == "FALSE"
    religious_500 = by_path(
        resolve_candidate_source_paths(
            "종교집회장", {"use_floor_area": numeric_fact(500, "square_meter")}
        )
    )
    assert religious_500["4/나"].state == "FALSE"
    assert religious_500["6/가"].state == "TRUE"

    pub_149 = by_path(
        resolve_candidate_source_paths(
            "단란주점", {"use_floor_area": numeric_fact(149, "square_meter")}
        )
    )
    assert set(pub_149) == {"4/더", "16/가"}
    assert pub_149["4/더"].state == "TRUE"
    assert pub_149["16/가"].state == "FALSE"
    pub_150 = by_path(
        resolve_candidate_source_paths(
            "단란주점", {"use_floor_area": numeric_fact(150, "square_meter")}
        )
    )
    assert pub_150["4/더"].state == "FALSE"
    assert pub_150["16/가"].state == "TRUE"

    broadcast_999 = by_path(
        resolve_candidate_source_paths(
            "방송국", {"use_floor_area": numeric_fact(999, "square_meter")}
        )
    )
    assert set(broadcast_999) == {"3/바", "24/가"}
    assert broadcast_999["3/바"].state == "TRUE"
    assert broadcast_999["24/가"].state == "FALSE"
    broadcast_1000 = by_path(
        resolve_candidate_source_paths(
            "방송국", {"use_floor_area": numeric_fact(1000, "square_meter")}
        )
    )
    assert broadcast_1000["3/바"].state == "FALSE"
    assert broadcast_1000["24/가"].state == "TRUE"

    telecom = by_path(
        resolve_candidate_source_paths(
            "통신용 시설", {"use_floor_area": numeric_fact(999, "square_meter")}
        )
    )
    assert set(telecom) == {"3/아", "24/라"}
    assert telecom["3/아"].state == "UNSET"
    assert telecom["3/아"].qualification_status == "UNREGISTERED"
    assert telecom["24/라"].state == "UNSET"
    assert telecom["24/라"].qualification_status == "VERIFIED"

    performance_hall_results = resolve_candidate_source_paths(
        "공연장", {"use_floor_area": numeric_fact(499, "square_meter")}
    )
    performance_hall = by_path(performance_hall_results)
    assert set(performance_hall) == {"4/가", "5/가"}
    assert performance_hall["4/가"].state == "TRUE"
    assert performance_hall["5/가"].state == "FALSE"
    assert performance_hall["4/가"].qualification_status == "VERIFIED"
    assert performance_hall["5/가"].qualification_status == "VERIFIED"

    performance_hall_boundary = by_path(
        resolve_candidate_source_paths(
            "공연장", {"use_floor_area": numeric_fact(500, "square_meter")}
        )
    )
    assert performance_hall_boundary["4/가"].state == "FALSE"
    assert performance_hall_boundary["5/가"].state == "TRUE"

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
        resolve_candidate_source_paths(
            "사무소", {"use_floor_area": numeric_fact(29, "square_meter")}
        )
    )
    assert set(office) == {"3/자", "4/하", "14/나/1"}
    assert office["3/자"].state == "TRUE"
    assert office["4/하"].state == "FALSE"
    assert office["14/나/1"].state == "FALSE"

    ev_charger = by_path(
        resolve_candidate_source_paths(
            "전기자동차 충전소",
            {"use_floor_area": numeric_fact(999, "square_meter")},
        )
    )
    assert set(ev_charger) == {"3/차", "20/자"}
    assert ev_charger["3/차"].state == "TRUE"
    assert ev_charger["20/자"].state == "FALSE"
    assert ev_charger["3/차"].qualification_status == "VERIFIED"
    assert ev_charger["20/자"].qualification_status == "VERIFIED"

    ev_charger_boundary = by_path(
        resolve_candidate_source_paths(
            "전기자동차 충전소",
            {"use_floor_area": numeric_fact(1000, "square_meter")},
        )
    )
    assert ev_charger_boundary["3/차"].state == "FALSE"
    assert ev_charger_boundary["20/자"].state == "TRUE"

    for canonical_name, path, below, boundary in (
        ("소매점", "3/가", 999, 1000),
        ("자동차영업소", "4/다", 999, 1000),
        ("단란주점", "4/더", 149, 150),
        ("공유보관시설", "4/버", 999, 1000),
    ):
        below_result = by_path(
            resolve_candidate_source_paths(
                canonical_name,
                {"use_floor_area": numeric_fact(below, "square_meter")},
            )
        )
        boundary_result = by_path(
            resolve_candidate_source_paths(
                canonical_name,
                {"use_floor_area": numeric_fact(boundary, "square_meter")},
            )
        )
        assert below_result[path].state == "TRUE"
        assert boundary_result[path].state == "FALSE"

    power = by_path(resolve_candidate_source_paths("발전시설"))
    assert set(power) == {"25"}
    assert power["25"].state == "UNSET"
    assert power["25"].qualification_status == "VERIFIED"

    for canonical_name, path in (("체육관", "13/나"), ("운동장", "13/다")):
        no_seats = by_path(
            resolve_candidate_source_paths(
                canonical_name,
                {"has_spectator_seating": {"state": "FALSE"}},
            )
        )
        assert path in no_seats
        assert no_seats[path].state == "TRUE"
        assert no_seats[path].qualification_status == "VERIFIED"

        below = by_path(
            resolve_candidate_source_paths(
                canonical_name,
                {
                    "has_spectator_seating": {"state": "TRUE"},
                    "spectator_seating_area": numeric_fact(999, "square_meter"),
                },
            )
        )
        boundary = by_path(
            resolve_candidate_source_paths(
                canonical_name,
                {
                    "has_spectator_seating": {"state": "TRUE"},
                    "spectator_seating_area": numeric_fact(1000, "square_meter"),
                },
            )
        )
        missing = by_path(resolve_candidate_source_paths(canonical_name))
        assert below[path].state == "TRUE"
        assert boundary[path].state == "FALSE"
        assert missing[path].state == "UNSET"

    animal_hospital = by_path(
        resolve_candidate_source_paths(
            "동물병원", {"use_floor_area": numeric_fact(299, "square_meter")}
        )
    )
    assert animal_hospital["3/카"].state == "TRUE"
    assert animal_hospital["4/차"].state == "FALSE"

    missing_major_use = candidate_results_for_major_use(
        performance_hall_results,
        "존재하지 않는 대분류",
    )
    assert missing_major_use == ()

    assert aggregate_candidate_state(()) == "UNSET"
    assert aggregate_candidate_state(table_tennis_neighborhood) == "TRUE"
    assert aggregate_candidate_state(table_tennis_sports) == "FALSE"

    synthetic_states = [
        ("TRUE", "TRUE"),
        ("UNKNOWN", "UNKNOWN"),
        ("UNSET", "UNSET"),
        ("FALSE", "FALSE"),
    ]
    for input_state, expected_state in synthetic_states:
        synthetic = (
            type(table_tennis_neighborhood[0])(
                entry=table_tennis_neighborhood[0].entry,
                state=input_state,
                qualification_status="VERIFIED",
            ),
        )
        assert aggregate_candidate_state(synthetic) == expected_state

    mixed_true = (
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="FALSE",
            qualification_status="VERIFIED",
        ),
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="TRUE",
            qualification_status="VERIFIED",
        ),
    )
    mixed_unknown = (
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="FALSE",
            qualification_status="VERIFIED",
        ),
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="UNKNOWN",
            qualification_status="VERIFIED",
        ),
    )
    mixed_unset = (
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="FALSE",
            qualification_status="VERIFIED",
        ),
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="UNSET",
            qualification_status="VERIFIED",
        ),
    )
    all_false = (
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="FALSE",
            qualification_status="VERIFIED",
        ),
        type(table_tennis_neighborhood[0])(
            entry=table_tennis_neighborhood[0].entry,
            state="FALSE",
            qualification_status="VERIFIED",
        ),
    )
    assert aggregate_candidate_state(mixed_true) == "TRUE"
    assert aggregate_candidate_state(mixed_unknown) == "UNKNOWN"
    assert aggregate_candidate_state(mixed_unset) == "UNSET"
    assert aggregate_candidate_state(all_false) == "FALSE"

    assert negate_candidate_state("TRUE") == "FALSE"
    assert negate_candidate_state("FALSE") == "TRUE"
    assert negate_candidate_state("UNSET") == "UNSET"
    assert negate_candidate_state("UNKNOWN") == "UNKNOWN"

    assert (
        major_use_classification_state(
            table_tennis_results,
            "제1종 근린생활시설",
        )
        == "TRUE"
    )
    assert (
        excluded_major_use_state(
            table_tennis_results,
            "제1종 근린생활시설",
        )
        == "FALSE"
    )
    assert (
        major_use_classification_state(
            table_tennis_results,
            "제2종 근린생활시설",
        )
        == "UNSET"
    )
    assert (
        excluded_major_use_state(
            table_tennis_results,
            "제2종 근린생활시설",
        )
        == "UNSET"
    )
    assert (
        major_use_classification_state(
            performance_hall_results,
            "제2종 근린생활시설",
        )
        == "TRUE"
    )
    assert (
        excluded_major_use_state(
            performance_hall_results,
            "제2종 근린생활시설",
        )
        == "FALSE"
    )
    assert (
        major_use_classification_state(
            performance_hall_results,
            "존재하지 않는 대분류",
        )
        == "UNSET"
    )
    assert (
        excluded_major_use_state(
            performance_hall_results,
            "존재하지 않는 대분류",
        )
        == "UNSET"
    )

    unknown = resolve_candidate_source_paths("등록되지 않은 용도")
    assert unknown == ()

    print("RESULT: PASS")
    print("Table-tennis candidate paths: ('3/마', '13/가')")
    print("3/마 verified numeric evaluation: PASS")
    print("13/가 dual major-use exclusion evaluation: PASS")
    print("Table-tennis major-use lookup: PASS")
    print("Apartment single-path verified qualification: PASS")
    print("General/rental dormitory complete qualification resolution: PASS")
    print("Religious-assembly 4/나 ↔ 6/가 chained classification: PASS")
    print("Pub 4/더 ↔ 16/가 chained classification: PASS")
    print("Broadcast-station 3/바 ↔ 24/가 chained classification: PASS")
    print("Telecom 3/아 remains UNREGISTERED and 24/라 stays fail-closed: PASS")
    print("Performance-hall 4/가 ↔ 5/가 chained classification: PASS")
    print("Performance-hall major-use lookup: PASS")
    print("EV-charger 3/차 ↔ 20/자 chained classification: PASS")
    print("Retail, auto-sales, pub, shared-storage numeric boundaries: PASS")
    print("Power-facility exclusion remains UNSET without first-neighborhood candidate: PASS")
    print("Gymnasium 13/나 and playground 13/다 spectator-seat qualification: PASS")
    print("Animal-hospital 3/카 ↔ 4/차 chained classification: PASS")
    print("Office numeric + exclusion chain: PASS")
    print("Unknown major use and canonical name fail-closed: PASS")
    print("Four-state major-use aggregation: PASS")
    print("Four-state safe negation: PASS")
    print("Major-use classification state composition: PASS")
    print("Excluded major-use state composition: PASS")
    print(
        "Not proven: full non-numeric qualification coverage, automatic final classification "
        "derivation, final source-path selection, frontend integration, PROJECT "
        "mapping, or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
