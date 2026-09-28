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

    rule = _find_rule(
        {"rules": candidate_snapshot["rules"]},
        3,
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

    result_checks = {
        "admission": admission.verified,
        "applicability": (
            baseline_rule.get("applicability")
            == candidate_rule.get("applicability")
        ),
        "required_inputs": (
            baseline_rule.get("required_inputs")
            == candidate_rule.get("required_inputs")
        ),
        "blocked_by": (
            baseline_rule.get("blocked_by")
            == candidate_rule.get("blocked_by")
        ),
        "unknown_by": (
            baseline_rule.get("unknown_by")
            == candidate_rule.get("unknown_by")
        ),
        "numeric_effect": (
            baseline_rule.get("numeric_effect")
            == candidate_rule.get("numeric_effect")
        ),
        "current_numeric_effect": (
            baseline_rule.get("current_numeric_effect")
            == candidate_rule.get("current_numeric_effect")
        ),
        "rule_count": (
            len(baseline.get("rules", []))
            == len(candidate.get("rules", []))
            == 314
        ),
        "bcr": (
            baseline.get("numeric", {}).get(
                "building_coverage_ratio"
            )
            == candidate.get("numeric", {}).get(
                "building_coverage_ratio"
            )
            == 50.0
        ),
        "far": (
            baseline.get("numeric", {}).get(
                "floor_area_ratio"
            )
            == candidate.get("numeric", {}).get(
                "floor_area_ratio"
            )
            == 250.0
        ),
        "expression_status": (
            candidate_rule.get(
                "condition_expression_status"
            )
            == VERIFIED
        ),
    }

    print("=== E-5 INDEX 3 BEHAVIORAL REGRESSION ===")
    print("ADMISSION_STATUS =", admission.status)
    print(
        "BASELINE_APPLICABILITY =",
        baseline_rule.get("applicability"),
    )
    print(
        "CANDIDATE_APPLICABILITY =",
        candidate_rule.get("applicability"),
    )
    print(
        "BASELINE_REASON =",
        baseline_rule.get("applicability_reason"),
    )
    print(
        "CANDIDATE_REASON =",
        candidate_rule.get("applicability_reason"),
    )
    print(
        "DIFF_REASON_ONLY =",
        baseline_rule.get("applicability_reason")
        != candidate_rule.get("applicability_reason"),
    )

    for name, passed in result_checks.items():
        print(
            name.upper(),
            "=",
            passed,
        )

    all_pass = all(
        result_checks.values()
    )

    print("all_pass:", all_pass)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
