from __future__ import annotations

from itertools import product

from hybrid_spatial_notice_uqq700_production_adapter import (
    Uqq700ProductionAdapterInput,
    adapt_uqq700_production_state,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_ADAPTER_PASS"


def _stage_input(identity: bool, validity: bool, spatial: bool) -> Uqq700ProductionAdapterInput:
    return Uqq700ProductionAdapterInput(
        authority={"authority_source_qualified": True},
        historical_candidate={"historical_notice_candidate_qualified": True},
        designation_identity={
            "official_designation_identity_verified": identity,
        },
        current_validity={
            "current_validity_verified": validity,
        },
        site_spatial_inclusion={
            "site_spatial_inclusion_verified": spatial,
        },
    )


def _check_case(identity: bool, validity: bool, spatial: bool) -> list[tuple[str, bool]]:
    result = adapt_uqq700_production_state(
        _stage_input(identity, validity, spatial),
        search_hit=True,
        http_200=True,
        negative_evidence={"search_no_hit": True, "site_non_display": True},
    )
    expected_runtime = identity and validity and spatial
    gates = result["positive_gates"]

    return [
        ("target UQQ700", result.get("standard_code") == "UQQ700"),
        ("resolution type", result.get("resolution_type") == "HYBRID_SPATIAL_NOTICE"),
        ("resolution UNKNOWN", result.get("resolution") == "UNKNOWN"),
        ("identity exact mirror", gates.get("official_designation_identity_verified") is identity),
        ("validity exact mirror", gates.get("current_validity_verified") is validity),
        ("spatial exact mirror", gates.get("site_spatial_inclusion_verified") is spatial),
        ("minimum gate strict AND", result.get("minimum_registration_gate_satisfied") is expected_runtime),
        ("runtime registration strict AND", result.get("runtime_registration_allowed") is expected_runtime),
        ("negative evidence disabled", result.get("negative_evidence_allowed") is False),
        ("legal absence disabled", result.get("legal_absence_inference_allowed") is False),
        ("SITE FALSE disabled", result.get("site_false_inference_allowed") is False),
        ("SITE promotion disabled", result.get("site_promotion_allowed") is False),
        ("SITE TRUE inference disabled", result.get("site_true_inference_allowed") is False),
        ("production wiring not applied", result.get("production_wiring_applied") is False),
        ("runtime registry not mutated", result.get("runtime_registry_mutated") is False),
        ("diagnostics non-dispositive", result.get("diagnostic_discovery", {}).get("dispositive") is False),
    ]


def main() -> int:
    all_checks: list[tuple[str, bool]] = []

    for identity, validity, spatial in product((False, True), repeat=3):
        label = f"I={identity} V={validity} S={spatial}"
        checks = _check_case(identity, validity, spatial)
        case_pass = all(ok for _, ok in checks)
        all_checks.append((label, case_pass))
        print(label, "PASS" if case_pass else "FAIL")
        for name, ok in checks:
            if not ok:
                print("  FAIL:", name)

    baseline = adapt_uqq700_production_state(Uqq700ProductionAdapterInput())
    baseline_checks = [
        ("baseline resolution UNKNOWN", baseline.get("resolution") == "UNKNOWN"),
        ("baseline minimum gate false", baseline.get("minimum_registration_gate_satisfied") is False),
        ("baseline runtime false", baseline.get("runtime_registration_allowed") is False),
        ("baseline identity false", baseline.get("positive_gates", {}).get("official_designation_identity_verified") is False),
        ("baseline validity false", baseline.get("positive_gates", {}).get("current_validity_verified") is False),
        ("baseline spatial false", baseline.get("positive_gates", {}).get("site_spatial_inclusion_verified") is False),
        ("baseline no SITE promotion", baseline.get("site_promotion_allowed") is False),
        ("baseline no registry mutation", baseline.get("runtime_registry_mutated") is False),
    ]
    baseline_pass = all(ok for _, ok in baseline_checks)
    all_checks.append(("UQQ700 empty baseline", baseline_pass))
    print("UQQ700 empty baseline", "PASS" if baseline_pass else "FAIL")
    for name, ok in baseline_checks:
        if not ok:
            print("  FAIL:", name)

    all_pass = all(ok for _, ok in all_checks)
    print("CLASSIFICATION:", PASS_CLASSIFICATION if all_pass else "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_ADAPTER_FAIL")
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
