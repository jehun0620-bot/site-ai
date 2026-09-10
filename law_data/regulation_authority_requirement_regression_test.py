from __future__ import annotations

from law_data.authority_source_scope import AuthoritySourceScope
from law_data.regulation_authority_requirement import (
    evaluate_regulation_authority_requirement,
)
from law_data.regulation_resolution_profile import RegulationResolutionProfile


CLASSIFICATION = "STEP22_REGULATION_AUTHORITY_REQUIREMENT_BOUNDARY_PASS"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def _profile(name: str = "개발밀도관리구역") -> RegulationResolutionProfile:
    return RegulationResolutionProfile(
        name=name,
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        standard_code="UQQ700" if name == "개발밀도관리구역" else None,
        standard_code_verified=name == "개발밀도관리구역",
        authority_requirements=(
            "OFFICIAL DESIGNATION IDENTITY VERIFIED",
            "CURRENT VALIDITY VERIFIED",
        ),
        source_policy_requirements=(
            "SITE SPATIAL INCLUSION VERIFIED",
        ),
        negative_evidence_allowed=False,
        legal_absence_inference_allowed=False,
        site_promotion_allowed=False,
        production_registration_allowed=False,
        runtime_registration_allowed=False,
    )


def main() -> None:
    profile = _profile()

    missing_scope = evaluate_regulation_authority_requirement(
        profile,
        None,
    ).to_dict()
    require(missing_scope["profile_present"] is True, "profile must be present")
    require(
        missing_scope["condition_identity_aligned"] is False,
        "missing scope must not align condition identity",
    )
    require(
        missing_scope["authority_requirement_satisfied"] is False,
        "missing scope must fail closed",
    )

    descriptive_only = evaluate_regulation_authority_requirement(
        profile,
        {
            "source_uri": "https://example.go.kr/notice/1",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획",
            "target_regulation": "개발밀도관리구역",
        },
    ).to_dict()
    require(
        descriptive_only["condition_identity_aligned"] is True,
        "exact condition identity should be descriptively aligned",
    )
    require(
        descriptive_only["authority_chain_verified"] is False,
        "descriptive metadata must not verify authority chain",
    )
    require(
        descriptive_only["authority_requirement_satisfied"] is False,
        "descriptive metadata must not satisfy authority requirement",
    )

    explicit_partial = evaluate_regulation_authority_requirement(
        profile,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="도시계획",
            legal_authority_scope_verified=True,
            target_regulation="개발밀도관리구역",
            target_regulation_compatible=True,
            target_regulation_compatibility_verified=False,
        ),
    ).to_dict()
    require(
        explicit_partial["authority_chain_verified"] is False,
        "unverified regulation compatibility must block authority chain",
    )
    require(
        explicit_partial["authority_requirement_satisfied"] is False,
        "partial explicit verification must remain blocked",
    )

    verified_incompatible = evaluate_regulation_authority_requirement(
        profile,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="도시계획",
            legal_authority_scope_verified=True,
            target_regulation="개발밀도관리구역",
            target_regulation_compatible=False,
            target_regulation_compatibility_verified=True,
        ),
    ).to_dict()
    require(
        verified_incompatible["authority_chain_verified"] is False,
        "verified incompatibility must not verify positive authority chain",
    )
    require(
        verified_incompatible["authority_requirement_satisfied"] is False,
        "verified incompatibility must not satisfy authority requirement",
    )

    wrong_target = evaluate_regulation_authority_requirement(
        profile,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="도시계획",
            legal_authority_scope_verified=True,
            target_regulation="다른 규제",
            target_regulation_compatible=True,
            target_regulation_compatibility_verified=True,
        ),
    ).to_dict()
    require(
        wrong_target["authority_chain_verified"] is True,
        "scope may be internally verified for its own explicit target",
    )
    require(
        wrong_target["condition_identity_aligned"] is False,
        "different target regulation must not align with profile",
    )
    require(
        wrong_target["authority_requirement_satisfied"] is False,
        "verified authority for another target must not satisfy this profile",
    )

    fully_verified = evaluate_regulation_authority_requirement(
        profile,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="도시계획",
            legal_authority_scope_verified=True,
            target_regulation="개발밀도관리구역",
            target_regulation_compatible=True,
            target_regulation_compatibility_verified=True,
        ),
    ).to_dict()
    require(
        fully_verified["authority_chain_verified"] is True,
        "all explicit positive scope gates must verify authority chain",
    )
    require(
        fully_verified["authority_requirement_satisfied"] is True,
        "matching profile plus explicit verified positive authority chain must satisfy authority requirement",
    )
    require(
        fully_verified["source_policy_requirements"]
        == ["SITE SPATIAL INCLUSION VERIFIED"],
        "source-policy requirements must be preserved diagnostically",
    )
    require(
        "site_state" not in fully_verified and "state" not in fully_verified,
        "authority requirement boundary must not manufacture SITE state",
    )
    require(
        "runtime_registration_allowed" not in fully_verified,
        "authority assessment must not manufacture runtime registration permission",
    )
    require(
        "production_registration_allowed" not in fully_verified,
        "authority assessment must not manufacture production registration permission",
    )

    absent_profile = evaluate_regulation_authority_requirement(
        None,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="도시계획",
            legal_authority_scope_verified=True,
            target_regulation="개발밀도관리구역",
            target_regulation_compatible=True,
            target_regulation_compatibility_verified=True,
        ),
    ).to_dict()
    require(
        absent_profile["profile_present"] is False,
        "missing profile must remain absent",
    )
    require(
        absent_profile["authority_requirement_satisfied"] is False,
        "verified scope without profile must fail closed",
    )

    no_declared_authority_requirement = RegulationResolutionProfile(
        name="synthetic condition",
        condition_type="SITE",
        resolution_type="SPATIAL",
        authority_requirements=(),
        source_policy_requirements=("SYNTHETIC SOURCE REQUIREMENT",),
    )
    no_requirement = evaluate_regulation_authority_requirement(
        no_declared_authority_requirement,
        AuthoritySourceScope(
            source_uri="https://example.go.kr/notice/1",
            source_host="example.go.kr",
            official_host_verified=True,
            region_binding="서울특별시",
            region_binding_verified=True,
            source_role="PRIMARY",
            source_role_verified=True,
            legal_authority_scope="synthetic",
            legal_authority_scope_verified=True,
            target_regulation="synthetic condition",
            target_regulation_compatible=True,
            target_regulation_compatibility_verified=True,
        ),
    ).to_dict()
    require(
        no_requirement["authority_requirements_declared"] is False,
        "empty authority requirement declaration must stay explicit",
    )
    require(
        no_requirement["authority_requirement_satisfied"] is False,
        "absence of declared authority requirement must not become implicit satisfaction",
    )

    print("=" * 78)
    print("STEP 22 REGULATION AUTHORITY REQUIREMENT BOUNDARY REGRESSION")
    print("=" * 78)
    print("Profile/scope descriptive identity match -> authority verification: NONE")
    print("Official-looking host / PRIMARY / authority text promotion: NONE")
    print("Partial or incompatible authority chain promotion: NONE")
    print("Cross-regulation verified authority reuse: BLOCKED")
    print("Positive requirement satisfaction: EXPLICIT VERIFIED MATCHING CHAIN ONLY")
    print("Source-policy requirement auto-satisfaction: NONE")
    print("SITE/production/runtime mutation semantics: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
