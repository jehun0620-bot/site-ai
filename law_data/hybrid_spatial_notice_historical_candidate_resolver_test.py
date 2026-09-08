from __future__ import annotations

from hybrid_spatial_notice_historical_candidate_resolver import (
    HistoricalNoticeCandidateInput,
    QUALIFIED_HISTORICAL_NOTICE_CANDIDATE,
    REJECTED_AUTHORITY_UNQUALIFIED,
    REJECTED_DOCUMENT_ROLE_WEAK,
    REJECTED_INVALID_URL,
    REJECTED_TARGET_UNBOUND,
    collect_historical_notice_candidates,
    qualify_historical_notice_candidate,
)

PASS_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_HISTORICAL_CANDIDATE_RESOLVER_PASS"
FAIL_CLASSIFICATION = "HYBRID_SPATIAL_NOTICE_HISTORICAL_CANDIDATE_RESOLVER_REGRESSION"


def main() -> int:
    cases = [
        (
            "qualified historical notice candidate",
            HistoricalNoticeCandidateInput(
                url="https://www.seongnam.go.kr/notice/view.do?id=1",
                title="개발밀도관리구역 지정 고시",
                notice_number="성남시 고시 제2001-1호",
                published_date="2001-01-01",
                authority_source_qualified=True,
                target_name_present=True,
                document_role="designation_notice_candidate",
            ),
            QUALIFIED_HISTORICAL_NOTICE_CANDIDATE,
        ),
        (
            "invalid url",
            HistoricalNoticeCandidateInput(
                url="not-a-url",
                authority_source_qualified=True,
                target_name_present=True,
                document_role="notice",
            ),
            REJECTED_INVALID_URL,
        ),
        (
            "authority source must already be qualified",
            HistoricalNoticeCandidateInput(
                url="https://example.com/notice/1",
                authority_source_qualified=False,
                target_name_present=True,
                document_role="notice",
            ),
            REJECTED_AUTHORITY_UNQUALIFIED,
        ),
        (
            "weak document role",
            HistoricalNoticeCandidateInput(
                url="https://www.seongnam.go.kr/news/1",
                authority_source_qualified=True,
                target_name_present=True,
                document_role="press_release",
            ),
            REJECTED_DOCUMENT_ROLE_WEAK,
        ),
        (
            "target name must be bound",
            HistoricalNoticeCandidateInput(
                url="https://www.seongnam.go.kr/notice/2",
                authority_source_qualified=True,
                target_name_present=False,
                document_role="notice",
            ),
            REJECTED_TARGET_UNBOUND,
        ),
    ]

    checks: list[tuple[str, bool, str]] = []

    for label, item, expected in cases:
        result = qualify_historical_notice_candidate(item)
        ok = result.status == expected
        checks.append((label, ok, result.status))

    qualified = qualify_historical_notice_candidate(cases[0][1])
    safety_ok = all(
        value is False
        for value in (
            qualified.official_designation_identity_verified,
            qualified.current_validity_verified,
            qualified.site_spatial_inclusion_verified,
            qualified.runtime_registration_allowed,
            qualified.dispositive,
        )
    )
    checks.append(("candidate != designation identity/current validity/spatial/runtime", safety_ok, qualified.status))

    batch = collect_historical_notice_candidates([case[1] for case in cases])
    batch_ok = [result.status for result in batch] == [case[2] for case in cases]
    checks.append(("batch order/pure qualification", batch_ok, ",".join(result.status for result in batch)))

    all_pass = all(ok for _, ok, _ in checks)
    classification = PASS_CLASSIFICATION if all_pass else FAIL_CLASSIFICATION

    print("=" * 88)
    print("HYBRID_SPATIAL_NOTICE HISTORICAL CANDIDATE RESOLVER TEST")
    print("=" * 88)
    print("Network access: DISABLED")
    print("Designation identity promotion: DISABLED")
    print("Current validity inference: DISABLED")
    print("SITE spatial inclusion inference: DISABLED")
    print("Runtime registration: DISABLED")
    print()

    for label, ok, status in checks:
        print(f"{label}: {'PASS' if ok else 'FAIL'} -> {status}")

    print()
    print(f"CLASSIFICATION: {classification}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
