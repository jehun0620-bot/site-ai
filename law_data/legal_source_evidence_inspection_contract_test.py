# -*- coding: utf-8 -*-
"""No-network/no-write contract for unverified source metadata inspection."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import patch

from law_data.authority_source_scope import AuthoritySourceScope
from law_data.legal_jurisdiction_context import parse_legal_jurisdiction_context
from law_data.legal_source_evidence_inspection import (
    INDEPENDENT_CHECKS_REQUIRED,
    inspect_legal_source_evidence,
)
from law_data.legal_source_registry import (
    LegalSourceRecord,
    build_legal_source_registry,
)


def _rejects(error_type: type[Exception], call, *args, **kwargs) -> None:
    try:
        call(*args, **kwargs)
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def _ordinance(**overrides) -> LegalSourceRecord:
    # All content below is synthetic; no real law source or validity is claimed.
    kwargs = dict(
        source_system="SYNTHETIC_PROVIDER",
        source_namespace="ordin",
        source_id="EXAMPLE-001",
        title="합성 조례",
        source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO",
        jurisdiction_code="11",
        version_id="00012",
        source_uri="https://example.go.kr/ordin/1",
        promulgation_date="2024-02-29",
        effective_date="2024-03-01",
    )
    kwargs.update(overrides)
    return LegalSourceRecord(**kwargs)


def main() -> None:
    original = _ordinance()
    seoul_context = parse_legal_jurisdiction_context("1168010300100120002")
    other_context = parse_legal_jurisdiction_context("2635010500105240002")

    # No fetch, file access, snapshot write, or network connection in inspection.
    with patch("builtins.open", side_effect=AssertionError("unexpected IO")), patch(
        "socket.socket", side_effect=AssertionError("unexpected network")
    ):
        inspected = inspect_legal_source_evidence(original, jurisdiction_context=seoul_context)
    output = inspected.to_dict()
    assert inspected.source_key == original.source_key
    assert inspected.version_key == original.version_key
    assert inspected.version_identity_status == "EXPLICIT_ID_UNVERIFIED"
    assert inspected.jurisdiction_code_relation == "LEXICALLY_EQUAL_UNVERIFIED"
    assert inspected.missing_metadata_fields == ()
    assert inspected.independent_checks_required == INDEPENDENT_CHECKS_REQUIRED
    assert output["source_identity_basis"] == "CALLER_SUPPLIED_UNVERIFIED"
    for decision in (
        "source_verification_decision", "current_validity_decision",
        "legal_authority_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert output[decision] == "NOT_EVALUATED"
    assert "authority_chain_verified" not in output
    assert "region_binding_verified" not in output
    assert "SOURCE_VERIFIED" not in output.values()

    # Matching and nonmatching PNU prefixes are descriptive only.
    assert inspect_legal_source_evidence(
        original, jurisdiction_context=other_context
    ).jurisdiction_code_relation == "LEXICALLY_DIFFERENT_UNVERIFIED"
    assert inspect_legal_source_evidence(original).jurisdiction_code_relation == "NOT_CHECKED"
    basic = _ordinance(
        source_id="EXAMPLE-SIGUNGU", jurisdiction_level="SIGUNGU", jurisdiction_code="11680"
    )
    assert inspect_legal_source_evidence(
        basic, jurisdiction_context=seoul_context
    ).jurisdiction_code_relation == "LEXICALLY_EQUAL_UNVERIFIED"
    assert inspect_legal_source_evidence(
        basic, jurisdiction_context=other_context
    ).jurisdiction_code_relation == "LEXICALLY_DIFFERENT_UNVERIFIED"

    # Null version is unknown, never a synonym for latest/current.
    unknown = _ordinance(
        version_id=None, source_uri=None, promulgation_date=None, effective_date=None
    )
    amended = _ordinance(version_id="00013", effective_date="2025-03-01")
    registry = build_legal_source_registry([original, original, amended, unknown])
    assert len(registry.records) == 3
    assert registry.version_exact(*original.source_key, "00012") == original
    assert registry.version_exact(*original.source_key, "00013") == amended
    assert registry.version_exact(*original.source_key, None) == unknown
    assert registry.version_exact(*original.source_key, "LATEST") is None
    inspected_unknown = inspect_legal_source_evidence(
        registry.version_exact(*original.source_key, None)
    )
    assert inspected_unknown.version_key[-1] is None
    assert inspected_unknown.version_identity_status == "UNKNOWN"
    assert inspected_unknown.missing_metadata_fields == (
        "version_id", "source_uri", "promulgation_date", "effective_date"
    )
    assert inspected_unknown.to_dict()["current_validity_decision"] == "NOT_EVALUATED"
    assert inspect_legal_source_evidence(
        registry.version_exact(*original.source_key, "00013")
    ).version_identity_status == "EXPLICIT_ID_UNVERIFIED"

    national = LegalSourceRecord(
        source_system="SYNTHETIC_PROVIDER", source_namespace="law",
        source_id="EXAMPLE-NAT", title="합성 전국 법령", source_type="NATIONAL_LAW",
        jurisdiction_level="NATIONAL",
    )
    national_result = inspect_legal_source_evidence(national, jurisdiction_context=other_context)
    assert national_result.jurisdiction_code_relation == "NO_LOCAL_CODE"
    assert national_result.jurisdiction_code is None
    assert national_result.to_dict()["legal_applicability_decision"] == "NOT_EVALUATED"

    review = _ordinance(source_state="REVIEW_REQUIRED")
    assert inspect_legal_source_evidence(review).source_state == "REVIEW_REQUIRED"
    assert inspect_legal_source_evidence(original).source_state == "NOT_VERIFIED"
    _rejects(ValueError, _ordinance, source_state="SOURCE_VERIFIED")

    # Similar strings on a separate Scope never become verified in inspection.
    scope = AuthoritySourceScope(
        source_uri=original.source_uri,
        region_binding=original.jurisdiction_code,
        source_role="PRIMARY",
        legal_authority_scope="합성 관할 설명",
        target_regulation="합성 조례",
        target_regulation_compatible=True,
    )
    assert scope.authority_chain_verified is False
    assert scope.region_binding_verified is False
    assert inspect_legal_source_evidence(original).to_dict()["legal_authority_decision"] == "NOT_EVALUATED"

    # Immutability, input validation, output separation.
    before = original.to_dict()
    mutable_output = inspected.to_dict()
    mutable_output["missing_metadata_fields"].append("FORGED")
    mutable_output["source_key"].append("FORGED")
    assert inspected.to_dict()["missing_metadata_fields"] == []
    assert inspected.source_key == original.source_key
    assert original.to_dict() == before
    assert inspect_legal_source_evidence(original) == inspect_legal_source_evidence(original)
    _rejects(TypeError, inspect_legal_source_evidence, {"source_id": "EXAMPLE-001"})
    _rejects(TypeError, inspect_legal_source_evidence, original, jurisdiction_context="11")
    try:
        inspected.source_state = "SOURCE_VERIFIED"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("inspection must be immutable")

    print("LEGAL_SOURCE_EVIDENCE_INSPECTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
