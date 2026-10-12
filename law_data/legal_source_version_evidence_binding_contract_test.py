# -*- coding: utf-8 -*-
"""Synthetic-only, offline, no-snapshot contract for version/evidence binding."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from unittest.mock import patch

from law_data.legal_source_registry import LegalSourceRecord, build_legal_source_registry
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
    bind_legal_source_version_evidence,
)


def rejects(error_type: type[Exception], call, *args, **kwargs) -> None:
    try:
        call(*args, **kwargs)
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def source(**kwargs) -> LegalSourceRecord:
    values = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", title="합성 조례", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        source_uri="https://example.go.kr/ordin", effective_date="2024-03-01",
    )
    values.update(kwargs)
    return LegalSourceRecord(**values)


def evidence(**kwargs) -> LegalSourceVersionEvidenceReference:
    values = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        evidence_id="ARTIFACT-A-v12", evidence_uri="https://example.go.kr/document",
        declared_sha256="A" * 64,
    )
    values.update(kwargs)
    return LegalSourceVersionEvidenceReference(**values)


def main() -> None:
    original = source()
    reference = evidence()
    original_payload = original.to_dict()

    # A plausible official-looking URI and a syntactically valid digest are
    # caller-supplied DESCRIPTIONS. No IO or cryptographic comparison occurs.
    with patch("builtins.open", side_effect=AssertionError("unexpected file IO")), patch(
        "socket.socket", side_effect=AssertionError("unexpected network IO")
    ):
        bound = bind_legal_source_version_evidence(original, reference)

    assert bound.status == "IDENTITY_ALIGNED_UNVERIFIED"
    assert bound.source_key == original.source_key
    assert bound.version_key == original.version_key
    assert bound.reference_version_key == reference.version_key
    assert bound.exact_version_aligned is True
    assert bound.declared_scope_aligned is True
    assert bound.evidence_reference_collision is False
    assert bound.missing_reference_fields == ()
    assert reference.declared_sha256 == "a" * 64
    result = bound.to_dict()
    assert result["source_identity_basis"] == "CALLER_SUPPLIED_UNVERIFIED"
    for decision in (
        "source_verification_decision", "original_text_identity_decision",
        "current_validity_decision", "legal_authority_decision",
        "legal_applicability_decision", "production_admission_decision",
    ):
        assert result[decision] == "NOT_EVALUATED"
    for forbidden in (
        "SOURCE_VERIFIED", "authority_chain_verified", "region_binding_verified",
        "site_promotion_allowed", "production_registration_allowed", "runtime_registration_allowed",
    ):
        assert forbidden not in result

    # Source-system, namespace, and ID are separate dimensions. Names or URLs
    # cannot bridge a mismatch, even with identical declared digests.
    for changes in (
        {"source_system": "OTHER"},
        {"source_namespace": "law"},
        {"source_id": "ORD-B"},
    ):
        assert bind_legal_source_version_evidence(original, evidence(**changes)).status == "SOURCE_IDENTITY_MISMATCH"

    # No automatic latest selection, zero-stripping, or cross-version re-use.
    later = source(version_id="00013")
    unknown = source(version_id=None)
    registry = build_legal_source_registry([original, later, unknown])
    assert registry.version_exact(*original.source_key, "00012") == original
    assert registry.version_exact(*original.source_key, "00013") == later
    assert registry.version_exact(*original.source_key, "LATEST") is None
    assert bind_legal_source_version_evidence(later, reference).status == "VERSION_MISMATCH"
    assert bind_legal_source_version_evidence(original, evidence(version_id="12")).status == "VERSION_MISMATCH"
    assert bind_legal_source_version_evidence(unknown, evidence(version_id=None)).status == "VERSION_UNKNOWN"
    assert bind_legal_source_version_evidence(original, evidence(version_id=None)).status == "VERSION_UNKNOWN"
    assert bind_legal_source_version_evidence(unknown, reference).status == "VERSION_UNKNOWN"

    # Same declared evidence artifact ID bound to distinct versions in a supplied
    # snapshot is a collision. This is not a guarantee of global uniqueness.
    reused = evidence(version_id="00013")
    assert bind_legal_source_version_evidence(later, reused, known_references=(reference,)).status == "EVIDENCE_REFERENCE_COLLISION"
    assert bind_legal_source_version_evidence(original, reference, known_references=(reused,)).evidence_reference_collision is True
    assert bind_legal_source_version_evidence(original, reference, known_references=(reference,)).status == "IDENTITY_ALIGNED_UNVERIFIED"
    distinct = evidence(version_id="00013", evidence_id="ARTIFACT-A-v13")
    assert bind_legal_source_version_evidence(later, distinct, known_references=(reference,)).status == "IDENTITY_ALIGNED_UNVERIFIED"
    assert bound.to_dict()["original_text_identity_decision"] == "NOT_EVALUATED"
    # Even a different syntactically valid claimed digest changes no legal gate.
    different_digest = evidence(
        version_id="00013", evidence_id="ARTIFACT-A-v13", declared_sha256="b" * 64
    )
    assert bind_legal_source_version_evidence(
        later, different_digest
    ).to_dict()["original_text_identity_decision"] == "NOT_EVALUATED"

    # Exact descriptive scope mismatch is not judicial/legal authorization.
    assert bind_legal_source_version_evidence(original, evidence(jurisdiction_code="26")).status == "DECLARED_SCOPE_MISMATCH"
    assert bind_legal_source_version_evidence(original, evidence(
        jurisdiction_level="SIGUNGU", jurisdiction_code="11680"
    )).status == "DECLARED_SCOPE_MISMATCH"
    national = LegalSourceRecord(
        source_system="SYNTHETIC", source_namespace="law", source_id="STAT-A",
        title="합성 국가법령", source_type="NATIONAL_LAW",
        jurisdiction_level="NATIONAL", version_id="00003",
    )
    natref = evidence(
        source_namespace="law", source_id="STAT-A", version_id="00003",
        source_type="NATIONAL_LAW", jurisdiction_level="NATIONAL",
        jurisdiction_code=None, evidence_id="LAW-EVIDENCE-A",
    )
    assert bind_legal_source_version_evidence(national, natref).status == "IDENTITY_ALIGNED_UNVERIFIED"

    # An incomplete citation is rejected as an alignment result, and a claimed
    # digest is only checked for shape (not equality with document bytes).
    assert bind_legal_source_version_evidence(original, evidence(evidence_uri=None)).status == "EVIDENCE_REFERENCE_INCOMPLETE"
    missing_hash = bind_legal_source_version_evidence(original, evidence(declared_sha256=None))
    assert missing_hash.status == "EVIDENCE_REFERENCE_INCOMPLETE"
    assert missing_hash.missing_reference_fields == ("declared_sha256",)
    assert bind_legal_source_version_evidence(original, evidence(
        evidence_uri=None, declared_sha256=None
    )).missing_reference_fields == ("evidence_uri", "declared_sha256")
    for kwargs in (
        {"source_system": ""}, {"source_id": 123}, {"evidence_id": " "},
        {"version_id": " "}, {"jurisdiction_code": "１１"},
        {"evidence_uri": "file:///private/evidence"},
        {"evidence_uri": "example.go.kr"},
        {"declared_sha256": "not-a-digest"},
        {"declared_sha256": "f" * 63},
    ):
        rejects(ValueError, evidence, **kwargs)
    rejects(TypeError, bind_legal_source_version_evidence, {"source_id": "ORD-A"}, reference)
    rejects(TypeError, bind_legal_source_version_evidence, original, {"evidence_id": "ARTIFACT-A-v12"})
    rejects(TypeError, bind_legal_source_version_evidence, original, reference, known_references=[reference])
    rejects(TypeError, bind_legal_source_version_evidence, original, reference, known_references=(object(),))
    rejects(TypeError, evidence, official_source_verified=True)

    # Caller state, registry state and prior assessments are not mutated.
    result["source_key"].append("FORGED")
    result["missing_reference_fields"].append("FORGED")
    assert bound.to_dict()["source_key"] == list(original.source_key)
    assert bound.to_dict()["missing_reference_fields"] == []
    assert original.to_dict() == original_payload
    assert reference.declared_sha256 == "a" * 64
    try:
        bound.status = "SOURCE_VERIFIED"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("binding must be immutable")
    try:
        reference.version_id = "00013"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("reference must be immutable")

    print("LEGAL_SOURCE_VERSION_EVIDENCE_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
