from __future__ import annotations

from pathlib import Path

from hybrid_spatial_notice_uqq700_production_adapter import (
    Uqq700ProductionAdapterInput,
    adapt_uqq700_production_state,
)


PASS_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_SEAM_ISOLATION_PASS"
)
FAIL_CLASSIFICATION = (
    "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_SEAM_ISOLATION_REGRESSION"
)

BASE_DIR = Path(__file__).resolve().parent
PRODUCTION_SEAM_PATH = BASE_DIR / "development_density_management_evidence_resolution_test.py"

VERIFIED_PATH_TOKENS = (
    "hybrid_spatial_notice_uqq700_designation_document_provenance_verifier",
    "hybrid_spatial_notice_uqq700_verified_provenance_identity_adapter",
    "adapt_verified_uqq700_provenance_to_identity",
    "verify_uqq700_designation_document_provenance",
)


def main() -> int:
    checks: list[tuple[str, bool]] = []

    source = PRODUCTION_SEAM_PATH.read_text(encoding="utf-8")

    checks.append(
        (
            "production seam does not import verified Gate-1 path",
            all(token not in source for token in VERIFIED_PATH_TOKENS),
        )
    )
    checks.append(
        (
            "production seam keeps explicitly empty positive-stage input",
            "Uqq700ProductionAdapterInput()" in source,
        )
    )
    checks.append(
        (
            "production seam does not populate designation_identity",
            "designation_identity=" not in source,
        )
    )
    checks.append(
        (
            "production seam records positive-stage inputs as not wired",
            '"positive_stage_inputs_wired": False' in source,
        )
    )

    diagnostics_only = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(),
        search_hit=True,
        http_200=True,
        negative_evidence={
            "announcement_no_hit": True,
            "candidate_layer_no_hit": True,
            "site_non_display": True,
        },
    )

    gates = diagnostics_only["positive_gates"]
    checks.append(
        (
            "diagnostics cannot activate Gate 1",
            gates["official_designation_identity_verified"] is False,
        )
    )
    checks.append(
        (
            "diagnostics cannot activate Gate 2",
            gates["current_validity_verified"] is False,
        )
    )
    checks.append(
        (
            "diagnostics cannot activate Gate 3",
            gates["site_spatial_inclusion_verified"] is False,
        )
    )
    checks.append(
        (
            "minimum registration gate remains closed",
            diagnostics_only["minimum_registration_gate_satisfied"] is False,
        )
    )
    checks.append(
        (
            "runtime registration remains disabled",
            diagnostics_only["runtime_registration_allowed"] is False,
        )
    )
    checks.append(
        (
            "resolution remains UNKNOWN",
            diagnostics_only["resolution"] == "UNKNOWN",
        )
    )
    checks.append(
        (
            "SITE promotion and SITE TRUE inference remain disabled",
            diagnostics_only["site_promotion_allowed"] is False
            and diagnostics_only["site_true_inference_allowed"] is False,
        )
    )
    checks.append(
        (
            "negative/legal-absence/SITE-FALSE inference remain disabled",
            diagnostics_only["negative_evidence_allowed"] is False
            and diagnostics_only["legal_absence_inference_allowed"] is False
            and diagnostics_only["site_false_inference_allowed"] is False,
        )
    )
    checks.append(
        (
            "production adapter remains non-mutating",
            diagnostics_only["production_wiring_applied"] is False
            and diagnostics_only["runtime_registry_mutated"] is False,
        )
    )

    all_pass = all(passed for _, passed in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 96)
    print("UQQ700 HYBRID_SPATIAL_NOTICE PRODUCTION SEAM ISOLATION TEST")
    print("=" * 96)
    print("Verified Gate-1 production import: DISALLOWED")
    print("Positive-stage production wiring: DISALLOWED")
    print("Diagnostic Gate promotion: DISALLOWED")
    print("Runtime registration mutation: DISABLED")
    print()

    for label, passed in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'}")

    print()
    print(f"CLASSIFICATION: {classification}")
    print(f"all_pass: {all_pass}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
