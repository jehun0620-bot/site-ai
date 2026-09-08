from __future__ import annotations

from hybrid_spatial_notice_site_spatial_inclusion_verifier import (
    REJECTED_CURRENT_VALIDITY_UNVERIFIED,
    REJECTED_DESIGNATION_GEOMETRY_UNBOUND,
    REJECTED_DESIGNATION_IDENTITY_UNVERIFIED,
    REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION,
    REJECTED_SITE_GEOMETRY_UNBOUND,
    REJECTED_SPATIAL_SOURCE_UNOFFICIAL,
    VERIFIED,
    SiteSpatialEvidence,
    verify_many,
    verify_site_spatial_inclusion,
)

PASS_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_SITE_SPATIAL_INCLUSION_VERIFIER_PASS"
FAIL_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_SITE_SPATIAL_INCLUSION_VERIFIER_REGRESSION"


def evidence(**overrides: bool) -> SiteSpatialEvidence:
    values = {
        "official_designation_identity_verified": True,
        "current_validity_verified": True,
        "official_spatial_source_verified": True,
        "designation_geometry_bound": True,
        "site_geometry_bound": True,
        "positive_spatial_intersection_verified": True,
    }
    values.update(overrides)
    return SiteSpatialEvidence(**values)


def main() -> int:
    cases = [
        ("positive official spatial intersection", evidence(), VERIFIED, True),
        (
            "designation identity required",
            evidence(official_designation_identity_verified=False),
            REJECTED_DESIGNATION_IDENTITY_UNVERIFIED,
            False,
        ),
        (
            "current validity required",
            evidence(current_validity_verified=False),
            REJECTED_CURRENT_VALIDITY_UNVERIFIED,
            False,
        ),
        (
            "official spatial source required",
            evidence(official_spatial_source_verified=False),
            REJECTED_SPATIAL_SOURCE_UNOFFICIAL,
            False,
        ),
        (
            "designation geometry required",
            evidence(designation_geometry_bound=False),
            REJECTED_DESIGNATION_GEOMETRY_UNBOUND,
            False,
        ),
        (
            "site geometry required",
            evidence(site_geometry_bound=False),
            REJECTED_SITE_GEOMETRY_UNBOUND,
            False,
        ),
        (
            "positive spatial intersection required",
            evidence(positive_spatial_intersection_verified=False),
            REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION,
            False,
        ),
    ]

    checks: list[tuple[str, bool, str]] = []
    for label, item, expected_status, expected_verified in cases:
        result = verify_site_spatial_inclusion(item)
        passed = (
            result["status"] == expected_status
            and result["site_spatial_inclusion_verified"] is expected_verified
        )
        checks.append((label, passed, result["status"]))

    weak_hits = verify_site_spatial_inclusion(
        evidence(positive_spatial_intersection_verified=False),
        address_name_hit=True,
        search_hit=True,
        candidate_layer_hit=True,
    )
    checks.append(
        (
            "address/search/candidate-layer hits != spatial inclusion",
            weak_hits["site_spatial_inclusion_verified"] is False
            and weak_hits["diagnostic_discovery"]["dispositive"] is False,
            weak_hits["status"],
        )
    )

    no_hits = verify_site_spatial_inclusion(
        evidence(positive_spatial_intersection_verified=False),
        address_name_hit=False,
        search_hit=False,
        candidate_layer_hit=False,
    )
    checks.append(
        (
            "no-hit != SITE FALSE/legal absence",
            no_hits["site_false_inference_allowed"] is False
            and no_hits["legal_absence_inference_allowed"] is False
            and no_hits["negative_evidence_allowed"] is False,
            no_hits["status"],
        )
    )

    verified = verify_site_spatial_inclusion(evidence())
    checks.append(
        (
            "spatial verification alone does not register/promote SITE",
            verified["site_spatial_inclusion_verified"] is True
            and verified["minimum_registration_gate_satisfied"] is False
            and verified["runtime_registration_allowed"] is False
            and verified["site_promotion_allowed"] is False,
            verified["status"],
        )
    )

    batch = verify_many(
        [
            evidence(),
            evidence(current_validity_verified=False),
            evidence(official_spatial_source_verified=False),
            evidence(positive_spatial_intersection_verified=False),
        ]
    )
    batch_statuses = [row["status"] for row in batch]
    batch_expected = [
        VERIFIED,
        REJECTED_CURRENT_VALIDITY_UNVERIFIED,
        REJECTED_SPATIAL_SOURCE_UNOFFICIAL,
        REJECTED_NO_POSITIVE_SPATIAL_INTERSECTION,
    ]
    checks.append(
        (
            "batch order/pure verification",
            batch_statuses == batch_expected,
            ",".join(batch_statuses),
        )
    )

    all_pass = all(passed for _, passed, _ in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("HYBRID_SPATIAL_NOTICE SITE SPATIAL INCLUSION VERIFIER TEST")
    print("=" * 88)
    print("Network access: DISABLED")
    print("Negative evidence SITE FALSE inference: DISABLED")
    print("SITE promotion: DISABLED")
    print("Runtime registration: DISABLED")
    print()

    for label, passed, status in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'} -> {status}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
