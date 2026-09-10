from __future__ import annotations

from law_data.regulation_resolution_profile import (
    RegulationResolutionProfile,
    normalize_regulation_resolution_profile,
)


CLASSIFICATION = "STEP19_REGULATION_RESOLUTION_PROFILE_BOUNDARY_PASS"


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def main() -> None:
    unverified = normalize_regulation_resolution_profile(
        name="도시지역편입해제구역",
        condition_type="SITE_HISTORY",
        resolution_type="HISTORICAL_SITE_EVENT",
        standard_code=None,
        standard_code_verified=True,
        authority_requirements=(
            "OFFICIAL_EVENT_IDENTITY_VERIFIED",
            "SITE_HISTORY_COMPLETENESS_VERIFIED",
        ),
        source_policy_requirements=(
            "OFFICIAL_HISTORICAL_NOTICE",
            "SITE_SPECIFIC_EVENT_EVIDENCE",
        ),
    ).to_dict()

    require(
        unverified["standard_code"] is None,
        "unverified historical standard code must remain absent",
    )
    require(
        unverified["standard_code_verified"] is False,
        "missing standard code must not become verified",
    )
    require(
        unverified["production_registration_allowed"] is False,
        "profile metadata must not enable production registration",
    )
    require(
        unverified["runtime_registration_allowed"] is False,
        "profile metadata must not enable runtime registration",
    )
    require(
        "state" not in unverified,
        "resolution profile must not manufacture SITE state",
    )

    constructor_rejected_missing_verified_code = False
    try:
        RegulationResolutionProfile(
            name="synthetic historical condition",
            condition_type="SITE_HISTORY",
            resolution_type="HISTORICAL_SITE_EVENT",
            standard_code=None,
            standard_code_verified=True,
        )
    except ValueError:
        constructor_rejected_missing_verified_code = True

    require(
        constructor_rejected_missing_verified_code,
        "verified standard code without explicit identity must be rejected",
    )

    uqq700 = normalize_regulation_resolution_profile(
        name="개발밀도관리구역",
        condition_type="SITE",
        resolution_type="HYBRID_SPATIAL_NOTICE",
        standard_code="UQQ700",
        standard_code_verified=True,
        authority_requirements=(
            "OFFICIAL_DESIGNATION_IDENTITY_VERIFIED",
            "CURRENT_VALIDITY_VERIFIED",
            "SITE_SPATIAL_INCLUSION_VERIFIED",
        ),
        source_policy_requirements=(
            "OFFICIAL_DESIGNATION_NOTICE",
            "CURRENT_VALIDITY_EVIDENCE",
            "SITE_SPATIAL_EVIDENCE",
        ),
    ).to_dict()

    require(
        uqq700["standard_code"] == "UQQ700",
        "verified UQQ700 identity must be preserved",
    )
    require(
        uqq700["standard_code_verified"] is True,
        "explicit UQQ700 code verification must be preserved",
    )
    require(
        uqq700["resolution_type"] == "HYBRID_SPATIAL_NOTICE",
        "UQQ700 resolution type must remain HYBRID_SPATIAL_NOTICE",
    )
    require(
        uqq700["negative_evidence_allowed"] is False,
        "UQQ700 negative evidence must remain disabled",
    )
    require(
        uqq700["legal_absence_inference_allowed"] is False,
        "UQQ700 legal absence inference must remain disabled",
    )
    require(
        uqq700["site_promotion_allowed"] is False,
        "UQQ700 SITE promotion must remain disabled",
    )
    require(
        uqq700["production_registration_allowed"] is False,
        "UQQ700 profile must not enable production registration",
    )
    require(
        uqq700["runtime_registration_allowed"] is False,
        "UQQ700 profile must not enable runtime registration",
    )
    require(
        "state" not in uqq700,
        "UQQ700 profile metadata must not resolve SITE state",
    )

    fail_closed = normalize_regulation_resolution_profile(
        name="synthetic spatial condition",
        condition_type="SITE",
        resolution_type="SPATIAL",
    ).to_dict()

    require(
        fail_closed["standard_code"] is None,
        "unspecified standard code must remain absent",
    )
    require(
        fail_closed["standard_code_verified"] is False,
        "unspecified standard code must remain unverified",
    )
    require(
        fail_closed["authority_identity_verified"] is False,
        "authority identity must default fail-closed",
    )
    require(
        fail_closed["source_policy_verified"] is False,
        "source policy must default fail-closed",
    )
    require(
        fail_closed["negative_evidence_allowed"] is False,
        "negative evidence must default fail-closed",
    )
    require(
        fail_closed["legal_absence_inference_allowed"] is False,
        "legal absence inference must default fail-closed",
    )
    require(
        fail_closed["site_promotion_allowed"] is False,
        "SITE promotion must default fail-closed",
    )
    require(
        fail_closed["production_registration_allowed"] is False,
        "production registration must default fail-closed",
    )
    require(
        fail_closed["runtime_registration_allowed"] is False,
        "runtime registration must default fail-closed",
    )

    print("=" * 72)
    print("STEP 19 REGULATION RESOLUTION PROFILE BOUNDARY REGRESSION")
    print("=" * 72)
    print("Unverified standard-code guessing: NONE")
    print("Verified-code identity preservation: PASS")
    print("Authority/source-policy defaults: FAIL-CLOSED")
    print("SITE state resolution from profile metadata: NONE")
    print("UQQ700 negative/legal-absence/SITE promotion: DISABLED")
    print("Production/runtime registration from profile metadata: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
