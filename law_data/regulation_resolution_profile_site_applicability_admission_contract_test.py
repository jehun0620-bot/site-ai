from __future__ import annotations

from dataclasses import replace

from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    ADMITTED,
    HISTORICAL_PARCEL_EVENT_BINDING,
    REJECTED,
    SPATIAL_PARCEL_INCLUSION,
    UNKNOWN,
    RegulationResolutionProfileSiteApplicabilityEvidence,
    admit_site_applicability,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _eligibility() -> RegulationResolutionProfileSiteDecisionEligibility:
    result = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    assert result.eligible
    return result


def _site(pnu: str = PNU):
    return {
        "site_id": "11680-10300-0012-0000",
        "address": "서울특별시 강남구 개포동 12번지",
        "pnu": pnu,
        "sigungu_code": "11680",
        "bjdong_code": "10300",
        "main_no": "0012",
        "sub_no": "0000",
        "zone": "TEST",
        "identity_status": "COMPLETE",
    }


def _historical_evidence(**changes):
    value = RegulationResolutionProfileSiteApplicabilityEvidence(
        resolver_family=HISTORICAL_SITE_EVENT,
        evidence_kind=HISTORICAL_PARCEL_EVENT_BINDING,
        target_pnu=PNU,
        evidence_pnu=PNU,
        applicability_verified=True,
        applicability_state="APPLIES",
    )
    return replace(value, **changes)


def main() -> None:
    eligibility = _eligibility()

    admitted = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(),
    )
    assert admitted.status == ADMITTED
    assert admitted.admitted is True
    assert admitted.identity_bound is True
    assert admitted.family_evidence_matched is True
    assert admitted.candidate_site_decision is False

    cross_pnu = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(evidence_pnu=OTHER_PNU),
    )
    assert cross_pnu.status == REJECTED
    assert cross_pnu.admitted is False
    assert "parcel_identity_binding" in cross_pnu.missing_gates

    forged_target = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(target_pnu=OTHER_PNU),
    )
    assert forged_target.status == REJECTED
    assert forged_target.admitted is False

    unbound = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(applicability_verified=False),
    )
    assert unbound.status == UNKNOWN
    assert unbound.admitted is False

    unknown = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(
            applicability_verified=True,
            applicability_state="UNKNOWN",
        ),
    )
    assert unknown.status == UNKNOWN
    assert unknown.admitted is False

    wrong_family = admit_site_applicability(
        eligibility,
        _site(),
        _historical_evidence(
            resolver_family=HYBRID_SPATIAL_NOTICE,
            evidence_kind=SPATIAL_PARCEL_INCLUSION,
        ),
    )
    assert wrong_family.status == REJECTED
    assert wrong_family.admitted is False
    assert "resolver_family_evidence" in wrong_family.missing_gates

    incomplete_identity = admit_site_applicability(
        eligibility,
        {**_site(), "identity_status": "PARTIAL"},
        _historical_evidence(),
    )
    assert incomplete_identity.status == REJECTED
    assert incomplete_identity.admitted is False

    missing_pnu = admit_site_applicability(
        eligibility,
        {**_site(), "pnu": ""},
        _historical_evidence(),
    )
    assert missing_pnu.status == REJECTED
    assert missing_pnu.admitted is False

    invalid_eligibility = replace(eligibility, site_promotion_allowed=True)
    rejected = admit_site_applicability(
        invalid_eligibility,
        _site(),
        _historical_evidence(),
    )
    assert rejected.status == REJECTED
    assert rejected.admitted is False

    for result in (
        admitted,
        cross_pnu,
        forged_target,
        unbound,
        unknown,
        wrong_family,
        incomplete_identity,
        missing_pnu,
        rejected,
    ):
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("PROVENANCE_BOUND_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
