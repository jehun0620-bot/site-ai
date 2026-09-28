"""Fail-closed admission for verified E-5 ATOM expressions.

This module only admits a narrow, semantically transparent case:
one explicit non-derived rule condition mapped 1:1 to an ATOM expression.
It does not change rule applicability or grant runtime/production authority.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping


VERIFIED = "VERIFIED"
REVIEW_REQUIRED = "REVIEW_REQUIRED"
REJECTED = "REJECTED"
EXPRESSION_ADMISSION_PROOF_VERSION = "E5_ATOM_V1"

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
class ExpressionAdmissionResult:
    status: str
    expression_verified: bool
    identity_bound: bool
    single_condition_bound: bool
    source_bound: bool
    non_derived_bound: bool
    proof_fingerprint: str | None
    missing_gates: tuple[str, ...]

    @property
    def verified(self) -> bool:
        return (
            self.status == VERIFIED
            and self.expression_verified is True
            and self.identity_bound is True
            and self.single_condition_bound is True
            and self.source_bound is True
            and self.non_derived_bound is True
            and bool(self.proof_fingerprint)
        )


def expression_admission_proof_fingerprint(
    *,
    clause_index: Any,
    condition_name: str,
    condition_type: str,
    condition_state: str,
    expression: Mapping[str, Any],
) -> str:
    return _fingerprint(
        (
            EXPRESSION_ADMISSION_PROOF_VERSION,
            clause_index,
            condition_name,
            condition_type,
            condition_state,
            dict(expression),
        )
    )


def admit_atom_expression(
    rule: Mapping[str, Any] | None,
    expression: Mapping[str, Any] | None,
) -> ExpressionAdmissionResult:
    rule_map = rule if isinstance(rule, Mapping) else {}
    expression_map = expression if isinstance(expression, Mapping) else {}

    gates: list[tuple[str, bool]] = []

    expression_shape = (
        expression_map.get("op") == "ATOM"
        and isinstance(expression_map.get("condition"), Mapping)
    )
    gates.append(("atom_expression", expression_shape))

    condition = (
        expression_map.get("condition")
        if isinstance(expression_map.get("condition"), Mapping)
        else {}
    )
    name = _text(condition.get("name"))
    condition_type = _text(condition.get("type"))
    identity_present = bool(name and condition_type)
    gates.append(("expression_identity", identity_present))

    candidates = [
        item
        for item in rule_map.get("conditions", [])
        if isinstance(item, Mapping)
        and _text(item.get("name")) == name
        and _text(item.get("type")) == condition_type
    ]
    single_condition_bound = len(candidates) == 1
    gates.append(("single_condition_binding", single_condition_bound))

    bound = candidates[0] if single_condition_bound else {}
    state = _text(bound.get("state"))
    state_valid = state in _VALID_STATES
    gates.append(("condition_state_valid", state_valid))

    source_bound = bool(_text(bound.get("source")))
    gates.append(("condition_source_bound", source_bound))

    non_derived_bound = bound.get("derived") is False
    gates.append(("condition_non_derived", non_derived_bound))

    passed = all(value for _, value in gates)

    missing = tuple(name for name, value in gates if not value)

    proof = (
        expression_admission_proof_fingerprint(
            clause_index=rule_map.get("clause_index"),
            condition_name=name,
            condition_type=condition_type,
            condition_state=state,
            expression=expression_map,
        )
        if passed
        else None
    )

    return ExpressionAdmissionResult(
        status=VERIFIED if passed else REJECTED,
        expression_verified=passed,
        identity_bound=identity_present,
        single_condition_bound=single_condition_bound,
        source_bound=source_bound,
        non_derived_bound=non_derived_bound,
        proof_fingerprint=proof,
        missing_gates=missing,
    )
