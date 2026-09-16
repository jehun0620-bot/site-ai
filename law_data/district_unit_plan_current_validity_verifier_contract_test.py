from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_current_validity_verifier import (
    verify_district_unit_plan_current_validity,
)
from .district_unit_plan_designation_identity_verifier import (
    verify_district_unit_plan_designation_identity,
)


def _designation_record() -> dict:
    return {
        "ANCMNT_MNG_CD": "UPIS-TEST-001",
        "ANCMNT_YMD": "2026-09-16",
        "ANCMNT_NO": "서울특별시고시 제2026-001호",
        "ANCMNT_INST": "서울특별시",
        "TKCG_INST": "도시공간본부",
        "TTL": "도시관리계획(지구단위계획) 결정 고시",
        "CN": "지구단위계획 결정에 관한 공식 고시 기록",
    }


def _positive_evidence(identity: dict) -> dict:
    return {
        "designation_identity": deepcopy(identity),
        "query_success": True,
        "authority_verified": True,
        "notice_chain_verified": True,
        "current_validity_state": "CURRENT",
        "explicit_current_effect_verified": True,
        "source": "official_notice_chain_test_fixture",
    }


def main() -> None:
    designation = verify_district_unit_plan_designation_identity(_designation_record())
    identity = designation["announcement_identity"]

    verified = verify_district_unit_plan_current_validity(
        designation,
        [_positive_evidence(identity)],
    )
    assert verified["current_validity_verified"] is True
    assert verified["validity_state"] == "VERIFIED_CURRENT"
    assert verified["checks"]["positive_evidence_count"] == 1

    for key in (
        "site_spatial_inclusion_verified",
        "site_truth_decision_allowed",
        "site_promotion_allowed",
        "production_registration_allowed",
        "runtime_registration_allowed",
    ):
        assert verified[key] is False

    wrong_chain = _positive_evidence(identity)
    wrong_chain["designation_identity"]["ANCMNT_MNG_CD"] = "OTHER-CHAIN"
    rejected = verify_district_unit_plan_current_validity(designation, [wrong_chain])
    assert rejected["current_validity_verified"] is False
    assert rejected["validity_state"] == "UNKNOWN"

    missing = verify_district_unit_plan_current_validity(designation, [])
    assert missing["current_validity_verified"] is False

    search_failure = _positive_evidence(identity)
    search_failure["query_success"] = False
    rejected = verify_district_unit_plan_current_validity(designation, [search_failure])
    assert rejected["current_validity_verified"] is False

    repealed = _positive_evidence(identity)
    repealed["current_validity_state"] = "REPEALED"
    repealed["explicit_current_effect_verified"] = False
    rejected = verify_district_unit_plan_current_validity(
        designation,
        [_positive_evidence(identity), repealed],
    )
    assert rejected["current_validity_verified"] is False
    assert rejected["validity_state"] == "UNKNOWN"
    assert rejected["checks"]["invalidating_evidence_count"] == 1

    ambiguous = _positive_evidence(identity)
    ambiguous["current_validity_state"] = "UNKNOWN"
    ambiguous["explicit_current_effect_verified"] = False
    rejected = verify_district_unit_plan_current_validity(designation, [ambiguous])
    assert rejected["current_validity_verified"] is False

    inferred_from_absence = _positive_evidence(identity)
    inferred_from_absence["explicit_current_effect_verified"] = False
    rejected = verify_district_unit_plan_current_validity(
        designation,
        [inferred_from_absence],
    )
    assert rejected["current_validity_verified"] is False

    unverified_authority = _positive_evidence(identity)
    unverified_authority["authority_verified"] = False
    rejected = verify_district_unit_plan_current_validity(
        designation,
        [unverified_authority],
    )
    assert rejected["current_validity_verified"] is False

    unverified_chain = _positive_evidence(identity)
    unverified_chain["notice_chain_verified"] = False
    rejected = verify_district_unit_plan_current_validity(designation, [unverified_chain])
    assert rejected["current_validity_verified"] is False

    forged_designation = deepcopy(designation)
    forged_designation["official_designation_identity_verified"] = False
    rejected = verify_district_unit_plan_current_validity(
        forged_designation,
        [_positive_evidence(identity)],
    )
    assert rejected["current_validity_verified"] is False
    assert rejected["announcement_identity"] == {}

    malformed = verify_district_unit_plan_current_validity(None, None)
    assert malformed["current_validity_verified"] is False
    assert malformed["validity_state"] == "UNKNOWN"

    print("DISTRICT_UNIT_PLAN_CURRENT_VALIDITY_VERIFIER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
