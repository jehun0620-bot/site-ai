# -*- coding: utf-8 -*-

"""Memory-only Rule 125 full Building Use set candidate regression.

No production JSON is written. The candidate represents the exact source use set:
공연장 OR 집회장 OR 관람장, together with 자연경관지구 and
applicable_use_floor_area > 1000 square_meter.

집회장 public classification is still unresolved elsewhere. This test proves only
Rule Engine expression behavior when a confirmed canonical fact is supplied.
"""

from __future__ import annotations

import copy
from typing import Any, Dict

from law_data import rule_evaluation_pipeline as pipeline
from law_data.building_use_rule125_expression_admission import (
    admit_rule125_full_expression_candidate,
)

RULE_INDEX = 125
PARENT_INDEX = 123
VERIFIED = "VERIFIED"

EXPRESSION = {
    "op": "AND",
    "children": [
        {
            "op": "ATOM",
            "condition": {"type": "SITE", "name": "자연경관지구"},
        },
        {
            "op": "OR",
            "children": [
                {"op": "BUILDING_USE", "identity": "canonical", "value": "공연장"},
                {"op": "BUILDING_USE", "identity": "canonical", "value": "집회장"},
                {"op": "BUILDING_USE", "identity": "canonical", "value": "관람장"},
            ],
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
        item for item in result.get("rules", [])
        if isinstance(item, dict) and item.get("clause_index") == clause_index
    ]
    if len(matches) != 1:
        raise AssertionError(f"clause_index {clause_index} rule count: {len(matches)}")
    return matches[0]


def building_use_fact(name: str) -> Dict[str, Any]:
    return {
        "canonical_name": name,
        "major_use": "문화 및 집회시설",
        "source_path": "TEST_CONFIRMED_FACT",
        "classification_status": "RESOLVED",
    }


def run_candidate(
    *,
    building_use_name: str | None,
    applicable_area: float | str | None,
    spectator_area: float | None = None,
) -> Dict[str, Any]:
    original_load_json = pipeline.load_json
    original_snapshot = original_load_json(pipeline.SITE_COMPLETE_PATH)
    candidate_snapshot = copy.deepcopy(original_snapshot)
    candidate_rule = find_rule(candidate_snapshot, RULE_INDEX)

    admission = admit_rule125_full_expression_candidate(candidate_rule, EXPRESSION)
    if not admission.verified:
        raise AssertionError(f"candidate admission rejected: {admission.missing_gates}")

    candidate_rule["condition_expression"] = copy.deepcopy(EXPRESSION)
    candidate_rule["condition_expression_status"] = VERIFIED

    facts: Dict[str, Any] = {}
    if building_use_name is not None:
        facts["building_use"] = building_use_fact(building_use_name)
    if applicable_area == "UNKNOWN":
        facts["applicable_use_floor_area"] = {"state": "UNKNOWN"}
    elif applicable_area is not None:
        facts["applicable_use_floor_area"] = {
            "value": applicable_area,
            "unit": "square_meter",
        }
    if spectator_area is not None:
        facts["spectator_seating_area"] = {
            "value": spectator_area,
            "unit": "square_meter",
        }

    def candidate_load_json(path):
        loaded = original_load_json(path)
        return candidate_snapshot if path == pipeline.SITE_COMPLETE_PATH else loaded

    pipeline.load_json = candidate_load_json
    try:
        return pipeline.evaluate_site_rules(
            project_profile={},
            procedure_profile={},
            site_condition_context={
                "자연경관지구": {
                    "state": "TRUE",
                    "confidence": "HIGH",
                    "source": "RULE125_FULL_EXPRESSION_CANDIDATE_TEST",
                }
            },
            fact_context=facts,
        )
    finally:
        pipeline.load_json = original_load_json


def required_types(rule: Dict[str, Any]) -> list[str]:
    return [
        str(item.get("type"))
        for item in rule.get("required_inputs", [])
        if isinstance(item, dict)
    ]


def main() -> int:
    cases = {
        "performance 1001": run_candidate(building_use_name="공연장", applicable_area=1001),
        "spectator 1001": run_candidate(building_use_name="관람장", applicable_area=1001),
        "spectator 1000": run_candidate(building_use_name="관람장", applicable_area=1000),
        "assembly 1001 engine fact": run_candidate(building_use_name="집회장", applicable_area=1001),
        "office 1001": run_candidate(building_use_name="사무소", applicable_area=1001),
        "missing use": run_candidate(building_use_name=None, applicable_area=1001),
        "missing area": run_candidate(building_use_name="관람장", applicable_area=None),
        "unknown area": run_candidate(building_use_name="관람장", applicable_area="UNKNOWN"),
        "spectator-only numeric": run_candidate(
            building_use_name="관람장",
            applicable_area=None,
            spectator_area=5000,
        ),
    }
    target = {name: find_rule(result, RULE_INDEX) for name, result in cases.items()}
    parent = {name: find_rule(result, PARENT_INDEX) for name, result in cases.items()}

    missing_use_requirements = target["missing use"].get("required_inputs", [])
    missing_use_building_use = [
        item
        for item in missing_use_requirements
        if isinstance(item, dict) and item.get("type") == "BUILDING_USE"
    ]

    validations = {
        "all runs keep 314 rules": all(len(r.get("rules", [])) == 314 for r in cases.values()),
        "performance 1001 applicable": target["performance 1001"].get("applicability") == "APPLICABLE",
        "spectator 1001 applicable": target["spectator 1001"].get("applicability") == "APPLICABLE",
        "spectator 1000 not applicable": target["spectator 1000"].get("applicability") == "NOT_APPLICABLE",
        "assembly engine fact matches expression": target["assembly 1001 engine fact"].get("applicability") == "APPLICABLE",
        "office not applicable": target["office 1001"].get("applicability") == "NOT_APPLICABLE",
        "missing use conditional": target["missing use"].get("applicability") == "CONDITIONAL",
        "missing use requested": "BUILDING_USE" in required_types(target["missing use"]),
        "missing use is one canonical choice-set requirement": (
            missing_use_building_use
            == [
                {
                    "type": "BUILDING_USE",
                    "name": "building_use",
                    "identity": "canonical",
                    "state": "UNSET",
                    "allowed_values": ["공연장", "집회장", "관람장"],
                }
            ]
        ),
        "missing area conditional": target["missing area"].get("applicability") == "CONDITIONAL",
        "missing area requested": "NUMERIC_FACT" in required_types(target["missing area"]),
        "unknown area unknown": target["unknown area"].get("applicability") == "UNKNOWN",
        "spectator area cannot substitute applicable area": (
            target["spectator-only numeric"].get("applicability") == "CONDITIONAL"
            and "NUMERIC_FACT" in required_types(target["spectator-only numeric"])
        ),
        "parent retained": all(rule.get("clause_index") == PARENT_INDEX for rule in parent.values()),
        "candidate remains verified in memory": all(
            rule.get("condition_expression_status") == VERIFIED for rule in target.values()
        ),
    }

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: memory-only full-use-set expression candidate. "
        "집회장 public classification and production admission remain unproven."
    )
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
