from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
EXPECTED_RESOLUTION = "UNKNOWN"
EXPECTED_CLASSIFICATION = (
    "STEP17_POST_SEONGNAM_RESIDUAL_SOURCE_FAMILIES_TERMINALLY_RECONCILED_UQQ700_UNKNOWN"
)

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
INPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_step17_post_seongnam_residual_terminal_reconciliation.json"
)
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_uqq700_unknown_registration_guard_test.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def deep_find_bool(data: Any, candidate_keys: tuple[str, ...]) -> bool | None:
    normalized = {k.lower().replace("_", "").replace(" ", "") for k in candidate_keys}

    def walk(value: Any) -> bool | None:
        if isinstance(value, dict):
            for key, child in value.items():
                nk = str(key).lower().replace("_", "").replace(" ", "")
                if nk in normalized and isinstance(child, bool):
                    return child
            for child in value.values():
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found is not None:
                    return found
        return None

    return walk(data)


def deep_find_value(data: Any, candidate_keys: tuple[str, ...]) -> Any:
    normalized = {k.lower().replace("_", "").replace(" ", "") for k in candidate_keys}

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            for key, child in value.items():
                nk = str(key).lower().replace("_", "").replace(" ", "")
                if nk in normalized:
                    return child
            for child in value.values():
                found = walk(child)
                if found is not None:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = walk(child)
                if found is not None:
                    return found
        return None

    return walk(data)


