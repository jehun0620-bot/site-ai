# -*- coding: ascii -*-
"""Offline synthetic contract; never authenticates or actually acquires law."""
from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

from law_data.legal_source_eflaw_local_acquisition_observation import (
    LOCAL_CLOCK_ANOMALY, LOCAL_NON_SUCCESS, LOCAL_SUCCESS,
    fetch_legal_source_eflaw_with_local_observation,
)
from law_data.legal_source_eflaw_local_observation_variant_binding import (
    ALIGNED, BINDING_UNRESOLVED, INSPECTION_FAILED, NOT_REGISTERED,
    OBSERVATION_UNRESOLVED, OUTCOME_MISMATCH, REQUEST_MISMATCH,
    LegalSourceEflawLocalObservationVariantBinding,
    inspect_legal_source_eflaw_local_observation_variant_binding,
)
from law_data.legal_source_eflaw_request_variant_registry import (
    LegalSourceEflawRequestVariant,
    build_legal_source_eflaw_request_variant_registry,
)
from law_data.legal_source_http_safety_boundary import (
    HTTP_REJECTED, LegalSourceHttpFetchOutcome,
)
from law_data.legal_source_response_identity_inspection_contract_test import make_input
from law_data.legal_source_public_request_descriptor import build_legal_source_public_request_descriptor

CREDENTIAL = "SYNTHETIC_PRIVATE_OC_NOT_A_REAL_API_KEY"


def rejected(function, exception_type, message):
    try:
        function()
    except exception_type as exc:
        assert str(exc) == message, "UNEXPECTED_REJECTION"
        assert CREDENTIAL not in str(exc)
    else:
        raise AssertionError("MISSING_REJECTION")


def safe(result):
    doc = result.public_record()
    public = json.dumps(doc, ensure_ascii=True)
    private = (CREDENTIAL, "OC=", "SYNTHETIC-NATIONAL", "SYNTHETIC-eflaw",
               "121615", "20120106", "https://", "2012-01-06")
    for secret in private:
        assert secret not in public and secret not in repr(result), "PRIVATE_DATA_EXPOSED"
    for field in ("acquisition_authenticity_decision", "official_origin_decision",
                  "original_text_identity_decision", "source_verification_decision",
                  "current_validity_decision", "legal_authority_decision",
                  "legal_applicability_decision", "production_admission_decision"):
        assert doc[field] == "NOT_EVALUATED"
    assert doc["requested_descriptor_basis"] == "CALLER_SUPPLIED_NOT_WIRE_OBSERVED"
    assert "response_sha256" not in doc and "local_event_id" not in doc


