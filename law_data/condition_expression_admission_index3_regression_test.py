from __future__ import annotations

import copy

from law_data import rule_evaluation_pipeline as pipeline
from law_data.condition_expression_admission import (
    VERIFIED,
    admit_atom_expression,
)


def _find_rule(result, clause_index):
    return next(
        item
        for item in result.get("rules", [])
        if isinstance(item, dict)
        and item.get("clause_index") == clause_index
    )


def main() -> int:
    original_load_json = pipeline.load_json

    baseline = pipeline.evaluate_site_rules(
        project_profile={},
        procedure_profile={},
    )

    original_snapshot = original_load_json(
        pipeline.SITE_COMPLETE_PATH
    )

    candidate_snapshot = copy.deepcopy(
        original_snapshot
    )

    rule = next(
        item
        for item in candidate_snapshot.get("rules", [])
        if isinstance(item, dict)
        and item.get("clause_index") == 3
    )

    expression = {
        "op": "ATOM",
        "condition": {
            "name": "지구단위계획",
            "type": "SITE",
        },
    }

    admission = admit_atom_expression(
        rule,
        expression,
    )

    if not admission.verified:
        print("ADMISSION_VERIFIED = False")
        print("MISSING_GATES =", admission.missing_gates)
        return 1

    rule["condition_expression"] = expression
    rule["condition_expression_status"] = VERIFIED

    def candidate_load_json(path):
        loaded = original_load_json(path)
        if path == pipeline.SITE_COMPLETE_PATH:
            return candidate_snapshot
        return loaded

    pipeline.load_json = candidate_load_json

    try:
        candidate = pipeline.evaluate_site_rules(
            project_profile={},
            procedure_profile={},
        )
    finally:
        pipeline.load_json = original_load_json

    baseline_rule = _find_rule(baseline, 3)
    candidate_rule = _find_rule(candidate, 3)

    operational_keys = [
        "applicability",
        "applicability_reason",
        "required_inputs",
        "blocked_by",
        "unknown_by",
        "numeric_effect",
        "current_numeric_effect",
    ]

    operational_equal = all(
        baseline_rule.get(key) == candidate_rule.get(key)
        for key in operational_keys
    )

    validations = {
        "admission verified": admission.verified,
        "baseline clause 3 applicable": (
            baseline_rule.get("applicability") == "APPLICABLE"
        ),
        "candidate expression verified": (
            candidate_rule.get("condition_expression_status")
            == VERIFIED
        ),
        "candidate clause 3 applicable": (
            candidate_rule.get("applicability") == "APPLICABLE"
        ),
        "operational behavior preserved": operational_equal,
        "baseline rule count 314": (
            len(baseline.get("rules", [])) == 314
        ),
        "candidate rule count 314": (
            len(candidate.get("rules", [])) == 314
        ),
        "baseline BCR 50": (
            baseline.get("numeric", {}).get("building_coverage_ratio")
            == 50.0
        ),
        "candidate BCR 50": (
            candidate.get("numeric", {}).get("building_coverage_ratio")
            == 50.0
        ),
        "baseline FAR 250": (
            baseline.get("numeric", {}).get("floor_area_ratio")
            == 250.0
        ),
        "candidate FAR 250": (
            candidate.get("numeric", {}).get("floor_area_ratio")
            == 250.0
        ),
    }

    all_pass = all(validations.values())

    print("=== E-5 INDEX 3 CANDIDATE REGRESSION ===")
    print("ADMISSION_STATUS =", admission.status)
    print("BASELINE_CLAUSE_3 =", baseline_rule.get("applicability"))
    print("CANDIDATE_CLAUSE_3 =", candidate_rule.get("applicability"))
    print("OPERATIONAL_BEHAVIOR_PRESERVED =", operational_equal)
    print(
        "BASELINE_SUMMARY =",
        baseline.get("summary"),
    )
    print(
        "CANDIDATE_SUMMARY =",
        candidate.get("summary"),
    )
    print("all_pass:", all_pass)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