def main() -> int:
    print("=" * 84)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("UQQ700 UNKNOWN REGISTRATION GUARD TEST")
    print("=" * 84)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Input: {INPUT_PATH}")
    print("Network access: DISABLED")
    print("Registry mutation: DISABLED")
    print("SITE promotion: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []
    try:
        data = load_json(INPUT_PATH)
    except Exception as exc:
        data = {}
        diagnostics.append({"type": "input_load_error", "error": repr(exc)})

    input_classification = data.get("classification")
    input_resolution = data.get("resolution") or data.get("uqq700") or data.get("uqq700_resolution")

    official_designation_verified = deep_find_bool(
        data,
        (
            "official_designation_identity_verified",
            "OFFICIAL DESIGNATION IDENTITY VERIFIED",
        ),
    )
    current_validity_verified = deep_find_bool(
        data,
        (
            "current_validity_verified",
            "CURRENT VALIDITY VERIFIED",
        ),
    )
    site_spatial_inclusion_verified = deep_find_bool(
        data,
        (
            "site_spatial_inclusion_verified",
            "SITE SPATIAL INCLUSION VERIFIED",
        ),
    )
    minimum_gate_satisfied = deep_find_bool(
        data,
        (
            "minimum_registration_gate_satisfied",
            "Minimum registration gate satisfied",
        ),
    )

    negative_evidence_allowed = deep_find_bool(
        data,
        ("negative_evidence_allowed", "Negative evidence allowed"),
    )
    legal_absence_inference_allowed = deep_find_bool(
        data,
        ("legal_absence_inference_allowed", "Legal absence inference allowed"),
    )
    site_false_inference_allowed = deep_find_bool(
        data,
        ("site_false_inference_allowed", "SITE FALSE inference allowed"),
    )
    site_promotion_allowed = deep_find_bool(
        data,
        ("site_promotion_allowed", "SITE promotion allowed"),
    )
    runtime_registration_allowed = deep_find_bool(
        data,
        ("runtime_registration_allowed", "Runtime registration allowed"),
    )

    # Conservative derivation: registration is allowed only when all three positive gates are explicitly True.
    derived_minimum_gate = (
        official_designation_verified is True
        and current_validity_verified is True
        and site_spatial_inclusion_verified is True
    )
    derived_registration_allowed = derived_minimum_gate

    checks = {
        "input_classification_is_expected": input_classification == EXPECTED_CLASSIFICATION,
        "resolution_is_unknown": input_resolution == EXPECTED_RESOLUTION,
        "official_designation_identity_verified_is_false": official_designation_verified is False,
        "current_validity_verified_is_false": current_validity_verified is False,
        "site_spatial_inclusion_verified_is_false": site_spatial_inclusion_verified is False,
        "reported_minimum_registration_gate_is_false": minimum_gate_satisfied is False,
        "derived_minimum_registration_gate_is_false": derived_minimum_gate is False,
        "negative_evidence_allowed_is_false": negative_evidence_allowed is False,
        "legal_absence_inference_allowed_is_false": legal_absence_inference_allowed is False,
        "site_false_inference_allowed_is_false": site_false_inference_allowed is False,
        "site_promotion_allowed_is_false": site_promotion_allowed is False,
        "runtime_registration_allowed_is_false": runtime_registration_allowed is False,
        "derived_runtime_registration_allowed_is_false": derived_registration_allowed is False,
    }

    # Fail closed if any required invariant is absent instead of silently treating missing as False.
    required_values_present = all(
        value is not None
        for value in (
            official_designation_verified,
            current_validity_verified,
            site_spatial_inclusion_verified,
            minimum_gate_satisfied,
            negative_evidence_allowed,
            legal_absence_inference_allowed,
            site_false_inference_allowed,
            site_promotion_allowed,
            runtime_registration_allowed,
        )
    )
    checks["all_required_guard_values_present"] = required_values_present

    all_pass = all(checks.values())

    print("GUARD INPUT STATE")
    print("-" * 84)
    print(f"classification: {input_classification}")
    print(f"resolution: {input_resolution}")
    print(f"OFFICIAL DESIGNATION IDENTITY VERIFIED: {official_designation_verified}")
    print(f"CURRENT VALIDITY VERIFIED: {current_validity_verified}")
    print(f"SITE SPATIAL INCLUSION VERIFIED: {site_spatial_inclusion_verified}")
    print(f"Minimum registration gate satisfied: {minimum_gate_satisfied}")
    print(f"Derived minimum registration gate: {derived_minimum_gate}")
    print(f"Negative evidence allowed: {negative_evidence_allowed}")
    print(f"Legal absence inference allowed: {legal_absence_inference_allowed}")
    print(f"SITE FALSE inference allowed: {site_false_inference_allowed}")
    print(f"SITE promotion allowed: {site_promotion_allowed}")
    print(f"Runtime registration allowed: {runtime_registration_allowed}")
    print(f"Derived runtime registration allowed: {derived_registration_allowed}")
    print()

    print("REGRESSION CHECKS")
    print("-" * 84)
    for key, value in checks.items():
        print(f"{key}: {value}")
    print()

    if all_pass:
        classification = "UQQ700_UNKNOWN_REGISTRATION_GUARD_HARDENED_PASS"
        next_action = (
            "KEEP_UQQ700_OUT_OF_RUNTIME_REGISTRY_UNTIL_ALL_THREE_POSITIVE_REGISTRATION_GATES_ARE_VERIFIED"
        )
    else:
        classification = "UQQ700_UNKNOWN_REGISTRATION_GUARD_REGRESSION_DETECTED"
        next_action = (
            "STOP_RUNTIME_PROMOTION_AND_INSPECT_THE_RECONCILIATION_OR_REGISTRATION_GUARD_INVARIANT_BEFORE_ANY_FURTHER_INTEGRATION"
        )

    safety = {
        "network_access_used": False,
        "registry_mutation_used": False,
        "site_promotion_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": EXPECTED_RESOLUTION,
    }

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": EXPECTED_RESOLUTION,
        "input": str(INPUT_PATH),
        "input_classification": input_classification,
        "input_resolution": input_resolution,
        "observed": {
            "official_designation_identity_verified": official_designation_verified,
            "current_validity_verified": current_validity_verified,
            "site_spatial_inclusion_verified": site_spatial_inclusion_verified,
            "minimum_registration_gate_satisfied": minimum_gate_satisfied,
            "negative_evidence_allowed": negative_evidence_allowed,
            "legal_absence_inference_allowed": legal_absence_inference_allowed,
            "site_false_inference_allowed": site_false_inference_allowed,
            "site_promotion_allowed": site_promotion_allowed,
            "runtime_registration_allowed": runtime_registration_allowed,
        },
        "derived": {
            "minimum_registration_gate_satisfied": derived_minimum_gate,
            "runtime_registration_allowed": derived_registration_allowed,
        },
        "checks": checks,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": safety,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 84)
    print("RESOLUTION")
    print("=" * 84)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {EXPECTED_RESOLUTION}")
    print("Runtime registration allowed: False")
    print("SITE promotion allowed: False")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