def main():
    checked = 0
    http, record, ref = make_input((
        "eflaw", "121615", "20120106", "SYNTHETIC-NATIONAL-SOURCE",
        "Synthetic National Law", "2012-01-06",
    ))
    other, _, _ = make_input((
        "eflaw", "121615", "20120201", "SYNTHETIC-NATIONAL-SOURCE",
        "Synthetic National Law", "2012-02-01",
    ))
    variant = LegalSourceEflawRequestVariant(http.descriptor, record, ref)
    registry = build_legal_source_eflaw_request_variant_registry([variant])
    empty = build_legal_source_eflaw_request_variant_registry([])
    observe = fetch_legal_source_eflaw_with_local_observation
    inspect = inspect_legal_source_eflaw_local_observation_variant_binding

    with patch("socket.socket", side_effect=AssertionError("SOCKET_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("SOCKET_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_READ_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_WRITE_FORBIDDEN")
    ), patch("law_data.legal_source_eflaw_local_acquisition_observation.fetch_legal_source_http") as fetch:
        rejected(lambda: observe(http.descriptor, CREDENTIAL), ValueError,
                 "LOCAL_OBSERVATION_OPT_IN_REQUIRED")
        assert fetch.call_count == 0
        checked += 1

        fetch.return_value = http
        good_observation = observe(http.descriptor, CREDENTIAL, enabled=True)
        assert fetch.call_count == 1
        assert good_observation.status == LOCAL_SUCCESS
        assert good_observation.http_outcome is http
        assert good_observation.response_sha256 == hashlib.sha256(http.payload).hexdigest()
        assert good_observation.response_byte_count == len(http.payload)
        result = inspect(registry, variant, http.descriptor, good_observation)
        assert result.status == ALIGNED
        assert result.registered_variant_check == result.requested_descriptor_check == "MATCH"
        safe(result)
        checked += 1

        # The caller's declared requested descriptor must be separately bound.
        r = inspect(registry, variant, other.descriptor, good_observation)
        assert r.status == REQUEST_MISMATCH
        safe(r)
        checked += 1

        # Old observation wrapper can hold a swapped outcome and report LOCAL_SUCCESS.
        fetch.reset_mock(return_value=True)
        fetch.return_value = other
        swapped_observation = observe(http.descriptor, CREDENTIAL, enabled=True)
        assert swapped_observation.status == LOCAL_SUCCESS
        assert swapped_observation.http_outcome.descriptor != http.descriptor
        r = inspect(registry, variant, http.descriptor, swapped_observation)
        assert r.status == OUTCOME_MISMATCH
        safe(r)
        checked += 1

        # A plausible observation with a changed payload is NOT source identity.
        fetch.reset_mock(return_value=True)
        fetch.return_value = replace(http, payload=http.payload + b"X")
        tampered_observation = observe(http.descriptor, CREDENTIAL, enabled=True)
        assert tampered_observation.status == LOCAL_SUCCESS
        r = inspect(registry, variant, http.descriptor, tampered_observation)
        assert r.status == BINDING_UNRESOLVED
        safe(r)
        checked += 1

        fetch.reset_mock(return_value=True)
        fetch.return_value = LegalSourceHttpFetchOutcome(http.descriptor, HTTP_REJECTED, 403)
        denied = observe(http.descriptor, CREDENTIAL, enabled=True)
        assert denied.status == LOCAL_NON_SUCCESS
        r = inspect(registry, variant, http.descriptor, denied)
        assert r.status == OBSERVATION_UNRESOLVED
        safe(r)
        checked += 1

        # Local reversed-clock event cannot be admitted even with valid bytes.
        fetch.reset_mock(return_value=True)
        fetch.return_value = http
        with patch("law_data.legal_source_eflaw_local_acquisition_observation._utc_iso",
                   side_effect=("2026-10-14T14:00:01.000000Z", "2026-10-14T14:00:00.000000Z")):
            reversed_clock = observe(http.descriptor, CREDENTIAL, enabled=True)
        assert reversed_clock.status == LOCAL_CLOCK_ANOMALY
        r = inspect(registry, variant, http.descriptor, reversed_clock)
        assert r.status == OBSERVATION_UNRESOLVED
        checked += 1

        assert inspect(empty, variant, http.descriptor, good_observation).status == NOT_REGISTERED
        checked += 1
        detached = LegalSourceEflawRequestVariant(
            http.descriptor, record, replace(ref, evidence_id="SYNTHETIC-DETACHED")
        )
        assert inspect(registry, detached, http.descriptor, good_observation).status == NOT_REGISTERED
        checked += 1

        # The local observation hash is a self-computed byte digest, not an
        # independent comparison to the reference; upstream must recheck.
        forged_reference = replace(ref, declared_sha256="f" * 64)
        forged_variant = LegalSourceEflawRequestVariant(http.descriptor, record, forged_reference)
        forged_registry = build_legal_source_eflaw_request_variant_registry([forged_variant])
        assert inspect(forged_registry, forged_variant, http.descriptor,
                       good_observation).status == BINDING_UNRESOLVED
        checked += 1

        # All untrusted upstream exceptions are sanitized.
        with patch(
            "law_data.legal_source_eflaw_local_observation_variant_binding.inspect_legal_source_eflaw_request_variant_http_binding",
            side_effect=RuntimeError("OC=" + CREDENTIAL),
        ):
            failure = inspect(registry, variant, http.descriptor, good_observation)
            assert failure.status == INSPECTION_FAILED
            safe(failure)
        checked += 1

        for fn, code in (
            (lambda: inspect(None, variant, http.descriptor, good_observation),
             "INVALID_VARIANT_REGISTRY"),
            (lambda: inspect(registry, None, http.descriptor, good_observation),
             "INVALID_VARIANT"),
            (lambda: inspect(registry, variant, None, good_observation),
             "INVALID_REQUEST_DESCRIPTOR"),
            (lambda: inspect(registry, variant, http.descriptor, None),
             "INVALID_LOCAL_OBSERVATION"),
            (lambda: inspect(registry, variant, http.descriptor, good_observation,
                             known_references=[]), "INVALID_KNOWN_REFERENCES"),
        ):
            rejected(fn, TypeError, code)
            checked += 1

        rejected(lambda: LegalSourceEflawLocalObservationVariantBinding(
            ALIGNED, "MATCH", "MATCH", "MATCH", "MATCH", "MATCH"), ValueError,
            "DIRECT_OBSERVATION_VARIANT_RESULT_FORBIDDEN")
        checked += 1
        rejected(lambda: LegalSourceEflawLocalObservationVariantBinding(
            ALIGNED, "MISMATCH", "MATCH", "MATCH", "MATCH", "MATCH"), ValueError,
            "INCONSISTENT_OBSERVATION_VARIANT_SUCCESS")
        checked += 1
        rejected(lambda: LegalSourceEflawLocalObservationVariantBinding(
            "SOURCE_VERIFIED", "MATCH", "MATCH", "MATCH", "MATCH", "MATCH"), ValueError,
            "INVALID_OBSERVATION_VARIANT_STATUS")
        checked += 1
        try:
            result.status = REQUEST_MISMATCH
        except (FrozenInstanceError, AttributeError):
            checked += 1
        else:
            raise AssertionError("RESULT_MUTABLE")

    assert checked == 20, checked
    print("SYNTHETIC_OBSERVATION_VARIANT_CASES:", checked)
    print("EXPLICIT_REQUEST_AND_OUTCOME_DESCRIPTOR_GUARDS: True")
    print("LOCAL_SUCCESS_WITH_TAMPERED_BYTES_REJECTED_UPSTREAM: True")
    print("LOCAL_SUCCESS_WITH_SWAPPED_DESCRIPTOR_REJECTED: True")
    print("UNATTESTED_LOCAL_CLOCK_NEVER_PROMOTED: True")
    print("REAL_API_KEY_USED: False")
    print("NETWORK_REQUESTS: 0")
    print("FILES_WRITTEN: 0")
    print("ACQUISITION_AUTHENTICITY: NOT_EVALUATED")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_LOCAL_OBSERVATION_VARIANT_BINDING_CONTRACT_PASS")


if __name__ == "__main__":
    main()
