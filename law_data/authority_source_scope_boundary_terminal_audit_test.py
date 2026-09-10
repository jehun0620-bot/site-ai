from __future__ import annotations

from pathlib import Path

from law_data.authority_source_scope import (
    AuthoritySourceScope,
    normalize_authority_source_scope,
)
from law_data.urban_area_conversion_provenance_policy_adapter import (
    CONDITION_NAME,
    adapt_urban_area_conversion_provenance_policy,
)


CLASSIFICATION = "STEP20_AUTHORITY_SOURCE_SCOPE_BOUNDARY_TERMINALLY_RECONCILED"

BASE_DIR = Path(__file__).resolve().parent.parent


def _diagnostic_payload() -> dict[str, object]:
    return {
        "checks": {
            "combined_candidate_count": 1,
            "direct_notice_hit_count": 1,
            "notice_123_identified": True,
            "announcement_query_success": True,
            "national_archive_candidates_confirmed": True,
            "national_archive_candidate_count": 2,
            "source_url": "https://example.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            # Verification-looking diagnostic fields must be ignored by the
            # condition-specific adapter when binding AuthoritySourceScope.
            "official_host_verified": True,
            "region_binding_verified": True,
            "source_role_verified": True,
            "legal_authority_scope_verified": True,
            "target_regulation_compatible": True,
            "target_regulation_compatibility_verified": True,
        }
    }


def test_boundary_defaults_fail_closed() -> None:
    scope = AuthoritySourceScope()

    assert scope.official_host_verified is False
    assert scope.region_binding_verified is False
    assert scope.source_role_verified is False
    assert scope.legal_authority_scope_verified is False
    assert scope.target_regulation_compatible is None
    assert scope.target_regulation_compatibility_verified is False
    assert scope.authority_chain_verified is False


def test_descriptive_metadata_does_not_self_verify() -> None:
    scope = normalize_authority_source_scope(
        {
            "source_uri": "https://example.go.kr/notice/123",
            "region_binding": "서울특별시",
            "source_role": "PRIMARY",
            "legal_authority_scope": "도시계획 고시",
            "target_regulation": "개발밀도관리구역",
            "target_regulation_compatible": True,
        }
    )

    assert scope.source_host == "example.go.kr"
    assert scope.official_host_verified is False
    assert scope.region_binding_verified is False
    assert scope.source_role_verified is False
    assert scope.legal_authority_scope_verified is False
    assert scope.target_regulation_compatible is True
    assert scope.target_regulation_compatibility_verified is False
    assert scope.authority_chain_verified is False


def test_missing_and_no_hit_do_not_become_incompatible() -> None:
    missing = normalize_authority_source_scope(None)
    no_hit = normalize_authority_source_scope(
        {
            "target_regulation": CONDITION_NAME,
            "diagnostics": {"search_result": "NO_HIT"},
        }
    )

    assert missing.target_regulation_compatible is None
    assert missing.target_regulation_compatibility_verified is False
    assert no_hit.target_regulation_compatible is None
    assert no_hit.target_regulation_compatibility_verified is False
    assert no_hit.authority_chain_verified is False


def test_positive_authority_chain_requires_every_explicit_gate() -> None:
    scope = AuthoritySourceScope(
        source_host="city.go.kr",
        official_host_verified=True,
        region_binding="서울특별시",
        region_binding_verified=True,
        source_role="PRIMARY",
        source_role_verified=True,
        legal_authority_scope="도시계획 고시",
        legal_authority_scope_verified=True,
        target_regulation="대상 규제",
        target_regulation_compatible=True,
        target_regulation_compatibility_verified=True,
    )

    assert scope.authority_chain_verified is True


def test_historical_provenance_integration_remains_blocked() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    scope = result["authority_source_scope"]
    policy = result["provenance_policy"]
    gates = policy["gates"]

    assert result["condition"] == "도시지역편입해제구역"
    assert scope["source_host"] == "example.go.kr"
    assert scope["source_role"] == "PRIMARY"
    assert scope["official_host_verified"] is False
    assert scope["region_binding_verified"] is False
    assert scope["source_role_verified"] is False
    assert scope["legal_authority_scope_verified"] is False
    assert scope["target_regulation_compatible"] is None
    assert scope["target_regulation_compatibility_verified"] is False
    assert scope["authority_chain_verified"] is False

    assert gates["source_authority_identity_verified"] is False
    assert gates["source_role_explicit"] is False
    assert policy["provenance_policy_verified"] is False
    assert policy["provenance_state"] == "BLOCKED"


