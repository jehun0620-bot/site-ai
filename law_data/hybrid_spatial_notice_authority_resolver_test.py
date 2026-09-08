from __future__ import annotations

from hybrid_spatial_notice_authority_resolver import (
    AuthorityQualification,
    AuthoritySourceCandidate,
    qualify_authority_source,
    qualify_authority_sources,
)


def make_candidate(**overrides):
    values = {
        "url": "https://www.example.go.kr/notice/list",
        "authority_name": "예시시",
        "region": "예시도 예시시",
        "title": "고시·공고",
        "heading": "고시·공고",
        "breadcrumb": "홈 > 행정정보 > 고시·공고",
        "endpoint_role": "HISTORICAL_NOTICE_ENTRY",
        "official_host_verified": True,
        "region_binding_verified": True,
        "entry_endpoint_verified": True,
        "role_verified": True,
    }
    values.update(overrides)
    return AuthoritySourceCandidate(**values)


def assert_safety_contract(result):
    assert result["designation_identity_verified"] is False
    assert result["current_validity_verified"] is False
    assert result["site_spatial_inclusion_verified"] is False
    assert result["minimum_registration_gate_satisfied"] is False
    assert result["runtime_registration_allowed"] is False
    assert result["site_promotion_allowed"] is False
    assert result["site_false_inference_allowed"] is False
    assert result["legal_absence_inference_allowed"] is False
    assert result["negative_evidence_allowed"] is False
    assert result["diagnostic_evidence"]["dispositive_for_designation_identity"] is False
    assert result["diagnostic_evidence"]["dispositive_for_legal_absence"] is False


def main() -> int:
    cases = [
        (
            "qualified official authority source",
            make_candidate(),
            AuthorityQualification.QUALIFIED_OFFICIAL_AUTHORITY_SOURCE,
            True,
        ),
        (
            "invalid url",
            make_candidate(url="not-a-url"),
            AuthorityQualification.REJECTED_INVALID_URL,
            False,
        ),
        (
            "non official host",
            make_candidate(official_host_verified=False),
            AuthorityQualification.REJECTED_NON_OFFICIAL_HOST,
            False,
        ),
        (
            "region unbound",
            make_candidate(region_binding_verified=False),
            AuthorityQualification.REJECTED_REGION_UNBOUND,
            False,
        ),
        (
            "detail document cannot be entry endpoint",
            make_candidate(entry_endpoint_verified=False),
            AuthorityQualification.REJECTED_DETAIL_DOCUMENT,
            False,
        ),
        (
            "weak endpoint role",
            make_candidate(role_verified=False),
            AuthorityQualification.REJECTED_ROLE_WEAK,
            False,
        ),
    ]

    print("=" * 88)
    print("HYBRID_SPATIAL_NOTICE AUTHORITY RESOLVER TEST")
    print("=" * 88)
    print("Network access: DISABLED")
    print("Runtime registration: DISABLED")
    print("SITE promotion: DISABLED")
    print()

    for name, candidate, expected_qualification, expected_qualified in cases:
        result = qualify_authority_source(
            candidate,
            diagnostic_evidence={
                "search_hit": True,
                "http_200": True,
                "no_hit_elsewhere": True,
            },
        )
        assert result["qualification"] == expected_qualification.value, name
        assert result["authority_source_qualified"] is expected_qualified, name
        assert_safety_contract(result)
        print(f"{name}: PASS -> {result['qualification']}")

    qualified = qualify_authority_source(make_candidate())
    assert qualified["authority_source_qualified"] is True
    assert qualified["designation_identity_verified"] is False
    assert qualified["runtime_registration_allowed"] is False
    print("qualified authority source != designation identity: PASS")

    batch = qualify_authority_sources(
        [
            make_candidate(),
            make_candidate(region_binding_verified=False),
            make_candidate(role_verified=False),
        ]
    )
    assert len(batch) == 3
    assert [row["authority_source_qualified"] for row in batch] == [True, False, False]
    print("batch order/pure qualification: PASS")

    print()
    print("CLASSIFICATION: HYBRID_SPATIAL_NOTICE_AUTHORITY_RESOLVER_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
