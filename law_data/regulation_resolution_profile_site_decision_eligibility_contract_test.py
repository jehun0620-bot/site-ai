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
    build_resolver_family_dispatch_plan,
)
from .regulation_resolution_profile_resolver_family_execution import (
    execute_admitted_resolver_family,
)
from .regulation_resolution_profile_site_decision_eligibility import (
    ELIGIBLE,
    INELIGIBLE,
    REJECTED,
    evaluate_site_decision_eligibility,
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


def _chain(*, name: str, condition_type: str, resolution_type: str, resolver_input):
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
    execution = execute_admitted_resolver_family(
        plan,
        resolver_input,
        admitted_profile=profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )
    assert execution.executed
    return seed, evidence, verification, profile, plan, resolver_input, execution


def _eligibility(chain):
    seed, evidence, verification, profile, plan, resolver_input, execution = chain
    return evaluate_site_decision_eligibility(
        execution,
        plan,
        resolver_input,
        admitted_profile=profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    historical_false = _chain(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        resolver_input=HistoricalSiteEventEvidenceState(
            official_history_source_verified=True,
            history_scope_complete_verified=True,
            required_originals_resolved=True,
            candidate_universe_exhaustively_enumerated=True,
            all_candidates_classified_non_target=True,
        ),
    )
    historical_true_candidate = _chain(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        resolver_input=HistoricalSiteEventEvidenceState(
            verified_qualifying_event_present=True,
        ),
    )
    historical_unknown = _chain(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        resolver_input=HistoricalSiteEventEvidenceState(),
    )
    hybrid = _chain(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        resolver_input=HybridSpatialNoticeStageResults(
            designation_identity={"official_designation_identity_verified": True},
            current_validity={"current_validity_verified": True},
            site_spatial_inclusion={"site_spatial_inclusion_verified": True},
        ),
    )

    eligible_false = _eligibility(historical_false)
    assert eligible_false.status == ELIGIBLE
    assert eligible_false.eligible is True
    assert eligible_false.resolver_result_verified is True
    assert eligible_false.resolution == "FALSE"
    assert eligible_false.candidate_site_decision is False
    assert eligible_false.conclusive_for_site_decision is True

    true_candidate = _eligibility(historical_true_candidate)
    assert true_candidate.status == INELIGIBLE
    assert true_candidate.eligible is False
    assert true_candidate.resolver_result_verified is True
    assert true_candidate.resolution == "TRUE_CANDIDATE"
    assert true_candidate.candidate_site_decision is None

    unknown = _eligibility(historical_unknown)
    assert unknown.status == INELIGIBLE
    assert unknown.eligible is False
    assert unknown.resolution == "UNKNOWN"

    hybrid_result = _eligibility(hybrid)
    assert hybrid_result.status == INELIGIBLE
    assert hybrid_result.eligible is False
    assert hybrid_result.resolution == "UNKNOWN"
    assert hybrid[6].resolver_output is not None
    assert hybrid[6].resolver_output["runtime_registration_allowed"] is True

    for result in (eligible_false, true_candidate, unknown, hybrid_result):
        assert result.standard_code_used is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # Exact provenance remains mandatory; execution alone cannot establish eligibility.
    no_provenance = evaluate_site_decision_eligibility(
        historical_false[6],
        historical_false[4],
        historical_false[5],
    )
    assert no_provenance.status == REJECTED
    assert no_provenance.eligible is False

    # Cross-admission provenance fails closed.
    cross_provenance = evaluate_site_decision_eligibility(
        historical_false[6],
        historical_false[4],
        historical_false[5],
        admitted_profile=historical_false[3],
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert cross_provenance.status == REJECTED
    assert cross_provenance.eligible is False

    # A forged STEP110 wrapper cannot create a decision candidate.
    forged_execution = replace(
        historical_true_candidate[6],
        resolver_output={
            **(historical_true_candidate[6].resolver_output or {}),
            "resolution": "FALSE",
            "resolution_basis": "VERIFIED_EXHAUSTIVE_DISPROOF",
        },
    )
    forged = evaluate_site_decision_eligibility(
        forged_execution,
        historical_true_candidate[4],
        historical_true_candidate[5],
        admitted_profile=historical_true_candidate[3],
        seed=historical_true_candidate[0],
        evidence=historical_true_candidate[1],
        verification=historical_true_candidate[2],
    )
    assert forged.status == REJECTED
    assert forged.eligible is False

    # Downstream permission escalation invalidates exact STEP112 reproduction.
    escalated_execution = replace(historical_false[6], site_promotion_allowed=True)
    escalated = evaluate_site_decision_eligibility(
        escalated_execution,
        historical_false[4],
        historical_false[5],
        admitted_profile=historical_false[3],
        seed=historical_false[0],
        evidence=historical_false[1],
        verification=historical_false[2],
    )
    assert escalated.status == REJECTED
    assert escalated.eligible is False

    invalid = evaluate_site_decision_eligibility(
        None,  # type: ignore[arg-type]
        historical_false[4],
        historical_false[5],
        admitted_profile=historical_false[3],
        seed=historical_false[0],
        evidence=historical_false[1],
        verification=historical_false[2],
    )
    assert invalid.status == REJECTED
    assert invalid.eligible is False

    print("STEP114_PROVENANCE_BOUND_SITE_DECISION_ELIGIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
