from __future__ import annotations

import json
from pathlib import Path
from typing import Any

TARGET_NAME = "개발밀도관리구역"
TARGET_CODE = "UQQ700"
TARGET_STATUS = "UNKNOWN"
RESOLUTION_TYPE = "HYBRID_SPATIAL_NOTICE"

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "law_data" / "output"
OUTPUT_PATH = OUTPUT_DIR / "development_density_management_area_step17_post_seongnam_residual_terminal_reconciliation.json"

SOURCE_SPECS = [
    {
        "source_family": "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY",
        "candidates": [
            "development_density_management_area_gyeonggi_historical_local_gazette_alternate_source_family_terminal_reconciliation.json",
        ],
        "accepted_classifications": {
            "GYEONGGI_HISTORICAL_LOCAL_GAZETTE_ALTERNATE_SOURCE_FAMILY_OPERATIONALLY_CLOSED_NO_VERIFIED_UQQ700_TARGET",
        },
        "terminal_state": "OPERATIONALLY_CLOSED_NO_VERIFIED_TARGET",
        "dispositive": False,
        "note": "Operational closure only; no legal-absence inference.",
    },
    {
        "source_family": "KRIHS_SEARCH_AND_PUBLICATION_CONTEXT_PATH",
        "candidates": [
            "development_density_management_area_krihs_library_detail_identity_verification.json",
            "development_density_management_area_krihs_uqq700_result_identity_hardening.json",
        ],
        "accepted_classifications": {
            "KRIHS_LIBRARY_THREE_PUBLICATION_IDENTITIES_VERIFIED",
            "KRIHS_UQQ700_NO_IDENTIFIABLE_RESULT_LEAD_AFTER_LEXICAL_SCOPING",
        },
        "terminal_state": "NON_DISPOSITIVE_CONTEXT_PATH_CONCLUDED",
        "dispositive": False,
        "note": "Verified publications are contextual leads only, not designation/current-validity/site-inclusion proof.",
    },
    {
        "source_family": "MOLIT_I0204_QUALIFIED_POST_TITLE_SEARCH",
        "candidates": [
            "development_density_management_area_molit_i0204_post_bounded_uqq700_title_search.json",
        ],
        "accepted_classifications": {
            "MOLIT_I0204_POST_BOUNDED_UQQ700_TITLE_SEARCH_NO_RESULT",
        },
        "terminal_state": "QUALIFIED_TITLE_SEARCH_OPERATIONALLY_CLOSED_NO_RESULT",
        "dispositive": False,
        "note": "No-result applies only to the qualified POST title-search path.",
    },
    {
        "source_family": "SEONGNAM_CITY_PLANNING_PLAN_DOCUMENT_ARCHIVE_LEGACY_PDF_BINARY_ACCESS",
        "candidates": [
            "development_density_management_area_seongnam_legacy_pdf_exact_six_recorded_route_family_reconciliation.json",
        ],
        "accepted_classifications": {
            "SEONGNAM_LEGACY_PDF_EXACT_SIX_RECORDED_ROUTE_FAMILIES_RECONCILED_NO_ADDITIONAL_LITERAL_FAMILY",
        },
        "terminal_state": "EXACT_SIX_LEGACY_FILE_ACCESS_OPERATIONALLY_BOUNDED_TECHNICAL_UNRESOLVED",
        "dispositive": False,
        "note": "Exact-six identities/routes recovered; binary access remains unresolved without additional recorded literal route family.",
    },
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def pick_input(candidates: list[str]) -> tuple[Path | None, dict[str, Any] | None, str | None]:
    for name in candidates:
        path = OUTPUT_DIR / name
        if not path.exists():
            continue
        try:
            return path, load_json(path), None
        except Exception as exc:
            return path, None, repr(exc)
    return None, None, "no candidate input found"


def main() -> int:
    print("=" * 86)
    print("DEVELOPMENT DENSITY MANAGEMENT AREA")
    print("STEP17 POST-SEONGNAM RESIDUAL TERMINAL RECONCILIATION")
    print("=" * 86)
    print(f"Target: {TARGET_NAME}")
    print(f"Standard code: {TARGET_CODE}")
    print(f"Resolution type: {RESOLUTION_TYPE}")
    print("Network access: DISABLED")
    print("Negative evidence / legal absence inference: DISABLED")
    print("SITE promotion / runtime registration: DISABLED")
    print()

    source_results: list[dict[str, Any]] = []
    missing_or_invalid = 0

    for spec in SOURCE_SPECS:
        path, data, error = pick_input(spec["candidates"])
        classification = data.get("classification") if isinstance(data, dict) else None
        resolution = data.get("resolution") if isinstance(data, dict) else None
        all_pass = data.get("all_pass") if isinstance(data, dict) else None
        classification_ok = classification in spec["accepted_classifications"]
        resolution_ok = resolution in (None, "UNKNOWN")
        input_valid = bool(path and data is not None and classification_ok and resolution_ok and all_pass is not False)
        if not input_valid:
            missing_or_invalid += 1

        row = {
            "source_family": spec["source_family"],
            "input_path": str(path) if path else None,
            "input_error": error,
            "input_classification": classification,
            "input_resolution": resolution,
            "input_all_pass": all_pass,
            "input_valid": input_valid,
            "terminal_state": spec["terminal_state"] if input_valid else "PREREQUISITE_TECHNICAL_UNKNOWN",
            "dispositive": spec["dispositive"],
            "note": spec["note"],
        }
        source_results.append(row)

    print("SOURCE FAMILY TERMINAL STATES")
    print("-" * 86)
    for row in source_results:
        print(f"SOURCE FAMILY: {row['source_family']}")
        print(f"  input_valid={row['input_valid']}")
        print(f"  input_classification={row['input_classification']}")
        print(f"  terminal_state={row['terminal_state']}")
        print(f"  dispositive={row['dispositive']}")
        print(f"  note={row['note']}")
        print()

    all_inputs_valid = missing_or_invalid == 0
    if all_inputs_valid:
        classification = "STEP17_POST_SEONGNAM_RESIDUAL_SOURCE_FAMILIES_TERMINALLY_RECONCILED_UQQ700_UNKNOWN"
        next_action = "PRESERVE_UQQ700_UNKNOWN_AND_UPDATE_PROJECT_STATUS_OR_HANDOFF_WITHOUT_SITE_PROMOTION_OR_RUNTIME_REGISTRATION"
    else:
        classification = "STEP17_POST_SEONGNAM_RESIDUAL_TERMINAL_RECONCILIATION_PREREQUISITE_TECHNICAL_UNKNOWN"
        next_action = "RESTORE_ONLY_MISSING_LOCAL_PREREQUISITE_OUTPUTS_WITHOUT_NEW_NEGATIVE_EVIDENCE_OR_SOURCE_PROMOTION"

    registration_gate = {
        "official_designation_identity_verified": False,
        "current_validity_verified": False,
        "site_spatial_inclusion_verified": False,
        "minimum_registration_gate_satisfied": False,
    }

    safety = {
        "network_access_used": False,
        "negative_evidence_allowed": False,
        "legal_absence_inference_allowed": False,
        "site_false_inference_allowed": False,
        "site_promotion_allowed": False,
        "runtime_registration_allowed": False,
        "uqq700_resolution": TARGET_STATUS,
    }

    validation = {
        "target_name": TARGET_NAME == "개발밀도관리구역",
        "standard_code": TARGET_CODE == "UQQ700",
        "resolution_type": RESOLUTION_TYPE == "HYBRID_SPATIAL_NOTICE",
        "network_disabled": safety["network_access_used"] is False,
        "negative_evidence_disabled": safety["negative_evidence_allowed"] is False,
        "legal_absence_inference_disabled": safety["legal_absence_inference_allowed"] is False,
        "site_false_inference_disabled": safety["site_false_inference_allowed"] is False,
        "site_promotion_disabled": safety["site_promotion_allowed"] is False,
        "runtime_registration_blocked": safety["runtime_registration_allowed"] is False,
        "uqq700_remains_unknown": safety["uqq700_resolution"] == "UNKNOWN",
        "registration_gate_not_satisfied": registration_gate["minimum_registration_gate_satisfied"] is False,
    }
    all_pass = all(validation.values())

    payload = {
        "target": TARGET_NAME,
        "standard_code": TARGET_CODE,
        "resolution_type": RESOLUTION_TYPE,
        "resolution": TARGET_STATUS,
        "source_family_count": len(SOURCE_SPECS),
        "all_inputs_valid": all_inputs_valid,
        "source_families": source_results,
        "registration_gate": registration_gate,
        "classification": classification,
        "next_action": next_action,
        "safety": safety,
        "validation": validation,
        "all_pass": all_pass,
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 86)
    print("RESOLUTION")
    print("=" * 86)
    print(f"Source family count: {len(SOURCE_SPECS)}")
    print(f"All inputs valid: {all_inputs_valid}")
    print(f"CLASSIFICATION: {classification}")
    print(f"Next action: {next_action}")
    print(f"UQQ700: {TARGET_STATUS}")
    print("OFFICIAL DESIGNATION IDENTITY VERIFIED: False")
    print("CURRENT VALIDITY VERIFIED: False")
    print("SITE SPATIAL INCLUSION VERIFIED: False")
    print("Minimum registration gate satisfied: False")
    print("Negative evidence allowed: False")
    print("Legal absence inference allowed: False")
    print("SITE FALSE inference allowed: False")
    print("SITE promotion allowed: False")
    print("Runtime registration allowed: False")
    print(f"Output: {OUTPUT_PATH}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
