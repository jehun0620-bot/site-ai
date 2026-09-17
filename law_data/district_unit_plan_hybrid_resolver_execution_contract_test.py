from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_hybrid_resolver_execution import (
    execute_district_unit_plan_hybrid_resolver,
)


PNU = "1168010600100010000"


def _admission() -> dict:
    return {
        "resolver_input_admitted": True,
        "condition_name": "지구단위계획",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "canonical_pnu": PNU,
        "hybrid_binding": {
            "hybrid_gate_binding_verified": True,
            "condition_name": "지구단위계획",
            "canonical_pnu": PNU,
            "binding_scope": {
                "designation_to_current_validity": True,
                "spatial_to_canonical_pnu": True,
                "designation_to_spatial_notice_identity": True,
            },
        },
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }


def _execute(admission=None, pnu=PNU) -> dict:
    return execute_district_unit_plan_hybrid_resolver(
        _admission() if admission is None else admission,
        canonical_pnu=pnu,
    )


def main() -> None:
    executed = _execute()
    assert executed["resolver_execution_verified"] is True
    assert executed["resolution"] == "UNKNOWN"
    assert executed["resolution_type"] == "HYBRID_SPATIAL_NOTICE"
    assert executed["canonical_pnu"] == PNU
    assert executed["parcel_applicability_verified"] is False

    for key in (
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert executed[key] is False

    not_admitted = _admission()
    not_admitted["resolver_input_admitted"] = False
    assert _execute(not_admitted)["resolver_execution_verified"] is False

    wrong_condition = _admission()
    wrong_condition["condition_name"] = "개발밀도관리구역"
    assert _execute(wrong_condition)["resolver_execution_verified"] is False

    wrong_type = _admission()
    wrong_type["resolution_type"] = "STANDARD_CODE"
    assert _execute(wrong_type)["resolver_execution_verified"] is False

    wrong_pnu = _admission()
    wrong_pnu["canonical_pnu"] = "1168010600100020000"
    assert _execute(wrong_pnu)["resolver_execution_verified"] is False

    missing_binding = _admission()
    missing_binding["hybrid_binding"] = {}
    assert _execute(missing_binding)["resolver_execution_verified"] is False

    unverified_binding = _admission()
    unverified_binding["hybrid_binding"]["hybrid_gate_binding_verified"] = False
    assert _execute(unverified_binding)["resolver_execution_verified"] is False

    wrong_binding_pnu = _admission()
    wrong_binding_pnu["hybrid_binding"]["canonical_pnu"] = "1168010600100020000"
    assert _execute(wrong_binding_pnu)["resolver_execution_verified"] is False

    forged_authority = _admission()
    forged_authority["runtime_registration_allowed"] = True
    forged_authority["production_registration_allowed"] = True
    forged_authority["site_truth_decision_allowed"] = True
    forged_authority["site_promotion_allowed"] = True
    bounded = _execute(forged_authority)
    assert bounded["resolver_execution_verified"] is True
    assert bounded["resolution"] == "UNKNOWN"
    assert bounded["parcel_applicability_verified"] is False
    assert bounded["runtime_registration_allowed"] is False
    assert bounded["production_registration_allowed"] is False
    assert bounded["site_truth_decision_allowed"] is False
    assert bounded["site_promotion_allowed"] is False

    malformed = execute_district_unit_plan_hybrid_resolver(None, canonical_pnu="")
    assert malformed["resolver_execution_verified"] is False
    assert malformed["resolver_admission"] == {}
    assert malformed["resolution"] == "UNKNOWN"

    print("DISTRICT_UNIT_PLAN_HYBRID_RESOLVER_EXECUTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
