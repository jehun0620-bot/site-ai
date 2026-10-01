# -*- coding: utf-8 -*-

"""Fail-closed admission for the verified Rule 125 performance-hall expression.

This module admits only the already-tested performance-hall branch:

SITE 자연경관지구
AND canonical BUILDING_USE 공연장
AND applicable_use_floor_area > 1000 square_meter

It does not admit 집회장, 관람장, or full Rule 125 automation.
It does not write production data or grant runtime authority by itself.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


VERIFIED = "VERIFIED"
REJECTED = "REJECTED"
PROOF_VERSION = "RULE125_PERFORMANCE_HALL_V1"
FULL_EXPRESSION_PROOF_VERSION = "RULE125_FULL_USE_SET_CANDIDATE_V1"
FULL_BUILDING_USE_VALUES = ("공연장", "집회장", "관람장")

RULE_INDEX = 125
SITE_TYPE = "SITE"
SITE_NAME = "자연경관지구"
BUILDING_USE_IDENTITY = "canonical"
BUILDING_USE_VALUE = "공연장"
NUMERIC_TARGET = "applicable_use_floor_area"
NUMERIC_OPERATOR = "GT"
NUMERIC_VALUE = 1000
NUMERIC_UNIT = "square_meter"

_VALID_STATES = {"TRUE", "FALSE", "UNKNOWN", "UNSET"}


def _text(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _fingerprint(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class Rule125ExpressionAdmissionResult:
    status: str
    expression_verified: bool
    rule_bound: bool
    site_bound: bool
    building_use_bound: bool
    numeric_bound: bool
    source_bound: bool
    non_derived_bound: bool
    proof_fingerprint: str | None
    missing_gates: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.expression_verified is True
            and self.rule_bound is True
            and self.site_bound is True
            and self.building_use_bound is True
            and self.numeric_bound is True
            and self.source_bound is True
            and self.non_derived_bound is True
            and bool(self.proof_fingerprint)
        )


def rule125_expression_admission_proof_fingerprint(
    *,
    rule: Mapping[str, Any],
    expression: Mapping[str, Any],
) -> str:
    return _fingerprint(
        (
            PROOF_VERSION,
            rule.get("clause_index"),
            dict(expression),
        )
    )


def admit_rule125_performance_hall_expression(
    rule: Mapping[str, Any] | None,
    expression: Mapping[str, Any] | None,
) -> Rule125ExpressionAdmissionResult:
    rule_map = rule if isinstance(rule, Mapping) else {}
    expression_map = expression if isinstance(expression, Mapping) else {}

    gates: list[tuple[str, bool]] = []

    rule_bound = rule_map.get("clause_index") == RULE_INDEX
    gates.append(("rule_125_binding", rule_bound))

    conditions = [
        item
        for item in rule_map.get("conditions", [])
        if isinstance(item, Mapping)
        and _text(item.get("type")) == SITE_TYPE
        and _text(item.get("name")) == SITE_NAME
    ]
    single_site_condition = len(conditions) == 1
    gates.append(("single_natural_landscape_condition", single_site_condition))

    site_condition = conditions[0] if single_site_condition else {}
    site_state_valid = _text(site_condition.get("state")) in _VALID_STATES
    gates.append(("site_condition_state_valid", site_state_valid))

    source_bound = bool(_text(site_condition.get("source")))
    gates.append(("site_condition_source_bound", source_bound))

    non_derived_bound = site_condition.get("derived") is False
    gates.append(("site_condition_non_derived", non_derived_bound))

    children = expression_map.get("children")
    expression_and = (
        expression_map.get("op") == "AND"
        and isinstance(children, list)
        and len(children) == 3
    )
    gates.append(("three_child_and_expression", expression_and))

    child_list = children if isinstance(children, list) else []

    expected_site = {
        "op": "ATOM",
        "condition": {
            "type": SITE_TYPE,
            "name": SITE_NAME,
        },
    }
    expected_building_use = {
        "op": "BUILDING_USE",
        "identity": BUILDING_USE_IDENTITY,
        "value": BUILDING_USE_VALUE,
    }
    expected_numeric = {
        "op": "NUMERIC",
        "target": NUMERIC_TARGET,
        "operator": NUMERIC_OPERATOR,
        "value": NUMERIC_VALUE,
        "unit": NUMERIC_UNIT,
    }

    site_bound = (
        len(child_list) == 3
        and child_list[0] == expected_site
    )
    gates.append(("site_expression_binding", site_bound))

    building_use_bound = (
        len(child_list) == 3
        and child_list[1] == expected_building_use
    )
    gates.append(("performance_hall_binding", building_use_bound))

    numeric_bound = (
        len(child_list) == 3
        and child_list[2] == expected_numeric
    )
    gates.append(("applicable_use_floor_area_binding", numeric_bound))

    passed = all(value for _, value in gates)
    missing = tuple(name for name, value in gates if not value)

    proof = (
        rule125_expression_admission_proof_fingerprint(
            rule=rule_map,
            expression=expression_map,
        )
        if passed
        else None
    )

    return Rule125ExpressionAdmissionResult(
        status=VERIFIED if passed else REJECTED,
        expression_verified=passed,
        rule_bound=rule_bound,
        site_bound=site_bound,
        building_use_bound=building_use_bound,
        numeric_bound=numeric_bound,
        source_bound=source_bound,
        non_derived_bound=non_derived_bound,
        proof_fingerprint=proof,
        missing_gates=missing,
    )


def rule125_full_expression_candidate_proof_fingerprint(
    *,
    rule: Mapping[str, Any],
    expression: Mapping[str, Any],
) -> str:
    """Fingerprint the exact full-use-set candidate shape only."""
    return _fingerprint(
        (
            FULL_EXPRESSION_PROOF_VERSION,
            rule.get("clause_index"),
            dict(expression),
        )
    )


def admit_rule125_full_expression_candidate(
    rule: Mapping[str, Any] | None,
    expression: Mapping[str, Any] | None,
) -> Rule125ExpressionAdmissionResult:
    """Admit only the exact memory-only full Rule 125 candidate expression.

    This is a candidate proof boundary, not production authority.
    """
    rule_map = rule if isinstance(rule, Mapping) else {}
    expression_map = expression if isinstance(expression, Mapping) else {}
    gates: list[tuple[str, bool]] = []

    rule_bound = rule_map.get("clause_index") == RULE_INDEX
    gates.append(("rule_125_binding", rule_bound))

    conditions = [
        item
        for item in rule_map.get("conditions", [])
        if isinstance(item, Mapping)
        and _text(item.get("type")) == SITE_TYPE
        and _text(item.get("name")) == SITE_NAME
    ]
    single_site_condition = len(conditions) == 1
    gates.append(("single_natural_landscape_condition", single_site_condition))
    site_condition = conditions[0] if single_site_condition else {}

    site_state_valid = _text(site_condition.get("state")) in _VALID_STATES
    gates.append(("site_condition_state_valid", site_state_valid))
    source_bound = bool(_text(site_condition.get("source")))
    gates.append(("site_condition_source_bound", source_bound))
    non_derived_bound = site_condition.get("derived") is False
    gates.append(("site_condition_non_derived", non_derived_bound))

    children = expression_map.get("children")
    expression_and = (
        expression_map.get("op") == "AND"
        and isinstance(children, list)
        and len(children) == 3
    )
    gates.append(("three_child_and_expression", expression_and))
    child_list = children if isinstance(children, list) else []

    expected_site = {
        "op": "ATOM",
        "condition": {"type": SITE_TYPE, "name": SITE_NAME},
    }
    site_bound = len(child_list) == 3 and child_list[0] == expected_site
    gates.append(("site_expression_binding", site_bound))

    expected_use_children = [
        {
            "op": "BUILDING_USE",
            "identity": BUILDING_USE_IDENTITY,
            "value": value,
        }
        for value in FULL_BUILDING_USE_VALUES
    ]
    expected_use_or = {"op": "OR", "children": expected_use_children}
    building_use_bound = (
        len(child_list) == 3
        and child_list[1] == expected_use_or
    )
    gates.append(("full_building_use_set_binding", building_use_bound))

    expected_numeric = {
        "op": "NUMERIC",
        "target": NUMERIC_TARGET,
        "operator": NUMERIC_OPERATOR,
        "value": NUMERIC_VALUE,
        "unit": NUMERIC_UNIT,
    }
    numeric_bound = (
        len(child_list) == 3
        and child_list[2] == expected_numeric
    )
    gates.append(("applicable_use_floor_area_binding", numeric_bound))

    passed = all(value for _, value in gates)
    missing = tuple(name for name, value in gates if not value)
    proof = (
        rule125_full_expression_candidate_proof_fingerprint(
            rule=rule_map,
            expression=expression_map,
        )
        if passed
        else None
    )

    return Rule125ExpressionAdmissionResult(
        status=VERIFIED if passed else REJECTED,
        expression_verified=passed,
        rule_bound=rule_bound,
        site_bound=site_bound,
        building_use_bound=building_use_bound,
        numeric_bound=numeric_bound,
        source_bound=source_bound,
        non_derived_bound=non_derived_bound,
        proof_fingerprint=proof,
        missing_gates=missing,
    )
