from __future__ import annotations

from law_data.urban_area_conversion_production_readiness_adapter import (
    ADAPTER_MODE,
    CONDITION_NAME,
    adapt_urban_area_conversion_production_readiness,
)


CLASSIFICATION = "URBAN_AREA_CONVERSION_PRODUCTION_READINESS_ADAPTER_PASS"


def _check(label: str, value: bool) -> tuple[str, bool]:
    return label, bool(value)


def main() -> int:
    result = adapt_urban_area_conversion_production_readiness()
    readiness = result["readiness"]
    gates = readiness["gates"]
    semantics = result["semantic_contract"]
    blockers = result["condition_specific_blockers"]

    checks = [
        _check(
            "condition identity is explicitly mapped",
            result["condition"] == CONDITION_NAME
            and gates["condition_identity_verified"] is True,
        ),
        _check(
            "standard code remains unverified",
            gates["standard_code_verified"] is False
            and blockers["standard_code_unverified"] is True,
        ),
        _check(
            "positive evidence contract implementation is ready",
            gates["positive_evidence_contract_ready"] is True
            and semantics["positive_evidence_contract_ready"] is True,
        ),
        _check(
            "positive contract readiness does not assert actual event evidence",
            semantics["actual_verified_qualifying_event_present"] is False
            and result["promotion_guards"][
                "contract_readiness_promoted_to_evidence_satisfaction"
            ]
            is False,
        ),
        _check(
            "history completeness contract implementation is ready",
            gates["history_completeness_contract_ready"] is True
            and semantics["history_completeness_contract_ready"] is True,
        ),
        _check(
            "completeness contract readiness does not assert actual completeness",
            semantics["actual_history_scope_complete_verified"] is False,
        ),
        _check(
            "provenance policy remains unverified",
            gates["provenance_policy_verified"] is False
            and blockers["provenance_policy_unverified"] is True,
        ),
        _check(
            "runtime registration policy remains unverified",
            gates["runtime_registration_policy_verified"] is False
            and blockers["runtime_registration_policy_unverified"] is True,
        ),
        _check(
            "current readiness is exactly three of six gates",
            readiness["verified_gate_count"] == 3
            and readiness["required_gate_count"] == 6,
        ),
        _check(
            "current condition remains production blocked",
            readiness["production_wiring_ready"] is False
            and readiness["readiness_state"] == "BLOCKED",
        ),
        _check(
            "missing gates are the three condition-specific blockers",
            readiness["missing_gates"]
            == [
                "standard_code_verified",
                "provenance_policy_verified",
                "runtime_registration_policy_verified",
            ],
        ),
        _check(
            "condition name cannot manufacture a standard code",
            result["promotion_guards"]["condition_name_promoted_to_standard_code"]
            is False,
        ),
        _check(
            "UNKNOWN cannot manufacture runtime registration",
            result["promotion_guards"][
                "current_unknown_resolution_promoted_to_runtime_registration"
            ]
            is False,
        ),
        _check(
            "adapter remains read-only and production-unwired",
            result["adapter_mode"] == ADAPTER_MODE
            and result["output_written"] is False
            and result["production_wiring_applied"] is False
            and result["overlay_mutated"] is False
            and result["runtime_registry_mutated"] is False
            and readiness["production_wiring_applied"] is False
            and readiness["overlay_mutated"] is False
            and readiness["runtime_registry_mutated"] is False,
        ),
        _check(
            "contract readiness semantics are explicit",
            semantics[
                "contract_ready_means_implementation_ready_not_evidence_satisfied"
            ]
            is True,
        ),
    ]

    all_pass = all(value for _, value in checks)

    print("=" * 72)
    print("URBAN AREA CONVERSION PRODUCTION READINESS ADAPTER")
    print("=" * 72)
    for label, value in checks:
        print(f"{label}: {value}")
    print("-" * 72)
    print("all_pass:", all_pass)
    print("CLASSIFICATION:", CLASSIFICATION if all_pass else "FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
