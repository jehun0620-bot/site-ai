from __future__ import annotations

from dataclasses import FrozenInstanceError

from law_data.authority_source_scope import (
    AuthoritySourceScope,
    normalize_authority_source_scope,
)


CLASSIFICATION = "STEP20_AUTHORITY_SOURCE_SCOPE_BOUNDARY_PASS"


def _assert_no_site_or_runtime_semantics(payload: dict) -> None:
    forbidden = {
        "state",
        "site_state",
        "resolver_result",
        "production_eligible",
        "production_registration_allowed",
        "runtime_registered",
        "runtime_registration_allowed",
        "site_promotion_allowed",
        "negative_evidence_allowed",
        "legal_absence_inference_allowed",
    }
    assert forbidden.isdisjoint(payload)


def test_default_is_fail_closed() -> None:
    scope = AuthoritySourceScope()

    assert scope.source_uri is None
    assert scope.source_host is None
    assert scope.official_host_verified is False
    assert scope.region_binding is None
    assert scope.region_binding_verified is False
    assert scope.source_role is None
    assert scope.source_role_verified is False
    assert scope.legal_authority_scope is None
    assert scope.legal_authority_scope_verified is False
    assert scope.target_regulation is None
    assert scope.target_regulation_compatible is None
    assert scope.target_regulation_compatibility_verified is False
    assert scope.authority_chain_verified is False
    _assert_no_site_or_runtime_semantics(scope.to_dict())


def test_official_looking_host_does_not_verify_authority() -> None:
    scope = normalize_authority_source_scope(
        {
            "source_uri": "https://example.go.kr/notice/123",
        }
    )

    assert scope.source_host == "example.go.kr"
    assert scope.official_host_verified is False
    assert scope.authority_chain_verified is False


def test_descriptive_metadata_does_not_self_verify() -> None:
    scope = normalize_authority_source_scope(
        {
            "source_uri": "https://city.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            "target_regulation": "개발밀도관리구역",
            "target_regulation_compatible": True,
        }
    )

    assert scope.source_host == "city.go.kr"
    assert scope.official_host_verified is False
    assert scope.region_binding == "서울특별시"
    assert scope.region_binding_verified is False
    assert scope.source_role == "PRIMARY"
    assert scope.source_role_verified is False
    assert scope.legal_authority_scope == "도시계획 고시"
    assert scope.legal_authority_scope_verified is False
    assert scope.target_regulation == "개발밀도관리구역"
    assert scope.target_regulation_compatible is True
    assert scope.target_regulation_compatibility_verified is False
    assert scope.authority_chain_verified is False


def test_missing_or_no_hit_does_not_become_incompatible() -> None:
    missing = normalize_authority_source_scope(None)
    no_hit = normalize_authority_source_scope(
        {
            "target_regulation": "개발밀도관리구역",
            "diagnostics": {"search_result": "NO_HIT"},
        }
    )

    assert missing.target_regulation_compatible is None
    assert missing.target_regulation_compatibility_verified is False
    assert no_hit.target_regulation_compatible is None
    assert no_hit.target_regulation_compatibility_verified is False
    assert no_hit.authority_chain_verified is False


def test_verified_compatibility_requires_explicit_boolean() -> None:
    try:
        AuthoritySourceScope(
            target_regulation="개발밀도관리구역",
            target_regulation_compatibility_verified=True,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "verified compatibility must not exist without explicit compatible/incompatible evidence"
        )


def test_positive_authority_chain_requires_every_verified_gate() -> None:
    scope = AuthoritySourceScope(
        source_uri="https://city.go.kr/notice/123",
        source_host="city.go.kr",
        official_host_verified=True,
        region_binding="서울특별시",
        region_binding_verified=True,
        source_role="PRIMARY",
        source_role_verified=True,
        legal_authority_scope="도시계획 고시",
        legal_authority_scope_verified=True,
        target_regulation="개발밀도관리구역",
        target_regulation_compatible=True,
        target_regulation_compatibility_verified=True,
    )

    assert scope.authority_chain_verified is True
    _assert_no_site_or_runtime_semantics(scope.to_dict())


def test_verified_incompatibility_is_not_positive_authority_chain() -> None:
    scope = AuthoritySourceScope(
        source_host="city.go.kr",
        official_host_verified=True,
        region_binding="서울특별시",
        region_binding_verified=True,
        source_role="PRIMARY",
        source_role_verified=True,
        legal_authority_scope="도시계획 고시",
        legal_authority_scope_verified=True,
        target_regulation="개발밀도관리구역",
        target_regulation_compatible=False,
        target_regulation_compatibility_verified=True,
    )

    assert scope.target_regulation_compatible is False
    assert scope.target_regulation_compatibility_verified is True
    assert scope.authority_chain_verified is False


def test_contract_and_diagnostics_are_immutable() -> None:
    scope = AuthoritySourceScope(diagnostics={"source": "fixture"})

    try:
        scope.source_host = "changed.example"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("AuthoritySourceScope must remain frozen")

    try:
        scope.diagnostics["source"] = "mutated"
    except TypeError:
        pass
    else:
        raise AssertionError("diagnostics must remain read-only")


def run_regression() -> None:
    test_default_is_fail_closed()
    test_official_looking_host_does_not_verify_authority()
    test_descriptive_metadata_does_not_self_verify()
    test_missing_or_no_hit_does_not_become_incompatible()
    test_verified_compatibility_requires_explicit_boolean()
    test_positive_authority_chain_requires_every_verified_gate()
    test_verified_incompatibility_is_not_positive_authority_chain()
    test_contract_and_diagnostics_are_immutable()

    print("=" * 68)
    print("STEP 20 AUTHORITY SOURCE SCOPE BOUNDARY REGRESSION")
    print("=" * 68)
    print("Official-looking host authority inference: NONE")
    print("Region/source-role/authority-scope self-verification: NONE")
    print("Target regulation metadata compatibility inference: NONE")
    print("Missing/no-hit incompatibility inference: NONE")
    print("Authority chain positive gate: EXPLICIT VERIFIED EVIDENCE ONLY")
    print("SITE/resolver/production/runtime semantics: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_regression()
