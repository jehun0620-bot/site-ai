from __future__ import annotations

from dataclasses import replace

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
from .regulation_resolution_profile import RegulationResolutionProfile
from .regulation_resolution_profile_registry import get_regulation_resolution_profile
from .regulation_resolution_profile_resolver_family_eligibility import (
    ELIGIBLE,
    REJECTED,
    evaluate_resolver_family_eligibility,
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


def _admission(*, name: str, condition_type: str, resolution_type: str):
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
    return seed, evidence, verification, profile


def _evaluate(admission):
    seed, evidence, verification, profile = admission
    return evaluate_resolver_family_eligibility(
        profile,
        seed=seed,
        evidence=evidence,
        verification=verification,
    )


def main() -> None:
    hybrid = _admission(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    hybrid_result = _evaluate(hybrid)
    assert hybrid_result.status == ELIGIBLE
    assert hybrid_result.eligible is True
    assert hybrid_result.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert hybrid_result.standard_code_used is False
    assert hybrid[3].standard_code is None

    district_unit_plan = _admission(
        name="지구단위계획",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    district_unit_plan_result = _evaluate(district_unit_plan)
    assert district_unit_plan_result.status == ELIGIBLE
    assert district_unit_plan_result.eligible is True
    assert district_unit_plan_result.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert district_unit_plan_result.standard_code_used is False
    assert district_unit_plan[3].standard_code is None

    historical = _admission(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    historical_result = _evaluate(historical)
    assert historical_result.status == ELIGIBLE
    assert historical_result.eligible is True
    assert historical_result.resolver_family == "HISTORICAL_SITE_EVENT"

    for result in (hybrid_result, district_unit_plan_result, historical_result):
        assert result.resolver_execution_allowed is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # Profile-only use no longer carries STEP101 provenance and fails closed.
    profile_only = evaluate_resolver_family_eligibility(hybrid[3])
    assert profile_only.status == REJECTED
    assert profile_only.eligible is False

    unknown = _admission(
        name="미등록조건",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    assert _evaluate(unknown).status == REJECTED

    wrong = _admission(
        name="개발밀도관리구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    assert _evaluate(wrong).status == REJECTED

    builtin = get_regulation_resolution_profile("개발밀도관리구역")
    assert builtin is not None
    builtin_result = evaluate_resolver_family_eligibility(builtin)
    assert builtin_result.status == REJECTED

    forged = RegulationResolutionProfile(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        standard_code=None,
        standard_code_verified=False,
        diagnostics=dict(hybrid[3].diagnostics),
    )
    forged_result = evaluate_resolver_family_eligibility(forged)
    assert forged_result.status == REJECTED

    # Exact profile with another admission's provenance must not cross-bind.
    cross = evaluate_resolver_family_eligibility(
        hybrid[3],
        seed=historical[0],
        evidence=historical[1],
        verification=historical[2],
    )
    assert cross.status == REJECTED
    assert cross.eligible is False

    escalated = replace(hybrid[3], runtime_registration_allowed=True)
    escalated_result = evaluate_resolver_family_eligibility(
        escalated,
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert escalated_result.status == REJECTED
    assert escalated_result.runtime_registration_allowed is False

    invalid_result = evaluate_resolver_family_eligibility(None)  # type: ignore[arg-type]
    assert invalid_result.status == REJECTED
    assert invalid_result.resolver_family is None

    print("STEP104_VERIFIED_PROFILE_RESOLVER_FAMILY_ELIGIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
