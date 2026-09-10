from __future__ import annotations

from law_data.historical_site_event_production_readiness_gate import (
    HistoricalSiteEventProductionReadinessEvidence,
    evaluate_historical_site_event_production_readiness,
)


CLASSIFICATION = "HISTORICAL_SITE_EVENT_PRODUCTION_READINESS_GATE_PASS"


def _check(label: str, value: bool) -> tuple[str, bool]:
    return label, bool(value)


def main() -> int:
    empty = evaluate_historical_site_event_production_readiness(
        HistoricalSiteEventProductionReadinessEvidence()
    )

    all_but_standard_code = evaluate_historical_site_event_production_readiness(
        HistoricalSiteEventProductionReadinessEvidence(
            condition_identity_verified=True,
            standard_code_verified=False,
            positive_evidence_contract_ready=True,
            history_completeness_contract_ready=True,
            provenance_policy_verified=True,
            runtime_registration_policy_verified=True,
        )
    )

    contracts_only = evaluate_historical_site_event_production_readiness(
        HistoricalSiteEventProductionReadinessEvidence(
            positive_evidence_contract_ready=True,
            history_completeness_contract_ready=True,
        )
    )

    all_verified = evaluate_historical_site_event_production_readiness(
        HistoricalSiteEventProductionReadinessEvidence(
            condition_identity_verified=True,
            standard_code_verified=True,
            positive_evidence_contract_ready=True,
            history_completeness_contract_ready=True,
            provenance_policy_verified=True,
            runtime_registration_policy_verified=True,
        )
    )

    checks = [
        _check(
            "empty evidence is blocked",
            empty["production_wiring_ready"] is False
            and empty["readiness_state"] == "BLOCKED"
            and empty["verified_gate_count"] == 0,
        ),
        _check(
            "all six gates are required",
            empty["required_gate_count"] == 6
            and len(empty["missing_gates"]) == 6,
        ),
        _check(
            "unverified standard code alone blocks readiness",
            all_but_standard_code["production_wiring_ready"] is False
            and all_but_standard_code["readiness_state"] == "BLOCKED"
            and all_but_standard_code["verified_gate_count"] == 5
            and all_but_standard_code["missing_gates"] == ["standard_code_verified"],
        ),
        _check(
            "contracts alone cannot bypass identity and policy gates",
            contracts_only["production_wiring_ready"] is False
            and contracts_only["verified_gate_count"] == 2
            and "condition_identity_verified" in contracts_only["missing_gates"]
            and "standard_code_verified" in contracts_only["missing_gates"]
            and "provenance_policy_verified" in contracts_only["missing_gates"]
            and "runtime_registration_policy_verified"
            in contracts_only["missing_gates"],
        ),
        _check(
            "all positively verified gates can mark readiness only",
            all_verified["production_wiring_ready"] is True
            and all_verified["readiness_state"] == "READY"
            and all_verified["verified_gate_count"] == 6
            and all_verified["missing_gates"] == [],
        ),
        _check(
            "READY does not itself apply production wiring",
            all_verified["production_wiring_applied"] is False
            and all_verified["overlay_mutated"] is False
            and all_verified["runtime_registry_mutated"] is False,
        ),
        _check(
            "negative and legal absence inference stay disabled",
            all_verified["negative_evidence_inference_allowed"] is False
            and all_verified["legal_absence_inference_allowed"] is False,
        ),
        _check(
            "promotion guards remain explicit",
            all(value is False for value in all_verified["promotion_guards"].values()),
        ),
    ]

    all_pass = all(value for _, value in checks)

    print("=" * 72)
    print("HISTORICAL SITE EVENT PRODUCTION READINESS GATE")
    print("=" * 72)
    for label, value in checks:
        print(f"{label}: {value}")
    print("-" * 72)
    print("all_pass:", all_pass)
    print("CLASSIFICATION:", CLASSIFICATION if all_pass else "FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
