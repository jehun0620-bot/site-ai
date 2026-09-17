"""Contract test for district-unit-plan SITE-truth promotion authorization."""

from dataclasses import replace

from .common_site_applicability_admission import CommonSiteApplicabilityAdmission
from .district_unit_plan_site_truth_promotion_authorization import (
    BOUNDARY_NAME,
    authorize_district_unit_plan_site_truth_promotion,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)

PNU = "1168010600100010000"
OTHER_PNU = "1168010600100020000"


def _admission() -> CommonSiteApplicabilityAdmission:
    return CommonSiteApplicabilityAdmission(
        status="ADMITTED",
        resolver_family=HYBRID_SPATIAL_NOTICE,
        canonical_pnu=PNU,
        candidate_site_decision=True,
        applicability_state="APPLIES",
        candidate_verified=True,
        evidence_verified=True,
        family_matched=True,
        evidence_kind_matched=True,
        pnu_bound=True,
        site_applicability_admitted=True,
    )


def _assert_no_execution_authority(result) -> None:
    assert result.site_truth_decision_allowed is False
    assert result.site_truth_mutation_allowed is False
    assert result.promotion_execution_allowed is False
    assert result.production_readiness_allowed is False
    assert result.production_registration_allowed is False
    assert result.runtime_registration_allowed is False
    assert result.public_api_exposure_allowed is False


def main() -> None:
    result = authorize_district_unit_plan_site_truth_promotion(
        _admission(), canonical_pnu=PNU
    )
    assert result.authorized
    assert result.boundary == BOUNDARY_NAME
    assert result.canonical_pnu == PNU
    assert result.resolver_family == HYBRID_SPATIAL_NOTICE
    assert result.condition_name == "지구단위계획"
    assert result.bound_state == "TRUE"
    assert result.provenance_kind == "HYBRID_SPATIAL_NOTICE_VERIFIED"
    _assert_no_execution_authority(result)

    wrong_pnu = authorize_district_unit_plan_site_truth_promotion(
        _admission(), canonical_pnu=OTHER_PNU
    )
    assert not wrong_pnu.authorized
    _assert_no_execution_authority(wrong_pnu)

    historical = replace(_admission(), resolver_family=HISTORICAL_SITE_EVENT)
    assert not authorize_district_unit_plan_site_truth_promotion(
        historical, canonical_pnu=PNU
    ).authorized

    false_candidate = replace(_admission(), candidate_site_decision=False)
    assert not authorize_district_unit_plan_site_truth_promotion(
        false_candidate, canonical_pnu=PNU
    ).authorized

    unknown_applicability = replace(_admission(), applicability_state="UNKNOWN")
    assert not authorize_district_unit_plan_site_truth_promotion(
        unknown_applicability, canonical_pnu=PNU
    ).authorized

    forged_runtime = replace(_admission(), runtime_registration_allowed=True)
    forged_result = authorize_district_unit_plan_site_truth_promotion(
        forged_runtime, canonical_pnu=PNU
    )
    assert not forged_result.authorized
    _assert_no_execution_authority(forged_result)

    assert not authorize_district_unit_plan_site_truth_promotion(
        None, canonical_pnu=PNU
    ).authorized
    assert not authorize_district_unit_plan_site_truth_promotion(
        _admission(), canonical_pnu=""
    ).authorized

    print("DISTRICT_UNIT_PLAN_SITE_TRUTH_PROMOTION_AUTHORIZATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
