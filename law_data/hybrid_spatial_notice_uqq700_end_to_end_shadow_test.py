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
PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_END_TO_END_SHADOW_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_END_TO_END_SHADOW_REGRESSION"


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

    baseline_identity = _deep_find(
        reconciliation, "official_designation_identity_verified"
    )
    baseline_validity = _deep_find(reconciliation, "current_validity_verified")
    baseline_spatial = _deep_find(reconciliation, "site_spatial_inclusion_verified")
    baseline_runtime = _deep_find(reconciliation, "runtime_registration_allowed")
    baseline_resolution = _deep_find(reconciliation, "resolution")

    shadow = orchestrate_hybrid_spatial_notice(
        HybridSpatialNoticeStageResults(
            designation_identity={
                "official_designation_identity_verified": baseline_identity is True
            },
            current_validity={
                "current_validity_verified": baseline_validity is True
            },
            site_spatial_inclusion={
                "site_spatial_inclusion_verified": baseline_spatial is True
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
    states = [str(row.get("state") or row.get("resolution") or "") for row in rows]
    unknown_rows = sum(state == "UNKNOWN" for state in states)
    false_rows = sum(state == "FALSE" for state in states)
    true_rows = sum(state == "TRUE" for state in states)

    checks = {
        "baseline_identity_not_verified": baseline_identity is False,
        "baseline_validity_not_verified": baseline_validity is False,
        "baseline_spatial_not_verified": baseline_spatial is False,
        "baseline_runtime_blocked": baseline_runtime is False,
        "baseline_resolution_unknown": baseline_resolution == "UNKNOWN",
        "shadow_identity_not_verified": shadow["positive_gates"][
            "official_designation_identity_verified"
        ] is False,
        "shadow_validity_not_verified": shadow["positive_gates"][
            "current_validity_verified"
        ] is False,
        "shadow_spatial_not_verified": shadow["positive_gates"][
            "site_spatial_inclusion_verified"
        ] is False,
        "shadow_resolution_unknown": shadow["resolution"] == "UNKNOWN",
        "shadow_runtime_blocked": shadow["runtime_registration_allowed"] is False,
        "negative_evidence_disabled": shadow["negative_evidence_allowed"] is False,
        "legal_absence_inference_disabled": shadow[
            "legal_absence_inference_allowed"
        ] is False,
        "site_false_inference_disabled": shadow["site_false_inference_allowed"] is False,
        "site_promotion_disabled": shadow["site_promotion_allowed"] is False,
        "diagnostic_discovery_non_dispositive": shadow["diagnostic_discovery"][
            "dispositive"
        ] is False,
        "site_complete_has_uqq700_rows": len(rows) > 0,
        "site_complete_no_false_uqq700": false_rows == 0,
        "site_complete_no_true_uqq700": true_rows == 0,
        "site_complete_unknown_uqq700_present": unknown_rows > 0,
    }

    all_pass = all(checks.values())
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE END-TO-END SHADOW TEST")
    print("=" * 88)
    print("Runtime mutation: DISABLED")
    print("SITE mutation: DISABLED")
    print("Output writes: DISABLED")
    print()
    print(f"baseline identity: {baseline_identity} -> shadow {shadow['positive_gates']['official_designation_identity_verified']}")
    print(f"baseline validity: {baseline_validity} -> shadow {shadow['positive_gates']['current_validity_verified']}")
    print(f"baseline spatial: {baseline_spatial} -> shadow {shadow['positive_gates']['site_spatial_inclusion_verified']}")
    print(f"baseline runtime registration: {baseline_runtime} -> shadow {shadow['runtime_registration_allowed']}")
    print(f"baseline resolution: {baseline_resolution} -> shadow {shadow['resolution']}")
    print(f"UQQ700 SITE rows: {len(rows)} | UNKNOWN={unknown_rows} FALSE={false_rows} TRUE={true_rows}")
    print()

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
