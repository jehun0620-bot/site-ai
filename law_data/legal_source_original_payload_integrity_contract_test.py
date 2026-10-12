# -*- coding: utf-8 -*-
"""Synthetic, offline, no-file/no-network payload-integrity contract."""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_registry import LegalSourceRecord, build_legal_source_registry
from law_data.legal_source_version_evidence_binding import (
    LegalSourceVersionEvidenceReference,
)
from law_data.legal_source_original_payload_integrity import (
    inspect_legal_source_original_payload_integrity,
)


PAYLOAD = b"synthetic ordinance bytes\r\n\x00\xff\n"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


def source(**changes) -> LegalSourceRecord:
    fields = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", title="합성 조례", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        source_uri="https://example.go.kr/ordin", effective_date="2024-03-01",
    )
    fields.update(changes)
    return LegalSourceRecord(**fields)


def evidence(**changes) -> LegalSourceVersionEvidenceReference:
    fields = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        evidence_id="DOCUMENT-A-v12", evidence_uri="https://example.go.kr/official-looking",
        declared_sha256=DIGEST.upper(),
    )
    fields.update(changes)
    return LegalSourceVersionEvidenceReference(**fields)


def rejected(error, fn, *args, **kwargs) -> None:
    try:
        fn(*args, **kwargs)
    except error:
        return
    raise AssertionError(f"Expected {error.__name__}")


def inspect(record, reference, payload=PAYLOAD, **kwargs):
    return inspect_legal_source_original_payload_integrity(
        record, reference, payload, **kwargs
    )


