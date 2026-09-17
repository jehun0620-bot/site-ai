"""Contract test for the common SITE applicability admission boundary."""

from dataclasses import replace

from .common_site_applicability_admission import admit_common_site_applicability
from .common_site_applicability_admission_candidate import (
    CommonSiteApplicabilityAdmissionCandidate,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    HISTORICAL_PARCEL_EVENT_BINDING,
    SPATIAL_PARCEL_INCLUSION,
    RegulationResolutionProfileSiteApplicabilityEvidence,
)

PNU = "1168010600100010000"
OTHER_PNU = "1168010600100020000"


def _candidate(family: str, decision: bool) -> CommonSiteApplicabilityAdmissionCandidate:
    return CommonSiteApplicabilityAdmissionCandidate(
        status="ADMITTED",
        resolver_family=family,
        canonical_pnu=PNU,
        candidate_site_decision=decision,
        conclusive_for_site_decision=True,
        source_candidate_verified=True,
        source_kind=(
            "GENERIC_STEP114"
            if family == HISTORICAL_SITE_EVENT
            else "DISTRICT_UNIT_PLAN_COMMON"
        ),
    )


def _evidence(family: str, kind: str, pnu: str = PNU):
    return RegulationResolutionProfileSiteApplicabilityEvidence(
        resolver_family=family,
        evidence_kind=kind,
        target_pnu=pnu,
        evidence_pnu=pnu,
        applicability_verified=True,
        applicability_state="APPLIES",
    )


def _assert_no_authority(result) -> None:
    assert result.site_truth_decision_allowed is False
    assert result.site_promotion_allowed is False
    assert result.production_readiness_allowed is False
    assert result.production_registration_allowed is False
    assert result.runtime_registration_allowed is False


def main() -> None:
    historical = admit_common_site_applicability(
        _candidate(HISTORICAL_SITE_EVENT, False),
        _evidence(HISTORICAL_SITE_EVENT, HISTORICAL_PARCEL_EVENT_BINDING),
        canonical_pnu=PNU,
    )
    assert historical.admitted
    assert historical.candidate_site_decision is False
    assert historical.applicability_state == "APPLIES"
    _assert_no_authority(historical)

    hybrid = admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION),
        canonical_pnu=PNU,
    )
    assert hybrid.admitted
    assert hybrid.candidate_site_decision is True
    assert hybrid.applicability_state == "APPLIES"
    _assert_no_authority(hybrid)

    wrong_family = admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        _evidence(HISTORICAL_SITE_EVENT, HISTORICAL_PARCEL_EVENT_BINDING),
        canonical_pnu=PNU,
    )
    assert not wrong_family.admitted

    wrong_kind = admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        _evidence(HYBRID_SPATIAL_NOTICE, HISTORICAL_PARCEL_EVENT_BINDING),
        canonical_pnu=PNU,
    )
    assert not wrong_kind.admitted

    wrong_pnu = admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION, OTHER_PNU),
        canonical_pnu=PNU,
    )
    assert not wrong_pnu.admitted

    forged_candidate = replace(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        production_registration_allowed=True,
    )
    forged_candidate_result = admit_common_site_applicability(
        forged_candidate,
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION),
        canonical_pnu=PNU,
    )
    assert not forged_candidate_result.admitted
    _assert_no_authority(forged_candidate_result)

    unverified_evidence = replace(
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION),
        applicability_verified=False,
    )
    assert not admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        unverified_evidence,
        canonical_pnu=PNU,
    ).admitted

    assert not admit_common_site_applicability(
        None,
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION),
        canonical_pnu=PNU,
    ).admitted
    assert not admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        None,
        canonical_pnu=PNU,
    ).admitted
    assert not admit_common_site_applicability(
        _candidate(HYBRID_SPATIAL_NOTICE, True),
        _evidence(HYBRID_SPATIAL_NOTICE, SPATIAL_PARCEL_INCLUSION),
        canonical_pnu="",
    ).admitted

    print("COMMON_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
