from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path


LAW_DATA_DIR = Path(__file__).resolve().parent
if str(LAW_DATA_DIR.parent) not in sys.path:
    sys.path.insert(0, str(LAW_DATA_DIR.parent))

from law_data.historical_site_event_resolver import UNKNOWN  # noqa: E402
from law_data.urban_area_conversion_historical_site_event_evidence_bridge import (  # noqa: E402
    INPUT_CHECKS_MISSING,
    INPUT_FILE_MISSING,
    INPUT_INVALID_JSON,
    INPUT_INVALID_ROOT,
    INPUT_OK,
    bridge_payload,
    load_evidence_bridge,
)


def current_like_checks() -> dict[str, object]:
    return {
        "announcement_query_success": True,
        "announcement_total_count": 43508,
        "combined_candidate_count": 8,
        "combined_target_candidate_count": 0,
        "combined_unresolved_count": 0,
        "all_combined_candidates_classified_non_target": True,
        "direct_notice_hit_count": 1,
        "direct_target_event_count": 0,
        "direct_notice_is_not_target_history": True,
        "current_UQ111_positive_area_count": 1,
        "current_urban_area_confirmed": True,
        "current_UQ141_positive_area_count": 0,
        "current_greenbelt_absent": True,
        "historic_daechi_notice_chain_confirmed": True,
        "historic_missing_content_notice_count": 2,
        "historic_chain_has_missing_content": True,
        "national_archive_candidate_count": 2,
        "national_archive_original_unverified_count": 2,
        "national_archive_original_pending": True,
    }


def main() -> int:
    current_payload = {"checks": current_like_checks()}
    current_bridge = bridge_payload(current_payload)

    originals_resolved_checks = current_like_checks()
    originals_resolved_checks.update(
        {
            "historic_missing_content_notice_count": 0,
            "historic_chain_has_missing_content": False,
            "national_archive_original_unverified_count": 0,
            "national_archive_original_pending": False,
        }
    )
    originals_resolved_bridge = bridge_payload(
        {"checks": originals_resolved_checks}
    )

    missing_checks_bridge = bridge_payload({})
    invalid_root_bridge = bridge_payload(None)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)

        missing_file_bridge = load_evidence_bridge(temp_root / "missing.json")

        invalid_json_path = temp_root / "invalid.json"
        invalid_json_path.write_text("{not-json", encoding="utf-8")
        invalid_json_bridge = load_evidence_bridge(invalid_json_path)

        invalid_root_path = temp_root / "root-list.json"
        invalid_root_path.write_text("[]", encoding="utf-8")
        invalid_root_file_bridge = load_evidence_bridge(invalid_root_path)

        valid_path = temp_root / "history.json"
        valid_path.write_text(
            json.dumps(current_payload, ensure_ascii=False),
            encoding="utf-8",
        )
        valid_file_bridge = load_evidence_bridge(valid_path)

    fail_closed_results = (
        missing_checks_bridge,
        invalid_root_bridge,
        missing_file_bridge,
        invalid_json_bridge,
        invalid_root_file_bridge,
    )

    all_results = (
        current_bridge,
        originals_resolved_bridge,
        valid_file_bridge,
        *fail_closed_results,
    )

    checks = {
        "current actual-like payload remains UNKNOWN": (
            current_bridge["generalized_resolution"] == UNKNOWN
        ),
        "current unresolved originals are preserved through bridge": (
            current_bridge["shadow"]["shadow_diagnostics"][
                "unresolved_historical_source_present"
            ]
            is True
        ),
        "valid file path reads checks without production wiring": (
            valid_file_bridge["input_status"] == INPUT_OK
            and valid_file_bridge["checks_present"] is True
            and valid_file_bridge["generalized_resolution"] == UNKNOWN
        ),
        "missing file fails closed UNKNOWN": (
            missing_file_bridge["input_status"] == INPUT_FILE_MISSING
            and missing_file_bridge["generalized_resolution"] == UNKNOWN
        ),
        "invalid JSON fails closed UNKNOWN": (
            invalid_json_bridge["input_status"] == INPUT_INVALID_JSON
            and invalid_json_bridge["generalized_resolution"] == UNKNOWN
        ),
        "non-object JSON root fails closed UNKNOWN": (
            invalid_root_file_bridge["input_status"] == INPUT_INVALID_ROOT
            and invalid_root_file_bridge["generalized_resolution"] == UNKNOWN
        ),
        "missing checks fail closed UNKNOWN": (
            missing_checks_bridge["input_status"] == INPUT_CHECKS_MISSING
            and missing_checks_bridge["generalized_resolution"] == UNKNOWN
        ),
        "non-mapping payload fails closed UNKNOWN": (
            invalid_root_bridge["input_status"] == INPUT_INVALID_ROOT
            and invalid_root_bridge["generalized_resolution"] == UNKNOWN
        ),
        "resolving originals alone still cannot manufacture FALSE": (
            originals_resolved_bridge["generalized_resolution"] == UNKNOWN
            and originals_resolved_bridge["shadow"]["generalized_resolution"]
            ["evidence_state"]["history_scope_complete_verified"]
            is False
        ),
        "legacy database-negative eligibility is not global completeness": (
            originals_resolved_bridge["shadow"]["shadow_diagnostics"]
            ["official_database_negative"]
            is True
            and originals_resolved_bridge["global_history_completeness_promoted"]
            is False
            and originals_resolved_bridge["legacy_false_eligibility_promoted"]
            is False
        ),
        "bridge never writes output": all(
            result["output_written"] is False for result in all_results
        ),
        "bridge remains production-unwired": all(
            result["production_wiring_applied"] is False
            and result["overlay_mutated"] is False
            and result["runtime_registry_mutated"] is False
            for result in all_results
        ),
        "shadow generic negative inference stays disabled": all(
            result["shadow"]["generalized_resolution"]
            ["generic_negative_inference_allowed"]
            is False
            for result in all_results
        ),
        "shadow discovery cannot infer legal absence": all(
            result["shadow"]["generalized_resolution"]
            ["legal_absence_inference_from_discovery_allowed"]
            is False
            for result in all_results
        ),
    }

    all_pass = all(checks.values())

    print("=" * 72)
    print("URBAN AREA CONVERSION HISTORICAL SITE EVENT EVIDENCE BRIDGE")
    print("=" * 72)
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print("-" * 72)
    print(f"all_pass: {all_pass}")
    print(
        "CLASSIFICATION: "
        + (
            "URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_EVIDENCE_BRIDGE_PASS"
            if all_pass
            else "URBAN_AREA_CONVERSION_HISTORICAL_SITE_EVENT_EVIDENCE_BRIDGE_FAIL"
        )
    )

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
