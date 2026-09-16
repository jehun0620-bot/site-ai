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
from .regulation_resolution_profile_resolver_family_dispatch_plan import (
    PLANNED,
    REJECTED,
    SUPPORTED_RESOLVER_FAMILIES,
    build_resolver_family_dispatch_plan,
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


def _plan(admission):
    seed, evidence, verification, profile = admission
    return build_resolver_family_dispatch_plan(
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
    hybrid_plan = _plan(hybrid)
    assert hybrid_plan.status == PLANNED
    assert hybrid_plan.planned is True
    assert hybrid_plan.resolver_family == "HYBRID_SPATIAL_NOTICE"

    district_unit_plan = _admission(
        name="지구단위계획",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    district_unit_plan_dispatch = _plan(district_unit_plan)
    assert district_unit_plan_dispatch.status == PLANNED
    assert district_unit_plan_dispatch.planned is True
    assert district_unit_plan_dispatch.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert district_unit_plan[3].standard_code is None
    assert district_unit_plan_dispatch.standard_code_used is False

    historical = _admission(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    historical_plan = _plan(historical)
    assert historical_plan.status == PLANNED
    assert historical_plan.planned is True
    assert historical_plan.resolver_family == "HISTORICAL_SITE_EVENT"

    assert SUPPORTED_RESOLVER_FAMILIES == {
        "HYBRID_SPATIAL_NOTICE",
        "HISTORICAL_SITE_EVENT",
    }

    for plan in (hybrid_plan, district_unit_plan_dispatch, historical_plan):
        assert plan.standard_code_used is False
        assert plan.resolver_callable_selected is False
        assert plan.resolver_input_built is False
        assert plan.resolver_execution_allowed is False
        assert plan.site_truth_decision_allowed is False
        assert plan.site_promotion_allowed is False
        assert plan.production_registration_allowed is False
        assert plan.runtime_registration_allowed is False

    # A genuine profile without its exact provenance artifacts is insufficient.
    hybrid_profile_only = build_resolver_family_dispatch_plan(hybrid[3])
    assert hybrid_profile_only.status == REJECTED
    assert hybrid_profile_only.planned is False

    builtin = get_regulation_resolution_profile("개발밀도관리구역")
    assert builtin is not None
    builtin_plan = build_resolver_family_dispatch_plan(builtin)
    assert builtin_plan.status == REJECTED
    assert builtin_plan.planned is False

    wrong = _admission(
        name="개발밀도관리구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    wrong_plan = _plan(wrong)
    assert wrong_plan.status == REJECTED
    assert wrong_plan.planned is False

    unknown = _admission(
        name="미등록조건",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    unknown_plan = _plan(unknown)
    assert unknown_plan.status == REJECTED
    assert unknown_plan.planned is False

    # Cross-admission provenance cannot be reused with another genuine profile.
    cross_plan = build_resolver_family_dispatch_plan(
        hybrid[3],
        seed=historical[0],
        evidence=historical[1],
        verification=historical[2],
    )
    assert cross_plan.status == REJECTED
    assert cross_plan.planned is False

    escalated = replace(hybrid[3], runtime_registration_allowed=True)
    escalated_plan = build_resolver_family_dispatch_plan(
        escalated,
        seed=hybrid[0],
        evidence=hybrid[1],
        verification=hybrid[2],
    )
    assert escalated_plan.status == REJECTED
    assert escalated_plan.planned is False
    assert escalated_plan.runtime_registration_allowed is False

    forged = RegulationResolutionProfile(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        diagnostics=dict(hybrid[3].diagnostics),
    )
    forged_without_artifacts = build_resolver_family_dispatch_plan(forged)
    assert forged_without_artifacts.status == REJECTED
    assert forged_without_artifacts.planned is False

    invalid_plan = build_resolver_family_dispatch_plan(None)  # type: ignore[arg-type]
    assert invalid_plan.status == REJECTED
    assert invalid_plan.planned is False
    assert invalid_plan.resolver_family is None

    print("STEP106_VERIFIED_RESOLVER_FAMILY_DISPATCH_PLAN_CONTRACT_PASS")


if __name__ == "__main__":
    main()
