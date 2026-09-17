from __future__ import annotations

from copy import deepcopy

from .district_unit_plan_spatial_parcel_applicability_evidence import (
    REJECTED,
    UNKNOWN,
    VERIFIED,
    build_district_unit_plan_spatial_parcel_applicability_evidence,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    HYBRID_SPATIAL_NOTICE,
)
from .regulation_resolution_profile_site_applicability_admission import (
    SPATIAL_PARCEL_INCLUSION,
)

PNU = "1168010600100010000"
OTHER_PNU = "1168010600100020000"


def _site(pnu=PNU) -> dict:
    return {"identity_status": "COMPLETE", "pnu": pnu}


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
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }


def _spatial(pnu=PNU) -> dict:
    return {
        "site_spatial_inclusion_verified": True,
        "condition_name": "지구단위계획",
        "canonical_pnu": pnu,
        "source_pnu": pnu,
        "dataset": "LT_C_UPISUQ161",
        "site_truth_decision_allowed": False,
        "site_promotion_allowed": False,
        "production_registration_allowed": False,
        "runtime_registration_allowed": False,
    }


def _build(site=None, candidate=None, spatial=None):
    return build_district_unit_plan_spatial_parcel_applicability_evidence(
        _site() if site is None else site,
        _candidate() if candidate is None else candidate,
        _spatial() if spatial is None else spatial,
    )


def main() -> None:
    verified = _build()
    assert verified.status == VERIFIED
    assert verified.verified is True
    assert verified.applicability_verified is True
    assert verified.applicability_state == "APPLIES"
    assert verified.applicability_evidence is not None
    assert verified.applicability_evidence.resolver_family == HYBRID_SPATIAL_NOTICE
    assert verified.applicability_evidence.evidence_kind == SPATIAL_PARCEL_INCLUSION
    assert verified.applicability_evidence.target_pnu == PNU
    assert verified.applicability_evidence.evidence_pnu == PNU

    wrong_candidate_pnu = _build(candidate=_candidate(OTHER_PNU))
    assert wrong_candidate_pnu.status == REJECTED
    assert wrong_candidate_pnu.verified is False
    assert "parcel_pnu_binding" in wrong_candidate_pnu.missing_gates

    wrong_spatial_pnu = _spatial(OTHER_PNU)
    rejected_spatial_pnu = _build(spatial=wrong_spatial_pnu)
    assert rejected_spatial_pnu.status == REJECTED
    assert rejected_spatial_pnu.verified is False

    unverified_candidate = _candidate()
    unverified_candidate["positive_candidate_verified"] = False
    candidate_unknown = _build(candidate=unverified_candidate)
    assert candidate_unknown.status == UNKNOWN
    assert candidate_unknown.applicability_state == UNKNOWN
    assert candidate_unknown.applicability_evidence is None

    forged_candidate_resolution = _candidate()
    forged_candidate_resolution["source_resolution"] = "TRUE_CANDIDATE"
    forged_unknown = _build(candidate=forged_candidate_resolution)
    assert forged_unknown.status == UNKNOWN
    assert forged_unknown.verified is False

    forged_candidate_applicability = _candidate()
    forged_candidate_applicability["parcel_applicability_verified"] = True
    applicability_unknown = _build(candidate=forged_candidate_applicability)
    assert applicability_unknown.status == UNKNOWN
    assert applicability_unknown.verified is False

    unverified_spatial = _spatial()
    unverified_spatial["site_spatial_inclusion_verified"] = False
    spatial_unknown = _build(spatial=unverified_spatial)
    assert spatial_unknown.status == UNKNOWN
    assert spatial_unknown.applicability_evidence is None

    wrong_dataset = _spatial()
    wrong_dataset["dataset"] = "OTHER_DATASET"
    dataset_unknown = _build(spatial=wrong_dataset)
    assert dataset_unknown.status == UNKNOWN

    incomplete_site = _build(site={"identity_status": "INCOMPLETE", "pnu": PNU})
    assert incomplete_site.status == REJECTED

    malformed = build_district_unit_plan_spatial_parcel_applicability_evidence(
        None,
        None,
        None,
    )
    assert malformed.status == REJECTED
    assert malformed.verified is False

    forged_authority_candidate = _candidate()
    forged_authority_candidate["site_promotion_allowed"] = True
    bounded = _build(candidate=forged_authority_candidate)
    assert bounded.verified is True

    for result in (
        verified,
        wrong_candidate_pnu,
        rejected_spatial_pnu,
        candidate_unknown,
        forged_unknown,
        applicability_unknown,
        spatial_unknown,
        dataset_unknown,
        incomplete_site,
        malformed,
        bounded,
    ):
        assert result.site_decision_eligible is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    print("DISTRICT_UNIT_PLAN_SPATIAL_PARCEL_APPLICABILITY_EVIDENCE_CONTRACT_PASS")


if __name__ == "__main__":
    main()
