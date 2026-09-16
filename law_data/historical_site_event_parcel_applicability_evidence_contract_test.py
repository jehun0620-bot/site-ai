from __future__ import annotations

from dataclasses import replace

from .historical_site_event_parcel_applicability_evidence import (
    REJECTED,
    UNKNOWN,
    VERIFIED,
    HistoricalSiteEventParcelEvidenceInput,
    build_historical_site_event_parcel_applicability_evidence,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HISTORICAL_SITE_EVENT,
)
from .regulation_resolution_profile_site_applicability_admission import (
    HISTORICAL_PARCEL_EVENT_BINDING,
)

PNU = "1168010300100120000"
OTHER_PNU = "1168010300100130000"


def _site(pnu: str = PNU):
    return {
        "site_id": "11680-10300-0012-0000",
        "pnu": pnu,
        "identity_status": "COMPLETE",
    }


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
    verified = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(),
    )
    assert verified.status == VERIFIED
    assert verified.verified is True
    assert verified.pnu_matched is True
    assert verified.applicability_verified is True
    assert verified.applicability_state == "APPLIES"
    assert verified.applicability_evidence is not None
    assert verified.applicability_evidence.resolver_family == HISTORICAL_SITE_EVENT
    assert (
        verified.applicability_evidence.evidence_kind
        == HISTORICAL_PARCEL_EVENT_BINDING
    )
    assert verified.applicability_evidence.target_pnu == PNU
    assert verified.applicability_evidence.evidence_pnu == PNU

    cross_pnu = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(evidence_pnu=OTHER_PNU),
    )
    assert cross_pnu.status == REJECTED
    assert cross_pnu.verified is False
    assert cross_pnu.applicability_evidence is None
    assert "pnu_matched" in cross_pnu.missing_gates

    forged_target = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(target_pnu=OTHER_PNU),
    )
    assert forged_target.status == REJECTED
    assert forged_target.verified is False

    invalid_pnu = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(evidence_pnu="11680"),
    )
    assert invalid_pnu.status == REJECTED
    assert invalid_pnu.verified is False
    assert "evidence_pnu_valid" in invalid_pnu.missing_gates

    incomplete_site = build_historical_site_event_parcel_applicability_evidence(
        {**_site(), "identity_status": "PARTIAL"},
        _evidence(),
    )
    assert incomplete_site.status == REJECTED
    assert incomplete_site.verified is False

    source_unknown = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(official_source_verified=False),
    )
    assert source_unknown.status == UNKNOWN
    assert source_unknown.verified is False
    assert source_unknown.applicability_state == "UNKNOWN"

    parcel_unknown = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(parcel_binding_verified=False),
    )
    assert parcel_unknown.status == UNKNOWN
    assert parcel_unknown.verified is False

    event_unknown = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(event_binding_verified=False),
    )
    assert event_unknown.status == UNKNOWN
    assert event_unknown.verified is False

    missing_event_identity = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        _evidence(event_identity=""),
    )
    assert missing_event_identity.status == UNKNOWN
    assert missing_event_identity.verified is False

    missing_input = build_historical_site_event_parcel_applicability_evidence(
        _site(),
        None,
    )
    assert missing_input.status == REJECTED
    assert missing_input.verified is False

    for result in (
        verified,
        cross_pnu,
        forged_target,
        invalid_pnu,
        incomplete_site,
        source_unknown,
        parcel_unknown,
        event_unknown,
        missing_event_identity,
        missing_input,
    ):
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("HISTORICAL_SITE_EVENT_PARCEL_APPLICABILITY_EVIDENCE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
