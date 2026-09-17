"""Contract tests for the common SITE applicability admission candidate boundary."""

from dataclasses import replace

from .common_site_applicability_admission_candidate import (
    ADMITTED,
    REJECTED,
    admit_common_site_applicability_candidate,
)
from .district_unit_plan_common_site_decision_candidate_adapter import (
    ADAPTED,
    DistrictUnitPlanCommonSiteDecisionCandidate,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _historical() -> RegulationResolutionProfileSiteDecisionEligibility:
    return RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )


def _district() -> DistrictUnitPlanCommonSiteDecisionCandidate:
    return DistrictUnitPlanCommonSiteDecisionCandidate(
        status=ADAPTED,
        resolver_family=HYBRID_SPATIAL_NOTICE,
        condition_name="지구단위계획",
        canonical_pnu=PNU,
        candidate_site_decision=True,
        conclusive_for_site_decision=True,
        source_eligibility_verified=True,
    )


def _assert_no_authority(result) -> None:
    assert result.generic_site_applicability_admission_allowed is False
    assert result.site_truth_decision_allowed is False
    assert result.site_promotion_allowed is False
    assert result.production_readiness_allowed is False
    assert result.production_registration_allowed is False
    assert result.runtime_registration_allowed is False


def run_contract() -> None:
    historical = admit_common_site_applicability_candidate(_historical(), canonical_pnu=PNU)
    assert historical.status == ADMITTED
    assert historical.admitted
    assert historical.resolver_family == HISTORICAL_SITE_EVENT
    assert historical.candidate_site_decision is False
    assert historical.source_kind == "GENERIC_STEP114"
    _assert_no_authority(historical)

    district = admit_common_site_applicability_candidate(_district(), canonical_pnu=PNU)
    assert district.status == ADMITTED
    assert district.admitted
    assert district.resolver_family == HYBRID_SPATIAL_NOTICE
    assert district.canonical_pnu == PNU
    assert district.candidate_site_decision is True
    assert district.source_kind == "DISTRICT_UNIT_PLAN_COMMON"
    _assert_no_authority(district)

    cross_pnu = admit_common_site_applicability_candidate(_district(), canonical_pnu=OTHER_PNU)
    assert cross_pnu.status == REJECTED
    assert not cross_pnu.admitted
    _assert_no_authority(cross_pnu)

    forged_district = replace(_district(), generic_site_applicability_admission_allowed=True)
    forged = admit_common_site_applicability_candidate(forged_district, canonical_pnu=PNU)
    assert forged.status == REJECTED
    assert not forged.admitted
    _assert_no_authority(forged)

    nonconclusive = replace(_district(), conclusive_for_site_decision=False)
    rejected = admit_common_site_applicability_candidate(nonconclusive, canonical_pnu=PNU)
    assert rejected.status == REJECTED
    assert not rejected.admitted

    forged_historical = replace(_historical(), site_promotion_allowed=True)
    rejected = admit_common_site_applicability_candidate(forged_historical, canonical_pnu=PNU)
    assert rejected.status == REJECTED
    assert not rejected.admitted
    _assert_no_authority(rejected)

    missing_pnu = admit_common_site_applicability_candidate(_district(), canonical_pnu="")
    assert missing_pnu.status == REJECTED
    assert not missing_pnu.admitted

    malformed = admit_common_site_applicability_candidate(None, canonical_pnu=PNU)
    assert malformed.status == REJECTED
    assert not malformed.admitted
    _assert_no_authority(malformed)

    print("COMMON_SITE_APPLICABILITY_ADMISSION_CANDIDATE_CONTRACT_PASS")


if __name__ == "__main__":
    run_contract()
