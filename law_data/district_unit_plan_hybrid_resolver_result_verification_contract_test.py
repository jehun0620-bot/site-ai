from __future__ import annotations

from .district_unit_plan_hybrid_resolver_result_verification import (
    verify_district_unit_plan_hybrid_resolver_result,
)


PNU = "1168010600100010000"


def _execution() -> dict:
    return {
        "resolver_execution_verified": True,
        "condition_name": "지구단위계획",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "resolution": "UNKNOWN",
        "canonical_pnu": PNU,
        "resolver_admission": {
            "resolver_input_admitted": True,
            "condition_name": "지구단위계획",
            "resolution_type": "HYBRID_SPATIAL_NOTICE",
            "canonical_pnu": PNU,
        },
        "parcel_applicability_verified": False,
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }


def _verify(execution=None, pnu=PNU) -> dict:
    return verify_district_unit_plan_hybrid_resolver_result(
        _execution() if execution is None else execution,
        canonical_pnu=pnu,
    )


def main() -> None:
    verified = _verify()
    assert verified["resolver_result_verified"] is True
    assert verified["resolution"] == "UNKNOWN"
    assert verified["parcel_applicability_verified"] is False
    assert verified["site_decision_eligible"] is False

    for key in (
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert verified[key] is False

    not_executed = _execution()
    not_executed["resolver_execution_verified"] = False
    assert _verify(not_executed)["resolver_result_verified"] is False

    wrong_condition = _execution()
    wrong_condition["condition_name"] = "개발밀도관리구역"
    assert _verify(wrong_condition)["resolver_result_verified"] is False

    wrong_type = _execution()
    wrong_type["resolution_type"] = "STANDARD_CODE"
    assert _verify(wrong_type)["resolver_result_verified"] is False

    forged_resolution = _execution()
    forged_resolution["resolution"] = "TRUE"
    assert _verify(forged_resolution)["resolver_result_verified"] is False

    wrong_pnu = _execution()
    wrong_pnu["canonical_pnu"] = "1168010600100020000"
    assert _verify(wrong_pnu)["resolver_result_verified"] is False

    missing_admission = _execution()
    missing_admission["resolver_admission"] = {}
    assert _verify(missing_admission)["resolver_result_verified"] is False

    wrong_admission_pnu = _execution()
    wrong_admission_pnu["resolver_admission"]["canonical_pnu"] = "1168010600100020000"
    assert _verify(wrong_admission_pnu)["resolver_result_verified"] is False

    forged_applicability = _execution()
    forged_applicability["parcel_applicability_verified"] = True
    assert _verify(forged_applicability)["resolver_result_verified"] is False

    forged_authority = _execution()
    forged_authority["site_truth_decision_allowed"] = True
    forged_authority["site_promotion_allowed"] = True
    forged_authority["production_registration_allowed"] = True
    forged_authority["runtime_registration_allowed"] = True
    bounded = _verify(forged_authority)
    assert bounded["resolver_result_verified"] is True
    assert bounded["parcel_applicability_verified"] is False
    assert bounded["site_decision_eligible"] is False
    assert bounded["site_truth_decision_allowed"] is False
    assert bounded["site_promotion_allowed"] is False
    assert bounded["production_registration_allowed"] is False
    assert bounded["runtime_registration_allowed"] is False

    malformed = verify_district_unit_plan_hybrid_resolver_result(None, canonical_pnu="")
    assert malformed["resolver_result_verified"] is False
    assert malformed["resolver_execution"] == {}
    assert malformed["resolution"] == "UNKNOWN"

    print("DISTRICT_UNIT_PLAN_HYBRID_RESOLVER_RESULT_VERIFICATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
