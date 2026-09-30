# -*- coding: utf-8 -*-

"""
Rule 125 performance-hall production-candidate regression.

This is a memory-only candidate test. It does not write production JSON.

The test copies the real 314-rule snapshot, attaches the already-tested
performance-hall expression to Rule 125 in memory, marks that copied rule
VERIFIED only for candidate execution, and runs the real Rule Engine.

Important:
- This does NOT grant production admission.
- This proves only the 공연장 branch.
- 집회장 / 관람장 remain outside the proven classifier scope.
"""

from __future__ import annotations

import copy
from typing import Any, Dict

from law_data import rule_evaluation_pipeline as pipeline


RULE_INDEX = 125
PARENT_INDEX = 123
VERIFIED = "VERIFIED"

EXPRESSION = {
    "op": "AND",
    "children": [
        {
            "op": "ATOM",
            "condition": {
                "type": "SITE",
                "name": "자연경관지구",
            },
        },
        {
            "op": "BUILDING_USE",
            "identity": "canonical",
            "value": "공연장",
        },
        {
            "op": "NUMERIC",
            "target": "applicable_use_floor_area",
            "operator": "GT",
            "value": 1000,
            "unit": "square_meter",
        },
    ],
}


def find_rule(result: Dict[str, Any], clause_index: int) -> Dict[str, Any]:
    matches = [
        item
        for item in result.get("rules", [])
        if isinstance(item, dict)
        and item.get("clause_index") == clause_index
    ]
    if len(matches) != 1:
        raise AssertionError(
            f"clause_index {clause_index} rule count: {len(matches)}"
        )
    return matches[0]


def building_use_fact(canonical_name: str) -> Dict[str, Any]:
    return {
        "canonical_name": canonical_name,
        "major_use": "문화 및 집회시설",
        "source_path": "5/가",
        "classification_status": "RESOLVED",
    }


def area_fact(value: float) -> Dict[str, Any]:
    return {
        "value": value,
        "unit": "square_meter",
    }


def run_candidate(
    *,
    building_use_name: str | None,
    applicable_use_floor_area: float | None,
) -> Dict[str, Any]:
    original_load_json = pipeline.load_json
    original_snapshot = original_load_json(pipeline.SITE_COMPLETE_PATH)
    candidate_snapshot = copy.deepcopy(original_snapshot)

    candidate_rule = find_rule(candidate_snapshot, RULE_INDEX)
    candidate_rule["condition_expression"] = copy.deepcopy(EXPRESSION)
    candidate_rule["condition_expression_status"] = VERIFIED

    facts: Dict[str, Any] = {}
    if building_use_name is not None:
        facts["building_use"] = building_use_fact(building_use_name)
    if applicable_use_floor_area is not None:
        facts["applicable_use_floor_area"] = area_fact(
            applicable_use_floor_area
        )

    def candidate_load_json(path):
        loaded = original_load_json(path)
        if path == pipeline.SITE_COMPLETE_PATH:
            return candidate_snapshot
        return loaded

    pipeline.load_json = candidate_load_json
    try:
        return pipeline.evaluate_site_rules(
            project_profile={},
            procedure_profile={},
            site_condition_context={
                "자연경관지구": {
                    "state": "TRUE",
                    "confidence": "HIGH",
                    "source": "RULE_125_PRODUCTION_CANDIDATE_TEST",
                }
            },
            fact_context=facts,
        )
    finally:
        pipeline.load_json = original_load_json


def requirement_types(rule: Dict[str, Any]) -> list[str]:
    return [
        str(item.get("type"))
        for item in rule.get("required_inputs", [])
        if isinstance(item, dict)
    ]


def main() -> int:
    cases = {
        "performance hall 1001": run_candidate(
            building_use_name="공연장",
            applicable_use_floor_area=1001,
        ),
        "performance hall 1000": run_candidate(
            building_use_name="공연장",
            applicable_use_floor_area=1000,
        ),
        "different building use": run_candidate(
            building_use_name="사무소",
            applicable_use_floor_area=1001,
        ),
        "missing building use": run_candidate(
            building_use_name=None,
            applicable_use_floor_area=1001,
        ),
        "missing applicable area": run_candidate(
            building_use_name="공연장",
            applicable_use_floor_area=None,
        ),
    }

    target = {
        name: find_rule(result, RULE_INDEX)
        for name, result in cases.items()
    }
    parent = {
        name: find_rule(result, PARENT_INDEX)
        for name, result in cases.items()
    }

    validations = {
        "all candidate runs keep 314 rules": all(
            len(result.get("rules", [])) == 314
            for result in cases.values()
        ),
        "performance hall 1001 applicable": (
            target["performance hall 1001"].get("applicability")
            == "APPLICABLE"
        ),
        "1000 boundary not applicable": (
            target["performance hall 1000"].get("applicability")
            == "NOT_APPLICABLE"
        ),
        "different building use not applicable": (
            target["different building use"].get("applicability")
            == "NOT_APPLICABLE"
        ),
        "missing building use conditional": (
            target["missing building use"].get("applicability")
            == "CONDITIONAL"
        ),
        "missing building use requested": (
            "BUILDING_USE"
            in requirement_types(target["missing building use"])
        ),
        "missing area conditional": (
            target["missing applicable area"].get("applicability")
            == "CONDITIONAL"
        ),
        "missing area requested": (
            "NUMERIC_FACT"
            in requirement_types(target["missing applicable area"])
        ),
        "parent remains conditional": all(
            rule.get("applicability") == "CONDITIONAL"
            for rule in parent.values()
        ),
        "parent still requests procedure": all(
            "PROCEDURE" in requirement_types(rule)
            for rule in parent.values()
        ),
        "candidate expression remains verified in result": all(
            rule.get("condition_expression_status") == VERIFIED
            for rule in target.values()
        ),
    }

    print("=" * 70)
    print("RULE 125 PERFORMANCE-HALL PRODUCTION CANDIDATE")
    print("=" * 70)

    for name, rule in target.items():
        print()
        print(name)
        print("  applicability:", rule.get("applicability"))
        print("  reason:", rule.get("applicability_reason"))
        print("  required_inputs:", rule.get("required_inputs"))

    print()
    print("PARENT RULE 123")
    for name, rule in parent.items():
        print(
            f"  {name}: "
            f"{rule.get('applicability')} | "
            f"{requirement_types(rule)}"
        )

    print()
    print("VALIDATIONS")
    for name, passed in validations.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: memory-only production candidate; "
        "공연장 branch only; no production admission granted."
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
