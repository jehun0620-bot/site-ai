from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_hybrid_resolver_admission import (
    admit_district_unit_plan_hybrid_resolver_input,
)


PNU = "1168010600100010000"


def _binding() -> dict:
    return {
        "hybrid_gate_binding_verified": True,
        "condition_name": "지구단위계획",
        "canonical_pnu": PNU,
        "announcement_identity": {"ANCMNT_MNG_CD": "UPIS-TEST-001"},
        "binding_scope": {
            "designation_to_current_validity": True,
            "spatial_to_canonical_pnu": True,
            "designation_to_spatial_notice_identity": True,
        },
        "stage_results": {
            "designation_identity": {"marker": "designation"},
            "current_validity": {"marker": "validity"},
            "site_spatial_inclusion": {"marker": "spatial"},
            "spatial_notice_identity": {"marker": "notice-identity"},
        },
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }


def _admit(binding=None, pnu=PNU) -> dict:
    return admit_district_unit_plan_hybrid_resolver_input(
        _binding() if binding is None else binding,
        canonical_pnu=pnu,
    )


def main() -> None:
    admitted = _admit()
    assert admitted["resolver_input_admitted"] is True
    assert admitted["resolution_type"] == "HYBRID_SPATIAL_NOTICE"
    assert admitted["canonical_pnu"] == PNU
    assert admitted["hybrid_binding"]["hybrid_gate_binding_verified"] is True

    for key in (
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert admitted[key] is False

    missing_binding_gate = _binding()
    missing_binding_gate["hybrid_gate_binding_verified"] = False
    assert _admit(missing_binding_gate)["resolver_input_admitted"] is False

    wrong_condition = _binding()
    wrong_condition["condition_name"] = "개발밀도관리구역"
    assert _admit(wrong_condition)["resolver_input_admitted"] is False

    wrong_pnu = _binding()
    wrong_pnu["canonical_pnu"] = "1168010600100020000"
    assert _admit(wrong_pnu)["resolver_input_admitted"] is False

    missing_scope = _binding()
    missing_scope["binding_scope"]["designation_to_spatial_notice_identity"] = False
    assert _admit(missing_scope)["resolver_input_admitted"] is False

    missing_stages = _binding()
    missing_stages["stage_results"] = {}
    assert _admit(missing_stages)["resolver_input_admitted"] is False

    forged_authority = _binding()
    forged_authority["runtime_registration_allowed"] = True
    forged_authority["production_registration_allowed"] = True
    forged_authority["site_truth_decision_allowed"] = True
    forged_authority["site_promotion_allowed"] = True
    bounded = _admit(forged_authority)
    assert bounded["resolver_input_admitted"] is True
    assert bounded["runtime_registration_allowed"] is False
    assert bounded["production_registration_allowed"] is False
    assert bounded["site_truth_decision_allowed"] is False
    assert bounded["site_promotion_allowed"] is False

    malformed = admit_district_unit_plan_hybrid_resolver_input(None, canonical_pnu="")
    assert malformed["resolver_input_admitted"] is False
    assert malformed["hybrid_binding"] == {}

    print("DISTRICT_UNIT_PLAN_HYBRID_RESOLVER_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
