from __future__ import annotations

from copy import deepcopy

from law_data.district_unit_plan_spatial_notice_identity_verifier import (
    verify_district_unit_plan_spatial_notice_identity,
)


PNU = "1168010300100120000"
NOTICE_CODE = "11000NTC199603305909"


def _designation() -> dict:
    return {
        "official_designation_identity_verified": True,
        "condition_name": "지구단위계획",
        "announcement_identity": {
            "ANCMNT_MNG_CD": NOTICE_CODE,
            "ANCMNT_YMD": "1996-03-30T00:00:00.000",
            "ANCMNT_NO": "1996-65",
            "ANCMNT_INST": "서울특별시",
            "TKCG_INST": "서울특별시",
            "TTL": "지구단위계획 관련 공식 고시",
            "CN": "지구단위계획",
        },
    }


def _spatial() -> dict:
    return {
        "site_spatial_inclusion_verified": True,
        "condition_name": "지구단위계획",
        "canonical_pnu": PNU,
        "source_pnu": PNU,
        "dataset": "LT_C_UPISUQ161",
        "evidence": {
            "name": "지구단위계획",
            "type": "SITE",
            "pnu": PNU,
            "source": {
                "provider": "VWorld",
                "dataset": "LT_C_UPISUQ161",
                "crs": "EPSG:4326",
            },
            "feature_properties": {
                "ntfc_sn": NOTICE_CODE,
                "dgm_nm": "대치택지개발지구",
                "present_sn": "11000UQ161PS202005260028",
            },
        },
    }


def _assert_authority_stays_closed(result: dict) -> None:
    assert result["current_validity_verified"] is False
    assert result["site_truth_decision_allowed"] is False
    assert result["site_promotion_allowed"] is False
    assert result["production_registration_allowed"] is False
    assert result["runtime_registration_allowed"] is False


def main() -> int:
    admitted = verify_district_unit_plan_spatial_notice_identity(
        _designation(), _spatial()
    )
    assert admitted["designation_to_spatial_notice_identity_verified"] is True
    assert admitted["announcement_management_code"] == NOTICE_CODE
    assert admitted["spatial_notice_code"] == NOTICE_CODE
    assert admitted["checks"]["exact_management_code_match"] is True
    assert admitted["announcement_identity"]
    assert admitted["spatial_evidence"]
    _assert_authority_stays_closed(admitted)

    mismatch_spatial = _spatial()
    mismatch_spatial["evidence"]["feature_properties"]["ntfc_sn"] = "OTHER"
    mismatch = verify_district_unit_plan_spatial_notice_identity(
        _designation(), mismatch_spatial
    )
    assert mismatch["designation_to_spatial_notice_identity_verified"] is False
    assert mismatch["checks"]["exact_management_code_match"] is False
    assert mismatch["announcement_identity"] == {}
    assert mismatch["spatial_evidence"] == {}
    _assert_authority_stays_closed(mismatch)

    missing_spatial = _spatial()
    del missing_spatial["evidence"]["feature_properties"]["ntfc_sn"]
    missing = verify_district_unit_plan_spatial_notice_identity(
        _designation(), missing_spatial
    )
    assert missing["designation_to_spatial_notice_identity_verified"] is False
    assert missing["checks"]["spatial_notice_code_present"] is False
    _assert_authority_stays_closed(missing)

    wrong_condition = _designation()
    wrong_condition["condition_name"] = "개발밀도관리구역"
    condition_rejected = verify_district_unit_plan_spatial_notice_identity(
        wrong_condition, _spatial()
    )
    assert condition_rejected["designation_to_spatial_notice_identity_verified"] is False
    assert condition_rejected["checks"]["designation_condition_matches"] is False
    _assert_authority_stays_closed(condition_rejected)

    unverified_spatial = _spatial()
    unverified_spatial["site_spatial_inclusion_verified"] = False
    spatial_rejected = verify_district_unit_plan_spatial_notice_identity(
        _designation(), unverified_spatial
    )
    assert spatial_rejected["designation_to_spatial_notice_identity_verified"] is False
    assert spatial_rejected["checks"]["spatial_inclusion_verified"] is False
    _assert_authority_stays_closed(spatial_rejected)

    wrong_pnu = _spatial()
    wrong_pnu["source_pnu"] = "1168010300100130000"
    pnu_rejected = verify_district_unit_plan_spatial_notice_identity(
        _designation(), wrong_pnu
    )
    assert pnu_rejected["designation_to_spatial_notice_identity_verified"] is False
    assert pnu_rejected["checks"]["source_pnu_matches"] is False
    _assert_authority_stays_closed(pnu_rejected)

    print("DISTRICT_UNIT_PLAN_SPATIAL_NOTICE_IDENTITY_VERIFIER_CONTRACT_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
