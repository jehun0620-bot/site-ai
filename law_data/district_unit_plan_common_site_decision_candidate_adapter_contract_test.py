from __future__ import annotations

from dataclasses import replace

from .district_unit_plan_common_site_decision_candidate_adapter import (
    ADAPTED,
    REJECTED,
    adapt_district_unit_plan_common_site_decision_candidate,
)
from .district_unit_plan_conclusive_site_decision_eligibility import (
    DistrictUnitPlanConclusiveSiteDecisionEligibility,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)

PNU = "1168010300100120000"


def _eligibility() -> DistrictUnitPlanConclusiveSiteDecisionEligibility:
    return DistrictUnitPlanConclusiveSiteDecisionEligibility(
        status="ELIGIBLE",
        canonical_pnu=PNU,
        positive_candidate_verified=True,
        parcel_applicability_verified=True,
        parcel_applicability_state="APPLIES",
        pnu_bound=True,
        candidate_site_decision=True,
        conclusive_for_site_decision=True,
        missing_gates=(),
    )


def _assert_no_authority(result) -> None:
    assert result.generic_step114_satisfied is False
    assert result.generic_site_applicability_admission_allowed is False
    assert result.site_truth_decision_allowed is False
    assert result.site_promotion_allowed is False
    assert result.production_readiness_allowed is False
    assert result.production_registration_allowed is False
    assert result.runtime_registration_allowed is False


def main() -> None:
    source = _eligibility()
    assert source.eligible

    result = adapt_district_unit_plan_common_site_decision_candidate(
        source,
        canonical_pnu=PNU,
    )
    assert result.status == ADAPTED
    assert result.adapted
    assert result.resolver_family == HYBRID_SPATIAL_NOTICE
    assert result.condition_name == "지구단위계획"
    assert result.canonical_pnu == PNU
    assert result.candidate_site_decision is True
    assert result.conclusive_for_site_decision is True
    assert result.source_eligibility_verified is True
    _assert_no_authority(result)

    wrong_pnu = adapt_district_unit_plan_common_site_decision_candidate(
        source,
        canonical_pnu="1168010300100130000",
    )
    assert wrong_pnu.status == REJECTED
    assert not wrong_pnu.adapted
    assert wrong_pnu.candidate_site_decision is None
    _assert_no_authority(wrong_pnu)

    for forged in (
        replace(source, positive_candidate_verified=False),
        replace(source, parcel_applicability_verified=False),
        replace(source, parcel_applicability_state="UNKNOWN"),
        replace(source, pnu_bound=False),
        replace(source, candidate_site_decision=None),
        replace(source, conclusive_for_site_decision=False),
        replace(source, missing_gates=("forged",)),
        replace(source, generic_step114_satisfied=True),
        replace(source, site_truth_decision_allowed=True),
        replace(source, site_promotion_allowed=True),
        replace(source, production_readiness_allowed=True),
        replace(source, production_registration_allowed=True),
        replace(source, runtime_registration_allowed=True),
    ):
        rejected = adapt_district_unit_plan_common_site_decision_candidate(
            forged,
            canonical_pnu=PNU,
        )
        assert rejected.status == REJECTED
        assert not rejected.adapted
        assert rejected.candidate_site_decision is None
        _assert_no_authority(rejected)

    missing = adapt_district_unit_plan_common_site_decision_candidate(
        None,
        canonical_pnu=PNU,
    )
    assert missing.status == REJECTED
    assert not missing.adapted
    _assert_no_authority(missing)

    empty_pnu = adapt_district_unit_plan_common_site_decision_candidate(
        source,
        canonical_pnu="",
    )
    assert empty_pnu.status == REJECTED
    assert not empty_pnu.adapted
    _assert_no_authority(empty_pnu)

    print("DISTRICT_UNIT_PLAN_COMMON_SITE_DECISION_CANDIDATE_ADAPTER_CONTRACT_PASS")


if __name__ == "__main__":
    main()
