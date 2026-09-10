from __future__ import annotations

from law_data.regulation_resolution_profile_registry import (
    BUILTIN_REGULATION_RESOLUTION_PROFILES,
    UQQ700_CONDITION_NAME,
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
    list_regulation_resolution_profiles,
)


CLASSIFICATION = "STEP19_REGULATION_RESOLUTION_PROFILE_REGISTRY_PASS"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    print("=" * 60)
    print("STEP 19 REGULATION RESOLUTION PROFILE REGISTRY REGRESSION")
    print("=" * 60)

    uqq700 = get_regulation_resolution_profile(UQQ700_CONDITION_NAME)
    require(uqq700 is not None, "UQQ700 profile missing")
    require(uqq700.standard_code == "UQQ700", "UQQ700 standard code changed")
    require(uqq700.standard_code_verified is True, "UQQ700 code identity not verified")
    require(
        uqq700.resolution_type == "HYBRID_SPATIAL_NOTICE",
        "UQQ700 resolution type changed",
    )
    require(uqq700.negative_evidence_allowed is False, "UQQ700 negative evidence enabled")
    require(
        uqq700.legal_absence_inference_allowed is False,
        "UQQ700 legal absence inference enabled",
    )
    require(uqq700.site_promotion_allowed is False, "UQQ700 SITE promotion enabled")
    require(
        uqq700.production_registration_allowed is False,
        "UQQ700 production registration enabled",
    )
    require(
        uqq700.runtime_registration_allowed is False,
        "UQQ700 runtime registration enabled",
    )

    historical = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical is not None, "historical profile missing")
    require(
        historical.resolution_type == "HISTORICAL_SITE_EVENT",
        "historical resolution type changed",
    )
    require(
        historical.standard_code is None,
        "historical standard code must remain absent",
    )
    require(
        historical.standard_code_verified is False,
        "historical standard code must remain unverified",
    )
    require(
        historical.negative_evidence_allowed is False,
        "historical negative evidence enabled",
    )
    require(
        historical.legal_absence_inference_allowed is False,
        "historical legal absence inference enabled",
    )
    require(
        historical.site_promotion_allowed is False,
        "historical SITE promotion enabled",
    )
    require(
        historical.production_registration_allowed is False,
        "historical production registration enabled",
    )
    require(
        historical.runtime_registration_allowed is False,
        "historical runtime registration enabled",
    )

    require(get_regulation_resolution_profile("") is None, "empty name inferred")
    require(
        get_regulation_resolution_profile("개발밀도관리구역 ") is None,
        "trimmed alias unexpectedly resolved",
    )
    require(
        get_regulation_resolution_profile("UNKNOWN_CONDITION") is None,
        "unknown condition unexpectedly resolved",
    )
    require(
        get_regulation_resolution_profile("UQQ700") is None,
        "standard code must not act as condition-name alias",
    )

    profiles = list_regulation_resolution_profiles()
    require(len(profiles) == 2, "unexpected built-in profile count")
    require(isinstance(profiles, tuple), "profile list must be immutable tuple")

    mutation_blocked = False
    try:
        BUILTIN_REGULATION_RESOLUTION_PROFILES["MUTATION"] = uqq700  # type: ignore[index]
    except TypeError:
        mutation_blocked = True
    require(mutation_blocked, "registry mapping is mutable")

    import law_data.regulation_resolution_profile_registry as registry

    for forbidden_name in (
        "register",
        "register_profile",
        "update",
        "update_profile",
        "resolve",
        "evaluate",
        "promote",
        "register_runtime",
    ):
        require(
            not hasattr(registry, forbidden_name),
            f"forbidden mutation/runtime surface present: {forbidden_name}",
        )

    for profile in profiles:
        payload = profile.to_dict()
        require("state" not in payload, "profile must not manufacture SITE state")
        require("site_state" not in payload, "profile must not manufacture SITE state")
        require("resolver_result" not in payload, "profile must not manufacture resolver result")
        require(
            payload["production_registration_allowed"] is False,
            "profile unexpectedly allows production registration",
        )
        require(
            payload["runtime_registration_allowed"] is False,
            "profile unexpectedly allows runtime registration",
        )

    print("UQQ700 exact-name profile lookup: PASS")
    print("UQQ700 safety permissions: ALL DISABLED")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Unknown/alias/code lookup inference: NONE")
    print("Registry mutation surface: NONE")
    print("SITE state/resolver/runtime semantics: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
