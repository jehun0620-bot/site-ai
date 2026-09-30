# -*- coding: utf-8 -*-

"""Contract regression for Rule 125 performance-hall expression admission."""

from __future__ import annotations

from copy import deepcopy

from law_data.building_use_rule125_expression_admission import (
    REJECTED,
    VERIFIED,
    admit_rule125_performance_hall_expression,
    rule125_expression_admission_proof_fingerprint,
)


def rule() -> dict:
    return {
        "clause_index": 125,
        "conditions": [
            {
                "type": "SITE",
                "name": "자연경관지구",
                "state": "TRUE",
                "confidence": "HIGH",
                "source": "SITE_CONDITION_SNAPSHOT",
                "derived": False,
            }
        ],
    }


def expression() -> dict:
    return {
        "op": "AND",
        "children": [
            {
                "op": "ATOM",
                "condition": {
                    "type": "SITE",
                    "name": "자연경관지구",
                },
            },
            {
                "op": "BUILDING_USE",
                "identity": "canonical",
                "value": "공연장",
            },
            {
                "op": "NUMERIC",
                "target": "applicable_use_floor_area",
                "operator": "GT",
                "value": 1000,
                "unit": "square_meter",
            },
        ],
    }


def rejected(
    candidate_rule: dict,
    candidate_expression: dict,
) -> bool:
    result = admit_rule125_performance_hall_expression(
        candidate_rule,
        candidate_expression,
    )
    return (
        result.status == REJECTED
        and not result.verified
        and result.proof_fingerprint is None
        and bool(result.missing_gates)
    )


def main() -> int:
    base_rule = rule()
    base_expression = expression()

    admitted = admit_rule125_performance_hall_expression(
        base_rule,
        base_expression,
    )

    validations = {
        "exact expression verified": admitted.verified,
        "verified status": admitted.status == VERIFIED,
        "no missing gates": admitted.missing_gates == (),
        "proof fingerprint": (
            admitted.proof_fingerprint
            == rule125_expression_admission_proof_fingerprint(
                rule=base_rule,
                expression=base_expression,
            )
        ),
    }

    wrong_rule = rule()
    wrong_rule["clause_index"] = 126
    validations["wrong rule rejected"] = rejected(
        wrong_rule,
        expression(),
    )

    wrong_op = expression()
    wrong_op["op"] = "OR"
    validations["OR rejected"] = rejected(rule(), wrong_op)

    wrong_site = expression()
    wrong_site["children"][0]["condition"]["name"] = "경관지구"
    validations["wrong SITE rejected"] = rejected(rule(), wrong_site)

    wrong_identity = expression()
    wrong_identity["children"][1]["identity"] = "major"
    validations["non-canonical identity rejected"] = rejected(
        rule(),
        wrong_identity,
    )

    office = expression()
    office["children"][1]["value"] = "사무소"
    validations["office rejected"] = rejected(rule(), office)

    assembly = expression()
    assembly["children"][1]["value"] = "집회장"
    validations["assembly hall rejected"] = rejected(rule(), assembly)

    spectator = expression()
    spectator["children"][1]["value"] = "관람장"
    validations["spectator facility rejected"] = rejected(
        rule(),
        spectator,
    )

    wrong_target = expression()
    wrong_target["children"][2]["target"] = "total_floor_area"
    validations["total floor area rejected"] = rejected(
        rule(),
        wrong_target,
    )

    wrong_operator = expression()
    wrong_operator["children"][2]["operator"] = "GTE"
    validations["GTE rejected"] = rejected(rule(), wrong_operator)

    wrong_value = expression()
    wrong_value["children"][2]["value"] = 999
    validations["999 threshold rejected"] = rejected(rule(), wrong_value)

    wrong_unit = expression()
    wrong_unit["children"][2]["unit"] = "square_feet"
    validations["wrong unit rejected"] = rejected(rule(), wrong_unit)

    extra_child = expression()
    extra_child["children"].append(
        {
            "op": "ATOM",
            "condition": {
                "type": "PROCEDURE",
                "name": "도시계획위원회심의",
            },
        }
    )
    validations["extra child rejected"] = rejected(rule(), extra_child)

    duplicate_site_rule = rule()
    duplicate_site_rule["conditions"].append(
        deepcopy(duplicate_site_rule["conditions"][0])
    )
    validations["duplicate SITE condition rejected"] = rejected(
        duplicate_site_rule,
        expression(),
    )

    derived_rule = rule()
    derived_rule["conditions"][0]["derived"] = True
    validations["derived SITE condition rejected"] = rejected(
        derived_rule,
        expression(),
    )

    no_source_rule = rule()
    no_source_rule["conditions"][0]["source"] = ""
    validations["missing SITE source rejected"] = rejected(
        no_source_rule,
        expression(),
    )

    invalid_state_rule = rule()
    invalid_state_rule["conditions"][0]["state"] = "MAYBE"
    validations["invalid SITE state rejected"] = rejected(
        invalid_state_rule,
        expression(),
    )

    print("=" * 70)
    print("RULE 125 PERFORMANCE-HALL EXPRESSION ADMISSION")
    print("=" * 70)

    for name, passed in validations.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    all_pass = all(validations.values())
    print()
    print("RESULT:", "PASS" if all_pass else "FAIL")
    print(
        "Scope: Rule 125 공연장 branch only; "
        "집회장/관람장 and full Rule 125 remain unverified."
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
