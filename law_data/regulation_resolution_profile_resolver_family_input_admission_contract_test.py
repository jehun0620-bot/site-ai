from __future__ import annotations

from dataclasses import replace

from .historical_site_event_resolver import HistoricalSiteEventEvidenceState
from .hybrid_spatial_notice_orchestrator import HybridSpatialNoticeStageResults
from .legal_condition_catalogue_seed import (
    LegalConditionCatalogueSeed,
    LegalEnumerationProvenance,
)
from .legal_condition_classification_profile_admission import (
    LegalConditionClassificationEvidence,
    admit_verified_classification_to_profile,
    seed_identity_fingerprint,
    verify_classification_evidence,
)
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    PLANNED,
    RegulationResolutionProfileResolverFamilyDispatchPlan,
    build_resolver_family_dispatch_plan,
)
from .regulation_resolution_profile_resolver_family_input_admission import (
    ADMITTED,
    REJECTED,
    admit_resolver_family_input,
)


def _verified_seed(name: str) -> LegalConditionCatalogueSeed:
    return LegalConditionCatalogueSeed(
        condition_name=name,
        legal_basis="국토의 계획 및 이용에 관한 법률",
        provenance=LegalEnumerationProvenance(
            source_family="STATUTE_APPENDIX",
            source_uri="https://example.invalid/statute",
            law_id="TEST-LAW",
            law_version_id="TEST-VERSION",
            effective_date="2026-01-01",
            appendix_id="APPENDIX-1",
            row_id=f"ROW-{name}",
            source_identity_verified=True,
            row_binding_verified=True,
        ),
    )


def _dispatch_admission(*, name: str, condition_type: str, resolution_type: str):
    seed = _verified_seed(name)
    evidence = LegalConditionClassificationEvidence(
        condition_name=seed.condition_name,
        legal_basis=seed.legal_basis,
        seed_fingerprint=seed_identity_fingerprint(seed),
        condition_type=condition_type,
        resolution_type=resolution_type,
        official_source_qualified=True,
        condition_identity_bound=True,
        legal_basis_bound=True,
        classification_statement_bound=True,
        same_source_binding=True,
    )
    verification = verify_classification_evidence(seed, evidence)
    assert verification.verified
    profile = admit_verified_classification_to_profile(seed, evidence, verification)
    plan = build_resolver_family_dispatch_plan(
        profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    assert plan.status == PLANNED
    assert plan.planned
    return seed, evidence, verification, profile, plan


def _admit(admission, resolver_input):
    seed, evidence, verification, profile, plan = admission
    return admit_resolver_family_input(
        plan,
        resolver_input,
        admitted_profile=profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    historical_admission = _dispatch_admission(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    hybrid_admission = _dispatch_admission(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    historical_plan = historical_admission[4]
    hybrid_plan = hybrid_admission[4]

    historical_input = HistoricalSiteEventEvidenceState()
    hybrid_input = HybridSpatialNoticeStageResults()

    historical = _admit(historical_admission, historical_input)
    assert historical.status == ADMITTED
    assert historical.admitted is True
    assert historical.resolver_family == "HISTORICAL_SITE_EVENT"
    assert historical.input_type == "HistoricalSiteEventEvidenceState"

    hybrid = _admit(hybrid_admission, hybrid_input)
    assert hybrid.status == ADMITTED
    assert hybrid.admitted is True
    assert hybrid.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert hybrid.input_type == "HybridSpatialNoticeStageResults"

    cross_historical = _admit(historical_admission, hybrid_input)
    assert cross_historical.status == REJECTED
    assert cross_historical.admitted is False
    assert cross_historical.family_input_matches is False

    cross_hybrid = _admit(hybrid_admission, historical_input)
    assert cross_hybrid.status == REJECTED
    assert cross_hybrid.admitted is False
    assert cross_hybrid.family_input_matches is False

    for result in (historical, hybrid):
        assert result.standard_code_used is False
        assert result.resolver_callable_selected is False
        assert result.resolver_execution_allowed is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # Genuine plan alone is insufficient without the provenance-bearing profile chain.
    plan_only = admit_resolver_family_input(hybrid_plan, hybrid_input)
    assert plan_only.status == REJECTED
    assert plan_only.admitted is False
    assert plan_only.dispatch_plan_verified is False

    escalated_plan = replace(hybrid_plan, resolver_execution_allowed=True)
    escalated = admit_resolver_family_input(
        escalated_plan,
        hybrid_input,
        admitted_profile=hybrid_admission[3],
        seed=hybrid_admission[0],
        evidence=hybrid_admission[1],
        verification=hybrid_admission[2],
    )
    assert escalated.status == REJECTED
    assert escalated.admitted is False

    # Supported-family forged PLANNED plan must not authenticate itself.
    forged_supported = RegulationResolutionProfileResolverFamilyDispatchPlan(
        status=PLANNED,
        resolver_family="HYBRID_SPATIAL_NOTICE",
        classification_compatible=True,
    )
    forged_supported_result = admit_resolver_family_input(
        forged_supported,
        hybrid_input,
    )
    assert forged_supported_result.status == REJECTED
    assert forged_supported_result.admitted is False
    assert forged_supported_result.dispatch_plan_verified is False

    unsupported_plan = RegulationResolutionProfileResolverFamilyDispatchPlan(
        status=PLANNED,
        resolver_family="UNSUPPORTED_FAMILY",
        classification_compatible=True,
    )
    unsupported = admit_resolver_family_input(unsupported_plan, hybrid_input)
    assert unsupported.status == REJECTED
    assert unsupported.admitted is False

    # Cross-admission provenance cannot authenticate another genuine plan.
    cross_provenance = admit_resolver_family_input(
        hybrid_plan,
        hybrid_input,
        admitted_profile=hybrid_admission[3],
        seed=historical_admission[0],
        evidence=historical_admission[1],
        verification=historical_admission[2],
    )
    assert cross_provenance.status == REJECTED
    assert cross_provenance.admitted is False
    assert cross_provenance.dispatch_plan_verified is False

    arbitrary_input = _admit(hybrid_admission, {"family": "HYBRID"})
    assert arbitrary_input.status == REJECTED
    assert arbitrary_input.admitted is False

    invalid_plan = admit_resolver_family_input(None, hybrid_input)  # type: ignore[arg-type]
    assert invalid_plan.status == REJECTED
    assert invalid_plan.admitted is False

    print("STEP108_RESOLVER_FAMILY_INPUT_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
