from __future__ import annotations

from dataclasses import replace

from .district_unit_plan_conclusive_site_decision_eligibility import (
    ELIGIBLE,
    INELIGIBLE,
    REJECTED,
    evaluate_district_unit_plan_conclusive_site_decision_eligibility,
)
from .district_unit_plan_spatial_parcel_applicability_evidence import (
    build_district_unit_plan_spatial_parcel_applicability_evidence,
)

PNU = "1168010600100010000"
OTHER_PNU = "1168010600100020000"


def _candidate(pnu=PNU) -> dict:
    return {
        "positive_candidate_verified": True,
        "candidate_state": "POSITIVE_CANDIDATE",
        "condition_name": "지구단위계획",
        "resolution_type": "HYBRID_SPATIAL_NOTICE",
        "source_resolution": "UNKNOWN",
        "canonical_pnu": pnu,
        "parcel_applicability_verified": False,
        "site_decision_eligible": False,
    }


def _parcel(candidate=None, pnu=PNU):
    candidate = _candidate(pnu) if candidate is None else candidate
    return build_district_unit_plan_spatial_parcel_applicability_evidence(
        {"identity_status": "COMPLETE", "pnu": pnu},
        candidate,
        {
            "site_spatial_inclusion_verified": True,
            "condition_name": "지구단위계획",
            "canonical_pnu": pnu,
            "source_pnu": pnu,
            "dataset": "LT_C_UPISUQ161",
        },
    )


def main() -> None:
    candidate = _candidate()
    parcel = _parcel(candidate)
    eligible = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate,
        parcel,
        canonical_pnu=PNU,
    )
    assert eligible.status == ELIGIBLE
    assert eligible.eligible is True
    assert eligible.candidate_site_decision is True
    assert eligible.conclusive_for_site_decision is True
    assert eligible.parcel_applicability_verified is True
    assert eligible.parcel_applicability_state == "APPLIES"
    assert eligible.pnu_bound is True
    assert eligible.generic_step114_satisfied is False

    wrong_candidate_pnu = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        _candidate(OTHER_PNU),
        parcel,
        canonical_pnu=PNU,
    )
    assert wrong_candidate_pnu.status == INELIGIBLE
    assert wrong_candidate_pnu.eligible is False
    assert wrong_candidate_pnu.candidate_site_decision is None

    candidate_unknown = _candidate()
    candidate_unknown["positive_candidate_verified"] = False
    unknown = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate_unknown,
        parcel,
        canonical_pnu=PNU,
    )
    assert unknown.status == INELIGIBLE
    assert unknown.eligible is False

    forged_resolution = _candidate()
    forged_resolution["source_resolution"] = "TRUE_CANDIDATE"
    forged = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        forged_resolution,
        parcel,
        canonical_pnu=PNU,
    )
    assert forged.status == INELIGIBLE

    no_parcel = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate,
        None,
        canonical_pnu=PNU,
    )
    assert no_parcel.status == INELIGIBLE
    assert no_parcel.parcel_applicability_verified is False

    rejected_parcel = _parcel(candidate, OTHER_PNU)
    rejected = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate,
        rejected_parcel,
        canonical_pnu=PNU,
    )
    assert rejected.status == REJECTED
    assert rejected.eligible is False

    forged_parcel = replace(parcel, applicability_verified=False)
    forged_parcel_result = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate,
        forged_parcel,
        canonical_pnu=PNU,
    )
    assert forged_parcel_result.status == INELIGIBLE
    assert forged_parcel_result.eligible is False

    missing_pnu = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        candidate,
        parcel,
        canonical_pnu="",
    )
    assert missing_pnu.status == REJECTED

    forged_authority_candidate = _candidate()
    forged_authority_candidate["site_promotion_allowed"] = True
    bounded = evaluate_district_unit_plan_conclusive_site_decision_eligibility(
        forged_authority_candidate,
        parcel,
        canonical_pnu=PNU,
    )
    assert bounded.eligible is True

    for result in (
        eligible,
        wrong_candidate_pnu,
        unknown,
        forged,
        no_parcel,
        rejected,
        forged_parcel_result,
        missing_pnu,
        bounded,
    ):
        assert result.generic_step114_satisfied is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("DISTRICT_UNIT_PLAN_CONCLUSIVE_SITE_DECISION_ELIGIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
