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


def _dispatch_plan(*, name: str, condition_type: str, resolution_type: str):
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
    plan = build_resolver_family_dispatch_plan(profile)
    assert plan.status == PLANNED
    assert plan.planned
    return plan


def main() -> None:
    historical_plan = _dispatch_plan(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    hybrid_plan = _dispatch_plan(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )

    historical_input = HistoricalSiteEventEvidenceState()
    hybrid_input = HybridSpatialNoticeStageResults()

    historical = admit_resolver_family_input(historical_plan, historical_input)
    assert historical.status == ADMITTED
    assert historical.admitted is True
    assert historical.resolver_family == "HISTORICAL_SITE_EVENT"
    assert historical.input_type == "HistoricalSiteEventEvidenceState"

    hybrid = admit_resolver_family_input(hybrid_plan, hybrid_input)
    assert hybrid.status == ADMITTED
    assert hybrid.admitted is True
    assert hybrid.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert hybrid.input_type == "HybridSpatialNoticeStageResults"

    # Cross-family inputs must fail closed.
    cross_historical = admit_resolver_family_input(historical_plan, hybrid_input)
    assert cross_historical.status == REJECTED
    assert cross_historical.admitted is False
    assert cross_historical.family_input_matches is False

    cross_hybrid = admit_resolver_family_input(hybrid_plan, historical_input)
    assert cross_hybrid.status == REJECTED
    assert cross_hybrid.admitted is False
    assert cross_hybrid.family_input_matches is False

    # Admission is still non-executable and grants no SITE/production/runtime authority.
    for result in (historical, hybrid):
        assert result.standard_code_used is False
        assert result.resolver_callable_selected is False
        assert result.resolver_execution_allowed is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # A plan whose fail-closed permissions were escalated is no longer planned.
    escalated_plan = replace(hybrid_plan, resolver_execution_allowed=True)
    escalated = admit_resolver_family_input(escalated_plan, hybrid_input)
    assert escalated.status == REJECTED
    assert escalated.admitted is False

    # A manually forged plan with an unsupported family cannot admit any input.
    unsupported_plan = RegulationResolutionProfileResolverFamilyDispatchPlan(
        status=PLANNED,
        resolver_family="UNSUPPORTED_FAMILY",
        classification_compatible=True,
    )
    unsupported = admit_resolver_family_input(unsupported_plan, hybrid_input)
    assert unsupported.status == REJECTED
    assert unsupported.admitted is False

    # Arbitrary objects and invalid plans cannot cross the boundary.
    arbitrary_input = admit_resolver_family_input(hybrid_plan, {"family": "HYBRID"})
    assert arbitrary_input.status == REJECTED
    assert arbitrary_input.admitted is False

    invalid_plan = admit_resolver_family_input(None, hybrid_input)  # type: ignore[arg-type]
    assert invalid_plan.status == REJECTED
    assert invalid_plan.admitted is False

    print("STEP108_RESOLVER_FAMILY_INPUT_ADMISSION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
