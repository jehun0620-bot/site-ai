from __future__ import annotations

from hybrid_spatial_notice_designation_identity_verifier import (
    DesignationIdentityEvidence,
    REJECTED_AUTHORITY_UNQUALIFIED,
    REJECTED_CANDIDATE_UNQUALIFIED,
    REJECTED_DESIGNATION_ACT_UNBOUND,
    REJECTED_NOTICE_IDENTITY_INSUFFICIENT,
    REJECTED_TARGET_UNBOUND,
    VERIFIED,
    verify_designation_identity,
    verify_many,
)

PASS_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_DESIGNATION_IDENTITY_VERIFIER_PASS"
FAIL_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_DESIGNATION_IDENTITY_VERIFIER_REGRESSION"


def evidence(**overrides: bool) -> DesignationIdentityEvidence:
    values = {
        "candidate_qualified": True,
        "authority_source_qualified": True,
        "target_name_bound": True,
        "designation_act_bound": True,
        "notice_number_bound": True,
        "issuing_authority_bound": True,
        "effective_or_notice_date_bound": True,
    }
    values.update(overrides)
    return DesignationIdentityEvidence(**values)


def main() -> int:
    cases = [
        (
            "verified official designation identity",
            evidence(),
            VERIFIED,
            True,
        ),
        (
            "candidate must already be qualified",
            evidence(candidate_qualified=False),
            REJECTED_CANDIDATE_UNQUALIFIED,
            False,
        ),
        (
            "authority source must already be qualified",
            evidence(authority_source_qualified=False),
            REJECTED_AUTHORITY_UNQUALIFIED,
            False,
        ),
        (
            "target must be bound",
            evidence(target_name_bound=False),
            REJECTED_TARGET_UNBOUND,
            False,
        ),
        (
            "designation act must be bound",
            evidence(designation_act_bound=False),
            REJECTED_DESIGNATION_ACT_UNBOUND,
            False,
        ),
        (
            "notice number required",
            evidence(notice_number_bound=False),
            REJECTED_NOTICE_IDENTITY_INSUFFICIENT,
            False,
        ),
        (
            "issuing authority required",
            evidence(issuing_authority_bound=False),
            REJECTED_NOTICE_IDENTITY_INSUFFICIENT,
            False,
        ),
        (
            "notice/effective date required",
            evidence(effective_or_notice_date_bound=False),
            REJECTED_NOTICE_IDENTITY_INSUFFICIENT,
            False,
        ),
    ]

    checks: list[tuple[str, bool, str]] = []
    for label, item, expected_status, expected_verified in cases:
        result = verify_designation_identity(item)
        passed = (
            result["status"] == expected_status
            and result["official_designation_identity_verified"] is expected_verified
        )
        checks.append((label, passed, result["status"]))

    verified = verify_designation_identity(evidence())
    separation_check = (
        verified["official_designation_identity_verified"] is True
        and verified["current_validity_verified"] is False
        and verified["site_spatial_inclusion_verified"] is False
        and verified["minimum_registration_gate_satisfied"] is False
        and verified["runtime_registration_allowed"] is False
        and verified["site_false_inference_allowed"] is False
        and verified["site_promotion_allowed"] is False
        and verified["legal_absence_inference_allowed"] is False
        and verified["negative_evidence_allowed"] is False
    )
    checks.append(
        (
            "identity verification != validity/spatial/runtime promotion",
            separation_check,
            verified["status"],
        )
    )

    batch = verify_many(
        [
            evidence(),
            evidence(candidate_qualified=False),
            evidence(target_name_bound=False),
            evidence(notice_number_bound=False),
        ]
    )
    batch_statuses = [row["status"] for row in batch]
    batch_expected = [
        VERIFIED,
        REJECTED_CANDIDATE_UNQUALIFIED,
        REJECTED_TARGET_UNBOUND,
        REJECTED_NOTICE_IDENTITY_INSUFFICIENT,
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
    print("HYBRID_SPATIAL_NOTICE DESIGNATION IDENTITY VERIFIER TEST")
    print("=" * 88)
    print("Network access: DISABLED")
    print("Current validity inference: DISABLED")
    print("SITE spatial inclusion inference: DISABLED")
    print("Runtime registration: DISABLED")
    print()

    for label, passed, status in checks:
        print(f"{label}: {'PASS' if passed else 'FAIL'} -> {status}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
