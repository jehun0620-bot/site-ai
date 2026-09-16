from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_designation_identity_verifier import (
    verify_district_unit_plan_designation_identity,
)


def _official_record() -> dict:
    return {
        "ANCMNT_MNG_CD": "UPIS-TEST-001",
        "ANCMNT_YMD": "2026-09-16",
        "ANCMNT_NO": "서울특별시고시 제2026-001호",
        "ANCMNT_INST": "서울특별시",
        "TKCG_INST": "도시공간본부",
        "TTL": "도시관리계획(지구단위계획) 결정 고시",
        "CN": "지구단위계획 결정에 관한 공식 고시 기록",
    }


def main() -> None:
    raw = _official_record()
    verified = verify_district_unit_plan_designation_identity(raw)

    assert verified["official_designation_identity_verified"] is True
    assert verified["condition_name"] == "지구단위계획"
    assert verified["announcement_identity"]["ANCMNT_MNG_CD"] == "UPIS-TEST-001"
    assert verified["announcement_identity"]["ANCMNT_NO"] == raw["ANCMNT_NO"]
    assert verified["announcement_identity"]["TTL"] == raw["TTL"]

    for key in (
        "current_validity_verified",
        "site_spatial_inclusion_verified",
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert verified[key] is False

    for field in (
        "ANCMNT_MNG_CD",
        "ANCMNT_YMD",
        "ANCMNT_NO",
        "ANCMNT_INST",
        "TTL",
    ):
        candidate = deepcopy(raw)
        candidate[field] = ""
        rejected = verify_district_unit_plan_designation_identity(candidate)
        assert rejected["official_designation_identity_verified"] is False, field
        assert rejected["announcement_identity"] == {}, field

    wrong_condition = deepcopy(raw)
    wrong_condition["TTL"] = "도시관리계획 변경 결정 고시"
    wrong_condition["CN"] = "개발밀도관리구역 관련 공식 고시"
    rejected = verify_district_unit_plan_designation_identity(wrong_condition)
    assert rejected["official_designation_identity_verified"] is False
    assert rejected["announcement_identity"] == {}

    title_only = deepcopy(raw)
    title_only["CN"] = ""
    verified_title_only = verify_district_unit_plan_designation_identity(title_only)
    assert verified_title_only["official_designation_identity_verified"] is True

    content_only = deepcopy(raw)
    content_only["TTL"] = "도시관리계획 결정 고시"
    content_only["CN"] = "지구단위계획 결정에 관한 공식 고시"
    verified_content_only = verify_district_unit_plan_designation_identity(content_only)
    assert verified_content_only["official_designation_identity_verified"] is True

    malformed = verify_district_unit_plan_designation_identity(None)
    assert malformed["official_designation_identity_verified"] is False
    assert malformed["announcement_identity"] == {}

    print("DISTRICT_UNIT_PLAN_DESIGNATION_IDENTITY_VERIFIER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
