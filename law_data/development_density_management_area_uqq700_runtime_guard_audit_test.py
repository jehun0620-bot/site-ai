from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
EXPECTED_RESOLUTION = "UNKNOWN"
EXPECTED_RECONCILIATION_CLASSIFICATION = (
    "STEP17_POST_SEONGNAM_RESIDUAL_SOURCE_FAMILIES_TERMINALLY_RECONCILED_UQQ700_UNKNOWN"
)
PASS_CLASSIFICATION = "UQQ700_RUNTIME_GUARD_AUDIT_PASS"
FAIL_CLASSIFICATION = "UQQ700_RUNTIME_GUARD_AUDIT_REGRESSION_DETECTED"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
RECONCILIATION_PATH = OUTPUT_DIR / (
    "development_density_management_area_step17_post_seongnam_residual_terminal_reconciliation.json"
)
BASELINE_PATH = OUTPUT_DIR / "site_rule_evaluation_site_complete.json"
OUTPUT_PATH = OUTPUT_DIR / (
    "development_density_management_area_uqq700_runtime_guard_audit_test.json"
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_key(value: Any) -> str:
    return str(value).lower().replace("_", "").replace(" ", "")


def deep_find_value(data: Any, candidate_keys: tuple[str, ...]) -> Any:
    normalized = {normalize_key(key) for key in candidate_keys}

    def walk(value: Any) -> Any:
        if isinstance(value, dict):
            for key, child in value.items():
                if normalize_key(key) in normalized:
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


def deep_find_bool(data: Any, candidate_keys: tuple[str, ...]) -> bool | None:
    value = deep_find_value(data, candidate_keys)
    return value if isinstance(value, bool) else None


def collect_baseline_matches(data: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_matches: list[dict[str, Any]] = []
    condition_like_matches: list[dict[str, Any]] = []

    def walk(value: Any, path: str = "$") -> None:
        if isinstance(value, dict):
            encoded = json.dumps(value, ensure_ascii=False)
            if TARGET_NAME in encoded or TARGET_CODE in encoded:
                scalar = {
                    str(key): child
                    for key, child in value.items()
                    if not isinstance(child, (dict, list))
                }
                row = {"path": path, "scalar": scalar}
                raw_matches.append(row)

                if (
                    scalar.get("name") == TARGET_NAME
                    or scalar.get("standard_code") == TARGET_CODE
                    or scalar.get("code") == TARGET_CODE
                    or scalar.get("standardCode") == TARGET_CODE
                ):
                    condition_like_matches.append(row)

            for key, child in value.items():
                walk(child, f"{path}.{key}")

        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(data)
    return raw_matches, condition_like_matches


def main() -> int:
    print("=" * 88)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("UQQ700 RUNTIME GUARD AUDIT TEST")
    print("=" * 88)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Reconciliation input: {RECONCILIATION_PATH}")
    print(f"Baseline input: {BASELINE_PATH}")
    print("Network access: DISABLED")
    print("Registry mutation: DISABLED")
    print("SITE promotion: DISABLED")
    print()

    diagnostics: list[dict[str, Any]] = []

    try:
        reconciliation = load_json(RECONCILIATION_PATH)
    except Exception as exc:
        reconciliation = {}
        diagnostics.append(
            {
                "type": "reconciliation_load_error",
                "path": str(RECONCILIATION_PATH),
                "error": repr(exc),
            }
        )

    try:
        baseline = load_json(BASELINE_PATH)
    except Exception as exc:
        baseline = {}
        diagnostics.append(
            {
                "type": "baseline_load_error",
                "path": str(BASELINE_PATH),
                "error": repr(exc),
            }
        )

    reconciliation_classification = reconciliation.get("classification")
    reconciliation_resolution = (
        reconciliation.get("resolution")
        or reconciliation.get("uqq700")
        or reconciliation.get("uqq700_resolution")
    )

    official_designation_verified = deep_find_bool(
        reconciliation,
        (
            "official_designation_identity_verified",
            "OFFICIAL DESIGNATION IDENTITY VERIFIED",
        ),
    )
    current_validity_verified = deep_find_bool(
        reconciliation,
        (
            "current_validity_verified",
            "CURRENT VALIDITY VERIFIED",
        ),
    )
    site_spatial_inclusion_verified = deep_find_bool(
        reconciliation,
        (
            "site_spatial_inclusion_verified",
            "SITE SPATIAL INCLUSION VERIFIED",
        ),
    )
    minimum_registration_gate_satisfied = deep_find_bool(
        reconciliation,
        (
            "minimum_registration_gate_satisfied",
            "Minimum registration gate satisfied",
        ),
    )
    negative_evidence_allowed = deep_find_bool(
        reconciliation,
        ("negative_evidence_allowed", "Negative evidence allowed"),
    )
    legal_absence_inference_allowed = deep_find_bool(
        reconciliation,
        ("legal_absence_inference_allowed", "Legal absence inference allowed"),
    )
    site_false_inference_allowed = deep_find_bool(
        reconciliation,
        ("site_false_inference_allowed", "SITE FALSE inference allowed"),
    )
    site_promotion_allowed = deep_find_bool(
        reconciliation,
        ("site_promotion_allowed", "SITE promotion allowed"),
    )
    runtime_registration_allowed = deep_find_bool(
        reconciliation,
        ("runtime_registration_allowed", "Runtime registration allowed"),
    )

    derived_minimum_gate = (
        official_designation_verified is True
        and current_validity_verified is True
        and site_spatial_inclusion_verified is True
    )
    derived_runtime_registration_allowed = derived_minimum_gate

    raw_matches, condition_like_matches = collect_baseline_matches(baseline)

    required_guard_values_present = all(
        value is not None
        for value in (
            official_designation_verified,
            current_validity_verified,
            site_spatial_inclusion_verified,
            minimum_registration_gate_satisfied,
            negative_evidence_allowed,
            legal_absence_inference_allowed,
            site_false_inference_allowed,
            site_promotion_allowed,
            runtime_registration_allowed,
        )
    )

    checks = {
        "reconciliation_input_loaded": bool(reconciliation),
        "baseline_input_loaded": bool(baseline),
        "reconciliation_classification_is_expected": (
            reconciliation_classification == EXPECTED_RECONCILIATION_CLASSIFICATION
        ),
        "uqq700_resolution_is_unknown": reconciliation_resolution == EXPECTED_RESOLUTION,
        "official_designation_identity_verified_is_false": official_designation_verified is False,
        "current_validity_verified_is_false": current_validity_verified is False,
        "site_spatial_inclusion_verified_is_false": site_spatial_inclusion_verified is False,
        "reported_minimum_registration_gate_is_false": (
            minimum_registration_gate_satisfied is False
        ),
        "derived_minimum_registration_gate_is_false": derived_minimum_gate is False,
        "negative_evidence_allowed_is_false": negative_evidence_allowed is False,
        "legal_absence_inference_allowed_is_false": legal_absence_inference_allowed is False,
        "site_false_inference_allowed_is_false": site_false_inference_allowed is False,
        "site_promotion_allowed_is_false": site_promotion_allowed is False,
        "runtime_registration_allowed_is_false": runtime_registration_allowed is False,
        "derived_runtime_registration_allowed_is_false": (
            derived_runtime_registration_allowed is False
        ),
        "all_required_guard_values_present": required_guard_values_present,
        "baseline_raw_uqq700_match_count_is_zero": len(raw_matches) == 0,
        "baseline_condition_like_uqq700_match_count_is_zero": (
            len(condition_like_matches) == 0
        ),
    }

    all_pass = all(checks.values())

    print("RECONCILIATION GUARD STATE")
    print("-" * 88)
    print(f"classification: {reconciliation_classification}")
    print(f"resolution: {reconciliation_resolution}")
    print(f"OFFICIAL DESIGNATION IDENTITY VERIFIED: {official_designation_verified}")
    print(f"CURRENT VALIDITY VERIFIED: {current_validity_verified}")
    print(f"SITE SPATIAL INCLUSION VERIFIED: {site_spatial_inclusion_verified}")
    print(f"Minimum registration gate satisfied: {minimum_registration_gate_satisfied}")
    print(f"Derived minimum registration gate: {derived_minimum_gate}")
    print(f"Negative evidence allowed: {negative_evidence_allowed}")
    print(f"Legal absence inference allowed: {legal_absence_inference_allowed}")
    print(f"SITE FALSE inference allowed: {site_false_inference_allowed}")
    print(f"SITE promotion allowed: {site_promotion_allowed}")
    print(f"Runtime registration allowed: {runtime_registration_allowed}")
    print(f"Derived runtime registration allowed: {derived_runtime_registration_allowed}")
    print()

    print("CLEAN BASELINE AUDIT")
    print("-" * 88)
    print(f"baseline file exists: {BASELINE_PATH.exists()}")
    print(f"raw UQQ700/target matching object count: {len(raw_matches)}")
    print(f"condition-like UQQ700/target match count: {len(condition_like_matches)}")

    for index, item in enumerate(condition_like_matches, 1):
        print()
        print(f"[{index}] path={item['path']}")
        print(json.dumps(item["scalar"], ensure_ascii=False, indent=2))

    print()
    print("REGRESSION CHECKS")
    print("-" * 88)
    for name, value in checks.items():
        print(f"{name}: {value}")

    if all_pass:
        classification = PASS_CLASSIFICATION
        next_action = (
            "KEEP_UQQ700_UNKNOWN_AND_OUT_OF_RUNTIME_REGISTRATION_UNTIL_ALL_THREE_"
            "POSITIVE_REGISTRATION_GATES_ARE_VERIFIED"
        )
    else:
        classification = FAIL_CLASSIFICATION
        next_action = (
            "STOP_ANY_UQQ700_RUNTIME_PROMOTION_AND_INSPECT_RECONCILIATION_OR_"
            "BASELINE_CONTAMINATION_BEFORE_FURTHER_INTEGRATION"
        )

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution": EXPECTED_RESOLUTION,
        "inputs": {
            "reconciliation": str(RECONCILIATION_PATH),
            "baseline": str(BASELINE_PATH),
        },
        "observed": {
            "reconciliation_classification": reconciliation_classification,
            "reconciliation_resolution": reconciliation_resolution,
            "official_designation_identity_verified": official_designation_verified,
            "current_validity_verified": current_validity_verified,
            "site_spatial_inclusion_verified": site_spatial_inclusion_verified,
            "minimum_registration_gate_satisfied": minimum_registration_gate_satisfied,
            "negative_evidence_allowed": negative_evidence_allowed,
            "legal_absence_inference_allowed": legal_absence_inference_allowed,
            "site_false_inference_allowed": site_false_inference_allowed,
            "site_promotion_allowed": site_promotion_allowed,
            "runtime_registration_allowed": runtime_registration_allowed,
            "baseline_raw_match_count": len(raw_matches),
            "baseline_condition_like_match_count": len(condition_like_matches),
        },
        "derived": {
            "minimum_registration_gate_satisfied": derived_minimum_gate,
            "runtime_registration_allowed": derived_runtime_registration_allowed,
        },
        "baseline_matches": {
            "raw": raw_matches,
            "condition_like": condition_like_matches,
        },
        "checks": checks,
        "classification": classification,
        "next_action": next_action,
        "diagnostics": diagnostics,
        "safety": {
            "network_access_used": False,
            "registry_mutation_used": False,
            "site_promotion_used": False,
            "negative_evidence_allowed": False,
            "legal_absence_inference_allowed": False,
            "site_false_inference_allowed": False,
            "runtime_registration_allowed": False,
        },
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print("=" * 88)
    print("RESOLUTION")
    print("=" * 88)
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {EXPECTED_RESOLUTION}")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
