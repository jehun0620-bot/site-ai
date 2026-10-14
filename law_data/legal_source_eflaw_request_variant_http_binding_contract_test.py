# -*- coding: utf-8 -*-
"""No-network/no-file eflaw request-variant HTTP binding contract tests."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    build_legal_source_eflaw_request_variant_registry,
)
from law_data.legal_source_eflaw_request_variant_registry_contract_test import create
from law_data.legal_source_eflaw_request_variant_http_binding import (
    BOUND, DECLARED_DATE_MISMATCH, DECLARED_DATE_UNRESOLVED,
    DESCRIPTOR_MISMATCH, IDENTITY_UNRESOLVED, INSPECTION_FAILED, NOT_REGISTERED,
    LegalSourceEflawRequestVariantHttpBinding,
    inspect_legal_source_eflaw_request_variant_http_binding,
)
from law_data.legal_source_response_identity_inspection_contract_test import make_input
from law_data.legal_source_public_request_descriptor import build_legal_source_public_request_descriptor
from law_data.legal_source_http_safety_boundary import LegalSourceHttpFetchOutcome, SUCCESS

SECRET = "SYNTHETIC_PRIVATE_CREDENTIAL_NOT_FOR_PUBLIC_LOG"


def rejects(callback, expected_type, expected_code):
    try:
        callback()
    except expected_type as exc:
        assert str(exc) == expected_code, "UNEXPECTED_ERROR_CODE"
        assert SECRET not in str(exc)
    else:
        raise AssertionError("REJECTION_NOT_RAISED")


def check_safe(result):
    public = result.public_record()
    serialized = json.dumps(public, ensure_ascii=True)
    for token in (SECRET, "SYNTHETIC-NATIONAL-SOURCE", "121615", "20120106",
                  "synthetic.example", "SYNTHETIC-EVIDENCE", "OC=", "SOURCE_VERIFIED"):
        assert token not in serialized, "PRIVATE_CONTENT_EXPOSED"
    for key in (
        "official_origin_decision", "source_verification_decision",
        "original_text_identity_decision", "current_validity_decision",
        "legal_authority_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert public[key] == "NOT_EVALUATED"
    assert "SYNTHETIC" not in repr(result)


def main():
    count = 0
    # make_input uses escaped Unicode keys in the checked-in test fixture;
    # the PowerShell pipe cannot damage those source-file literal keys.
    raw, record, ref = make_input((
        "eflaw", "121615", "20120106",
        "SYNTHETIC-NATIONAL-SOURCE", "Synthetic National Law", "2012-01-06",
    ))
    variant = LegalSourceEflawRequestVariant(raw.descriptor, record, ref)
    registry = build_legal_source_eflaw_request_variant_registry([variant])
    inspect = inspect_legal_source_eflaw_request_variant_http_binding

    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "write_bytes", side_effect=AssertionError("FILE_WRITE_FORBIDDEN")
    ), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_READ_FORBIDDEN")
    ):
        good = inspect(registry, variant, raw)
        assert good.status == BOUND
        check_safe(good)
        count += 1

        swapped = replace(raw, descriptor=build_legal_source_public_request_descriptor({
            "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120201",
        }))
        outcome = inspect(registry, variant, swapped)
        assert outcome.status == DESCRIPTOR_MISMATCH
        check_safe(outcome)
        count += 1

        altered_mst = replace(raw, descriptor=build_legal_source_public_request_descriptor({
            "target": "eflaw", "type": "JSON", "MST": "149889", "efYd": "20120106",
        }))
        assert inspect(registry, variant, altered_mst).status == DESCRIPTOR_MISMATCH
        count += 1

        tampered = replace(raw, payload=raw.payload + b"\n")
        assert inspect(registry, variant, tampered).status == IDENTITY_UNRESOLVED
        count += 1

        http_failure = LegalSourceHttpFetchOutcome(raw.descriptor, "TRANSPORT_TIMEOUT", None, None)
        assert inspect(registry, variant, http_failure).status == IDENTITY_UNRESOLVED
        count += 1

        fake_date = LegalSourceEflawRequestVariant(
            raw.descriptor, replace(record, effective_date="2012-02-01"), ref,
        )
        mismatch_reg = build_legal_source_eflaw_request_variant_registry([fake_date])
        assert inspect(mismatch_reg, fake_date, raw).status == DECLARED_DATE_MISMATCH
        count += 1

        unknown_date = LegalSourceEflawRequestVariant(
            raw.descriptor, replace(record, effective_date=None), ref,
        )
        unknown_reg = build_legal_source_eflaw_request_variant_registry([unknown_date])
        assert inspect(unknown_reg, unknown_date, raw).status == DECLARED_DATE_UNRESOLVED
        count += 1

        detached = LegalSourceEflawRequestVariant(
            raw.descriptor, record, replace(ref, evidence_id="SYNTHETIC-EVIDENCE-OTHER"),
        )
        assert inspect(registry, detached, raw).status == NOT_REGISTERED
        count += 1

        empty = build_legal_source_eflaw_request_variant_registry([])
        assert inspect(empty, variant, raw).status == NOT_REGISTERED
        count += 1

        # Genuine second request date may be registered for the same MST, but
        # its response payload must have matching content date and hash.
        second_http, second_record, second_ref = make_input((
            "eflaw", "121615", "20120201",
            "SYNTHETIC-NATIONAL-SOURCE", "Synthetic National Law", "2012-02-01",
        ))
        second_ref = replace(second_ref, evidence_id="SYNTHETIC-EVIDENCE-B")
        second_variant = LegalSourceEflawRequestVariant(second_http.descriptor, second_record, second_ref)
        pair = build_legal_source_eflaw_request_variant_registry([variant, second_variant])
        assert inspect(pair, variant, raw).status == BOUND
        assert inspect(pair, second_variant, second_http).status == BOUND
        assert inspect(pair, variant, second_http).status == DESCRIPTOR_MISMATCH
        count += 3

        # Even an otherwise identical descriptor with mismatched actual JSON
        # effective date is rejected by the existing identity inspector.
        assert inspect(pair, second_variant, replace(second_http, payload=raw.payload)).status == IDENTITY_UNRESOLVED
        count += 1

        # A third reference with same evidence ID at a DIFFERENT MST is an
        # explicit local collision even if it isn't in the variant inventory.
        another = create(mst="149889", efyd="20140117", evidence_id=ref.evidence_id)
        assert inspect(registry, variant, raw, known_references=(another.reference,)).status == IDENTITY_UNRESOLVED
        count += 1

        rejects(lambda: inspect(None, variant, raw), TypeError, "INVALID_VARIANT_REGISTRY")
        rejects(lambda: inspect(registry, None, raw), TypeError, "INVALID_VARIANT")
        rejects(lambda: inspect(registry, variant, None), TypeError, "INVALID_HTTP_OUTCOME")
        rejects(lambda: inspect(registry, variant, raw, known_references=[]), TypeError, "INVALID_KNOWN_REFERENCES")
        count += 4

        # Exceptions from upstream must be suppressed and turned into fixed codes.
        with patch(
            "law_data.legal_source_eflaw_request_variant_http_binding.inspect_legal_source_response_identity",
            side_effect=ValueError(SECRET),
        ):
            failed = inspect(registry, variant, raw)
            assert failed.status == INSPECTION_FAILED
            check_safe(failed)
            count += 1

        rejects(lambda: LegalSourceEflawRequestVariantHttpBinding(
            BOUND, "MATCH", "MATCH_DECLARED_UNVERIFIED", SECRET,
        ), ValueError, "INVALID_UPSTREAM_IDENTITY_STATUS")
        count += 1

        rejects(lambda: LegalSourceEflawRequestVariantHttpBinding(
            BOUND, "MATCH", "MATCH_DECLARED_UNVERIFIED", "RESPONSE_IDENTITY_ALIGNED_LIMITED_UNVERIFIED_ORIGIN",
        ), ValueError, "DIRECT_BINDING_RESULT_CONSTRUCTION_FORBIDDEN")
        count += 1

        rejects(lambda: LegalSourceEflawRequestVariantHttpBinding(
            BOUND, "MISMATCH", "MATCH_DECLARED_UNVERIFIED", "RESPONSE_IDENTITY_ALIGNED_LIMITED_UNVERIFIED_ORIGIN",
        ), ValueError, "INCONSISTENT_VARIANT_HTTP_SUCCESS")
        count += 1

        try:
            good.status = DESCRIPTOR_MISMATCH
        except (FrozenInstanceError, AttributeError):
            count += 1
        else:
            raise AssertionError("MUTABLE_BINDING")

    print("TARGETS_TESTED: 1")
    print("SYNTHETIC_EFLAW_HTTP_BINDING_CASES:", count)
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("SOURCE_CODE_CHANGED: False")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_REQUEST_HTTP_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
