# -*- coding: utf-8 -*-

"""
Building Use Rule 125 production hierarchy regression.

Read-only test:
- inspect the real 314-rule production snapshot;
- confirm Rule 123 / Rule 125 hierarchy facts;
- report existing expression attachment;
- do not modify production data or decide integration policy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent.parent
PRODUCTION_RULE_PATH = (
    BASE_DIR / "law_data" / "output" / "site_rule_evaluation_site_complete.json"
)
SOURCE_CLAUSE_PATH = (
    BASE_DIR / "law_data" / "output" / "law_special_rule_clauses.json"
)

EXPECTED_RULE_COUNT = 314
PARENT_INDEX = 123
TARGET_INDEX = 125
EXPECTED_TITLE = "자연경관지구 안에서의 건축제한"


def safe_string(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"입력 파일 없음: {path}")
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def find_by_clause_index(
    items: List[Dict[str, Any]],
    clause_index: int,
) -> Dict[str, Any]:
    matches = []
    for position, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            continue
        actual_index = item.get("clause_index", position)
        if int(actual_index) == clause_index:
            matches.append(item)

    if len(matches) != 1:
        raise AssertionError(
            f"clause_index {clause_index} 항목 수: {len(matches)}"
        )
    return matches[0]


def source_path(item: Dict[str, Any]) -> tuple[str, str, str]:
    return (
        safe_string(item.get("paragraph")),
        safe_string(item.get("item")),
        safe_string(item.get("subitem")),
    )


def expression_summary(rule: Dict[str, Any]) -> Dict[str, Any]:
    expression = rule.get("condition_expression")
    return {
        "status": safe_string(rule.get("condition_expression_status")),
        "present": isinstance(expression, dict),
        "op": (
            safe_string(expression.get("op"))
            if isinstance(expression, dict)
            else ""
        ),
    }


def main() -> int:
    production = load_json(PRODUCTION_RULE_PATH)
    source = load_json(SOURCE_CLAUSE_PATH)

    rules = [
        item
        for item in production.get("rules", [])
        if isinstance(item, dict)
    ]
    clauses = [
        item
        for item in source.get("clauses", [])
        if isinstance(item, dict)
    ]

    assert len(rules) == EXPECTED_RULE_COUNT, len(rules)
    assert len(clauses) == EXPECTED_RULE_COUNT, len(clauses)

    parent_rule = find_by_clause_index(rules, PARENT_INDEX)
    target_rule = find_by_clause_index(rules, TARGET_INDEX)
    parent_source = find_by_clause_index(clauses, PARENT_INDEX)
    target_source = find_by_clause_index(clauses, TARGET_INDEX)

    assert safe_string(parent_rule.get("rule_title")) == EXPECTED_TITLE
    assert safe_string(target_rule.get("rule_title")) == EXPECTED_TITLE
    assert safe_string(parent_source.get("rule_title")) == EXPECTED_TITLE
    assert safe_string(target_source.get("rule_title")) == EXPECTED_TITLE

    assert source_path(parent_source) == ("①", "", "")
    assert source_path(target_source) == ("①", "2", "")

    assert safe_string(parent_source.get("structural_role")) == "CONTAINER"
    assert safe_string(target_source.get("structural_role")) == "LEAF"

    target_text = safe_string(target_source.get("text"))
    for required_text in (
        "공연장",
        "집회장",
        "관람장",
        "1천제곱미터",
        "초과",
    ):
        assert required_text in target_text, required_text

    parent_expression = expression_summary(parent_rule)
    target_expression = expression_summary(target_rule)

    print("=" * 60)
    print("BUILDING USE RULE 125 PRODUCTION HIERARCHY")
    print("=" * 60)
    print(f"Production rule count: {len(rules)}")
    print(f"Source clause count: {len(clauses)}")
    print()
    print("PARENT")
    print(f"  clause_index: {PARENT_INDEX}")
    print(f"  role: {safe_string(parent_source.get('structural_role'))}")
    print(f"  path: {source_path(parent_source)}")
    print(f"  expression: {parent_expression}")
    print()
    print("TARGET")
    print(f"  clause_index: {TARGET_INDEX}")
    print(f"  role: {safe_string(target_source.get('structural_role'))}")
    print(f"  path: {source_path(target_source)}")
    print(f"  expression: {target_expression}")
    print(f"  text: {target_text}")
    print()
    print("CONFIRMED")
    print("  - Rule 123 and Rule 125 are separate production entries.")
    print("  - Rule 123 source role is CONTAINER.")
    print("  - Rule 125 source role is LEAF.")
    print("  - Rule 125 is paragraph ① item 2.")
    print("  - Rule 125 text contains 공연장/집회장/관람장.")
    print("  - Rule 125 text contains the 1천제곱미터 초과 condition.")
    print()
    print("NOT DECIDED BY THIS TEST")
    print("  - Whether Rule 123 should be suppressed or retained.")
    print("  - Whether Rule 125 should receive a production expression now.")
    print("  - How sibling clauses should be integrated.")
    print()
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
