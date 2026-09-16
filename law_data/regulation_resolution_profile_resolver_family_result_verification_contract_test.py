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
from .regulation_resolution_profile_resolver_family_result_verification import (
    REJECTED,
    VERIFIED,
    verify_resolver_family_result,
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


def _verify(chain):
    seed, evidence, verification, profile, plan, resolver_input, execution = chain
    return verify_resolver_family_result(
        execution,
        plan,
        resolver_input,
        admitted_profile=profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    historical_true = _chain(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        resolver_input=HistoricalSiteEventEvidenceState(
            verified_qualifying_event_present=True,
        ),
    )
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

    historical_true_verified = _verify(historical_true)
    assert historical_true_verified.status == VERIFIED
    assert historical_true_verified.verified is True
    assert historical_true_verified.resolution == "TRUE_CANDIDATE"

    historical_false_verified = _verify(historical_false)
    assert historical_false_verified.status == VERIFIED
    assert historical_false_verified.verified is True
    assert historical_false_verified.resolution == "FALSE"

    hybrid_verified = _verify(hybrid)
    assert hybrid_verified.status == VERIFIED
    assert hybrid_verified.verified is True
    assert hybrid_verified.resolution == "UNKNOWN"

    for result in (
        historical_true_verified,
        historical_false_verified,
        hybrid_verified,
    ):
        assert result.standard_code_used is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_readiness_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # Execution result alone cannot authenticate itself without exact provenance.
    execution_only = verify_resolver_family_result(
        hybrid[6],
        hybrid[4],
        hybrid[5],
    )
    assert execution_only.status == REJECTED
    assert execution_only.verified is False

    # Cross-admission provenance fails reproduction of the execution result.
    cross_provenance = verify_resolver_family_result(
        hybrid[6],
        hybrid[4],
        hybrid[5],
        admitted_profile=hybrid[3],
        seed=historical_true[0],
        evidence=historical_true[1],
        verification=historical_true[2],
    )
    assert cross_provenance.status == REJECTED
    assert cross_provenance.verified is False

    # Tampering with family/result identity is rejected.
    forged_output = dict(hybrid[6].resolver_output or {})
    forged_output["resolution_type"] = "HISTORICAL_SITE_EVENT"
    forged_execution = replace(hybrid[6], resolver_output=forged_output)
    forged = verify_resolver_family_result(
        forged_execution,
        hybrid[4],
        hybrid[5],
        admitted_profile=hybrid[3],
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert forged.status == REJECTED
    assert forged.verified is False

    # A resolver-local runtime flag is not downstream registration authority.
    assert hybrid[6].resolver_output is not None
    assert hybrid[6].resolver_output["runtime_registration_allowed"] is True
    assert hybrid_verified.runtime_registration_allowed is False
    assert hybrid_verified.production_registration_allowed is False
    assert hybrid_verified.site_promotion_allowed is False

    # Permission escalation on the STEP110 wrapper invalidates exact reproduction.
    escalated_execution = replace(hybrid[6], site_promotion_allowed=True)
    escalated = verify_resolver_family_result(
        escalated_execution,
        hybrid[4],
        hybrid[5],
        admitted_profile=hybrid[3],
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert escalated.status == REJECTED
    assert escalated.verified is False

    invalid = verify_resolver_family_result(
        None,  # type: ignore[arg-type]
        hybrid[4],
        hybrid[5],
        admitted_profile=hybrid[3],
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert invalid.status == REJECTED
    assert invalid.verified is False

    print("STEP112_PROVENANCE_BOUND_RESOLVER_FAMILY_RESULT_VERIFICATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
