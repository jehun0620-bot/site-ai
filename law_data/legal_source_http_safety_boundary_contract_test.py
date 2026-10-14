# -*- coding: utf-8 -*-
"""Offline synthetic tests: MOLEG HTTP credential and exception boundary."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from law_data.legal_source_http_safety_boundary import (
    CONNECTION_FAILED,
    HTTP_REJECTED,
    REDIRECT_BLOCKED,
    SUCCESS,
    TIMEOUT,
    TLS_FAILED,
    TRANSPORT_FAILED,
    LegalSourceHttpFetchOutcome,
    fetch_legal_source_http,
)
from law_data.legal_source_public_request_descriptor import (
    ENDPOINT,
    build_legal_source_public_request_descriptor,
)

SECRET = "SYNTHETIC_PRIVATE_CREDENTIAL_DO_NOT_LOG"
NATIONAL = {"target": "eflaw", "type": "JSON", "MST": "288857", "efYd": "20260918"}
SEOUL = {"target": "ordin", "type": "JSON", "MST": "2149501"}


class FakeResponse:
    """Response.url/request are forbidden: accessing them fails the test."""

    def __init__(self, status_code, payload=b"", history=()):
        self.status_code = status_code
        self.content = payload
        self.history = list(history)

    @property
    def url(self):
        raise AssertionError("PRIVATE_RESPONSE_URL_ACCESSED")

    @property
    def request(self):
        raise AssertionError("PRIVATE_REQUEST_ACCESSED")

    @property
    def headers(self):
        raise AssertionError("RAW_RESPONSE_HEADERS_ACCESSED")

    def raise_for_status(self):
        raise AssertionError("RAISE_FOR_STATUS_MUST_NOT_BE_CALLED")


def check_public(outcome, expected_status, expected_code=None, expected_payload=None):
    assert type(outcome) is LegalSourceHttpFetchOutcome
    assert outcome.status == expected_status
    assert outcome.http_status == expected_code
    assert outcome.payload == expected_payload
    record = outcome.public_record()
    safe_text = json.dumps(record, ensure_ascii=False)
    assert SECRET not in safe_text
    assert SECRET not in repr(outcome)
    assert "OC=" not in safe_text
    assert "OC=" not in repr(outcome)
    assert "payload" not in record
    assert "request_url" not in record
    assert "response_url" not in record
    assert "error" not in record
    assert record["record_kind"] == "LEGAL_HTTP_FETCH_PUBLIC_DIAGNOSTIC_V1"
    assert record["source_verification"] == "NOT_EVALUATED"
    assert record["legal_applicability"] == "NOT_EVALUATED"
    assert record["production_admission"] == "NOT_EVALUATED"
    assert record["response_byte_count"] == (len(expected_payload) if expected_payload is not None else None)
    assert set(record["public_request"]) == (
        {"schema_version", "source_system", "endpoint", "target", "type", "MST", "efYd", "record_kind", "credential_included"}
        if outcome.descriptor.target == "eflaw"
        else {"schema_version", "source_system", "endpoint", "target", "type", "MST", "record_kind", "credential_included"}
    )
    record["public_request"]["MST"] = "TAMPERED"
    assert outcome.descriptor.public_parameters()["MST"] != "TAMPERED"
    assert not hasattr(outcome, "__context__")
    try:
        outcome.status = "PROMOTED"  # type: ignore[misc]
    except (FrozenInstanceError, AttributeError):
        pass
    else:
        raise AssertionError("MUTABLE_OUTCOME")


def run_case(descriptor, scenario, status, code=None, payload=None):
    with patch("law_data.legal_source_http_safety_boundary.requests.get", side_effect=scenario if isinstance(scenario, Exception) else None, return_value=None if isinstance(scenario, Exception) else scenario) as getter:
        outcome = fetch_legal_source_http(descriptor, SECRET)
        assert getter.call_count == 1
        args, kwargs = getter.call_args
        assert args == (ENDPOINT,)
        assert kwargs["params"] == {**descriptor.public_parameters(), "OC": SECRET}
        assert kwargs["timeout"] == 30.0
        assert kwargs["allow_redirects"] is False
        assert kwargs["verify"] is True
    check_public(outcome, status, code, payload)
    return outcome


def check_rejected_call(call, expected_code):
    try:
        call()
    except ValueError as exc:
        assert str(exc) == expected_code
        assert SECRET not in repr(exc)
    else:
        raise AssertionError("INVALID_INPUT_ACCEPTED")


def main():
    # Never use an actual credential or call a real network API.
    with patch("socket.socket", side_effect=AssertionError("UNEXPECTED_SOCKET")), patch("socket.create_connection", side_effect=AssertionError("UNEXPECTED_CONNECT")), patch("builtins.open", side_effect=AssertionError("UNEXPECTED_FILE_IO")), patch.object(Path, "write_bytes", side_effect=AssertionError("UNEXPECTED_FILE_WRITE")):
        tested = 0
        for criteria in (NATIONAL, SEOUL):
            descriptor = build_legal_source_public_request_descriptor(criteria)
            raw_payload = b"{\"value\":\"" + SECRET.encode("ascii") + b"\"}"
            outcome = run_case(descriptor, FakeResponse(200, raw_payload), SUCCESS, 200, raw_payload)
            assert outcome.payload == raw_payload  # Exact original bytes preserved internally.
            tested += 1
            run_case(descriptor, FakeResponse(200, b""), SUCCESS, 200, b"")
            tested += 1
            for status_code in (201, 204, 400, 403, 404, 500):
                run_case(descriptor, FakeResponse(status_code), HTTP_REJECTED, status_code)
                tested += 1
            for code in (301, 302, 303, 307, 308):
                run_case(descriptor, FakeResponse(code), REDIRECT_BLOCKED, code)
                tested += 1
            run_case(descriptor, FakeResponse(200, raw_payload, history=(FakeResponse(302),)), REDIRECT_BLOCKED, 200)
            tested += 1
            # Unsafe response values must not be surfaced.
            run_case(descriptor, FakeResponse("403"), TRANSPORT_FAILED)
            tested += 1
            run_case(descriptor, FakeResponse(True), TRANSPORT_FAILED)
            tested += 1
            run_case(descriptor, FakeResponse(200, "not bytes"), TRANSPORT_FAILED)
            tested += 1
            unsafe_text = "request=https://www.law.go.kr/?OC=" + SECRET
            cases = (
                (requests.exceptions.Timeout(unsafe_text), TIMEOUT),
                (requests.exceptions.ConnectTimeout(unsafe_text), TIMEOUT),
                (requests.exceptions.ReadTimeout(unsafe_text), TIMEOUT),
                (requests.exceptions.SSLError(unsafe_text), TLS_FAILED),
                (requests.exceptions.ConnectionError(unsafe_text), CONNECTION_FAILED),
                (requests.exceptions.HTTPError(unsafe_text), TRANSPORT_FAILED),
                (requests.exceptions.RequestException(unsafe_text), TRANSPORT_FAILED),
                (RuntimeError(unsafe_text), TRANSPORT_FAILED),
            )
            for original, status in cases:
                run_case(descriptor, original, status)
                tested += 1
            # Bad caller input rejected with fixed messages before any request.
            with patch("law_data.legal_source_http_safety_boundary.requests.get", side_effect=AssertionError("UNEXPECTED_REQUEST")) as getter:
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, ""), "INVALID_CREDENTIAL")
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, SECRET + "\n"), "INVALID_CREDENTIAL")
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, 123), "INVALID_CREDENTIAL")
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, SECRET, timeout_seconds=True), "INVALID_TIMEOUT")
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, SECRET, timeout_seconds=float("nan")), "INVALID_TIMEOUT")
                check_rejected_call(lambda: fetch_legal_source_http(descriptor, SECRET, timeout_seconds=121), "INVALID_TIMEOUT")
                check_rejected_call(lambda: fetch_legal_source_http("http://unsafe/?OC=" + SECRET, SECRET), "INVALID_DESCRIPTOR")
                assert getter.call_count == 0
            # Directly constructed outcomes must obey the same transport-failure
            # status contract as fetch_legal_source_http(). None is required.
            for failure in (TIMEOUT, CONNECTION_FAILED, TLS_FAILED, TRANSPORT_FAILED):
                for incorrect_code in (200, 302, 403):
                    check_rejected_call(
                        lambda status=failure, code=incorrect_code:
                            LegalSourceHttpFetchOutcome(descriptor, status, code),
                        "INCONSISTENT_TRANSPORT_OUTCOME",
                    )
                    tested += 1
                check_public(LegalSourceHttpFetchOutcome(descriptor, failure), failure)
                tested += 1
            # A blocked redirect may hold the final 200 after a redirect history;
            # HTTP rejection with a concrete non-200 status also remains valid.
            check_public(LegalSourceHttpFetchOutcome(descriptor, REDIRECT_BLOCKED, 200), REDIRECT_BLOCKED, 200)
            tested += 1
            check_public(LegalSourceHttpFetchOutcome(descriptor, REDIRECT_BLOCKED, 302), REDIRECT_BLOCKED, 302)
            tested += 1
            check_public(LegalSourceHttpFetchOutcome(descriptor, HTTP_REJECTED, 403), HTTP_REJECTED, 403)
            tested += 1
        print("TARGETS_TESTED: 2")
        print("SYNTHETIC_HTTP_CASES:", tested)
        print("REAL_API_KEY_USED: False")
        print("NETWORK_REQUESTS: 0")
        print("FILES_WRITTEN: 0")
        print("SOURCE_CODE_CHANGED: False")
        print("PRODUCTION_ADMISSION: NOT_EVALUATED")
        print("LEGAL_SOURCE_HTTP_SAFETY_BOUNDARY_CONTRACT_PASS")


if __name__ == "__main__":
    main()
