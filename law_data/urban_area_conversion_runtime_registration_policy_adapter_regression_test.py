from __future__ import annotations

from law_data.historical_site_event_resolver import RESOLUTION_TYPE, UNKNOWN
from law_data.urban_area_conversion_runtime_registration_policy_adapter import (
    ADAPTER_MODE,
    CONDITION_NAME,
    adapt_urban_area_conversion_runtime_registration_policy,
)


def main() -> None:
    print("=" * 72)
    print("URBAN AREA CONVERSION RUNTIME REGISTRATION POLICY ADAPTER")
    print("=" * 72)

    result = adapt_urban_area_conversion_runtime_registration_policy()
    policy = result["runtime_registration_policy"]
    gates = policy["gates"]

    checks = {
        "condition identity is preserved": result["condition"] == CONDITION_NAME,
        "adapter remains read-only and production-unwired": result["adapter_mode"] == ADAPTER_MODE,
        "resolver type is HISTORICAL_SITE_EVENT": result["resolver_type"] == RESOLUTION_TYPE,
        "current condition resolution remains UNKNOWN": result["current_resolution"] == UNKNOWN,
        "production wiring remains not ready": gates["production_wiring_ready"] is False,
        "standard code remains unverified": gates["standard_code_verified"] is False,
        "provenance policy remains unverified": gates["provenance_policy_verified"] is False,
        "resolver type gate is satisfied": gates["resolver_type_verified"] is True,
        "UNKNOWN is a supported historical resolution": gates["resolution_supported"] is True,
        "registration eligibility is blocked": policy["registration_eligible"] is False,
        "registration state is BLOCKED": policy["registration_state"] == "BLOCKED",
        "missing gates are the three current blockers": set(policy["missing_gates"])
        == {
            "production_wiring_ready",
            "standard_code_verified",
            "provenance_policy_verified",
        },
        "condition name cannot manufacture standard code": result["promotion_guards"]["condition_name_promoted_to_standard_code"] is False,
        "UNKNOWN cannot manufacture SITE FALSE": result["promotion_guards"]["unknown_promoted_to_site_false"] is False,
        "UNKNOWN cannot manufacture SITE TRUE": result["promotion_guards"]["unknown_promoted_to_site_true"] is False,
        "policy eligibility cannot manufacture actual registration": result["promotion_guards"]["policy_eligibility_promoted_to_actual_registration"] is False,
        "negative evidence inference remains disabled": policy["negative_evidence_inference_allowed"] is False,
        "legal absence inference remains disabled": policy["legal_absence_inference_allowed"] is False,
        "adapter writes no output": result["output_written"] is False,
        "adapter performs no production wiring": result["production_wiring_applied"] is False,
        "adapter performs no overlay mutation": result["overlay_mutated"] is False,
        "adapter performs no runtime registry mutation": result["runtime_registry_mutated"] is False,
        "common policy also performs no runtime mutation": policy["runtime_registry_mutated"] is False,
    }

    for label, passed in checks.items():
        print(f"{label}: {passed}")

    all_pass = all(checks.values())

    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_RUNTIME_REGISTRATION_POLICY_ADAPTER_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_RUNTIME_REGISTRATION_POLICY_ADAPTER_FAIL"
        )
    )

    if not all_pass:
        raise AssertionError("runtime registration policy adapter regression failed")


if __name__ == "__main__":
    main()
