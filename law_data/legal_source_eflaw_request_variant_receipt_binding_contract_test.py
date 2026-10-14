# -*- coding: ascii -*-
"""Offline-only synthetic tests for claimed eflaw receipt descriptor linkage."""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_acquisition_receipt_inspection import (
    LegalSourceAcquisitionReceipt,
    inspect_legal_source_acquisition_receipt,
)
from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    build_legal_source_eflaw_request_variant_registry,
)
from law_data.legal_source_eflaw_request_variant_http_binding import (
    BOUND, inspect_legal_source_eflaw_request_variant_http_binding,
)
from law_data.legal_source_eflaw_request_variant_receipt_binding import (
    ALIGNED, NOT_REGISTERED, DESCRIPTOR_MISMATCH, LOCATOR_MISSING,
    LOCATOR_MISMATCH, HTTP_UNRESOLVED, RECEIPT_UNRESOLVED,
    INSPECTION_FAILED, LegalSourceEflawRequestVariantReceiptBinding,
    inspect_legal_source_eflaw_request_variant_receipt_binding,
)
from law_data.legal_source_response_identity_inspection_contract_test import make_input
from law_data.legal_source_public_request_descriptor import build_legal_source_public_request_descriptor

SECRET = "SYNTHETIC_OC_PRIVATE_NEVER_PRINT"


def rejects(fn, error: type[Exception], status: str) -> None:
    try:
        fn()
    except error as exc:
        assert str(exc) == status, "UNEXPECTED_EXCEPTION_CODE"
        assert SECRET not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def safe(diag: LegalSourceEflawRequestVariantReceiptBinding) -> None:
    doc = diag.public_record()
    raw = json.dumps(doc, ensure_ascii=True)
    for secret in (SECRET, "OC=", "SYNTHETIC-NATIONAL-SOURCE",
                   "SYNTHETIC-EVIDENCE", "20120106", "121615",
                   "lawService.do", "SOURCE_VERIFIED"):
        assert secret not in raw and secret not in repr(diag), "SENSITIVE_DIAGNOSTIC"
    for key in ("acquisition_authenticity_decision", "official_origin_decision",
                "original_text_identity_decision", "source_verification_decision",
                "current_validity_decision", "legal_authority_decision",
                "legal_applicability_decision", "production_admission_decision"):
        assert doc[key] == "NOT_EVALUATED"


def make_receipt(record, ref, http, uri: str | None) -> LegalSourceAcquisitionReceipt:
    return LegalSourceAcquisitionReceipt(
        source_system=record.source_system,
        source_namespace=record.source_namespace,
        source_id=record.source_id,
        version_id=record.version_id,
        evidence_id=ref.evidence_id,
        requested_url=uri,
        final_url=uri,
        http_status=200,
        content_type="application/json",
        response_byte_count=len(http.payload),
        response_sha256=hashlib.sha256(http.payload).hexdigest(),
        acquisition_id="SYNTHETIC-CALLER-CLAIM-NOT-AN-AUTHENTICATED-RECEIPT",
        observed_at_utc="2026-01-01T00:00:00Z",
    )


