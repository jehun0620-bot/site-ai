# -*- coding: ascii -*-
"""Offline synthetic tests for opt-in in-memory eflaw LOCAL observation."""
from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch

import requests

from law_data.legal_source_eflaw_local_acquisition_observation import (
    LOCAL_CLOCK_ANOMALY, LOCAL_NON_SUCCESS, LOCAL_SUCCESS,
    LegalSourceEflawLocalAcquisitionObservation,
    fetch_legal_source_eflaw_with_local_observation,
)
from law_data.legal_source_http_safety_boundary import (
    HTTP_REJECTED, REDIRECT_BLOCKED, TIMEOUT,
)
from law_data.legal_source_public_request_descriptor import (
    ENDPOINT, build_legal_source_public_request_descriptor,
)

SECRET = "SYNTHETIC_PRIVATE_CREDENTIAL_NO_LOG"
DATA = b'{"local":"response"}'


class FakeResponse:
    def __init__(self, status=200, body=DATA, history=()):
        self.status_code = status
        self.content = body
        self.history = history

    @property
    def url(self):
        raise AssertionError("UNSAFE_URL_ACCESSED")

    @property
    def request(self):
        raise AssertionError("UNSAFE_REQUEST_ACCESSED")

    @property
    def headers(self):
        raise AssertionError("UNSAFE_HEADERS_ACCESSED")


def rejects(call, label):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == label, "UNEXPECTED_ERROR_CODE"
        assert SECRET not in str(exc)
    else:
        raise AssertionError("EXPECTED_REJECTION")


def safe(observation):
    record = observation.public_record()
    body = json.dumps(record, ensure_ascii=True)
    for sensitive in (SECRET, "OC=", "https://", "SYNTHETIC", "DATA", "20000101"):
        assert sensitive not in body, "PRIVATE_DIAGNOSTIC_EXPOSED"
        assert sensitive not in repr(observation), "PRIVATE_REPR_EXPOSED"
    for field in (
        "acquisition_authenticity_decision", "official_origin_decision",
        "source_verification_decision", "current_validity_decision",
        "legal_authority_decision", "original_text_identity_decision", "legal_applicability_decision",
        "production_admission_decision",
    ):
        assert record[field] == "NOT_EVALUATED"
    assert record["response_content_type"] == "NOT_OBSERVED"
    assert record["final_response_url"] == "NOT_OBSERVED"
    assert record["actual_authenticated_request_url"] == "NOT_OBSERVED"
    assert "response_sha256" not in record
    assert "local_event_id" not in record
    assert "local_started_at_utc" not in record
    assert "local_finished_at_utc" not in record
    assert "payload" not in record


