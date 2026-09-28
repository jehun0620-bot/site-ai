from __future__ import annotations

import copy

from law_data import rule_evaluation_pipeline as pipeline
from law_data.condition_expression_admission import VERIFIED, admit_atom_expression


def _find(result, clause_index):
    return next(
        item for item in result.get("rules", [])
        if isinstance(item, dict) and item.get("clause_index") == clause_index
    )


def _behavioral_equal(baseline_rule, candidate_rule):
    keys = (
        "applicability",
        "required_inputs",
        "blocked_by",
        "unknown_by",
        "numeric_effect",
        "current_numeric_effect",
    )
    return all(
        baseline_rule.get(key) == candidate_rule.get(key)
        for key in keys
    )


def main() -> int:
    original_load_json = pipeline.load_json
    baseline = pipeline.evaluate_site_rules(
        project_profile={},
        procedure_profile={},
    )
    original_snapshot = original_load_json(pipeline.SITE_COMPLETE_PATH)

    candidates = []
    rejected = []

    for rule in original_snapshot.get("rules", []):
        if not isinstance(rule, dict) or len(rule.get("conditions", [])) != 1:
            continue

        condition = rule["conditions"][0]
        expression = {
            "op": "ATOM",
            "condition": {
                "name": condition.get("name"),
                "type": condition.get("type"),
            },
        }
        admission = admit_atom_expression(rule, expression)
        if admission.verified:
            candidates.append(
                (rule.get("clause_index"), expression, admission)
            )
        else:
            rejected.append(rule.get("clause_index"))

    results = []

    for clause_index, expression, admission in candidates:
        candidate_snapshot = copy.deepcopy(original_snapshot)
        candidate_rule = _find(
            {"rules": candidate_snapshot["rules"]},
            clause_index,
        )
        candidate_rule["condition_expression"] = expression
        candidate_rule["condition_expression_status"] = VERIFIED

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

        baseline_rule = _find(baseline, clause_index)
        evaluated_rule = _find(candidate, clause_index)

        results.append({
            "clause_index": clause_index,
            "admission_verified": admission.verified,
            "behavioral_equal": _behavioral_equal(
                baseline_rule,
                evaluated_rule,
            ),
            "baseline_applicability": baseline_rule.get("applicability"),
            "candidate_applicability": evaluated_rule.get("applicability"),
            "baseline_reason": baseline_rule.get("applicability_reason"),
            "candidate_reason": evaluated_rule.get("applicability_reason"),
            "required_inputs_equal": (
                baseline_rule.get("required_inputs")
                == evaluated_rule.get("required_inputs")
            ),
            "blocked_by_equal": (
                baseline_rule.get("blocked_by")
                == evaluated_rule.get("blocked_by")
            ),
            "unknown_by_equal": (
                baseline_rule.get("unknown_by")
                == evaluated_rule.get("unknown_by")
            ),
            "numeric_effect_equal": (
                baseline_rule.get("numeric_effect")
                == evaluated_rule.get("numeric_effect")
            ),
            "current_numeric_effect_equal": (
                baseline_rule.get("current_numeric_effect")
                == evaluated_rule.get("current_numeric_effect")
            ),
        })

    passed = [item for item in results if item["behavioral_equal"]]
    failed = [item for item in results if not item["behavioral_equal"]]

    print("=== E-5 VERIFIED CANDIDATE BEHAVIORAL REGRESSION ===")
    print("RULE_COUNT =", len(original_snapshot.get("rules", [])))
    print("ADMITTED_CANDIDATE_COUNT =", len(candidates))
    print("ADMISSION_REJECTED_COUNT =", len(rejected))
    print("BEHAVIORAL_PASS_COUNT =", len(passed))
    print("BEHAVIORAL_FAIL_COUNT =", len(failed))
    print("REJECTED_CLAUSE_INDEXES =", rejected)

    if failed:
        print()
        print("=== BEHAVIORAL FAILURES ===")
        for item in failed:
            print(
                "INDEX=",
                item["clause_index"],
                "| BASELINE=",
                item["baseline_applicability"],
                "| CANDIDATE=",
                item["candidate_applicability"],
                "| REASON_DIFF=",
                item["baseline_reason"] != item["candidate_reason"],
                "| INPUTS=",
                item["required_inputs_equal"],
                "| BLOCKED=",
                item["blocked_by_equal"],
                "| UNKNOWN=",
                item["unknown_by_equal"],
                "| NUMERIC=",
                item["numeric_effect_equal"],
                "| CURRENT_NUMERIC=",
                item["current_numeric_effect_equal"],
            )

    validations = {
        "314 rules": len(original_snapshot.get("rules", [])) == 314,
        "83 admitted": len(candidates) == 83,
        "21 rejected": len(rejected) == 21,
        "all admitted behavior preserved": len(failed) == 0,
    }

    all_pass = all(validations.values())
    print()
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
