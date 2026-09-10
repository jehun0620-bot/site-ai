from __future__ import annotations

from pathlib import Path

from law_data.regulation_resolution_profile_registry import (
    BUILTIN_REGULATION_RESOLUTION_PROFILES,
    UQQ700_CONDITION_NAME,
    URBAN_AREA_CONVERSION_CONDITION_NAME,
    get_regulation_resolution_profile,
    list_regulation_resolution_profiles,
)
from law_data.urban_area_conversion_production_readiness_adapter import (
    adapt_urban_area_conversion_production_readiness,
)


CLASSIFICATION = (
    "STEP19_REGULATION_RESOLUTION_PROFILE_BOUNDARY_TERMINALLY_RECONCILED"
)
ROOT = Path(__file__).resolve().parent.parent


def require(condition: bool, label: str) -> None:
    if not condition:
        raise AssertionError(label)


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def main() -> None:
    print("=" * 72)
    print("STEP 19 REGULATION RESOLUTION PROFILE BOUNDARY TERMINAL AUDIT")
    print("=" * 72)

    profiles = list_regulation_resolution_profiles()
    require(isinstance(profiles, tuple), "profile snapshot must be immutable tuple")
    require(len(profiles) == 2, "unexpected built-in profile count")

    mutation_blocked = False
    try:
        BUILTIN_REGULATION_RESOLUTION_PROFILES["MUTATION"] = profiles[0]  # type: ignore[index]
    except TypeError:
        mutation_blocked = True
    require(mutation_blocked, "profile registry mapping must remain immutable")

    require(get_regulation_resolution_profile("") is None, "empty name inferred")
    require(
        get_regulation_resolution_profile("개발밀도관리구역 ") is None,
        "trimmed alias unexpectedly resolved",
    )
    require(
        get_regulation_resolution_profile("UQQ700") is None,
        "standard code unexpectedly acts as condition-name alias",
    )
    require(
        get_regulation_resolution_profile("UNKNOWN_CONDITION") is None,
        "unknown condition unexpectedly synthesized a profile",
    )

    uqq700 = get_regulation_resolution_profile(UQQ700_CONDITION_NAME)
    require(uqq700 is not None, "UQQ700 profile missing")
    require(uqq700.condition_type == "SITE", "UQQ700 condition type changed")
    require(
        uqq700.resolution_type == "HYBRID_SPATIAL_NOTICE",
        "UQQ700 resolution type changed",
    )
    require(uqq700.standard_code == "UQQ700", "UQQ700 standard code changed")
    require(
        uqq700.standard_code_verified is True,
        "UQQ700 standard-code identity verification changed",
    )
    require(
        uqq700.authority_identity_verified is False,
        "UQQ700 authority identity was promoted",
    )
    require(
        uqq700.source_policy_verified is False,
        "UQQ700 source policy was promoted",
    )
    require(
        uqq700.negative_evidence_allowed is False,
        "UQQ700 negative evidence permission enabled",
    )
    require(
        uqq700.legal_absence_inference_allowed is False,
        "UQQ700 legal absence inference enabled",
    )
    require(
        uqq700.site_promotion_allowed is False,
        "UQQ700 SITE promotion enabled",
    )
    require(
        uqq700.production_registration_allowed is False,
        "UQQ700 production registration enabled",
    )
    require(
        uqq700.runtime_registration_allowed is False,
        "UQQ700 runtime registration enabled",
    )
    uqq700_payload = uqq700.to_dict()
    require("state" not in uqq700_payload, "UQQ700 profile manufactured SITE state")
    require(
        "resolver_result" not in uqq700_payload,
        "UQQ700 profile manufactured resolver result",
    )

    historical = get_regulation_resolution_profile(
        URBAN_AREA_CONVERSION_CONDITION_NAME
    )
    require(historical is not None, "historical profile missing")
    require(
        historical.condition_type == "SITE_HISTORY",
        "historical condition type changed",
    )
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
        historical.production_registration_allowed is False,
        "historical production registration enabled",
    )
    require(
        historical.runtime_registration_allowed is False,
        "historical runtime registration enabled",
    )

    readiness_result = adapt_urban_area_conversion_production_readiness()
    readiness = readiness_result.get("readiness")
    require(isinstance(readiness, dict), "historical readiness payload missing")
    require(
        readiness.get("readiness_state") == "BLOCKED",
        "historical readiness must remain BLOCKED",
    )
    require(
        readiness.get("production_wiring_ready") is False,
        "historical production wiring unexpectedly became ready",
    )
    require(
        readiness_result.get("production_wiring_applied") is False,
        "historical production wiring was applied",
    )
    require(
        readiness_result.get("overlay_mutated") is False,
        "historical SITE overlay was mutated",
    )
    require(
        readiness_result.get("runtime_registry_mutated") is False,
        "historical runtime registry was mutated",
    )

    spatial_evaluator = read_text("law_data/spatial_condition_evaluator.py")
    require(
        "SPATIAL_CONDITION_REGISTRY" in spatial_evaluator,
        "runtime spatial registry missing",
    )
    require(
        "regulation_resolution_profile_registry" not in spatial_evaluator,
        "profile registry must not be wired into runtime spatial evaluator",
    )

    builder = read_text("law_data/site_analysis_builder.py")
    service = read_text("site_data/site_analysis_service.py")
    orchestrator = read_text("site_data/site_analysis_orchestrator.py")
    response = read_text("site_data/site_analysis_response.py")

    for label, text in (
        ("builder", builder),
        ("service", service),
        ("orchestrator", orchestrator),
        ("public response", response),
    ):
        require(
            "regulation_resolution_profile_registry" not in text,
            f"profile registry unexpectedly wired into {label}",
        )

    registry_module = read_text("law_data/regulation_resolution_profile_registry.py")
    for forbidden_surface in (
        "def register_",
        "def update_",
        "def resolve_",
        "def evaluate_",
        "def promote_",
        "def register_runtime",
    ):
        require(
            forbidden_surface not in registry_module,
            f"forbidden executable/mutation surface present: {forbidden_surface}",
        )

    print("Profile contract SITE-state manufacture: NONE")
    print("Immutable exact-name registry boundary: PASS")
    print("Unknown/alias/code inference: NONE")
    print("Historical standard code: ABSENT / UNVERIFIED")
    print("Historical production readiness: BLOCKED")
    print("UQQ700 identity/profile safety locks: PRESERVED")
    print("Profile registry -> spatial runtime registry wiring: NONE")
    print("Builder/service/orchestrator/public API auto-wiring: NONE")
    print("Resolver/SITE/runtime mutation: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    main()