def main():
    tested = 0
    national = build_legal_source_public_request_descriptor({
        "target": "eflaw", "type": "JSON", "MST": "121615", "efYd": "20120106",
    })
    ordin = build_legal_source_public_request_descriptor({
        "target": "ordin", "type": "JSON", "MST": "2149501",
    })
    call = fetch_legal_source_eflaw_with_local_observation

    with patch("socket.socket", side_effect=AssertionError("NETWORK_FORBIDDEN")), patch(
        "socket.create_connection", side_effect=AssertionError("NETWORK_FORBIDDEN")
    ), patch("builtins.open", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch.object(
        Path, "read_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")
    ), patch.object(Path, "write_bytes", side_effect=AssertionError("FILE_IO_FORBIDDEN")), patch(
        "law_data.legal_source_http_safety_boundary.requests.get"
    ) as getter:
        rejects(lambda: call(national, SECRET), "LOCAL_OBSERVATION_OPT_IN_REQUIRED")
        tested += 1
        rejects(lambda: call(national, SECRET, enabled=1), "LOCAL_OBSERVATION_OPT_IN_REQUIRED")
        tested += 1
        rejects(lambda: call(ordin, SECRET, enabled=True), "INVALID_EFLAW_DESCRIPTOR")
        tested += 1
        rejects(lambda: call("not-a-descriptor", SECRET, enabled=True), "INVALID_EFLAW_DESCRIPTOR")
        tested += 1
        assert getter.call_count == 0

        rejects(lambda: call(national, "", enabled=True), "INVALID_CREDENTIAL")
        tested += 1
        rejects(lambda: call(national, SECRET + "\n", enabled=True), "INVALID_CREDENTIAL")
        tested += 1
        rejects(lambda: call(national, SECRET, enabled=True, timeout_seconds=True), "INVALID_TIMEOUT")
        tested += 1
        assert getter.call_count == 0

        getter.return_value = FakeResponse()
        observed = call(national, SECRET, enabled=True)
        assert observed.status == LOCAL_SUCCESS
        assert observed.http_outcome.payload == DATA
        assert observed.response_sha256 == hashlib.sha256(DATA).hexdigest()
        assert observed.response_byte_count == len(DATA)
        assert observed.local_started_at_utc.endswith("Z")
        assert observed.local_finished_at_utc.endswith("Z")
        assert len(observed.local_event_id) == 32
        assert observed.local_started_at_utc <= observed.local_finished_at_utc
        assert getter.call_count == 1
        args, kwargs = getter.call_args
        assert args == (ENDPOINT,)
        assert kwargs == {
            "params": {**national.public_parameters(), "OC": SECRET},
            "timeout": 30.0, "allow_redirects": False, "verify": True,
        }
        safe(observed)
        tested += 1

        getter.reset_mock(return_value=True)
        getter.return_value = FakeResponse(status=403)
        denied = call(national, SECRET, enabled=True)
        assert denied.status == LOCAL_NON_SUCCESS
        assert denied.http_outcome.status == HTTP_REJECTED
        assert denied.response_byte_count is None and denied.response_sha256 is None
        assert getter.call_count == 1
        safe(denied)
        tested += 1

        getter.reset_mock(return_value=True)
        getter.return_value = FakeResponse(status=302)
        redirected = call(national, SECRET, enabled=True)
        assert redirected.status == LOCAL_NON_SUCCESS
        assert redirected.http_outcome.status == REDIRECT_BLOCKED
        assert getter.call_count == 1
        safe(redirected)
        tested += 1

        getter.reset_mock(return_value=True)
        getter.side_effect = requests.exceptions.Timeout("OC=" + SECRET)
        failed = call(national, SECRET, enabled=True)
        assert failed.status == LOCAL_NON_SUCCESS
        assert failed.http_outcome.status == TIMEOUT
        assert getter.call_count == 1
        safe(failed)
        tested += 1
        getter.side_effect = None
        getter.reset_mock(return_value=True)

        getter.return_value = FakeResponse(status=200, body=b"")
        empty = call(national, SECRET, enabled=True)
        assert empty.status == LOCAL_SUCCESS
        assert empty.response_byte_count == 0
        assert empty.response_sha256 == hashlib.sha256(b"").hexdigest()
        safe(empty)
        tested += 1

        with patch(
            "law_data.legal_source_eflaw_local_acquisition_observation._utc_iso",
            side_effect=("2026-10-14T14:00:01.000000Z", "2026-10-14T14:00:00.000000Z"),
        ):
            clock = call(national, SECRET, enabled=True)
            assert clock.status == LOCAL_CLOCK_ANOMALY
            safe(clock)
            tested += 1

        rejects(
            lambda: LegalSourceEflawLocalAcquisitionObservation(
                observed.http_outcome, observed.local_event_id,
                observed.local_started_at_utc, observed.local_finished_at_utc,
                observed.response_sha256, observed.response_byte_count, LOCAL_SUCCESS,
            ),
            "DIRECT_LOCAL_OBSERVATION_CONSTRUCTION_FORBIDDEN",
        )
        tested += 1
        rejects(lambda: replace(observed, response_sha256="f" * 64),
                "INCONSISTENT_LOCAL_BYTES")
        tested += 1
        rejects(lambda: replace(observed, response_byte_count=999),
                "INCONSISTENT_LOCAL_BYTES")
        tested += 1
        rejects(lambda: replace(observed, status=LOCAL_NON_SUCCESS),
                "INCONSISTENT_LOCAL_OBSERVATION_STATUS")
        tested += 1
        try:
            observed.status = LOCAL_NON_SUCCESS
        except (AttributeError, FrozenInstanceError):
            tested += 1
        else:
            raise AssertionError("OBSERVATION_MUTABLE")

    print("SYNTHETIC_OPT_IN_OBSERVATION_CASES:", tested)
    print("LEGACY_FETCH_UNCHANGED: True")
    print("SENSITIVE_RESPONSE_METADATA_ACCESSED: False")
    print("LOCAL_TIMESTAMP_AND_EVENT_ID_NOT_ATTESTED: True")
    print("CONTENT_TYPE_OR_FINAL_URL_FABRICATED: False")
    print("NETWORK_REQUESTS: 0")
    print("REAL_API_KEY_USED: False")
    print("FILES_WRITTEN: 0")
    print("PRODUCTION_ADMISSION: NOT_EVALUATED")
    print("LEGAL_SOURCE_EFLAW_LOCAL_ACQUISITION_OBSERVATION_CONTRACT_PASS")


if __name__ == "__main__":
    main()
