from __future__ import annotations

from itertools import product

from hybrid_spatial_notice_orchestrator import (
    HybridSpatialNoticeStageResults,
    orchestrate_hybrid_spatial_notice,
)


PASS_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_ORCHESTRATOR_REGRESSION_MATRIX_PASS"
FAIL_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_ORCHESTRATOR_REGRESSION_MATRIX_REGRESSION"


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    for identity, validity, spatial in product([False, True], repeat=3):
        result = orchestrate_hybrid_spatial_notice(
            HybridSpatialNoticeStageResults(
                designation_identity={
                    "official_designation_identity_verified": identity,
                },
                current_validity={
                    "current_validity_verified": validity,
                },
                site_spatial_inclusion={
                    "site_spatial_inclusion_verified": spatial,
                },
            ),
            search_hit=True,
            http_200=True,
            negative_evidence={
                "search_no_hit": False,
                "site_non_display": False,
            },
        )

        expected_gate = identity and validity and spatial
        label = f"I={identity} V={validity} S={spatial}"
        passed = (
            result["positive_gates"][
                "official_designation_identity_verified"
            ] is identity
            and result["positive_gates"]["current_validity_verified"] is validity
            and result["positive_gates"][
                "site_spatial_inclusion_verified"
            ] is spatial
            and result["minimum_registration_gate_satisfied"] is expected_gate
            and result["runtime_registration_allowed"] is expected_gate
            and result["resolution"] == "UNKNOWN"
            and result["negative_evidence_allowed"] is False
            and result["legal_absence_inference_allowed"] is False
            and result["site_false_inference_allowed"] is False
            and result["site_promotion_allowed"] is False
            and result["diagnostic_discovery"]["dispositive"] is False
        )
        checks.append((label, passed, str(expected_gate)))

    discovery_only = orchestrate_hybrid_spatial_notice(
        HybridSpatialNoticeStageResults(),
        search_hit=True,
        http_200=True,
        negative_evidence={
            "search_no_hit": False,
            "site_non_display": False,
            "candidate_layer_no_hit": False,
        },
    )
    checks.append(
        (
            "search hit + HTTP 200 cannot promote gates",
            discovery_only["positive_gates"][
                "official_designation_identity_verified"
            ] is False
            and discovery_only["positive_gates"][
                "current_validity_verified"
            ] is False
            and discovery_only["positive_gates"][
                "site_spatial_inclusion_verified"
            ] is False
            and discovery_only["runtime_registration_allowed"] is False,
            discovery_only["resolution"],
        )
    )

    negative_only = orchestrate_hybrid_spatial_notice(
        HybridSpatialNoticeStageResults(),
        search_hit=False,
        http_200=False,
        negative_evidence={
            "search_no_hit": True,
            "site_non_display": True,
            "candidate_layer_no_hit": True,
        },
    )
    checks.append(
        (
            "negative evidence cannot infer absence/SITE FALSE",
            negative_only["negative_evidence_allowed"] is False
            and negative_only["legal_absence_inference_allowed"] is False
            and negative_only["site_false_inference_allowed"] is False
            and negative_only["runtime_registration_allowed"] is False
            and negative_only["resolution"] == "UNKNOWN",
            negative_only["resolution"],
        )
    )

    all_pass = all(passed for _, passed, _ in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("HYBRID_SPATIAL_NOTICE ORCHESTRATOR REGRESSION MATRIX TEST")
    print("=" * 88)
    print("Runtime mutation: DISABLED")
    print("SITE mutation: DISABLED")
    print("Negative evidence legal inference: DISABLED")
    print()

    for label, passed, detail in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'} -> {detail}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
