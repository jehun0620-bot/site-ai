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
from .regulation_resolution_profile_registry import (
    get_regulation_resolution_profile,
)
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


def _admitted_profile(
    *,
    name: str,
    condition_type: str,
    resolution_type: str,
) -> RegulationResolutionProfile:
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
    return admit_verified_classification_to_profile(seed, evidence, verification)


def main() -> None:
    hybrid = _admitted_profile(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    hybrid_result = evaluate_resolver_family_eligibility(hybrid)
    assert hybrid_result.status == ELIGIBLE
    assert hybrid_result.eligible is True
    assert hybrid_result.resolver_family == "HYBRID_SPATIAL_NOTICE"
    assert hybrid_result.standard_code_used is False
    assert hybrid.standard_code is None

    historical = _admitted_profile(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    historical_result = evaluate_resolver_family_eligibility(historical)
    assert historical_result.status == ELIGIBLE
    assert historical_result.eligible is True
    assert historical_result.resolver_family == "HISTORICAL_SITE_EVENT"
    assert historical_result.standard_code_used is False
    assert historical.standard_code is None

    # Eligibility never grants execution, SITE truth, promotion, or registration.
    for result in (hybrid_result, historical_result):
        assert result.resolver_execution_allowed is False
        assert result.site_truth_decision_allowed is False
        assert result.site_promotion_allowed is False
        assert result.production_registration_allowed is False
        assert result.runtime_registration_allowed is False

    # Unknown exact name has no compatible registry baseline and fails closed.
    unknown = _admitted_profile(
        name="미등록조건",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
    )
    unknown_result = evaluate_resolver_family_eligibility(unknown)
    assert unknown_result.status == REJECTED
    assert unknown_result.eligible is False
    assert unknown_result.resolver_family is None

    # Wrong classification for a known name fails STEP103 compatibility.
    wrong = _admitted_profile(
        name="개발밀도관리구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
    )
    wrong_result = evaluate_resolver_family_eligibility(wrong)
    assert wrong_result.status == REJECTED
    assert wrong_result.eligible is False
    assert wrong_result.resolver_family is None

    # Built-in registry data alone is not verified admission evidence.
    builtin = get_regulation_resolution_profile("개발밀도관리구역")
    assert builtin is not None
    builtin_result = evaluate_resolver_family_eligibility(builtin)
    assert builtin_result.status == REJECTED
    assert builtin_result.eligible is False
    assert builtin_result.resolver_family is None

    # Forged admission diagnostics without exact STEP101 fingerprints fail closed.
    forged = RegulationResolutionProfile(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        standard_code=None,
        standard_code_verified=False,
        diagnostics={"classification_admission": "VERIFIED"},
    )
    forged_result = evaluate_resolver_family_eligibility(forged)
    assert forged_result.status == REJECTED
    assert forged_result.eligible is False

    # Permission escalation invalidates the admitted-profile shape through STEP103.
    escalated = replace(hybrid, runtime_registration_allowed=True)
    escalated_result = evaluate_resolver_family_eligibility(escalated)
    assert escalated_result.status == REJECTED
    assert escalated_result.eligible is False
    assert escalated_result.runtime_registration_allowed is False

    # Non-profile input is rejected without exception or inference.
    invalid_result = evaluate_resolver_family_eligibility(None)  # type: ignore[arg-type]
    assert invalid_result.status == REJECTED
    assert invalid_result.eligible is False
    assert invalid_result.resolver_family is None

    print("STEP104_VERIFIED_PROFILE_RESOLVER_FAMILY_ELIGIBILITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
