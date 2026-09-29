# -*- coding: utf-8 -*-
"""Regression for the initial verified Annex 1 qualification registry."""

from law_data.building_use_annex1_qualification_registry import (
    VERIFIED,
    VERIFIED_QUALIFICATION_RULES,
    qualification_rule_for_path,
)
from law_data.building_use_annex1_semantic_model import SourcePath
from law_data.rule_evaluation_pipeline import evaluate_condition_expression


EXPECTED_PATHS = ("2/가", "2/나", "2/다", "3/마", "5/가")


def fact(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def evaluate(path: str, facts: dict) -> str:
    rule = qualification_rule_for_path(SourcePath(*path.split("/")))
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

    performance_hall = qualification_rule_for_path(SourcePath("5", "가"))
    if performance_hall is None:
        raise AssertionError("Verified 5/가 qualification rule missing.")
    if performance_hall.expression is not None:
        raise AssertionError("5/가 must not invent a numeric/general expression.")
    if performance_hall.excluded_major_uses != ("제2종 근린생활시설",):
        raise AssertionError("5/가 excluded major-use mismatch.")

    if qualification_rule_for_path(SourcePath("13", "가")) is not None:
        raise AssertionError("Unverified 13/가 must not be admitted.")

    print("RESULT: PASS")
    print("Verified qualification rule count:", len(VERIFIED_QUALIFICATION_RULES))
    print("Verified source paths:", tuple(VERIFIED_QUALIFICATION_RULES))
    print("2/가 apartment boundary + UNSET: PASS")
    print("2/나 row-house GT + LTE boundaries: PASS")
    print("2/다 multiplex-house LTE boundaries: PASS")
    print("3/마 table-tennis/dojo LT boundary: PASS")
    print("5/가 performance-hall major-use exclusion registration: PASS")
    print("Unverified source path fail-closed: PASS")
    print(
        "Not proven: full Annex 1 qualification coverage, non-numeric "
        "qualification evaluation, final canonical-use resolution, frontend "
        "integration, PROJECT mapping, or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
