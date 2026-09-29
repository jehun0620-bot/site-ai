# -*- coding: utf-8 -*-
"""Compatibility regression for STATE + NOT building-use qualification primitives."""

from law_data.rule_evaluation_pipeline import evaluate_condition_expression


def state_fact(state: str) -> dict:
    return {"state": state}


def numeric_fact(value: float, unit: str) -> dict:
    return {"value": value, "unit": unit}


def evaluate(expression: dict, facts: dict | None = None) -> str:
    return evaluate_condition_expression({}, expression, facts).get("state")


def main() -> None:
    state_expression = {
        "op": "STATE",
        "target": "has_spectator_seating",
    }

    for state in ("TRUE", "FALSE", "UNKNOWN", "UNSET"):
        actual = evaluate(
            state_expression,
            {"has_spectator_seating": state_fact(state)},
        )
        assert actual == state, (state, actual)

    assert evaluate(state_expression, {}) == "UNSET"
    assert evaluate(state_expression, None) == "UNSET"
    assert evaluate(
        state_expression,
        {"has_spectator_seating": {"state": "INVALID"}},
    ) == "UNKNOWN"
    assert evaluate(
        state_expression,
        {"has_spectator_seating": True},
    ) == "UNKNOWN"

    not_expression = {
        "op": "NOT",
        "child": state_expression,
    }
    expected_not = {
        "TRUE": "FALSE",
        "FALSE": "TRUE",
        "UNKNOWN": "UNKNOWN",
        "UNSET": "UNSET",
    }
    for state, expected in expected_not.items():
        actual = evaluate(
            not_expression,
            {"has_spectator_seating": state_fact(state)},
        )
        assert actual == expected, (state, actual)

    spectator_expression = {
        "op": "OR",
        "children": [
            not_expression,
            {
                "op": "NUMERIC",
                "target": "spectator_seating_area",
                "operator": "LT",
                "value": 1000,
                "unit": "square_meter",
            },
        ],
    }

    cases = [
        (
            {
                "has_spectator_seating": state_fact("FALSE"),
            },
            "TRUE",
        ),
        (
            {
                "has_spectator_seating": state_fact("TRUE"),
                "spectator_seating_area": numeric_fact(999, "square_meter"),
            },
            "TRUE",
        ),
        (
            {
                "has_spectator_seating": state_fact("TRUE"),
                "spectator_seating_area": numeric_fact(1000, "square_meter"),
            },
            "FALSE",
        ),
        (
            {},
            "UNSET",
        ),
        (
            {
                "has_spectator_seating": state_fact("UNKNOWN"),
            },
            "UNKNOWN",
        ),
    ]

    for facts, expected in cases:
        actual = evaluate(spectator_expression, facts)
        assert actual == expected, (facts, actual)

    malformed_not = {"op": "NOT", "child": "invalid"}
    assert evaluate(malformed_not, {}) == "UNKNOWN"

    unsupported = {"op": "STATE", "target": ""}
    assert evaluate(unsupported, {}) == "UNKNOWN"

    print("RESULT: PASS")
    print("STATE TRUE/FALSE/UNKNOWN/UNSET passthrough: PASS")
    print("STATE missing fact remains UNSET: PASS")
    print("STATE malformed fact fails UNKNOWN: PASS")
    print("NOT preserves four-state safety: PASS")
    print("OR(NOT STATE, NUMERIC) spectator-seat pattern: PASS")
    print("Malformed STATE/NOT fail-closed: PASS")
    print(
        "Not proven: Annex 1 13/나 or 13/다 registry linkage, frontend input, "
        "final source-path selection, PROJECT mapping, or Rule Engine end-to-end integration."
    )


if __name__ == "__main__":
    main()
