from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hybrid_spatial_notice_orchestrator import (
    HybridSpatialNoticeStageResults,
    orchestrate_hybrid_spatial_notice,
)


BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
RECONCILIATION_PATH = OUTPUT_DIR / (
    "development_density_management_area_"
    "step17_post_seongnam_residual_terminal_reconciliation.json"
)
SITE_COMPLETE_PATH = OUTPUT_DIR / "site_rule_evaluation_site_complete.json"

TARGET_CODE = "UQQ700"
TARGET_NAME = "개발밀도관리구역"
PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_GENERALIZATION_GUARD_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_GENERALIZATION_GUARD_REGRESSION"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _deep_find(obj: Any, key: str) -> Any:
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for value in obj.values():
            found = _deep_find(value, key)
            if found is not None:
                return found
    elif isinstance(obj, list):
        for value in obj:
            found = _deep_find(value, key)
            if found is not None:
                return found
    return None


def _uqq700_rows(obj: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        code = str(obj.get("standard_code") or obj.get("code") or "")
        name = str(obj.get("name") or obj.get("target_name") or "")
        if code == TARGET_CODE or name == TARGET_NAME:
            rows.append(obj)
        for value in obj.values():
            rows.extend(_uqq700_rows(value))
    elif isinstance(obj, list):
        for value in obj:
            rows.extend(_uqq700_rows(value))
    return rows


def main() -> int:
    reconciliation = _load(RECONCILIATION_PATH)
    site_complete = _load(SITE_COMPLETE_PATH)

    identity = _deep_find(reconciliation, "official_designation_identity_verified")
    validity = _deep_find(reconciliation, "current_validity_verified")
    spatial = _deep_find(reconciliation, "site_spatial_inclusion_verified")
    minimum_gate = _deep_find(reconciliation, "minimum_registration_gate_satisfied")
    runtime = _deep_find(reconciliation, "runtime_registration_allowed")
    resolution = _deep_find(reconciliation, "resolution")
    negative_allowed = _deep_find(reconciliation, "negative_evidence_allowed")
    absence_allowed = _deep_find(reconciliation, "legal_absence_inference_allowed")
    site_false_allowed = _deep_find(reconciliation, "site_false_inference_allowed")
    site_promotion_allowed = _deep_find(reconciliation, "site_promotion_allowed")

    shadow = orchestrate_hybrid_spatial_notice(
        HybridSpatialNoticeStageResults(
            designation_identity={
                "official_designation_identity_verified": identity is True,
            },
            current_validity={
                "current_validity_verified": validity is True,
            },
            site_spatial_inclusion={
                "site_spatial_inclusion_verified": spatial is True,
            },
        ),
        search_hit=False,
        http_200=True,
        negative_evidence={
            "search_no_hit": True,
            "site_non_display": True,
            "candidate_layer_no_hit": True,
        },
    )

    rows = _uqq700_rows(site_complete)
    row_states = [str(row.get("state") or row.get("resolution") or "") for row in rows]

    checks = {
        "identity_gate_still_false": identity is False,
        "validity_gate_still_false": validity is False,
        "spatial_gate_still_false": spatial is False,
        "minimum_gate_still_false": minimum_gate is False,
        "runtime_registration_still_false": runtime is False,
        "resolution_still_unknown": resolution == "UNKNOWN",
        "negative_evidence_still_disabled": negative_allowed is False,
        "legal_absence_inference_still_disabled": absence_allowed is False,
        "site_false_inference_still_disabled": site_false_allowed is False,
        "site_promotion_still_disabled": site_promotion_allowed is False,
        "shadow_minimum_gate_false": shadow[
            "minimum_registration_gate_satisfied"
        ] is False,
        "shadow_runtime_registration_false": shadow[
            "runtime_registration_allowed"
        ] is False,
        "shadow_resolution_unknown": shadow["resolution"] == "UNKNOWN",
        "shadow_negative_evidence_disabled": shadow[
            "negative_evidence_allowed"
        ] is False,
        "shadow_legal_absence_disabled": shadow[
            "legal_absence_inference_allowed"
        ] is False,
        "shadow_site_false_disabled": shadow[
            "site_false_inference_allowed"
        ] is False,
        "shadow_site_promotion_disabled": shadow["site_promotion_allowed"] is False,
        "site_rows_present": len(rows) > 0,
        "site_rows_have_no_false": "FALSE" not in row_states,
        "site_rows_have_no_true": "TRUE" not in row_states,
        "site_rows_include_unknown": "UNKNOWN" in row_states,
    }

    all_pass = all(checks.values())
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE GENERALIZATION GUARD TEST")
    print("=" * 88)
    print("Runtime mutation: DISABLED")
    print("SITE mutation: DISABLED")
    print("Output writes: DISABLED")
    print()
    print(
        "baseline gates: "
        f"identity={identity} validity={validity} spatial={spatial} minimum={minimum_gate}"
    )
    print(f"baseline resolution={resolution} runtime_registration={runtime}")
    print(f"UQQ700 SITE rows={len(rows)}")
    print()

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
