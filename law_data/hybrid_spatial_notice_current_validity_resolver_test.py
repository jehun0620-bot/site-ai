from __future__ import annotations

from datetime import date

from hybrid_spatial_notice_current_validity_resolver import (
    ACT_AMEND_CONTINUE,
    ACT_DESIGNATE,
    ACT_RELEASE,
    CURRENT_RELEASE_VERIFIED,
    CURRENT_VALIDITY_UNKNOWN,
    CURRENT_VALIDITY_VERIFIED,
    VerifiedNoticeAct,
    resolve_current_validity,
)

PASS_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_CURRENT_VALIDITY_RESOLVER_PASS"
FAIL_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_CURRENT_VALIDITY_RESOLVER_REGRESSION"


def act(kind: str, year: int, verified: bool = True, number: str = "") -> VerifiedNoticeAct:
    return VerifiedNoticeAct(
        act_type=kind,
        effective_date=date(year, 1, 1),
        official_designation_identity_verified=verified,
        notice_number=number,
    )


def main() -> int:
    checks: list[tuple[str, bool, str]] = []

    no_history = resolve_current_validity([], search_no_hit=True)
    checks.append((
        "no-hit/no history != legal absence or release",
        no_history["status"] == CURRENT_VALIDITY_UNKNOWN
        and no_history["current_release_verified"] is False
        and no_history["legal_absence_inference_allowed"] is False
        and no_history["history"]["search_no_hit_dispositive"] is False,
        str(no_history["status"]),
    ))

    incomplete = resolve_current_validity(
        [act(ACT_DESIGNATE, 2005, number="2005-1")],
        downstream_history_complete=False,
    )
    checks.append((
        "designation without complete downstream history stays unknown",
        incomplete["status"] == CURRENT_VALIDITY_UNKNOWN
        and incomplete["current_validity_verified"] is False,
        str(incomplete["status"]),
    ))

    current = resolve_current_validity(
        [
            act(ACT_DESIGNATE, 2005, number="2005-1"),
            act(ACT_AMEND_CONTINUE, 2012, number="2012-7"),
        ],
        downstream_history_complete=True,
    )
    checks.append((
        "complete verified designate/amend chain -> current validity verified",
        current["status"] == CURRENT_VALIDITY_VERIFIED
        and current["current_validity_verified"] is True
        and current["current_release_verified"] is False,
        str(current["status"]),
    ))

    released = resolve_current_validity(
        [
            act(ACT_DESIGNATE, 2005),
            act(ACT_AMEND_CONTINUE, 2012),
            act(ACT_RELEASE, 2018, number="2018-9"),
        ],
        downstream_history_complete=False,
    )
    checks.append((
        "explicit verified release -> release verified",
        released["status"] == CURRENT_RELEASE_VERIFIED
        and released["current_validity_verified"] is False
        and released["current_release_verified"] is True,
        str(released["status"]),
    ))

    unverified_release = resolve_current_validity(
        [
            act(ACT_DESIGNATE, 2005),
            act(ACT_RELEASE, 2018, verified=False),
        ],
        downstream_history_complete=True,
    )
    checks.append((
        "unverified release cannot terminate designation",
        unverified_release["status"] == CURRENT_VALIDITY_VERIFIED
        and unverified_release["current_release_verified"] is False
        and unverified_release["history"]["verified_act_count"] == 1,
        str(unverified_release["status"]),
    ))

    reordered = resolve_current_validity(
        [
            act(ACT_RELEASE, 2020),
            act(ACT_DESIGNATE, 2000),
            act(ACT_AMEND_CONTINUE, 2010),
        ],
        downstream_history_complete=True,
    )
    checks.append((
        "timeline is evaluated chronologically",
        reordered["status"] == CURRENT_RELEASE_VERIFIED
        and reordered["history"]["latest_verified_act_type"] == ACT_RELEASE,
        str(reordered["status"]),
    ))

    separation = (
        current["site_spatial_inclusion_verified"] is False
        and current["minimum_registration_gate_satisfied"] is False
        and current["runtime_registration_allowed"] is False
        and current["negative_evidence_allowed"] is False
        and current["site_false_inference_allowed"] is False
        and current["site_promotion_allowed"] is False
    )
    checks.append((
        "validity verification != spatial/runtime promotion",
        separation,
        str(current["status"]),
    ))

    all_pass = all(passed for _, passed, _ in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("HYBRID_SPATIAL_NOTICE CURRENT VALIDITY RESOLVER TEST")
    print("=" * 88)
    print("Network access: DISABLED")
    print("Negative evidence legal inference: DISABLED")
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
