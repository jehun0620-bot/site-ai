from __future__ import annotations

from law_data.condition_expression_admission import (
    VERIFIED,
    admit_atom_expression,
)
from law_data.rule_evaluation_pipeline import (
    SITE_COMPLETE_PATH,
    load_json,
)


def main() -> int:
    snapshot = load_json(SITE_COMPLETE_PATH)
    rules = snapshot.get("rules", [])

    rule = next(
        (
            item for item in rules
            if isinstance(item, dict)
            and item.get("clause_index") == 3
        ),
        None,
    )

    if not isinstance(rule, dict):
        print("INDEX_3_FOUND = False")
        return 1

    print("INDEX_3_FOUND = True")
    print("EXISTING_EXPRESSION =", bool(rule.get("condition_expression")))
    print(
        "EXISTING_EXPRESSION_STATUS =",
        rule.get("condition_expression_status"),
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

    print("ADMISSION_STATUS =", admission.status)
    print("ADMISSION_VERIFIED =", admission.verified)
    print("MISSING_GATES =", admission.missing_gates)

    validations = {
        "rule found": True,
        "no existing expression": not bool(
            rule.get("condition_expression")
        ),
        "no existing status": not bool(
            rule.get("condition_expression_status")
        ),
        "condition count is one": (
            len(rule.get("conditions", [])) == 1
        ),
        "candidate admission verified": (
            admission.status == VERIFIED
            and admission.verified
        ),
    }

    all_pass = all(validations.values())

    print("all_pass:", all_pass)

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