def main() -> None:
    record = source()
    reference = evidence()
    before = record.to_dict()

    # Entire comparison is offline, even with an official-looking URL.
    with patch("builtins.open", side_effect=AssertionError("disk access")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("disk access")
    ), patch("socket.socket", side_effect=AssertionError("socket access")), patch(
        "socket.create_connection", side_effect=AssertionError("network access")
    ):
        matched = inspect(record, reference)
    assert matched.status == "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"
    assert matched.binding_status == "IDENTITY_ALIGNED_UNVERIFIED"
    assert matched.computed_sha256 == DIGEST
    assert matched.declared_sha256 == DIGEST
    assert matched.payload_byte_count == len(PAYLOAD)
    assert matched.digest_matches is True
    assert matched.version_key == record.version_key
    assert matched.reference_version_key == reference.version_key
    assert matched.evidence_key == reference.evidence_key
    assert record.to_dict() == before

    output = matched.to_dict()
    assert output["payload_identity_basis"] == "CALLER_SUPPLIED_BYTES_AND_DIGEST"
    for key in (
        "official_origin_decision", "original_text_identity_decision",
        "source_verification_decision", "current_validity_decision",
        "legal_authority_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert output[key] == "NOT_EVALUATED"
    for forbidden in (
        "SOURCE_VERIFIED", "authority_chain_verified", "site_truth_decision_allowed",
        "site_promotion_allowed", "production_registration_allowed",
        "runtime_registration_allowed", "legal_source_current_verified",
    ):
        assert forbidden not in output
        assert forbidden not in output.values()

    # Altering any actual byte (including whitespace) invalidates the match.
    for other in (PAYLOAD + b"\n", PAYLOAD.replace(b"\r\n", b"\n"), b"different"):
        mismatch = inspect(record, reference, other)
        assert mismatch.status == "CONTENT_DIGEST_MISMATCH"
        assert mismatch.digest_matches is False
        assert mismatch.computed_sha256 == hashlib.sha256(other).hexdigest()
        assert mismatch.declared_sha256 == DIGEST
        assert mismatch.to_dict()["official_origin_decision"] == "NOT_EVALUATED"

    # A fake digest-looking value is NOT independent evidence of actual bytes.
    invented = evidence(declared_sha256="f" * 64)
    assert inspect(record, invented).status == "CONTENT_DIGEST_MISMATCH"
    assert inspect(record, evidence()).status == "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"
    assert inspect(record, evidence(), PAYLOAD).to_dict()["original_text_identity_decision"] == "NOT_EVALUATED"

    # Unknown bytes and empty payload are never interpreted as a legal document.
    for payload in (None, b""):
        result = inspect(record, reference, payload)
        assert result.status == "PAYLOAD_MISSING"
        assert result.digest_matches is None
        assert result.computed_sha256 is None

    # Missing URI or digest, including a missing expected hash, blocks any
    # positive digest comparison. The old binding supplies the precise reason.
    for change in ({"declared_sha256": None}, {"evidence_uri": None},
                   {"declared_sha256": None, "evidence_uri": None}):
        blocked = inspect(record, evidence(**change))
        assert blocked.status == "EVIDENCE_BINDING_REJECTED"
        assert blocked.binding_status == "EVIDENCE_REFERENCE_INCOMPLETE"
        assert blocked.digest_matches is None
        assert blocked.computed_sha256 is None

    # Exact system/namespace/ID, scope, and version must bind independently
    # of matching digest and actual bytes.
    for change, expected_status in (
        ({"source_system": "OTHER"}, "SOURCE_IDENTITY_MISMATCH"),
        ({"source_namespace": "law"}, "SOURCE_IDENTITY_MISMATCH"),
        ({"source_id": "ORD-B"}, "SOURCE_IDENTITY_MISMATCH"),
        ({"version_id": "00013"}, "VERSION_MISMATCH"),
        ({"version_id": "12"}, "VERSION_MISMATCH"),
        ({"jurisdiction_code": "26"}, "DECLARED_SCOPE_MISMATCH"),
        ({"jurisdiction_level": "SIGUNGU", "jurisdiction_code": "11680"}, "DECLARED_SCOPE_MISMATCH"),
    ):
        blocked = inspect(record, evidence(**change))
        assert blocked.status == "EVIDENCE_BINDING_REJECTED"
        assert blocked.binding_status == expected_status
        assert blocked.computed_sha256 is None
        assert blocked.digest_matches is None

    later = source(version_id="00013")
    unknown = source(version_id=None)
    registry = build_legal_source_registry([record, later, unknown])
    assert registry.version_exact(*record.source_key, "00012") == record
    assert registry.version_exact(*record.source_key, "00013") == later
    assert registry.version_exact(*record.source_key, "LATEST") is None
    assert inspect(later, reference).binding_status == "VERSION_MISMATCH"
    for lhs, rhs in ((unknown, evidence(version_id=None)), (record, evidence(version_id=None))):
        assert inspect(lhs, rhs).binding_status == "VERSION_UNKNOWN"

    # Collision is evaluated only across caller-supplied known references.
    reused = evidence(version_id="00013")
    collision = inspect(later, reused, known_references=(reference,))
    assert collision.status == "EVIDENCE_BINDING_REJECTED"
    assert collision.binding_status == "EVIDENCE_REFERENCE_COLLISION"
    assert collision.digest_matches is None
    assert inspect(record, reference, known_references=(reference,)).digest_matches is True

    # Also support synthetic national sources, still without source admission.
    national = LegalSourceRecord(
        source_system="SYNTHETIC", source_namespace="law", source_id="LAW-A",
        title="합성 국가법령", source_type="NATIONAL_LAW",
        jurisdiction_level="NATIONAL", version_id="00003",
    )
    natref = evidence(
        source_namespace="law", source_id="LAW-A", version_id="00003",
        source_type="NATIONAL_LAW", jurisdiction_level="NATIONAL",
        jurisdiction_code=None, evidence_id="LAW-DOCUMENT-A",
    )
    assert inspect(national, natref).status == "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"

    # Reject implicit text encoding, mutable data and file or path handles.
    for bad in ("document text", bytearray(PAYLOAD), memoryview(PAYLOAD), Path("/tmp/example"), 123):
        rejected(TypeError, inspect, record, reference, bad)
    rejected(TypeError, inspect, {"source_id": "ORD-A"}, reference)
    rejected(TypeError, inspect, record, {"evidence_id": "DOCUMENT-A-v12"})
    rejected(TypeError, inspect, record, reference, known_references=[reference])
    rejected(TypeError, inspect, record, reference, known_references=(object(),))
    rejected(TypeError, evidence, source_verified=True)

    # Output mutation cannot change an immutable result or the source input.
    output["source_key"].append("FORGED")
    output["version_key"].append("FORGED")
    assert matched.to_dict()["source_key"] == list(record.source_key)
    assert matched.to_dict()["version_key"] == list(record.version_key)
    assert record.to_dict() == before
    try:
        matched.status = "SOURCE_VERIFIED"
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("immutable result required")

    print("LEGAL_SOURCE_ORIGINAL_PAYLOAD_INTEGRITY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
