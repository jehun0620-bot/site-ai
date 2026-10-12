# -*- coding: utf-8 -*-
"""Synthetic/offline contract: acquisition metadata can NEVER certify origin."""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_registry import LegalSourceRecord
from law_data.legal_source_version_evidence_binding import LegalSourceVersionEvidenceReference
from law_data.legal_source_acquisition_receipt_inspection import (
    LegalSourceAcquisitionReceipt,
    inspect_legal_source_acquisition_receipt,
)

PAYLOAD = b"%PDF-1.4\r\n% synthetic document\n\x00\xff"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()
URL = "https://synthetic.example/test-document.pdf"


def source(**changes) -> LegalSourceRecord:
    data = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", title="합성 조례", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        source_uri="https://synthetic.example/ordinance-index",
    )
    data.update(changes)
    return LegalSourceRecord(**data)


def evidence(**changes) -> LegalSourceVersionEvidenceReference:
    data = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", source_type="LOCAL_ORDINANCE",
        jurisdiction_level="SIDO", jurisdiction_code="11",
        evidence_id="ARTIFACT-A-12", evidence_uri=URL, declared_sha256=DIGEST,
    )
    data.update(changes)
    return LegalSourceVersionEvidenceReference(**data)


def receipt(**changes) -> LegalSourceAcquisitionReceipt:
    data = dict(
        source_system="SYNTHETIC", source_namespace="ordin", source_id="ORD-A",
        version_id="00012", evidence_id="ARTIFACT-A-12",
        requested_url=URL, final_url=URL, http_status=200,
        content_type="application/pdf; charset=binary", response_byte_count=len(PAYLOAD),
        response_sha256=DIGEST.upper(), acquisition_id="synthetic-fetch-1",
        observed_at_utc="2026-10-12T01:02:03Z",
    )
    data.update(changes)
    return LegalSourceAcquisitionReceipt(**data)


def inspect(rec=None, ref=None, payload=PAYLOAD, recpt=None, **kwargs):
    return inspect_legal_source_acquisition_receipt(
        rec if rec is not None else source(),
        ref if ref is not None else evidence(), payload,
        recpt if recpt is not None else receipt(), **kwargs,
    )


def rejects(error_type, callback, *args, **kwargs) -> None:
    try:
        callback(*args, **kwargs)
    except error_type:
        return
    raise AssertionError(f"Expected {error_type.__name__}")


