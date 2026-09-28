from __future__ import annotations

import re
from collections import Counter

from law_data import rule_evaluation_pipeline as pipeline
from law_data.condition_expression_admission import admit_atom_expression


REVIEW_REQUIRED = "REVIEW_REQUIRED"
COMPLETE_CANDIDATE = "COMPLETE_CANDIDATE"


OWN_BOOLEAN_PATTERNS = (
    r"다음\s*각\s*(?:호|목)",
    r"어느\s*하나에\s*해당",
    r"모두\s*(?:갖춘|충족)",
    r"각\s*(?:호|목)의\s*(?:어느\s*)?하나",
)
OWN_EXTRA_PREDICATE_PATTERNS = (
    r"\d+\s*년(?:이|을)?\s*경과",
    r"필요한\s*경우",
    r"인정하는\s*경우",
    r"제공하는\s*경우",
    r"설치하여\s*기부하는\s*경우",
    r"변경(?:되는|하는)\s*경우",
    r"미달하는\s*지역",
    r"초과할\s*것으로\s*예상",
)
CROSS_RULE_PATTERNS = (
    r"제\s*\d+\s*항에\s*따라\s*산정",
    r"제\s*\d+\s*항에\s*따라\s*적용",
    r"제\s*\d+\s*항의\s*규정에\s*따라",
    r"제\s*\d+\s*항\s*및\s*제\s*\d+\s*항",
    r"제\s*\d+조(?:제\s*\d+항)?\s*규정에\s*따른\s*용적률",
    r"제\s*\d+조(?:제\s*\d+항)?에\s*따른\s*용적률",
)
CALCULATION_PATTERNS = (
    r"\([^)]*[+\-*/×][^)]*\)",
    r"\d+(?:\.\d+)?\s*α",
    r"산출되는\s*비율",
    r"연면적의\s*\d+배",
    r"용적률의\s*\d+퍼센트",
    r"\d+퍼센트\s*이하의\s*범위",
)
INHERITED_BOOLEAN_PATTERNS = (
    r"다음\s*각\s*(?:호|목)",
    r"어느\s*하나에\s*해당",
)


def _matches(text, patterns):
    return any(re.search(pattern, text) for pattern in patterns)


def _single_condition_candidates(rules):
    rows = []
    for rule in rules:
        conditions = rule.get("conditions")
        if not isinstance(conditions, list) or len(conditions) != 1:
            continue
        condition = conditions[0]
        if not isinstance(condition, dict):
            continue

        expression = {
            "op": "ATOM",
            "condition": {
                "name": condition.get("name"),
                "type": condition.get("type"),
            },
        }
        admission = admit_atom_expression(rule, expression)
        if admission.verified:
            rows.append(rule)
    return rows


def _review(rule):
    own_text = str(rule.get("text") or "")
    inherited = str(rule.get("inherited_context") or "")

    signals = {
        "own_boolean": _matches(own_text, OWN_BOOLEAN_PATTERNS),
        "own_extra_predicate": _matches(own_text, OWN_EXTRA_PREDICATE_PATTERNS),
        "cross_rule": _matches(own_text, CROSS_RULE_PATTERNS),
        "calculation": _matches(own_text, CALCULATION_PATTERNS),
        "inherited_boolean": _matches(inherited, INHERITED_BOOLEAN_PATTERNS),
    }

    # Inherited boolean wording alone is not enough to reject a child clause.
    # It is retained as review metadata, while own-text complexity is fail-closed.
    hard_review = any(
        signals[key]
        for key in (
            "own_boolean",
            "own_extra_predicate",
            "cross_rule",
            "calculation",
        )
    )

    status = REVIEW_REQUIRED if hard_review else COMPLETE_CANDIDATE
    return status, signals


def main():
    payload = pipeline.load_json(pipeline.SITE_COMPLETE_PATH)
    rules = payload.get("rules", [])
    candidates = _single_condition_candidates(rules)

    rows = []
    for rule in candidates:
        status, signals = _review(rule)
        condition = rule["conditions"][0]
        rows.append(
            {
                "clause_index": rule.get("clause_index"),
                "condition": condition.get("name"),
                "paragraph": rule.get("paragraph"),
                "item": rule.get("item"),
                "subitem": rule.get("subitem"),
                "status": status,
                "signals": tuple(
                    key for key, value in signals.items() if value
                ),
            }
        )

    status_counts = Counter(row["status"] for row in rows)
    signal_counts = Counter(
        signal
        for row in rows
        for signal in row["signals"]
    )

    print("=== E-5 ATOM PREDICATE COMPLETENESS INVENTORY ===")
    print("ADMITTED_CANDIDATE_COUNT =", len(candidates))
    print("STATUS_COUNTS =", dict(status_counts))
    print("SIGNAL_COUNTS =", dict(signal_counts))

    review_rows = [
        row for row in rows if row["status"] == REVIEW_REQUIRED
    ]
    print("REVIEW_REQUIRED_INDEXES =", [
        row["clause_index"] for row in review_rows
    ])

    print()
    print("=== REVIEW REQUIRED DETAILS ===")
    for row in review_rows:
        print(
            "INDEX=",
            row["clause_index"],
            "| CONDITION=",
            row["condition"],
            "| STRUCTURE=",
            (row["paragraph"], row["item"], row["subitem"]),
            "| SIGNALS=",
            row["signals"],
        )

    validations = {
        "candidate count": len(candidates) == 83,
        "partition": sum(status_counts.values()) == len(candidates),
        "known statuses": set(status_counts).issubset(
            {COMPLETE_CANDIDATE, REVIEW_REQUIRED}
        ),
    }
    all_pass = all(validations.values())
    print()
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
