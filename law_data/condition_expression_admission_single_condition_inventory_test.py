from __future__ import annotations

from collections import Counter

from law_data.rule_evaluation_pipeline import (
    SITE_COMPLETE_PATH,
    load_json,
)
from law_data.condition_expression_admission import admit_atom_expression


def main() -> int:
    snapshot = load_json(SITE_COMPLETE_PATH)
    rules = snapshot.get("rules", [])

    single = [
        rule for rule in rules
        if isinstance(rule, dict)
        and len(rule.get("conditions", [])) == 1
    ]

    results = []
    for rule in single:
        condition = rule["conditions"][0]
        expression = {
            "op": "ATOM",
            "condition": {
                "name": condition.get("name"),
                "type": condition.get("type"),
            },
        }
        admission = admit_atom_expression(rule, expression)
        results.append((rule, condition, admission))

    status_counts = Counter(item[2].status for item in results)
    type_counts = Counter(
        str(item[1].get("type"))
        for item in results
    )
    rejected_gates = Counter(
        gate
        for _, _, result in results
        for gate in result.missing_gates
    )

    verified = [
        (rule, condition, admission)
        for rule, condition, admission in results
        if admission.verified
    ]

    print("=== E-5 SINGLE-CONDITION ADMISSION INVENTORY ===")
    print("RULE_COUNT =", len(rules))
    print("SINGLE_CONDITION_COUNT =", len(single))
    print("ADMISSION_STATUS_COUNTS =", dict(status_counts))
    print("CONDITION_TYPE_COUNTS =", dict(type_counts))
    print("REJECTED_GATE_COUNTS =", dict(rejected_gates))
    print("VERIFIED_CANDIDATE_COUNT =", len(verified))

    print()
    print("=== VERIFIED CANDIDATE SAMPLE (MAX 20) ===")
    for rule, condition, admission in verified[:20]:
        print(
            "INDEX=",
            rule.get("clause_index"),
            "| TYPE=",
            condition.get("type"),
            "| NAME=",
            condition.get("name"),
            "| STATE=",
            condition.get("state"),
            "| SOURCE=",
            condition.get("source"),
            "| PROOF=",
            bool(admission.proof_fingerprint),
        )

    # This is an inventory only. It intentionally does not write,
    # mutate, or register any production expression.
    validations = {
        "rule count 314": len(rules) == 314,
        "single condition count 104": len(single) == 104,
        "verified candidates have proof": all(
            bool(result.proof_fingerprint)
            for _, _, result in verified
        ),
        "verified candidates are single": all(
            len(rule.get("conditions", [])) == 1
            for rule, _, _ in verified
        ),
    }

    all_pass = all(validations.values())

    print()
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
