from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_hybrid_positive_candidate import (
    POSITIVE_CANDIDATE,
    evaluate_district_unit_plan_hybrid_positive_candidate,
)
from .district_unit_plan_hybrid_resolver_result_verification_contract_test import (
    PNU,
    _verified_execution,
)
from .district_unit_plan_hybrid_resolver_result_verification import (
    verify_district_unit_plan_hybrid_resolver_result,
)

OTHER_PNU = "1168010300100130000"


def _verified_result():
    return verify_district_unit_plan_hybrid_resolver_result(
        _verified_execution(),
        canonical_pnu=PNU,
    )


def main() -> None:
    verified_result = _verified_result()
    assert verified_result["resolver_result_verified"] is True

    candidate = evaluate_district_unit_plan_hybrid_positive_candidate(
        verified_result,
        canonical_pnu=PNU,
    )
    assert candidate["positive_candidate_verified"] is True
    assert candidate["candidate_state"] == POSITIVE_CANDIDATE
    assert candidate["source_resolution"] == "UNKNOWN"
    assert candidate["parcel_applicability_verified"] is False
    assert candidate["site_decision_eligible"] is False

    wrong_pnu = evaluate_district_unit_plan_hybrid_positive_candidate(
        verified_result,
        canonical_pnu=OTHER_PNU,
    )
    assert wrong_pnu["positive_candidate_verified"] is False
    assert wrong_pnu["candidate_state"] is None

    forged_resolution = deepcopy(verified_result)
    forged_resolution["resolution"] = "TRUE_CANDIDATE"
    forged = evaluate_district_unit_plan_hybrid_positive_candidate(
        forged_resolution,
        canonical_pnu=PNU,
    )
    assert forged["positive_candidate_verified"] is False

    missing_binding = deepcopy(verified_result)
    missing_binding["resolver_execution"]["resolver_admission"]["hybrid_binding"] = {}
    rejected_binding = evaluate_district_unit_plan_hybrid_positive_candidate(
        missing_binding,
        canonical_pnu=PNU,
    )
    assert rejected_binding["positive_candidate_verified"] is False

    forged_parcel = deepcopy(verified_result)
    forged_parcel["parcel_applicability_verified"] = True
    rejected_parcel = evaluate_district_unit_plan_hybrid_positive_candidate(
        forged_parcel,
        canonical_pnu=PNU,
    )
    assert rejected_parcel["positive_candidate_verified"] is False

    forged_step114 = deepcopy(verified_result)
    forged_step114["site_decision_eligible"] = True
    rejected_step114 = evaluate_district_unit_plan_hybrid_positive_candidate(
        forged_step114,
        canonical_pnu=PNU,
    )
    assert rejected_step114["positive_candidate_verified"] is False

    forged_authority = deepcopy(verified_result)
    forged_authority["site_promotion_allowed"] = True
    authority_candidate = evaluate_district_unit_plan_hybrid_positive_candidate(
        forged_authority,
        canonical_pnu=PNU,
    )
    assert authority_candidate["positive_candidate_verified"] is True

    for result in (
        candidate,
        wrong_pnu,
        forged,
        rejected_binding,
        rejected_parcel,
        rejected_step114,
        authority_candidate,
    ):
        assert result["parcel_applicability_verified"] is False
        assert result["site_decision_eligible"] is False
        assert result["site_truth_decision_allowed"] is False
        assert result["site_promotion_allowed"] is False
        assert result["production_registration_allowed"] is False
        assert result["runtime_registration_allowed"] is False

    print("DISTRICT_UNIT_PLAN_HYBRID_POSITIVE_CANDIDATE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
