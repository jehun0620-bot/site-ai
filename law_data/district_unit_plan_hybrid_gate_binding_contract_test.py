from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_hybrid_gate_binding import (
    bind_district_unit_plan_hybrid_gates,
)


PNU = "1168010600100010000"
IDENTITY = {
    "ANCMNT_MNG_CD": "UPIS-TEST-001",
    "ANCMNT_YMD": "2026-09-16",
    "ANCMNT_NO": "서울특별시고시 제2026-001호",
    "ANCMNT_INST": "서울특별시",
    "TKCG_INST": "도시공간본부",
    "TTL": "도시관리계획(지구단위계획) 결정 고시",
    "CN": "지구단위계획 결정에 관한 공식 고시 기록",
}


def _designation() -> dict:
    return {
        "official_designation_identity_verified": True,
        "condition_name": "지구단위계획",
        "announcement_identity": deepcopy(IDENTITY),
        "runtime_registration_allowed": False,
    }


def _validity() -> dict:
    return {
        "official_designation_identity_verified": True,
        "current_validity_verified": True,
        "condition_name": "지구단위계획",
        "announcement_identity": deepcopy(IDENTITY),
        "runtime_registration_allowed": False,
    }


def _spatial() -> dict:
    return {
        "site_spatial_inclusion_verified": True,
        "condition_name": "지구단위계획",
        "canonical_pnu": PNU,
        "source_pnu": PNU,
        "dataset": "LT_C_UPISUQ161",
        "runtime_registration_allowed": False,
    }


def _notice_identity() -> dict:
    return {
        "designation_to_spatial_notice_identity_verified": True,
        "condition_name": "지구단위계획",
        "canonical_pnu": PNU,
        "dataset": "LT_C_UPISUQ161",
        "announcement_management_code": "UPIS-TEST-001",
        "spatial_notice_code": "UPIS-TEST-001",
        "announcement_identity": deepcopy(IDENTITY),
        "runtime_registration_allowed": False,
    }


def _bind(
    designation=None,
    validity=None,
    spatial=None,
    notice_identity=None,
    pnu=PNU,
) -> dict:
    return bind_district_unit_plan_hybrid_gates(
        _designation() if designation is None else designation,
        _validity() if validity is None else validity,
        _spatial() if spatial is None else spatial,
        _notice_identity() if notice_identity is None else notice_identity,
        canonical_pnu=pnu,
    )


def main() -> None:
    admitted = _bind()
    assert admitted["hybrid_gate_binding_verified"] is True
    assert admitted["announcement_identity"]["ANCMNT_MNG_CD"] == "UPIS-TEST-001"
    assert admitted["binding_scope"]["designation_to_current_validity"] is True
    assert admitted["binding_scope"]["spatial_to_canonical_pnu"] is True
    assert admitted["binding_scope"]["designation_to_spatial_notice_identity"] is True

    for key in (
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert admitted[key] is False

    wrong_chain = _validity()
    wrong_chain["announcement_identity"]["ANCMNT_MNG_CD"] = "OTHER-CHAIN"
    assert _bind(validity=wrong_chain)["hybrid_gate_binding_verified"] is False

    wrong_notice_chain = _notice_identity()
    wrong_notice_chain["announcement_identity"]["ANCMNT_MNG_CD"] = "OTHER-NOTICE"
    assert _bind(notice_identity=wrong_notice_chain)["hybrid_gate_binding_verified"] is False

    forged_notice_boolean = _notice_identity()
    forged_notice_boolean["announcement_identity"] = {}
    assert _bind(notice_identity=forged_notice_boolean)["hybrid_gate_binding_verified"] is False

    missing_notice_gate = _notice_identity()
    missing_notice_gate["designation_to_spatial_notice_identity_verified"] = False
    assert _bind(notice_identity=missing_notice_gate)["hybrid_gate_binding_verified"] is False

    wrong_pnu = _spatial()
    wrong_pnu["canonical_pnu"] = "1168010600100020000"
    assert _bind(spatial=wrong_pnu)["hybrid_gate_binding_verified"] is False

    wrong_source_pnu = _spatial()
    wrong_source_pnu["source_pnu"] = "1168010600100020000"
    assert _bind(spatial=wrong_source_pnu)["hybrid_gate_binding_verified"] is False

    wrong_notice_pnu = _notice_identity()
    wrong_notice_pnu["canonical_pnu"] = "1168010600100020000"
    assert _bind(notice_identity=wrong_notice_pnu)["hybrid_gate_binding_verified"] is False

    missing_designation_gate = _designation()
    missing_designation_gate["official_designation_identity_verified"] = False
    assert _bind(designation=missing_designation_gate)["hybrid_gate_binding_verified"] is False

    missing_validity_gate = _validity()
    missing_validity_gate["current_validity_verified"] = False
    assert _bind(validity=missing_validity_gate)["hybrid_gate_binding_verified"] is False

    missing_spatial_gate = _spatial()
    missing_spatial_gate["site_spatial_inclusion_verified"] = False
    assert _bind(spatial=missing_spatial_gate)["hybrid_gate_binding_verified"] is False

    forged_boolean = _validity()
    forged_boolean["announcement_identity"] = {}
    assert _bind(validity=forged_boolean)["hybrid_gate_binding_verified"] is False

    malformed = bind_district_unit_plan_hybrid_gates(
        None, None, None, None, canonical_pnu=""
    )
    assert malformed["hybrid_gate_binding_verified"] is False
    assert malformed["stage_results"] == {}

    escalated_inputs = (_designation(), _validity(), _spatial(), _notice_identity())
    for item in escalated_inputs:
        item["runtime_registration_allowed"] = True
        item["production_registration_allowed"] = True
    bounded = bind_district_unit_plan_hybrid_gates(
        *escalated_inputs,
        canonical_pnu=PNU,
    )
    assert bounded["hybrid_gate_binding_verified"] is True
    assert bounded["runtime_registration_allowed"] is False
    assert bounded["production_registration_allowed"] is False
    assert bounded["site_truth_decision_allowed"] is False
    assert bounded["site_promotion_allowed"] is False

    print("DISTRICT_UNIT_PLAN_HYBRID_GATE_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
