from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hybrid_spatial_notice_resolver import (
    HybridSpatialNoticeGateState,
    resolve_hybrid_spatial_notice,
)

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
EXPECTED_RESOLUTION = "UNKNOWN"
PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SHADOW_PARITY_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_SHADOW_PARITY_REGRESSION"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
RECONCILIATION_PATH = OUTPUT_DIR / (
    "development_density_management_area_step17_post_seongnam_residual_terminal_reconciliation.json"
)
BASELINE_PATH = OUTPUT_DIR / "site_rule_evaluation_site_complete.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_key(value: Any) -> str:
    return str(value).lower().replace("_", "").replace(" ", "")


def deep_find_bool(data: Any, candidate_keys: tuple[str, ...]) -> bool | None:
    normalized = {normalize_key(key) for key in candidate_keys}

    def walk(value: Any) -> bool | None:
        if isinstance(value, dict):
            for key, child in value.items():
                if normalize_key(key) in normalized and isinstance(child, bool):
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
    reconciliation = load_json(RECONCILIATION_PATH)
    baseline = load_json(BASELINE_PATH)

    observed_identity = deep_find_bool(
        reconciliation,
        ("official_designation_identity_verified", "OFFICIAL DESIGNATION IDENTITY VERIFIED"),
    )
    observed_validity = deep_find_bool(
        reconciliation,
        ("current_validity_verified", "CURRENT VALIDITY VERIFIED"),
    )
    observed_spatial = deep_find_bool(
        reconciliation,
        ("site_spatial_inclusion_verified", "SITE SPATIAL INCLUSION VERIFIED"),
    )
    observed_minimum_gate = deep_find_bool(
        reconciliation,
        ("minimum_registration_gate_satisfied", "Minimum registration gate satisfied"),
    )
    observed_runtime_registration = deep_find_bool(
        reconciliation,
        ("runtime_registration_allowed", "Runtime registration allowed"),
    )

    required_gate_values_present = all(
        value is not None
        for value in (
            observed_identity,
            observed_validity,
            observed_spatial,
            observed_minimum_gate,
            observed_runtime_registration,
        )
    )

    shadow = resolve_hybrid_spatial_notice(
        HybridSpatialNoticeGateState(
            official_designation_identity_verified=observed_identity is True,
            current_validity_verified=observed_validity is True,
            site_spatial_inclusion_verified=observed_spatial is True,
        )
    )

    baseline_guard = baseline.get("uqq700_guard", {})
    if not isinstance(baseline_guard, dict):
        baseline_guard = {}

    checks = {
        "required_gate_values_present": required_gate_values_present,
        "uqq700_observed_identity_not_verified": observed_identity is False,
        "uqq700_observed_validity_not_verified": observed_validity is False,
        "uqq700_observed_spatial_not_verified": observed_spatial is False,
        "shadow_resolution_is_unknown": shadow["resolution"] == EXPECTED_RESOLUTION,
        "shadow_minimum_gate_matches_observed": (
            shadow["minimum_registration_gate_satisfied"] == observed_minimum_gate
        ),
        "shadow_runtime_registration_matches_observed": (
            shadow["runtime_registration_allowed"] == observed_runtime_registration
        ),
        "shadow_negative_evidence_disabled": shadow["negative_evidence_allowed"] is False,
        "shadow_legal_absence_inference_disabled": (
            shadow["legal_absence_inference_allowed"] is False
        ),
        "shadow_site_false_inference_disabled": (
            shadow["site_false_inference_allowed"] is False
        ),
        "shadow_site_promotion_disabled": shadow["site_promotion_allowed"] is False,
        "baseline_guard_resolution_matches_shadow": (
            baseline_guard.get("resolution") == shadow["resolution"]
        ),
        "baseline_guard_registration_matches_shadow": (
            baseline_guard.get("runtime_registration_allowed")
            == shadow["runtime_registration_allowed"]
        ),
        "baseline_guard_negative_evidence_matches_shadow": (
            baseline_guard.get("negative_evidence_allowed")
            == shadow["negative_evidence_allowed"]
        ),
        "baseline_guard_legal_absence_matches_shadow": (
            baseline_guard.get("legal_absence_inference_allowed")
            == shadow["legal_absence_inference_allowed"]
        ),
        "baseline_guard_site_false_matches_shadow": (
            baseline_guard.get("site_false_inference_allowed")
            == shadow["site_false_inference_allowed"]
        ),
        "baseline_guard_site_promotion_matches_shadow": (
            baseline_guard.get("site_promotion_allowed")
            == shadow["site_promotion_allowed"]
        ),
    }

    all_pass = all(checks.values())
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE SHADOW PARITY TEST")
    print("=" * 88)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Reconciliation input: {RECONCILIATION_PATH}")
    print(f"Baseline input: {BASELINE_PATH}")
    print("Runtime mutation: DISABLED")
    print("SITE promotion: DISABLED")
    print()
    print("OBSERVED -> SHADOW")
    print("-" * 88)
    print(f"identity: {observed_identity} -> {shadow['positive_gates']['official_designation_identity_verified']}")
    print(f"validity: {observed_validity} -> {shadow['positive_gates']['current_validity_verified']}")
    print(f"spatial: {observed_spatial} -> {shadow['positive_gates']['site_spatial_inclusion_verified']}")
    print(f"minimum gate: {observed_minimum_gate} -> {shadow['minimum_registration_gate_satisfied']}")
    print(f"runtime registration: {observed_runtime_registration} -> {shadow['runtime_registration_allowed']}")
    print(f"resolution: {baseline_guard.get('resolution')} -> {shadow['resolution']}")
    print()
    print("PARITY CHECKS")
    print("-" * 88)
    for name, value in checks.items():
        print(f"{name}: {value}")
    print()
    print(f"CLASSIFICATION: {classification}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
