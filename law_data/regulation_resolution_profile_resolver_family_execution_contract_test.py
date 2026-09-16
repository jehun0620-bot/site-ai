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
from .regulation_resolution_profile_resolver_family_execution import (
    EXECUTED,
    REJECTED,
    execute_admitted_resolver_family,
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


def _execution_chain(*, name: str, condition_type: str, resolution_type: str):
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
    assert plan.planned
    return seed, evidence, verification, profile, plan


def _execute(chain, resolver_input):
    seed, evidence, verification, profile, plan = chain
    return execute_admitted_resolver_family(
        plan,
        resolver_input,
        admitted_profile=profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    historical_chain = _execution_chain(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    hybrid_chain = _execution_chain(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )

    historical = _execute(
        historical_chain,
        HistoricalSiteEventEvidenceState(verified_qualifying_event_present=True),
    )
    assert historical.status == EXECUTED
    assert historical.executed is True
    assert historical.resolver_family == "HISTORICAL_SITE_EVENT"
    assert historical.resolver_output is not None
    assert historical.resolver_output["resolution_type"] == "HISTORICAL_SITE_EVENT"
    assert historical.resolver_output["resolution"] == "TRUE_CANDIDATE"
    assert historical.resolver_output["automatic_true_promotion_allowed"] is False
    assert historical.resolver_output["production_wiring_applied"] is False
    assert historical.resolver_output["runtime_registry_mutated"] is False

    hybrid_input = HybridSpatialNoticeStageResults(
        designation_identity={"official_designation_identity_verified": True},
        current_validity={"current_validity_verified": True},
        site_spatial_inclusion={"site_spatial_inclusion_verified": True},
    )
    hybrid = _execute(hybrid_chain, hybrid_input)
    assert hybrid.status == EXECUTED
    assert hybrid.executed is True
    assert hybrid.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert hybrid.resolver_output is not None
    assert hybrid.resolver_output["resolution_type"] == "HYBRID_SPATIAL_NOTICE"

    for result in (historical, hybrid):
        assert result.standard_code_used is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # A genuine plan without the exact provenance-bearing chain cannot execute.
    plan_only = execute_admitted_resolver_family(hybrid_chain[4], hybrid_input)
    assert plan_only.status == REJECTED
    assert plan_only.executed is False

    # Family-crossed input is rejected before any resolver call.
    cross_input = _execute(hybrid_chain, HistoricalSiteEventEvidenceState())
    assert cross_input.status == REJECTED
    assert cross_input.executed is False

    # Cross-admission provenance cannot authenticate another genuine plan.
    cross_provenance = execute_admitted_resolver_family(
        hybrid_chain[4],
        hybrid_input,
        admitted_profile=hybrid_chain[3],
        seed=historical_chain[0],
        evidence=historical_chain[1],
        verification=historical_chain[2],
    )
    assert cross_provenance.status == REJECTED
    assert cross_provenance.executed is False

    # A supported-family forged PLANNED plan cannot authenticate itself.
    forged_plan = RegulationResolutionProfileResolverFamilyDispatchPlan(
        status=PLANNED,
        resolver_family="HYBRID_SPATIAL_NOTICE",
        classification_compatible=True,
    )
    forged = execute_admitted_resolver_family(forged_plan, hybrid_input)
    assert forged.status == REJECTED
    assert forged.executed is False

    escalated_plan = replace(hybrid_chain[4], resolver_execution_allowed=True)
    escalated = execute_admitted_resolver_family(
        escalated_plan,
        hybrid_input,
        admitted_profile=hybrid_chain[3],
        seed=hybrid_chain[0],
        evidence=hybrid_chain[1],
        verification=hybrid_chain[2],
    )
    assert escalated.status == REJECTED
    assert escalated.executed is False

    arbitrary = _execute(hybrid_chain, {"resolver": "HYBRID_SPATIAL_NOTICE"})
    assert arbitrary.status == REJECTED
    assert arbitrary.executed is False

    invalid = execute_admitted_resolver_family(None, hybrid_input)  # type: ignore[arg-type]
    assert invalid.status == REJECTED
    assert invalid.executed is False

    print("STEP110_PROVENANCE_BOUND_RESOLVER_FAMILY_EXECUTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