def test_negative_site_and_runtime_guards_remain_closed() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    policy = result["provenance_policy"]

    assert policy["negative_evidence_inference_allowed"] is False
    assert policy["legal_absence_inference_allowed"] is False
    assert policy["site_promotion_applied"] is False
    assert policy["production_wiring_applied"] is False
    assert policy["overlay_mutated"] is False
    assert policy["runtime_registry_mutated"] is False

    assert result["output_written"] is False
    assert result["production_wiring_applied"] is False
    assert result["overlay_mutated"] is False
    assert result["runtime_registry_mutated"] is False


def test_no_uqq700_cross_condition_wiring() -> None:
    result = adapt_urban_area_conversion_provenance_policy(_diagnostic_payload())
    rendered = repr(result)

    assert result["condition"] == "도시지역편입해제구역"
    assert result["authority_source_scope"]["target_regulation"] == "도시지역편입해제구역"
    assert "UQQ700" not in rendered
    assert "개발밀도관리구역" not in rendered


def _read_source(relative_path: str) -> str:
    return (BASE_DIR / relative_path).read_text(encoding="utf-8")


def test_no_runtime_or_public_api_auto_wiring() -> None:
    isolated_paths = (
        "law_data/spatial_condition_evaluator.py",
        "law_data/site_analysis_builder.py",
        "site_data/site_analysis_service.py",
        "site_data/site_analysis_orchestrator.py",
        "site_data/site_analysis_response.py",
    )

    for relative_path in isolated_paths:
        source = _read_source(relative_path)
        assert "authority_source_scope" not in source, relative_path
        assert "AuthoritySourceScope" not in source, relative_path


def test_boundary_does_not_require_authority_registry() -> None:
    boundary_source = _read_source("law_data/authority_source_scope.py")

    forbidden_registry_surfaces = (
        "SOURCE_AUTHORITY_REGISTRY",
        "AUTHORITY_SCOPE_REGISTRY",
        "REGULATION_AUTHORITY_REQUIREMENTS",
        "def register_",
        "def register_runtime",
        "def resolve_",
        "def evaluate_",
        "def promote_",
    )

    for token in forbidden_registry_surfaces:
        assert token not in boundary_source


def test_boundary_has_no_site_state_or_registration_contract() -> None:
    payload = AuthoritySourceScope().to_dict()
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


def run_terminal_audit() -> None:
    test_boundary_defaults_fail_closed()
    test_descriptive_metadata_does_not_self_verify()
    test_missing_and_no_hit_do_not_become_incompatible()
    test_positive_authority_chain_requires_every_explicit_gate()
    test_historical_provenance_integration_remains_blocked()
    test_negative_site_and_runtime_guards_remain_closed()
    test_no_uqq700_cross_condition_wiring()
    test_no_runtime_or_public_api_auto_wiring()
    test_boundary_does_not_require_authority_registry()
    test_boundary_has_no_site_state_or_registration_contract()

    print("=" * 76)
    print("STEP 20 AUTHORITY SOURCE SCOPE BOUNDARY TERMINAL AUDIT")
    print("=" * 76)
    print("Authority/source scope default fail-closed: PASS")
    print("Official-looking host / descriptive metadata authority inference: NONE")
    print("Missing/no-hit incompatibility inference: NONE")
    print("Positive authority chain: EXPLICIT VERIFIED GATES ONLY")
    print("Historical provenance state: BLOCKED")
    print("Diagnostic verification-looking field promotion: NONE")
    print("Negative/legal absence/SITE promotion: NONE")
    print("Production/runtime mutation: NONE")
    print("UQQ700 cross-condition wiring: NONE")
    print("Builder/service/orchestrator/public API/spatial runtime auto-wiring: NONE")
    print("Authority registry requirement: NONE")
    print(f"CLASSIFICATION: {CLASSIFICATION}")


if __name__ == "__main__":
    run_terminal_audit()
