from __future__ import annotations

from law_data.regulation_resolution_profile_registry import (
    UQQ700_CONDITION_NAME,
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
)
from law_data.urban_area_conversion_production_readiness_adapter import (
    adapt_urban_area_conversion_production_readiness,
)


CLASSIFICATION = "STEP19_REGULATION_RESOLUTION_PROFILE_READINESS_INTEGRATION_PASS"


def require(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)


def main() -> None:
    print("=" * 72)
    print("STEP 19 REGULATION RESOLUTION PROFILE READINESS INTEGRATION REGRESSION")
    print("=" * 72)

    historical_profile = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical_profile is not None, "historical profile lookup failed")
    require(
        historical_profile.standard_code is None,
        "historical standard code must remain absent",
    )
    require(
        historical_profile.standard_code_verified is False,
        "historical standard code must remain unverified",
    )

    result = adapt_urban_area_conversion_production_readiness()
    readiness = result.get("readiness")
    require(isinstance(readiness, dict), "readiness payload missing")
    gates = readiness.get("gates")
    require(isinstance(gates, dict), "readiness gates missing")

    require(
        gates.get("condition_identity_verified") is True,
        "exact-name profile identity should be preserved",
    )
    require(
        gates.get("standard_code_verified") is False,
        "unverified standard code was promoted",
    )
    require(
        gates.get("positive_evidence_contract_ready") is True,
        "existing positive-evidence contract readiness changed",
    )
    require(
        gates.get("history_completeness_contract_ready") is True,
        "existing history-completeness contract readiness changed",
    )
    require(
        gates.get("provenance_policy_verified") is False,
        "profile presence promoted provenance verification",
    )
    require(
        gates.get("runtime_registration_policy_verified") is False,
        "profile presence promoted runtime policy verification",
    )
    require(
        readiness.get("production_wiring_ready") is False,
        "historical readiness unexpectedly became ready",
    )
    require(
        readiness.get("readiness_state") == "BLOCKED",
        "historical readiness must remain BLOCKED",
    )
    require(
        readiness.get("negative_evidence_inference_allowed") is False,
        "negative evidence inference enabled",
    )
    require(
        readiness.get("legal_absence_inference_allowed") is False,
        "legal absence inference enabled",
    )
    require(
        readiness.get("production_wiring_applied") is False,
        "production wiring was applied",
    )
    require(
        readiness.get("overlay_mutated") is False,
        "SITE overlay was mutated",
    )
    require(
        readiness.get("runtime_registry_mutated") is False,
        "runtime registry was mutated",
    )

    profile_payload = result.get("resolution_profile")
    require(isinstance(profile_payload, dict), "profile diagnostic payload missing")
    require(
        profile_payload.get("standard_code") is None,
        "adapter diagnostic guessed historical standard code",
    )
    require(
        profile_payload.get("standard_code_verified") is False,
        "adapter diagnostic promoted historical standard code",
    )
    require("state" not in profile_payload, "profile manufactured SITE state")
    require(
        profile_payload.get("production_registration_allowed") is False,
        "profile enabled production registration",
    )
    require(
        profile_payload.get("runtime_registration_allowed") is False,
        "profile enabled runtime registration",
    )

    blockers = result.get("condition_specific_blockers")
    require(isinstance(blockers, dict), "condition-specific blockers missing")
    require(blockers.get("profile_missing") is False, "known profile marked missing")
    require(
        blockers.get("standard_code_unverified") is True,
        "standard-code blocker must remain active",
    )

    uqq700 = get_regulation_resolution_profile(UQQ700_CONDITION_NAME)
    require(uqq700 is not None, "UQQ700 profile missing")
    require(uqq700.standard_code == "UQQ700", "UQQ700 code identity changed")
    require(
        uqq700.resolution_type == "HYBRID_SPATIAL_NOTICE",
        "UQQ700 resolution type changed",
    )
    require(
        uqq700.runtime_registration_allowed is False,
        "UQQ700 profile enabled runtime registration",
    )
    require(
        result.get("condition") == URBAN_AREA_CONVERSION_CONDITION_NAME,
        "historical readiness adapter crossed into UQQ700 condition",
    )

    for key in (
        "output_written",
        "production_wiring_applied",
        "overlay_mutated",
        "runtime_registry_mutated",
    ):
        require(result.get(key) is False, f"mutation guard changed: {key}")

    print("Historical profile exact-name integration: PASS")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Historical production readiness: BLOCKED")
    print("Profile metadata -> evidence verification promotion: NONE")
    print("UQQ700 cross-condition readiness/runtime wiring: NONE")
    print("Resolver/SITE/runtime mutation: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
