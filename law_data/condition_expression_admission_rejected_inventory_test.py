from __future__ import annotations

from law_data.rule_evaluation_pipeline import SITE_COMPLETE_PATH, load_json
from law_data.condition_expression_admission import admit_atom_expression


REJECTED_INDEXES = {
    20, 49, 50, 150, 151, 152, 154, 156, 157, 158, 159,
    160, 161, 162, 163, 164, 165, 166, 188, 272, 314,
}


def main() -> int:
    snapshot = load_json(SITE_COMPLETE_PATH)
    rules = snapshot.get("rules", [])

    print("=== E-5 REJECTED 21 INVENTORY ===")
    found = 0

    for rule in rules:
        if not isinstance(rule, dict) or rule.get("clause_index") not in REJECTED_INDEXES:
            continue
        conditions = rule.get("conditions", [])
        if len(conditions) != 1:
            print("INDEX=", rule.get("clause_index"), "| CONDITION_COUNT=", len(conditions))
            continue

        condition = conditions[0]
        expression = {
            "op": "ATOM",
            "condition": {
                "name": condition.get("name"),
                "type": condition.get("type"),
            },
        }
        admission = admit_atom_expression(rule, expression)
        print(
            "INDEX=", rule.get("clause_index"),
            "| TYPE=", condition.get("type"),
            "| NAME=", condition.get("name"),
            "| STATE=", condition.get("state"),
            "| SOURCE=", condition.get("source"),
            "| DERIVED=", condition.get("derived"),
            "| DERIVED_FROM=", condition.get("derived_from"),
            "| STATUS=", admission.status,
            "| MISSING=", admission.missing_gates,
        )
        found += 1

    all_pass = found == len(REJECTED_INDEXES)
    print("FOUND_REJECTED_COUNT =", found)
    print("EXPECTED_REJECTED_COUNT =", len(REJECTED_INDEXES))
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
