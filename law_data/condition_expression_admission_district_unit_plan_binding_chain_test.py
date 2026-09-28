from __future__ import annotations

import copy

from law_data import rule_evaluation_pipeline as pipeline
from law_data.condition_expression_admission import VERIFIED


TARGET_INDEXES = (49, 50, 314)
CONDITION_NAME = "지구단위계획"
CONDITION_TYPE = "SITE"
RUNTIME_SOURCE = "RUNTIME_SPATIAL_CONDITION"


def _find_rule(result, clause_index):
    return next(
        rule
        for rule in result.get("rules", [])
        if isinstance(rule, dict)
        and rule.get("clause_index") == clause_index
    )


def _condition(rule):
    return next(
        item
        for item in rule.get("conditions", [])
        if isinstance(item, dict)
        and item.get("name") == CONDITION_NAME
        and item.get("type") == CONDITION_TYPE
    )


def _runtime_context(state):
    return {
        CONDITION_NAME: {
            "name": CONDITION_NAME,
            "type": CONDITION_TYPE,
            "state": state,
            "confidence": "HIGH",
            "source": {
                "dataset": "LT_C_UPISUQ161",
                "test_marker": "E5_DERIVED_BINDING_CHAIN",
            },
            "resolution": "E5_DERIVED_BINDING_CHAIN",
            "pnu": "TEST_PNU",
        }
    }


def _evaluate(snapshot, state, verified_expression):
    original_load_json = pipeline.load_json
    candidate_snapshot = copy.deepcopy(snapshot)

    if verified_expression:
        for clause_index in TARGET_INDEXES:
            rule = next(
                item
                for item in candidate_snapshot.get("rules", [])
                if isinstance(item, dict)
                and item.get("clause_index") == clause_index
            )
            rule["condition_expression"] = {
                "op": "ATOM",
                "condition": {
                    "name": CONDITION_NAME,
                    "type": CONDITION_TYPE,
                },
            }
            rule["condition_expression_status"] = VERIFIED

    def candidate_load_json(path):
        if path == pipeline.SITE_COMPLETE_PATH:
            return copy.deepcopy(candidate_snapshot)
        return original_load_json(path)

    pipeline.load_json = candidate_load_json
    try:
        return pipeline.evaluate_site_rules(
            project_profile={},
            procedure_profile={},
            site_condition_context=_runtime_context(state),
        )
    finally:
        pipeline.load_json = original_load_json


def main():
    snapshot = pipeline.load_json(pipeline.SITE_COMPLETE_PATH)

    source_rules = {
        index: next(
            rule
            for rule in snapshot.get("rules", [])
            if isinstance(rule, dict)
            and rule.get("clause_index") == index
        )
        for index in TARGET_INDEXES
    }

    source_binding_ok = all(
        len(rule.get("conditions", [])) == 1
        and _condition(rule).get("derived") is True
        and _condition(rule).get("derived_from") == "rule_title"
        for rule in source_rules.values()
    )

    failures = []
    cases = {}

    for state in ("TRUE", "FALSE", "UNKNOWN"):
        legacy = _evaluate(snapshot, state, False)
        expression = _evaluate(snapshot, state, True)

        case_rows = []
        for index in TARGET_INDEXES:
            legacy_rule = _find_rule(legacy, index)
            expression_rule = _find_rule(expression, index)
            legacy_condition = _condition(legacy_rule)
            expression_condition = _condition(expression_rule)

            provenance_ok = (
                legacy_condition.get("state") == state
                and legacy_condition.get("confidence") == "HIGH"
                and legacy_condition.get("source") == RUNTIME_SOURCE
                and expression_condition.get("state") == state
                and expression_condition.get("source") == RUNTIME_SOURCE
            )

            behavior_ok = all(
                legacy_rule.get(key) == expression_rule.get(key)
                for key in (
                    "applicability",
                    "required_inputs",
                    "blocked_by",
                    "unknown_by",
                    "numeric_effect",
                    "current_numeric_effect",
                )
            )

            row = {
                "index": index,
                "state": state,
                "provenance_ok": provenance_ok,
                "behavior_ok": behavior_ok,
                "legacy_applicability": legacy_rule.get("applicability"),
                "expression_applicability": expression_rule.get("applicability"),
            }
            case_rows.append(row)

            if not provenance_ok or not behavior_ok:
                failures.append(row)

        cases[state] = case_rows

    print("=== E-5 DISTRICT UNIT PLAN DERIVED BINDING CHAIN ===")
    print("TARGET_INDEXES =", TARGET_INDEXES)
    print("SOURCE_BINDING_OK =", source_binding_ok)

    for state in ("TRUE", "FALSE", "UNKNOWN"):
        rows = cases[state]
        print(
            state,
            "PROVENANCE_PASS =",
            sum(1 for row in rows if row["provenance_ok"]),
            "/",
            len(rows),
            "| BEHAVIOR_PASS =",
            sum(1 for row in rows if row["behavior_ok"]),
            "/",
            len(rows),
        )

    if failures:
        print()
        print("=== FAILURES ===")
        for row in failures:
            print(row)

    validations = {
        "source binding": source_binding_ok,
        "all provenance": all(
            row["provenance_ok"]
            for rows in cases.values()
            for row in rows
        ),
        "all behavior": all(
            row["behavior_ok"]
            for rows in cases.values()
            for row in rows
        ),
    }

    all_pass = all(validations.values())
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
