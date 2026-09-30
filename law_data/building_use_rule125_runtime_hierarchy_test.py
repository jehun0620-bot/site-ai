# -*- coding: utf-8 -*-

"""
Rule 125 runtime hierarchy probe.

This test does not modify production JSON or Rule Engine code.
It uses the existing site_condition_context input to make
자연경관지구 TRUE at runtime, runs the real 314-rule pipeline,
and inspects Rule 123 / Rule 125 results.
"""

from __future__ import annotations

from typing import Any, Dict, List

from law_data.rule_evaluation_pipeline import evaluate_site_rules


PARENT_INDEX = 123
TARGET_INDEX = 125


def find_rule(
    rules: List[Dict[str, Any]],
    clause_index: int,
) -> Dict[str, Any]:
    matches = [
        rule
        for rule in rules
        if isinstance(rule, dict)
        and int(rule.get("clause_index", -1)) == clause_index
    ]

    if len(matches) != 1:
        raise AssertionError(
            f"clause_index {clause_index} rule count: {len(matches)}"
        )

    return matches[0]


def condition_summary(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []

    for condition in rule.get("conditions", []):
        if not isinstance(condition, dict):
            continue

        result.append(
            {
                "type": condition.get("type"),
                "name": condition.get("name"),
                "state": condition.get("state"),
                "confidence": condition.get("confidence"),
                "source": condition.get("source"),
            }
        )

    return result


def required_input_summary(rule: Dict[str, Any]) -> List[Dict[str, Any]]:
    result = []

    for item in rule.get("required_inputs", []):
        if not isinstance(item, dict):
            continue

        result.append(
            {
                "type": item.get("type"),
                "name": item.get("name"),
                "state": item.get("state"),
            }
        )

    return result


def main() -> int:
    result = evaluate_site_rules(
        site_condition_context={
            "자연경관지구": {
                "state": "TRUE",
                "confidence": "HIGH",
                "source": "RULE_125_RUNTIME_HIERARCHY_TEST",
            }
        }
    )

    rules = result.get("rules", [])

    if not isinstance(rules, list):
        raise AssertionError("evaluate_site_rules result rules가 list가 아님")

    assert len(rules) == 314, len(rules)

    parent = find_rule(rules, PARENT_INDEX)
    target = find_rule(rules, TARGET_INDEX)

    parent_conditions = condition_summary(parent)
    target_conditions = condition_summary(target)

    parent_natural = [
        condition
        for condition in parent_conditions
        if condition.get("name") == "자연경관지구"
    ]
    target_natural = [
        condition
        for condition in target_conditions
        if condition.get("name") == "자연경관지구"
    ]

    assert len(parent_natural) == 1, parent_natural
    assert len(target_natural) == 1, target_natural
    assert parent_natural[0].get("state") == "TRUE", parent_natural
    assert target_natural[0].get("state") == "TRUE", target_natural

    print("=" * 60)
    print("BUILDING USE RULE 125 RUNTIME HIERARCHY")
    print("=" * 60)
    print(f"Production rule count: {len(rules)}")
    print("Runtime SITE override: 자연경관지구 = TRUE")
    print()

    for label, rule in (
        ("PARENT", parent),
        ("TARGET", target),
    ):
        print(label)
        print(f"  clause_index: {rule.get('clause_index')}")
        print(f"  paragraph: {rule.get('paragraph')}")
        print(f"  item: {rule.get('item')}")
        print(f"  applicability: {rule.get('applicability')}")
        print(f"  reason: {rule.get('applicability_reason')}")
        print(f"  conditions: {condition_summary(rule)}")
        print(f"  required_inputs: {required_input_summary(rule)}")
        print(
            "  expression_status: "
            f"{rule.get('condition_expression_status')}"
        )
        print(
            "  expression_present: "
            f"{isinstance(rule.get('condition_expression'), dict)}"
        )
        print()

    print("CONFIRMED")
    print("  - Runtime 자연경관지구 TRUE reached Rule 123.")
    print("  - Runtime 자연경관지구 TRUE reached Rule 125.")
    print("  - Both entries remain present in the 314-rule result.")
    print()
    print("NOT DECIDED BY THIS TEST")
    print("  - Whether Rule 123 should be suppressed or retained.")
    print("  - Whether Rule 125 should receive a production expression.")
    print("  - Whether parent/child evaluation policy must change.")
    print()
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
