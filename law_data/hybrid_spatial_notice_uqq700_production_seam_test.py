from __future__ import annotations

from hybrid_spatial_notice_uqq700_production_adapter import (
    Uqq700ProductionAdapterInput,
    adapt_uqq700_production_state,
)


PASS_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_SEAM_PASS"
FAIL_CLASSIFICATION = "UQQ700_HYBRID_SPATIAL_NOTICE_PRODUCTION_SEAM_REGRESSION"


def main() -> int:
    checks: list[tuple[str, bool]] = []

    baseline = adapt_uqq700_production_state(Uqq700ProductionAdapterInput())
    gates = baseline.get("positive_gates", {})
    checks.extend(
        [
            ("baseline UQQ700", baseline.get("standard_code") == "UQQ700"),
            ("baseline resolution UNKNOWN", baseline.get("resolution") == "UNKNOWN"),
            (
                "baseline identity unverified",
                gates.get("official_designation_identity_verified") is False,
            ),
            (
                "baseline validity unverified",
                gates.get("current_validity_verified") is False,
            ),
            (
                "baseline spatial unverified",
                gates.get("site_spatial_inclusion_verified") is False,
            ),
            (
                "baseline minimum gate false",
                baseline.get("minimum_registration_gate_satisfied") is False,
            ),
            (
                "baseline runtime registration false",
                baseline.get("runtime_registration_allowed") is False,
            ),
            (
                "baseline negative evidence disabled",
                baseline.get("negative_evidence_allowed") is False,
            ),
            (
                "baseline legal absence disabled",
                baseline.get("legal_absence_inference_allowed") is False,
            ),
            (
                "baseline SITE FALSE disabled",
                baseline.get("site_false_inference_allowed") is False,
            ),
            (
                "baseline SITE promotion disabled",
                baseline.get("site_promotion_allowed") is False,
            ),
            (
                "baseline SITE TRUE inference disabled",
                baseline.get("site_true_inference_allowed") is False,
            ),
            (
                "baseline production wiring mutation false",
                baseline.get("production_wiring_applied") is False,
            ),
            (
                "baseline runtime registry mutation false",
                baseline.get("runtime_registry_mutated") is False,
            ),
        ]
    )

    discovery_hit = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(),
        search_hit=True,
        http_200=True,
        negative_evidence={"announcement_no_hit": False},
    )
    hit_gates = discovery_hit.get("positive_gates", {})
    checks.extend(
        [
            (
                "search hit cannot verify identity",
                hit_gates.get("official_designation_identity_verified") is False,
            ),
            (
                "HTTP 200 cannot verify validity",
                hit_gates.get("current_validity_verified") is False,
            ),
            (
                "discovery cannot verify spatial inclusion",
                hit_gates.get("site_spatial_inclusion_verified") is False,
            ),
            (
                "discovery hit stays UNKNOWN",
                discovery_hit.get("resolution") == "UNKNOWN",
            ),
            (
                "discovery hit cannot register runtime",
                discovery_hit.get("runtime_registration_allowed") is False,
            ),
            (
                "discovery hit diagnostic only",
                discovery_hit.get("diagnostic_discovery", {}).get("dispositive")
                is False,
            ),
        ]
    )

    negative = adapt_uqq700_production_state(
        Uqq700ProductionAdapterInput(),
        search_hit=False,
        http_200=False,
        negative_evidence={
            "announcement_no_hit": True,
            "candidate_layer_no_hit": True,
            "site_non_display": True,
        },
    )
    checks.extend(
        [
            ("negative evidence stays UNKNOWN", negative.get("resolution") == "UNKNOWN"),
            (
                "negative evidence cannot infer legal absence",
                negative.get("legal_absence_inference_allowed") is False,
            ),
            (
                "negative evidence cannot infer SITE FALSE",
                negative.get("site_false_inference_allowed") is False,
            ),
            (
                "negative evidence cannot promote SITE",
                negative.get("site_promotion_allowed") is False,
            ),
            (
                "negative evidence cannot register runtime",
                negative.get("runtime_registration_allowed") is False,
            ),
            (
                "negative evidence diagnostic only",
                negative.get("diagnostic_discovery", {}).get("dispositive") is False,
            ),
        ]
    )

    all_pass = all(ok for _, ok in checks)

    print("=" * 88)
    print("UQQ700 HYBRID_SPATIAL_NOTICE PRODUCTION SEAM TEST")
    print("=" * 88)
    print("Positive stage inputs wired: False")
    print("Runtime registry mutation: DISABLED")
    print("SITE mutation: DISABLED")
    print()
    for name, ok in checks:
        print(f"{name}: {'PASS' if ok else 'FAIL'}")
    print()
    print("CLASSIFICATION:", PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION)
    print("all_pass:", all_pass)
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