def main() -> None:
    record, reference, claimed = source(), evidence(), receipt()
    before_record = record.to_dict()
    # Inspection invokes existing pure modules; no HTTP, filesystem or snapshots.
    with patch("builtins.open", side_effect=AssertionError("unexpected disk IO")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("unexpected disk IO")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("unexpected disk IO")), patch(
        "socket.socket", side_effect=AssertionError("unexpected network IO")
    ), patch("socket.create_connection", side_effect=AssertionError("unexpected network IO")):
        matched = inspect(record, reference, PAYLOAD, claimed)

    assert matched.status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"
    assert matched.integrity_status == "CONTENT_DIGEST_MATCH_UNVERIFIED_ORIGIN"
    assert matched.binding_status == "IDENTITY_ALIGNED_UNVERIFIED"
    assert matched.version_key == record.version_key
    assert matched.receipt_version_key == claimed.version_key
    assert matched.evidence_key == reference.evidence_key
    assert matched.receipt_identity_aligned is True
    assert matched.receipt_byte_count_matches is True
    assert matched.receipt_digest_matches is True
    assert matched.missing_receipt_fields == ()
    assert matched.url_relation == "UNCHANGED_DECLARED"
    assert claimed.response_sha256 == DIGEST
    assert record.to_dict() == before_record
    output = matched.to_dict()
    assert output["receipt_identity_basis"] == "CALLER_SUPPLIED_UNATTESTED"
    for key in (
        "acquisition_authenticity_decision", "official_origin_decision",
        "original_text_identity_decision", "source_verification_decision",
        "current_validity_decision", "legal_authority_decision",
        "legal_applicability_decision", "production_admission_decision",
    ):
        assert output[key] == "NOT_EVALUATED"
    for forbidden in (
        "SOURCE_VERIFIED", "official_source_verified", "official_host_verified",
        "source_identity_verified", "authority_chain_verified", "site_promotion_allowed",
        "runtime_registration_allowed", "production_registration_allowed",
    ):
        assert forbidden not in output and forbidden not in output.values()

    # Neither witness ID, UTC timestamp, nor plausible HTTPS site is proof of
    # a real request. Fully forged self-consistent claims MUST stay UNVERIFIED.
    fake_payload = b"self-authored bytes but no official fetch"
    fake_hash = hashlib.sha256(fake_payload).hexdigest()
    forged = inspect(
        ref=evidence(declared_sha256=fake_hash), payload=fake_payload,
        recpt=receipt(response_sha256=fake_hash, response_byte_count=len(fake_payload),
                      observed_at_utc="2000-01-01T00:00:00Z", acquisition_id="FAKE"),
    )
    assert forged.status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"
    assert forged.to_dict()["official_origin_decision"] == "NOT_EVALUATED"
    assert forged.to_dict()["acquisition_authenticity_decision"] == "NOT_EVALUATED"

    # Receipt and evidence must use exactly the same source, namespace, version
    # and evidence-artifact ID. Do not silently select latest or strip zeros.
    for changes in (
        {"source_system": "OTHER"}, {"source_namespace": "law"},
        {"source_id": "ORD-B"}, {"version_id": "00013"},
        {"version_id": "12"}, {"version_id": None},
        {"evidence_id": "OTHER-ARTIFACT"},
    ):
        result = inspect(recpt=receipt(**changes))
        assert result.status == "RECEIPT_IDENTITY_MISMATCH", changes
        assert result.receipt_identity_aligned is False
    assert inspect(rec=source(version_id="00013")).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(ref=evidence(version_id=None)).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(ref=evidence(source_namespace="law")).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(ref=evidence(declared_sha256=None)).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(payload=b"altered", recpt=receipt(response_sha256=hashlib.sha256(b"altered").hexdigest(), response_byte_count=7)).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(payload=None).status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert inspect(payload=b"").status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    other = evidence(version_id="00013")
    blocked = inspect(known_references=(other,))
    assert blocked.status == "UPSTREAM_INTEGRITY_UNRESOLVED"
    assert blocked.binding_status == "EVIDENCE_REFERENCE_COLLISION"

    # Required receipt fields must never be inferred from ref, payload, URL,
    # claimed response metadata or current wall time.
    for field in (
        "requested_url", "final_url", "http_status", "content_type",
        "response_byte_count", "response_sha256", "acquisition_id", "observed_at_utc",
    ):
        result = inspect(recpt=receipt(**{field: None}))
        assert result.status == "RECEIPT_INCOMPLETE", field
        assert field in result.missing_receipt_fields
    partial = inspect(recpt=receipt(final_url=None, response_sha256=None))
    assert partial.missing_receipt_fields == ("final_url", "response_sha256")
    assert partial.url_relation == "NOT_COMPARABLE"

    # Success requires an exactly claimed HTTP 200, *not* a real 200 witness.
    for code in (201, 206, 301, 403, 404, 500):
        assert inspect(recpt=receipt(http_status=code)).status == "RECEIPT_HTTP_STATUS_NOT_200"

    # Exact, case-sensitive URL comparison; never infer legal authority from
    # hostname, nor silently follow or accept an unreviewed redirect.
    assert inspect(recpt=receipt(requested_url="https://synthetic.example/other.pdf")).status == "RECEIPT_REQUEST_URL_MISMATCH"
    changed = inspect(recpt=receipt(final_url="https://other.example/test-document.pdf"))
    assert changed.status == "RECEIPT_REDIRECT_REVIEW_REQUIRED"
    assert changed.url_relation == "CHANGED_UNVERIFIED"
    assert inspect(recpt=receipt(final_url=URL + "?download=1")).status == "RECEIPT_REDIRECT_REVIEW_REQUIRED"
    http_url = URL.replace("https://", "http://")
    assert inspect(ref=evidence(evidence_uri=http_url), recpt=receipt(requested_url=http_url, final_url=http_url)).status == "RECEIPT_NON_HTTPS_URL_REVIEW_REQUIRED"

    assert inspect(recpt=receipt(response_byte_count=len(PAYLOAD) + 1)).status == "RECEIPT_BYTE_COUNT_MISMATCH"
    assert inspect(recpt=receipt(response_sha256="f" * 64)).status == "RECEIPT_DIGEST_MISMATCH"
    assert inspect(recpt=receipt(response_sha256=DIGEST, response_byte_count=len(PAYLOAD))).status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"

    # A successful HTTP response or even a matching digest may be an error page.
    # HTML needs explicit document-level review (not a legal-positive).
    assert inspect(recpt=receipt(content_type="text/html; charset=utf-8")).status == "RECEIPT_DOCUMENT_FORMAT_REVIEW_REQUIRED"
    error_page = b"<!DOCTYPE html><html><body>Access Denied</body></html>"
    error_hash = hashlib.sha256(error_page).hexdigest()
    assert inspect(
        ref=evidence(declared_sha256=error_hash), payload=error_page,
        recpt=receipt(response_byte_count=len(error_page), response_sha256=error_hash,
                      content_type="application/pdf"),
    ).status == "RECEIPT_DOCUMENT_FORMAT_REVIEW_REQUIRED"

    # Shape checks reject invalid receipts, not guesses/corrections.
    for changes in (
        {"source_id": ""}, {"source_namespace": 3}, {"evidence_id": " "},
        {"version_id": " "}, {"http_status": True}, {"http_status": "200"},
        {"http_status": 999}, {"response_byte_count": False},
        {"response_byte_count": -1}, {"response_byte_count": "10"},
        {"response_sha256": "x" * 64}, {"response_sha256": "f" * 63},
        {"observed_at_utc": "2026-02-30T00:00:00Z"},
        {"observed_at_utc": "2026-10-12T01:02:03"},
        {"requested_url": "ftp://synthetic.example/a"},
        {"final_url": "https://user:pass@synthetic.example/a"},
        {"requested_url": "https://synthetic.example/line\n"},
    ):
        rejects(ValueError, receipt, **changes)
    rejects(TypeError, inspect, recpt={"http_status": 200})
    rejects(TypeError, inspect, payload="not actual bytes")
    rejects(TypeError, inspect, known_references=[evidence()])
    rejects(TypeError, receipt, official_source_verified=True)

    output["version_key"].append("FORGED")
    output["missing_receipt_fields"].append("FORGED")
    assert matched.to_dict()["version_key"] == list(record.version_key)
    assert matched.to_dict()["missing_receipt_fields"] == []
    assert record.to_dict() == before_record
    for obj, field in ((claimed, "http_status"), (matched, "status")):
        try:
            setattr(obj, field, "SOURCE_VERIFIED")
        except FrozenInstanceError:
            pass
        else:
            raise AssertionError("receipt / inspection must be immutable")

    print("LEGAL_SOURCE_ACQUISITION_RECEIPT_INSPECTION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