def main() -> None:
    http, record, original_reference = make_input((
        "eflaw", "121615", "20120106", "SYNTHETIC-NATIONAL-SOURCE",
        "Synthetic National Law", "2012-01-06",
    ))
    correct_uri = http.descriptor.public_descriptor_url()
    reference = replace(original_reference, evidence_id="SYNTHETIC-EVIDENCE-A",
                        evidence_uri=correct_uri)
    variant = LegalSourceEflawRequestVariant(http.descriptor, record, reference)
    registry = build_legal_source_eflaw_request_variant_registry([variant])
    receipt = make_receipt(record, reference, http, correct_uri)
    audit = inspect_legal_source_eflaw_request_variant_receipt_binding
    count = 0

    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_READ_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_WRITE_FORBIDDEN")):
        # A canonical public locator is still only a claim, never an observed URL.
        aligned = audit(registry, variant, http, receipt)
        assert aligned.status == ALIGNED
        assert aligned.public_record()["locator_basis"] == "EXACT_CREDENTIAL_FREE_CALLER_CLAIM_NOT_WITNESSED_HTTP_URL"
        safe(aligned)
        count += 1

        other_descriptor = build_legal_source_public_request_descriptor({
            "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120201",
        })
        # Reproduce the verified legacy gap: both legacy checks pass, but the
        # receipt claims a DIFFERENT public efYd from the HTTP variant request.
        wrong_uri = other_descriptor.public_descriptor_url()
        swapped_reference = replace(reference, evidence_uri=wrong_uri)
        swapped_variant = LegalSourceEflawRequestVariant(http.descriptor, record, swapped_reference)
        swapped_registry = build_legal_source_eflaw_request_variant_registry([swapped_variant])
        swapped_receipt = make_receipt(record, swapped_reference, http, wrong_uri)
        assert inspect_legal_source_eflaw_request_variant_http_binding(
            swapped_registry, swapped_variant, http
        ).status == BOUND
        assert inspect_legal_source_acquisition_receipt(
            record, swapped_reference, http.payload, swapped_receipt
        ).status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"
        assert audit(swapped_registry, swapped_variant, http, swapped_receipt).status == LOCATOR_MISMATCH
        count += 1

        malformed_uris = (
            correct_uri + "&OC=" + SECRET,
            correct_uri + "&efYd=20120201",
            correct_uri.replace("efYd=", "%65fYd="),
            correct_uri.replace("MST=121615", "MST=999999"),
            correct_uri.replace("efYd=20120106", "efYd=20120201"),
            correct_uri.replace("target=eflaw", "target=ordin"),
            correct_uri.replace("type=JSON", "type=XML"),
            correct_uri + "&extra=x",
            correct_uri + "#fragment",
            correct_uri.replace("www.law.go.kr", "different.example"),
            correct_uri.replace("?target=eflaw&type=JSON", "?type=JSON&target=eflaw"),
        )
        for uri in malformed_uris:
            # Matching receipt/reference URL and bytes alone is insufficient.
            other_ref = replace(reference, evidence_uri=uri)
            other_variant = LegalSourceEflawRequestVariant(http.descriptor, record, other_ref)
            other_registry = build_legal_source_eflaw_request_variant_registry([other_variant])
            other_receipt = make_receipt(record, other_ref, http, uri)
            old = inspect_legal_source_acquisition_receipt(
                record, other_ref, http.payload, other_receipt,
            )
            assert old.status == "RECEIPT_CONSISTENT_UNVERIFIED_ORIGIN"
            result = audit(other_registry, other_variant, http, other_receipt)
            assert result.status == LOCATOR_MISMATCH
            safe(result)
            count += 1

        assert audit(registry, variant, http, replace(receipt, requested_url=None)).status == LOCATOR_MISSING
        count += 1
        assert audit(registry, variant, http, replace(receipt, final_url=None)).status == LOCATOR_MISSING
        count += 1
        assert audit(registry, variant, http, replace(receipt, requested_url=wrong_uri)).status == LOCATOR_MISMATCH
        count += 1

        changed_http = replace(http, descriptor=other_descriptor)
        assert audit(registry, variant, changed_http, receipt).status == DESCRIPTOR_MISMATCH
        count += 1
        altered_bytes = replace(http, payload=http.payload + b" ")
        assert audit(registry, variant, altered_bytes, receipt).status == HTTP_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, response_byte_count=1)).status == RECEIPT_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, response_sha256="0" * 64)).status == RECEIPT_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, evidence_id="OTHER-EVIDENCE")).status == RECEIPT_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, http_status=503)).status == RECEIPT_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, content_type="text/html")).status == RECEIPT_UNRESOLVED
        count += 1
        assert audit(registry, variant, http, replace(receipt, observed_at_utc=None)).status == RECEIPT_UNRESOLVED
        count += 1

        empty = build_legal_source_eflaw_request_variant_registry([])
        assert audit(empty, variant, http, receipt).status == NOT_REGISTERED
        count += 1
        detached = LegalSourceEflawRequestVariant(
            variant.descriptor, variant.record, replace(variant.reference, evidence_id="DETACHED")
        )
        assert audit(registry, detached, http, receipt).status == NOT_REGISTERED
        count += 1

        another_http, another_record, another_ref = make_input((
            "eflaw", "149889", "20140117", "SYNTHETIC-NATIONAL-SOURCE",
            "Synthetic National Law", "2014-01-17",
        ))
        another_ref = replace(another_ref, evidence_id=reference.evidence_id)
        assert audit(registry, variant, http, receipt, known_references=(another_ref,)).status == HTTP_UNRESOLVED
        count += 1

        with patch(
            "law_data.legal_source_eflaw_request_variant_receipt_binding.inspect_legal_source_acquisition_receipt",
            side_effect=ValueError(SECRET),
        ):
            result = audit(registry, variant, http, receipt)
            assert result.status == INSPECTION_FAILED
            safe(result)
            count += 1

        for bad, expected in (
            (lambda: audit(None, variant, http, receipt), "INVALID_VARIANT_REGISTRY"),
            (lambda: audit(registry, None, http, receipt), "INVALID_VARIANT"),
            (lambda: audit(registry, variant, None, receipt), "INVALID_HTTP_OUTCOME"),
            (lambda: audit(registry, variant, http, None), "INVALID_CLAIMED_RECEIPT"),
            (lambda: audit(registry, variant, http, receipt, known_references=[]), "INVALID_KNOWN_REFERENCES"),
            (lambda: LegalSourceEflawRequestVariantReceiptBinding(ALIGNED, "MATCH", "MATCH", "MATCH", "MATCH"),
             "DIRECT_RECEIPT_VARIANT_RESULT_FORBIDDEN"),
            (lambda: LegalSourceEflawRequestVariantReceiptBinding(ALIGNED, "MISMATCH", "MATCH", "MATCH", "MATCH"),
             "INCONSISTENT_RECEIPT_VARIANT_SUCCESS"),
        ):
            rejects(bad, (ValueError, TypeError), expected)
            count += 1

        try:
            aligned.status = LOCATOR_MISMATCH
        except (AttributeError, TypeError):
            count += 1
        else:
            raise AssertionError("MUTABLE_RECEIPT_VARIANT_RESULT")

    print("SYNTHETIC_RECEIPT_LOCATOR_CASES:", count)
    print("LEGACY_DIFFERENT_EFYD_CLAIM_REPRODUCED: True")
    print("NEW_CROSS_DESCRIPTOR_GUARD_REJECTS: True")
    print("CREDENTIAL_FREE_LOCATOR_ONLY: True")
    print("NETWORK_REQUESTS: 0")
    print("REAL_API_KEY_USED: False")
    print("FILES_WRITTEN: 0")
    print("SOURCE_CODE_CHANGED: False")
    print("OFFICIAL_ORIGIN_DECISION: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_REQUEST_VARIANT_RECEIPT_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
