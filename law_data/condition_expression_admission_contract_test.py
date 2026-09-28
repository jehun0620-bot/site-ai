from __future__ import annotations

from dataclasses import replace

from .condition_expression_admission import (
    VERIFIED,
    admit_atom_expression,
    expression_admission_proof_fingerprint,
)


def _rule() -> dict:
    return {
        "clause_index": 3,
        "conditions": [
            {
                "name": "지구단위계획",
                "type": "SITE",
                "state": "TRUE",
                "confidence": "HIGH",
                "source": "SITE_CONDITION_SNAPSHOT",
                "derived": False,
                "derived_from": None,
            }
        ],
    }


def _expression() -> dict:
    return {
        "op": "ATOM",
        "condition": {
            "name": "지구단위계획",
            "type": "SITE",
        },
    }


def main() -> None:
    result = admit_atom_expression(_rule(), _expression())

    assert result.verified
    assert result.status == VERIFIED
    assert result.missing_gates == ()
    assert result.proof_fingerprint == expression_admission_proof_fingerprint(
        clause_index=3,
        condition_name="지구단위계획",
        condition_type="SITE",
        condition_state="TRUE",
        expression=_expression(),
    )

    wrong_name = _expression()
    wrong_name["condition"]["name"] = "개발밀도관리구역"
    assert not admit_atom_expression(_rule(), wrong_name).verified

    duplicate = _rule()
    duplicate["conditions"].append(dict(duplicate["conditions"][0]))
    assert not admit_atom_expression(duplicate, _expression()).verified

    derived = _rule()
    derived["conditions"][0]["derived"] = True
    assert not admit_atom_expression(derived, _expression()).verified

    no_source = _rule()
    no_source["conditions"][0]["source"] = ""
    assert not admit_atom_expression(no_source, _expression()).verified

    invalid_state = _rule()
    invalid_state["conditions"][0]["state"] = "MAYBE"
    assert not admit_atom_expression(invalid_state, _expression()).verified

    wrong_op = {"op": "NUMERIC", "condition": _expression()["condition"]}
    assert not admit_atom_expression(_rule(), wrong_op).verified

    print("E5_ATOM_EXPRESSION_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
