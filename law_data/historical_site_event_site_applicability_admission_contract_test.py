from __future__ import annotations

from dataclasses import replace

from .historical_site_event_parcel_applicability_evidence import (
    HistoricalSiteEventParcelEvidenceInput,
)
from .historical_site_event_site_applicability_admission import (
    ADMITTED,
    REJECTED,
    UNKNOWN,
    admit_historical_site_event_site_applicability,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    RegulationResolutionProfileSiteDecisionEligibility,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _site(pnu: str = PNU):
    return {
        "site_id": "11680-10300-0012-0000",
        "pnu": pnu,
        "identity_status": "COMPLETE",
    }


def _eligibility():
    value = RegulationResolutionProfileSiteDecisionEligibility(
        status=ELIGIBLE,
        resolver_family=HISTORICAL_SITE_EVENT,
        resolver_result_verified=True,
        resolution="FALSE",
        candidate_site_decision=False,
        conclusive_for_site_decision=True,
    )
    assert value.eligible
    return value


def _evidence(**changes):
    value = HistoricalSiteEventParcelEvidenceInput(
        target_pnu=PNU,
        evidence_pnu=PNU,
        event_identity="TEST-HISTORICAL-EVENT-1",
        official_source_verified=True,
        parcel_binding_verified=True,
        event_binding_verified=True,
    )
    return replace(value, **changes)


def main() -> None:
    eligibility = _eligibility()

    admitted = admit_historical_site_event_site_applicability(
        eligibility,
        _site(),
        _evidence(),
    )
    assert admitted.status == ADMITTED
    assert admitted.admitted is True
    assert admitted.parcel_evidence_result.verified is True
    assert admitted.site_admission is not None
    assert admitted.site_admission.admitted is True
    assert admitted.candidate_site_decision is False

    cross_pnu = admit_historical_site_event_site_applicability(
        eligibility,
        _site(),
        _evidence(evidence_pnu=OTHER_PNU),
    )
    assert cross_pnu.status == REJECTED
    assert cross_pnu.admitted is False
    assert cross_pnu.site_admission is None
    assert cross_pnu.candidate_site_decision is None

    unknown_binding = admit_historical_site_event_site_applicability(
        eligibility,
        _site(),
        _evidence(parcel_binding_verified=False),
    )
    assert unknown_binding.status == UNKNOWN
    assert unknown_binding.admitted is False
    assert unknown_binding.candidate_site_decision is None

    incomplete_site = admit_historical_site_event_site_applicability(
        eligibility,
        {**_site(), "identity_status": "PARTIAL"},
        _evidence(),
    )
    assert incomplete_site.status == REJECTED
    assert incomplete_site.admitted is False

    invalid_eligibility = replace(eligibility, site_promotion_allowed=True)
    eligibility_rejected = admit_historical_site_event_site_applicability(
        invalid_eligibility,
        _site(),
        _evidence(),
    )
    assert eligibility_rejected.status == REJECTED
    assert eligibility_rejected.admitted is False
    assert eligibility_rejected.site_admission is not None
    assert eligibility_rejected.site_admission.admitted is False
    assert eligibility_rejected.candidate_site_decision is None

    missing_evidence = admit_historical_site_event_site_applicability(
        eligibility,
        _site(),
        None,
    )
    assert missing_evidence.status == REJECTED
    assert missing_evidence.admitted is False

    for result in (
        admitted,
        cross_pnu,
        unknown_binding,
        incomplete_site,
        eligibility_rejected,
        missing_evidence,
    ):
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("HISTORICAL_SITE_EVENT_SITE_APPLICABILITY_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
