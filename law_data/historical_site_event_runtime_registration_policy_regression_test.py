from __future__ import annotations

from law_data.historical_site_event_resolver import (
    FALSE,
    RESOLUTION_TYPE,
    TRUE_CANDIDATE,
    UNKNOWN,
)
from law_data.historical_site_event_runtime_registration_policy import (
    HistoricalSiteEventRuntimeRegistrationEvidence,
    evaluate_historical_site_event_runtime_registration_policy,
)


CLASSIFICATION = "HISTORICAL_SITE_EVENT_RUNTIME_REGISTRATION_POLICY_PASS"


def _evaluate(
    *,
    production_wiring_ready: bool = True,
    standard_code_verified: bool = True,
    provenance_policy_verified: bool = True,
    resolver_type: str = RESOLUTION_TYPE,
    resolution: str = UNKNOWN,
) -> dict[str, object]:
    return evaluate_historical_site_event_runtime_registration_policy(
        HistoricalSiteEventRuntimeRegistrationEvidence(
            production_wiring_ready=production_wiring_ready,
            standard_code_verified=standard_code_verified,
            provenance_policy_verified=provenance_policy_verified,
            resolver_type=resolver_type,
            resolution=resolution,
        )
    )


def _check(label: str, value: bool) -> tuple[str, bool]:
    return label, bool(value)


def main() -> int:
    empty = evaluate_historical_site_event_runtime_registration_policy(
        HistoricalSiteEventRuntimeRegistrationEvidence()
    )
    unknown = _evaluate(resolution=UNKNOWN)
    true_candidate = _evaluate(resolution=TRUE_CANDIDATE)
    false_resolution = _evaluate(resolution=FALSE)
    no_wiring = _evaluate(production_wiring_ready=False)
    no_standard_code = _evaluate(standard_code_verified=False)
    no_provenance = _evaluate(provenance_policy_verified=False)
    wrong_type = _evaluate(resolver_type="HYBRID_SPATIAL_NOTICE")
    unsupported_resolution = _evaluate(resolution="TRUE")

    checks = [
        _check(
            "empty evidence is registration blocked",
            empty["registration_eligible"] is False
            and empty["registration_state"] == "BLOCKED",
        ),
        _check(
            "production wiring readiness is mandatory",
            no_wiring["registration_eligible"] is False
            and "production_wiring_ready" in no_wiring["missing_gates"],
        ),
        _check(
            "verified standard code is mandatory",
            no_standard_code["registration_eligible"] is False
            and "standard_code_verified" in no_standard_code["missing_gates"],
        ),
        _check(
            "verified provenance policy is mandatory",
            no_provenance["registration_eligible"] is False
            and "provenance_policy_verified" in no_provenance["missing_gates"],
        ),
        _check(
            "resolver type must be HISTORICAL_SITE_EVENT",
            wrong_type["registration_eligible"] is False
            and "resolver_type_verified" in wrong_type["missing_gates"],
        ),
        _check(
            "unsupported resolution is blocked",
            unsupported_resolution["registration_eligible"] is False
            and "resolution_supported" in unsupported_resolution["missing_gates"],
        ),
        _check(
            "UNKNOWN can be policy-eligible without SITE promotion",
            unknown["registration_eligible"] is True
            and unknown["resolution_semantics"][
                "unknown_is_registered_as_site_false"
            ]
            is False
            and unknown["resolution_semantics"][
                "unknown_is_registered_as_site_true"
            ]
            is False,
        ),
        _check(
            "TRUE_CANDIDATE can be policy-eligible without SITE TRUE promotion",
            true_candidate["registration_eligible"] is True
            and true_candidate["resolution_semantics"][
                "true_candidate_is_registered_as_site_true"
            ]
            is False
            and true_candidate["resolution_semantics"][
                "true_candidate_is_registered_as_site_false"
            ]
            is False,
        ),
        _check(
            "FALSE can be policy-eligible but is never inferred by policy",
            false_resolution["registration_eligible"] is True
            and false_resolution["resolution_semantics"][
                "false_is_inferred_from_registration_policy"
            ]
            is False,
        ),
        _check(
            "all allowed historical resolutions are explicit",
            set(unknown["allowed_resolutions"])
            == {UNKNOWN, TRUE_CANDIDATE, FALSE},
        ),
        _check(
            "negative and legal absence inference remain disabled",
            unknown["negative_evidence_inference_allowed"] is False
            and unknown["legal_absence_inference_allowed"] is False,
        ),
        _check(
            "eligibility never performs runtime mutation",
            all(
                result["runtime_registry_mutated"] is False
                and result["overlay_mutated"] is False
                and result["site_promotion_applied"] is False
                and result["production_wiring_applied"] is False
                for result in (unknown, true_candidate, false_resolution)
            ),
        ),
    ]

    all_pass = all(value for _, value in checks)

    print("=" * 72)
    print("HISTORICAL SITE EVENT RUNTIME REGISTRATION POLICY")
    print("=" * 72)
    for label, value in checks:
        print(f"{label}: {value}")
    print("-" * 72)
    print("all_pass:", all_pass)
    print("CLASSIFICATION:", CLASSIFICATION if all_pass else "FAIL")

    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
