# -*- coding: utf-8 -*-
"""Regression for the initial verified Annex 1 qualification registry."""

from law_data.building_use_annex1_qualification_registry import (
    VERIFIED,
    VERIFIED_CANONICAL_QUALIFICATION_RULES,
    VERIFIED_QUALIFICATION_RULES,
    qualification_rule_for_path,
    qualification_rules_for_candidate,
)
from law_data.building_use_annex1_semantic_model import SourcePath
from law_data.rule_evaluation_pipeline import evaluate_condition_expression


EXPECTED_PATHS = ("3/가", "3/차", "4/다", "4/카", "4/더", "4/버", "20/자", "25", "2/가", "2/나", "2/다", "2/라/1", "2/라/2", "4/나", "6/가", "16/가", "3/바", "24/가", "24/라", "3/마", "4/가", "3/카", "4/차", "3/자", "4/하", "14/나/1", "13/가", "13/나", "13/다", "5/가")


def fact(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def source_path_from_key(path: str) -> SourcePath:
    parts = path.split("/")
    if len(parts) == 1:
        return SourcePath(parts[0])
    if len(parts) == 2:
        return SourcePath(parts[0], parts[1])
    if len(parts) == 3:
        return SourcePath(parts[0], parts[1], int(parts[2]))
    raise ValueError(f"unsupported source path: {path}")


def evaluate(path: str, facts: dict) -> str:
    rule = qualification_rule_for_path(source_path_from_key(path))
    if rule is None:
        raise AssertionError(f"qualification rule missing: {path}")
    if rule.expression is None:
        raise AssertionError(f"numeric expression missing: {path}")
    return evaluate_condition_expression({}, rule.expression, facts).get("state")


def assert_state(path: str, facts: dict, expected: str) -> None:
    actual = evaluate(path, facts)
    if actual != expected:
        raise AssertionError(
            f"{path}: expected state {expected}, got {actual}; facts={facts}"
        )


def main() -> None:
    if tuple(VERIFIED_QUALIFICATION_RULES) != EXPECTED_PATHS:
        raise AssertionError(
            f"Unexpected qualification paths: {tuple(VERIFIED_QUALIFICATION_RULES)}"
        )

    for path, rule in VERIFIED_QUALIFICATION_RULES.items():
        if rule.source_path.key != path:
            raise AssertionError(
                f"registry key mismatch: {path} != {rule.source_path.key}"
            )
        if rule.expression_status != VERIFIED:
            raise AssertionError(f"non-VERIFIED rule admitted: {path}")
        if not rule.source_text.strip():
            raise AssertionError(f"source text missing: {path}")

    assert_state(
        "2/가",
        {"residential_floor_count": fact(5, "floor")},
        "TRUE",
    )
    assert_state(
        "2/가",
        {"residential_floor_count": fact(4, "floor")},
        "FALSE",
    )
    assert_state("2/가", {}, "UNSET")

    assert_state(
        "2/나",
        {
            "residential_floor_area": fact(661, "square_meter"),
            "residential_floor_count": fact(4, "floor"),
        },
        "TRUE",
    )
    assert_state(
        "2/나",
        {
            "residential_floor_area": fact(660, "square_meter"),
            "residential_floor_count": fact(4, "floor"),
        },
        "FALSE",
    )
    assert_state(
        "2/나",
        {
            "residential_floor_area": fact(661, "square_meter"),
            "residential_floor_count": fact(5, "floor"),
        },
        "FALSE",
    )

    assert_state(
        "2/다",
        {
            "residential_floor_area": fact(660, "square_meter"),
            "residential_floor_count": fact(4, "floor"),
        },
        "TRUE",
    )
    assert_state(
        "2/다",
        {
            "residential_floor_area": fact(661, "square_meter"),
            "residential_floor_count": fact(4, "floor"),
        },
        "FALSE",
    )

    general_dormitory_true = {
        "dormitory_building_standard_compliant": {"state": "TRUE"},
        "has_individually_owned_room": {"state": "FALSE"},
        "general_dormitory_eligible_occupancy": {"state": "TRUE"},
        "common_cooking_household_ratio": fact(50, "percent"),
    }
    assert_state("2/라/1", general_dormitory_true, "TRUE")
    assert_state(
        "2/라/1",
        {**general_dormitory_true, "common_cooking_household_ratio": fact(49, "percent")},
        "FALSE",
    )
    assert_state(
        "2/라/1",
        {**general_dormitory_true, "dormitory_building_standard_compliant": {"state": "FALSE"}},
        "FALSE",
    )
    assert_state(
        "2/라/1",
        {**general_dormitory_true, "has_individually_owned_room": {"state": "TRUE"}},
        "FALSE",
    )
    assert_state("2/라/1", {}, "UNSET")

    rental_dormitory_true = {
        "dormitory_building_standard_compliant": {"state": "TRUE"},
        "has_individually_owned_room": {"state": "FALSE"},
        "qualified_dormitory_rental_operator": {"state": "TRUE"},
        "rental_room_count": fact(20, "room"),
        "common_cooking_household_ratio": fact(50, "percent"),
    }
    assert_state("2/라/2", rental_dormitory_true, "TRUE")
    assert_state(
        "2/라/2",
        {**rental_dormitory_true, "rental_room_count": fact(19, "room")},
        "FALSE",
    )
    assert_state(
        "2/라/2",
        {**rental_dormitory_true, "common_cooking_household_ratio": fact(49, "percent")},
        "FALSE",
    )
    assert_state(
        "2/라/2",
        {**rental_dormitory_true, "qualified_dormitory_rental_operator": {"state": "FALSE"}},
        "FALSE",
    )
    assert_state(
        "2/라/2",
        {**rental_dormitory_true, "has_individually_owned_room": {"state": "TRUE"}},
        "FALSE",
    )
    assert_state("2/라/2", {}, "UNSET")

    assert_state("4/나", {"use_floor_area": fact(499, "square_meter")}, "TRUE")
    assert_state("4/나", {"use_floor_area": fact(500, "square_meter")}, "FALSE")
    assert_state("3/바", {"use_floor_area": fact(999, "square_meter")}, "TRUE")
    assert_state("3/바", {"use_floor_area": fact(1000, "square_meter")}, "FALSE")

    assert qualification_rule_for_path(SourcePath("6", "가")).excluded_major_uses == ("제2종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("16", "가")).excluded_major_uses == ("제2종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("24", "가")).excluded_major_uses == ("제1종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("24", "라")).excluded_major_uses == ("제1종 근린생활시설",)

    # 3/아 is intentionally unregistered: its 1,000㎡ condition applies only
    # to one canonical use inside this MULTI_USE source path.
    if qualification_rule_for_path(SourcePath("3", "아")) is not None:
        raise AssertionError("3/아 must remain unregistered at SourcePath scope.")

    telecom_rules = qualification_rules_for_candidate(
        SourcePath("3", "아"), "통신용 시설"
    )
    assert len(telecom_rules) == 1
    telecom_rule = telecom_rules[0]
    assert telecom_rule.source_path == SourcePath("3", "아")
    assert telecom_rule.expression == {
        "op": "NUMERIC",
        "target": "use_floor_area",
        "operator": "LT",
        "value": 1000,
        "unit": "square_meter",
    }
    for other_name in ("변전소", "도시가스배관시설", "정수장", "양수장"):
        assert qualification_rules_for_candidate(
            SourcePath("3", "아"), other_name
        ) == ()
    assert len(VERIFIED_CANONICAL_QUALIFICATION_RULES) == 1

    assert_state(
        "3/마",
        {"use_floor_area": fact(499, "square_meter")},
        "TRUE",
    )
    assert_state(
        "3/마",
        {"use_floor_area": fact(500, "square_meter")},
        "FALSE",
    )

    for path, below, boundary in (
        ("3/가", 999, 1000),
        ("3/차", 999, 1000),
        ("4/다", 999, 1000),
        ("4/카", 499, 500),
        ("4/더", 149, 150),
        ("4/버", 999, 1000),
    ):
        assert_state(path, {"use_floor_area": fact(below, "square_meter")}, "TRUE")
        assert_state(path, {"use_floor_area": fact(boundary, "square_meter")}, "FALSE")

    assert_state("4/카", {}, "UNSET")

    assert qualification_rule_for_path(SourcePath("20", "자")).excluded_major_uses == ("제1종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("25")).excluded_major_uses == ("제1종 근린생활시설",)

    assert_state("4/가", {"use_floor_area": fact(499, "square_meter")}, "TRUE")
    assert_state("4/가", {"use_floor_area": fact(500, "square_meter")}, "FALSE")
    assert_state("3/카", {"use_floor_area": fact(299, "square_meter")}, "TRUE")
    assert_state("3/카", {"use_floor_area": fact(300, "square_meter")}, "FALSE")
    assert_state("3/자", {"use_floor_area": fact(29, "square_meter")}, "TRUE")
    assert_state("3/자", {"use_floor_area": fact(30, "square_meter")}, "FALSE")
    assert_state("4/하", {"use_floor_area": fact(499, "square_meter")}, "TRUE")
    assert_state("4/하", {"use_floor_area": fact(500, "square_meter")}, "FALSE")

    assert qualification_rule_for_path(SourcePath("4", "차")).excluded_major_uses == ("제1종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("4", "하")).excluded_major_uses == ("제1종 근린생활시설",)
    assert qualification_rule_for_path(SourcePath("14", "나", 1)).excluded_major_uses == ("제1종 근린생활시설", "제2종 근린생활시설")
    assert qualification_rule_for_path(SourcePath("13", "가")).excluded_major_uses == ("제1종 근린생활시설", "제2종 근린생활시설")

    for path in ("13/나", "13/다"):
        assert_state(
            path,
            {"has_spectator_seating": {"state": "FALSE"}},
            "TRUE",
        )
        assert_state(
            path,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": fact(999, "square_meter"),
            },
            "TRUE",
        )
        assert_state(
            path,
            {
                "has_spectator_seating": {"state": "TRUE"},
                "spectator_seating_area": fact(1000, "square_meter"),
            },
            "FALSE",
        )
        assert_state(path, {}, "UNSET")

    performance_hall = qualification_rule_for_path(SourcePath("5", "가"))
    if performance_hall is None:
        raise AssertionError("Verified 5/가 qualification rule missing.")
    if performance_hall.expression is not None:
        raise AssertionError("5/가 must not invent a numeric/general expression.")
    if performance_hall.excluded_major_uses != ("제2종 근린생활시설",):
        raise AssertionError("5/가 excluded major-use mismatch.")

    print("RESULT: PASS")
    print("Verified qualification rule count:", len(VERIFIED_QUALIFICATION_RULES))
    print("Verified source paths:", tuple(VERIFIED_QUALIFICATION_RULES))
    print("2/가 apartment boundary + UNSET: PASS")
    print("2/나 row-house GT + LTE boundaries: PASS")
    print("2/다 multiplex-house LTE boundaries: PASS")
    print("2/라/1 general-dormitory common/state/ratio qualification: PASS")
    print("2/라/2 rental-dormitory common/operator/room/ratio qualification: PASS")
    print("4/나, 3/바 numeric boundaries: PASS")
    print("6/가, 16/가, 24/가, 24/라 major-use exclusions: PASS")
    print("3/아 remains intentionally unregistered at SourcePath scope: PASS")
    print("3/아 + 통신용 시설 canonical-specific qualification: PASS")
    print("Canonical-specific qualification rule count:", len(VERIFIED_CANONICAL_QUALIFICATION_RULES))
    print("3/마 table-tennis/dojo LT boundary: PASS")
    print("3/가, 3/차, 4/다, 4/카, 4/더, 4/버 numeric boundaries: PASS")
    print("4/카 missing fact remains UNSET through shared numeric semantics: PASS")
    print("20/자, 25 first-neighborhood exclusions: PASS")
    print("4/가, 3/카, 3/자, 4/하 numeric boundaries: PASS")
    print("4/차, 4/하 single major-use exclusions: PASS")
    print("13/가, 14/나/1 dual major-use exclusions: PASS")
    print("13/나, 13/다 spectator-seat STATE/NOT/NUMERIC boundaries: PASS")
    print("5/가 performance-hall major-use exclusion registration: PASS")
    print("Unverified source path fail-closed: PASS")
    print(
        "Not proven: full Annex 1 qualification coverage, non-numeric "
        "qualification evaluation, final canonical-use resolution, frontend "
        "integration, PROJECT mapping, or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
